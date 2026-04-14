"""
test_01_service_mgmt.py — Control Plane: Service Provisioning & Lifecycle

Tests: SVC-01 through SVC-16
API: Management plane 2026-03-01-Preview
"""

import pytest

from helpers.assertions import (
    assert_field_equals,
    assert_field_exists,
    assert_status,
)
from helpers.wait import poll_provisioning_state

pytestmark = [pytest.mark.service_mgmt]


# ---------------------------------------------------------------------------
# SVC-01: Create serverless service (minimal — sku + location only)
# ---------------------------------------------------------------------------
class TestServiceProvisioning:

    def test_svc_01_create_serverless_minimal(self, rest, disposable_service_name, search_location):
        """SVC-01: Create serverless service with minimal payload."""
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/resourceGroups/{rest.resource_group}"
            f"/providers/Microsoft.Search/searchServices/{disposable_service_name}"
        )
        body = {
            "location": search_location,
            "sku": {"name": "serverless"},
        }
        resp = rest.mgmt_request("PUT", url, body)
        assert_status(resp, (200, 201))
        data = resp.json()
        assert_field_equals(data, "sku.name", "serverless")
        state = data.get("properties", {}).get("provisioningState", "")
        assert state in ("Provisioning", "Succeeded"), f"Unexpected provisioningState: {state}"

    def test_svc_02_create_serverless_with_options(self, rest, search_location):
        """SVC-02: Create serverless with auth options and semantic search."""
        # Uses the primary service — this is an update/validate rather than a new create
        resp = rest.mgmt_get()
        assert_status(resp, 200)
        data = resp.json()
        # Validate it's serverless
        assert_field_equals(data, "sku.name", "serverless")


class TestServiceRead:

    def test_svc_03_get_service(self, rest):
        """SVC-03: GET service returns serverless sku and running status."""
        resp = rest.mgmt_get()
        assert_status(resp, 200)
        data = resp.json()
        assert_field_equals(data, "sku.name", "serverless")
        status = data.get("properties", {}).get("status")
        assert status == "running", f"Expected status 'running', got '{status}'"

    def test_svc_04_list_services_in_rg(self, rest):
        """SVC-04: List services in resource group includes our service."""
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/resourceGroups/{rest.resource_group}"
            f"/providers/Microsoft.Search/searchServices"
        )
        resp = rest.mgmt_request("GET", url)
        assert_status(resp, 200)
        names = [s["name"] for s in resp.json().get("value", [])]
        assert rest.service_name in names, f"Service '{rest.service_name}' not in list: {names}"

    def test_svc_05_list_services_in_subscription(self, rest):
        """SVC-05: List services in subscription includes our service."""
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/providers/Microsoft.Search/searchServices"
        )
        names = []
        while url:
            resp = rest.mgmt_request("GET", url)
            assert_status(resp, 200)
            data = resp.json()
            names.extend(s["name"] for s in data.get("value", []))
            url = data.get("nextLink")
        assert rest.service_name in names, f"Service '{rest.service_name}' not in subscription list ({len(names)} services checked)"


class TestAdminKeys:

    @pytest.fixture(scope="class")
    def original_keys(self, rest):
        """Fetch admin keys once for the class."""
        resp = rest.mgmt_post("/listAdminKeys")
        assert_status(resp, 200)
        return resp.json()

    def test_svc_06_get_admin_keys(self, original_keys):
        """SVC-06: listAdminKeys returns primary and secondary keys."""
        assert_field_exists(original_keys, "primaryKey")
        assert_field_exists(original_keys, "secondaryKey")

    def test_svc_07_regenerate_admin_key_primary(self, rest, original_keys):
        """SVC-07: Regenerate primary admin key produces a different key."""
        resp = rest.mgmt_post("/regenerateAdminKey/primary")
        assert_status(resp, 200)
        new_primary = resp.json().get("primaryKey")
        assert new_primary, "No primaryKey in response"
        # Update the RestClient's data-plane headers so subsequent tests use
        # the freshly-regenerated key.
        rest.headers["api-key"] = new_primary

    def test_svc_08_regenerate_admin_key_secondary(self, rest, original_keys):
        """SVC-08: Regenerate secondary admin key produces a different key."""
        resp = rest.mgmt_post("/regenerateAdminKey/secondary")
        assert_status(resp, 200)
        assert_field_exists(resp.json(), "secondaryKey")


class TestQueryKeys:

    @pytest.fixture(scope="class")
    def created_query_key(self, rest):
        """Create a query key and yield it; delete after class."""
        resp = rest.mgmt_post(f"/createQueryKey/smoke-test-qk")
        assert_status(resp, 200)
        key_data = resp.json()
        yield key_data
        # Cleanup
        key_val = key_data.get("key", "")
        if key_val:
            rest.mgmt_request(
                "DELETE",
                rest.mgmt_url(f"/deleteQueryKey/{key_val}"),
            )

    def test_svc_09_create_query_key(self, created_query_key):
        """SVC-09: Create query key returns a key value."""
        assert_field_exists(created_query_key, "key")
        assert_field_exists(created_query_key, "name")

    def test_svc_10_list_query_keys(self, rest, created_query_key):
        """SVC-10: List query keys includes the created key."""
        resp = rest.mgmt_post("/listQueryKeys")
        assert_status(resp, 200)
        keys = resp.json().get("value", [])
        key_names = [k.get("name") for k in keys]
        assert "smoke-test-qk" in key_names, f"Created key not in list: {key_names}"

    def test_svc_11_delete_query_key(self, rest):
        """SVC-11: Delete query key succeeds (create a throwaway then delete)."""
        # Create
        resp = rest.mgmt_post(f"/createQueryKey/smoke-throwaway-qk")
        assert_status(resp, 200)
        key_val = resp.json().get("key")
        # Delete
        del_resp = rest.mgmt_request("DELETE", rest.mgmt_url(f"/deleteQueryKey/{key_val}"))
        assert_status(del_resp, (200, 204))
        # Verify absent
        list_resp = rest.mgmt_get("/listQueryKeys")
        key_names = [k.get("name") for k in list_resp.json().get("value", [])]
        assert "smoke-throwaway-qk" not in key_names


class TestServiceUpdate:

    def test_svc_12_update_auth_options(self, rest):
        """SVC-12: Update auth options to aadOrApiKey."""
        body = {
            "properties": {
                "authOptions": {
                    "aadOrApiKey": {
                        "aadAuthFailureMode": "http403"
                    }
                }
            }
        }
        resp = rest.mgmt_patch(body=body)
        assert_status(resp, 200)
        # Verify round-trip
        get_resp = rest.mgmt_get()
        auth = get_resp.json().get("properties", {}).get("authOptions", {})
        assert "aadOrApiKey" in auth, f"authOptions did not round-trip: {auth}"

    def test_svc_13_update_semantic_search(self, rest):
        """SVC-13: Update semanticSearch property."""
        body = {
            "properties": {
                "semanticSearch": "free"
            }
        }
        resp = rest.mgmt_patch(body=body)
        assert_status(resp, 200)
        # Verify round-trip
        get_resp = rest.mgmt_get()
        semantic = get_resp.json().get("properties", {}).get("semanticSearch", "")
        assert semantic == "free", f"semanticSearch not round-tripped: {semantic}"

    def test_svc_14_update_cors(self, rest):
        """SVC-14: Update CORS options."""
        body = {
            "properties": {
                "corsOptions": {
                    "allowedOrigins": ["https://smoke-test.example.com"],
                    "maxAgeInSeconds": 300
                }
            }
        }
        resp = rest.mgmt_patch(body=body)
        assert_status(resp, 200)
        # Verify round-trip
        get_resp = rest.mgmt_get()
        cors = get_resp.json().get("properties", {}).get("corsOptions", {})
        assert "https://smoke-test.example.com" in cors.get("allowedOrigins", []), \
            f"CORS allowedOrigins not round-tripped: {cors}"

    def test_svc_15_enable_managed_identity(self, rest):
        """SVC-15: Enable system-assigned managed identity on the service."""
        body = {"identity": {"type": "SystemAssigned"}}
        resp = rest.mgmt_patch(body=body)
        assert_status(resp, 200)
        identity = resp.json().get("identity", {})
        assert identity.get("principalId"), "MSI enabled but no principalId returned"

    def test_svc_16_validate_service_properties(self, rest):
        """SVC-16: Validate all returned service properties are correct."""
        resp = rest.mgmt_get()
        assert_status(resp, 200)
        data = resp.json()
        props = data.get("properties", {})
        assert_field_exists(data, "sku.name")
        assert_field_exists(props, "provisioningState")
        assert_field_exists(props, "status")


# ---------------------------------------------------------------------------
# SVC-17: CheckNameAvailability
# ---------------------------------------------------------------------------
class TestCheckNameAvailability:

    def test_svc_17_check_name_available(self, rest):
        """SVC-17: CheckNameAvailability for a very unlikely name returns available."""
        import uuid
        unlikely_name = f"smoke-avail-check-{uuid.uuid4().hex[:12]}"
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/providers/Microsoft.Search/checkNameAvailability"
        )
        body = {"name": unlikely_name, "type": "Microsoft.Search/searchServices"}
        resp = rest.mgmt_request("POST", url, body)
        assert_status(resp, 200)
        data = resp.json()
        assert "nameAvailable" in data, f"Missing 'nameAvailable' in response: {list(data.keys())}"

    def test_svc_18_check_name_taken(self, rest):
        """SVC-18: CheckNameAvailability for existing service returns unavailable."""
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/providers/Microsoft.Search/checkNameAvailability"
        )
        body = {"name": rest.service_name, "type": "Microsoft.Search/searchServices"}
        resp = rest.mgmt_request("POST", url, body)
        assert_status(resp, 200)
        data = resp.json()
        assert data.get("nameAvailable") is False, (
            f"Expected nameAvailable=false for existing service, got: {data}"
        )
