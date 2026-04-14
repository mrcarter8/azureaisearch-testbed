# Phase 8 — Miscellaneous Service Operations

**API:** Data plane `2025-11-01-preview`  
**Result:** 10/10 passed

---

## MSC-01: Service statistics (counters)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Service Statistics |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `counters` |
| **Result** | PASS |

---

## MSC-02: Analyze API (standard.lucene)

| | |
|---|---|
| **Operation** | Read (analyze text) |
| **Object** | Analyzer output |
| **Request** | `POST /indexes/{index}/analyze?api-version=2025-11-01-preview` |
| **Body** | `{"text": "luxury hotel with pool and spa", "analyzer": "standard.lucene"}` |
| **Expected Response** | `200` |
| **Verified** | Status 200; `tokens` array has > 0 entries |
| **Result** | PASS |

---

## MSC-03: Analyze API (en.microsoft)

| | |
|---|---|
| **Operation** | Read (analyze text) |
| **Object** | Analyzer output |
| **Request** | `POST /indexes/{index}/analyze?api-version=2025-11-01-preview` |
| **Body** | `{"text": "world-class gaming & fine dining", "analyzer": "en.microsoft"}` |
| **Expected Response** | `200` |
| **Verified** | Status 200; `tokens` array has > 0 entries |
| **Result** | PASS |

---

## MSC-04: Bad API version (rejected 400)

| | |
|---|---|
| **Operation** | Read (invalid param) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2000-01-01` |
| **Body** | None |
| **Expected Response** | `400` |
| **Verified** | Status 400 |
| **Result** | PASS |

---

## MSC-05: Very old API version (rejected)

| | |
|---|---|
| **Operation** | Read (invalid param) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2014-07-31-Preview` |
| **Body** | None |
| **Expected Response** | `400` or `404` |
| **Verified** | Status 400 or 404 |
| **Result** | PASS |

---

## MSC-06: PUT with stale ETag (rejected 412)

| | |
|---|---|
| **Operation** | Read → Update (expected rejection) |
| **Object** | Index (ETag concurrency) |
| **Requests** | 1. `GET /indexes/{index}` — get current definition |
| | 2. `PUT /indexes/{index}` with `If-Match: "stale-etag-value"` header |
| **Expected Response** | `412` (Precondition Failed) |
| **Verified** | Status 412 |
| **Result** | PASS |

---

## MSC-07: PUT with If-None-Match:* (rejected 412)

| | |
|---|---|
| **Operation** | Update (expected rejection — index already exists) |
| **Object** | Index |
| **Request** | `PUT /indexes/{index}?api-version=2025-11-01-preview` with `If-None-Match: *` header |
| **Body** | `{"name": "{index}", "fields": [{"name": "HotelId", "type": "Edm.String", "key": true}]}` |
| **Expected Response** | `412` (Precondition Failed) |
| **Verified** | Status 412 — index already exists, If-None-Match:* prevents overwrite |
| **Result** | PASS |

---

## MSC-08: Malformed JSON body (rejected 400)

| | |
|---|---|
| **Operation** | Read (search with bad body) |
| **Object** | Documents |
| **Request** | `POST /indexes/{index}/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{{not valid json}}` (raw string, not parsed JSON) |
| **Expected Response** | `400` |
| **Verified** | Status 400. Note: uses raw `requests.post` with SSL retry loop (bypasses RestClient) |
| **Result** | PASS |

---

## MSC-09: Select nonexistent field (rejected)

| | |
|---|---|
| **Operation** | Read (search with bad select) |
| **Object** | Documents |
| **Request** | `POST /indexes/{index}/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"search": "*", "select": "NonExistentField", "top": 1}` |
| **Expected Response** | `400` or `404` |
| **Verified** | Status 400 or 404 |
| **Result** | PASS |

---

## MSC-10: Serverless stats limits check

| | |
|---|---|
| **Operation** | Read |
| **Object** | Service Statistics |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `counters` contains `documentCount` or `indexCounter` |
| **Result** | PASS |
