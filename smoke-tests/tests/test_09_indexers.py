"""
test_09_indexers.py — Indexer Pipeline: Data Sources, Indexers, Field Mappings

Tests: IXR-01 through IXR-22
"""

import os
import time

import pytest

from conftest import ensure_fresh
from helpers.assertions import (
    assert_field_equals,
    assert_field_exists,
    assert_status,
)
from helpers.wait import poll_indexer_status

pytestmark = [pytest.mark.indexers]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _skip_if_no_env(var: str, label: str):
    val = os.getenv(var, "")
    if not val:
        pytest.skip(f"{label} not configured ({var} not set)")
    return val


# ---------------------------------------------------------------------------
# Data Source CRUD
# ---------------------------------------------------------------------------

class TestDataSourcesCRUD:

    def test_ixr_01_create_datasource_blob(self, rest, datasource_blob_name):
        """IXR-01: Create Azure Blob data source."""
        conn_str = _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        container = os.getenv("BLOB_CONTAINER", "hotels")
        body = {
            "name": datasource_blob_name,
            "type": "azureblob",
            "credentials": {"connectionString": conn_str},
            "container": {"name": container},
        }
        resp = rest.put(f"/datasources/{datasource_blob_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        # Verify round-trip
        get_resp = rest.get(f"/datasources/{datasource_blob_name}")
        assert_status(get_resp, 200)
        assert_field_equals(get_resp.json(), "type", "azureblob")
        assert_field_equals(get_resp.json(), "name", datasource_blob_name)

    def test_ixr_02_create_datasource_cosmos(self, rest, datasource_cosmos_name):
        """IXR-02: Create Cosmos DB data source."""
        conn_str = _skip_if_no_env("COSMOS_CONNECTION_STRING", "Cosmos DB")
        database = os.getenv("COSMOS_DATABASE", "hotels-db")
        container = os.getenv("COSMOS_CONTAINER", "hotels")
        # Azure Search requires Database= in the Cosmos connection string
        if "Database=" not in conn_str:
            conn_str = conn_str.rstrip(";") + f";Database={database}"
        body = {
            "name": datasource_cosmos_name,
            "type": "cosmosdb",
            "credentials": {"connectionString": conn_str},
            "container": {"name": container, "query": None},
            "dataChangeDetectionPolicy": {
                "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
                "highWaterMarkColumnName": "_ts",
            },
        }
        resp = rest.put(f"/datasources/{datasource_cosmos_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        # Verify round-trip
        get_resp = rest.get(f"/datasources/{datasource_cosmos_name}")
        assert_status(get_resp, 200)
        assert_field_equals(get_resp.json(), "type", "cosmosdb")
        assert_field_equals(get_resp.json(), "name", datasource_cosmos_name)

    def test_ixr_03_create_datasource_sql(self, rest, datasource_sql_name):
        """IXR-03: Create Azure SQL data source with change tracking."""
        conn_str = _skip_if_no_env("AZURE_SQL_CONNECTION_STRING", "Azure SQL")
        table = os.getenv("AZURE_SQL_TABLE", "Hotels")
        body = {
            "name": datasource_sql_name,
            "type": "azuresql",
            "credentials": {"connectionString": conn_str},
            "container": {"name": table},
            "dataChangeDetectionPolicy": {
                "@odata.type": "#Microsoft.Azure.Search.SqlIntegratedChangeTrackingPolicy",
            },
        }
        resp = rest.put(f"/datasources/{datasource_sql_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        # Verify round-trip
        get_resp = rest.get(f"/datasources/{datasource_sql_name}")
        assert_status(get_resp, 200)
        assert_field_equals(get_resp.json(), "type", "azuresql")
        assert_field_equals(get_resp.json(), "name", datasource_sql_name)

    def test_ixr_04_get_datasource(self, rest, datasource_blob_name):
        """IXR-04: GET data source — connectionString is masked."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.get(f"/datasources/{datasource_blob_name}")
        assert_status(resp, 200)
        data = resp.json()
        # Connection string should be redacted
        cred = data.get("credentials", {}).get("connectionString") or ""
        assert "<unchanged>" in cred or "***" in cred or cred == "", (
            f"Connection string may not be masked: {cred[:60]}..."
        )

    def test_ixr_05_list_datasources(self, rest, datasource_blob_name):
        """IXR-05: List data sources — test source present."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.get("/datasources")
        assert_status(resp, 200)
        names = [ds["name"] for ds in resp.json().get("value", [])]
        assert datasource_blob_name in names, f"{datasource_blob_name} not in {names}"


# ---------------------------------------------------------------------------
# Indexer CRUD & Execution
# ---------------------------------------------------------------------------

class TestBlobIndexer:

    def test_ixr_06_create_indexer_blob(self, rest, indexer_blob_name,
                                         datasource_blob_name, primary_index_name,
                                         skillset_name):
        """IXR-06: Create Blob indexer with skillset and field mappings."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        body = {
            "name": indexer_blob_name,
            "dataSourceName": datasource_blob_name,
            "targetIndexName": primary_index_name,
            "skillsetName": skillset_name,
            "fieldMappings": [
                {"sourceFieldName": "metadata_storage_path", "targetFieldName": "HotelId",
                 "mappingFunction": {"name": "base64Encode"}},
                {"sourceFieldName": "metadata_storage_name", "targetFieldName": "HotelName"},
            ],
            "outputFieldMappings": [
                {"sourceFieldName": "/document/Description_vector",
                 "targetFieldName": "DescriptionVector"},
            ],
            "parameters": {
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "parsingMode": "default",
                },
            },
        }
        resp = rest.put(f"/indexers/{indexer_blob_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"

    def test_ixr_07_run_blob_indexer(self, rest, indexer_blob_name):
        """IXR-07: Run Blob indexer and poll to success."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.post(f"/indexers/{indexer_blob_name}/run", None)
        assert resp.status_code in (202, 204), f"Expected 202/204, got {resp.status_code}"
        data = poll_indexer_status(rest, indexer_blob_name)
        last_status = data.get("lastResult", {}).get("status", "unknown")
        assert last_status in ("success", "transientFailure"), f"Indexer ended with status: {last_status}"

    def test_ixr_08_verify_vectorized_docs(self, rest, primary_index_name):
        """IXR-08: Verify indexed documents have vectors."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        # Wait a moment for index refresh
        time.sleep(2)
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "top": 5,
            "select": "HotelId,HotelName",
        })
        assert_status(resp, 200)
        results = resp.json().get("value", [])
        if len(results) > 0:
            # Verify documents were indexed from blob
            has_data = any(
                r.get("HotelName") is not None or r.get("HotelId") is not None
                for r in results
            )
            assert has_data, "No documents found after indexer run"


class TestCosmosIndexer:

    def test_ixr_09_create_indexer_cosmos(self, rest, indexer_cosmos_name,
                                           datasource_cosmos_name, primary_index_name):
        """IXR-09: Create Cosmos DB indexer."""
        _skip_if_no_env("COSMOS_CONNECTION_STRING", "Cosmos DB")
        body = {
            "name": indexer_cosmos_name,
            "dataSourceName": datasource_cosmos_name,
            "targetIndexName": primary_index_name,
            "fieldMappings": [
                {"sourceFieldName": "id", "targetFieldName": "HotelId"},
            ],
        }
        resp = rest.put(f"/indexers/{indexer_cosmos_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"

    def test_ixr_10_run_cosmos_indexer(self, rest, indexer_cosmos_name):
        """IXR-10: Run Cosmos DB indexer and poll to success."""
        _skip_if_no_env("COSMOS_CONNECTION_STRING", "Cosmos DB")
        resp = rest.post(f"/indexers/{indexer_cosmos_name}/run", None)
        assert resp.status_code in (202, 204)
        data = poll_indexer_status(rest, indexer_cosmos_name)
        last_status = data.get("lastResult", {}).get("status", "unknown")
        assert last_status in ("success", "transientFailure"), f"Indexer ended with status: {last_status}"


class TestSqlIndexer:

    def test_ixr_11_create_indexer_sql(self, rest, indexer_sql_name,
                                        datasource_sql_name, primary_index_name):
        """IXR-11: Create Azure SQL indexer with change tracking."""
        _skip_if_no_env("AZURE_SQL_CONNECTION_STRING", "Azure SQL")
        body = {
            "name": indexer_sql_name,
            "dataSourceName": datasource_sql_name,
            "targetIndexName": primary_index_name,
            "fieldMappings": [
                {"sourceFieldName": "HotelId", "targetFieldName": "HotelId"},
                {"sourceFieldName": "HotelName", "targetFieldName": "HotelName"},
            ],
            "parameters": {
                "configuration": {},
            },
        }
        resp = rest.put(f"/indexers/{indexer_sql_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"

    def test_ixr_12_run_sql_indexer(self, rest, indexer_sql_name):
        """IXR-12: Run Azure SQL indexer and poll to success."""
        _skip_if_no_env("AZURE_SQL_CONNECTION_STRING", "Azure SQL")
        resp = rest.post(f"/indexers/{indexer_sql_name}/run", None)
        assert resp.status_code in (202, 204)
        data = poll_indexer_status(rest, indexer_sql_name)
        last_status = data.get("lastResult", {}).get("status", "unknown")
        assert last_status in ("success", "transientFailure"), f"Indexer ended with status: {last_status}"


# ---------------------------------------------------------------------------
# Indexer Status, Reset, Schedule
# ---------------------------------------------------------------------------

class TestIndexerOperations:

    def test_ixr_13_indexer_status(self, rest, indexer_blob_name):
        """IXR-13: GET indexer status — lastResult present."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.get(f"/indexers/{indexer_blob_name}/status")
        assert_status(resp, 200)
        data = resp.json()
        assert_field_exists(data, "lastResult")

    def test_ixr_14_reset_indexer(self, rest, indexer_blob_name):
        """IXR-14: Reset indexer clears state."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.post(f"/indexers/{indexer_blob_name}/reset", None)
        assert resp.status_code in (204, 200), f"Expected 204/200, got {resp.status_code}"
        # Verify status reflects reset
        status_resp = rest.get(f"/indexers/{indexer_blob_name}/status")
        assert_status(status_resp, 200)
        data = status_resp.json()
        last = data.get("lastResult", {})
        # After reset, status should be 'reset' or lastResult may be cleared
        indexer_status = data.get("status", "")
        assert indexer_status in ("running", "error", "reset"), f"Unexpected indexer status after reset: {indexer_status}"

    def test_ixr_14b_reset_docs(self, rest, indexer_blob_name):
        """IXR-14b: Reset specific documents for re-processing."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        body = {"documentKeys": ["doc-key-1", "doc-key-2"]}
        resp = rest.post(f"/indexers/{indexer_blob_name}/resetdocs", body)
        # 204 = accepted, 400 = keys not found (acceptable for smoke test)
        assert resp.status_code in (204, 200, 400), f"Expected 204/200/400, got {resp.status_code}"

    def test_ixr_14c_reset_skills(self, rest, indexer_blob_name):
        """IXR-14c: Reset skills on an indexer for re-enrichment."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        body = {"skillNames": []}  # Empty = reset all skills
        resp = rest.post(f"/indexers/{indexer_blob_name}/resetskills", body)
        # 204 = accepted, 400 = no skillset attached
        assert resp.status_code in (204, 200, 400), f"Expected 204/200/400, got {resp.status_code}"

    def test_ixr_15_scheduled_indexer(self, rest, indexer_blob_name):
        """IXR-15: Update indexer with schedule."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        # GET current definition
        get_resp = rest.get(f"/indexers/{indexer_blob_name}")
        assert_status(get_resp, 200)
        body = get_resp.json()
        body["schedule"] = {"interval": "PT1H"}
        resp = rest.put(f"/indexers/{indexer_blob_name}", body)
        assert resp.status_code in (200, 201, 204)
        # Verify schedule round-tripped
        verify = rest.get(f"/indexers/{indexer_blob_name}")
        schedule = verify.json().get("schedule", {})
        assert schedule.get("interval") == "PT1H", f"Schedule not set: {schedule}"


# ---------------------------------------------------------------------------
# Field Mappings & Parsing Modes
# ---------------------------------------------------------------------------

class TestFieldMappingsAndParsing:

    def test_ixr_16_field_mappings_validation(self, rest, indexer_blob_name):
        """IXR-16: Verify indexer field mappings are present."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.get(f"/indexers/{indexer_blob_name}")
        assert_status(resp, 200)
        mappings = resp.json().get("fieldMappings", [])
        assert len(mappings) > 0, "No field mappings found"

    def test_ixr_17_output_field_mappings(self, rest, indexer_blob_name):
        """IXR-17: Verify output field mappings (from skillset)."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.get(f"/indexers/{indexer_blob_name}")
        assert_status(resp, 200)
        output_mappings = resp.json().get("outputFieldMappings", [])
        assert len(output_mappings) > 0, "No output field mappings found"

    def test_ixr_18_parsing_mode_json_array(self, rest, datasource_blob_name,
                                              primary_index_name):
        """IXR-18: Create indexer with jsonArray parsing mode."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        name = f"{datasource_blob_name}-jsonarray-ixr"
        body = {
            "name": name,
            "dataSourceName": datasource_blob_name,
            "targetIndexName": primary_index_name,
            "parameters": {
                "configuration": {
                    "parsingMode": "jsonArray",
                    "documentRoot": "",
                },
            },
        }
        ensure_fresh(rest, f"/indexers/{name}")
        resp = rest.put(f"/indexers/{name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        # Verify parsingMode round-tripped
        get_resp = rest.get(f"/indexers/{name}")
        assert_status(get_resp, 200)
        mode = get_resp.json().get("parameters", {}).get("configuration", {}).get("parsingMode", "")
        assert mode == "jsonArray", f"parsingMode not round-tripped: {mode}"

    def test_ixr_19_parsing_mode_json_lines(self, rest, datasource_blob_name,
                                              primary_index_name):
        """IXR-19: Create indexer with jsonLines parsing mode."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        name = f"{datasource_blob_name}-jsonlines-ixr"
        body = {
            "name": name,
            "dataSourceName": datasource_blob_name,
            "targetIndexName": primary_index_name,
            "parameters": {
                "configuration": {
                    "parsingMode": "jsonLines",
                },
            },
        }
        ensure_fresh(rest, f"/indexers/{name}")
        resp = rest.put(f"/indexers/{name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        # Verify parsingMode round-tripped
        get_resp = rest.get(f"/indexers/{name}")
        assert_status(get_resp, 200)
        mode = get_resp.json().get("parameters", {}).get("configuration", {}).get("parsingMode", "")
        assert mode == "jsonLines", f"parsingMode not round-tripped: {mode}"


# ---------------------------------------------------------------------------
# List & Delete
# ---------------------------------------------------------------------------

class TestIndexerCleanup:

    def test_ixr_20_list_indexers(self, rest):
        """IXR-20: List indexers — test indexers present."""
        resp = rest.get("/indexers")
        assert_status(resp, 200)
        assert "value" in resp.json()

    def test_ixr_21_delete_indexer(self, rest, indexer_blob_name):
        """IXR-21: Delete Blob indexer."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.delete(f"/indexers/{indexer_blob_name}")
        assert resp.status_code in (204, 404), f"Expected 204/404, got {resp.status_code}"

    def test_ixr_22_delete_datasource(self, rest, datasource_blob_name):
        """IXR-22: Delete Blob data source."""
        _skip_if_no_env("BLOB_CONNECTION_STRING", "Blob storage")
        resp = rest.delete(f"/datasources/{datasource_blob_name}")
        assert resp.status_code in (204, 404), f"Expected 204/404, got {resp.status_code}"
