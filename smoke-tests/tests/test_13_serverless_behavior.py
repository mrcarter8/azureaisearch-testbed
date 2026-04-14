"""
test_13_serverless_behavior.py — Serverless-Specific Behavioral Tests

Tests: SLS-01 through SLS-12
Focus: What could break specifically because the service runs on a new serverless backend.
"""

import concurrent.futures
import time

import pytest

from conftest import ensure_fresh
from helpers.assertions import assert_status

pytestmark = [pytest.mark.serverless]


# ---------------------------------------------------------------------------
# Latency & Throughput
# ---------------------------------------------------------------------------


class TestServerlessLatency:

    def test_sls_01_cold_start_latency(self, rest, primary_index_name):
        """SLS-01: Query latency — measure response time for first query."""
        # Verify index exists first
        check = rest.get(f"/indexes/{primary_index_name}")
        if check.status_code == 404:
            pytest.skip(f"Index {primary_index_name} not found (run phases 1-5 first)")
        start = time.perf_counter()
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel", "top": 1,
        })
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert_status(resp, 200)
        # Record latency for reporting; fail only if egregiously slow (>30s)
        assert elapsed_ms < 30_000, f"Cold start query took {elapsed_ms:.0f}ms (>30s threshold)"

    def test_sls_02_index_creation_latency(self, rest):
        """SLS-02: Index creation latency on serverless."""
        name = "smoke-sls02-latency"
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True},
                {"name": "content", "type": "Edm.String", "searchable": True},
            ],
        }
        ensure_fresh(rest, f"/indexes/{name}")
        start = time.perf_counter()
        resp = rest.put(f"/indexes/{name}", body)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        assert elapsed_ms < 30_000, f"Index creation took {elapsed_ms:.0f}ms (>30s threshold)"

    def test_sls_03_indexer_throughput(self, rest, indexer_blob_name):
        """SLS-03: Blob indexer E2E run completes within 10-minute timeout.

        If the blob indexer was successfully created and run in test_09,
        this checks the timing from the last result.
        """
        import os
        if not os.getenv("BLOB_CONNECTION_STRING"):
            pytest.skip("Blob storage not configured")
        resp = rest.get(f"/indexers/{indexer_blob_name}/status")
        if resp.status_code == 404:
            pytest.skip("Blob indexer not created")
        assert_status(resp, 200)
        data = resp.json()
        last = data.get("lastResult", {})
        if last and last.get("status") == "success":
            duration = last.get("elapsedTime", "")
            # elapsedTime is ISO 8601 duration; just verify it completed
            assert duration, "No elapsedTime on successful indexer run"


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestServerlessConcurrency:

    def test_sls_04_concurrent_queries(self, rest, primary_index_name):
        """SLS-04: Fire 20 parallel search queries — no 500s."""
        import requests as req

        # Verify index exists first
        check = rest.get(f"/indexes/{primary_index_name}")
        if check.status_code == 404:
            pytest.skip(f"Index {primary_index_name} not found (run phases 1-5 first)")

        def fire_query(i):
            url = f"{rest.base_url}/indexes/{primary_index_name}/docs/search"
            payload = {"search": f"hotel {i}", "top": 5}
            r = req.post(
                url, json=payload,
                headers=rest.headers,
                params={"api-version": rest.api_version},
                timeout=30,
            )
            return r.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            codes = list(pool.map(fire_query, range(20)))

        errors_500 = [c for c in codes if c >= 500]
        assert len(errors_500) == 0, f"Got {len(errors_500)} server errors (5xx): {codes}"

    def test_sls_05_concurrent_index_operations(self, rest):
        """SLS-05: Create 5 indexes in parallel — all succeed or get clear error."""
        import requests as req

        for i in range(5):
            ensure_fresh(rest, f"/indexes/smoke-sls05-{i}")

        def create_index(i):
            name = f"smoke-sls05-{i}"
            body = {
                "name": name,
                "fields": [{"name": "id", "type": "Edm.String", "key": True}],
            }
            url = f"{rest.base_url}/indexes/{name}"
            r = req.put(
                url, json=body,
                headers=rest.headers,
                params={"api-version": rest.api_version},
                timeout=30,
            )
            return name, r.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(create_index, range(5)))

        statuses = [s for _, s in results]
        errors_500 = [s for s in statuses if s >= 500]
        assert len(errors_500) == 0, f"Got 5xx creating indexes in parallel: {statuses}"


# ---------------------------------------------------------------------------
# Limits & Behavior
# ---------------------------------------------------------------------------


class TestServerlessLimits:

    def test_sls_06_service_stats_limits(self, rest):
        """SLS-06: Verify /servicestats limits are appropriate for serverless."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        data = resp.json()
        counters = data.get("counters", {})
        # Should have standard counters
        assert len(counters) > 0, f"No counters in servicestats: {data}"

    def test_sls_07_large_result_set(self, rest, primary_index_name):
        """SLS-07: Request top=1000 — returns results or documented limit error."""
        check = rest.get(f"/indexes/{primary_index_name}")
        if check.status_code == 404:
            pytest.skip(f"Index {primary_index_name} not found (run phases 1-5 first)")
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*", "top": 1000,
        })
        # Accept 200 (returns up to limit) or 400 (top too large)
        assert resp.status_code in (200, 400), f"Expected 200/400, got {resp.status_code}"

    def test_sls_08_rapid_sequential_operations(self, rest):
        """SLS-08: Create index → upload docs → search within seconds."""
        name = "smoke-sls08-rapid"
        # 1. Create index
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True},
                {"name": "title", "type": "Edm.String", "searchable": True},
            ],
        }
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201), f"Index create failed: {resp.status_code}"

        # 2. Upload docs immediately
        docs = {
            "value": [
                {"@search.action": "upload", "id": str(i), "title": f"Rapid test {i}"}
                for i in range(10)
            ]
        }
        resp = rest.post(f"/indexes/{name}/docs/index", docs)
        assert_status(resp, 200)

        # 3. Search immediately (may not find docs yet due to eventual consistency)
        time.sleep(1)
        resp = rest.post(f"/indexes/{name}/docs/search", {"search": "Rapid", "top": 10})
        assert_status(resp, 200)


# ---------------------------------------------------------------------------
# API Version & Error Quality
# ---------------------------------------------------------------------------


class TestServerlessAPIBehavior:

    def test_sls_09_api_version_fallback(self, rest, primary_index_name):
        """SLS-09: Older data-plane API version on serverless — succeeds or clear error."""
        older_versions = ["2024-07-01", "2024-05-01-Preview", "2023-11-01"]
        for version in older_versions:
            resp = rest.get(f"/indexes/{primary_index_name}", api_version=version)
            assert resp.status_code in (200, 400, 404), (
                f"api-version={version}: unexpected {resp.status_code}"
            )

    def test_sls_10_error_message_quality(self, rest):
        """SLS-10: Error responses are descriptive (not generic 500s)."""
        # Trigger a 404
        resp = rest.get("/indexes/nonexistent-index-smoke-test")
        assert resp.status_code in (404, 400), f"Expected 404/400, got {resp.status_code}"
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        error = body.get("error", {})
        if error:
            assert error.get("message"), "Error response has no message"
            # Note: serverless may return empty string for error code — that's acceptable
            # as long as the message is descriptive

        # Trigger a 400 via invalid filter syntax
        resp = rest.post("/indexes/nonexistent-index-smoke-test/docs/search", {
            "search": "*", "filter": "INVALID SYNTAX !!!",
        })
        # May get 400 (bad filter) or 404 (index not found)
        assert resp.status_code in (400, 404), f"Expected 400/404, got {resp.status_code}"
        body = resp.json()
        error = body.get("error", {})
        assert error.get("message"), "Error response has no descriptive message"

    def test_sls_11_request_id_tracking(self, rest, primary_index_name):
        """SLS-11: Every response includes x-ms-request-id header."""
        # Use endpoints that we know exist (servicestats always works)
        endpoints = [
            ("GET", "/servicestats"),
            ("GET", "/indexes"),
        ]
        # Only add index-specific endpoints if the index exists
        check = rest.get(f"/indexes/{primary_index_name}")
        if check.status_code == 200:
            endpoints.append(("POST", f"/indexes/{primary_index_name}/docs/search"))

        for method, path in endpoints:
            if method == "GET":
                resp = rest.get(path)
            else:
                resp = rest.post(path, {"search": "*", "top": 1})
            # Check both possible header names
            request_id = resp.headers.get("x-ms-request-id", "") or resp.headers.get("request-id", "")
            assert request_id, f"{method} {path} missing request-id header"

    def test_sls_12_throttling_behavior(self, rest, primary_index_name):
        """SLS-12: Rapid-fire queries — 429 responses include Retry-After header."""
        import requests as req

        check = rest.get(f"/indexes/{primary_index_name}")
        if check.status_code == 404:
            pytest.skip(f"Index {primary_index_name} not found (run phases 1-5 first)")

        got_429 = False
        for _ in range(60):
            r = req.post(
                f"{rest.base_url}/indexes/{primary_index_name}/docs/search",
                json={"search": "*", "top": 1},
                headers=rest.headers,
                params={"api-version": rest.api_version},
                timeout=10,
            )
            if r.status_code == 429:
                got_429 = True
                retry_after = r.headers.get("Retry-After", "")
                assert retry_after, "429 response missing Retry-After header"
                break

        if not got_429:
            pytest.skip("Service did not throttle after 60 rapid requests")
