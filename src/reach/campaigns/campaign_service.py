from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from reach.db.campaign_models import (
    Campaign,
    CampaignRecipient,
    DeliveryAttempt,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignService:
    """Workspace-scoped service for campaign management."""

    def __init__(self, session: Session, workspace_id: int):
        if workspace_id <= 0:
            raise ValueError("workspace_id must be a positive integer.")

        self.session = session
        self.workspace_id = workspace_id

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    def create_campaign(
        self,
        *,
        name: str,
        message_template: str,
        channel: str = "email",
        description: str | None = None,
        subject: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> Campaign:
        """Create a new draft campaign inside the current workspace."""

        name = name.strip()
        message_template = message_template.strip()
        channel = channel.strip().lower()

        if not name:
            raise ValueError("Campaign name cannot be empty.")

        if not message_template:
            raise ValueError("Message template cannot be empty.")

        if channel not in {"email", "whatsapp"}:
            raise ValueError("Channel must be 'email' or 'whatsapp'.")

        campaign = Campaign(
            workspace_id=self.workspace_id,
            name=name,
            description=description.strip() if description else None,
            channel=channel,
            subject=subject.strip() if subject else None,
            message_template=message_template,
            status="draft",
            scheduled_at=scheduled_at,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        self.session.add(campaign)
        self.session.commit()
        self.session.refresh(campaign)

        return campaign

    def get_campaign(self, campaign_id: int) -> Campaign | None:
        """Return a campaign only if it belongs to this workspace."""

        statement = select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == self.workspace_id,
        )

        return self.session.execute(statement).scalar_one_or_none()

    def list_campaigns(self) -> list[Campaign]:
        """Return all campaigns belonging to this workspace."""

        statement = (
            select(Campaign)
            .where(Campaign.workspace_id == self.workspace_id)
            .order_by(Campaign.created_at.desc())
        )

        return list(self.session.execute(statement).scalars().all())

    def update_campaign_status(
        self,
        campaign_id: int,
        status: str,
    ) -> Campaign:
        """Update a campaign status within the current workspace."""

        campaign = self.get_campaign(campaign_id)

        if campaign is None:
            raise ValueError("Campaign not found in this workspace.")

        allowed_statuses = {
            "draft",
            "scheduled",
            "running",
            "completed",
            "cancelled",
        }

        status = status.strip().lower()

        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid campaign status: {status}. "
                f"Allowed values: {sorted(allowed_statuses)}"
            )

        now = utc_now()

        campaign.status = status
        campaign.updated_at = now

        if status == "running" and campaign.started_at is None:
            campaign.started_at = now

        elif status == "completed":
            if campaign.started_at is None:
                campaign.started_at = now
            campaign.completed_at = now

        elif status == "cancelled":
            campaign.cancelled_at = now

        self.session.commit()
        self.session.refresh(campaign)

        return campaign

    # ------------------------------------------------------------------
    # Recipients
    # ------------------------------------------------------------------

    def add_recipient(
        self,
        campaign_id: int,
        *,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> CampaignRecipient:
        """Add one recipient to a workspace-owned campaign."""

        campaign = self.get_campaign(campaign_id)

        if campaign is None:
            raise ValueError("Campaign not found in this workspace.")

        email = email.strip().lower() if email else None
        phone = phone.strip() if phone else None
        full_name = full_name.strip() if full_name else None

        if campaign.channel == "email" and not email:
            raise ValueError("Email is required for an email campaign.")

        if campaign.channel == "whatsapp" and not phone:
            raise ValueError("Phone is required for a WhatsApp campaign.")

        recipient = CampaignRecipient(
            campaign_id=campaign.id,
            workspace_id=self.workspace_id,
            full_name=full_name,
            email=email,
            phone=phone,
            status="pending",
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        self.session.add(recipient)
        self.session.commit()
        self.session.refresh(recipient)

        return recipient

    def add_recipients(
        self,
        campaign_id: int,
        recipients: Iterable[dict],
    ) -> list[CampaignRecipient]:
        """Add multiple recipients to a workspace-owned campaign."""

        campaign = self.get_campaign(campaign_id)

        if campaign is None:
            raise ValueError("Campaign not found in this workspace.")

        created: list[CampaignRecipient] = []

        for data in recipients:
            recipient = CampaignRecipient(
                campaign_id=campaign.id,
                workspace_id=self.workspace_id,
                full_name=(
                    data.get("full_name", "").strip()
                    if data.get("full_name")
                    else None
                ),
                email=(
                    data.get("email", "").strip().lower()
                    if data.get("email")
                    else None
                ),
                phone=(
                    data.get("phone", "").strip()
                    if data.get("phone")
                    else None
                ),
                status="pending",
                created_at=utc_now(),
                updated_at=utc_now(),
            )

            if campaign.channel == "email" and not recipient.email:
                raise ValueError(
                    "Every recipient in an email campaign must have an email."
                )

            if campaign.channel == "whatsapp" and not recipient.phone:
                raise ValueError(
                    "Every recipient in a WhatsApp campaign must have a phone number."
                )

            self.session.add(recipient)
            created.append(recipient)

        self.session.commit()

        for recipient in created:
            self.session.refresh(recipient)

        return created

    def list_recipients(
        self,
        campaign_id: int,
    ) -> list[CampaignRecipient]:
        """List recipients only for a campaign owned by this workspace."""

        campaign = self.get_campaign(campaign_id)

        if campaign is None:
            raise ValueError("Campaign not found in this workspace.")

        statement = (
            select(CampaignRecipient)
            .where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.workspace_id == self.workspace_id,
            )
            .order_by(CampaignRecipient.created_at.asc())
        )

        return list(self.session.execute(statement).scalars().all())

    # ------------------------------------------------------------------
    # Delivery attempts
    # ------------------------------------------------------------------

    def create_delivery_attempt(
        self,
        campaign_recipient_id: int,
        *,
        provider: str,
        channel: str,
        status: str = "pending",
        provider_message_id: str | None = None,
        error_message: str | None = None,
    ) -> DeliveryAttempt:
        """Create a delivery-attempt record for a workspace-owned recipient."""

        statement = select(CampaignRecipient).where(
            CampaignRecipient.id == campaign_recipient_id,
            CampaignRecipient.workspace_id == self.workspace_id,
        )

        recipient = self.session.execute(statement).scalar_one_or_none()

        if recipient is None:
            raise ValueError("Recipient not found in this workspace.")

        attempt = DeliveryAttempt(
            campaign_recipient_id=recipient.id,
            workspace_id=self.workspace_id,
            provider=provider.strip(),
            channel=channel.strip().lower(),
            status=status.strip().lower(),
            provider_message_id=provider_message_id,
            error_message=error_message,
            attempted_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        self.session.add(attempt)
        self.session.commit()
        self.session.refresh(attempt)

        return attempt

    def list_delivery_attempts(
        self,
        campaign_recipient_id: int,
    ) -> list[DeliveryAttempt]:
        """List delivery attempts for a workspace-owned recipient."""

        recipient_statement = select(CampaignRecipient).where(
            CampaignRecipient.id == campaign_recipient_id,
            CampaignRecipient.workspace_id == self.workspace_id,
        )

        recipient = self.session.execute(
            recipient_statement
        ).scalar_one_or_none()

        if recipient is None:
            raise ValueError("Recipient not found in this workspace.")

        statement = (
            select(DeliveryAttempt)
            .where(
                DeliveryAttempt.campaign_recipient_id == campaign_recipient_id,
                DeliveryAttempt.workspace_id == self.workspace_id,
            )
            .order_by(DeliveryAttempt.created_at.asc())
        )

        return list(self.session.execute(statement).scalars().all())
