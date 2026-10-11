from __future__ import annotations

from reach.campaigns.campaign_service import CampaignService
from reach.db.campaign_models import CampaignRecipient, DeliveryAttempt
from reach.db.identity_models import Workspace
from reach.db.session import get_session


def get_or_create_test_workspace(
    session,
    *,
    name: str,
    slug: str,
) -> Workspace:
    workspace = (
        session.query(Workspace)
        .filter(Workspace.slug == slug)
        .first()
    )

    if workspace:
        return workspace

    workspace = Workspace(
        name=name,
        slug=slug,
    )

    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    return workspace


def main() -> None:
    session = get_session()

    try:
        # --------------------------------------------------------------
        # Create two isolated workspaces
        # --------------------------------------------------------------

        workspace_a = get_or_create_test_workspace(
            session,
            name="Campaign Test Workspace A",
            slug="campaign-test-a",
        )

        workspace_b = get_or_create_test_workspace(
            session,
            name="Campaign Test Workspace B",
            slug="campaign-test-b",
        )

        # --------------------------------------------------------------
        # Clean previous test data
        # --------------------------------------------------------------

        session.query(DeliveryAttempt).filter(
            DeliveryAttempt.workspace_id.in_(
                [workspace_a.id, workspace_b.id]
            )
        ).delete(synchronize_session=False)

        session.query(CampaignRecipient).filter(
            CampaignRecipient.workspace_id.in_(
                [workspace_a.id, workspace_b.id]
            )
        ).delete(synchronize_session=False)

        from reach.db.campaign_models import Campaign

        session.query(Campaign).filter(
            Campaign.workspace_id.in_(
                [workspace_a.id, workspace_b.id]
            )
        ).delete(synchronize_session=False)

        session.commit()

        # --------------------------------------------------------------
        # Test Workspace A
        # --------------------------------------------------------------

        service_a = CampaignService(
            session,
            workspace_a.id,
        )

        campaign = service_a.create_campaign(
            name="AI Outreach Test",
            description="Campaign service integration test",
            channel="email",
            subject="Hello from NammaWeb",
            message_template="Hello {{full_name}}, this is a test message.",
        )

        assert campaign.id is not None
        assert campaign.workspace_id == workspace_a.id
        assert campaign.status == "draft"

        print("CREATE CAMPAIGN: PASS")

        # --------------------------------------------------------------
        # Add recipients
        # --------------------------------------------------------------

        recipient_1 = service_a.add_recipient(
            campaign.id,
            full_name="Alice",
            email="ALICE@EXAMPLE.COM",
        )

        assert recipient_1.id is not None
        assert recipient_1.workspace_id == workspace_a.id
        assert recipient_1.email == "alice@example.com"
        assert recipient_1.status == "pending"

        print("ADD SINGLE RECIPIENT: PASS")

        recipients = service_a.add_recipients(
            campaign.id,
            [
                {
                    "full_name": "Bob",
                    "email": "bob@example.com",
                },
                {
                    "full_name": "Charlie",
                    "email": "charlie@example.com",
                },
            ],
        )

        assert len(recipients) == 2

        all_recipients = service_a.list_recipients(campaign.id)

        assert len(all_recipients) == 3

        print("ADD BULK RECIPIENTS: PASS")

        # --------------------------------------------------------------
        # Campaign listing
        # --------------------------------------------------------------

        campaigns_a = service_a.list_campaigns()

        assert len(campaigns_a) == 1
        assert campaigns_a[0].id == campaign.id

        print("LIST CAMPAIGNS: PASS")

        # --------------------------------------------------------------
        # Status lifecycle
        # --------------------------------------------------------------

        updated = service_a.update_campaign_status(
            campaign.id,
            "scheduled",
        )

        assert updated.status == "scheduled"

        updated = service_a.update_campaign_status(
            campaign.id,
            "running",
        )

        assert updated.status == "running"
        assert updated.started_at is not None

        updated = service_a.update_campaign_status(
            campaign.id,
            "completed",
        )

        assert updated.status == "completed"
        assert updated.completed_at is not None

        print("CAMPAIGN STATUS LIFECYCLE: PASS")

        # --------------------------------------------------------------
        # Delivery attempt
        # --------------------------------------------------------------

        attempt = service_a.create_delivery_attempt(
            recipient_1.id,
            provider="fake",
            channel="email",
            status="sent",
            provider_message_id="fake-msg-001",
        )

        assert attempt.id is not None
        assert attempt.workspace_id == workspace_a.id
        assert attempt.status == "sent"

        attempts = service_a.list_delivery_attempts(
            recipient_1.id
        )

        assert len(attempts) == 1
        assert attempts[0].provider_message_id == "fake-msg-001"

        print("DELIVERY ATTEMPT: PASS")

        # --------------------------------------------------------------
        # CRITICAL: workspace isolation
        # --------------------------------------------------------------

        service_b = CampaignService(
            session,
            workspace_b.id,
        )

        hidden_campaign = service_b.get_campaign(
            campaign.id
        )

        assert hidden_campaign is None

        print("CROSS-WORKSPACE CAMPAIGN ISOLATION: PASS")

        assert service_b.list_campaigns() == []

        print("CROSS-WORKSPACE LIST ISOLATION: PASS")

        try:
            service_b.add_recipient(
                campaign.id,
                full_name="Should Fail",
                email="should-not-work@example.com",
            )
        except ValueError as exc:
            assert "not found in this workspace" in str(exc).lower()
            print("CROSS-WORKSPACE WRITE BLOCK: PASS")
        else:
            raise AssertionError(
                "Cross-workspace recipient insertion was not blocked."
            )

        # --------------------------------------------------------------
        # Final verification
        # --------------------------------------------------------------

        workspace_a_campaigns = (
            session.query(Campaign)
            .filter(Campaign.workspace_id == workspace_a.id)
            .count()
        )

        workspace_b_campaigns = (
            session.query(Campaign)
            .filter(Campaign.workspace_id == workspace_b.id)
            .count()
        )

        assert workspace_a_campaigns == 1
        assert workspace_b_campaigns == 0

        print("FINAL WORKSPACE COUNTS: PASS")
        print(
            f"WORKSPACE A CAMPAIGNS: {workspace_a_campaigns}"
        )
        print(
            f"WORKSPACE B CAMPAIGNS: {workspace_b_campaigns}"
        )

        print("")
        print("========================================")
        print("CAMPAIGN SERVICE TESTS: ALL PASS")
        print("========================================")

    finally:
        session.close()


if __name__ == "__main__":
    main()
