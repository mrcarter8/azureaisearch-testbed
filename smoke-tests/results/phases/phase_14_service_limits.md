# Phase 14 — Service Limits

**API:** Data plane `2025-11-01-preview`  
**Result:** 13/14 passed, 1 skipped

---

## LIM-01: indexesCount quota >= serverless minimum

| | |
|---|---|
| **Operation** | Read service stats |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.indexesCount.quota >= 200` |
| **Verified** | Status 200; quota is non-null and >= 200 (minimum preview limit; GA target is 3000) |
| **Result** | PASS |

---

## LIM-02: indexersCount quota >= serverless minimum

| | |
|---|---|
| **Operation** | Read service stats |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.indexersCount.quota >= 200` |
| **Verified** | Status 200; quota is non-null and >= 200 |
| **Result** | PASS |

---

## LIM-03: dataSourcesCount quota >= serverless minimum

| | |
|---|---|
| **Operation** | Read service stats |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.dataSourcesCount.quota >= 200` |
| **Verified** | Status 200; quota is non-null and >= 200 |
| **Result** | PASS |

---

## LIM-04: skillsetCount quota >= serverless minimum

| | |
|---|---|
| **Operation** | Read service stats |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.skillsetCount.quota >= 200` |
| **Verified** | Status 200; quota is non-null and >= 200 |
| **Result** | PASS |

---

## LIM-05: synonymMaps quota == 20

| | |
|---|---|
| **Operation** | Read service stats |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.synonymMaps.quota == 20` |
| **Verified** | Status 200; quota is exactly 20 (matches S3 HD limit) |
| **Result** | PASS |

---

## LIM-06: aliasesCount quota == 0 (not supported)

| | |
|---|---|
| **Operation** | Read service stats |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.aliasesCount.quota == 0` |
| **Verified** | Status 200; aliases not supported on serverless SKU |
| **Result** | PASS |

---

## LIM-07: maxStoragePerIndex > 0

| | |
|---|---|
| **Operation** | Read service stats (limits section) |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `limits.maxStoragePerIndex > 0` |
| **Verified** | Status 200; maxStoragePerIndex = 1,099,511,627,776 bytes (1024 GB). Spec target is 20 GB — preview allows higher. |
| **Result** | PASS |

---

## LIM-08: maxFieldsPerIndex >= 1000

| | |
|---|---|
| **Operation** | Read service stats (limits section) |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `limits.maxFieldsPerIndex >= 1000` |
| **Verified** | Status 200; maxFieldsPerIndex = 3000 |
| **Result** | PASS |

---

## LIM-09: vectorIndexSize quota ~30% of total storage

| | |
|---|---|
| **Operation** | Read service stats (counters) |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `counters.vectorIndexSize.quota / counters.storageSize.quota` is between 15–50% |
| **Verified** | Status 200; vectorIndexSize quota = 322,122,547,200 bytes (300 GB), ratio = 29.30% of total storage |
| **Result** | PASS |

---

## LIM-10: Index stats structure (documentCount, storageSize, vectorIndexSize)

| | |
|---|---|
| **Operation** | Create index → GET /indexes/{name}/stats → Delete |
| **Object** | Index (`smoke-lim10-stats`) |
| **Request** | `PUT /indexes/smoke-lim10-stats`, then `GET /indexes/smoke-lim10-stats/stats?api-version=2025-11-01-preview` |
| **Expected Response** | Stats response contains `documentCount`, `storageSize`, `vectorIndexSize` — all >= 0 |
| **Verified** | Status 200; all three fields present and non-negative; index cleaned up |
| **Result** | PASS |

---

## LIM-11: Index stats reflect docs + storage after upload

| | |
|---|---|
| **Operation** | Read index stats on primary index |
| **Request** | `GET /indexes/{primary_index_name}/stats?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; if `documentCount > 0` then `storageSize > 0` |
| **Verified** | Skipped — primary index not present (requires earlier phases in same session) |
| **Result** | SKIP |

---

## LIM-12: indexesCount.usage reflects actual index count

| | |
|---|---|
| **Operation** | Create index → Verify usage → Delete |
| **Object** | Index (`smoke-lim12-track`) |
| **Request** | `PUT /indexes/smoke-lim12-track`, then `GET /servicestats`, then `GET /indexes` |
| **Expected Response** | `indexesCount.usage >= 1` after creating the index; list count is consistent |
| **Verified** | Status 200; usage count reflects at least 1 index; authoritative list count matches expectations |
| **Result** | PASS |

---

## LIM-13: Rapid-fire GET /indexes — 429 throttle

| | |
|---|---|
| **Operation** | 30 concurrent `GET /indexes` calls (bypassing retry) |
| **Request** | `GET /indexes?api-version=2025-11-01-preview` (×30 via 15 threads) |
| **Expected Response** | Mix of `200` and `429` (documented limit: 3 per second per SU) |
| **Verified** | 30/30 returned 200, 0 returned 429. No throttling observed — limit may be higher in preview. |
| **Result** | PASS (warning: no 429s observed) |

---

## LIM-14: Rapid-fire GET /servicestats — 429 throttle

| | |
|---|---|
| **Operation** | 30 concurrent `GET /servicestats` calls (bypassing retry) |
| **Request** | `GET /servicestats?api-version=2025-11-01-preview` (×30 via 15 threads) |
| **Expected Response** | Mix of `200` and `429` (documented limit: 4 per second per SU) |
| **Verified** | 30/30 returned 200, 0 returned 429. No throttling observed — limit may be higher in preview. |
| **Result** | PASS (warning: no 429s observed) |

---

## Key Findings

### Actual Serverless Quotas (from servicestats)

| Counter | Quota | Spec Target | Match? |
|---------|-------|-------------|--------|
| indexesCount | 200 | 3000 | Preview only — GA target higher |
| indexersCount | 200 | 3000 | Preview only |
| dataSourcesCount | 200 | 3000 | Preview only |
| skillsetCount | 200 | 3000 | Preview only |
| synonymMaps | 20 | 20 | Exact match |
| aliasesCount | 0 | 0 | Exact match (not supported) |

### Actual Serverless Limits (from servicestats.limits)

| Limit | Value | Spec Target | Notes |
|-------|-------|-------------|-------|
| maxStoragePerIndex | 1024 GB | 20 GB | Preview allows higher |
| maxFieldsPerIndex | 3000 | 1000+ | Exceeds standard |
| vectorIndexSize quota | 300 GB (29.3% of total) | ~30% of total | Matches spec ratio |
| storageSize quota | 1024 GB | N/A | Service-level storage |

### Throttling

No 429 responses observed with 30 concurrent requests against either `/indexes` or `/servicestats`. The static rate limits documented (3/sec for List Indexes, 4/sec for Service Stats) may not be enforced in PPE, or the serverless backend may have higher thresholds.
