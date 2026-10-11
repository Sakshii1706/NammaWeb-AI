from __future__ import annotations

import os
import time as time_module
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from reach.campaigns.campaign_execution_service import CampaignExecutionService
from reach.campaigns.campaign_service import CampaignService
from reach.campaigns.compliance_service import ComplianceService
from reach.db import get_session, init_db
from reach.db.campaign_models import Campaign
from reach.providers.fake_providers import FakeEmailProvider, FakeWhatsAppProvider
from reach.providers.registry import ProviderRegistry


@dataclass(frozen=True)
class SchedulerExecution:
    campaign_id: int
    workspace_id: int
    status: str
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    error: str | None = None


class CampaignScheduler:
    """
    Finds due scheduled campaigns and executes them in test mode.

    The scheduler deliberately uses only the built-in fake providers.
    It never sends real email or WhatsApp messages.
    """

    def __init__(self, session=None) -> None:
        self.session = session

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def build_test_provider_registry() -> ProviderRegistry:
        registry = ProviderRegistry()
        registry.register(FakeEmailProvider())
        registry.register(FakeWhatsAppProvider())
        return registry

    def _get_session(self):
        if self.session is not None:
            return self.session, False

        return get_session(), True

    def find_due_campaigns(
        self,
        *,
        now: datetime | None = None,
    ) -> list[Campaign]:
        if now is None:
            now = self.utcnow()

        statement = (
            select(Campaign)
            .where(
                Campaign.status == "scheduled",
                Campaign.scheduled_at.is_not(None),
                Campaign.scheduled_at <= now,
            )
            .order_by(
                Campaign.scheduled_at.asc(),
                Campaign.id.asc(),
            )
        )

        session, owns_session = self._get_session()

        try:
            return list(
                session.execute(statement).scalars().all()
            )
        finally:
            if owns_session:
                session.close()

    def execute_due_campaigns(
        self,
        *,
        now: datetime | None = None,
    ) -> list[SchedulerExecution]:
        if now is None:
            now = self.utcnow()

        session, owns_session = self._get_session()

        try:
            statement = (
                select(Campaign)
                .where(
                    Campaign.status == "scheduled",
                    Campaign.scheduled_at.is_not(None),
                    Campaign.scheduled_at <= now,
                )
                .order_by(
                    Campaign.scheduled_at.asc(),
                    Campaign.id.asc(),
                )
            )

            campaigns = list(
                session.execute(statement).scalars().all()
            )

            results: list[SchedulerExecution] = []

            for campaign in campaigns:
                campaign_id = campaign.id
                workspace_id = campaign.workspace_id

                try:
                    campaign_service = CampaignService(
                        session,
                        workspace_id,
                    )

                    compliance_service = ComplianceService(
                        session,
                        workspace_id,
                    )

                    provider_registry = (
                        self.build_test_provider_registry()
                    )

                    execution_service = CampaignExecutionService(
                        campaign_service,
                        compliance_service,
                        provider_registry,
                    )

                    execution_result = (
                        execution_service.execute_campaign(
                            workspace_id=workspace_id,
                            campaign_id=campaign_id,
                        )
                    )

                    results.append(
                        SchedulerExecution(
                            campaign_id=execution_result.campaign_id,
                            workspace_id=workspace_id,
                            status="completed",
                            sent=execution_result.sent,
                            failed=execution_result.failed,
                            skipped=execution_result.skipped,
                        )
                    )

                except Exception as exc:
                    session.rollback()

                    results.append(
                        SchedulerExecution(
                            campaign_id=campaign_id,
                            workspace_id=workspace_id,
                            status="error",
                            error=str(exc),
                        )
                    )

            return results

        finally:
            if owns_session:
                session.close()


def run_scheduler_once() -> list[SchedulerExecution]:
    """
    Run one scheduler pass.
    """
    init_db()

    scheduler = CampaignScheduler()

    return scheduler.execute_due_campaigns()


def print_scheduler_results(
    results: list[SchedulerExecution],
) -> None:
    if not results:
        print(
            f"[{datetime.now(timezone.utc).isoformat()}] "
            "No due scheduled campaigns."
        )
        return

    for result in results:
        print(
            f"[{datetime.now(timezone.utc).isoformat()}] "
            f"campaign_id={result.campaign_id} "
            f"workspace_id={result.workspace_id} "
            f"status={result.status} "
            f"sent={result.sent} "
            f"skipped={result.skipped} "
            f"failed={result.failed}"
            + (
                f" error={result.error}"
                if result.error
                else ""
            )
        )


def run_scheduler_forever(
    interval_seconds: int = 30,
) -> None:
    """
    Continuously check for due campaigns.

    The default interval is 30 seconds.
    Set NAMMAWEB_SCHEDULER_INTERVAL_SECONDS to override it.
    """

    if interval_seconds < 1:
        raise ValueError(
            "interval_seconds must be at least 1 second."
        )

    init_db()

    print("")
    print("=" * 60)
    print("NAMMAWEB CAMPAIGN SCHEDULER")
    print("=" * 60)
    print("Mode: TEST / FAKE PROVIDERS ONLY")
    print(
        f"Interval: {interval_seconds} second(s)"
    )
    print("Real email/WhatsApp sending: DISABLED")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    print("")

    try:
        while True:
            try:
                results = CampaignScheduler().execute_due_campaigns()
                print_scheduler_results(results)

            except Exception as exc:
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] "
                    f"Scheduler error: {exc}"
                )

            time_module.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("")
        print("Scheduler stopped cleanly.")


def _get_interval_from_environment() -> int:
    raw_value = os.getenv(
        "NAMMAWEB_SCHEDULER_INTERVAL_SECONDS",
        "30",
    )

    try:
        interval = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            "NAMMAWEB_SCHEDULER_INTERVAL_SECONDS must be an integer."
        ) from exc

    if interval < 1:
        raise ValueError(
            "NAMMAWEB_SCHEDULER_INTERVAL_SECONDS must be at least 1."
        )

    return interval


if __name__ == "__main__":
    interval = _get_interval_from_environment()

    run_scheduler_forever(
        interval_seconds=interval,
    )
