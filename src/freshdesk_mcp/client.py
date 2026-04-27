from __future__ import annotations

from typing import Any

import httpx

from .config import FreshdeskSettings


class FreshdeskClient:
    def __init__(self, settings: FreshdeskSettings) -> None:
        self._settings = settings

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(
            base_url=self._settings.base_url,
            auth=(self._settings.api_key, "X"),
            headers={"Accept": "application/json"},
            timeout=self._settings.timeout_seconds,
        ) as client:
            response = await client.request(
                method,
                f"/api/v2/{path.lstrip('/')}",
                params=params,
                json=json,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            if len(detail) > 500:
                detail = f"{detail[:497]}..."
            raise RuntimeError(
                f"Freshdesk API request failed with status {exc.response.status_code}: {detail}"
            ) from exc

        if response.status_code == 204 or not response.content:
            return {"ok": True}
        return response.json()
