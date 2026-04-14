"""
wait.py — Polling utilities for async Azure AI Search operations.
"""

from __future__ import annotations

import time

from helpers.rest_client import RestClient


def poll_indexer_status(
    rest: RestClient,
    indexer_name: str,
    *,
    timeout_seconds: int = 600,
    initial_interval: float = 2.0,
    max_interval: float = 30.0,
) -> dict:
    """Poll ``GET /indexers/{name}/status`` until the last execution completes.

    Returns the parsed JSON body of the final status response.
    Raises ``TimeoutError`` if *timeout_seconds* is exceeded.
    Raises ``RuntimeError`` on persistent failure.
    """
    deadline = time.monotonic() + timeout_seconds
    interval = initial_interval

    while True:
        resp = rest.get(f"/indexers('{indexer_name}')/status")
        if resp.status_code != 200:
            raise RuntimeError(
                f"GET indexer status returned {resp.status_code}: {resp.text[:1000]}"
            )

        data = resp.json()
        last = data.get("lastResult") or {}
        status = last.get("status", "inProgress")

        if status == "success":
            return data
        if status == "transientFailure":
            return data
        if status == "persistentFailure":
            msg = last.get("errorMessage", "(no error message)")
            raise RuntimeError(f"Indexer '{indexer_name}' failed permanently: {msg}")
        # transientFailure or inProgress — keep polling

        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Indexer '{indexer_name}' did not complete within {timeout_seconds}s. "
                f"Last status: {status}"
            )

        time.sleep(interval)
        interval = min(interval * 1.5, max_interval)


def poll_provisioning_state(
    rest: RestClient,
    *,
    timeout_seconds: int = 300,
    initial_interval: float = 5.0,
    max_interval: float = 30.0,
) -> dict:
    """Poll ``GET`` on the management-plane service until provisioningState is terminal.

    Returns the parsed JSON body when state is 'Succeeded'.
    Raises ``RuntimeError`` on 'Failed' or 'Canceled'.
    Raises ``TimeoutError`` if *timeout_seconds* is exceeded.
    """
    deadline = time.monotonic() + timeout_seconds
    interval = initial_interval

    while True:
        resp = rest.mgmt_get()
        if resp.status_code != 200:
            raise RuntimeError(
                f"GET service returned {resp.status_code}: {resp.text[:1000]}"
            )

        data = resp.json()
        state = data.get("properties", {}).get("provisioningState", "unknown")

        if state == "Succeeded":
            return data
        if state in ("Failed", "Canceled"):
            raise RuntimeError(f"Service provisioning {state}.")

        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Service provisioning did not complete within {timeout_seconds}s. "
                f"Last state: {state}"
            )

        time.sleep(interval)
        interval = min(interval * 1.5, max_interval)
