"""
test_06_synonym_maps.py — Synonym Map CRUD

Tests: SYN-01 through SYN-06
"""

import pytest

from conftest import ensure_fresh
from helpers.assertions import assert_field_exists, assert_search_results, assert_status

pytestmark = [pytest.mark.synonyms]


class TestSynonymMapCRUD:

    def test_syn_01_create_synonym_map(self, rest, synonym_map_name):
        """SYN-01: Create synonym map with Solr rules."""
        body = {
            "name": synonym_map_name,
            "format": "solr",
            "synonyms": "inn, lodge, hotel\npool, swimming pool\nspa, wellness center, retreat\nfancy, luxury, upscale\nbudget, cheap, affordable\napartment => suite",
        }
        resp = rest.put(f"/synonymmaps('{synonym_map_name}')", body)
        assert_status(resp, (200, 201, 204))

    def test_syn_02_get_synonym_map(self, rest, synonym_map_name):
        """SYN-02: GET synonym map returns rules."""
        resp = rest.get(f"/synonymmaps('{synonym_map_name}')")
        assert_status(resp, 200)
        data = resp.json()
        assert_field_exists(data, "synonyms")
        assert "hotel" in data["synonyms"]

    def test_syn_03_list_synonym_maps(self, rest, synonym_map_name):
        """SYN-03: List synonym maps includes our map."""
        resp = rest.get("/synonymmaps")
        assert_status(resp, 200)
        names = [m["name"] for m in resp.json().get("value", [])]
        assert synonym_map_name in names

    def test_syn_04_update_synonym_map(self, rest, synonym_map_name):
        """SYN-04: Update synonym map with new rules."""
        body = {
            "name": synonym_map_name,
            "format": "solr",
            "synonyms": "inn, lodge, hotel\npool, swimming pool\nspa, wellness center, retreat\nfancy, luxury, upscale\nbudget, cheap, affordable\napartment => suite\nocean, sea, beach",
        }
        resp = rest.put(f"/synonymmaps('{synonym_map_name}')", body)
        assert_status(resp, (200, 204))
        # Verify
        get_resp = rest.get(f"/synonymmaps('{synonym_map_name}')")
        assert "ocean" in get_resp.json()["synonyms"]

    def test_syn_05_delete_disposable(self, rest):
        """SYN-05: Create and delete a throwaway synonym map."""
        name = "smoke-syn-throwaway"
        body = {"name": name, "format": "solr", "synonyms": "a, b, c"}
        ensure_fresh(rest, f"/synonymmaps('{name}')")
        rest.put(f"/synonymmaps('{name}')", body)
        del_resp = rest.delete(f"/synonymmaps('{name}')")
        assert_status(del_resp, 204)
        get_resp = rest.get(f"/synonymmaps('{name}')")
        assert_status(get_resp, 404)

    def test_syn_06_synonym_query_expansion(self, rest, primary_index_name):
        """SYN-06: Search 'inn' expands to match 'hotel' via synonym map."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "inn",
            "select": "HotelName, Description",
            "top": 5,
        })
        data = assert_search_results(resp, min_count=1)
        # Synonym 'inn' should expand to include 'hotel' matches
        text_blob = " ".join(
            (r.get("HotelName", "") + " " + r.get("Description", "")).lower()
            for r in data["value"]
        )
        assert "hotel" in text_blob or "inn" in text_blob or "lodge" in text_blob, (
            f"Synonym expansion for 'inn' didn't return hotel/inn/lodge-related results: "
            f"{[r.get('HotelName') for r in data['value']]}"
        )
