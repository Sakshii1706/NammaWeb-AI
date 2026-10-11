from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from reach.campaigns.campaign_execution_service import CampaignExecutionService
from reach.campaigns.campaign_service import CampaignService
from reach.campaigns.compliance_service import ComplianceService
from reach.db.base import Base
from reach.db.campaign_models import CampaignRecipient, DeliveryAttempt
from reach.db.identity_models import Workspace
from reach.providers.base import SendRequest, SendResult
from reach.providers.fake_providers import (
    FakeEmailProvider,
    FakeWhatsAppProvider,
)
from reach.providers.registry import ProviderRegistry


def make_test_session(tmp_path) -> tuple[Session, int]:
    database_path = tmp_path / "campaign_execution.db"

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    session = Session(engine)

    workspace = Workspace(
        name="Campaign Execution Test Workspace",
        slug="campaign-execution-test",
    )

    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    return session, workspace.id


def build_execution_service(
    session: Session,
    workspace_id: int,
    email_provider=None,
    whatsapp_provider=None,
) -> CampaignExecutionService:
    campaign_service = CampaignService(
        session,
        workspace_id,
    )

    compliance_service = ComplianceService(
        session,
        workspace_id,
    )

    email_provider = email_provider or FakeEmailProvider()
    whatsapp_provider = whatsapp_provider or FakeWhatsAppProvider()

    provider_registry = ProviderRegistry()

    provider_registry.register(email_provider)
    provider_registry.register(whatsapp_provider)

    return CampaignExecutionService(
        campaign_service=campaign_service,
        compliance_service=compliance_service,
        provider_registry=provider_registry,
    )


class SelectiveFailureEmailProvider:
    """
    Test provider that succeeds for most recipients but deliberately
    fails for configured email addresses.
    """

    provider_name = "selective-failure-email"
    channel = "email"

    def __init__(self, failing_recipients: set[str] | None = None):
        self.failing_recipients = failing_recipients or set()
        self.sent_messages: list[SendRequest] = []
        self.failed_messages: list[SendRequest] = []

    def send(self, request: SendRequest) -> SendResult:
        if request.recipient in self.failing_recipients:
            self.failed_messages.append(request)

            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Simulated provider failure.",
            )

        self.sent_messages.append(request)

        message_id = (
            f"selective-email-{len(self.sent_messages):06d}"
        )

        return SendResult(
            success=True,
            provider=self.provider_name,
            channel=self.channel,
            provider_message_id=message_id,
        )


def grant_email_consent(
    compliance_service: ComplianceService,
    email: str,
) -> None:
    compliance_service.grant_consent(
        channel="email",
        contact_key=email,
        source="test",
    )


def get_recipients(
    session: Session,
    workspace_id: int,
    campaign_id: int,
) -> list[CampaignRecipient]:
    return session.scalars(
        select(CampaignRecipient)
        .where(
            CampaignRecipient.workspace_id == workspace_id,
            CampaignRecipient.campaign_id == campaign_id,
        )
        .order_by(CampaignRecipient.id)
    ).all()


def get_attempts(
    session: Session,
    workspace_id: int,
) -> list[DeliveryAttempt]:
    return session.scalars(
        select(DeliveryAttempt)
        .where(
            DeliveryAttempt.workspace_id == workspace_id,
        )
        .order_by(DeliveryAttempt.id)
    ).all()


def test_campaign_execution_enforces_compliance(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        campaign_service = CampaignService(
            session,
            workspace_id,
        )

        compliance_service = ComplianceService(
            session,
            workspace_id,
        )

        email_provider = FakeEmailProvider()
        whatsapp_provider = FakeWhatsAppProvider()

        provider_registry = ProviderRegistry()
        provider_registry.register(email_provider)
        provider_registry.register(whatsapp_provider)

        execution_service = CampaignExecutionService(
            campaign_service=campaign_service,
            compliance_service=compliance_service,
            provider_registry=provider_registry,
        )

        campaign = campaign_service.create_campaign(
            name="Compliance Execution Test",
            description="Verify compliance blocks are enforced.",
            channel="email",
            subject="Test Campaign",
            message_template="Hello {{full_name}}!",
        )

        recipients = campaign_service.add_recipients(
            campaign_id=campaign.id,
            recipients=[
                {"full_name": "Alice", "email": "alice@test.com"},
                {"full_name": "Bob", "email": "bob@test.com"},
                {"full_name": "Carol", "email": "carol@test.com"},
                {"full_name": "David", "email": "david@test.com"},
                {"full_name": "Eve", "email": "eve@test.com"},
            ],
        )

        assert len(recipients) == 5

        # Alice + David: valid consent -> allowed.
        grant_email_consent(
            compliance_service,
            "alice@test.com",
        )

        grant_email_consent(
            compliance_service,
            "david@test.com",
        )

        # Carol: consent exists, but suppression blocks delivery.
        grant_email_consent(
            compliance_service,
            "carol@test.com",
        )

        compliance_service.suppress(
            channel="email",
            contact_key="carol@test.com",
            reason="user_requested",
            source="test",
        )

        # Eve: consent was granted and then revoked.
        grant_email_consent(
            compliance_service,
            "eve@test.com",
        )

        compliance_service.revoke_consent(
            channel="email",
            contact_key="eve@test.com",
        )

        # Bob has no consent.

        result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert result.total_recipients == 5
        assert result.sent == 2
        assert result.failed == 0
        assert result.skipped == 3

        sent_addresses = [
            request.recipient
            for request in email_provider.sent_messages
        ]

        assert sent_addresses == [
            "alice@test.com",
            "david@test.com",
        ]

        assert "bob@test.com" not in sent_addresses
        assert "carol@test.com" not in sent_addresses
        assert "eve@test.com" not in sent_addresses

        stored_recipients = get_recipients(
            session,
            workspace_id,
            campaign.id,
        )

        status_by_email = {
            recipient.email: recipient.status
            for recipient in stored_recipients
        }

        assert status_by_email["alice@test.com"] == "sent"
        assert status_by_email["bob@test.com"] == "skipped"
        assert status_by_email["carol@test.com"] == "skipped"
        assert status_by_email["david@test.com"] == "sent"
        assert status_by_email["eve@test.com"] == "skipped"

        attempts = get_attempts(
            session,
            workspace_id,
        )

        sent_attempts = [
            attempt
            for attempt in attempts
            if attempt.status == "sent"
        ]

        skipped_attempts = [
            attempt
            for attempt in attempts
            if attempt.status == "skipped"
        ]

        assert len(sent_attempts) == 2
        assert len(skipped_attempts) == 3

        session.refresh(campaign)

        assert campaign.status == "completed"

    finally:
        session.close()


def test_campaign_execution_is_idempotent_for_sent_recipients(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        email_provider = FakeEmailProvider()

        execution_service = build_execution_service(
            session,
            workspace_id,
            email_provider=email_provider,
        )

        campaign_service = CampaignService(
            session,
            workspace_id,
        )

        compliance_service = ComplianceService(
            session,
            workspace_id,
        )

        campaign = campaign_service.create_campaign(
            name="Idempotency Test",
            message_template="Hello {{full_name}}!",
            channel="email",
        )

        campaign_service.add_recipients(
            campaign_id=campaign.id,
            recipients=[
                {"full_name": "Alice", "email": "alice@test.com"},
                {"full_name": "Bob", "email": "bob@test.com"},
            ],
        )

        grant_email_consent(
            compliance_service,
            "alice@test.com",
        )

        grant_email_consent(
            compliance_service,
            "bob@test.com",
        )

        first_result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert first_result.sent == 2
        assert first_result.failed == 0
        assert first_result.skipped == 0

        assert len(email_provider.sent_messages) == 2

        second_result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        # A second execution must not resend recipients that are already sent.
        assert second_result.total_recipients == 2
        assert second_result.sent == 0
        assert second_result.failed == 0
        assert second_result.skipped == 0

        assert len(email_provider.sent_messages) == 2

    finally:
        session.close()


def test_failed_recipient_can_be_retried(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        email_provider = SelectiveFailureEmailProvider(
            failing_recipients={"bob@test.com"},
        )

        execution_service = build_execution_service(
            session,
            workspace_id,
            email_provider=email_provider,
        )

        campaign_service = CampaignService(
            session,
            workspace_id,
        )

        compliance_service = ComplianceService(
            session,
            workspace_id,
        )

        campaign = campaign_service.create_campaign(
            name="Retry Failed Recipient Test",
            message_template="Hello {{full_name}}!",
            channel="email",
        )

        campaign_service.add_recipients(
            campaign_id=campaign.id,
            recipients=[
                {"full_name": "Alice", "email": "alice@test.com"},
                {"full_name": "Bob", "email": "bob@test.com"},
            ],
        )

        grant_email_consent(
            compliance_service,
            "alice@test.com",
        )

        grant_email_consent(
            compliance_service,
            "bob@test.com",
        )

        first_result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert first_result.sent == 1
        assert first_result.failed == 1
        assert first_result.skipped == 0

        recipients = get_recipients(
            session,
            workspace_id,
            campaign.id,
        )

        status_by_email = {
            recipient.email: recipient.status
            for recipient in recipients
        }

        assert status_by_email["alice@test.com"] == "sent"
        assert status_by_email["bob@test.com"] == "failed"

        # Make Bob succeed on the next attempt.
        email_provider.failing_recipients.remove(
            "bob@test.com"
        )

        second_result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert second_result.sent == 1
        assert second_result.failed == 0
        assert second_result.skipped == 0

        # Alice must not have been sent again.
        sent_addresses = [
            request.recipient
            for request in email_provider.sent_messages
        ]

        assert sent_addresses.count("alice@test.com") == 1
        assert sent_addresses.count("bob@test.com") == 1

        recipients = get_recipients(
            session,
            workspace_id,
            campaign.id,
        )

        status_by_email = {
            recipient.email: recipient.status
            for recipient in recipients
        }

        assert status_by_email["alice@test.com"] == "sent"
        assert status_by_email["bob@test.com"] == "sent"

    finally:
        session.close()


def test_provider_failure_is_persisted_as_delivery_attempt(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        email_provider = SelectiveFailureEmailProvider(
            failing_recipients={"bob@test.com"},
        )

        execution_service = build_execution_service(
            session,
            workspace_id,
            email_provider=email_provider,
        )

        campaign_service = CampaignService(
            session,
            workspace_id,
        )

        compliance_service = ComplianceService(
            session,
            workspace_id,
        )

        campaign = campaign_service.create_campaign(
            name="Provider Failure Test",
            message_template="Hello {{full_name}}!",
            channel="email",
        )

        campaign_service.add_recipients(
            campaign_id=campaign.id,
            recipients=[
                {"full_name": "Bob", "email": "bob@test.com"},
            ],
        )

        grant_email_consent(
            compliance_service,
            "bob@test.com",
        )

        result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert result.total_recipients == 1
        assert result.sent == 0
        assert result.failed == 1
        assert result.skipped == 0

        attempts = get_attempts(
            session,
            workspace_id,
        )

        assert len(attempts) == 1

        attempt = attempts[0]

        assert attempt.provider == "selective-failure-email"
        assert attempt.channel == "email"
        assert attempt.status == "failed"
        assert attempt.provider_message_id is None
        assert attempt.error_message == "Simulated provider failure."

    finally:
        session.close()


def test_delivery_history_preserves_multiple_attempts(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        email_provider = SelectiveFailureEmailProvider(
            failing_recipients={"bob@test.com"},
        )

        execution_service = build_execution_service(
            session,
            workspace_id,
            email_provider=email_provider,
        )

        campaign_service = CampaignService(
            session,
            workspace_id,
        )

        compliance_service = ComplianceService(
            session,
            workspace_id,
        )

        campaign = campaign_service.create_campaign(
            name="Delivery History Test",
            message_template="Hello {{full_name}}!",
            channel="email",
        )

        campaign_service.add_recipient(
            campaign_id=campaign.id,
            full_name="Bob",
            email="bob@test.com",
        )

        grant_email_consent(
            compliance_service,
            "bob@test.com",
        )

        # First attempt fails.
        first_result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert first_result.failed == 1

        attempts_after_failure = get_attempts(
            session,
            workspace_id,
        )

        assert len(attempts_after_failure) == 1
        assert attempts_after_failure[0].status == "failed"

        # Second attempt succeeds.
        email_provider.failing_recipients.remove(
            "bob@test.com"
        )

        second_result = execution_service.execute_campaign(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
        )

        assert second_result.sent == 1

        attempts_after_retry = get_attempts(
            session,
            workspace_id,
        )

        assert len(attempts_after_retry) == 2

        assert attempts_after_retry[0].status == "failed"
        assert attempts_after_retry[1].status == "sent"

        assert attempts_after_retry[1].provider_message_id is not None

    finally:
        session.close()