from __future__ import annotations

from reach.providers.base import MessageProvider, SendRequest, SendResult


class FakeEmailProvider:
    """Deterministic email provider for local development and tests."""

    provider_name = "fake-email"
    channel = "email"

    def __init__(self) -> None:
        self.sent_messages: list[SendRequest] = []

    def send(self, request: SendRequest) -> SendResult:
        if not request.recipient.strip():
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Recipient email is empty.",
            )

        if "@" not in request.recipient:
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Invalid email address.",
            )

        if not request.message.strip():
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Message is empty.",
            )

        self.sent_messages.append(request)

        message_id = f"fake-email-{len(self.sent_messages):06d}"

        return SendResult(
            success=True,
            provider=self.provider_name,
            channel=self.channel,
            provider_message_id=message_id,
        )


class FakeWhatsAppProvider:
    """Deterministic WhatsApp provider for local development and tests."""

    provider_name = "fake-whatsapp"
    channel = "whatsapp"

    def __init__(self) -> None:
        self.sent_messages: list[SendRequest] = []

    def send(self, request: SendRequest) -> SendResult:
        if not request.recipient.strip():
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Recipient phone number is empty.",
            )

        if not request.message.strip():
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Message is empty.",
            )

        self.sent_messages.append(request)

        message_id = f"fake-whatsapp-{len(self.sent_messages):06d}"

        return SendResult(
            success=True,
            provider=self.provider_name,
            channel=self.channel,
            provider_message_id=message_id,
        )
