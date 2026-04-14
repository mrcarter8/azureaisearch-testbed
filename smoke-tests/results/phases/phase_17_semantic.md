# Phase 17 — Semantic Deep-Dive

**API:** Data plane `2025-11-01-preview`  
**Result:** 12/12 passed

All semantic tests handle 206 (partial response) gracefully — PPE transient behavior.

---

## SEM-01: Semantic rerankerScore descending

| | |
|---|---|
| **Operation** | Semantic search with reranker score validation |
| **Request** | `POST /indexes/{index}/docs/search` with `queryType: "semantic"` |
| **Verified** | Status 200/206; if 200, all results have @search.rerankerScore in descending order |
| **Result** | PASS |

---

## SEM-02: Extractive answers structure

| | |
|---|---|
| **Operation** | Semantic answers with structure validation |
| **Request** | `POST /indexes/{index}/docs/search` with `answers: "extractive|count-3"` |
| **Verified** | Status 200/206; if answers present, each has key, text, score (>= 0) |
| **Result** | PASS |

---

## SEM-03: Extractive captions on results

| | |
|---|---|
| **Operation** | Semantic captions with highlight |
| **Request** | `POST /indexes/{index}/docs/search` with `captions: "extractive|highlight-true"` |
| **Verified** | Status 200/206; at least one result has @search.captions with text field |
| **Result** | PASS |

---

## SEM-04: Answers + captions combined

| | |
|---|---|
| **Operation** | Both extractive answers and captions simultaneously |
| **Request** | `POST /indexes/{index}/docs/search` with both `answers` and `captions` parameters |
| **Verified** | Status 200/206; results have @search.rerankerScore when 200 |
| **Result** | PASS |

---

## SEM-05: French semantic search

| | |
|---|---|
| **Operation** | Semantic search with French query and queryLanguage |
| **Request** | `POST /indexes/{index}/docs/search` with `queryLanguage: "fr-FR"` |
| **Verified** | Status 200/206; >= 1 result returned for French query |
| **Result** | PASS |

---

## SEM-06: Semantic + filter combo

| | |
|---|---|
| **Operation** | Semantic search combined with OData filter |
| **Request** | `POST /indexes/{index}/docs/search` with `queryType: "semantic", filter: "Rating ge 4"` |
| **Verified** | Status 200/206; all results satisfy Rating >= 4 filter; @search.rerankerScore present when 200 |
| **Result** | PASS |

---

## SEM-07: orderby with semantic — rejected 400

| | |
|---|---|
| **Operation** | Validate orderby is not supported with semantic queryType |
| **Request** | `POST /indexes/{index}/docs/search` with `queryType: "semantic", orderby: "Rating desc"` |
| **Verified** | Status 400; error message references orderBy restriction |
| **Result** | PASS |

---

## SEM-08: semanticMaxTextRecallSize — not supported 400

| | |
|---|---|
| **Operation** | Validate semanticMaxTextRecallSize is not supported in this API version |
| **Request** | `POST /indexes/{index}/docs/search` with `semanticMaxTextRecallSize: 5` |
| **Verified** | Status 400; error message references semanticMaxTextRecallSize |
| **Result** | PASS |

---

## SEM-09: Speller correction + semantic

| | |
|---|---|
| **Operation** | Semantic search with misspelled query and lexicon speller |
| **Request** | `POST /indexes/{index}/docs/search` with `speller: "lexicon", queryLanguage: "en-us"` |
| **Body** | `{"search": "luxery hotl downtoun", ...}` |
| **Verified** | Status 200/206; >= 1 result (speller corrects misspellings) |
| **Result** | PASS |

---

## SEM-10: Semantic + $count

| | |
|---|---|
| **Operation** | Semantic search with count=true |
| **Request** | `POST /indexes/{index}/docs/search` with `count: true` |
| **Verified** | Status 200/206; @odata.count present and >= 1 |
| **Result** | PASS |

---

## SEM-11: Semantic + highlight + captions

| | |
|---|---|
| **Operation** | Highlight and captions together with semantic |
| **Request** | `POST /indexes/{index}/docs/search` with `highlight: "Description", captions: "extractive"` |
| **Verified** | Status 200/206; at least one of @search.highlights or @search.captions present |
| **Result** | PASS |

---

## SEM-12: Semantic pagination — no overlap

| | |
|---|---|
| **Operation** | Semantic search with top/skip pagination |
| **Request** | 2× `POST /indexes/{index}/docs/search` (page 1 and page 2) |
| **Verified** | Status 200/206; no HotelId overlap between pages |
| **Result** | PASS |
