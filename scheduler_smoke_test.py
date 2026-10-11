from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from reach.campaigns.campaign_scheduler import CampaignScheduler
from reach.campaigns.campaign_service import CampaignService
from reach.campaigns.compliance_service import ComplianceService
from reach.db.base import Base
from reach.db import identity_models  # noqa: F401
from reach.db import models  # noqa: F401
from reach.db import campaign_models  # noqa: F401
from reach.db import compliance_models  # noqa: F401


def build_test_session():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    return Session()


def create_scheduled_campaign(
    session,
    *,
    workspace_id: int,
    scheduled_at: datetime,
    email: str = "scheduler@example.com",
):
    campaign_service = CampaignService(
        session,
        workspace_id,
    )

    campaign = campaign_service.create_campaign(
        name="Scheduler Test",
        message_template="Hello {{full_name}}",
        channel="email",
        subject="Scheduler test",
        scheduled_at=scheduled_at,
    )

    campaign_service.add_recipient(
        campaign.id,
        full_name="Scheduler User",
        email=email,
    )

    campaign_service.update_campaign_status(
        campaign.id,
        "scheduled",
    )

    compliance = ComplianceService(
        session,
        workspace_id,
    )

    compliance.grant_consent(
        channel="email",
        contact_key=email,
        source="scheduler test",
    )

    return campaign


def test_future_campaign_is_not_due():
    session = build_test_session()

    try:
        now = datetime.now(timezone.utc)

        campaign = create_scheduled_campaign(
            session,
            workspace_id=1,
            scheduled_at=now + timedelta(hours=1),
        )

        scheduler = CampaignScheduler(session)

        due = scheduler.find_due_campaigns(now=now)

        assert due == []
        assert campaign.status == "scheduled"

        print("PASS: future campaign is not due")

    finally:
        session.close()


def test_due_campaign_executes():
    session = build_test_session()

    try:
        now = datetime.now(timezone.utc)

        campaign = create_scheduled_campaign(
            session,
            workspace_id=1,
            scheduled_at=now - timedelta(minutes=1),
        )

        scheduler = CampaignScheduler(session)

        results = scheduler.execute_due_campaigns(now=now)

        assert len(results) == 1

        result = results[0]

        assert result.campaign_id == campaign.id
        assert result.workspace_id == 1
        assert result.status == "completed"
        assert result.sent == 1
        assert result.skipped == 0
        assert result.failed == 0

        session.refresh(campaign)

        assert campaign.status == "completed"

        recipients = CampaignService(
            session,
            1,
        ).list_recipients(campaign.id)

        assert len(recipients) == 1
        assert recipients[0].status == "sent"

        print("PASS: due campaign executes")

    finally:
        session.close()


def test_cancelled_campaign_is_not_executed():
    session = build_test_session()

    try:
        now = datetime.now(timezone.utc)

        campaign = create_scheduled_campaign(
            session,
            workspace_id=1,
            scheduled_at=now - timedelta(minutes=1),
        )

        campaign_service = CampaignService(
            session,
            1,
        )

        campaign_service.update_campaign_status(
            campaign.id,
            "cancelled",
        )

        scheduler = CampaignScheduler(session)

        results = scheduler.execute_due_campaigns(now=now)

        assert results == []

        session.refresh(campaign)

        assert campaign.status == "cancelled"

        print("PASS: cancelled campaign is not executed")

    finally:
        session.close()


def test_workspace_isolation_is_preserved():
    session = build_test_session()

    try:
        now = datetime.now(timezone.utc)

        campaign_one = create_scheduled_campaign(
            session,
            workspace_id=1,
            scheduled_at=now - timedelta(minutes=1),
            email="workspace1@example.com",
        )

        campaign_two = create_scheduled_campaign(
            session,
            workspace_id=2,
            scheduled_at=now - timedelta(minutes=1),
            email="workspace2@example.com",
        )

        scheduler = CampaignScheduler(session)

        results = scheduler.execute_due_campaigns(now=now)

        assert len(results) == 2

        result_workspace_ids = {
            result.workspace_id
            for result in results
        }

        assert result_workspace_ids == {1, 2}

        service_one = CampaignService(
            session,
            1,
        )

        service_two = CampaignService(
            session,
            2,
        )

        recipients_one = service_one.list_recipients(
            campaign_one.id
        )

        recipients_two = service_two.list_recipients(
            campaign_two.id
        )

        assert recipients_one[0].status == "sent"
        assert recipients_two[0].status == "sent"

        print("PASS: workspace isolation is preserved")

    finally:
        session.close()


def test_missing_consent_is_skipped():
    session = build_test_session()

    try:
        now = datetime.now(timezone.utc)

        campaign_service = CampaignService(
            session,
            1,
        )

        campaign = campaign_service.create_campaign(
            name="Blocked Scheduler Test",
            message_template="Hello {{full_name}}",
            channel="email",
            subject="Blocked",
            scheduled_at=now - timedelta(minutes=1),
        )

        campaign_service.add_recipient(
            campaign.id,
            full_name="Blocked User",
            email="blocked@example.com",
        )

        campaign_service.update_campaign_status(
            campaign.id,
            "scheduled",
        )

        scheduler = CampaignScheduler(session)

        results = scheduler.execute_due_campaigns(now=now)

        assert len(results) == 1

        result = results[0]

        assert result.status == "completed"
        assert result.sent == 0
        assert result.skipped == 1
        assert result.failed == 0

        recipients = campaign_service.list_recipients(
            campaign.id
        )

        assert recipients[0].status == "skipped"

        attempts = campaign_service.list_delivery_attempts(
            recipients[0].id
        )

        assert len(attempts) == 1
        assert attempts[0].status == "skipped"
        assert attempts[0].error_message == "no_valid_consent"

        print("PASS: missing consent is skipped")

    finally:
        session.close()


if __name__ == "__main__":
    print("========== SCHEDULER TESTS ==========")

    test_future_campaign_is_not_due()
    test_due_campaign_executes()
    test_cancelled_campaign_is_not_executed()
    test_workspace_isolation_is_preserved()
    test_missing_consent_is_skipped()

    print()
    print("SCHEDULER TESTS: PASS")
