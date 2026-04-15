"""
test_17_semantic.py — Semantic Search Deep-Dive

Tests: SEM-01 through SEM-12

Comprehensive semantic search validation: rerankerScore ordering, extractive
answers/captions structure, French language, filter+semantic combo, orderby
override, maxTextRecallSize, speller, count, highlight, and pagination.
206 is treated as a failure — it means the semantic ranker did not run.
"""

import pytest

from helpers.assertions import (
    assert_count_gte,
    assert_field_exists,
    assert_odata_count,
    assert_order,
    assert_search_results,
    assert_status,
)

pytestmark = [pytest.mark.queries]

SEMANTIC_CONFIG = "hotel-semantic-config"


class TestSemanticReranking:
    """Core semantic reranking behavior."""

    def test_sem_01_reranker_score_ordering(self, rest, primary_index_name):
        """SEM-01: Semantic results sorted by @search.rerankerScore descending."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "best luxury hotel with amazing views and great service",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "select": "HotelId, HotelName, Category",
            "top": 10,
        })
        assert_status(resp, 200)
        results = data.get("value", [])
        assert len(results) >= 1, "No results returned"
        # All results must have @search.rerankerScore
        scores = []
        for r in results:
            assert "@search.rerankerScore" in r, \
                f"Hotel {r.get('HotelId')} missing @search.rerankerScore"
            scores.append(r["@search.rerankerScore"])
        # Scores must be in descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"rerankerScore not descending at [{i}]: {scores[i]} < {scores[i+1]}"


class TestExtractiveFeatures:
    """Extractive answers and captions."""

    def test_sem_02_extractive_answers(self, rest, primary_index_name):
        """SEM-02: Semantic answers — @search.answers array with key, text, score."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "which hotel is located in the heart of downtown",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "answers": "extractive|count-3",
            "select": "HotelId, HotelName",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        # Answers should be returned for a pointed question on a small corpus
        answers = data.get("@search.answers", [])
        assert len(answers) >= 1, (
            f"Expected at least 1 semantic answer for a pointed question, "
            f"got {len(answers)}. Keys in response: {list(data.keys())}"
        )
        for ans in answers:
            assert "key" in ans, "Answer missing 'key'"
            assert "text" in ans, "Answer missing 'text'"
            assert "score" in ans, "Answer missing 'score'"
            assert ans["score"] >= 0, f"Answer score negative: {ans['score']}"
            assert len(ans["text"]) > 0, "Answer 'text' is empty"

    def test_sem_03_extractive_captions(self, rest, primary_index_name):
        """SEM-03: Semantic captions — @search.captions on each result."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel with great culinary experience",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "captions": "extractive|highlight-true",
            "select": "HotelId, HotelName",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "No results returned"
        # At least some results should have captions
        captions_found = 0
        for r in results:
            if "@search.captions" in r:
                captions_found += 1
                for cap in r["@search.captions"]:
                    assert "text" in cap, "Caption missing 'text'"
        assert captions_found >= 1, "No results had @search.captions"

    def test_sem_04_answers_and_captions_combined(self, rest, primary_index_name):
        """SEM-04: Both answers and captions requested simultaneously."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "what hotel has the best rating and amenities",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "answers": "extractive|count-3",
            "captions": "extractive|highlight-true",
            "select": "HotelId, HotelName, Rating",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1
        # rerankerScore on results
        for r in results:
            assert "@search.rerankerScore" in r, (
                f"Hotel {r.get('HotelId')} missing @search.rerankerScore"
            )
        # When both answers and captions are requested, verify captions are present
        captions_found = sum(1 for r in results if "@search.captions" in r)
        assert captions_found >= 1, (
            f"Expected at least 1 result with @search.captions when captions requested, "
            f"found {captions_found}/{len(results)}"
        )


class TestSemanticLanguage:
    """Language-specific semantic features."""

    def test_sem_05_french_semantic_search(self, rest, primary_index_name):
        """SEM-05: Semantic search in French on Description_fr field."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hôtel classique situé dans la ville",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "queryLanguage": "fr-FR",
            "select": "HotelId, HotelName, Description_fr",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "No results for French query"
        # Verify at least one result has French content in Description_fr
        has_french = any(
            r.get("Description_fr") and len(r["Description_fr"]) > 0
            for r in results
        )
        assert has_french, (
            f"French semantic search returned results but none have Description_fr content: "
            f"{[r.get('Description_fr', '<missing>') for r in results[:3]]}"
        )


class TestSemanticWithFilters:
    """Semantic search combined with OData filters."""

    def test_sem_06_semantic_plus_filter(self, rest, primary_index_name):
        """SEM-06: Semantic + filter — filter applied before reranking."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "beautiful hotel with great views",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "filter": "Rating ge 4",
            "select": "HotelId, HotelName, Rating",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        # All results must satisfy the filter
        for r in results:
            rating = r.get("Rating")
            assert rating is not None and rating >= 4, \
                f"Hotel {r.get('HotelId')} Rating {rating} should be >= 4"
        if results:
            assert "@search.rerankerScore" in results[0]

    def test_sem_07_semantic_orderby_override(self, rest, primary_index_name):
        """SEM-07: orderby with semantic search is rejected (not supported)."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel with amenities",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "orderby": "Rating desc",
            "select": "HotelId, HotelName, Rating",
            "top": 10,
        })
        assert_status(resp, 400)
        data = resp.json()
        err = data.get("error", {})
        assert "orderBy" in err.get("message", "").lower() or "orderby" in err.get("message", ""), \
            f"Expected error about orderBy, got: {err.get('message', '')}"


class TestSemanticParameters:
    """Semantic-specific query parameters."""

    def test_sem_08_max_text_recall_size(self, rest, primary_index_name):
        """SEM-08: semanticMaxTextRecallSize is not supported in this API version."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "semanticMaxTextRecallSize": 5,
            "count": True,
            "top": 25,
        })
        # This parameter is not valid in 2025-11-01-preview
        assert_status(resp, 400)
        err = resp.json().get("error", {})
        assert "semanticMaxTextRecallSize" in err.get("message", ""), \
            f"Expected error about semanticMaxTextRecallSize, got: {err.get('message', '')}"

    def test_sem_09_speller_correction(self, rest, primary_index_name):
        """SEM-09: Speller correction with misspelled query still finds results."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxery hotl downtoun",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "speller": "lexicon",
            "queryLanguage": "en-us",
            "select": "HotelId, HotelName",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Speller should correct misspellings and find results"
        has_reranker = any("@search.rerankerScore" in r for r in results)
        assert has_reranker, (
            "Semantic search with speller returned results but no rerankerScores "
            "— speller may not have corrected the query"
        )

    def test_sem_10_semantic_with_count(self, rest, primary_index_name):
        """SEM-10: $count=true with semantic search returns @odata.count."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel with excellent amenities",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "count": True,
            "top": 3,
        })
        assert_status(resp, 200)
        data = resp.json()
        count = data.get("@odata.count")
        assert count is not None, "@odata.count missing from semantic response"
        assert count >= 1, f"@odata.count should be >= 1, got {count}"


class TestSemanticWithOtherFeatures:
    """Semantic search combined with highlight and pagination."""

    def test_sem_11_semantic_with_highlight(self, rest, primary_index_name):
        """SEM-11: highlight works alongside semantic captions."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel plaza historic",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "captions": "extractive",
            "highlight": "Description",
            "highlightPreTag": "<em>",
            "highlightPostTag": "</em>",
            "select": "HotelId, HotelName",
            "top": 5,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "No results returned"
        # Highlights and captions should coexist
        highlights_found = any("@search.highlights" in r for r in results)
        captions_found = any("@search.captions" in r for r in results)
        assert highlights_found, (
            "@search.highlights not found on any result despite highlight param"
        )
        assert captions_found, (
            "@search.captions not found on any result despite captions param"
        )

    def test_sem_12_semantic_pagination(self, rest, primary_index_name):
        """SEM-12: Semantic search top/skip — no overlap between pages."""
        resp1 = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "top": 3, "skip": 0,
            "select": "HotelId",
        })
        resp2 = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "hotel",
            "queryType": "semantic",
            "semanticConfiguration": SEMANTIC_CONFIG,
            "top": 3, "skip": 3,
            "select": "HotelId",
        })
        assert_status(resp1, 200)
        assert_status(resp2, 200)
        ids1 = {r["HotelId"] for r in resp1.json().get("value", [])}
        ids2 = {r["HotelId"] for r in resp2.json().get("value", [])}
        overlap = ids1 & ids2
        assert len(overlap) == 0, f"Semantic pages overlap on IDs: {overlap}"
