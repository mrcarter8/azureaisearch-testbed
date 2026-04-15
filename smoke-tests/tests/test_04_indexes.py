"""
test_04_indexes.py — Index Management

Tests: IDX-01 through IDX-16

Gate: IDX-01 failure aborts run.
"""

import json
import os
import re

import pytest

from conftest import ensure_fresh
from helpers.assertions import (
    assert_count_gte,
    assert_field_equals,
    assert_field_exists,
    assert_status,
)

pytestmark = [pytest.mark.indexes]

_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "hotels_index_def.json")


def _load_index_template(name: str, aoai_config: dict, synonym_map_name: str | None = None) -> dict:
    """Load hotels_index_def.json, substitute placeholders, optionally wire synonym map."""
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        raw = f.read()
    replacements = {
        "{{index}}": name,
        "{{embedding_dimensions}}": str(aoai_config["embedding_dimensions"]),
        "{{aoai_endpoint}}": aoai_config["endpoint"],
        "{{aoai_embedding_deployment}}": aoai_config["embedding_deployment"],
        "{{aoai_api_key}}": aoai_config["api_key"],
        "{{aoai_embedding_model}}": aoai_config.get("embedding_model", aoai_config["embedding_deployment"]),
    }
    for placeholder, value in replacements.items():
        raw = raw.replace(placeholder, value)
    # dimensions is a string in JSON template — convert to integer
    body = json.loads(raw)
    for field in body.get("fields", []):
        if "dimensions" in field and isinstance(field["dimensions"], str):
            field["dimensions"] = int(field["dimensions"])
    # Wire synonym map onto HotelName and Description
    if synonym_map_name:
        for field in body["fields"]:
            if field["name"] in ("HotelName", "Description"):
                field["synonymMaps"] = [synonym_map_name]
    return body


class TestIndexCRUD:

    @pytest.mark.gate
    def test_idx_01_create_full_index(self, rest, primary_index_name, synonym_map_name, aoai_config):
        """IDX-01: Create full-featured index. GATE — failure aborts run."""
        # Ensure the synonym map exists before creating the index that references it
        syn_body = {
            "name": synonym_map_name,
            "format": "solr",
            "synonyms": "hotel, motel, inn\nsuites, penthouse",
        }
        rest.put(f"/synonymmaps/{synonym_map_name}", syn_body)
        body = _load_index_template(primary_index_name, aoai_config, synonym_map_name=synonym_map_name)
        resp = rest.put(f"/indexes/{primary_index_name}", body)
        assert_status(resp, (200, 201))

    def test_idx_02_get_index(self, rest, primary_index_name):
        """IDX-02: GET index returns all sections."""
        resp = rest.get(f"/indexes/{primary_index_name}")
        assert_status(resp, 200)
        data = resp.json()
        assert_field_equals(data, "name", primary_index_name)
        assert_field_exists(data, "fields")

    def test_idx_03_list_indexes(self, rest, primary_index_name):
        """IDX-03: List indexes includes our index."""
        resp = rest.get("/indexes", params={"$select": "name"})
        assert_status(resp, 200)
        names = [i["name"] for i in resp.json().get("value", [])]
        assert primary_index_name in names

    def test_idx_04_update_index_add_field(self, rest, primary_index_name):
        """IDX-04: Add a new field to existing index."""
        # GET current definition
        resp = rest.get(f"/indexes/{primary_index_name}")
        assert_status(resp, 200)
        body = resp.json()
        body["fields"].append({"name": "NewField", "type": "Edm.String", "searchable": True, "filterable": False})
        # PUT updated
        resp2 = rest.put(f"/indexes/{primary_index_name}", body)
        assert_status(resp2, (200, 204))
        # Verify
        resp3 = rest.get(f"/indexes/{primary_index_name}")
        field_names = [f["name"] for f in resp3.json()["fields"]]
        assert "NewField" in field_names

    def test_idx_05_index_statistics(self, rest, primary_index_name):
        """IDX-05: GET index statistics returns documentCount and storageSize."""
        resp = rest.get(f"/indexes/{primary_index_name}/stats")
        assert_status(resp, 200)
        data = resp.json()
        assert "documentCount" in data
        assert "storageSize" in data

    def test_idx_06_delete_disposable_index(self, rest):
        """IDX-06: Create and delete a throwaway index."""
        name = "smoke-disposable-idx"
        body = {
            "name": name,
            "fields": [{"name": "id", "type": "Edm.String", "key": True, "searchable": False}],
        }
        resp = rest.put(f"/indexes/{name}", body)
        assert_status(resp, (200, 201))
        del_resp = rest.delete(f"/indexes/{name}")
        assert_status(del_resp, 204)
        get_resp = rest.get(f"/indexes/{name}")
        assert_status(get_resp, 404)


class TestIndexRoundTrips:

    def test_idx_07_vector_config_roundtrip(self, rest, primary_index_name):
        """IDX-07: Vector config round-trips correctly."""
        resp = rest.get(f"/indexes/{primary_index_name}")
        data = resp.json()
        vs = data.get("vectorSearch", {})
        algos = vs.get("algorithms", [])
        profiles = vs.get("profiles", [])
        vectorizers = vs.get("vectorizers", [])
        assert len(algos) >= 1, "No algorithms in vectorSearch"
        assert len(profiles) >= 1, "No profiles in vectorSearch"
        assert len(vectorizers) >= 1, "No vectorizers in vectorSearch"

    def test_idx_08_semantic_config_roundtrip(self, rest, primary_index_name):
        """IDX-08: Semantic config round-trips correctly."""
        resp = rest.get(f"/indexes/{primary_index_name}")
        data = resp.json()
        sem = data.get("semantic", {})
        assert_field_exists(sem, "defaultConfiguration")
        configs = sem.get("configurations", [])
        assert len(configs) >= 1

    def test_idx_09_scoring_profile_roundtrip(self, rest, primary_index_name):
        """IDX-09: Scoring profiles round-trip correctly."""
        resp = rest.get(f"/indexes/{primary_index_name}")
        data = resp.json()
        profiles = data.get("scoringProfiles", [])
        assert len(profiles) >= 1
        names = [p["name"] for p in profiles]
        assert "boostHighRating" in names

    def test_idx_10_suggester_roundtrip(self, rest, primary_index_name):
        """IDX-10: Suggesters round-trip correctly."""
        resp = rest.get(f"/indexes/{primary_index_name}")
        data = resp.json()
        suggesters = data.get("suggesters", [])
        assert len(suggesters) >= 1
        assert suggesters[0]["name"] == "sg"

    def test_idx_11_cors_roundtrip(self, rest, primary_index_name):
        """IDX-11: CORS options round-trip correctly."""
        resp = rest.get(f"/indexes/{primary_index_name}")
        data = resp.json()
        cors = data.get("corsOptions", {})
        origins = cors.get("allowedOrigins", [])
        assert "https://smoke-test.example.com" in origins

    def test_idx_12_custom_analyzers_roundtrip(self, rest):
        """IDX-12: Custom analyzers round-trip correctly."""
        name = "smoke-custom-analyzer-idx"
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
                {"name": "content", "type": "Edm.String", "searchable": True, "analyzer": "my_custom_analyzer"},
            ],
            "analyzers": [
                {
                    "name": "my_custom_analyzer",
                    "@odata.type": "#Microsoft.Azure.Search.CustomAnalyzer",
                    "tokenizer": "standard_v2",
                    "tokenFilters": ["lowercase", "asciifolding"],
                },
            ],
        }
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert_status(resp, (200, 201))
        # Verify
        get_resp = rest.get(f"/indexes/{name}")
        analyzers = get_resp.json().get("analyzers", [])
        assert any(a["name"] == "my_custom_analyzer" for a in analyzers)


class TestIndexVariants:

    def test_idx_13_simple_index(self, rest, simple_index_name):
        """IDX-13: Create minimal index with fields only."""
        body = {
            "name": simple_index_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False, "filterable": True},
                {"name": "title", "type": "Edm.String", "searchable": True},
                {"name": "count", "type": "Edm.Int32", "filterable": True},
            ],
        }
        resp = rest.put(f"/indexes/{simple_index_name}", body)
        assert_status(resp, (200, 201))

    def test_idx_14_all_edm_types(self, rest):
        """IDX-14: Create index with every EDM type."""
        name = "smoke-all-types-idx"
        body = {
            "name": name,
            "fields": [
                {"name": "id",       "type": "Edm.String",           "key": True, "searchable": False},
                {"name": "str",      "type": "Edm.String",           "searchable": True},
                {"name": "int32",    "type": "Edm.Int32",            "filterable": True},
                {"name": "int64",    "type": "Edm.Int64",            "filterable": True},
                {"name": "dbl",      "type": "Edm.Double",           "filterable": True},
                {"name": "bool",     "type": "Edm.Boolean",          "filterable": True},
                {"name": "dt",       "type": "Edm.DateTimeOffset",   "filterable": True},
                {"name": "geo",      "type": "Edm.GeographyPoint",   "filterable": True},
                {"name": "strColl",  "type": "Collection(Edm.String)","searchable": True},
                {"name": "intColl",  "type": "Collection(Edm.Int32)", "filterable": True},
            ],
        }
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert_status(resp, (200, 201))
        # Verify all types round-trip
        get_resp = rest.get(f"/indexes/{name}")
        fields = {f["name"]: f["type"] for f in get_resp.json()["fields"]}
        assert fields["int32"] == "Edm.Int32"
        assert fields["geo"] == "Edm.GeographyPoint"


class TestIndexAliases:

    def test_idx_15_alias_quota_is_zero(self, rest):
        """IDX-15: Service has 0 alias quota — GET aliases returns empty list."""
        resp = rest.get("/aliases")
        assert_status(resp, 200)
        aliases = resp.json().get("value", [])
        assert len(aliases) == 0, f"Expected 0 aliases, got {len(aliases)}"

    def test_idx_16_alias_create_rejected_quota(self, rest, alias_name, primary_index_name):
        """IDX-16: Creating an alias is rejected with quota error."""
        body = {"name": alias_name, "indexes": [primary_index_name]}
        resp = rest.put(f"/aliases/{alias_name}", body)
        assert_status(resp, 429)
        assert "Only 0 can be created" in resp.text, (
            f"Expected quota error mentioning 'Only 0 can be created', got: {resp.text[:300]}"
        )
