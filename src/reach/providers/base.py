from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SendRequest:
    recipient: str
    message: str
    subject: str | None = None
    recipient_name: str | None = None


@dataclass(frozen=True)
class SendResult:
    success: bool
    provider: str
    channel: str
    provider_message_id: str | None = None
    error_message: str | None = None


class MessageProvider(Protocol):
    """Interface implemented by every outbound messaging provider."""

    provider_name: str
    channel: str

    def send(self, request: SendRequest) -> SendResult:
        ...
