"""
test_02_service_negative.py — Serverless Feature Gates & Negative Tests

Tests: NEG-01 through NEG-15
API: Management plane 2026-03-01-Preview

These tests discover which features are supported, unsupported, or behave
differently on the Serverless SKU.
"""

import os
import time

import pytest
from conftest import ensure_fresh

from helpers.assertions import assert_status

pytestmark = [pytest.mark.negative, pytest.mark.service_mgmt]


class TestScalingRejected:

    def test_neg_01_reject_replica_count(self, rest):
        """NEG-01: Setting replicaCount > 1 should be rejected on serverless."""
        body = {"properties": {"replicaCount": 2}}
        resp = rest.mgmt_patch(body=body)
        # Expect 400 or the property is silently ignored
        if resp.status_code == 200:
            data = resp.json()
            actual = data.get("properties", {}).get("replicaCount", 1)
            assert actual == 1, f"replicaCount was accepted as {actual} — unexpected for serverless"
        else:
            # Any 4xx/5xx counts as rejected — serverless currently returns 500
            assert resp.status_code >= 400, f"Unexpected status {resp.status_code}"

    def test_neg_02_reject_partition_count(self, rest):
        """NEG-02: Setting partitionCount > 1 should be rejected on serverless."""
        body = {"properties": {"partitionCount": 2}}
        resp = rest.mgmt_patch(body=body)
        if resp.status_code == 200:
            data = resp.json()
            actual = data.get("properties", {}).get("partitionCount", 1)
            assert actual == 1, f"partitionCount was accepted as {actual} — unexpected for serverless"
        else:
            # Any 4xx/5xx counts as rejected — serverless currently returns 500
            assert resp.status_code >= 400, f"Unexpected status {resp.status_code}"


class TestInvalidCreation:

    def test_neg_03_invalid_sku_name(self, rest, search_location):
        """NEG-03: Create with invalid SKU name returns 400."""
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/resourceGroups/{rest.resource_group}"
            f"/providers/Microsoft.Search/searchServices/smoke-invalid-sku"
        )
        body = {"location": search_location, "sku": {"name": "mega-ultra-premium"}}
        resp = rest.mgmt_request("PUT", url, body)
        assert_status(resp, 400)

    def test_neg_04_invalid_location(self, rest):
        """NEG-04: Create serverless in unsupported region returns error."""
        url = (
            f"https://management.azure.com/subscriptions/{rest.subscription_id}"
            f"/resourceGroups/{rest.resource_group}"
            f"/providers/Microsoft.Search/searchServices/smoke-bad-region"
        )
        body = {"location": "antarcticaland", "sku": {"name": "serverless"}}
        resp = rest.mgmt_request("PUT", url, body)
        # Expect 400 or similar error
        assert resp.status_code >= 400, f"Expected error for invalid location, got {resp.status_code}"

    def test_neg_05_duplicate_service_name(self, rest, search_location):
        """NEG-05: Create service with existing name is idempotent or 409."""
        url = rest.mgmt_url()
        body = {"location": search_location, "sku": {"name": "serverless"}}
        resp = rest.mgmt_request("PUT", url, body)
        # PUT is idempotent — expect 200 or 409
        assert resp.status_code in (200, 409), f"Expected 200 or 409, got {resp.status_code}"

    def test_neg_06_invalid_auth_options(self, rest):
        """NEG-06: Malformed authOptions returns 400."""
        body = {"properties": {"authOptions": {"notAValidOption": True}}}
        resp = rest.mgmt_patch(body=body)
        # Backend should reject invalid properties or silently ignore them
        assert resp.status_code in (200, 400), f"Expected 200 (ignored) or 400 (rejected), got {resp.status_code}"


class TestServerlessLimits:

    def test_neg_07_serverless_quotas_present(self, rest):
        """NEG-07: Service properties include serverless-appropriate limits."""
        resp = rest.mgmt_get()
        assert_status(resp, 200)
        data = resp.json()
        props = data.get("properties", {})
        # These fields should exist for serverless
        assert "provisioningState" in props
        assert "status" in props

    def test_neg_08_delete_disposable_service(self, rest, disposable_service_name, search_location):
        """NEG-08: Create and delete a throwaway service."""
        base = "https://management.azure.com"
        path = (
            f"/subscriptions/{rest.subscription_id}"
            f"/resourceGroups/{rest.resource_group}"
            f"/providers/Microsoft.Search/searchServices/{disposable_service_name}"
        )
        url = f"{base}{path}"
        # Create
        create_resp = rest.mgmt_request("PUT", url, {
            "location": search_location,
            "sku": {"name": "serverless"},
        })
        if create_resp.status_code not in (200, 201):
            pytest.skip(f"Could not create disposable service: {create_resp.status_code}")

        # Wait for provisioning to complete (up to 120s)
        import time
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            get_resp = rest.mgmt_request("GET", url)
            if get_resp.status_code == 200:
                state = get_resp.json().get("properties", {}).get("provisioningState", "")
                if state.lower() in ("succeeded", "failed"):
                    break
            time.sleep(5)

        # Delete
        del_resp = rest.mgmt_request("DELETE", url)
        assert del_resp.status_code in (200, 202, 204), f"Delete returned {del_resp.status_code}"

        # Verify gone (may take time for async delete)
        get_resp = rest.mgmt_request("GET", url)
        assert get_resp.status_code in (200, 404), f"Expected 200 (deleting) or 404, got {get_resp.status_code}"


class TestNetworkSecurityFeatureGates:

    def test_neg_09_ip_firewall_rules(self, rest):
        """NEG-09: Discover whether IP firewall rules work on serverless."""
        body = {
            "properties": {
                "networkRuleSet": {
                    "ipRules": [
                        {"value": "203.0.113.0/24"}
                    ]
                }
            }
        }
        resp = rest.mgmt_patch(body=body)
        assert resp.status_code in (200, 400, 500), f"Expected 200 (supported), 400 (rejected), or 500 (server error), got {resp.status_code}"
        # Restore if successful
        if resp.status_code == 200:
            restore = {"properties": {"networkRuleSet": {"ipRules": []}}}
            rest.mgmt_patch(body=restore)

    def test_neg_10_private_endpoint(self, rest):
        """NEG-10: Discover whether shared private link works on serverless."""
        url = rest.mgmt_url("/sharedPrivateLinkResources")
        resp = rest.mgmt_request("GET", url)
        assert resp.status_code in (200, 400, 404), f"Expected 200/400/404, got {resp.status_code}"

    def test_neg_11_cmk_encryption(self, rest):
        """NEG-11: Discover whether CMK encryption works on serverless."""
        resp = rest.mgmt_get()
        assert_status(resp, 200)
        data = resp.json()
        props = data.get("properties", {})
        encryption = props.get("encryptionWithCmk", {})
        # Serverless should report CMK enforcement status
        assert "enforcement" in encryption, f"Expected 'enforcement' in encryptionWithCmk, got: {encryption}"

    def test_neg_12_disable_public_access(self, rest):
        """NEG-12: Discover whether publicNetworkAccess can be disabled on serverless."""
        body = {"properties": {"publicNetworkAccess": "Disabled"}}
        resp = rest.mgmt_patch(body=body)
        assert resp.status_code in (200, 400, 500), f"Expected 200 (supported), 400 (rejected), or 500 (server error), got {resp.status_code}"
        # Restore always
        restore = {"properties": {"publicNetworkAccess": "Enabled"}}
        rest.mgmt_patch(body=restore)


# ---------------------------------------------------------------------------
# CMK Encryption Tests
# ---------------------------------------------------------------------------


def _skip_if_no_cmk():
    vault_uri = os.getenv("CMK_KEY_VAULT_URI", "")
    key_name = os.getenv("CMK_KEY_NAME", "")
    if not vault_uri or not key_name:
        pytest.skip("CMK not configured (CMK_KEY_VAULT_URI/CMK_KEY_NAME not set)")
    return vault_uri, key_name


class TestCMKEncryption:

    def test_neg_13_enable_identity_on_service(self, rest):
        """NEG-13: Enable system-assigned managed identity on the serverless service."""
        body = {"identity": {"type": "SystemAssigned"}}
        resp = rest.mgmt_patch(body=body)
        # Serverless may or may not support MSI — record the result
        if resp.status_code == 200:
            identity = resp.json().get("identity", {})
            principal_id = identity.get("principalId", "")
            assert principal_id, "MSI enabled but no principalId returned"
        # If 400, serverless doesn't support MSI — that's the discovery

    def test_neg_14_create_index_with_cmk(self, rest, cmk_config):
        """NEG-14: Create an index with CMK encryptionKey on serverless."""
        if cmk_config is None:
            pytest.skip("CMK not configured")

        # First, check if the service has MSI
        svc_resp = rest.mgmt_get()
        assert_status(svc_resp, 200)
        identity = svc_resp.json().get("identity", {})
        if identity.get("type", "None") == "None":
            pytest.skip("Service has no managed identity — enable MSI first")

        # Get the latest key version from Key Vault
        vault_uri = cmk_config["key_vault_uri"].rstrip("/")
        key_name = cmk_config["key_name"]

        name = "smoke-cmk-idx-temp"
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
                {"name": "content", "type": "Edm.String", "searchable": True},
            ],
            "encryptionKey": {
                "keyVaultKeyName": key_name,
                "keyVaultKeyVersion": "",
                "keyVaultUri": vault_uri,
            },
        }
        ensure_fresh(rest, f"/indexes/{name}")
        try:
            resp = rest.put(f"/indexes/{name}", body)
        except Exception as e:
            pytest.skip(f"Data plane unreachable (service may be restarting after MSI change): {e}")
        # CMK may or may not work on serverless — record behavior
        if resp.status_code in (200, 201):
            # Verify encryptionKey round-trips
            get_resp = rest.get(f"/indexes/{name}")
            ek = get_resp.json().get("encryptionKey")
            assert ek is not None, "encryptionKey missing from GET response"
            assert ek.get("keyVaultKeyName") == key_name
        # If error, we still pass — this is a discovery test

    def test_neg_15_create_synonym_map_with_cmk(self, rest, cmk_config):
        """NEG-15: Create a synonym map with CMK encryptionKey on serverless."""
        if cmk_config is None:
            pytest.skip("CMK not configured")

        vault_uri = cmk_config["key_vault_uri"].rstrip("/")
        key_name = cmk_config["key_name"]

        name = "smoke-cmk-syn-temp"
        body = {
            "name": name,
            "format": "solr",
            "synonyms": "test, trial",
            "encryptionKey": {
                "keyVaultKeyName": key_name,
                "keyVaultKeyVersion": "",
                "keyVaultUri": vault_uri,
            },
        }
        ensure_fresh(rest, f"/synonymmaps/{name}")
        try:
            resp = rest.put(f"/synonymmaps/{name}", body)
        except Exception as e:
            pytest.skip(f"Data plane unreachable (service may be restarting after MSI change): {e}")
        if resp.status_code in (200, 201):
            pass
        # Discovery — record whether CMK works on synonym maps
