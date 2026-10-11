from __future__ import annotations

import pytest

from reach.providers.config import (
    EmailProviderConfig,
    ProviderConfig,
    WhatsAppProviderConfig,
)
from reach.providers.factory import build_provider_registry
from reach.providers.fake_providers import (
    FakeEmailProvider,
    FakeWhatsAppProvider,
)
from reach.providers.smtp_provider import SMTPEmailProvider
from reach.providers.twilio_provider import TwilioWhatsAppProvider


def make_config(email=None, whatsapp=None):
    return ProviderConfig(
        email=email or EmailProviderConfig(),
        whatsapp=whatsapp or WhatsAppProviderConfig(),
    )


def test_factory_uses_fake_providers_by_default():
    registry = build_provider_registry(make_config())

    assert isinstance(registry.get("email"), FakeEmailProvider)
    assert isinstance(registry.get("whatsapp"), FakeWhatsAppProvider)
    assert registry.channels() == ("email", "whatsapp")


def test_factory_selects_smtp_provider():
    email = EmailProviderConfig(
        provider="smtp",
        smtp_host="smtp.example.com",
        smtp_port=587,
        from_email="sender@example.com",
    )

    registry = build_provider_registry(make_config(email=email))

    assert isinstance(registry.get("email"), SMTPEmailProvider)
    assert registry.get("email").provider_name == "smtp-email"


def test_factory_rejects_smtp_without_host():
    email = EmailProviderConfig(
        provider="smtp",
        from_email="sender@example.com",
    )

    with pytest.raises(ValueError, match="NAMMAWEB_SMTP_HOST"):
        build_provider_registry(make_config(email=email))


def test_factory_rejects_smtp_without_sender():
    email = EmailProviderConfig(
        provider="smtp",
        smtp_host="smtp.example.com",
    )

    with pytest.raises(ValueError, match="NAMMAWEB_FROM_EMAIL"):
        build_provider_registry(make_config(email=email))


def test_factory_requires_smtp_username_and_password_together():
    email = EmailProviderConfig(
        provider="smtp",
        smtp_host="smtp.example.com",
        from_email="sender@example.com",
        smtp_username="test-user",
    )

    with pytest.raises(ValueError, match="username and password"):
        build_provider_registry(make_config(email=email))


def test_factory_selects_twilio_without_importing_sdk():
    whatsapp = WhatsAppProviderConfig(
        provider="twilio",
        account_sid="test-sid",
        auth_token="test-token",
        from_number="whatsapp:+14155238886",
    )

    registry = build_provider_registry(make_config(whatsapp=whatsapp))

    assert isinstance(registry.get("whatsapp"), TwilioWhatsAppProvider)
    assert registry.get("whatsapp").provider_name == "twilio-whatsapp"


def test_factory_rejects_incomplete_twilio_config():
    whatsapp = WhatsAppProviderConfig(
        provider="twilio",
        account_sid="test-sid",
        auth_token="test-token",
    )

    with pytest.raises(ValueError, match="NAMMAWEB_TWILIO_FROM_NUMBER"):
        build_provider_registry(make_config(whatsapp=whatsapp))


def test_factory_rejects_unknown_email_provider():
    email = EmailProviderConfig(provider="sendgrid")

    with pytest.raises(ValueError, match="Unsupported email provider"):
        build_provider_registry(make_config(email=email))


def test_factory_rejects_unknown_whatsapp_provider():
    whatsapp = WhatsAppProviderConfig(provider="other")

    with pytest.raises(ValueError, match="Unsupported WhatsApp provider"):
        build_provider_registry(make_config(whatsapp=whatsapp))
