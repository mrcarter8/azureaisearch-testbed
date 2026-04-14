"""
test_08_misc.py — Miscellaneous Service Operations

Tests: MSC-01 through MSC-10
"""

import pytest

from helpers.assertions import assert_field_exists, assert_status

pytestmark = [pytest.mark.misc]


class TestServiceStats:

    def test_msc_01_service_statistics(self, rest):
        """MSC-01: GET /servicestats returns counters."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        data = resp.json()
        assert "counters" in data, "No counters in servicestats"

    def test_msc_10_serverless_stats_limits(self, rest):
        """MSC-10: Serverless service stats include appropriate limits."""
        resp = rest.get("/servicestats")
        assert_status(resp, 200)
        data = resp.json()
        counters = data.get("counters", {})
        # Document count and storage should be present
        assert "documentCount" in counters or "indexCounter" in counters, (
            f"Expected counters in servicestats, got: {list(counters.keys())}"
        )


class TestAnalyzeAPI:

    def test_msc_02_analyze_standard_lucene(self, rest, primary_index_name):
        """MSC-02: Analyze API with standard.lucene returns tokens."""
        resp = rest.post(f"/indexes/{primary_index_name}/analyze", {
            "text": "luxury hotel with pool and spa",
            "analyzer": "standard.lucene",
        })
        assert_status(resp, 200)
        data = resp.json()
        tokens = data.get("tokens", [])
        assert len(tokens) > 0, "No tokens returned from analyze"

    def test_msc_03_analyze_en_microsoft(self, rest, primary_index_name):
        """MSC-03: Analyze API with en.microsoft analyzer."""
        resp = rest.post(f"/indexes/{primary_index_name}/analyze", {
            "text": "world-class gaming & fine dining",
            "analyzer": "en.microsoft",
        })
        assert_status(resp, 200)
        tokens = resp.json().get("tokens", [])
        assert len(tokens) > 0


class TestErrorHandling:

    def test_msc_04_bad_api_version(self, rest):
        """MSC-04: Bad API version returns 400."""
        resp = rest.get("/indexes", api_version="2000-01-01")
        assert_status(resp, 400)

    def test_msc_05_unsupported_api_version(self, rest):
        """MSC-05: Very old api-version returns error."""
        resp = rest.get("/indexes", api_version="2014-07-31-Preview")
        assert resp.status_code in (400, 404), f"Expected error, got {resp.status_code}"

    def test_msc_06_etag_concurrency(self, rest, primary_index_name):
        """MSC-06: PUT with stale ETag returns 412."""
        # GET current to get an ETag
        get_resp = rest.get(f"/indexes/{primary_index_name}")
        assert_status(get_resp, 200)
        body = get_resp.json()
        # Use a fake stale ETag
        resp = rest.put(
            f"/indexes/{primary_index_name}",
            body,
            extra_headers={"If-Match": '"stale-etag-value"'},
        )
        assert_status(resp, 412)

    def test_msc_07_if_none_match(self, rest, primary_index_name):
        """MSC-07: PUT with If-None-Match: * on existing index returns 412."""
        body = {
            "name": primary_index_name,
            "fields": [{"name": "HotelId", "type": "Edm.String", "key": True}],
        }
        resp = rest.put(
            f"/indexes/{primary_index_name}",
            body,
            extra_headers={"If-None-Match": "*"},
        )
        assert_status(resp, 412)

    def test_msc_08_invalid_json(self, rest, primary_index_name):
        """MSC-08: Malformed JSON body returns 400."""
        import requests as req
        url = f"{rest.base_url}/indexes/{primary_index_name}/docs/search"
        headers = {**rest.headers, "Content-Type": "application/json"}
        params = {"api-version": rest.api_version}
        # Use retry loop — raw requests bypasses RestClient retries
        import time, random
        for attempt in range(6):
            try:
                resp = req.post(url, data="{{not valid json}}", headers=headers,
                                params=params, timeout=30)
                break
            except req.exceptions.SSLError:
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt + random.uniform(0, 1))
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"

    def test_msc_09_unknown_field_in_select(self, rest, primary_index_name):
        """MSC-09: Select on nonexistent field returns error."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "select": "NonExistentField",
            "top": 1,
        })
        assert resp.status_code in (400, 404), f"Expected 400 or 404, got {resp.status_code}"


class TestIndexStatsSummary:

    @pytest.mark.xfail(reason="indexStatsSummary endpoint not available in current API version", strict=False)
    def test_msc_11_index_stats_summary(self, rest):
        """MSC-11: GET /indexStatsSummary returns per-index document counts and storage."""
        resp = rest.get("/indexStatsSummary")
        assert_status(resp, 200)
        data = resp.json()
        assert "value" in data, f"Missing 'value' in indexStatsSummary: {list(data.keys())}"
        # Each entry should have name, documentCount, storageSize
        for entry in data["value"]:
            assert "name" in entry, f"Index stats entry missing 'name': {entry}"
            assert "documentCount" in entry or "documentCounter" in entry, \
                f"Index stats entry missing document count: {list(entry.keys())}"
