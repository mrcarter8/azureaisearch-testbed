"""
test_15_filters.py — Advanced OData Filter Tests

Tests: FLT-01 through FLT-20

Deep-dive into OData filter expressions: search.in(), collection operators
(any/all), double-nested lambdas, null comparisons, not() precedence,
search.ismatch/search.ismatchscoring, and combined filter+search scenarios.
Every test validates filter correctness by inspecting returned documents.
"""

import pytest

from helpers.assertions import (
    assert_all_match,
    assert_count_gte,
    assert_odata_count,
    assert_order,
    assert_search_results,
    assert_status,
)

pytestmark = [pytest.mark.queries]


class TestSearchInFunction:
    """Tests for the search.in() OData function."""

    def test_flt_01_search_in_comma_delimiter(self, rest, primary_index_name):
        """FLT-01: search.in() with comma delimiter matches exact categories."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "search.in(Category, 'Luxury,Boutique', ',')",
            "select": "HotelId, HotelName, Category",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        assert_all_match(data, "value",
            lambda r: r.get("Category") in ("Luxury", "Boutique"),
            "Category in (Luxury, Boutique)")
        count = data.get("@odata.count", 0)
        assert count >= 2, f"Expected at least 2 hotels, got {count}"

    def test_flt_02_search_in_pipe_delimiter(self, rest, primary_index_name):
        """FLT-02: search.in() with pipe delimiter on Category field."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "search.in(Category, 'Luxury|Suite', '|')",
            "select": "HotelId, Category",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        assert_all_match(data, "value",
            lambda r: r.get("Category") in ("Luxury", "Suite"),
            "Category in (Luxury, Suite)")


class TestCollectionFilters:
    """Tests for collection operators: any(), all(), nested lambdas."""

    def test_flt_03_rooms_any_baserate(self, rest, primary_index_name):
        """FLT-03: Rooms/any(r: r/BaseRate lt 200) — nested lambda on complex collection."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Rooms/any(r: r/BaseRate lt 200)",
            "select": "HotelId, HotelName, Rooms",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rooms = doc.get("Rooms", [])
            assert any(r.get("BaseRate", 999) < 200 for r in rooms), \
                f"Hotel {doc.get('HotelId')} has no room with BaseRate < 200: " \
                f"{[r.get('BaseRate') for r in rooms]}"

    def test_flt_04_rooms_all_non_smoking(self, rest, primary_index_name):
        """FLT-04: Rooms/all(r: not r/SmokingAllowed) — all operator, includes empty collections."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Rooms/all(r: not r/SmokingAllowed)",
            "select": "HotelId, HotelName, Rooms",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rooms = doc.get("Rooms") or []
            for room in rooms:
                assert room.get("SmokingAllowed") is not True, \
                    f"Hotel {doc.get('HotelId')} has smoking room: {room.get('Description')}"

    def test_flt_05_double_nested_any(self, rest, primary_index_name):
        """FLT-05: Rooms/any(r: r/Tags/any(t: t eq 'suite')) — double-nested lambda."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Rooms/any(r: r/Tags/any(t: t eq 'suite'))",
            "select": "HotelId, HotelName, Rooms",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rooms = doc.get("Rooms", [])
            found = any("suite" in (r.get("Tags") or []) for r in rooms)
            assert found, \
                f"Hotel {doc.get('HotelId')} has no room with 'suite' tag"

    def test_flt_06_not_rooms_any(self, rest, primary_index_name):
        """FLT-06: not Rooms/any() — documents with empty/null Rooms collection."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "not Rooms/any()",
            "select": "HotelId, HotelName, Rooms",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rooms = doc.get("Rooms") or []
            assert len(rooms) == 0, \
                f"Hotel {doc.get('HotelId')} has {len(rooms)} rooms, expected 0"
        # Hotels 6-10 have empty Rooms in our dataset
        assert_count_gte(data, "value", 1)

    def test_flt_07_search_in_collection(self, rest, primary_index_name):
        """FLT-07: Tags/any(t: search.in(t, 'pool,spa', ',')) — search.in on collection."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Tags/any(t: search.in(t, 'pool,spa', ','))",
            "select": "HotelId, HotelName, Tags",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            tags = doc.get("Tags") or []
            assert "pool" in tags or "spa" in tags, \
                f"Hotel {doc.get('HotelId')} Tags {tags} has neither 'pool' nor 'spa'"


class TestComparisonOperators:
    """Tests for ne, not(), range, and null comparisons."""

    def test_flt_08_ne_operator(self, rest, primary_index_name):
        """FLT-08: Category ne 'Boutique' — excludes Boutique, validates all results."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Category ne 'Boutique'",
            "select": "HotelId, Category",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        assert_all_match(data, "value",
            lambda r: r.get("Category") != "Boutique",
            "Category != Boutique")

    def test_flt_09_not_with_precedence(self, rest, primary_index_name):
        """FLT-09: not (Rating gt 4) — parenthesized negation, equivalent to Rating le 4 or null."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "not (Rating gt 4)",
            "select": "HotelId, HotelName, Rating",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rating = doc.get("Rating")
            if rating is not None:
                assert rating <= 4, \
                    f"Hotel {doc.get('HotelId')} Rating {rating} should be <= 4"

    def test_flt_10_range_filter(self, rest, primary_index_name):
        """FLT-10: Rating ge 2 and Rating le 3 — bounded range filter."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Rating ge 2 and Rating le 3",
            "select": "HotelId, HotelName, Rating",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rating = doc.get("Rating")
            assert rating is not None and 2 <= rating <= 3, \
                f"Hotel {doc.get('HotelId')} Rating {rating} not in [2, 3]"

    def test_flt_11_not_null_comparison(self, rest, primary_index_name):
        """FLT-11: ParkingIncluded ne null — only docs with parking info."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "ParkingIncluded ne null",
            "select": "HotelId, HotelName, ParkingIncluded",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            assert doc.get("ParkingIncluded") is not None, \
                f"Hotel {doc.get('HotelId')} has null ParkingIncluded"


class TestGeoFilter:
    """geo.distance with result validation."""

    def test_flt_12_geo_distance_validated(self, rest, primary_index_name):
        """FLT-12: geo.distance le 5km from Times Square — only NYC hotels returned."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "geo.distance(Location, geography'POINT(-73.9857 40.7484)') le 5",
            "select": "HotelId, HotelName, Address/City",
            "count": True,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        for doc in results:
            city = (doc.get("Address") or {}).get("City", "")
            assert city == "New York", \
                f"Hotel {doc.get('HotelId')} ({doc.get('HotelName')}) city={city}, expected New York"


class TestSearchMatchFunctions:
    """search.ismatch and search.ismatchscoring in $filter."""

    def test_flt_13_search_ismatch(self, rest, primary_index_name):
        """FLT-13: search.ismatch('luxury', 'Description') as filter predicate."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "search.ismatch('luxury', 'Description')",
            "select": "HotelId, HotelName, Description",
            "count": True,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Expected at least 1 match for 'luxury' in Description"

    def test_flt_14_search_ismatchscoring(self, rest, primary_index_name):
        """FLT-14: search.ismatchscoring combined with Rating filter — scoring contribution."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "search.ismatchscoring('luxury amenities') and Rating ge 3",
            "select": "HotelId, HotelName, Rating",
            "count": True,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        for doc in results:
            rating = doc.get("Rating")
            assert rating is not None and rating >= 3, \
                f"Hotel {doc.get('HotelId')} Rating {rating} should be >= 3"
            assert "@search.score" in doc, \
                f"Hotel {doc.get('HotelId')} missing @search.score"
            assert doc["@search.score"] > 0, \
                f"Hotel {doc.get('HotelId')} @search.score should be > 0"


class TestComplexTypeFilters:
    """Filters on complex type sub-fields."""

    def test_flt_15_complex_type_eq(self, rest, primary_index_name):
        """FLT-15: Address/StateProvince eq 'NY' — complex type field equality."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Address/StateProvince eq 'NY'",
            "select": "HotelId, HotelName, Address",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            state = (doc.get("Address") or {}).get("StateProvince")
            assert state == "NY", \
                f"Hotel {doc.get('HotelId')} StateProvince={state}, expected NY"

    def test_flt_16_chained_complex_type(self, rest, primary_index_name):
        """FLT-16: Address/Country eq 'USA' and Address/City ne 'New York' — chained complex."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Address/Country eq 'USA' and Address/City ne 'New York'",
            "select": "HotelId, HotelName, Address",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            addr = doc.get("Address") or {}
            assert addr.get("Country") == "USA", \
                f"Hotel {doc.get('HotelId')} Country={addr.get('Country')}"
            assert addr.get("City") != "New York", \
                f"Hotel {doc.get('HotelId')} City should not be New York"


class TestDateAndBooleanFilters:
    """Date range and boolean filter validation."""

    def test_flt_17_date_range(self, rest, primary_index_name):
        """FLT-17: LastRenovationDate in [2019, 2021) — date range filter validated."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "LastRenovationDate ge 2019-01-01T00:00:00Z and LastRenovationDate lt 2021-01-01T00:00:00Z",
            "select": "HotelId, HotelName, LastRenovationDate",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            dt_str = doc.get("LastRenovationDate", "")
            assert dt_str >= "2019-01-01" and dt_str < "2021-01-01", \
                f"Hotel {doc.get('HotelId')} date {dt_str} not in [2019, 2021)"

    def test_flt_18_boolean_with_count(self, rest, primary_index_name):
        """FLT-18: ParkingIncluded eq true — boolean correctness with $count cross-check."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "ParkingIncluded eq true",
            "select": "HotelId, HotelName, ParkingIncluded",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        assert_all_match(data, "value",
            lambda r: r.get("ParkingIncluded") is True,
            "ParkingIncluded == true")
        # Cross-check: count of parking-true plus parking-false/null should equal total
        count_true = data.get("@odata.count", 0)
        resp_false = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "ParkingIncluded ne true",
            "count": True,
            "top": 0,
        })
        assert_status(resp_false, 200)
        count_not_true = resp_false.json().get("@odata.count", 0)
        resp_all = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "count": True,
            "top": 0,
        })
        assert_status(resp_all, 200)
        count_all = resp_all.json().get("@odata.count", 0)
        assert count_true + count_not_true == count_all, \
            f"ParkingIncluded=true ({count_true}) + ne true ({count_not_true}) != total ({count_all})"


class TestCombinedFilterScenarios:
    """Filter combined with orderby, search, etc."""

    def test_flt_19_filter_plus_orderby(self, rest, primary_index_name):
        """FLT-19: Filter Category eq 'Luxury' with orderby Rating desc — both validated."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "Category eq 'Luxury'",
            "orderby": "Rating desc",
            "select": "HotelId, HotelName, Category, Rating",
        })
        data = assert_search_results(resp, min_count=1)
        assert_all_match(data, "value",
            lambda r: r.get("Category") == "Luxury",
            "Category == Luxury")
        assert_order(data, "value", "Rating", "desc")

    def test_flt_20_filter_plus_search(self, rest, primary_index_name):
        """FLT-20: Keyword search 'hotel' combined with filter Rating ge 4."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "filter": "Rating ge 4",
            "select": "HotelId, HotelName, Rating",
            "count": True,
        })
        data = assert_search_results(resp, min_count=1)
        for doc in data["value"]:
            rating = doc.get("Rating")
            assert rating is not None and rating >= 4, \
                f"Hotel {doc.get('HotelId')} Rating {rating} should be >= 4"
        # Keyword search contributes to scoring
        for doc in data["value"]:
            assert "@search.score" in doc and doc["@search.score"] > 0, \
                f"Hotel {doc.get('HotelId')} should have positive @search.score"
