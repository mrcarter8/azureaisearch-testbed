# Phase 11 — Integrated Vectorization

**API:** Data plane `2025-11-01-preview`  
**Result:** 19/19 passed

---

## VEC-01: Index with HNSW vectorSearch algorithm

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec01-hnsw`) |
| **Request** | `PUT /indexes/smoke-vec01-hnsw?api-version=2025-11-01-preview` |
| **Body** | Index with fields `[id (key), content (Edm.String), contentVector (Collection(Edm.Single), 1536 dims)]`, `vectorSearch.algorithms: [{"name": "hnsw-alg", "kind": "hnsw", "hnswParameters": {"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"}}]`, `vectorSearch.profiles: [{"name": "hnsw-profile", "algorithm": "hnsw-alg"}]` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.algorithms` contains entry with `kind == "hnsw"`; then deleted |
| **Result** | PASS |

---

## VEC-02: Index with exhaustiveKnn algorithm

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec02-eknn`) |
| **Request** | `PUT /indexes/smoke-vec02-eknn?api-version=2025-11-01-preview` |
| **Body** | Index with `vectorSearch.algorithms: [{"name": "eknn-alg", "kind": "exhaustiveKnn", "exhaustiveKnnParameters": {"metric": "cosine"}}]`, profile links to `eknn-alg` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.algorithms` contains entry with `kind == "exhaustiveKnn"`; then deleted |
| **Result** | PASS |

---

## VEC-03: Azure OpenAI vectorizer round-trips

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec03-vectorizer`) |
| **Request** | `PUT /indexes/smoke-vec03-vectorizer?api-version=2025-11-01-preview` |
| **Body** | Index with `vectorSearch.vectorizers: [{"name": "aoai-vectorizer", "kind": "azureOpenAI", "azureOpenAIParameters": {"resourceUri": "...", "deploymentId": "...", "modelName": "...", "apiKey": "..."}}]`, profile links algorithm + vectorizer |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.vectorizers` contains `"aoai-vectorizer"`; then deleted |
| **Result** | PASS |

---

## VEC-04: Profile linking algorithm + vectorizer is applied on field

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec04-profile`) |
| **Request** | `PUT /indexes/smoke-vec04-profile?api-version=2025-11-01-preview` |
| **Body** | Index with profile `"linked-profile"` linking `hnsw-alg` + `aoai-vec` vectorizer; `contentVector` field references `"linked-profile"` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `contentVector` field has `vectorSearchProfile == "linked-profile"`; then deleted |
| **Result** | PASS |

---

## VEC-05: Full pipeline index — chunking + embedding config present

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Index (`smoke-vec05-e2e`) |
| **Request** | `PUT /indexes/smoke-vec05-e2e?api-version=2025-11-01-preview` |
| **Body** | Index with HNSW algorithm, AOAI vectorizer, profile linking both; validates index creation for E2E pipeline (actual indexer run is Phase 9) |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## VEC-06: Scalar quantization configuration round-trips

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec06-scalar`) |
| **Request** | `PUT /indexes/smoke-vec06-scalar?api-version=2025-11-01-preview` |
| **Body** | Index with `vectorSearch.compressions: [{"name": "scalar-quant", "kind": "scalarQuantization", "scalarQuantizationParameters": {"quantizedDataType": "int8"}}]`, profile links `hnsw-alg` + compression `"scalar-quant"` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.compressions` contains entry with `kind == "scalarQuantization"`; then deleted |
| **Result** | PASS (fixed: removed unsupported `rerankWithOriginalVectors` and `defaultOversampling` properties) |

---

## VEC-07: Binary quantization configuration round-trips

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec07-binary`) |
| **Request** | `PUT /indexes/smoke-vec07-binary?api-version=2025-11-01-preview` |
| **Body** | Index with `vectorSearch.compressions: [{"name": "binary-quant", "kind": "binaryQuantization"}]`, profile links `hnsw-alg` + compression `"binary-quant"` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.compressions` contains entry with `kind == "binaryQuantization"`; then deleted |
| **Result** | PASS (fixed: removed unsupported `rerankWithOriginalVectors` property) |

---

## VEC-08: Vector field with stored:false

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec08-stored`) |
| **Request** | `PUT /indexes/smoke-vec08-stored?api-version=2025-11-01-preview` |
| **Body** | Index with `contentVector` field set to `"stored": false` — vector is usable for search but not retrievable via `$select` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `contentVector` field has `stored == false`; then deleted |
| **Result** | PASS |

---

## VEC-09: Index with 2 profiles on different vector fields

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Index (`smoke-vec09-multi`) |
| **Request** | `PUT /indexes/smoke-vec09-multi?api-version=2025-11-01-preview` |
| **Body** | Index with 2 HNSW algorithms (`hnsw-a` m=4/cosine, `hnsw-b` m=8/dotProduct), 2 profiles (`profile-a` → `hnsw-a`, `profile-b` → `hnsw-b`), 2 vector fields (`contentVector` → `profile-a`, `titleVector` → `profile-b` 1536 dims) |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.profiles` contains both `"profile-a"` and `"profile-b"`; then deleted |
| **Result** | PASS |

---

# E2E Integrated Vectorization (VEC-10 through VEC-19)

These tests create a 1000-document "tech articles" index with an Azure OpenAI vectorizer (`text-embedding-3-small`, 1536 dims), pre-compute embeddings via AOAI embedding API, upload documents with vectors, then exercise **query-time integrated vectorization** using `kind:"text"` vector queries (text → vector conversion happens server-side via the configured vectorizer).

**Corpus:** 10 categories (AI, Cloud, Security, DevOps, Database, Networking, Frontend, Backend, Mobile, IoT) × 10 topic sentences × 10 variation templates = 1000 synthetic tech articles. Each document has `id`, `title`, `content`, `category`, `author`, `publishDate`, `rating`, `tags`, and `contentVector` (1536-dim embedding).

---

## VEC-10: Create index with AOAI vectorizer for integrated vectorization

| | |
|---|---|
| **Operation** | Delete (cleanup) → Create → Read |
| **Object** | Index (`smoke-vec-e2e`) |
| **Request** | `PUT /indexes/smoke-vec-e2e?api-version=2025-11-01-preview` |
| **Body** | Index with 9 fields (`id`, `title`, `content`, `category`, `author`, `publishDate`, `rating`, `tags`, `contentVector` 1536-dim), `vectorSearch.algorithms: [{"name": "e2e-hnsw", "kind": "hnsw", ...}]`, `vectorSearch.vectorizers: [{"name": "e2e-aoai-vectorizer", "kind": "azureOpenAI", "azureOpenAIParameters": {resourceUri, deploymentId, modelName, apiKey}}]`, `vectorSearch.profiles: [{"name": "e2e-vector-profile", "algorithm": "e2e-hnsw", "vectorizer": "e2e-aoai-vectorizer"}]` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `vectorSearch.vectorizers` contains `"e2e-aoai-vectorizer"` and profile links to it |
| **Result** | PASS |

---

## VEC-11: Embed and upload 1000 tech articles

| | |
|---|---|
| **Operation** | Embed (AOAI API, 5 batches of 200) → Upload (10 batches of 100) → Wait for indexing |
| **Object** | Documents in `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/index?api-version=2025-11-01-preview` (×10 batches) |
| **Body** | Each batch: `{"value": [100 documents with @search.action: "upload", id, title, content, category, author, publishDate, rating, tags, contentVector]}` |
| **Expected Response** | `200` or `207` for each batch; doc count reaches 1000 |
| **Verified** | All 1000 embeddings computed (no nulls); each upload batch returns 200/207; `$count` reaches ≥ 1000 within 60s |
| **Result** | PASS |

---

## VEC-12: Vector query kind:text (integrated vectorization)

| | |
|---|---|
| **Operation** | Search with kind:text vectorQuery |
| **Object** | `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"count": true, "top": 10, "select": "id, title, category, rating", "vectorQueries": [{"kind": "text", "text": "machine learning and neural network algorithms for artificial intelligence", "fields": "contentVector", "k": 10}]}` |
| **Expected Response** | `200` with results |
| **Verified** | Status 200; results non-empty; all results have `@search.score`; AI category appears in top results (semantic relevance) |
| **Result** | PASS |

---

## VEC-13: Hybrid keyword + kind:text vector query

| | |
|---|---|
| **Operation** | Hybrid search (keyword + vector) |
| **Object** | `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"search": "kubernetes container orchestration", "searchFields": "title,content", "count": true, "top": 10, "select": "id, title, category", "vectorQueries": [{"kind": "text", "text": "container orchestration and cloud native deployment patterns", "fields": "contentVector", "k": 10}]}` |
| **Expected Response** | `200` with results |
| **Verified** | Status 200; results non-empty; Cloud category appears in results |
| **Result** | PASS |

---

## VEC-14: Vector kind:text query with $filter

| | |
|---|---|
| **Operation** | Filtered vector query |
| **Object** | `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"count": true, "top": 10, "filter": "category eq 'Security'", "select": "id, title, category", "vectorQueries": [{"kind": "text", "text": "encryption and network security threat detection protocols", "fields": "contentVector", "k": 50}]}` |
| **Expected Response** | `200` with results |
| **Verified** | Status 200; results non-empty; **every** result has `category == "Security"` (filter strictly applied to vector results) |
| **Result** | PASS |

---

## VEC-15: Vector kind:text query with $select

| | |
|---|---|
| **Operation** | Vector query with field projection |
| **Object** | `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"top": 5, "select": "id, category", "vectorQueries": [{"kind": "text", "text": "database query optimization and indexing strategies", "fields": "contentVector", "k": 5}]}` |
| **Expected Response** | `200` with results |
| **Verified** | Status 200; results non-empty; each result has `id` and `category` but **not** `title` or `content` ($select correctly restricts fields) |
| **Result** | PASS |

---

## VEC-16: Vector kind:text query with top/skip pagination

| | |
|---|---|
| **Operation** | Two paginated vector queries |
| **Object** | `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search?api-version=2025-11-01-preview` (×2) |
| **Body** | Page 1: `{top: 5, skip: 0, vectorQueries: [{kind: "text", text: "cloud computing infrastructure and deployment", k: 50}]}` — Page 2: `{top: 5, skip: 5, ...}` |
| **Expected Response** | `200` for both pages |
| **Verified** | Status 200; page 1 has 5 results; page 2 has 5 results; **no ID overlap** between pages |
| **Result** | PASS |

---

## VEC-17: Multiple kind:text vectorQueries

| | |
|---|---|
| **Operation** | Multi-vector query |
| **Object** | `smoke-vec-e2e` |
| **Request** | `POST /indexes/smoke-vec-e2e/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"count": true, "top": 10, "select": "id, title, category", "vectorQueries": [{"kind": "text", "text": "machine learning model training deep learning", "fields": "contentVector", "k": 10}, {"kind": "text", "text": "IoT sensor telemetry edge computing", "fields": "contentVector", "k": 10}]}` |
| **Expected Response** | `200` with results |
| **Verified** | Status 200; results non-empty; at least 2 distinct categories appear (semantically diverse queries produce mixed results) |
| **Result** | PASS |

---

## VEC-18: Scalar quantization + AOAI vectorizer query

| | |
|---|---|
| **Operation** | Create quantized index → Embed 5 docs → Upload → Wait → kind:text query → Delete |
| **Object** | Index (`smoke-vec18-quant-vec`) |
| **Request** | `PUT /indexes/smoke-vec18-quant-vec` to create, `POST .../docs/index` to upload, `POST .../docs/search` to query |
| **Body** | Index with `vectorSearch.compressions: [{"name": "sq8", "kind": "scalarQuantization", "scalarQuantizationParameters": {"quantizedDataType": "int8"}}]`, profile links HNSW + AOAI vectorizer + `"sq8"` compression. 5 sample documents with pre-computed embeddings uploaded. Query with `kind: "text"` through quantized + vectorizer profile. |
| **Expected Response** | `200`/`201` create; `200`/`207` upload; `200` search with results |
| **Verified** | Index created; documents uploaded; doc count reaches 5; kind:text query returns results through quantized+vectorizer profile; index deleted |
| **Result** | PASS |

---

## VEC-19: Delete E2E vectorization index + verify

| | |
|---|---|
| **Operation** | Delete → Verify 404 |
| **Object** | Index (`smoke-vec-e2e`) |
| **Request** | `DELETE /indexes/smoke-vec-e2e?api-version=2025-11-01-preview` |
| **Expected Response** | `204` (or `404` if already cleaned up) |
| **Verified** | Delete returns 204/404; subsequent GET returns 404 (index confirmed removed) |
| **Result** | PASS |
