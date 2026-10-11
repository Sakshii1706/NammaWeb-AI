from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from reach.db.mock_message_models import (
    MockMessageLog,
    MockMessageRecord,
    append_jsonl_record,
)


class MockMessageLogger:
    """
    Persistent logger for test-mode campaign messages.

    This logger records what the fake provider would have sent.
    It never sends a real email or WhatsApp message.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        campaign_id: int,
        workspace_id: int,
        recipient_id: int,
        channel: str,
        provider: str,
        recipient: str,
        recipient_name: str | None,
        subject: str | None,
        message: str,
        status: str,
        provider_message_id: str | None = None,
        error_message: str | None = None,
    ) -> MockMessageLog:
        created_at = datetime.now(timezone.utc)

        row = MockMessageLog(
            campaign_id=campaign_id,
            workspace_id=workspace_id,
            recipient_id=recipient_id,
            channel=channel,
            provider=provider,
            recipient=recipient,
            recipient_name=recipient_name,
            subject=subject,
            message=message,
            status=status,
            provider_message_id=provider_message_id,
            error_message=error_message,
            created_at=created_at,
        )

        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)

        record = MockMessageRecord(
            campaign_id=campaign_id,
            workspace_id=workspace_id,
            recipient_id=recipient_id,
            channel=channel,
            provider=provider,
            recipient=recipient,
            recipient_name=recipient_name,
            subject=subject,
            message=message,
            status=status,
            provider_message_id=provider_message_id,
            error_message=error_message,
            created_at=created_at,
        )

        try:
            append_jsonl_record(record)
        except OSError:
            # SQLite remains the authoritative audit log.
            # A JSONL filesystem failure must not break campaign execution.
            pass

        return row

    def list_for_workspace(
        self,
        workspace_id: int,
        *,
        campaign_id: int | None = None,
        limit: int = 100,
    ) -> list[MockMessageLog]:
        statement = (
            select(MockMessageLog)
            .where(MockMessageLog.workspace_id == workspace_id)
            .order_by(
                MockMessageLog.created_at.desc(),
                MockMessageLog.id.desc(),
            )
            .limit(limit)
        )

        if campaign_id is not None:
            statement = statement.where(
                MockMessageLog.campaign_id == campaign_id
            )

        return list(
            self.session.execute(statement).scalars().all()
        )
