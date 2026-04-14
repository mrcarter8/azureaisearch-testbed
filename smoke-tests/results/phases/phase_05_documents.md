# Phase 5 — Document CRUD Operations

**API:** Data plane `2025-11-01-preview`  
**Result:** 12/12 passed

---

## DOC-01: Upload 25 documents (batch) — GATE

| | |
|---|---|
| **Operation** | Create (batch upload) |
| **Object** | Documents in primary index |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [...]}` — 25 documents with `@search.action: "upload"`. First 5 are fully populated hotel docs (HotelId, HotelName, Description, Description_fr, Category, Tags, ParkingIncluded, LastRenovationDate, Rating, Location, Address, Rooms). Remaining 20 are generated with varying categories and fields |
| **Expected Response** | `200` or `207` |
| **Verified** | Status 200/207; every result in `value[]` has `status: true` (no failures). GATE: failure aborts run |
| **Result** | PASS |

---

## DOC-02: Lookup document by key

| | |
|---|---|
| **Operation** | Read (single doc) |
| **Object** | Document HotelId=1 |
| **Request** | `GET /indexes/{index}/docs/1?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `HotelName` == `"Stay-Kay City Hotel"`; `Category` == `"Boutique"` |
| **Result** | PASS |

---

## DOC-03: Document count

| | |
|---|---|
| **Operation** | Read (count) |
| **Object** | Index document count |
| **Request** | `GET /indexes/{index}/docs/$count?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response body (plain text integer) == `25`. Polls up to 10 times with 3s delay to allow indexing propagation |
| **Result** | PASS |

---

## DOC-04: Merge document (update single field)

| | |
|---|---|
| **Operation** | Update (merge) → Read (verify) |
| **Object** | Document HotelId=1 |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "merge", "HotelId": "1", "Rating": 4.5}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Merge returns 200/207; follow-up `GET .../docs/1` confirms `Rating` == `4.5` and `HotelName` == `"Stay-Kay City Hotel"` (untouched field preserved) |
| **Result** | PASS |

---

## DOC-05: MergeOrUpload existing document

| | |
|---|---|
| **Operation** | Update (mergeOrUpload) → Read (verify) |
| **Object** | Document HotelId=2 |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "mergeOrUpload", "HotelId": "2", "Rating": 3.0}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Returns 200/207; `GET .../docs/2` confirms `Rating` == `3.0` |
| **Result** | PASS |

---

## DOC-06: MergeOrUpload new document

| | |
|---|---|
| **Operation** | Create (mergeOrUpload, new doc) → Read (verify) |
| **Object** | Document HotelId=26 |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "mergeOrUpload", "HotelId": "26", "HotelName": "Upserted Hotel", "Description": "Created via mergeOrUpload", "Rating": 3.5}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Returns 200/207; `GET .../docs/26` returns 200 (document exists) |
| **Result** | PASS |

---

## DOC-07: Delete document + verify 404

| | |
|---|---|
| **Operation** | Delete → Read (verify 404) |
| **Object** | Document HotelId=26 |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "delete", "HotelId": "26"}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Delete returns 200/207; after 2s wait, `GET .../docs/26` returns 404 |
| **Result** | PASS |

---

## DOC-08: Upload document with vector field

| | |
|---|---|
| **Operation** | Update (mergeOrUpload with vector) → Read (verify) |
| **Object** | Document HotelId=1 (DescriptionVector) |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "mergeOrUpload", "HotelId": "1", "DescriptionVector": [0.0, 0.0, ... (1536 floats)]}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Returns 200/207; `GET .../docs/1?$select=HotelId` returns 200 with `HotelId` == `"1"` |
| **Result** | PASS |

---

## DOC-09: Upload large document (~300KB)

| | |
|---|---|
| **Operation** | Update (mergeOrUpload large text) |
| **Object** | Document HotelId=1 (Description) |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "mergeOrUpload", "HotelId": "1", "Description": "hotel hotel hotel... (50,000 repetitions, ~300KB)"}]}` |
| **Expected Response** | `200`/`207` (accepted) or `400`/`413` (size limit) |
| **Verified** | Status is one of 200, 207, 400, or 413 |
| **Result** | PASS |

---

## DOC-10: Upload unicode doc (CJK, emoji) + verify

| | |
|---|---|
| **Operation** | Update (mergeOrUpload unicode) → Read (verify) |
| **Object** | Document HotelId=1 (Description) |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "mergeOrUpload", "HotelId": "1", "Description": "Hôtel de première classe 一流酒店 🏨 فندق فاخر Ñoño"}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Returns 200/207; `GET .../docs/1?$select=HotelId,Description` confirms Description contains `"一流酒店"` and `"🏨"` |
| **Result** | PASS |

---

## DOC-11: Batch upload 1000 documents

| | |
|---|---|
| **Operation** | Create (batch upload) |
| **Object** | 1000 documents in simple index |
| **Request** | `POST /indexes/{simple-index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [...]}` — 1000 docs with `id`, `title`, `count` fields |
| **Expected Response** | `200`/`207` (accepted) or `400`/`413` (batch size limit) |
| **Verified** | Status is one of 200, 207, 400, or 413 |
| **Result** | PASS |

---

## DOC-12: Upload doc with empty string fields

| | |
|---|---|
| **Operation** | Update (mergeOrUpload) |
| **Object** | Document HotelId=1 (Description_fr) |
| **Request** | `POST /indexes/{index}/docs/index?api-version=2025-11-01-preview` |
| **Body** | `{"value": [{"@search.action": "mergeOrUpload", "HotelId": "1", "Description_fr": ""}]}` |
| **Expected Response** | `200` or `207` |
| **Verified** | Status 200/207 |
| **Result** | PASS |
