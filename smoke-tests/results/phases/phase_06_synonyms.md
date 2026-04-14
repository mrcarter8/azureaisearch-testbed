# Phase 6 — Synonym Map CRUD

**API:** Data plane `2025-11-01-preview`  
**Result:** 5/6 passed, 1 intermittent SSL failure (SYN-01)

---

## SYN-01: Create synonym map (Solr rules)

| | |
|---|---|
| **Operation** | Create |
| **Object** | Synonym Map |
| **Request** | `PUT /synonymmaps('{synonym-map}')?api-version=2025-11-01-preview` |
| **Body** | `{"name": "{synonym-map}", "format": "solr", "synonyms": "inn, lodge, hotel\npool, swimming pool\nspa, wellness center, retreat\nfancy, luxury, upscale\nbudget, cheap, affordable\napartment => suite"}` |
| **Expected Response** | `200`, `201`, or `204` |
| **Verified** | Status 200/201/204 |
| **Result** | **FAIL** (intermittent SSL handshake failure on PPE — same root cause as Bug 5177274) |

---

## SYN-02: Read synonym map

| | |
|---|---|
| **Operation** | Read |
| **Object** | Synonym Map |
| **Request** | `GET /synonymmaps('{synonym-map}')?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `synonyms` field exists; `synonyms` contains `"hotel"` |
| **Result** | PASS |

---

## SYN-03: List synonym maps

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Synonym Maps collection |
| **Request** | `GET /synonymmaps?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `value[].name` contains our synonym map name |
| **Result** | PASS |

---

## SYN-04: Update synonym map + verify

| | |
|---|---|
| **Operation** | Update → Read (verify) |
| **Object** | Synonym Map |
| **Request** | `PUT /synonymmaps('{synonym-map}')?api-version=2025-11-01-preview` |
| **Body** | Updated synonyms: adds `"ocean, sea, beach"` rule to existing ruleset |
| **Expected Response** | `200` or `204` |
| **Verified** | PUT returns 200/204; follow-up GET confirms `synonyms` contains `"ocean"` |
| **Result** | PASS |

---

## SYN-05: Create + delete + verify synonym map

| | |
|---|---|
| **Operation** | Create → Delete → Read (verify 404) |
| **Object** | Synonym Map `smoke-syn-throwaway` |
| **Requests** | 1. `PUT /synonymmaps('smoke-syn-throwaway')` with `synonyms: "a, b, c"` |
| | 2. `DELETE /synonymmaps('smoke-syn-throwaway')` → 204 |
| | 3. `GET /synonymmaps('smoke-syn-throwaway')` → 404 |
| **Verified** | Delete returns 204; GET returns 404 |
| **Result** | PASS |

---

## SYN-06: Search 'inn' expands to 'hotel' via synonyms

| | |
|---|---|
| **Operation** | Read (search with synonym expansion) |
| **Object** | Documents |
| **Request** | `POST /indexes/{index}/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"search": "inn", "select": "HotelName, Description", "top": 5}` |
| **Expected Response** | `200` |
| **Verified** | Status 200; at least 1 result returned (synonym expansion `inn → hotel` matches hotel documents) |
| **Result** | PASS |
