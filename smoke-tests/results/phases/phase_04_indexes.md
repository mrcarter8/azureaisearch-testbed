# Phase 4 — Index Management

**API:** Data plane `2025-11-01-preview`  
**Result:** 15/16 passed, 1 failed (IDX-16)

---

## IDX-01: Create full-featured index (GATE)

| | |
|---|---|
| **Operation** | Create (synonym map) → Create (index) |
| **Object** | Synonym Map + Index |
| **Requests** | 1. `PUT /synonymmaps/{synonym-map}` — create synonym map with Solr rules (`hotel, motel, inn`) |
| | 2. `PUT /indexes/{index}` — full-featured index with 14 fields, vector search (HNSW + exhaustiveKnn), AOAI vectorizer, semantic config, scoring profiles, suggesters, CORS |
| **Body (index)** | Fields: HotelId (key), HotelName, Description, Description_fr, Category, Tags, ParkingIncluded, LastRenovationDate, Rating, Location (GeographyPoint), DescriptionVector (1536-dim), Address (ComplexType with 5 sub-fields), Rooms (Collection of ComplexType with 8 sub-fields). VectorSearch: HNSW + exhaustiveKnn algorithms, hotel-vector-profile with AOAI vectorizer. Semantic: hotel-semantic-config. ScoringProfiles: boostHighRating (magnitude + freshness). Suggesters: sg (analyzingInfixMatching). CORS: allowedOrigins. |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201. GATE: failure aborts entire run |
| **Result** | PASS |

---

## IDX-02: Read index

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index |
| **Request** | `GET /indexes/{index}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `name` == index name; `fields` exists |
| **Result** | PASS |

---

## IDX-03: List indexes

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?$select=name&api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `value[].name` contains our index name |
| **Result** | PASS |

---

## IDX-04: Update index (add field)

| | |
|---|---|
| **Operation** | Read → Update → Read (verify) |
| **Object** | Index |
| **Requests** | 1. `GET /indexes/{index}` — get current definition |
| | 2. `PUT /indexes/{index}` — append `{"name": "NewField", "type": "Edm.String", "searchable": true}` to fields array |
| | 3. `GET /indexes/{index}` — verify field added |
| **Expected Response** | GET: 200; PUT: 200 or 204 |
| **Verified** | PUT status 200/204; follow-up GET has `"NewField"` in field names |
| **Result** | PASS |

---

## IDX-05: Read index statistics

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index Statistics |
| **Request** | `GET /indexes/{index}/stats?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `documentCount` and `storageSize` |
| **Result** | PASS |

---

## IDX-06: Create + delete + verify index gone

| | |
|---|---|
| **Operation** | Create → Delete → Read (verify 404) |
| **Object** | Index `smoke-disposable-idx` |
| **Requests** | 1. `PUT /indexes/smoke-disposable-idx` with minimal fields → 200/201 |
| | 2. `DELETE /indexes/smoke-disposable-idx` → 204 |
| | 3. `GET /indexes/smoke-disposable-idx` → 404 |
| **Verified** | Create 200/201; delete 204; GET returns 404 |
| **Result** | PASS |

---

## IDX-07: Read index (verify vector config)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index (vectorSearch section) |
| **Request** | `GET /indexes/{index}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | `vectorSearch.algorithms` has >= 1 entry; `vectorSearch.profiles` has >= 1 entry; `vectorSearch.vectorizers` has >= 1 entry |
| **Result** | PASS |

---

## IDX-08: Read index (verify semantic config)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index (semantic section) |
| **Request** | `GET /indexes/{index}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | `semantic.defaultConfiguration` exists; `semantic.configurations` has >= 1 entry |
| **Result** | PASS |

---

## IDX-09: Read index (verify scoring profiles)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index (scoringProfiles section) |
| **Request** | `GET /indexes/{index}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | `scoringProfiles` has >= 1 entry; contains profile named `"boostHighRating"` |
| **Result** | PASS |

---

## IDX-10: Read index (verify suggesters)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index (suggesters section) |
| **Request** | `GET /indexes/{index}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | `suggesters` has >= 1 entry; first suggester name == `"sg"` |
| **Result** | PASS |

---

## IDX-11: Read index (verify CORS)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Index (corsOptions section) |
| **Request** | `GET /indexes/{index}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | `corsOptions.allowedOrigins` contains `"https://smoke-test.example.com"` |
| **Result** | PASS |

---

## IDX-12: Create index with custom analyzer + verify + delete

| | |
|---|---|
| **Operation** | Create → Read (verify) → Delete |
| **Object** | Index `smoke-custom-analyzer-idx` |
| **Request** | `PUT /indexes/smoke-custom-analyzer-idx` |
| **Body** | Index with `analyzers: [{name: "my_custom_analyzer", @odata.type: "#Microsoft.Azure.Search.CustomAnalyzer", tokenizer: "standard_v2", tokenFilters: ["lowercase", "asciifolding"]}]`; field `content` uses `analyzer: "my_custom_analyzer"` |
| **Expected Response** | `200` or `201` |
| **Verified** | Create 200/201; GET confirms `analyzers[].name` contains `"my_custom_analyzer"`; cleanup DELETE |
| **Result** | PASS |

---

## IDX-13: Create simple index

| | |
|---|---|
| **Operation** | Create |
| **Object** | Index (minimal, fields only) |
| **Request** | `PUT /indexes/{simple-index}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "fields": [{"name": "id", "type": "Edm.String", "key": true}, {"name": "title", "type": "Edm.String"}, {"name": "count", "type": "Edm.Int32"}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | PASS |

---

## IDX-14: Create index with all EDM types + verify + delete

| | |
|---|---|
| **Operation** | Create → Read (verify) → Delete |
| **Object** | Index `smoke-all-types-idx` |
| **Request** | `PUT /indexes/smoke-all-types-idx` |
| **Body** | 10 fields: Edm.String, Edm.Int32, Edm.Int64, Edm.Double, Edm.Boolean, Edm.DateTimeOffset, Edm.GeographyPoint, Collection(Edm.String), Collection(Edm.Int32), plus key |
| **Expected Response** | `200` or `201` |
| **Verified** | Create 200/201; GET confirms `fields["int32"].type` == `"Edm.Int32"` and `fields["geo"].type` == `"Edm.GeographyPoint"`; cleanup DELETE |
| **Result** | PASS |

---

## IDX-15: List aliases (expect empty)

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Aliases collection |
| **Request** | `GET /aliases?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `value` array has length 0 (configured SKU quota = 0 aliases) |
| **Result** | PASS |

---

## IDX-16: Create alias (rejected, quota=0)

| | |
|---|---|
| **Operation** | Create (expected rejection) |
| **Object** | Alias |
| **Request** | `PUT /aliases/{alias}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "{alias}", "indexes": ["{index}"]}` |
| **Expected Response** | `429` |
| **Verified** | Status 429; response text contains `"Only 0 can be created"` |
| **Result** | **FAIL** — [Bug 5177274](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/5177274) (SSL handshake failure on PPE, ~50% TLS error rate) |
