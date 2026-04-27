from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class FreshdeskSettings:
    api_key: str
    domain: str
    timeout_seconds: float = 30.0

    @property
    def base_url(self) -> str:
        domain = self.domain.strip()
        if not domain:
            raise ConfigurationError("FRESHDESK_DOMAIN is empty.")
        if domain.startswith("http://") or domain.startswith("https://"):
            return domain.rstrip("/")
        return f"https://{domain.rstrip('/')}"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "FreshdeskSettings":
        source = env if env is not None else os.environ
        api_key = source.get("FRESHDESK_API_KEY", "").strip()
        domain = source.get("FRESHDESK_DOMAIN", "").strip()
        timeout_raw = source.get("FRESHDESK_TIMEOUT_SECONDS", "30").strip()

        if not api_key:
            raise ConfigurationError("Missing required environment variable FRESHDESK_API_KEY.")
        if not domain:
            raise ConfigurationError("Missing required environment variable FRESHDESK_DOMAIN.")

        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise ConfigurationError("FRESHDESK_TIMEOUT_SECONDS must be a number.") from exc

        return cls(api_key=api_key, domain=domain, timeout_seconds=timeout_seconds)
