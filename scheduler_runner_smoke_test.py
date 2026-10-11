from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from reach.campaigns.campaign_scheduler import CampaignScheduler
from reach.campaigns.campaign_service import CampaignService
from reach.db.base import Base


def make_test_session():
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
    grant_consent: bool,
):
    campaigns = CampaignService(
        session,
        workspace_id,
    )

    campaign = campaigns.create_campaign(
        name=f"Scheduler test {workspace_id}",
        message_template="Hello {{full_name}}",
        channel="email",
        subject="Scheduler test",
        scheduled_at=scheduled_at,
    )

    recipient = campaigns.add_recipient(
        campaign.id,
        full_name="Test User",
        email=f"test{workspace_id}@example.com",
    )

    if grant_consent:
        from reach.campaigns.compliance_service import ComplianceService

        compliance = ComplianceService(
            session,
            workspace_id,
        )

        compliance.grant_consent(
            channel="email",
            contact_key=recipient.email,
            source="scheduler test",
        )

    campaigns.update_campaign_status(
        campaign.id,
        "scheduled",
    )

    session.commit()

    return campaign, recipient


def main():
    print("")
    print("=" * 60)
    print("SCHEDULER RUNNER TESTS")
    print("=" * 60)

    session = make_test_session()

    now = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # Test 1: Future campaign must not execute
    # ---------------------------------------------------------
    future_campaign, _ = create_scheduled_campaign(
        session,
        workspace_id=1,
        scheduled_at=now + timedelta(minutes=10),
        grant_consent=True,
    )

    scheduler = CampaignScheduler(session)

    results = scheduler.execute_due_campaigns(
        now=now,
    )

    assert not any(
        result.campaign_id == future_campaign.id
        for result in results
    )

    print("PASS: future campaign is not executed")

    # ---------------------------------------------------------
    # Test 2: Due campaign executes
    # ---------------------------------------------------------
    due_campaign, due_recipient = create_scheduled_campaign(
        session,
        workspace_id=2,
        scheduled_at=now - timedelta(minutes=1),
        grant_consent=True,
    )

    results = scheduler.execute_due_campaigns(
        now=now,
    )

    due_results = [
        result
        for result in results
        if result.campaign_id == due_campaign.id
    ]

    assert len(due_results) == 1
    assert due_results[0].status == "completed"
    assert due_results[0].sent == 1

    session.refresh(due_recipient)

    assert due_recipient.status == "sent"

    print("PASS: due campaign executes")

    # ---------------------------------------------------------
    # Test 3: Missing consent is skipped
    # ---------------------------------------------------------
    blocked_campaign, blocked_recipient = create_scheduled_campaign(
        session,
        workspace_id=3,
        scheduled_at=now - timedelta(minutes=1),
        grant_consent=False,
    )

    results = scheduler.execute_due_campaigns(
        now=now,
    )

    blocked_results = [
        result
        for result in results
        if result.campaign_id == blocked_campaign.id
    ]

    assert len(blocked_results) == 1
    assert blocked_results[0].status == "completed"
    assert blocked_results[0].sent == 0
    assert blocked_results[0].skipped == 1

    session.refresh(blocked_recipient)

    assert blocked_recipient.status == "skipped"

    print("PASS: missing consent is skipped")

    # ---------------------------------------------------------
    # Test 4: Cancelled campaign is ignored
    # ---------------------------------------------------------
    cancelled_campaign, _ = create_scheduled_campaign(
        session,
        workspace_id=4,
        scheduled_at=now - timedelta(minutes=1),
        grant_consent=True,
    )

    campaigns = CampaignService(
        session,
        4,
    )

    campaigns.update_campaign_status(
        cancelled_campaign.id,
        "cancelled",
    )

    session.commit()

    results = scheduler.execute_due_campaigns(
        now=now,
    )

    assert not any(
        result.campaign_id == cancelled_campaign.id
        for result in results
    )

    print("PASS: cancelled campaign is ignored")

    # ---------------------------------------------------------
    # Test 5: Workspace isolation
    # ---------------------------------------------------------
    workspace_10_campaign, _ = create_scheduled_campaign(
        session,
        workspace_id=10,
        scheduled_at=now - timedelta(minutes=1),
        grant_consent=True,
    )

    workspace_11_campaign, _ = create_scheduled_campaign(
        session,
        workspace_id=11,
        scheduled_at=now + timedelta(minutes=10),
        grant_consent=True,
    )

    results = scheduler.execute_due_campaigns(
        now=now,
    )

    assert any(
        result.campaign_id == workspace_10_campaign.id
        for result in results
    )

    assert not any(
        result.campaign_id == workspace_11_campaign.id
        for result in results
    )

    print("PASS: workspace isolation is preserved")

    session.close()

    print("")
    print("SCHEDULER RUNNER TESTS: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
