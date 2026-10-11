from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from reach.db.base import Base
from reach.db.identity_models import Workspace
from reach.db.identity_models import User
from reach.db.campaign_models import Campaign, CampaignRecipient, DeliveryAttempt
from reach.db.mock_message_models import MockMessageLog
from reach.campaigns.campaign_service import CampaignService
from reach.campaigns.compliance_service import ComplianceService
from reach.campaigns.campaign_execution_service import CampaignExecutionService
from reach.providers.fake_providers import FakeEmailProvider
from reach.providers.base import SendRequest, SendResult
from reach.providers.registry import ProviderRegistry


def build_test_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return SessionLocal()


def build_execution_service(
    session,
    workspace_id,
    *,
    provider=None,
):

    campaign_service = CampaignService(session, workspace_id)
    compliance_service = ComplianceService(session, workspace_id)

    registry = ProviderRegistry()
    fake_email = provider or FakeEmailProvider()
    registry.register(fake_email)

    execution_service = CampaignExecutionService(
        campaign_service,
        compliance_service,
        registry,
    )

    return campaign_service, compliance_service, execution_service, fake_email


def create_workspace(session):
    workspace = Workspace(
        name="Mock Logging Test Workspace",
        slug="mock-logging-test",
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace


def create_campaign_with_recipient(
    session,
    workspace_id,
    *,
    email="test@example.com",
    name="Test User",
):
    campaign_service = CampaignService(session, workspace_id)

    campaign = campaign_service.create_campaign(
        name="Mock Logging Campaign",
        message_template="Hello {name}, this is a test message.",
        channel="email",
        subject="Test Subject",
    )

    recipient = campaign_service.add_recipient(
        campaign_id=campaign.id,
        full_name=name,
        email=email,
    )

    return campaign, recipient


def grant_consent(session, workspace_id, email):
    compliance_service = ComplianceService(session, workspace_id)
    compliance_service.grant_consent(
        channel="email",
        contact_key=email,
    )


class SelectiveFailureEmailProvider:
    provider_name = "selective-failure-email"
    channel = "email"

    def __init__(self, failing_recipients=None):
        self.failing_recipients = failing_recipients or set()
        self.sent_messages = []
        self.failed_messages = []

    def send(self, request):
        if request.recipient in self.failing_recipients:
            self.failed_messages.append(request)
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Simulated provider failure.",
            )

        self.sent_messages.append(request)
        return SendResult(
            success=True,
            provider=self.provider_name,
            channel=self.channel,
            provider_message_id="test-provider-message-id",
        )


def test_successful_send_creates_mock_log():
    session = build_test_session()

    try:
        workspace = create_workspace(session)

        campaign, recipient = create_campaign_with_recipient(
            session,
            workspace.id,
        )

        grant_consent(
            session,
            workspace.id,
            recipient.email,
        )

        (
            campaign_service,
            compliance_service,
            execution_service,
            fake_email,
        ) = build_execution_service(
            session,
            workspace.id,
        )

        result = execution_service.execute_campaign(
            workspace_id=workspace.id,
            campaign_id=campaign.id,
        )

        assert result.sent == 1
        assert result.failed == 0
        assert result.skipped == 0

        logs = list(
            session.execute(
                select(MockMessageLog)
                .where(MockMessageLog.workspace_id == workspace.id)
            ).scalars()
        )

        assert len(logs) == 1

        log = logs[0]

        assert log.campaign_id == campaign.id
        assert log.workspace_id == workspace.id
        assert log.recipient_id == recipient.id
        assert log.channel == "email"
        assert log.provider == "fake-email"
        assert log.recipient == "test@example.com"
        assert log.recipient_name == "Test User"
        assert log.subject == "Test Subject"
        assert log.message == "Hello {name}, this is a test message."
        assert log.status == "sent"
        assert log.provider_message_id is not None
        assert log.error_message is None

    finally:
        session.close()


def test_failed_send_creates_failed_mock_log():
    session = build_test_session()

    try:
        workspace = create_workspace(session)

        campaign, recipient = create_campaign_with_recipient(
            session,
            workspace.id,
        )

        grant_consent(
            session,
            workspace.id,
            recipient.email,
        )

        (
            campaign_service,
            compliance_service,
            execution_service,
            fake_email,
        ) = build_execution_service(
            session,
            workspace.id,
        )

        failing_provider = SelectiveFailureEmailProvider(
            failing_recipients={recipient.email},
        )

        (
            campaign_service,
            compliance_service,
            execution_service,
            fake_email,
        ) = build_execution_service(
            session,
            workspace.id,
            provider=failing_provider,
        )

        result = execution_service.execute_campaign(
            workspace_id=workspace.id,
            campaign_id=campaign.id,
        )

        assert result.sent == 0
        assert result.failed == 1
        assert result.skipped == 0

        logs = list(
            session.execute(
                select(MockMessageLog)
                .where(MockMessageLog.workspace_id == workspace.id)
            ).scalars()
        )

        assert len(logs) == 1

        log = logs[0]

        assert log.status == "failed"
        assert log.provider == "selective-failure-email"
        assert log.recipient == "test@example.com"
        assert log.provider_message_id is None
        assert log.error_message is not None

    finally:
        session.close()


def test_missing_consent_creates_skipped_mock_log():
    session = build_test_session()

    try:
        workspace = create_workspace(session)

        campaign, recipient = create_campaign_with_recipient(
            session,
            workspace.id,
        )

        (
            campaign_service,
            compliance_service,
            execution_service,
            fake_email,
        ) = build_execution_service(
            session,
            workspace.id,
        )

        result = execution_service.execute_campaign(
            workspace_id=workspace.id,
            campaign_id=campaign.id,
        )

        assert result.sent == 0
        assert result.failed == 0
        assert result.skipped == 1

        logs = list(
            session.execute(
                select(MockMessageLog)
                .where(MockMessageLog.workspace_id == workspace.id)
            ).scalars()
        )

        assert len(logs) == 1

        log = logs[0]

        assert log.status == "skipped"
        assert log.provider == "fake-email"
        assert log.recipient == "test@example.com"
        assert log.message == "Hello {name}, this is a test message."
        assert log.provider_message_id is None
        assert log.error_message is not None
        assert "consent" in log.error_message.lower()

    finally:
        session.close()


def test_mock_logs_are_workspace_isolated():
    session = build_test_session()

    try:
        workspace_one = create_workspace(session)

        workspace_two = Workspace(
            name="Second Workspace",
            slug="second-workspace",
        )
        session.add(workspace_two)
        session.commit()
        session.refresh(workspace_two)

        campaign, recipient = create_campaign_with_recipient(
            session,
            workspace_one.id,
        )

        grant_consent(
            session,
            workspace_one.id,
            recipient.email,
        )

        (
            campaign_service,
            compliance_service,
            execution_service,
            fake_email,
        ) = build_execution_service(
            session,
            workspace_one.id,
        )

        execution_service.execute_campaign(
            workspace_id=workspace_one.id,
            campaign_id=campaign.id,
        )

        workspace_one_logs = list(
            session.execute(
                select(MockMessageLog)
                .where(MockMessageLog.workspace_id == workspace_one.id)
            ).scalars()
        )

        workspace_two_logs = list(
            session.execute(
                select(MockMessageLog)
                .where(MockMessageLog.workspace_id == workspace_two.id)
            ).scalars()
        )

        assert len(workspace_one_logs) == 1
        assert len(workspace_two_logs) == 0

    finally:
        session.close()
