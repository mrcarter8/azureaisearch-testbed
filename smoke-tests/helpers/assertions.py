"""
assertions.py — Assertion helpers with structured diff output for failure reporting.

Every helper accepts the raw response or parsed JSON and produces clear
expected-vs-actual messages on failure.  They are designed to work with
the FailureReporter to capture context automatically.
"""

from __future__ import annotations

from typing import Any, Callable

import requests


def _resolve_path(obj: Any, path: str) -> tuple[bool, Any]:
    """Walk a dot-separated path into a nested dict/list.

    Returns (found: bool, value).
    """
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return False, None
        else:
            return False, None
    return True, current


# ── Status code ──────────────────────────────────────────────────────────────

def assert_status(response: requests.Response, expected: int | tuple[int, ...]) -> None:
    """Assert HTTP status code matches expected (single int or tuple of ints)."""
    if isinstance(expected, int):
        expected = (expected,)
    if response.status_code not in expected:
        body_preview = response.text[:2000] if response.text else "(empty body)"
        raise AssertionError(
            f"Expected status {expected}, got {response.status_code}.\n"
            f"URL: {response.request.method} {response.url}\n"
            f"Response body:\n{body_preview}"
        )


def assert_status_not(response: requests.Response, excluded: int | tuple[int, ...]) -> None:
    """Assert HTTP status code is NOT one of the excluded values."""
    if isinstance(excluded, int):
        excluded = (excluded,)
    if response.status_code in excluded:
        body_preview = response.text[:2000] if response.text else "(empty body)"
        raise AssertionError(
            f"Status {response.status_code} was explicitly excluded {excluded}.\n"
            f"URL: {response.request.method} {response.url}\n"
            f"Response body:\n{body_preview}"
        )


# ── Field-level checks ──────────────────────────────────────────────────────

def assert_field_exists(data: dict, path: str) -> Any:
    """Assert that *path* exists in *data* and is not None. Returns the value."""
    found, value = _resolve_path(data, path)
    if not found:
        raise AssertionError(f"Field '{path}' not found in response.\nKeys at root: {list(data.keys()) if isinstance(data, dict) else '(not a dict)'}")
    if value is None:
        raise AssertionError(f"Field '{path}' exists but is None.")
    return value


def assert_field_absent(data: dict, path: str) -> None:
    """Assert that *path* does NOT exist in *data*."""
    found, _ = _resolve_path(data, path)
    if found:
        raise AssertionError(f"Field '{path}' should be absent but was found in response.")


def assert_field_equals(data: dict, path: str, expected: Any) -> None:
    """Assert field at *path* equals *expected*."""
    found, actual = _resolve_path(data, path)
    if not found:
        raise AssertionError(f"Field '{path}' not found. Cannot compare to expected={expected!r}.")
    if actual != expected:
        raise AssertionError(f"Field '{path}': expected {expected!r}, got {actual!r}.")


def assert_field_contains(data: dict, path: str, substring: str) -> None:
    """Assert the string value at *path* contains *substring* (case-insensitive)."""
    found, actual = _resolve_path(data, path)
    if not found:
        raise AssertionError(f"Field '{path}' not found.")
    if not isinstance(actual, str) or substring.lower() not in actual.lower():
        raise AssertionError(f"Field '{path}': expected to contain '{substring}', got {actual!r}.")


# ── Collection checks ────────────────────────────────────────────────────────

def assert_count(data: dict, path: str, expected_count: int) -> None:
    """Assert the collection at *path* has exactly *expected_count* items."""
    found, items = _resolve_path(data, path)
    if not found or not isinstance(items, (list, tuple)):
        raise AssertionError(f"Field '{path}' not found or not a collection.")
    if len(items) != expected_count:
        raise AssertionError(f"Field '{path}': expected {expected_count} items, got {len(items)}.")


def assert_count_gte(data: dict, path: str, minimum: int) -> None:
    """Assert the collection at *path* has at least *minimum* items."""
    found, items = _resolve_path(data, path)
    if not found or not isinstance(items, (list, tuple)):
        raise AssertionError(f"Field '{path}' not found or not a collection.")
    if len(items) < minimum:
        raise AssertionError(f"Field '{path}': expected >= {minimum} items, got {len(items)}.")


def assert_all_match(data: dict, items_path: str, predicate: Callable[[Any], bool], description: str = "") -> None:
    """Assert every item in the collection at *items_path* satisfies *predicate*.

    *description* is shown in the error message to explain the predicate.
    """
    found, items = _resolve_path(data, items_path)
    if not found or not isinstance(items, (list, tuple)):
        raise AssertionError(f"Field '{items_path}' not found or not a collection.")
    for i, item in enumerate(items):
        if not predicate(item):
            raise AssertionError(
                f"Item [{i}] in '{items_path}' failed predicate"
                f"{' (' + description + ')' if description else ''}.\nItem: {item!r}"
            )


def assert_order(data: dict, items_path: str, field: str, direction: str = "asc") -> None:
    """Assert items in collection are sorted by *field* in *direction* ('asc' or 'desc')."""
    found, items = _resolve_path(data, items_path)
    if not found or not isinstance(items, (list, tuple)):
        raise AssertionError(f"Field '{items_path}' not found or not a collection.")
    if len(items) < 2:
        return  # Nothing to compare
    values = []
    for i, item in enumerate(items):
        ok, val = _resolve_path(item, field)
        if not ok:
            raise AssertionError(f"Item [{i}] in '{items_path}' missing field '{field}'.")
        values.append(val)
    for i in range(len(values) - 1):
        if values[i] is None or values[i + 1] is None:
            continue
        if direction == "desc" and values[i] < values[i + 1]:
            raise AssertionError(
                f"Sort violation at [{i}]: {values[i]} < {values[i+1]} (expected descending)."
            )
        if direction == "asc" and values[i] > values[i + 1]:
            raise AssertionError(
                f"Sort violation at [{i}]: {values[i]} > {values[i+1]} (expected ascending)."
            )


# ── Convenience ──────────────────────────────────────────────────────────────

def assert_search_results(response: requests.Response, *, min_count: int = 1) -> dict:
    """Assert a search response is 200 with at least *min_count* results. Returns parsed JSON."""
    assert_status(response, 200)
    data = response.json()
    results = data.get("value", [])
    if len(results) < min_count:
        raise AssertionError(f"Expected at least {min_count} search results, got {len(results)}.")
    return data


def assert_odata_count(data: dict, expected: int | None = None) -> int:
    """Assert @odata.count is present and optionally matches *expected*. Returns the count."""
    count = data.get("@odata.count")
    if count is None:
        raise AssertionError("@odata.count not present in response.")
    if expected is not None and count != expected:
        raise AssertionError(f"@odata.count: expected {expected}, got {count}.")
    return count
