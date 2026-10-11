from __future__ import annotations

from reach.providers.base import MessageProvider


class ProviderRegistry:
    """
    Registry for outbound messaging providers.

    Providers are registered by channel and resolved at runtime.
    """

    def __init__(self) -> None:
        self._providers: dict[str, MessageProvider] = {}

    def register(self, provider: MessageProvider) -> None:
        channel = provider.channel.strip().lower()

        if not channel:
            raise ValueError("Provider channel cannot be empty.")

        provider_name = provider.provider_name.strip()

        if not provider_name:
            raise ValueError("Provider name cannot be empty.")

        if channel in self._providers:
            raise ValueError(
                f"A provider is already registered for channel '{channel}'."
            )

        self._providers[channel] = provider

    def get(self, channel: str) -> MessageProvider:
        normalized = channel.strip().lower()

        if normalized not in self._providers:
            raise ValueError(
                f"No provider registered for channel '{normalized}'."
            )

        return self._providers[normalized]

    def has(self, channel: str) -> bool:
        normalized = channel.strip().lower()
        return normalized in self._providers

    def channels(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))