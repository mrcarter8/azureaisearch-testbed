# Phase 15 — Advanced Filters

**API:** Data plane `2025-11-01-preview`  
**Result:** 20/20 passed

---

## FLT-01: search.in() with comma delimiter

| | |
|---|---|
| **Operation** | Search with search.in() filter |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "search.in(Category, 'Luxury,Boutique', ',')", "select": "HotelId, HotelName, Category", "count": true}` |
| **Verified** | Status 200; all results have Category in (Luxury, Boutique); count >= 2 |
| **Result** | PASS |

---

## FLT-02: search.in() with pipe delimiter

| | |
|---|---|
| **Operation** | Search with search.in() using pipe separator |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "search.in(Category, 'Luxury|Suite', '|')", "select": "HotelId, Category", "count": true}` |
| **Verified** | Status 200; all results have Category in (Luxury, Suite) |
| **Result** | PASS |

---

## FLT-03: Rooms/any() with BaseRate lambda

| | |
|---|---|
| **Operation** | Collection lambda filter on complex type |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Rooms/any(r: r/BaseRate lt 200)", "select": "HotelId, HotelName, Rooms", "count": true}` |
| **Verified** | Status 200; every result has at least one Room with BaseRate < 200 |
| **Result** | PASS |

---

## FLT-04: Rooms/all() non-smoking

| | |
|---|---|
| **Operation** | Collection all() operator — no smoking rooms |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Rooms/all(r: not r/SmokingAllowed)", "select": "HotelId, HotelName, Rooms", "count": true}` |
| **Verified** | Status 200; no result has a Room with SmokingAllowed=true (includes docs with empty Rooms) |
| **Result** | PASS |

---

## FLT-05: Double-nested any — Rooms/any(r: r/Tags/any())

| | |
|---|---|
| **Operation** | Double-nested lambda on collection within complex type |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Rooms/any(r: r/Tags/any(t: t eq 'suite'))", "select": "HotelId, HotelName, Rooms", "count": true}` |
| **Verified** | Status 200; every result has a Room containing 'suite' in its Tags |
| **Result** | PASS |

---

## FLT-06: not Rooms/any() — empty collection

| | |
|---|---|
| **Operation** | Negated any() — docs with no Rooms |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "not Rooms/any()", "select": "HotelId, HotelName, Rooms", "count": true}` |
| **Verified** | Status 200; all results have empty/null Rooms collection |
| **Result** | PASS |

---

## FLT-07: search.in() on collection with lambda

| | |
|---|---|
| **Operation** | search.in() within Tags/any() lambda |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Tags/any(t: search.in(t, 'pool,spa', ','))", "select": "HotelId, HotelName, Tags", "count": true}` |
| **Verified** | Status 200; every result has 'pool' or 'spa' in Tags |
| **Result** | PASS |

---

## FLT-08: ne operator — Category ne 'Boutique'

| | |
|---|---|
| **Operation** | Not-equal filter on string field |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Category ne 'Boutique'", "select": "HotelId, Category", "count": true}` |
| **Verified** | Status 200; no result has Category == 'Boutique' |
| **Result** | PASS |

---

## FLT-09: not() with parenthesized precedence

| | |
|---|---|
| **Operation** | Negation — not (Rating gt 4) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "not (Rating gt 4)", "select": "HotelId, HotelName, Rating", "count": true}` |
| **Verified** | Status 200; all non-null Rating values are <= 4 |
| **Result** | PASS |

---

## FLT-10: Bounded range filter

| | |
|---|---|
| **Operation** | Range filter on Rating [2, 3] |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Rating ge 2 and Rating le 3", "select": "HotelId, HotelName, Rating", "count": true}` |
| **Verified** | Status 200; every result has Rating in [2.0, 3.0] |
| **Result** | PASS |

---

## FLT-11: Not-null comparison on filterable field

| | |
|---|---|
| **Operation** | Null exclusion filter |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "ParkingIncluded ne null", "select": "HotelId, HotelName, ParkingIncluded", "count": true}` |
| **Verified** | Status 200; every result has non-null ParkingIncluded |
| **Result** | PASS |

---

## FLT-12: geo.distance validated — NYC only

| | |
|---|---|
| **Operation** | Geo-distance filter with city validation |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "geo.distance(Location, geography'POINT(-73.9857 40.7484)') le 5", "select": "HotelId, HotelName, Address/City", "count": true}` |
| **Verified** | Status 200; every result has Address/City == 'New York' |
| **Result** | PASS |

---

## FLT-13: search.ismatch in filter

| | |
|---|---|
| **Operation** | Full-text search as filter predicate |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "search.ismatch('luxury', 'Description')", "select": "HotelId, HotelName, Description", "count": true}` |
| **Verified** | Status 200; >= 1 result containing 'luxury' in Description |
| **Result** | PASS |

---

## FLT-14: search.ismatchscoring + Rating filter

| | |
|---|---|
| **Operation** | Scoring-contributing text match combined with OData filter |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "search.ismatchscoring('luxury amenities') and Rating ge 3", "select": "HotelId, HotelName, Rating", "count": true}` |
| **Verified** | Status 200; all results have Rating >= 3; all have @search.score > 0 |
| **Result** | PASS |

---

## FLT-15: Complex type equality — Address/StateProvince

| | |
|---|---|
| **Operation** | Filter on complex type sub-field |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Address/StateProvince eq 'NY'", "select": "HotelId, HotelName, Address", "count": true}` |
| **Verified** | Status 200; all results have Address/StateProvince == 'NY' |
| **Result** | PASS |

---

## FLT-16: Chained complex type filters

| | |
|---|---|
| **Operation** | AND filter on two complex type sub-fields |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Address/Country eq 'USA' and Address/City ne 'New York'", "select": "HotelId, HotelName, Address", "count": true}` |
| **Verified** | Status 200; all results have Country == 'USA' and City != 'New York' |
| **Result** | PASS |

---

## FLT-17: Date range filter

| | |
|---|---|
| **Operation** | Date range on LastRenovationDate [2019, 2021) |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "LastRenovationDate ge 2019-01-01T00:00:00Z and LastRenovationDate lt 2021-01-01T00:00:00Z", "select": "HotelId, HotelName, LastRenovationDate", "count": true}` |
| **Verified** | Status 200; all results have date in [2019, 2021) |
| **Result** | PASS |

---

## FLT-18: Boolean filter with count cross-check

| | |
|---|---|
| **Operation** | ParkingIncluded eq true with partition cross-check |
| **Request** | 3× `POST /indexes/{index}/docs/search` |
| **Verified** | Status 200; all results have ParkingIncluded == true; count(true) + count(ne true) == total |
| **Result** | PASS |

---

## FLT-19: Filter + orderby combination

| | |
|---|---|
| **Operation** | Filter Category eq 'Luxury' with orderby Rating desc |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "*", "filter": "Category eq 'Luxury'", "orderby": "Rating desc", "select": "HotelId, HotelName, Category, Rating"}` |
| **Verified** | Status 200; all results are Luxury category; ratings in descending order |
| **Result** | PASS |

---

## FLT-20: Filter + keyword search

| | |
|---|---|
| **Operation** | Keyword + OData filter together |
| **Request** | `POST /indexes/{index}/docs/search` |
| **Body** | `{"search": "hotel", "filter": "Rating ge 4", "select": "HotelId, HotelName, Rating", "count": true}` |
| **Verified** | Status 200; all results have Rating >= 4; all have positive @search.score |
| **Result** | PASS |
