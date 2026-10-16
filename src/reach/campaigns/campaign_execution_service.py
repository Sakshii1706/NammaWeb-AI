from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from reach.providers.base import SendRequest
from reach.providers.registry import ProviderRegistry
from reach.campaigns.mock_message_logger import MockMessageLogger


@dataclass(frozen=True)
class ExecutionResult:
    campaign_id: int
    total_recipients: int
    sent: int
    failed: int
    skipped: int


class CampaignExecutionService:
    """
    Executes workspace-scoped campaigns through outbound providers.

    Execution is resumable:
    - pending recipients are processed
    - failed recipients are retried
    - sent recipients are never sent again
    - skipped recipients are never sent again

    Provider selection is delegated to ProviderRegistry.
    """

    def __init__(
        self,
        campaign_service,
        compliance_service,
        provider_registry: ProviderRegistry,
    ):
        self.campaign_service = campaign_service
        self.compliance_service = compliance_service
        self.provider_registry = provider_registry
        self.mock_message_logger = MockMessageLogger(
            campaign_service.session
        )

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def render_template(
        template: str,
        *,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> str:
        rendered = template or ""

        replacements = {
            "{{full_name}}": full_name or "",
            "{{email}}": email or "",
            "{{phone}}": phone or "",
        }

        for placeholder, value in replacements.items():
            rendered = rendered.replace(
                placeholder,
                value,
            )

        return rendered

    @staticmethod
    def _get_recipient_address(
        recipient,
        channel: str,
    ) -> str:
        normalized = channel.strip().lower()

        if normalized == "email":
            return (recipient.email or "").strip()

        if normalized == "whatsapp":
            return (recipient.phone or "").strip()

        raise ValueError(
            f"Unsupported campaign channel: {channel}"
        )

    def execute_campaign(
        self,
        workspace_id: int,
        campaign_id: int,
    ) -> ExecutionResult:
        """
        Execute or resume a campaign.

        Recipient state is the source of truth for resumability:

        pending  -> attempt delivery
        failed   -> retry delivery
        sent     -> skip
        skipped  -> skip
        """

        campaign = self.campaign_service.get_campaign(
            campaign_id=campaign_id,
        )

        if campaign is None:
            raise ValueError("Campaign not found")

        if campaign.status == "cancelled":
            raise ValueError(
                "Campaign cannot be executed from status 'cancelled'"
            )

        recipients = self.campaign_service.list_recipients(
            campaign_id=campaign_id,
        )

        now = self.utcnow()

        campaign.status = "running"

        if campaign.started_at is None:
            campaign.started_at = now

        campaign.updated_at = now

        self.campaign_service.session.commit()

        sent = 0
        failed = 0
        skipped = 0

        provider = self.provider_registry.get(
            campaign.channel
        )

        for recipient in recipients:
            # ----------------------------------------------------------
            # Idempotency / resumability
            # ----------------------------------------------------------

            if recipient.status in {"sent", "skipped"}:
                continue

            if recipient.status not in {"pending", "failed"}:
                continue

            destination = self._get_recipient_address(
                recipient,
                campaign.channel,
            )

            # ----------------------------------------------------------
            # Message rendering
            # ----------------------------------------------------------

            message = self.render_template(
                campaign.message_template or "",
                full_name=recipient.full_name,
                email=recipient.email,
                phone=recipient.phone,
            )

            # ----------------------------------------------------------
            # Compliance gate
            # ----------------------------------------------------------

            decision = self.compliance_service.check_can_send(
                channel=campaign.channel,
                contact_key=destination,
            )

            if not decision.allowed:
                recipient.status = "skipped"
                recipient.updated_at = self.utcnow()

                self.campaign_service.create_delivery_attempt(
                    campaign_recipient_id=recipient.id,
                    provider=provider.provider_name,
                    channel=campaign.channel,
                    status="skipped",
                    error_message=decision.reason,
                )

                self.mock_message_logger.record(
                    campaign_id=campaign.id,
                    workspace_id=workspace_id,
                    recipient_id=recipient.id,
                    channel=campaign.channel,
                    provider=provider.provider_name,
                    recipient=destination,
                    recipient_name=recipient.full_name,
                    subject=campaign.subject,
                    message=message,
                    status="skipped",
                    error_message=decision.reason,
                )

                self.campaign_service.session.commit()

                skipped += 1
                continue

            # ----------------------------------------------------------
            # Provider request
            # ----------------------------------------------------------

            request = SendRequest(
                recipient=destination,
                message=message,
                subject=campaign.subject,
                recipient_name=recipient.full_name,
            )

            # ----------------------------------------------------------
            # Provider call
            # ----------------------------------------------------------

            result = provider.send(request)

            # ----------------------------------------------------------
            # Successful delivery
            # ----------------------------------------------------------

            if result.success:
                recipient.status = "sent"

                recipient.provider_recipient_id = (
                    result.provider_message_id
                )

                self.campaign_service.create_delivery_attempt(
                    campaign_recipient_id=recipient.id,
                    provider=result.provider,
                    channel=result.channel,
                    status="sent",
                    provider_message_id=result.provider_message_id,
                )

                self.mock_message_logger.record(
                    campaign_id=campaign.id,
                    workspace_id=workspace_id,
                    recipient_id=recipient.id,
                    channel=result.channel,
                    provider=result.provider,
                    recipient=destination,
                    recipient_name=recipient.full_name,
                    subject=campaign.subject,
                    message=message,
                    status="sent",
                    provider_message_id=result.provider_message_id,
                )

                sent += 1

            # ----------------------------------------------------------
            # Failed delivery
            # ----------------------------------------------------------

            else:
                recipient.status = "failed"

                self.campaign_service.create_delivery_attempt(
                    campaign_recipient_id=recipient.id,
                    provider=result.provider,
                    channel=result.channel,
                    status="failed",
                    error_message=result.error_message,
                )

                self.mock_message_logger.record(
                    campaign_id=campaign.id,
                    workspace_id=workspace_id,
                    recipient_id=recipient.id,
                    channel=result.channel,
                    provider=result.provider,
                    recipient=destination,
                    recipient_name=recipient.full_name,
                    subject=campaign.subject,
                    message=message,
                    status="failed",
                    error_message=result.error_message,
                )

                failed += 1

            recipient.updated_at = self.utcnow()

            self.campaign_service.session.commit()

        # --------------------------------------------------------------
        # Execution pass completed
        # --------------------------------------------------------------

        now = self.utcnow()

        campaign.status = "completed"
        campaign.completed_at = now
        campaign.updated_at = now

        self.campaign_service.session.commit()

        return ExecutionResult(
            campaign_id=campaign.id,
            total_recipients=len(recipients),
            sent=sent,
            failed=failed,
            skipped=skipped,
        )
