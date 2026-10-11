from __future__ import annotations

import pytest

from reach.providers.config import (
    EmailProviderConfig,
    ProviderConfig,
    WhatsAppProviderConfig,
)


def test_default_providers_are_fake(monkeypatch):
    monkeypatch.delenv("NAMMAWEB_EMAIL_PROVIDER", raising=False)
    monkeypatch.delenv("NAMMAWEB_WHATSAPP_PROVIDER", raising=False)

    config = ProviderConfig.from_environment()

    assert config.email.provider == "fake"
    assert config.whatsapp.provider == "fake"


def test_email_config_reads_environment(monkeypatch):
    monkeypatch.setenv("NAMMAWEB_EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("NAMMAWEB_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("NAMMAWEB_SMTP_PORT", "465")
    monkeypatch.setenv("NAMMAWEB_SMTP_USERNAME", "test-user")
    monkeypatch.setenv("NAMMAWEB_SMTP_PASSWORD", "test-password")
    monkeypatch.setenv("NAMMAWEB_FROM_EMAIL", "sender@example.com")
    monkeypatch.setenv("NAMMAWEB_FROM_NAME", "NammaWeb")
    monkeypatch.setenv("NAMMAWEB_SMTP_USE_TLS", "false")

    config = EmailProviderConfig.from_environment()

    assert config.provider == "smtp"
    assert config.smtp_host == "smtp.example.com"
    assert config.smtp_port == 465
    assert config.smtp_username == "test-user"
    assert config.smtp_password == "test-password"
    assert config.from_email == "sender@example.com"
    assert config.from_name == "NammaWeb"
    assert config.use_tls is False


def test_whatsapp_config_reads_environment(monkeypatch):
    monkeypatch.setenv("NAMMAWEB_WHATSAPP_PROVIDER", "twilio")
    monkeypatch.setenv("NAMMAWEB_TWILIO_ACCOUNT_SID", "test-sid")
    monkeypatch.setenv("NAMMAWEB_TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("NAMMAWEB_TWILIO_FROM_NUMBER", "whatsapp:+14155238886")

    config = WhatsAppProviderConfig.from_environment()

    assert config.provider == "twilio"
    assert config.account_sid == "test-sid"
    assert config.auth_token == "test-token"
    assert config.from_number == "whatsapp:+14155238886"


def test_invalid_smtp_port_raises_error(monkeypatch):
    monkeypatch.setenv("NAMMAWEB_SMTP_PORT", "invalid")

    with pytest.raises(
        ValueError,
        match="NAMMAWEB_SMTP_PORT must be a valid integer",
    ):
        EmailProviderConfig.from_environment()
