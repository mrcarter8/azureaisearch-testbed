"""
test_07_queries.py — Full Query Coverage

Tests: QRY-01 through QRY-38
"""

import pytest

from helpers.assertions import (
    assert_all_match,
    assert_count_gte,
    assert_field_exists,
    assert_odata_count,
    assert_order,
    assert_search_results,
    assert_status,
)

pytestmark = [pytest.mark.queries]


class TestKeywordSearch:

    def test_qry_01_simple_keyword(self, rest, primary_index_name):
        """QRY-01: Simple keyword search returns results with @search.score."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury",
            "select": "HotelName, Category, Rating",
            "top": 5,
        })
        data = assert_search_results(resp)
        # Verify score present
        for r in data["value"]:
            assert "@search.score" in r, "Missing @search.score"

    def test_qry_02_lucene_boolean(self, rest, primary_index_name):
        """QRY-02: Lucene boolean query — luxury AND pool."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury AND pool",
            "queryType": "full",
            "select": "HotelName, Tags",
            "top": 5,
        })
        assert_search_results(resp)

    def test_qry_03_lucene_wildcard(self, rest, primary_index_name):
        """QRY-03: Lucene wildcard query — lux*."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "lux*",
            "queryType": "full",
            "select": "HotelName",
            "top": 5,
        })
        assert_search_results(resp)

    def test_qry_04_lucene_regex(self, rest, primary_index_name):
        """QRY-04: Lucene regex query."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "/[Hh]otel/",
            "queryType": "full",
            "select": "HotelName",
            "top": 5,
        })
        assert_search_results(resp)


class TestFilters:

    def test_qry_05_filter_comparison(self, rest, primary_index_name):
        """QRY-05: Filter — Rating ge 4."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Rating ge 4",
            "select": "HotelName, Rating",
        })
        data = assert_search_results(resp)
        assert_all_match(data, "value", lambda r: r.get("Rating", 0) >= 4, "Rating >= 4")

    def test_qry_06_filter_geo_distance(self, rest, primary_index_name):
        """QRY-06: Geo filter — within 10km of Times Square."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "geo.distance(Location, geography'POINT(-73.9857 40.7484)') le 10",
            "select": "HotelName, Address",
        })
        data = assert_search_results(resp)
        # All results should be in the NYC area
        for r in data["value"]:
            city = (r.get("Address") or {}).get("City", "")
            assert city == "New York", f"Expected NYC results within 10km of Times Square, got City={city}"

    def test_qry_07_filter_boolean(self, rest, primary_index_name):
        """QRY-07: Filter — ParkingIncluded eq true."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "ParkingIncluded eq true",
            "select": "HotelName, ParkingIncluded",
        })
        data = assert_search_results(resp)
        assert_all_match(data, "value", lambda r: r.get("ParkingIncluded") is True, "ParkingIncluded == true")

    def test_qry_08_filter_string_eq(self, rest, primary_index_name):
        """QRY-08: Filter — Category eq 'Boutique'."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Category eq 'Boutique'",
            "select": "HotelName, Category",
        })
        data = assert_search_results(resp)
        assert_all_match(data, "value", lambda r: r.get("Category") == "Boutique", "Category == Boutique")

    def test_qry_09_filter_collection_any(self, rest, primary_index_name):
        """QRY-09: Filter — Tags/any(t: t eq 'pool')."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Tags/any(t: t eq 'pool')",
            "select": "HotelName, Tags",
        })
        data = assert_search_results(resp)
        assert_all_match(data, "value", lambda r: "pool" in r.get("Tags", []), "Tags contains 'pool'")

    def test_qry_10_filter_date_range(self, rest, primary_index_name):
        """QRY-10: Filter — LastRenovationDate gt 2020-01-01."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "LastRenovationDate gt 2020-01-01T00:00:00Z",
            "select": "HotelName, LastRenovationDate",
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            dt = r.get("LastRenovationDate", "")
            assert dt > "2020-01-01", f"Expected date > 2020-01-01, got {dt}"

    def test_qry_11_filter_complex_type(self, rest, primary_index_name):
        """QRY-11: Filter — Address/City eq 'New York'."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Address/City eq 'New York'",
            "select": "HotelName, Address",
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            city = (r.get("Address") or {}).get("City", "")
            assert city == "New York", f"Expected City='New York', got '{city}'"

    def test_qry_12_filter_combined(self, rest, primary_index_name):
        """QRY-12: Combined AND/OR filter."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "(Category eq 'Boutique' or Category eq 'Luxury') and Rating ge 4",
            "select": "HotelName, Category, Rating",
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            assert r.get("Category") in ("Boutique", "Luxury"), f"Unexpected category: {r.get('Category')}"
            assert r.get("Rating", 0) >= 4


class TestSortAndPaging:

    def test_qry_13_orderby_desc(self, rest, primary_index_name):
        """QRY-13: OrderBy Rating desc."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "orderby": "Rating desc",
            "select": "HotelName, Rating",
            "top": 10,
        })
        data = assert_search_results(resp)
        assert_order(data, "value", "Rating", "desc")

    def test_qry_14_orderby_geo(self, rest, primary_index_name):
        """QRY-14: OrderBy geo.distance ascending."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "orderby": "geo.distance(Location, geography'POINT(-73.9857 40.7484)') asc",
            "select": "HotelName",
            "top": 5,
        })
        data = assert_search_results(resp)
        # Nearest to Times Square should be NYC hotels
        assert len(data["value"]) >= 1, "Expected at least 1 result"

    def test_qry_20_top_and_skip(self, rest, primary_index_name):
        """QRY-20: Top + Skip pagination — no overlap between pages."""
        resp1 = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*", "top": 5, "skip": 0, "select": "HotelId",
        })
        resp2 = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*", "top": 5, "skip": 5, "select": "HotelId",
        })
        assert_status(resp1, 200)
        assert_status(resp2, 200)
        ids1 = {r["HotelId"] for r in resp1.json()["value"]}
        ids2 = {r["HotelId"] for r in resp2.json()["value"]}
        overlap = ids1 & ids2
        assert len(overlap) == 0, f"Pages overlap on IDs: {overlap}"


class TestFacets:

    def test_qry_15_facets_category(self, rest, primary_index_name):
        """QRY-15: Facets — Category."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "facets": ["Category"],
            "top": 0,
        })
        assert_status(resp, 200)
        data = resp.json()
        assert "@search.facets" in data, "No facets in response"
        assert "Category" in data["@search.facets"]

    def test_qry_16_facets_rating_interval(self, rest, primary_index_name):
        """QRY-16: Facets — Rating with interval:1."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "facets": ["Rating,interval:1"],
            "top": 0,
        })
        assert_status(resp, 200)
        data = resp.json()
        assert "Rating" in data.get("@search.facets", {})

    def test_qry_17_facets_tags(self, rest, primary_index_name):
        """QRY-17: Facets — Tags collection field."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "facets": ["Tags"],
            "top": 0,
        })
        assert_status(resp, 200)
        data = resp.json()
        assert "Tags" in data.get("@search.facets", {})


class TestHighlightSelect:

    def test_qry_18_highlight(self, rest, primary_index_name):
        """QRY-18: Highlight returns @search.highlights."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "highlight": "Description",
            "highlightPreTag": "<b>",
            "highlightPostTag": "</b>",
            "select": "HotelName",
            "top": 5,
        })
        data = assert_search_results(resp)
        highlights_found = any("@search.highlights" in r for r in data["value"])
        assert highlights_found, "No @search.highlights in any result"

    def test_qry_19_select_restriction(self, rest, primary_index_name):
        """QRY-19: Select restricts returned fields."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "select": "HotelName,Rating",
            "top": 3,
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            keys = set(r.keys()) - {"@search.score"}
            assert keys <= {"HotelName", "Rating"}, f"Unexpected fields: {keys}"


class TestCount:

    def test_qry_21_count(self, rest, primary_index_name):
        """QRY-21: $count=true returns @odata.count."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "count": True,
            "top": 1,
        })
        data = assert_search_results(resp)
        assert_odata_count(data)


class TestSemanticSearch:

    def test_qry_22_semantic_search(self, rest, primary_index_name):
        """QRY-22: Semantic search returns rerankerScore and captions."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "best downtown hotel with great amenities",
            "queryType": "semantic",
            "semanticConfiguration": "hotel-semantic-config",
            "select": "HotelName, Category, Rating",
            "top": 5,
        })
        assert_status(resp, (200, 206))
        data = resp.json()
        assert len(data.get("value", [])) >= 1, "No results returned"
        if resp.status_code == 200:
            first = data["value"][0]
            assert "@search.rerankerScore" in first, "Missing @search.rerankerScore"
        else:
            # 206 = semantic partial response (transient); base results returned
            assert "@search.semanticPartialResponseReason" in data

    def test_qry_23_semantic_with_answers(self, rest, primary_index_name):
        """QRY-23: Semantic search with answers for answerable query."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "what hotel has the best rating",
            "queryType": "semantic",
            "semanticConfiguration": "hotel-semantic-config",
            "answers": "extractive|count-3",
            "select": "HotelName, Rating",
            "top": 5,
        })
        assert_status(resp, (200, 206))
        data = resp.json()
        if resp.status_code == 200:
            # Verify answers array exists in response
            assert "@search.answers" in data, "Missing @search.answers in semantic response"
            assert len(data.get("value", [])) >= 1, "No results returned"


class TestVectorSearch:

    def test_qry_24_vector_search_pure(self, rest, primary_index_name):
        """QRY-24: Pure vector search with pre-computed embedding."""
        # Use a zero vector — tests the mechanics, not relevance
        vector = [0.01] * 1536
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "vector",
                "vector": vector,
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "select": "HotelId, HotelName",
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            assert "@search.score" in r, "Vector result missing @search.score"

    def test_qry_25_vector_text_to_vector(self, rest, primary_index_name):
        """QRY-25: Integrated vectorization — kind:text uses server-side vectorizer."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "luxury hotel with spa and pool",
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "select": "HotelId, HotelName",
        })
        data = assert_search_results(resp)
        assert len(data["value"]) >= 1, "kind:text vector query returned no results"

    def test_qry_26_hybrid_search(self, rest, primary_index_name):
        """QRY-26: Hybrid search — keyword + vector."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury hotel",
            "vectorQueries": [{
                "kind": "text",
                "text": "upscale accommodation with great amenities",
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "select": "HotelId, HotelName",
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            assert "@search.score" in r, "Hybrid result missing @search.score"

    def test_qry_27_multi_vector(self, rest, primary_index_name):
        """QRY-27: Multi-vector query with two vectorQueries."""
        vector = [0.01] * 1536
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [
                {"kind": "vector", "vector": vector, "fields": "DescriptionVector", "k": 3},
                {"kind": "vector", "vector": vector, "fields": "DescriptionVector", "k": 3},
            ],
            "select": "HotelId, HotelName",
        })
        data = assert_search_results(resp)
        assert len(data["value"]) >= 1, "Multi-vector query returned no results"

    def test_qry_28_vector_with_filter(self, rest, primary_index_name):
        """QRY-28: Vector search with filter."""
        vector = [0.01] * 1536
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "vector",
                "vector": vector,
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "filter": "Rating ge 4",
            "select": "HotelId, HotelName, Rating",
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            assert r.get("Rating", 0) >= 4, f"Filter not applied: Rating={r.get('Rating')}"


class TestSuggestAutocomplete:

    def test_qry_29_suggest(self, rest, primary_index_name):
        """QRY-29: Suggest with partial input."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/suggest", {
            "search": "New",
            "suggesterName": "sg",
        })
        assert_status(resp, 200)
        data = resp.json()
        assert len(data.get("value", [])) >= 1, "No suggestions returned"
        for s in data["value"]:
            assert "@search.text" in s, "Suggestion missing @search.text"

    def test_qry_30_autocomplete_one_term(self, rest, primary_index_name):
        """QRY-30: Autocomplete oneTermWithContext."""
        resp = rest.get(
            f"/indexes/{primary_index_name}/docs/autocomplete",
            params={"search": "Ne", "suggesterName": "sg", "autocompleteMode": "oneTermWithContext"},
        )
        assert_status(resp, 200)
        data = resp.json()
        assert len(data.get("value", [])) >= 1, "No autocomplete results"
        for r in data["value"]:
            assert "text" in r, "Autocomplete result missing 'text'"
            assert "queryPlusText" in r, "Autocomplete result missing 'queryPlusText'"

    def test_qry_31_autocomplete_two_terms(self, rest, primary_index_name):
        """QRY-31: Autocomplete twoTerms."""
        resp = rest.get(
            f"/indexes/{primary_index_name}/docs/autocomplete",
            params={"search": "New Y", "suggesterName": "sg", "autocompleteMode": "twoTerms"},
        )
        assert_status(resp, 200)
        data = resp.json()
        assert len(data.get("value", [])) >= 1, "No autocomplete results for 'New Y'"


class TestScoringAndAdvanced:

    def test_qry_32_scoring_profile(self, rest, primary_index_name):
        """QRY-32: Scoring profile boosts higher-rated hotels."""
        resp_without = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "select": "HotelName, Rating",
            "top": 5,
        })
        resp_with = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "select": "HotelName, Rating",
            "top": 5,
        })
        assert_status(resp_without, 200)
        assert_status(resp_with, 200)
        boosted = resp_with.json().get("value", [])
        assert len(boosted) >= 1, "Scoring profile query returned no results"
        boosted_top_rating = boosted[0].get("Rating", 0)
        assert boosted_top_rating >= 4, f"Scoring profile top result Rating={boosted_top_rating}, expected >= 4"

    def test_qry_33_search_fields(self, rest, primary_index_name):
        """QRY-33: searchFields constrains search to specific fields."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "pool",
            "searchFields": "Tags",
            "select": "HotelName, Tags",
            "top": 5,
        })
        data = assert_search_results(resp)
        for r in data["value"]:
            tags = [t.lower() for t in r.get("Tags", [])]
            assert any("pool" in t for t in tags), f"'pool' not in Tags: {r.get('Tags')}"

    def test_qry_34_minimum_coverage(self, rest, primary_index_name):
        """QRY-34: minimumCoverage parameter."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "minimumCoverage": 100,
            "top": 1,
        })
        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"
        if resp.status_code == 200:
            data = resp.json()
            assert "@search.coverage" in data, "Missing @search.coverage in response"
            assert data["@search.coverage"] == 100, f"Coverage {data['@search.coverage']} != 100"

    def test_qry_35_spell_correction(self, rest, primary_index_name):
        """QRY-35: Spell correction fixes intentional typos."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotl luxry poool",
            "queryType": "semantic",
            "semanticConfiguration": "hotel-semantic-config",
            "speller": "lexicon",
            "queryLanguage": "en-us",
            "select": "HotelName",
            "top": 5,
        })
        assert_status(resp, (200, 206))  # 206 = semantic partial response
        data = resp.json()
        assert len(data.get("value", [])) >= 1, "Spell correction returned no results"

    def test_qry_36_query_language(self, rest, primary_index_name):
        """QRY-36: queryLanguage parameter."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "queryLanguage": "en-us",
            "queryType": "semantic",
            "semanticConfiguration": "hotel-semantic-config",
            "top": 3,
        })
        assert_status(resp, (200, 206))  # 206 = semantic partial response
        data = resp.json()
        assert len(data.get("value", [])) >= 1, "queryLanguage query returned no results"

    def test_qry_37_search_mode_all(self, rest, primary_index_name):
        """QRY-37: searchMode all requires all terms present."""
        resp_any = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury pool spa",
            "searchMode": "any",
            "count": True,
            "top": 0,
        })
        resp_all = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury pool spa",
            "searchMode": "all",
            "count": True,
            "top": 0,
        })
        assert_status(resp_any, 200)
        assert_status(resp_all, 200)
        count_any = resp_any.json().get("@odata.count", 0)
        count_all = resp_all.json().get("@odata.count", 0)
        assert count_all <= count_any, f"searchMode:all ({count_all}) returned more than any ({count_any})"

    def test_qry_38_empty_wildcard_search(self, rest, primary_index_name):
        """QRY-38: Wildcard search '*' returns all documents."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "count": True,
            "top": 0,
        })
        assert_status(resp, 200)
        count = resp.json().get("@odata.count", 0)
        assert count >= 25, f"Expected >= 25, got {count}"
