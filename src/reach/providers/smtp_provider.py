from __future__ import annotations

from email.message import EmailMessage
from email.utils import formataddr
import smtplib
import ssl

from reach.providers.base import SendRequest, SendResult
from reach.providers.config import EmailProviderConfig


class SMTPEmailProvider:
    """SMTP email provider. Connections are opened only when send() is called."""

    provider_name = "smtp-email"
    channel = "email"

    def __init__(self, config: EmailProviderConfig) -> None:
        self.config = config

    def send(self, request: SendRequest) -> SendResult:
        if not request.recipient.strip():
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Recipient email is empty.",
            )

        if not request.message.strip():
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="Message is empty.",
            )

        message = EmailMessage()
        message["Subject"] = request.subject or "Message from NammaWeb"
        message["From"] = (
            formataddr((self.config.from_name, self.config.from_email))
            if self.config.from_name
            else self.config.from_email
        )
        message["To"] = request.recipient
        message.set_content(request.message)

        try:
            if self.config.use_tls and self.config.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=20,
                    context=ssl.create_default_context(),
                ) as server:
                    self._authenticate(server)
                    refused = server.send_message(message)
            else:
                with smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=20,
                ) as server:
                    if self.config.use_tls:
                        server.starttls(context=ssl.create_default_context())
                    self._authenticate(server)
                    refused = server.send_message(message)

            if request.recipient in refused:
                return SendResult(
                    success=False,
                    provider=self.provider_name,
                    channel=self.channel,
                    error_message="SMTP server refused the recipient.",
                )

            return SendResult(
                success=True,
                provider=self.provider_name,
                channel=self.channel,
                provider_message_id=message.get("Message-ID"),
            )
        except Exception:
            # Do not expose SMTP credentials or server details to callers.
            return SendResult(
                success=False,
                provider=self.provider_name,
                channel=self.channel,
                error_message="SMTP delivery failed. Check server settings and logs.",
            )

    def _authenticate(self, server) -> None:
        if self.config.smtp_username:
            server.login(
                self.config.smtp_username,
                self.config.smtp_password,
            )
