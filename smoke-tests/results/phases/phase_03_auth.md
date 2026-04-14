# Phase 3 — Authentication & Authorization

**API:** Data plane `2025-11-01-preview`  
**Result:** 10/11 passed, 1 skipped (SEC-11)

---

## SEC-01: Admin key can read indexes (GATE)

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2025-11-01-preview` with `api-key: {admin-key}` header |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200 — admin key is authorized for read. GATE test: failure aborts entire run |
| **Result** | PASS |

---

## SEC-02: Admin key can create an index

| | |
|---|---|
| **Operation** | Create → Delete (cleanup) |
| **Object** | Index `smoke-auth-test-write` |
| **Request** | `PUT /indexes/smoke-auth-test-write?api-version=2025-11-01-preview` with `api-key: {admin-key}` |
| **Body** | `{"name": "smoke-auth-test-write", "fields": [{"name": "id", "type": "Edm.String", "key": true}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; cleanup `DELETE /indexes/smoke-auth-test-write` |
| **Result** | PASS |

---

## SEC-03: Query key can search

| | |
|---|---|
| **Operation** | Read (search) |
| **Object** | Documents |
| **Request** | `POST /indexes/{index}/docs/search?api-version=2025-11-01-preview` with `api-key: {query-key}` |
| **Body** | `{"search": "*", "top": 1}` |
| **Expected Response** | `200` (results) or `404` (index not yet created; auth still passed) |
| **Verified** | Status 200 or 404 — query key has search permission |
| **Result** | PASS |

---

## SEC-04: Query key cannot create index (rejected)

| | |
|---|---|
| **Operation** | Create (expected rejection) |
| **Object** | Index |
| **Request** | `PUT /indexes/smoke-query-write-test?api-version=2025-11-01-preview` with `api-key: {query-key}` |
| **Body** | `{"name": "smoke-query-write-test", "fields": [{"name": "id", "type": "Edm.String", "key": true}]}` |
| **Expected Response** | `401` or `403` |
| **Verified** | Status 401/403 — query key has no write permission |
| **Result** | PASS |

---

## SEC-05: Entra bearer token can read indexes

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2025-11-01-preview` with `Authorization: Bearer {entra-token}` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## SEC-06: Entra bearer token can create index

| | |
|---|---|
| **Operation** | Create → Delete (cleanup) |
| **Object** | Index `smoke-entra-write-test` |
| **Request** | `PUT /indexes/smoke-entra-write-test?api-version=2025-11-01-preview` with `Authorization: Bearer {entra-token}` |
| **Body** | `{"name": "smoke-entra-write-test", "fields": [{"name": "id", "type": "Edm.String", "key": true}]}` |
| **Expected Response** | `200`, `201`, or `204` |
| **Verified** | Status 200/201/204; cleanup DELETE |
| **Result** | PASS |

---

## SEC-07: No auth rejected

| | |
|---|---|
| **Operation** | Read (no credentials) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2025-11-01-preview` with no `api-key` or `Authorization` header |
| **Body** | None |
| **Expected Response** | `401` or `403` |
| **Verified** | Status 401/403 |
| **Result** | PASS |

---

## SEC-08: Invalid API key rejected

| | |
|---|---|
| **Operation** | Read (bad credentials) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2025-11-01-preview` with `api-key: this-is-not-a-valid-key` |
| **Body** | None |
| **Expected Response** | `401` or `403` |
| **Verified** | Status 401/403 |
| **Result** | PASS |

---

## SEC-09: Expired bearer token rejected

| | |
|---|---|
| **Operation** | Read (expired token) |
| **Object** | Indexes collection |
| **Request** | `GET /indexes?api-version=2025-11-01-preview` with `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired.invalid` |
| **Body** | None |
| **Expected Response** | `401` or `403` |
| **Verified** | Status 401/403 |
| **Result** | PASS |

---

## SEC-10: Entra RBAC can search

| | |
|---|---|
| **Operation** | Read (search) |
| **Object** | Documents |
| **Request** | `POST /indexes/{index}/docs/search?api-version=2025-11-01-preview` with `Authorization: Bearer {entra-token}` |
| **Body** | `{"search": "*", "top": 1}` |
| **Expected Response** | `200` or `404` |
| **Verified** | Status 200/404 — Entra token with RBAC can search |
| **Result** | PASS |

---

## SEC-11: Reader RBAC cannot write (skipped)

| | |
|---|---|
| **Operation** | Create (expected rejection) |
| **Object** | Index |
| **Request** | N/A — requires a dedicated reader-scoped service principal |
| **Verified** | N/A |
| **Result** | SKIP — requires dedicated reader-scoped SP not available in test setup |
