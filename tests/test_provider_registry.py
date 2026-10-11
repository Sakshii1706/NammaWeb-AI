from __future__ import annotations

import pytest

from reach.providers.fake_providers import (
    FakeEmailProvider,
    FakeWhatsAppProvider,
)
from reach.providers.registry import ProviderRegistry


def test_registry_registers_and_resolves_providers():
    registry = ProviderRegistry()

    email_provider = FakeEmailProvider()
    whatsapp_provider = FakeWhatsAppProvider()

    registry.register(email_provider)
    registry.register(whatsapp_provider)

    assert registry.get("email") is email_provider
    assert registry.get("whatsapp") is whatsapp_provider

    assert registry.has("email")
    assert registry.has("whatsapp")

    assert registry.channels() == (
        "email",
        "whatsapp",
    )


def test_registry_normalizes_channel_names():
    registry = ProviderRegistry()

    email_provider = FakeEmailProvider()

    registry.register(email_provider)

    assert registry.get("EMAIL") is email_provider
    assert registry.get(" Email ") is email_provider
    assert registry.has("EMAIL")


def test_registry_rejects_duplicate_channel():
    registry = ProviderRegistry()

    registry.register(FakeEmailProvider())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeEmailProvider())


def test_registry_rejects_unknown_channel():
    registry = ProviderRegistry()

    with pytest.raises(
        ValueError,
        match="No provider registered",
    ):
        registry.get("sms")


def test_registry_requires_valid_provider_metadata():
    registry = ProviderRegistry()

    class InvalidProvider:
        provider_name = ""
        channel = "email"

        def send(self, request):
            raise NotImplementedError

    with pytest.raises(
        ValueError,
        match="Provider name cannot be empty",
    ):
        registry.register(InvalidProvider())