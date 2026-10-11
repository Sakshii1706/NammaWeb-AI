from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from reach.db.base import Base


@dataclass(frozen=True)
class MockMessageRecord:
    campaign_id: int
    workspace_id: int
    recipient_id: int
    channel: str
    provider: str
    recipient: str
    recipient_name: str | None
    subject: str | None
    message: str
    status: str
    provider_message_id: str | None
    error_message: str | None
    created_at: datetime


class MockMessageLog(Base):
    """
    Persistent audit log for test-mode campaign messages.

    This table records mock deliveries only.
    It never sends a real email or WhatsApp message.
    """

    __tablename__ = "mock_message_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    campaign_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    recipient_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    recipient_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    subject: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


def append_jsonl_record(
    record: MockMessageRecord,
    *,
    log_directory: Path | None = None,
) -> Path:
    """
    Append a mock message record to a JSONL audit file.

    JSONL is useful for debugging and inspecting exactly what the
    mock provider would have sent.
    """

    if log_directory is None:
        log_directory = Path("data") / "mock_messages"

    log_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_path = log_directory / "mock_messages.jsonl"

    payload = {
        "campaign_id": record.campaign_id,
        "workspace_id": record.workspace_id,
        "recipient_id": record.recipient_id,
        "channel": record.channel,
        "provider": record.provider,
        "recipient": record.recipient,
        "recipient_name": record.recipient_name,
        "subject": record.subject,
        "message": record.message,
        "status": record.status,
        "provider_message_id": record.provider_message_id,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat(),
    }

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                payload,
                ensure_ascii=False,
            )
            + "\n"
        )

    return log_path
