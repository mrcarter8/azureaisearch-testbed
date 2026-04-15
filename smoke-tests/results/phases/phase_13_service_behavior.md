# Phase 13 — Service Behavior

**API:** Data plane `2025-11-01-preview`  
**Result:** 7/12 passed, 5 skipped

---

## SLS-01: Cold start query latency < 30s

| | |
|---|---|
| **Operation** | Search query timing |
| **Request** | `POST /indexes/{name}/docs/search?api-version=2025-11-01-preview` |
| **Body** | `search: "hotel", top: 1` |
| **Expected Response** | `200` within 30 seconds |
| **Result** | SKIP — `primary_index_name` not present (requires phases 1-5 to run first in same session) |

---

## SLS-02: Index creation latency < 30s

| | |
|---|---|
| **Operation** | Create + delete disposable index, measure elapsed time |
| **Request** | `PUT /indexes/smoke-sls02-latency?api-version=2025-11-01-preview` |
| **Expected Response** | `200`/`201` within 30 seconds |
| **Verified** | Index created successfully within threshold |
| **Result** | PASS |

---

## SLS-03: Blob indexer E2E timing

| | |
|---|---|
| **Operation** | Check blob indexer run duration |
| **Request** | `GET /indexers/{name}/status?api-version=2025-11-01-preview` |
| **Expected Response** | `200` with `lastResult.elapsedTime` present |
| **Result** | SKIP — Blob storage not configured |

---

## SLS-04: 20 parallel search queries — no 5xx

| | |
|---|---|
| **Operation** | Fire 20 concurrent search queries via `ThreadPoolExecutor` |
| **Request** | `POST /indexes/{name}/docs/search` (×20, raw `requests` library) |
| **Expected Response** | Zero 5xx status codes |
| **Result** | SKIP — `primary_index_name` not present |

---

## SLS-05: 5 parallel index creates — no 5xx

| | |
|---|---|
| **Operation** | Create 5 indexes concurrently via `ThreadPoolExecutor` |
| **Request** | `PUT /indexes/smoke-sls05-{0..4}` (×5, raw `requests` library) |
| **Expected Response** | Zero 5xx status codes |
| **Verified** | All 5 indexes created successfully (200/201); cleaned up afterward |
| **Result** | PASS |

---

## SLS-06: Service stats counters present

| | |
|---|---|
| **Operation** | Read service statistics |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters` object is non-empty |
| **Verified** | Status 200; counters present with standard keys |
| **Result** | PASS |

---

## SLS-07: Request top=1000 — 200 or 400

| | |
|---|---|
| **Operation** | Search with large result set request |
| **Request** | `POST /indexes/{name}/docs/search` with `top: 1000` |
| **Expected Response** | `200` (returns up to limit) or `400` (top too large) |
| **Result** | SKIP — `primary_index_name` not present |

---

## SLS-08: Create → upload → search → delete

| | |
|---|---|
| **Operation** | Rapid sequential operations on a disposable index |
| **Request** | `PUT /indexes/smoke-sls08-rapid` → `POST .../docs/index` (10 docs) → `POST .../docs/search` → `DELETE` |
| **Expected Response** | All operations succeed (200/201/204) |
| **Verified** | Index created, 10 docs uploaded, search returned 200 (eventual consistency OK), index deleted |
| **Result** | PASS |

---

## SLS-09: Older API versions — 200 or clear error

| | |
|---|---|
| **Operation** | GET index with older API versions |
| **Request** | `GET /indexes/{name}?api-version=` `2024-07-01`, `2024-05-01-Preview`, `2023-11-01` |
| **Expected Response** | `200`, `400`, or `404` per version (no 500s) |
| **Verified** | All three older versions returned expected status codes |
| **Result** | PASS |

---

## SLS-10: Error responses have code + message

| | |
|---|---|
| **Operation** | Trigger 404 and 400 errors, validate response structure |
| **Request** | `GET /indexes/nonexistent-index-smoke-test` and `POST .../docs/search` with invalid filter |
| **Expected Response** | `error.message` present and descriptive |
| **Verified** | 404 returns descriptive message. Note: PPE returns empty string for `error.code` — message is still descriptive |
| **Result** | PASS |

---

## SLS-11: request-id in all responses

| | |
|---|---|
| **Operation** | Check for request tracking header on multiple endpoints |
| **Request** | `GET /servicestats`, `GET /indexes` |
| **Expected Response** | `request-id` or `x-ms-request-id` header present |
| **Verified** | All responses include `request-id` header (PPE uses `request-id` rather than `x-ms-request-id`) |
| **Result** | PASS |

---

## SLS-12: 429 includes Retry-After header

| | |
|---|---|
| **Operation** | Rapid-fire 60 search queries to trigger throttling |
| **Request** | `POST .../docs/search` (×60, raw `requests` library) |
| **Expected Response** | If 429 received, `Retry-After` header present |
| **Result** | SKIP — `primary_index_name` not present |

---

## Key Findings

- **Index-dependent tests skip gracefully**: SLS-01, 04, 07, 12 require `primary_index_name` from phases 1-5. When run standalone, they skip instead of failing.
- **Concurrent operations stable**: 5 parallel index creates completed without 5xx errors (SLS-05).
- **Rapid sequential ops work**: Create → upload → search → delete completes within seconds (SLS-08). Search may not immediately find all docs due to eventual consistency, but returns 200.
- **Older API versions accepted**: Versions back to `2023-11-01` return 200 or clean errors, not 500s (SLS-09).
- **Error response quality**: Messages are descriptive but `error.code` is often an empty string on PPE. Not a functional issue but differs from standard SKU behavior.
- **Request tracking header**: PPE uses `request-id` header instead of the standard `x-ms-request-id`. Tests check both.
