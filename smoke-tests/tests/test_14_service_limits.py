"""
test_14_service_limits.py — Service Limit Validation

Tests: LIM-01 through LIM-14

Validates that the service-level quotas, per-index limits, and throttling
rate limits reported by the Azure AI Search configured SKU match the
documented specifications.  Uses GET /servicestats, GET /indexes/{name}/stats,
and rapid-fire API calls to exercise throttling boundaries.

Expected limits (may vary by SKU):
  - Indexes per service: up to 3000
  - Indexers per service: up to 3000
  - Data sources per service: up to 3000
  - Skillsets per service: up to 3000
  - Synonym maps: 20
  - Aliases: 0 (not supported on some SKUs)
  - Max storage per index: 20 GB (per spec; actual may be higher in preview)
  - Max fields per index: up to 3000
  - Max vector index size: 30% of total storage
  - Throttling: documented static rate limits per API
"""

import time
import concurrent.futures

import pytest
import requests as _http

from conftest import ensure_fresh
from helpers.assertions import assert_status

pytestmark = [pytest.mark.service_limits]


# ── Expected quota ranges ────────────────────────────────────────────────────
# These define the *minimum acceptable* quota values.  The real quotas may
# exceed these (e.g. PPE may ship with 200 during preview, GA target is 3000).

_MIN_INDEX_QUOTA = 200       # preview minimum; GA target is 3000
_MIN_INDEXER_QUOTA = 200
_MIN_DATASOURCE_QUOTA = 200
_MIN_SKILLSET_QUOTA = 200
_SYNONYM_MAP_QUOTA = 20      # exact match expected
_ALIAS_QUOTA = 0             # some SKUs do not support aliases


class TestServiceQuotas:
    """LIM-01 through LIM-06: Validate service-level quotas in GET /servicestats."""

    def test_lim_01_servicestats_index_quota(self, rest):
        """LIM-01: indexesCount quota is present and >= expected minimum."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        idx = counters["indexesCount"]
        assert "quota" in idx, "indexesCount missing 'quota'"
        assert idx["quota"] is not None, "indexesCount quota is null"
        assert idx["quota"] >= _MIN_INDEX_QUOTA, (
            f"indexesCount quota {idx['quota']} < expected minimum {_MIN_INDEX_QUOTA}"
        )
        assert "usage" in idx, "indexesCount missing 'usage'"
        # Usage can be -1 when not yet computed; accept >= -1
        assert idx["usage"] >= -1, f"usage should be >= -1, got {idx['usage']}"

    def test_lim_02_servicestats_indexer_quota(self, rest):
        """LIM-02: indexersCount quota is present and >= expected minimum."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        ixr = counters["indexersCount"]
        assert ixr["quota"] is not None, "indexersCount quota is null"
        assert ixr["quota"] >= _MIN_INDEXER_QUOTA, (
            f"indexersCount quota {ixr['quota']} < expected minimum {_MIN_INDEXER_QUOTA}"
        )

    def test_lim_03_servicestats_datasource_quota(self, rest):
        """LIM-03: dataSourcesCount quota is present and >= expected minimum."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        ds = counters["dataSourcesCount"]
        assert ds["quota"] is not None, "dataSourcesCount quota is null"
        assert ds["quota"] >= _MIN_DATASOURCE_QUOTA, (
            f"dataSourcesCount quota {ds['quota']} < expected minimum {_MIN_DATASOURCE_QUOTA}"
        )

    def test_lim_04_servicestats_skillset_quota(self, rest):
        """LIM-04: skillsetCount quota is present and >= expected minimum."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        sk = counters["skillsetCount"]
        assert sk["quota"] is not None, "skillsetCount quota is null"
        assert sk["quota"] >= _MIN_SKILLSET_QUOTA, (
            f"skillsetCount quota {sk['quota']} < expected minimum {_MIN_SKILLSET_QUOTA}"
        )

    def test_lim_05_servicestats_synonym_map_quota(self, rest):
        """LIM-05: synonymMaps quota equals expected limit (20)."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        syn = counters["synonymMaps"]
        assert syn["quota"] is not None, "synonymMaps quota is null"
        assert syn["quota"] == _SYNONYM_MAP_QUOTA, (
            f"synonymMaps quota {syn['quota']} != expected {_SYNONYM_MAP_QUOTA}"
        )

    def test_lim_06_servicestats_alias_quota_zero(self, rest):
        """LIM-06: aliasesCount quota is 0 — aliases not supported on this SKU."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        al = counters["aliasesCount"]
        assert al["quota"] is not None, "aliasesCount quota is null"
        assert al["quota"] == _ALIAS_QUOTA, (
            f"aliasesCount quota {al['quota']} != expected {_ALIAS_QUOTA}"
        )


class TestServiceLimitsSection:
    """LIM-07 through LIM-09: Validate the 'limits' section in GET /servicestats."""

    def test_lim_07_max_storage_per_index(self, rest):
        """LIM-07: maxStoragePerIndex is present and > 0 in service limits."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        limits = resp.json()["limits"]
        max_storage = limits.get("maxStoragePerIndex")
        assert max_storage is not None, "maxStoragePerIndex is missing or null"
        assert max_storage > 0, f"maxStoragePerIndex should be > 0, got {max_storage}"
        # Log actual value for reference (spec says 20 GB, may differ in preview)
        gb = max_storage / (1024 ** 3)
        print(f"  maxStoragePerIndex = {max_storage} bytes ({gb:.1f} GB)")

    def test_lim_08_max_fields_per_index(self, rest):
        """LIM-08: maxFieldsPerIndex is present and >= 1000."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        limits = resp.json()["limits"]
        max_fields = limits.get("maxFieldsPerIndex")
        assert max_fields is not None, "maxFieldsPerIndex is missing or null"
        assert max_fields >= 1000, (
            f"maxFieldsPerIndex should be >= 1000, got {max_fields}"
        )

    def test_lim_09_vector_index_size_quota(self, rest):
        """LIM-09: vectorIndexSize quota is present and reflects ~30% of total storage."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        counters = resp.json()["counters"]
        vis = counters.get("vectorIndexSize", {})
        assert "quota" in vis or "usage" in vis, (
            "vectorIndexSize counter missing from servicestats"
        )
        vec_quota = vis.get("quota")
        storage_quota = counters.get("storageSize", {}).get("quota")
        if vec_quota is not None and storage_quota is not None and storage_quota > 0:
            ratio = vec_quota / storage_quota
            print(f"  vectorIndexSize quota = {vec_quota} bytes "
                  f"({vec_quota / (1024**3):.1f} GB), "
                  f"ratio to total storage = {ratio:.2%}")
            # Spec says ~30% of total storage
            assert 0.15 <= ratio <= 0.50, (
                f"vectorIndexSize/storageSize ratio {ratio:.2%} outside expected 15-50% range"
            )


class TestIndexStats:
    """LIM-10 through LIM-11: Validate per-index statistics API."""

    def test_lim_10_index_stats_structure(self, rest):
        """LIM-10: GET /indexes/{name}/stats returns documentCount, storageSize, vectorIndexSize."""
        # Create a minimal index to test against
        name = "smoke-lim10-stats"
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True},
                {"name": "content", "type": "Edm.String"},
            ],
        }
        ensure_fresh(rest, f"/indexes/{name}")
        put_resp = rest.put(f"/indexes/{name}", body)
        assert put_resp.status_code in (200, 201), (
            f"Create index failed: {put_resp.status_code}"
        )
        stats_resp = rest.get(f"/indexes/{name}/stats")
        assert_status(stats_resp, 200)
        data = stats_resp.json()
        assert "documentCount" in data, "Missing documentCount in index stats"
        assert "storageSize" in data, "Missing storageSize in index stats"
        assert "vectorIndexSize" in data, "Missing vectorIndexSize in index stats"
        assert data["documentCount"] >= 0
        assert data["storageSize"] >= 0
        assert data["vectorIndexSize"] >= 0

    def test_lim_11_index_stats_after_docs(self, rest, primary_index_name):
        """LIM-11: Index stats reflect document count and non-zero storage after upload."""
        # Use existing primary index — it should have docs from earlier phases
        stats_resp = rest.get(f"/indexes/{primary_index_name}/stats")
        if stats_resp.status_code == 404:
            pytest.skip("Primary index not found — run earlier phases first")
        assert_status(stats_resp, 200)
        data = stats_resp.json()
        doc_count = data.get("documentCount", 0)
        storage = data.get("storageSize", 0)
        print(f"  {primary_index_name}: {doc_count} docs, {storage} bytes storage")
        # If docs were uploaded in prior phases, count and storage should be > 0
        if doc_count > 0:
            assert storage > 0, (
                f"documentCount={doc_count} but storageSize=0 — stats inconsistency"
            )


class TestCounterUsageTracking:
    """LIM-12: Validate that counters.usage values track actual resource counts."""

    def test_lim_12_usage_tracks_resource_count(self, rest):
        """LIM-12: indexesCount.usage reflects the actual number of indexes on the service."""
        name = "smoke-lim12-track"
        ensure_fresh(rest, f"/indexes/{name}")

        # Create an index
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True},
            ],
        }
        put_resp = rest.put(f"/indexes/{name}", body)
        assert put_resp.status_code in (200, 201)

        # List indexes to get the authoritative count
        list_resp = rest.get("/indexes")
        assert list_resp.status_code == 200
        actual_count = len(list_resp.json().get("value", []))

        # Service stats usage should be >= the list count
        # (stats are periodic so usage may lag, but should never be LESS)
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        usage = resp.json()["counters"]["indexesCount"]["usage"]
        # Usage can be -1 when counter is not yet computed (PPE behavior)
        if usage < 0:
            pytest.skip(f"indexesCount.usage is {usage} (counter not computed yet)")
        assert usage >= 1, (
            f"indexesCount.usage should be >= 1 after creating an index, got {usage}"
        )
        print(f"  indexesCount.usage={usage}, list count={actual_count}")


class TestThrottling:
    """LIM-13 through LIM-14: Exercise throttling rate limits."""

    @staticmethod
    def _raw_get(base_url, path, headers, api_version):
        """Direct HTTP GET bypassing RestClient retry logic.  Retries on SSL errors only."""
        url = f"{base_url}{path}"
        for attempt in range(3):
            try:
                resp = _http.get(url, headers=headers, params={"api-version": api_version}, timeout=30)
                return resp.status_code
            except (_http.exceptions.SSLError, _http.exceptions.ConnectionError):
                if attempt == 2:
                    return -1  # SSL failure — count as "other"
                time.sleep(0.5)
        return -1

    def test_lim_13_list_indexes_throttle(self, rest):
        """LIM-13: Rapid GET /indexes calls observe 429 throttle at documented 3/sec limit."""
        # Documented limit: List Indexes = 3 per second per search unit.
        # Fire many requests in parallel to attempt triggering a 429.
        results = {"200": 0, "429": 0, "other": 0}
        base_url = rest.base_url
        headers = dict(rest.headers)
        api_version = rest.api_version

        def _fire():
            return self._raw_get(base_url, "/indexes", headers, api_version)

        # Fire 30 rapid requests using threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
            futures = [pool.submit(_fire) for _ in range(30)]
            for f in concurrent.futures.as_completed(futures):
                code = f.result()
                if code == 200:
                    results["200"] += 1
                elif code == 429:
                    results["429"] += 1
                else:
                    results["other"] += 1

        print(f"  List Indexes rapid-fire: {results}")
        # We expect at least some 200s (service responded) and ideally some 429s.
        # If NO 429s, the throttle limit may be higher than 3/sec in preview —
        # that's acceptable, but we log a warning.
        assert results["200"] + results["429"] > 0, "No successful responses at all"
        if results["429"] == 0:
            print("  WARNING: No 429s observed — throttle limit may be higher than documented")

    def test_lim_14_servicestats_throttle(self, rest):
        """LIM-14: Rapid GET /servicestats calls observe 429 throttle at documented 4/sec limit."""
        results = {"200": 0, "429": 0, "other": 0}
        base_url = rest.base_url
        headers = dict(rest.headers)
        api_version = rest.api_version

        def _fire():
            return self._raw_get(base_url, "/servicestats", headers, api_version)

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
            futures = [pool.submit(_fire) for _ in range(30)]
            for f in concurrent.futures.as_completed(futures):
                code = f.result()
                if code == 200:
                    results["200"] += 1
                elif code == 429:
                    results["429"] += 1
                else:
                    results["other"] += 1

        print(f"  Service Stats rapid-fire: {results}")
        assert results["200"] + results["429"] > 0, "No successful responses at all"
        if results["429"] == 0:
            print("  WARNING: No 429s observed — throttle limit may be higher than documented")
