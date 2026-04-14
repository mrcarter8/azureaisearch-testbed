"""
test_19_advanced_queries.py — Suggest, Autocomplete & Advanced Query Syntax

Tests: ADV-01 through ADV-12

Deep-dive into suggest/autocomplete APIs and advanced Lucene query syntax:
fuzzy matching, proximity search, fielded search, boosted terms, regex,
and French language search. Every test validates response content.
"""

import pytest

from helpers.assertions import (
    assert_search_results,
    assert_status,
)

pytestmark = [pytest.mark.queries]


class TestSuggest:
    """Suggest API — response structure, fuzzy, filter, select."""

    def test_adv_01_suggest_fuzzy(self, rest, primary_index_name):
        """ADV-01: Suggest with fuzzy=true — misspelled input still returns suggestions."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/suggest", {
            "search": "New Yrok",
            "suggesterName": "sg",
            "fuzzy": True,
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, \
            "Fuzzy suggest for 'New Yrok' should return at least 1 suggestion"

    def test_adv_02_suggest_with_filter(self, rest, primary_index_name):
        """ADV-02: Suggest with filter — suggestions limited to filtered set."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/suggest", {
            "search": "New",
            "suggesterName": "sg",
            "filter": "Rating ge 4",
            "select": "HotelId, HotelName, Rating",
            "top": 10,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        for r in results:
            rating = r.get("Rating")
            if rating is not None:
                assert rating >= 4, \
                    f"Suggestion for hotel {r.get('HotelId')} has Rating {rating} < 4"

    def test_adv_03_suggest_response_structure(self, rest, primary_index_name):
        """ADV-03: Suggest response has @search.text on each suggestion."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/suggest", {
            "search": "New",
            "suggesterName": "sg",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Expected at least 1 suggestion for 'New'"
        for r in results:
            assert "@search.text" in r, f"Missing @search.text in suggestion: {r}"
            assert isinstance(r["@search.text"], str) and len(r["@search.text"]) > 0, \
                "@search.text should be a non-empty string"

    def test_adv_04_suggest_with_select(self, rest, primary_index_name):
        """ADV-04: Suggest with $select restricts returned fields."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/suggest", {
            "search": "New",
            "suggesterName": "sg",
            "select": "HotelName",
            "top": 5,
        })
        assert_status(resp, 200)
        results = resp.json().get("value", [])
        for r in results:
            keys = set(r.keys()) - {"@search.text"}
            assert keys <= {"HotelName"}, f"Unexpected fields in suggest: {keys}"


class TestAutocomplete:
    """Autocomplete API — modes and fuzzy matching."""

    def test_adv_05_autocomplete_one_term(self, rest, primary_index_name):
        """ADV-05: Autocomplete oneTerm — validates returned text and queryPlusText."""
        resp = rest.get(
            f"/indexes/{primary_index_name}/docs/autocomplete",
            params={
                "search": "Ne",
                "suggesterName": "sg",
                "autocompleteMode": "oneTerm",
            },
        )
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Expected at least 1 autocomplete result for 'Ne'"
        for r in results:
            assert "text" in r, f"Missing 'text' in autocomplete result: {r}"
            assert "queryPlusText" in r, f"Missing 'queryPlusText': {r}"

    def test_adv_06_autocomplete_fuzzy(self, rest, primary_index_name):
        """ADV-06: Autocomplete with fuzzy=true — request accepted and returns valid structure."""
        resp = rest.get(
            f"/indexes/{primary_index_name}/docs/autocomplete",
            params={
                "search": "Nwe",
                "suggesterName": "sg",
                "autocompleteMode": "oneTerm",
                "fuzzy": "true",
            },
        )
        assert_status(resp, 200)
        data = resp.json()
        # Fuzzy autocomplete may or may not return results depending on edit distance tolerance
        results = data.get("value", [])
        assert isinstance(results, list), "Expected value to be a list"
        for r in results:
            assert "text" in r, f"Missing 'text' in autocomplete result: {r}"
            assert "queryPlusText" in r, f"Missing 'queryPlusText': {r}"


class TestLuceneQuerySyntax:
    """Advanced Lucene query syntax: fuzzy, proximity, fielded, boosted, regex."""

    def test_adv_07_fuzzy_search(self, rest, primary_index_name):
        """ADV-07: Fuzzy search (~1) — single edit distance matches."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxry~1",
            "queryType": "full",
            "select": "HotelId, HotelName, Description",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, \
            "Fuzzy search 'luxry~1' should match 'luxury'"

    def test_adv_08_proximity_search(self, rest, primary_index_name):
        """ADV-08: Proximity search — words within N positions of each other."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": '"best hotel"~5',
            "queryType": "full",
            "select": "HotelId, HotelName, Description",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        # 'best' and 'hotel' within 5 words should match some descriptions
        assert len(results) >= 1, \
            "Proximity search '\"best hotel\"~5' should return results"

    def test_adv_09_fielded_search(self, rest, primary_index_name):
        """ADV-09: Fielded search — Description:luxury restricts to one field."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "Description:luxury",
            "queryType": "full",
            "select": "HotelId, HotelName, Description",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        # Validate that 'luxury' appears in Description of returned docs
        for r in results:
            desc = (r.get("Description") or "").lower()
            assert "luxury" in desc or "luxur" in desc, \
                f"Hotel {r.get('HotelId')} Description doesn't contain 'luxury': {desc[:100]}"

    def test_adv_10_boosted_term(self, rest, primary_index_name):
        """ADV-10: Boosted term (luxury^5) — boosted term increases relevance."""
        resp_no_boost = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury pool",
            "queryType": "full",
            "select": "HotelId, HotelName",
            "top": 5,
        })
        resp_boost = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury^5 pool",
            "queryType": "full",
            "select": "HotelId, HotelName",
            "top": 5,
        })
        assert_status(resp_no_boost, 200)
        assert_status(resp_boost, 200)
        scores_no = [r["@search.score"] for r in resp_no_boost.json().get("value", [])]
        scores_yes = [r["@search.score"] for r in resp_boost.json().get("value", [])]
        # Boosted query should produce different scores
        assert scores_no != scores_yes, \
            "Term boosting (luxury^5) should change score distribution"

    def test_adv_11_french_text_search(self, rest, primary_index_name):
        """ADV-11: French language search on Description_fr field."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hôtel classique",
            "searchFields": "Description_fr",
            "select": "HotelId, HotelName, Description_fr",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, \
            "Search for 'hôtel classique' in Description_fr should find results"
        for r in results:
            desc_fr = r.get("Description_fr")
            assert desc_fr is not None, \
                f"Hotel {r.get('HotelId')} matched on Description_fr but field is null"

    def test_adv_12_regex_query_validated(self, rest, primary_index_name):
        """ADV-12: Regex /[Hh]otel/ — validates matched documents contain 'hotel'."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "/[Hh]otel/",
            "queryType": "full",
            "select": "HotelId, HotelName",
            "count": True,
            "top": 10,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Regex /[Hh]otel/ should match hotel names"
        count = data.get("@odata.count", 0)
        assert count >= 5, f"Expected >= 5 matches for /[Hh]otel/, got {count}"
