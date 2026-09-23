from __future__ import annotations

from typing import Any

import httpx

from .config import Settings
from .errors import (
    BorealisAccessError,
    BorealisError,
    BorealisFileTooLargeError,
    BorealisNotFoundError,
    BorealisUnsupportedFileError,
)


class BorealisClient:
    """Small async client for the Borealis Dataverse API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def _headers(self, *, accept: str | None = None, authenticated: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {}
        if accept:
            headers["Accept"] = accept
        if authenticated and self.settings.authentication_configured:
            headers["X-Dataverse-key"] = self.settings.api_key
        return headers

    async def request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        accept: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        url = f"{self.settings.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        used_auth = self.settings.authentication_configured
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.request(method, url, params=params, headers=self._headers(accept=accept))
            if response.status_code == 401 and used_auth:
                used_auth = False
                response = await client.request(method, url, params=params, headers=self._headers(accept=accept, authenticated=False))
            if response.status_code == 404:
                raise BorealisNotFoundError(f"Borealis resource not found: {url}")
            if response.status_code in {401, 403}:
                raise BorealisAccessError(f"Borealis denied access ({response.status_code}).")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise BorealisError(f"Borealis API returned HTTP {response.status_code}: {response.text[:500]}") from exc
            payload = response.json()
            if isinstance(payload, dict) and payload.get("status") not in {None, "OK"}:
                raise BorealisError(f"Borealis API returned status {payload.get('status')!r}")
            return payload, used_auth

    async def request_text(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        accept: str | None = None,
    ) -> tuple[str, bool]:
        """GET/POST a non-JSON payload (e.g. DDI XML) and return the raw text."""
        url = f"{self.settings.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        used_auth = self.settings.authentication_configured
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.request(method, url, params=params, headers=self._headers(accept=accept))
            if response.status_code == 401 and used_auth:
                used_auth = False
                response = await client.request(method, url, params=params, headers=self._headers(accept=accept, authenticated=False))
            if response.status_code == 404:
                raise BorealisNotFoundError(f"Borealis resource not found: {url}")
            if response.status_code in {401, 403}:
                raise BorealisAccessError(f"Borealis denied access ({response.status_code}).")
            if response.status_code == 400:
                # Dataverse returns 400 (not 404) when a file exists but has no DDI to serve,
                # e.g. it was never tabular-ingested.
                raise BorealisUnsupportedFileError(f"Borealis rejected the request: {response.text[:300]}")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise BorealisError(f"Borealis API returned HTTP {response.status_code}: {response.text[:500]}") from exc
            return response.text, used_auth

    async def download_limited(self, file_id: str) -> tuple[bytes, str, bool]:
        endpoint = f"access/datafile/{file_id}"
        url = f"{self.settings.api_base_url.rstrip('/')}/{endpoint}"
        used_auth = self.settings.authentication_configured
        chunks: list[bytes] = []
        total = 0
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers=self._headers())
            if response.status_code == 401 and used_auth:
                used_auth = False
                response = await client.get(url, headers=self._headers(authenticated=False))
            if response.status_code == 404:
                raise BorealisNotFoundError(f"File {file_id} was not found.")
            if response.status_code in {401, 403}:
                raise BorealisAccessError(f"Access to file {file_id} is restricted.")
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > self.settings.max_file_bytes:
                    raise BorealisFileTooLargeError(
                        f"File exceeds the configured {self.settings.max_file_bytes:,}-byte limit."
                    )
                chunks.append(chunk)
        return b"".join(chunks), response.headers.get("content-type", ""), used_auth
