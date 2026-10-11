from __future__ import annotations

from reach.providers.config import ProviderConfig
from reach.providers.fake_providers import (
    FakeEmailProvider,
    FakeWhatsAppProvider,
)
from reach.providers.registry import ProviderRegistry
from reach.providers.smtp_provider import SMTPEmailProvider
from reach.providers.twilio_provider import TwilioWhatsAppProvider


def build_provider_registry(
    config: ProviderConfig | None = None,
) -> ProviderRegistry:
    """Build a registry from configuration; fake providers are the defaults."""

    config = config or ProviderConfig.from_environment()
    registry = ProviderRegistry()

    email_name = config.email.provider.strip().lower()
    if email_name == "fake":
        email_provider = FakeEmailProvider()
    elif email_name == "smtp":
        if not config.email.smtp_host or not config.email.smtp_host.strip():
            raise ValueError("SMTP requires NAMMAWEB_SMTP_HOST.")
        if not config.email.from_email or not config.email.from_email.strip():
            raise ValueError("SMTP requires NAMMAWEB_FROM_EMAIL.")
        if bool(config.email.smtp_username) != bool(config.email.smtp_password):
            raise ValueError(
                "SMTP username and password must either both be set or both be omitted."
            )
        email_provider = SMTPEmailProvider(config.email)
    else:
        raise ValueError(
            f"Unsupported email provider '{email_name}'. Use 'fake' or 'smtp'."
        )

    whatsapp_name = config.whatsapp.provider.strip().lower()
    if whatsapp_name == "fake":
        whatsapp_provider = FakeWhatsAppProvider()
    elif whatsapp_name == "twilio":
        if not config.whatsapp.account_sid:
            raise ValueError("Twilio requires NAMMAWEB_TWILIO_ACCOUNT_SID.")
        if not config.whatsapp.auth_token:
            raise ValueError("Twilio requires NAMMAWEB_TWILIO_AUTH_TOKEN.")
        if not config.whatsapp.from_number:
            raise ValueError("Twilio requires NAMMAWEB_TWILIO_FROM_NUMBER.")
        whatsapp_provider = TwilioWhatsAppProvider(config.whatsapp)
    else:
        raise ValueError(
            f"Unsupported WhatsApp provider '{whatsapp_name}'. "
            "Use 'fake' or 'twilio'."
        )

    registry.register(email_provider)
    registry.register(whatsapp_provider)
    return registry
