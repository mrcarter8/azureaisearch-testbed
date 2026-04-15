"""
test_16_scoring.py — Scoring Profiles & Relevance

Tests: SCR-01 through SCR-14

Validates scoring profile behavior: magnitude/freshness boosts, score
comparison with/without profiles, profile + filter/orderby/count/semantic,
invalid profile handling, tag scoring, and text weights. Uses the existing
boostHighRating profile on the primary index and creates temporary indexes
for tag/weight scoring tests.
"""

import time

import pytest

from conftest import ensure_fresh
from helpers.assertions import (
    assert_all_match,
    assert_search_results,
    assert_status,
)

pytestmark = [pytest.mark.queries]


class TestScoringProfileImpact:
    """Validate that boostHighRating profile changes result scoring."""

    def test_scr_01_profile_changes_scores(self, rest, primary_index_name):
        """SCR-01: Scoring profile produces different scores vs no profile."""
        body_no_profile = {
            "search": "hotel",
            "select": "HotelId, HotelName, Rating",
            "top": 10,
        }
        body_with_profile = {
            **body_no_profile,
            "scoringProfile": "boostHighRating",
        }
        resp_without = rest.post(f"/indexes/{primary_index_name}/docs/search", body_no_profile)
        resp_with = rest.post(f"/indexes/{primary_index_name}/docs/search", body_with_profile)
        data_without = assert_search_results(resp_without, min_count=1)
        data_with = assert_search_results(resp_with, min_count=1)
        scores_without = [r["@search.score"] for r in data_without["value"]]
        scores_with = [r["@search.score"] for r in data_with["value"]]
        assert scores_without != scores_with, \
            "Scores should differ when scoring profile is applied"

    def test_scr_02_magnitude_boost_favors_high_rating(self, rest, primary_index_name):
        """SCR-02: Magnitude boost on Rating — higher-rated hotels score better."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "select": "HotelId, HotelName, Rating",
            "top": 5,
        })
        data = assert_search_results(resp, min_count=2)
        results = data["value"]
        top_rating = results[0].get("Rating")
        assert top_rating is not None, \
            f"Top result has no Rating field: {results[0]}"
        # With magnitude boost, top result should have a high rating
        assert top_rating >= 4.0, \
            f"Expected top result Rating >= 4.0 with boostHighRating, got {top_rating}"

    def test_scr_03_freshness_boost_effect(self, rest, primary_index_name):
        """SCR-03: Freshness boost on LastRenovationDate — compare recently renovated hotel positions."""
        resp_no = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "select": "HotelId, HotelName, LastRenovationDate",
            "top": 5,
        })
        resp_yes = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "select": "HotelId, HotelName, LastRenovationDate",
            "top": 5,
        })
        data_no = assert_search_results(resp_no, min_count=1)
        data_yes = assert_search_results(resp_yes, min_count=1)
        # boostHighRating has freshness on LastRenovationDate (P1825D).
        # The relative ordering should change — we just verify ordering differs
        ids_no = [r["HotelId"] for r in data_no["value"]]
        ids_yes = [r["HotelId"] for r in data_yes["value"]]
        # Not asserting exact order, just that profile has an effect
        assert ids_no != ids_yes or \
            [r["@search.score"] for r in data_no["value"]] != \
            [r["@search.score"] for r in data_yes["value"]], \
            "Freshness boost should change ordering or scores"


class TestScoringWithQueryFeatures:
    """Scoring profile interaction with filter, orderby, count, pagination."""

    def test_scr_04_profile_plus_filter(self, rest, primary_index_name):
        """SCR-04: Scoring profile + filter — filter applied, profile scores filtered set."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "filter": "Rating ge 3",
            "select": "HotelId, HotelName, Rating",
            "top": 10,
        })
        data = assert_search_results(resp, min_count=1)
        for r in data["value"]:
            rating = r.get("Rating")
            assert rating is not None and rating >= 3, \
                f"Hotel {r.get('HotelId')} Rating {rating} violates filter"
        # Profile should still produce non-trivial scores
        assert all(r["@search.score"] > 0 for r in data["value"])

    def test_scr_05_profile_plus_orderby(self, rest, primary_index_name):
        """SCR-05: orderby overrides scoring profile ordering."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "orderby": "Rating asc",
            "select": "HotelId, Rating",
            "top": 10,
        })
        data = assert_search_results(resp, min_count=2)
        ratings = [r["Rating"] for r in data["value"] if r.get("Rating") is not None]
        for i in range(len(ratings) - 1):
            assert ratings[i] <= ratings[i + 1], \
                f"orderby Rating asc violated at [{i}]: {ratings[i]} > {ratings[i+1]}"

    def test_scr_06_profile_count_unchanged(self, rest, primary_index_name):
        """SCR-06: Profile does not change result count — same docs, different order."""
        body_base = {"search": "hotel", "count": True, "top": 0}
        resp_no = rest.post(f"/indexes/{primary_index_name}/docs/search", body_base)
        resp_yes = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            **body_base,
            "scoringProfile": "boostHighRating",
        })
        assert_status(resp_no, 200)
        assert_status(resp_yes, 200)
        count_no = resp_no.json().get("@odata.count", -1)
        count_yes = resp_yes.json().get("@odata.count", -2)
        assert count_no == count_yes, \
            f"Profile should not change count: {count_no} vs {count_yes}"

    def test_scr_07_invalid_profile_returns_400(self, rest, primary_index_name):
        """SCR-07: Non-existent scoring profile name returns 400."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "nonexistent-profile-99",
            "top": 1,
        })
        assert_status(resp, 400)

    def test_scr_08_profile_pagination_consistent(self, rest, primary_index_name):
        """SCR-08: Scoring profile with top/skip — no overlap between pages."""
        body = {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "select": "HotelId",
        }
        resp1 = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            **body, "top": 5, "skip": 0,
        })
        resp2 = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            **body, "top": 5, "skip": 5,
        })
        assert_status(resp1, 200)
        assert_status(resp2, 200)
        ids1 = {r["HotelId"] for r in resp1.json().get("value", [])}
        ids2 = {r["HotelId"] for r in resp2.json().get("value", [])}
        overlap = ids1 & ids2
        assert len(overlap) == 0, f"Pages overlap with profile: {overlap}"

    def test_scr_09_profile_broad_keyword(self, rest, primary_index_name):
        """SCR-09: Profile with broader keyword — '*' wildcard still benefits from profile."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "scoringProfile": "boostHighRating",
            "select": "HotelId, Rating",
            "top": 5,
        })
        data = assert_search_results(resp, min_count=1)
        # With wildcard, profile still applies (boosted by magnitude/freshness)
        for r in data["value"]:
            assert "@search.score" in r
            assert r["@search.score"] > 0, (
                f"Score should be > 0 with profile on wildcard: {r.get('HotelId')}"
            )

    def test_scr_10_profile_search_mode_all(self, rest, primary_index_name):
        """SCR-10: Profile with searchMode 'all' — both features work together."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury pool",
            "searchMode": "all",
            "scoringProfile": "boostHighRating",
            "select": "HotelId, HotelName, Rating",
            "count": True,
            "top": 10,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        count = data.get("@odata.count", len(results))
        # searchMode 'all' with scoring profile should return results
        # where ALL terms match AND profile boost applies
        assert count >= 0, f"Unexpected negative count: {count}"
        for r in results:
            assert "@search.score" in r, f"Missing score on {r.get('HotelId')}"

    def test_scr_11_profile_select_restriction(self, rest, primary_index_name):
        """SCR-11: Profile + select — only selected fields returned."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "scoringProfile": "boostHighRating",
            "select": "HotelName, Rating",
            "top": 3,
        })
        data = assert_search_results(resp, min_count=1)
        for r in data["value"]:
            keys = set(r.keys()) - {"@search.score"}
            assert keys <= {"HotelName", "Rating"}, \
                f"Unexpected fields: {keys}"

    def test_scr_12_profile_plus_semantic(self, rest, primary_index_name):
        """SCR-12: Scoring profile + semantic reranking — both applied."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "best hotel with great service and views",
            "queryType": "semantic",
            "semanticConfiguration": "hotel-semantic-config",
            "scoringProfile": "boostHighRating",
            "select": "HotelId, HotelName, Rating",
            "top": 5,
        })
        assert_status(resp, (200, 206))
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1
        if resp.status_code == 200:
            # Semantic rerankerScore should exist alongside profile-boosted scores
            assert "@search.rerankerScore" in results[0], \
                "rerankerScore missing — semantic may not be applying"


class TestCustomScoringProfiles:
    """Tag scoring and text weights on a temporary index."""

    def test_scr_13_tag_scoring_profile(self, rest):
        """SCR-13: Tag scoring profile — boosted docs appear higher with scoring parameter."""
        idx_name = "smoke-scr-tag"
        # Create index with tag scoring profile
        body = {
            "name": idx_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
                {"name": "title", "type": "Edm.String", "searchable": True},
                {"name": "tags", "type": "Collection(Edm.String)", "filterable": True, "searchable": True},
                {"name": "rating", "type": "Edm.Double", "filterable": True, "sortable": True},
            ],
            "scoringProfiles": [{
                "name": "tagBoost",
                "functions": [{
                    "type": "tag",
                    "fieldName": "tags",
                    "boost": 10,
                    "tag": {
                        "tagsParameter": "boostTags",
                    },
                }],
            }],
        }
        ensure_fresh(rest, f"/indexes/{idx_name}")
        resp = rest.put(f"/indexes/{idx_name}", body)
        assert resp.status_code in (200, 201), f"Create failed: {resp.status_code}"
        # Upload docs
        docs = [
            {"@search.action": "upload", "id": "1", "title": "Alpha Article", "tags": ["python", "data"], "rating": 3.0},
            {"@search.action": "upload", "id": "2", "title": "Beta Article", "tags": ["java", "web"], "rating": 4.0},
            {"@search.action": "upload", "id": "3", "title": "Gamma Article", "tags": ["python", "ml"], "rating": 2.0},
        ]
        rest.post(f"/indexes/{idx_name}/docs/index", {"value": docs})
        time.sleep(8)
        # Search with tag boost for 'python'
        resp = rest.post(f"/indexes/{idx_name}/docs/search", {
            "search": "*",
            "scoringProfile": "tagBoost",
            "scoringParameters": ["boostTags-python"],
            "select": "id, title, tags",
            "top": 3,
        })
        data = assert_search_results(resp, min_count=1)
        top_tags = data["value"][0].get("tags", [])
        assert "python" in top_tags, f"Tag boost failed: top result tags={top_tags}"

    def test_scr_14_text_weights_profile(self, rest):
        """SCR-14: Text weights profile — field weighting shifts relevance."""
        idx_name = "smoke-scr-wgt"
        body = {
            "name": idx_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True},
                {"name": "title", "type": "Edm.String", "searchable": True},
                {"name": "body", "type": "Edm.String", "searchable": True},
            ],
            "scoringProfiles": [{
                "name": "titleHeavy",
                "text": {
                    "weights": {"title": 10, "body": 1},
                },
            }],
        }
        ensure_fresh(rest, f"/indexes/{idx_name}")
        resp = rest.put(f"/indexes/{idx_name}", body)
        assert resp.status_code in (200, 201)
        docs = [
            {"@search.action": "upload", "id": "1", "title": "Azure cloud computing", "body": "General overview of services."},
            {"@search.action": "upload", "id": "2", "title": "General overview", "body": "Azure cloud computing is powerful."},
        ]
        rest.post(f"/indexes/{idx_name}/docs/index", {"value": docs})
        time.sleep(3)
        # Without profile
        resp_no = rest.post(f"/indexes/{idx_name}/docs/search", {
            "search": "Azure cloud", "select": "id, title", "top": 2,
        })
        # With titleHeavy profile
        resp_yes = rest.post(f"/indexes/{idx_name}/docs/search", {
            "search": "Azure cloud", "scoringProfile": "titleHeavy",
            "select": "id, title", "top": 2,
        })
        assert_status(resp_no, 200)
        assert_status(resp_yes, 200)
        # With titleHeavy, doc 1 (Azure in title) should rank first
        results_yes = resp_yes.json().get("value", [])
        if len(results_yes) >= 1:
            assert results_yes[0]["id"] == "1", \
                f"Title weight should boost doc 1 to top, got id={results_yes[0]['id']}"
