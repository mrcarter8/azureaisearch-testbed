# Phase 18 — Vector Queries

**API:** Data plane `2025-11-01-preview`  
**Result:** 4/16 passed, 12 skipped

VQR-01 through VQR-04 run on the primary hotels index. VQR-05 through VQR-16 require the `smoke-vec-e2e` index (1000-doc tech article corpus from Phase 11). When Phase 11 has not been run in the current session, these tests are skipped.

---

## VQR-01: kind:text vector query — scores present

| | |
|---|---|
| **Operation** | Integrated vectorization via kind:text |
| **Request** | `POST /indexes/{index}/docs/search` with vectorQueries kind:text |
| **Verified** | Status 200; all results have @search.score >= 0 |
| **Result** | PASS |

---

## VQR-02: Hybrid with sparse vectors

| | |
|---|---|
| **Operation** | Keyword + vector hybrid search |
| **Request** | `POST /indexes/{index}/docs/search` with `search: "luxury"` + vectorQueries kind:text |
| **Verified** | Status 200; >= 1 result (keyword match via RRF even with sparse vectors) |
| **Result** | PASS |

---

## VQR-03: Vector + filter correctness

| | |
|---|---|
| **Operation** | Vector search combined with OData filter |
| **Request** | `POST /indexes/{index}/docs/search` with vectorQueries + `filter: "Rating ge 4"` |
| **Verified** | Status 200; all results have Rating >= 4 |
| **Result** | PASS |

---

## VQR-04: Tri-modal — keyword + vector + semantic

| | |
|---|---|
| **Operation** | All three retrieval modes simultaneously |
| **Request** | `POST /indexes/{index}/docs/search` with `search + queryType: "semantic" + vectorQueries` |
| **Verified** | Status 200/206; >= 1 result; @search.rerankerScore present when 200 |
| **Result** | PASS |

---

## VQR-05: AI query returns AI category

| | |
|---|---|
| **Operation** | Vector relevance: AI-focused query on 1000-doc corpus |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with AI-focused text vector |
| **Expected** | >= 5/10 top results in AI category |
| **Result** | SKIP — E2E index not present |

---

## VQR-06: Security query returns Security category

| | |
|---|---|
| **Operation** | Vector relevance: Security-focused query |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with security-focused text vector |
| **Expected** | >= 5/10 top results in Security category |
| **Result** | SKIP — E2E index not present |

---

## VQR-07: Different queries → different top results

| | |
|---|---|
| **Operation** | Two different text vectors produce different #1 results |
| **Request** | 2× `POST /indexes/smoke-vec-e2e/docs/search` |
| **Expected** | Different top-1 doc IDs and categories |
| **Result** | SKIP — E2E index not present |

---

## VQR-08: Vector scores descending

| | |
|---|---|
| **Operation** | Validate @search.score in descending order |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with k=20 |
| **Expected** | Scores strictly in descending order |
| **Result** | SKIP — E2E index not present |

---

## VQR-09: exhaustiveKnn mode

| | |
|---|---|
| **Operation** | Exhaustive KNN bypasses HNSW index |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `exhaustive: true` |
| **Expected** | Relevant results still returned; Mobile category in results |
| **Result** | SKIP — E2E index not present |

---

## VQR-10: Oversampling parameter

| | |
|---|---|
| **Operation** | Oversampling expands candidate set before re-scoring |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `oversampling: 5.0` |
| **Expected** | Frontend category in results |
| **Result** | SKIP — E2E index not present |

---

## VQR-11: Vector weight parameter

| | |
|---|---|
| **Operation** | Weight parameter influences hybrid score contribution |
| **Request** | 2× searches with weight=0.1 and weight=5.0 |
| **Expected** | Low weight → keyword dominates; high weight → vector dominates |
| **Result** | SKIP — E2E index not present |

---

## VQR-12: orderby overrides vector scoring

| | |
|---|---|
| **Operation** | orderby on explicit field overrides vector score order |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `orderby: "rating desc"` |
| **Expected** | Ratings in descending order |
| **Result** | SKIP — E2E index not present |

---

## VQR-13: k vs top semantics

| | |
|---|---|
| **Operation** | k=50, top=3 — ANN retrieves 50 candidates, returns 3 |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `k: 50, top: 3` |
| **Expected** | Exactly 3 results returned |
| **Result** | SKIP — E2E index not present |

---

## VQR-14: Vector + $count

| | |
|---|---|
| **Operation** | Vector search with count=true |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `count: true` |
| **Expected** | @odata.count present and >= 1 |
| **Result** | SKIP — E2E index not present |

---

## VQR-15: Vector + facets

| | |
|---|---|
| **Operation** | Vector search with facets on category |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `facets: ["category"]` |
| **Expected** | @search.facets.category present with multiple entries |
| **Result** | SKIP — E2E index not present |

---

## VQR-16: Large k=500 result count

| | |
|---|---|
| **Operation** | Large k value on 1000-doc corpus |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search` with `k: 500, top: 500` |
| **Expected** | Count within 10% of k (450-500) |
| **Result** | SKIP — E2E index not present |
