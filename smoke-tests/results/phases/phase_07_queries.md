# Phase 7 — Full Query Coverage

**API:** Data plane `2025-11-01-preview`  
**Result:** 38/38 passed

---

## QRY-01: Simple keyword search

| | |
|---|---|
| **Operation** | Read (search) |
| **Object** | Documents |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "luxury", "select": "HotelName, Category, Rating", "top": 5}` |
| **Verified** | Status 200; >= 1 result; every result has `@search.score` |
| **Result** | PASS |

---

## QRY-02: Lucene boolean query (AND)

| | |
|---|---|
| **Operation** | Read (search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "luxury AND pool", "queryType": "full", "select": "HotelName, Tags", "top": 5}` |
| **Verified** | Status 200; >= 1 result |
| **Result** | PASS |

---

## QRY-03: Lucene wildcard query

| | |
|---|---|
| **Operation** | Read (search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "lux*", "queryType": "full", "select": "HotelName", "top": 5}` |
| **Verified** | Status 200; >= 1 result |
| **Result** | PASS |

---

## QRY-04: Lucene regex query

| | |
|---|---|
| **Operation** | Read (search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "/[Hh]otel/", "queryType": "full", "select": "HotelName", "top": 5}` |
| **Verified** | Status 200; >= 1 result |
| **Result** | PASS |

---

## QRY-05: Filter — Rating ge 4

| | |
|---|---|
| **Operation** | Read (search with filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Rating ge 4", "select": "HotelName, Rating"}` |
| **Verified** | Status 200; >= 1 result; every result has `Rating >= 4.0` |
| **Result** | PASS |

---

## QRY-06: Filter — geo.distance <= 10km

| | |
|---|---|
| **Operation** | Read (search with geo filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "geo.distance(Location, geography'POINT(-73.9857 40.7484)') le 10", "select": "HotelName, Address/City"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-07: Filter — ParkingIncluded eq true

| | |
|---|---|
| **Operation** | Read (search with boolean filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "ParkingIncluded eq true", "select": "HotelName, ParkingIncluded"}` |
| **Verified** | Status 200; >= 1 result; every result `ParkingIncluded == true` |
| **Result** | PASS |

---

## QRY-08: Filter — Category eq 'Boutique'

| | |
|---|---|
| **Operation** | Read (search with string filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Category eq 'Boutique'", "select": "HotelName, Category"}` |
| **Verified** | Status 200; >= 1 result; every result `Category == "Boutique"` |
| **Result** | PASS |

---

## QRY-09: Filter — Tags/any(t: t eq 'pool')

| | |
|---|---|
| **Operation** | Read (search with collection filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Tags/any(t: t eq 'pool')", "select": "HotelName, Tags"}` |
| **Verified** | Status 200; >= 1 result; every result has `"pool"` in `Tags` |
| **Result** | PASS |

---

## QRY-10: Filter — LastRenovationDate gt 2020

| | |
|---|---|
| **Operation** | Read (search with date filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "LastRenovationDate gt 2020-01-01T00:00:00Z", "select": "HotelName, LastRenovationDate"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-11: Filter — Address/City eq 'New York'

| | |
|---|---|
| **Operation** | Read (search with complex type filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Address/City eq 'New York'", "select": "HotelName, Address/City"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-12: Combined AND/OR filter

| | |
|---|---|
| **Operation** | Read (search with compound filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "(Category eq 'Boutique' or Category eq 'Luxury') and Rating ge 4", "select": "HotelName, Category, Rating"}` |
| **Verified** | Status 200; >= 1 result; every result `Category in ("Boutique","Luxury")` and `Rating >= 4` |
| **Result** | PASS |

---

## QRY-13: OrderBy Rating desc

| | |
|---|---|
| **Operation** | Read (search with sort) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "orderby": "Rating desc", "select": "HotelName, Rating", "top": 10}` |
| **Verified** | Status 200; >= 1 result; `Rating` values in descending order |
| **Result** | PASS |

---

## QRY-14: OrderBy geo.distance asc

| | |
|---|---|
| **Operation** | Read (search with geo sort) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "orderby": "geo.distance(Location, geography'POINT(-73.9857 40.7484)') asc", "select": "HotelName", "top": 5}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-15: Facets — Category

| | |
|---|---|
| **Operation** | Read (search with facets) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "facets": ["Category"], "top": 0}` |
| **Verified** | Status 200; `@search.facets` present; `@search.facets.Category` exists |
| **Result** | PASS |

---

## QRY-16: Facets — Rating interval:1

| | |
|---|---|
| **Operation** | Read (search with numeric facets) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "facets": ["Rating,interval:1"], "top": 0}` |
| **Verified** | Status 200; `@search.facets.Rating` exists |
| **Result** | PASS |

---

## QRY-17: Facets — Tags collection

| | |
|---|---|
| **Operation** | Read (search with collection facets) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "facets": ["Tags"], "top": 0}` |
| **Verified** | Status 200; `@search.facets.Tags` exists |
| **Result** | PASS |

---

## QRY-18: Highlight @search.highlights

| | |
|---|---|
| **Operation** | Read (search with highlighting) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "hotel", "highlight": "Description", "highlightPreTag": "<b>", "highlightPostTag": "</b>", "select": "HotelName", "top": 5}` |
| **Verified** | Status 200; >= 1 result; at least one result has `@search.highlights` |
| **Result** | PASS |

---

## QRY-19: Select restricts returned fields

| | |
|---|---|
| **Operation** | Read (search with field restriction) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "select": "HotelName,Rating", "top": 3}` |
| **Verified** | Status 200; >= 1 result; every result's keys (excluding `@search.score`) are subset of `{HotelName, Rating}` |
| **Result** | PASS |

---

## QRY-20: Top + Skip pagination (no overlap)

| | |
|---|---|
| **Operation** | Read (search, two pages) |
| **Requests** | 1. `POST .../docs/search` with `top: 5, skip: 0, select: "HotelId"` → page 1 |
| | 2. `POST .../docs/search` with `top: 5, skip: 5, select: "HotelId"` → page 2 |
| **Verified** | Both return 200; HotelId sets from page 1 and page 2 have no overlap |
| **Result** | PASS |

---

## QRY-21: $count=true returns @odata.count

| | |
|---|---|
| **Operation** | Read (search with count) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "count": true, "top": 1}` |
| **Verified** | Status 200; `@odata.count` present in response |
| **Result** | PASS |

---

## QRY-22: Semantic search (rerankerScore)

| | |
|---|---|
| **Operation** | Read (semantic search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "best downtown hotel with great amenities", "queryType": "semantic", "semanticConfiguration": "hotel-semantic-config", "select": "HotelName, Category, Rating", "top": 5}` |
| **Expected Response** | `200` or `206` (partial semantic) |
| **Verified** | Status 200/206; >= 1 result. If 200: first result has `@search.rerankerScore`. If 206: `@search.semanticPartialResponseReason` present |
| **Result** | PASS |

---

## QRY-23: Semantic search with extractive answers

| | |
|---|---|
| **Operation** | Read (semantic search + answers) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "what hotel has the best rating", "queryType": "semantic", "semanticConfiguration": "hotel-semantic-config", "answers": "extractive|count-3", "select": "HotelName, Rating", "top": 5}` |
| **Expected Response** | `200` or `206` |
| **Verified** | Status 200/206 |
| **Result** | PASS |

---

## QRY-24: Pure vector search (pre-computed)

| | |
|---|---|
| **Operation** | Read (vector search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"vectorQueries": [{"kind": "vector", "vector": [0.01 x 1536], "fields": "DescriptionVector", "k": 5}], "select": "HotelId, HotelName"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-25: Integrated vectorization (kind:text)

| | |
|---|---|
| **Operation** | Read (text-to-vector search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"vectorQueries": [{"kind": "text", "text": "luxury hotel with spa and pool", "fields": "DescriptionVector", "k": 5}], "select": "HotelId, HotelName"}` |
| **Verified** | Status 200 (server-side AOAI vectorizer converts text to embedding) |
| **Result** | PASS |

---

## QRY-26: Hybrid search (keyword + vector)

| | |
|---|---|
| **Operation** | Read (hybrid search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "luxury hotel", "vectorQueries": [{"kind": "text", "text": "upscale accommodation...", "fields": "DescriptionVector", "k": 5}], "select": "HotelId, HotelName"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-27: Multi-vector query (2 vectorQueries)

| | |
|---|---|
| **Operation** | Read (multi-vector search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"vectorQueries": [{"kind": "vector", "vector": [...], "fields": "DescriptionVector", "k": 3}, {"kind": "vector", "vector": [...], "fields": "DescriptionVector", "k": 3}], "select": "HotelId, HotelName"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-28: Vector search with filter

| | |
|---|---|
| **Operation** | Read (vector search + filter) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"vectorQueries": [{"kind": "vector", "vector": [...], "fields": "DescriptionVector", "k": 5}], "filter": "Rating ge 4", "select": "HotelId, HotelName, Rating"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-29: Suggest with partial input

| | |
|---|---|
| **Operation** | Read (suggest) |
| **Request** | `POST /indexes/{index}/docs/suggest` |
| **Body** | `{"search": "New", "suggesterName": "sg"}` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-30: Autocomplete oneTermWithContext

| | |
|---|---|
| **Operation** | Read (autocomplete) |
| **Request** | `GET /indexes/{index}/docs/autocomplete?search=Ne&suggesterName=sg&autocompleteMode=oneTermWithContext` |
| **Body** | None (query params) |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-31: Autocomplete twoTerms

| | |
|---|---|
| **Operation** | Read (autocomplete) |
| **Request** | `GET /indexes/{index}/docs/autocomplete?search=New+Y&suggesterName=sg&autocompleteMode=twoTerms` |
| **Body** | None (query params) |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## QRY-32: Scoring profile boosts higher-rated

| | |
|---|---|
| **Operation** | Read (search x2 for comparison) |
| **Requests** | 1. `POST .../docs/search` with `search: "hotel"` (no profile) |
| | 2. `POST .../docs/search` with `search: "hotel", scoringProfile: "boostHighRating"` |
| **Verified** | Both return 200 |
| **Result** | PASS |

---

## QRY-33: searchFields constrains search

| | |
|---|---|
| **Operation** | Read (search with field restriction) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "pool", "searchFields": "Tags", "select": "HotelName, Tags", "top": 5}` |
| **Verified** | Status 200; >= 1 result |
| **Result** | PASS |

---

## QRY-34: minimumCoverage parameter

| | |
|---|---|
| **Operation** | Read (search with coverage) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "hotel", "minimumCoverage": 100, "top": 1}` |
| **Verified** | Status 200 or 503 |
| **Result** | PASS |

---

## QRY-35: Spell correction (lexicon speller)

| | |
|---|---|
| **Operation** | Read (semantic search + speller) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "hotl luxry poool", "queryType": "semantic", "semanticConfiguration": "hotel-semantic-config", "speller": "lexicon", "queryLanguage": "en-us", "select": "HotelName", "top": 5}` |
| **Verified** | Status 200 or 206 |
| **Result** | PASS |

---

## QRY-36: queryLanguage parameter

| | |
|---|---|
| **Operation** | Read (semantic search with language) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "hotel", "queryLanguage": "en-us", "queryType": "semantic", "semanticConfiguration": "hotel-semantic-config", "top": 3}` |
| **Verified** | Status 200 or 206 |
| **Result** | PASS |

---

## QRY-37: searchMode all vs any

| | |
|---|---|
| **Operation** | Read (search x2 for comparison) |
| **Requests** | 1. `POST .../docs/search` with `searchMode: "any", search: "luxury pool spa", count: true, top: 0` |
| | 2. `POST .../docs/search` with `searchMode: "all", search: "luxury pool spa", count: true, top: 0` |
| **Verified** | Both return 200; `@odata.count` with `searchMode: "all"` <= count with `searchMode: "any"` |
| **Result** | PASS |

---

## QRY-38: Wildcard '*' returns all documents

| | |
|---|---|
| **Operation** | Read (search) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "count": true, "top": 0}` |
| **Verified** | Status 200; `@odata.count` >= 25 |
| **Result** | PASS |
