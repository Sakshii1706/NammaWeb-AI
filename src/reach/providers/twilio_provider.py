from __future__ import annotations

from reach.providers.base import SendRequest, SendResult
from reach.providers.config import WhatsAppProviderConfig


class TwilioWhatsAppProvider:
    """Twilio WhatsApp provider. The SDK is imported only when sending."""

    provider_name = "twilio-whatsapp"
    channel = "whatsapp"

    def __init__(self, config: WhatsAppProviderConfig) -> None:
        self.config = config

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

        try:
            from twilio.rest import Client

            client = Client(
                self.config.account_sid,
                self.config.auth_token,
            )

            recipient = request.recipient.strip()
            sender = self.config.from_number.strip()

            if not recipient.startswith("whatsapp:"):
                recipient = f"whatsapp:{recipient}"
            if not sender.startswith("whatsapp:"):
                sender = f"whatsapp:{sender}"

            result = client.messages.create(
                body=request.message,
                from_=sender,
                to=recipient,
            )

            return SendResult(
                success=True,
                provider=self.provider_name,
                channel=self.channel,
                provider_message_id=result.sid,
            )
        except ImportError:
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Twilio SDK is not installed. Install the twilio package.",
            )
        except Exception:
            # Avoid leaking account credentials or provider responses.
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Twilio delivery failed. Check credentials and provider logs.",
            )
