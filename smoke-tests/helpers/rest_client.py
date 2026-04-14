"""
rest_client.py — Thin HTTP wrapper for Azure AI Search REST API calls.

Features:
- Auto-injects api-version query param (configurable per call)
- Auto-injects auth headers (API key or Bearer token)
- Retry on 429/503 with exponential backoff + jitter (up to 3 retries)
- Captures full request/response pairs for failure reporting
- Management plane variant (mgmt_* methods) targeting management.azure.com
"""

from __future__ import annotations

import copy
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests


@dataclass
class RequestRecord:
    """Captured request/response pair for diagnostic reporting."""

    timestamp: str
    method: str
    url: str
    request_headers: dict
    request_body: Any
    status_code: int
    response_headers: dict
    response_body: Any
    x_ms_request_id: str | None
    elapsed_ms: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "method": self.method,
            "url": self.url,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "x_ms_request_id": self.x_ms_request_id,
            "elapsed_ms": self.elapsed_ms,
        }


def _redact_headers(headers: dict) -> dict:
    """Return a copy of headers with sensitive values redacted."""
    redacted = dict(headers)
    for key in list(redacted.keys()):
        lower = key.lower()
        if lower in ("api-key", "authorization"):
            val = str(redacted[key])
            if len(val) > 8:
                redacted[key] = val[:4] + "****" + val[-4:]
            else:
                redacted[key] = "****"
    return redacted


class RestClient:
    """
    HTTP client for Azure AI Search data-plane and management-plane REST APIs.

    Parameters
    ----------
    base_url : str
        Search service endpoint, e.g. ``https://myservice.search-ppe.windows-int.net``
    headers : dict
        Default headers merged into every request (auth, content-type).
    api_version : str
        Default api-version query parameter for data-plane calls.
    mgmt_api_version : str
        Default api-version for management-plane calls.
    max_retries : int
        Maximum retries on 429 / 503 (default 3).
    subscription_id : str | None
        Azure subscription ID (needed for mgmt calls).
    resource_group : str | None
        Resource group name (needed for mgmt calls).
    service_name : str | None
        Search service name (needed for mgmt calls).
    mgmt_headers : dict | None
        Separate auth headers for management-plane calls (Bearer token).
    """

    MGMT_BASE = "https://management.azure.com"
    RETRYABLE_CODES = (429, 503)

    def __init__(
        self,
        base_url: str,
        headers: dict,
        api_version: str,
        mgmt_api_version: str = "2026-03-01-Preview",
        max_retries: int = 5,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        service_name: str | None = None,
        mgmt_headers: dict | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.api_version = api_version
        self.mgmt_api_version = mgmt_api_version
        self.max_retries = max_retries
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.service_name = service_name
        self.mgmt_headers = mgmt_headers or {}

        # Rolling buffer of the last N request records (most recent kept for reporting)
        self.history: list[RequestRecord] = []
        self._last_record: RequestRecord | None = None

    # ── public properties ────────────────────────────────────────────────

    @property
    def last_record(self) -> RequestRecord | None:
        """Most recent request/response record."""
        return self._last_record

    # ── data-plane helpers ───────────────────────────────────────────────

    def get(self, path: str, *, params: dict | None = None, api_version: str | None = None) -> requests.Response:
        return self._request("GET", path, params=params, api_version=api_version)

    def put(self, path: str, body: dict | None = None, *, params: dict | None = None, api_version: str | None = None, extra_headers: dict | None = None) -> requests.Response:
        return self._request("PUT", path, json_body=body, params=params, api_version=api_version, extra_headers=extra_headers)

    def post(self, path: str, body: dict | None = None, *, params: dict | None = None, api_version: str | None = None) -> requests.Response:
        return self._request("POST", path, json_body=body, params=params, api_version=api_version)

    def delete(self, path: str, *, params: dict | None = None, api_version: str | None = None) -> requests.Response:
        return self._request("DELETE", path, params=params, api_version=api_version)

    def patch(self, path: str, body: dict | None = None, *, params: dict | None = None, api_version: str | None = None) -> requests.Response:
        return self._request("PATCH", path, json_body=body, params=params, api_version=api_version)

    # ── management-plane helpers ─────────────────────────────────────────

    @property
    def _mgmt_service_path(self) -> str:
        return (
            f"/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.Search/searchServices/{self.service_name}"
        )

    def mgmt_get(self, path: str = "", *, api_version: str | None = None) -> requests.Response:
        url = f"{self.MGMT_BASE}{self._mgmt_service_path}{path}"
        return self._request_raw("GET", url, headers=self._mgmt_request_headers(), params={"api-version": api_version or self.mgmt_api_version})

    def mgmt_put(self, path: str, body: dict | None = None, *, api_version: str | None = None) -> requests.Response:
        url = f"{self.MGMT_BASE}{self._mgmt_service_path}{path}"
        return self._request_raw("PUT", url, headers=self._mgmt_request_headers(), json_body=body, params={"api-version": api_version or self.mgmt_api_version})

    def mgmt_post(self, path: str = "", body: dict | None = None, *, api_version: str | None = None) -> requests.Response:
        url = f"{self.MGMT_BASE}{self._mgmt_service_path}{path}"
        return self._request_raw("POST", url, headers=self._mgmt_request_headers(), json_body=body, params={"api-version": api_version or self.mgmt_api_version})

    def mgmt_patch(self, path: str = "", body: dict | None = None, *, api_version: str | None = None) -> requests.Response:
        url = f"{self.MGMT_BASE}{self._mgmt_service_path}{path}"
        return self._request_raw("PATCH", url, headers=self._mgmt_request_headers(), json_body=body, params={"api-version": api_version or self.mgmt_api_version})

    def mgmt_delete(self, path: str = "", *, api_version: str | None = None) -> requests.Response:
        url = f"{self.MGMT_BASE}{self._mgmt_service_path}{path}"
        return self._request_raw("DELETE", url, headers=self._mgmt_request_headers(), params={"api-version": api_version or self.mgmt_api_version})

    def mgmt_url(self, path: str = "") -> str:
        """Build full management URL for the configured service."""
        return f"{self.MGMT_BASE}{self._mgmt_service_path}{path}"

    def mgmt_request(self, method: str, full_url: str, body: dict | None = None, *, api_version: str | None = None) -> requests.Response:
        """Make an arbitrary management-plane request to a full URL."""
        return self._request_raw(method, full_url, headers=self._mgmt_request_headers(), json_body=body, params={"api-version": api_version or self.mgmt_api_version})

    # ── internal ─────────────────────────────────────────────────────────

    def _mgmt_request_headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        h.update(self.mgmt_headers)
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        api_version: str | None = None,
        extra_headers: dict | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        merged_params = {"api-version": api_version or self.api_version}
        if params:
            merged_params.update(params)
        merged_headers = {**self.headers}
        if extra_headers:
            merged_headers.update(extra_headers)
        return self._request_raw(method, url, headers=merged_headers, json_body=json_body, params=merged_params)

    def _request_raw(
        self,
        method: str,
        url: str,
        *,
        headers: dict,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> requests.Response:
        last_response: requests.Response | None = None
        for attempt in range(self.max_retries + 1):
            ts = datetime.now(timezone.utc).isoformat()
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=json_body,
                    params=params,
                    timeout=120,
                )
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as exc:
                # Retry SSL/connection errors with backoff
                record = RequestRecord(
                    timestamp=ts,
                    method=method,
                    url=url,
                    request_headers=_redact_headers(headers),
                    request_body=json_body,
                    status_code=0,
                    response_headers={},
                    response_body=str(exc),
                    x_ms_request_id=None,
                    elapsed_ms=0,
                )
                self._save_record(record)
                if attempt == self.max_retries:
                    raise
                wait = 2 ** attempt + random.uniform(0, 1)
                time.sleep(wait)
                continue
            except requests.RequestException as exc:
                record = RequestRecord(
                    timestamp=ts,
                    method=method,
                    url=url,
                    request_headers=_redact_headers(headers),
                    request_body=json_body,
                    status_code=0,
                    response_headers={},
                    response_body=str(exc),
                    x_ms_request_id=None,
                    elapsed_ms=0,
                )
                self._save_record(record)
                raise

            last_response = resp

            # Record every attempt
            try:
                resp_body = resp.json()
            except Exception:
                resp_body = resp.text[:4000] if resp.text else None

            record = RequestRecord(
                timestamp=ts,
                method=method,
                url=url,
                request_headers=_redact_headers(headers),
                request_body=json_body,
                status_code=resp.status_code,
                response_headers=dict(resp.headers),
                response_body=resp_body,
                x_ms_request_id=resp.headers.get("x-ms-request-id"),
                elapsed_ms=resp.elapsed.total_seconds() * 1000,
            )
            self._save_record(record)

            if resp.status_code not in self.RETRYABLE_CODES or attempt == self.max_retries:
                return resp

            # Retry with backoff + jitter
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = 2 ** attempt
            else:
                wait = 2 ** attempt
            wait += random.uniform(0, 1)
            time.sleep(wait)

        return last_response  # type: ignore[return-value]

    def _save_record(self, record: RequestRecord) -> None:
        self._last_record = record
        self.history.append(record)
        # Keep history bounded
        if len(self.history) > 500:
            self.history = self.history[-250:]
