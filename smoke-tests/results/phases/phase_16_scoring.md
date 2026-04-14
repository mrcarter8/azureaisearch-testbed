# Phase 16 — Scoring Profiles

**API:** Data plane `2025-11-01-preview`  
**Result:** 14/14 passed

---

## SCR-01: Scoring profile changes scores

| | |
|---|---|
| **Operation** | Compare scores with/without boostHighRating profile |
| **Request** | 2× `POST /indexes/{index}/docs/search` (with and without scoringProfile) |
| **Verified** | Status 200; score arrays differ when profile is applied |
| **Result** | PASS |

---

## SCR-02: Magnitude boost favors high Rating

| | |
|---|---|
| **Operation** | Magnitude function on Rating field |
| **Request** | `POST /indexes/{index}/docs/search` with `scoringProfile: "boostHighRating"` |
| **Verified** | Status 200; top result has Rating >= 4.0 |
| **Result** | PASS |

---

## SCR-03: Freshness boost changes ordering

| | |
|---|---|
| **Operation** | Freshness function on LastRenovationDate |
| **Request** | 2× `POST /indexes/{index}/docs/search` |
| **Verified** | Status 200; result order or scores differ with profile vs without |
| **Result** | PASS |

---

## SCR-04: Profile + filter together

| | |
|---|---|
| **Operation** | Scoring profile with OData filter |
| **Request** | `POST /indexes/{index}/docs/search` with `scoringProfile + filter: "Rating ge 3"` |
| **Verified** | Status 200; all results satisfy filter; all have positive @search.score |
| **Result** | PASS |

---

## SCR-05: orderby overrides scoring profile

| | |
|---|---|
| **Operation** | orderby takes precedence over profile ordering |
| **Request** | `POST /indexes/{index}/docs/search` with `scoringProfile + orderby: "Rating asc"` |
| **Verified** | Status 200; ratings in ascending order despite descending profile |
| **Result** | PASS |

---

## SCR-06: Profile does not change result count

| | |
|---|---|
| **Operation** | Same query with/without profile — count identical |
| **Request** | 2× `POST /indexes/{index}/docs/search` with `count: true, top: 0` |
| **Verified** | @odata.count identical with and without profile |
| **Result** | PASS |

---

## SCR-07: Invalid profile name — 400

| | |
|---|---|
| **Operation** | Non-existent scoring profile name |
| **Request** | `POST /indexes/{index}/docs/search` with `scoringProfile: "nonexistent-profile-99"` |
| **Verified** | Status 400 |
| **Result** | PASS |

---

## SCR-08: Profile + pagination — no overlap

| | |
|---|---|
| **Operation** | top/skip with scoring profile |
| **Request** | 2× `POST /indexes/{index}/docs/search` (page 1 and page 2) |
| **Verified** | No HotelId overlap between pages |
| **Result** | PASS |

---

## SCR-09: Profile with wildcard search

| | |
|---|---|
| **Operation** | Scoring profile with `search: "*"` |
| **Request** | `POST /indexes/{index}/docs/search` with `search: "*", scoringProfile: "boostHighRating"` |
| **Verified** | Status 200; all results have @search.score |
| **Result** | PASS |

---

## SCR-10: Profile + searchMode all

| | |
|---|---|
| **Operation** | Scoring profile combined with searchMode: all |
| **Request** | `POST /indexes/{index}/docs/search` with `search: "luxury pool", searchMode: "all", scoringProfile: "boostHighRating"` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## SCR-11: Profile + select restriction

| | |
|---|---|
| **Operation** | Scoring profile with $select |
| **Request** | `POST /indexes/{index}/docs/search` with `select: "HotelName, Rating"` |
| **Verified** | Status 200; only HotelName and Rating fields returned (plus @search.score) |
| **Result** | PASS |

---

## SCR-12: Profile + semantic reranking

| | |
|---|---|
| **Operation** | Profile + queryType: semantic |
| **Request** | `POST /indexes/{index}/docs/search` with `scoringProfile + queryType: "semantic"` |
| **Verified** | Status 200/206; results have @search.rerankerScore when 200 |
| **Result** | PASS |

---

## SCR-13: Tag scoring profile (temp index)

| | |
|---|---|
| **Operation** | Create index with tag scoring profile → upload docs → search with tag boost |
| **Request** | `PUT /indexes/smoke-scr-tag` + `POST .../docs/index` + `POST .../docs/search` with `scoringParameters: ["boostTags-python"]` |
| **Verified** | Index created (201); docs uploaded; search returns results with 'python'-tagged doc on top |
| **Cleanup** | Index deleted |
| **Result** | PASS |

---

## SCR-14: Text weights profile (temp index)

| | |
|---|---|
| **Operation** | Create index with text weights → verify title-heavy weighting boosts title matches |
| **Request** | `PUT /indexes/smoke-scr-wgt` + `POST .../docs/index` + 2× search (with/without profile) |
| **Verified** | With titleHeavy profile, doc with search term in title ranks first |
| **Cleanup** | Index deleted |
| **Result** | PASS |
