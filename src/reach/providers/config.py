from __future__ import annotations

from dataclasses import dataclass
import os


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class EmailProviderConfig:
    provider: str = "fake"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    use_tls: bool = True

    @classmethod
    def from_environment(cls) -> "EmailProviderConfig":
        try:
            port = int(os.getenv("NAMMAWEB_SMTP_PORT", "587"))
        except ValueError as exc:
            raise ValueError("NAMMAWEB_SMTP_PORT must be a valid integer.") from exc

        return cls(
            provider=os.getenv("NAMMAWEB_EMAIL_PROVIDER", "fake").strip().lower(),
            smtp_host=os.getenv("NAMMAWEB_SMTP_HOST"),
            smtp_port=port,
            smtp_username=os.getenv("NAMMAWEB_SMTP_USERNAME"),
            smtp_password=os.getenv("NAMMAWEB_SMTP_PASSWORD"),
            from_email=os.getenv("NAMMAWEB_FROM_EMAIL"),
            from_name=os.getenv("NAMMAWEB_FROM_NAME"),
            use_tls=_get_bool("NAMMAWEB_SMTP_USE_TLS", True),
        )


@dataclass(frozen=True)
class WhatsAppProviderConfig:
    provider: str = "fake"
    account_sid: str | None = None
    auth_token: str | None = None
    from_number: str | None = None

    @classmethod
    def from_environment(cls) -> "WhatsAppProviderConfig":
        return cls(
            provider=os.getenv("NAMMAWEB_WHATSAPP_PROVIDER", "fake").strip().lower(),
            account_sid=os.getenv("NAMMAWEB_TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("NAMMAWEB_TWILIO_AUTH_TOKEN"),
            from_number=os.getenv("NAMMAWEB_TWILIO_FROM_NUMBER"),
        )


@dataclass(frozen=True)
class ProviderConfig:
    email: EmailProviderConfig
    whatsapp: WhatsAppProviderConfig

    @classmethod
    def from_environment(cls) -> "ProviderConfig":
        return cls(
            email=EmailProviderConfig.from_environment(),
            whatsapp=WhatsAppProviderConfig.from_environment(),
        )
