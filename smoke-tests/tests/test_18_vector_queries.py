"""
test_18_vector_queries.py — Vector Search Scenarios

Tests: VQR-01 through VQR-22

Comprehensive vector search validation: kind:text integrated vectorization,
exhaustive KNN, hybrid+semantic tri-modal, relevance differentiation,
score ordering, oversampling, weight parameter, k vs top semantics,
vector compression (scalar/binary quantization), and multi-field vector
queries. Uses both the primary hotels index and the E2E vector corpus
(smoke-vec-e2e) for meaningful relevance validation.
"""

import copy

import pytest

from conftest import ensure_fresh
from helpers.assertions import (
    assert_all_match,
    assert_search_results,
    assert_status,
)

pytestmark = [pytest.mark.vectorization]

_E2E_INDEX = "smoke-vec-e2e"


@pytest.fixture(scope="module")
def e2e_index(rest):
    """Return E2E index name if it exists, otherwise skip."""
    resp = rest.get(f"/indexes/{_E2E_INDEX}")
    if resp.status_code != 200:
        pytest.skip("E2E vector index (smoke-vec-e2e) not present — run test_11 first")
    # Verify it has documents
    count_resp = rest.get(f"/indexes/{_E2E_INDEX}/docs/$count")
    if count_resp.status_code != 200 or int(count_resp.text.strip()) < 100:
        pytest.skip("E2E vector index has insufficient documents")
    return _E2E_INDEX


# ---------------------------------------------------------------------------
# Primary index — structural vector search tests
# ---------------------------------------------------------------------------


class TestVectorOnPrimaryIndex:
    """Vector search on the primary hotels index (sparse vectors, kind:text)."""

    def test_vqr_01_kind_text_returns_scored_results(self, rest, primary_index_name):
        """VQR-01: kind:text vector query via integrated vectorizer returns scored results."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "luxury hotel with spa and pool near downtown",
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "select": "HotelId, HotelName",
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        for r in results:
            assert "@search.score" in r, f"Missing @search.score on {r.get('HotelId')}"
            assert r["@search.score"] >= 0, f"Negative score: {r['@search.score']}"

    def test_vqr_02_hybrid_with_sparse_vectors(self, rest, primary_index_name):
        """VQR-02: Hybrid (keyword + vector) — keyword search returns results even with sparse vectors."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "luxury",
            "vectorQueries": [{
                "kind": "text",
                "text": "upscale luxury hotel",
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "select": "HotelId, HotelName",
            "count": True,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        # Hybrid should return results even if vector field is sparse —
        # keyword match contributes via RRF fusion
        assert len(results) >= 1, "Hybrid search should return at least 1 result"

    def test_vqr_03_vector_filter_correctness(self, rest, primary_index_name):
        """VQR-03: Vector search + filter — all results satisfy filter predicate."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "hotel with great amenities",
                "fields": "DescriptionVector",
                "k": 10,
            }],
            "filter": "Rating ge 4",
            "select": "HotelId, HotelName, Rating",
        })
        assert_status(resp, 200)
        data = resp.json()
        for r in data.get("value", []):
            rating = r.get("Rating")
            assert rating is not None and rating >= 4, \
                f"Hotel {r.get('HotelId')} Rating {rating} violates filter Rating ge 4"

    def test_vqr_04_trimodal_hybrid_semantic(self, rest, primary_index_name):
        """VQR-04: Tri-modal — keyword + vector + semantic reranking."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "best hotel with excellent views",
            "queryType": "semantic",
            "semanticConfiguration": "hotel-semantic-config",
            "vectorQueries": [{
                "kind": "text",
                "text": "luxury accommodation scenic views",
                "fields": "DescriptionVector",
                "k": 5,
            }],
            "select": "HotelId, HotelName, Rating",
            "top": 5,
        })
        assert_status(resp, (200, 206))
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Tri-modal query should return results"
        if resp.status_code == 200:
            # Semantic rerankerScore should be present
            assert "@search.rerankerScore" in results[0], \
                "Tri-modal 200 response should have @search.rerankerScore"


class TestVectorCompression:
    """Vector search with scalar quantization, binary quantization, and exhaustive KNN on primary index."""

    def test_vqr_17_scalar_quantized_vector_search(self, rest, primary_index_name):
        """VQR-17: Scalar quantized (int8) vector field returns scored results."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "spa and wellness resort with pool",
                "fields": "DescriptionVectorSQ",
                "k": 5,
            }],
            "select": "HotelId, HotelName, Category",
        })
        assert_status(resp, 200)
        results = resp.json().get("value", [])
        assert len(results) >= 1, "Scalar quantized vector search returned no results"
        for r in results:
            assert "@search.score" in r, f"Missing @search.score on {r.get('HotelId')}"

    def test_vqr_18_binary_quantized_vector_search(self, rest, primary_index_name):
        """VQR-18: Binary quantized vector field returns scored results."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "budget hotel near downtown with free parking",
                "fields": "DescriptionVectorBQ",
                "k": 5,
            }],
            "select": "HotelId, HotelName, Category",
        })
        assert_status(resp, 200)
        results = resp.json().get("value", [])
        assert len(results) >= 1, "Binary quantized vector search returned no results"
        for r in results:
            assert "@search.score" in r, f"Missing @search.score on {r.get('HotelId')}"

    def test_vqr_19_exhaustive_knn_on_primary(self, rest, primary_index_name):
        """VQR-19: Exhaustive KNN vector field search returns results."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "historic boutique hotel with character",
                "fields": "DescriptionVectorEKNN",
                "k": 5,
            }],
            "select": "HotelId, HotelName, Category",
        })
        assert_status(resp, 200)
        results = resp.json().get("value", [])
        assert len(results) >= 1, "Exhaustive KNN vector search returned no results"
        for r in results:
            assert "@search.score" in r, f"Missing @search.score on {r.get('HotelId')}"

    def test_vqr_20_compression_vs_uncompressed_overlap(self, rest, primary_index_name):
        """VQR-20: Compressed and uncompressed fields return overlapping top results."""
        query_text = "luxury hotel with world-class amenities"
        # Uncompressed HNSW
        resp_hnsw = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": query_text,
                "fields": "DescriptionVector",
                "k": 10,
            }],
            "select": "HotelId",
        })
        # Scalar quantized
        resp_sq = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": query_text,
                "fields": "DescriptionVectorSQ",
                "k": 10,
            }],
            "select": "HotelId",
        })
        assert_status(resp_hnsw, 200)
        assert_status(resp_sq, 200)
        ids_hnsw = {r["HotelId"] for r in resp_hnsw.json().get("value", [])}
        ids_sq = {r["HotelId"] for r in resp_sq.json().get("value", [])}
        overlap = ids_hnsw & ids_sq
        # With reranking enabled, scalar quantized should have significant overlap
        assert len(overlap) >= 3, (
            f"Expected >= 3 overlapping results between HNSW and SQ, "
            f"got {len(overlap)}: HNSW={ids_hnsw}, SQ={ids_sq}"
        )

    def test_vqr_21_multi_field_vector_query(self, rest, primary_index_name):
        """VQR-21: Multi-vector query across two vector fields with different algorithms."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [
                {
                    "kind": "text",
                    "text": "eco-friendly sustainable green hotel",
                    "fields": "DescriptionVector",
                    "k": 5,
                },
                {
                    "kind": "text",
                    "text": "eco-friendly sustainable green hotel",
                    "fields": "DescriptionVectorEKNN",
                    "k": 5,
                },
            ],
            "select": "HotelId, HotelName, Category",
        })
        assert_status(resp, 200)
        results = resp.json().get("value", [])
        assert len(results) >= 1, "Multi-field vector query returned no results"
        # RRF fusion from two fields should give Eco-Friendly hotels higher scores
        categories = [r.get("Category") for r in results[:5]]
        assert "Eco-Friendly" in categories, (
            f"Expected Eco-Friendly in top 5 multi-field results: {categories}"
        )

    def test_vqr_22_hybrid_with_compressed_field(self, rest, primary_index_name):
        """VQR-22: Hybrid keyword + binary quantized vector search."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "business center meeting rooms",
            "vectorQueries": [{
                "kind": "text",
                "text": "business hotel conference center",
                "fields": "DescriptionVectorBQ",
                "k": 10,
            }],
            "select": "HotelId, HotelName, Category",
            "count": True,
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) >= 1, "Hybrid + BQ search returned no results"
        count = data.get("@odata.count")
        assert count is not None, "@odata.count missing from hybrid + BQ search"


# ---------------------------------------------------------------------------
# E2E index — meaningful relevance and feature tests
# ---------------------------------------------------------------------------


class TestVectorRelevance:
    """Relevance validation on the 1000-doc E2E corpus."""

    def test_vqr_05_ai_query_returns_ai_category(self, rest, e2e_index):
        """VQR-05: AI-focused text vector query returns AI-category docs primarily."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "deep learning neural networks machine learning algorithms",
                "fields": "contentVector",
                "k": 10,
            }],
            "select": "id, title, category",
            "top": 10,
        })
        data = assert_search_results(resp, min_count=1)
        categories = [r["category"] for r in data["value"]]
        ai_count = categories.count("AI")
        assert ai_count >= 5, \
            f"Expected >= 5 AI results in top 10, got {ai_count}: {categories}"

    def test_vqr_06_security_query_returns_security_category(self, rest, e2e_index):
        """VQR-06: Security-focused query returns Security-category docs primarily."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "zero trust encryption vulnerability penetration testing firewall",
                "fields": "contentVector",
                "k": 10,
            }],
            "select": "id, title, category",
            "top": 10,
        })
        data = assert_search_results(resp, min_count=1)
        categories = [r["category"] for r in data["value"]]
        sec_count = categories.count("Security")
        assert sec_count >= 5, \
            f"Expected >= 5 Security results in top 10, got {sec_count}: {categories}"

    def test_vqr_07_different_queries_different_top_result(self, rest, e2e_index):
        """VQR-07: Different text queries yield different #1 results."""
        resp_ai = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "transformer models natural language processing",
                "fields": "contentVector",
                "k": 1,
            }],
            "select": "id, category",
            "top": 1,
        })
        resp_iot = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "IoT sensor telemetry edge computing device management",
                "fields": "contentVector",
                "k": 1,
            }],
            "select": "id, category",
            "top": 1,
        })
        assert_status(resp_ai, 200)
        assert_status(resp_iot, 200)
        ai_top = resp_ai.json()["value"][0]
        iot_top = resp_iot.json()["value"][0]
        assert ai_top["id"] != iot_top["id"], \
            f"Different queries returned same top result: {ai_top['id']}"
        assert ai_top["category"] != iot_top["category"], \
            f"Expected different categories: AI query → {ai_top['category']}, IoT query → {iot_top['category']}"


class TestVectorScoring:
    """Score ordering and consistency."""

    def test_vqr_08_scores_descending(self, rest, e2e_index):
        """VQR-08: Vector search results ordered by @search.score descending."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "database optimization indexing query tuning",
                "fields": "contentVector",
                "k": 20,
            }],
            "select": "id, category",
            "top": 20,
        })
        data = assert_search_results(resp, min_count=2)
        scores = [r["@search.score"] for r in data["value"]]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"Score not descending at [{i}]: {scores[i]} < {scores[i+1]}"


class TestVectorModes:
    """Exhaustive KNN, oversampling, and weight parameters."""

    def test_vqr_09_exhaustive_knn(self, rest, e2e_index):
        """VQR-09: Exhaustive KNN search — exhaustive:true bypasses HNSW index."""
        query_body = {
            "vectorQueries": [{
                "kind": "text",
                "text": "cloud migration infrastructure deployment",
                "fields": "contentVector",
                "k": 10,
            }],
            "select": "id, title, category",
            "top": 10,
        }
        # HNSW baseline
        resp_hnsw = rest.post(f"/indexes/{e2e_index}/docs/search", query_body)
        hnsw_data = assert_search_results(resp_hnsw, min_count=1)
        hnsw_ids = {r["id"] for r in hnsw_data["value"]}

        # Exhaustive KNN — same query with exhaustive:true
        exh_body = copy.deepcopy(query_body)
        exh_body["vectorQueries"][0]["exhaustive"] = True
        resp_exh = rest.post(f"/indexes/{e2e_index}/docs/search", exh_body)
        exh_data = assert_search_results(resp_exh, min_count=1)
        exh_ids = {r["id"] for r in exh_data["value"]}

        # Both should return Cloud-category results and overlap significantly
        exh_categories = [r["category"] for r in exh_data["value"]]
        assert "Cloud" in exh_categories, f"Expected Cloud in exhaustive results: {exh_categories}"
        overlap = hnsw_ids & exh_ids
        assert len(overlap) >= 5, f"HNSW/exhaustive overlap too low ({len(overlap)}): HNSW={hnsw_ids}, EXH={exh_ids}"

    def test_vqr_10_oversampling(self, rest, primary_index_name):
        """VQR-10: Oversampling parameter expands candidate set before re-scoring (requires compressed field)."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "luxury hotel with pool and spa",
                "fields": "DescriptionVectorSQ",
                "k": 10,
                "oversampling": 5.0,
            }],
            "select": "HotelId, HotelName, Rating",
            "top": 10,
        })
        data = assert_search_results(resp, min_count=1)
        assert any(r.get("Rating", 0) >= 3 for r in data["value"]), \
            "Expected at least one result with Rating >= 3"

    def test_vqr_11_vector_weight(self, rest, e2e_index):
        """VQR-11: Vector weight parameter influences hybrid score contribution."""
        # Low vector weight — keyword should dominate
        resp_low = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "search": "DevOps CI/CD pipelines",
            "vectorQueries": [{
                "kind": "text",
                "text": "frontend React web development",
                "fields": "contentVector",
                "k": 10,
                "weight": 0.1,
            }],
            "select": "id, category",
            "top": 10,
        })
        # High vector weight — vector should dominate
        resp_high = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "search": "DevOps CI/CD pipelines",
            "vectorQueries": [{
                "kind": "text",
                "text": "frontend React web development",
                "fields": "contentVector",
                "k": 10,
                "weight": 5.0,
            }],
            "select": "id, category",
            "top": 10,
        })
        assert_status(resp_low, 200)
        assert_status(resp_high, 200)
        cats_low = [r["category"] for r in resp_low.json()["value"]]
        cats_high = [r["category"] for r in resp_high.json()["value"]]
        # With low vector weight, keyword "DevOps" should dominate
        devops_low = cats_low.count("DevOps")
        # With high vector weight, "frontend React" vector should bring Frontend
        frontend_high = cats_high.count("Frontend")
        # At least one of these should show the expected dominance
        assert devops_low >= 3 or frontend_high >= 3, \
            f"Weight parameter has no effect: low-weight DevOps={devops_low}, high-weight Frontend={frontend_high}"


class TestVectorWithQueryFeatures:
    """Vector search combined with orderby, count, facets, k/top semantics."""

    def test_vqr_12_vector_orderby_override(self, rest, e2e_index):
        """VQR-12: orderby overrides vector score ordering."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "cloud computing containers kubernetes",
                "fields": "contentVector",
                "k": 20,
            }],
            "orderby": "rating desc",
            "select": "id, category, rating",
            "top": 10,
        })
        data = assert_search_results(resp, min_count=2)
        ratings = [r["rating"] for r in data["value"] if r.get("rating") is not None]
        for i in range(len(ratings) - 1):
            assert ratings[i] >= ratings[i + 1], \
                f"orderby Rating desc violated at [{i}]: {ratings[i]} < {ratings[i+1]}"

    def test_vqr_13_k_vs_top_semantics(self, rest, e2e_index):
        """VQR-13: k=50, top=3 — ANN retrieves 50 candidates, returns only 3."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "backend API REST service design",
                "fields": "contentVector",
                "k": 50,
            }],
            "select": "id",
            "top": 3,
        })
        data = assert_search_results(resp, min_count=1)
        assert len(data["value"]) == 3, \
            f"top=3 should return exactly 3 results, got {len(data['value'])}"

    def test_vqr_14_vector_with_count(self, rest, e2e_index):
        """VQR-14: Vector search with $count=true returns @odata.count."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "networking load balancer CDN",
                "fields": "contentVector",
                "k": 50,
            }],
            "count": True,
            "top": 5,
        })
        data = assert_search_results(resp, min_count=1)
        count = data.get("@odata.count")
        assert count is not None, "@odata.count missing from vector search response"
        assert count >= 5, f"@odata.count should be >= 5, got {count}"

    def test_vqr_15_vector_with_facets(self, rest, e2e_index):
        """VQR-15: Vector search with facets — category distribution returned."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "software engineering best practices",
                "fields": "contentVector",
                "k": 50,
            }],
            "facets": ["category"],
            "top": 0,
        })
        assert_status(resp, 200)
        data = resp.json()
        facets = data.get("@search.facets", {})
        assert "category" in facets, "Category facet missing from vector search"
        assert len(facets["category"]) >= 2, \
            f"Expected multiple category facets, got {len(facets['category'])}"

    def test_vqr_16_large_k_result_count(self, rest, e2e_index):
        """VQR-16: Large k=500 on 1000-doc corpus returns substantial results."""
        resp = rest.post(f"/indexes/{e2e_index}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "technology and software development",
                "fields": "contentVector",
                "k": 500,
            }],
            "count": True,
            "top": 0,
        })
        assert_status(resp, 200)
        data = resp.json()
        count = data.get("@odata.count", 0)
        assert count >= 100, \
            f"Large k=500 should return >= 100 docs, got {count}"

