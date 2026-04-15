"""
test_03_auth.py — Authentication & Authorization

Tests: SEC-01 through SEC-11

Gate: SEC-01 failure aborts the entire run.
"""

import pytest
from conftest import ensure_fresh

from helpers.assertions import assert_status, assert_status_not

pytestmark = [pytest.mark.auth]


class TestApiKeyAuth:

    @pytest.mark.gate
    def test_sec_01_admin_key_read(self, rest):
        """SEC-01: Admin API key can read indexes. GATE — failure aborts run."""
        resp = rest.get("/indexes")
        assert_status(resp, 200)

    def test_sec_02_admin_key_write(self, rest):
        """SEC-02: Admin API key can create an index."""
        idx_name = "smoke-auth-test-write"
        body = {
            "name": idx_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False}
            ],
        }
        ensure_fresh(rest, f"/indexes/{idx_name}")
        resp = rest.put(f"/indexes/{idx_name}", body)
        assert_status(resp, (200, 201))

    def test_sec_03_query_key_search_allowed(self, rest_query, rest, primary_index_name):
        """SEC-03: Query key can search."""
        resp = rest_query.post(f"/indexes/{primary_index_name}/docs/search", {"search": "*", "top": 1})
        # 200 = search succeeded; 404 = auth passed but index doesn't exist yet
        assert_status(resp, (200, 404))

    def test_sec_04_query_key_write_rejected(self, rest_query):
        """SEC-04: Query key cannot create an index (403)."""
        body = {
            "name": "smoke-query-write-test",
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False}
            ],
        }
        resp = rest_query.put("/indexes/smoke-query-write-test", body)
        assert_status(resp, (401, 403))


class TestEntraAuth:

    def test_sec_05_entra_bearer_read(self, rest_entra):
        """SEC-05: Entra bearer token can read indexes."""
        resp = rest_entra.get("/indexes")
        assert_status(resp, 200)

    def test_sec_06_entra_bearer_write(self, rest_entra):
        """SEC-06: Entra bearer token (Contributor) can create an index."""
        idx_name = "smoke-entra-write-test"
        body = {
            "name": idx_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False}
            ],
        }
        resp = rest_entra.put(f"/indexes/{idx_name}", body)
        # 200=updated, 201=created, 204=created-no-content (observed on some SKUs)
        assert_status(resp, (200, 201, 204))
        # Cleanup
        rest_entra.delete(f"/indexes/{idx_name}")


class TestNoAuth:

    def test_sec_07_no_auth_rejected(self, rest_noauth):
        """SEC-07: Request with no auth headers is rejected."""
        resp = rest_noauth.get("/indexes")
        assert_status(resp, (401, 403))

    def test_sec_08_invalid_api_key(self, search_endpoint, search_api_version):
        """SEC-08: Invalid API key is rejected."""
        from helpers.rest_client import RestClient
        bad_client = RestClient(
            base_url=search_endpoint,
            headers={"api-key": "this-is-not-a-valid-key", "Content-Type": "application/json"},
            api_version=search_api_version,
        )
        resp = bad_client.get("/indexes")
        assert_status(resp, (401, 403))

    def test_sec_09_expired_bearer_token(self, search_endpoint, search_api_version):
        """SEC-09: Expired/invalid bearer token is rejected."""
        from helpers.rest_client import RestClient
        bad_client = RestClient(
            base_url=search_endpoint,
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired.invalid",
                "Content-Type": "application/json",
            },
            api_version=search_api_version,
        )
        resp = bad_client.get("/indexes")
        assert_status(resp, (401, 403))


class TestRBAC:

    def test_sec_10_rbac_reader_search(self, rest_entra, primary_index_name):
        """SEC-10: Entra token with at least reader RBAC can search."""
        resp = rest_entra.post(f"/indexes/{primary_index_name}/docs/search", {"search": "*", "top": 1})
        # 200 = search succeeded; 404 = auth passed but index doesn't exist yet
        assert_status(resp, (200, 404))
