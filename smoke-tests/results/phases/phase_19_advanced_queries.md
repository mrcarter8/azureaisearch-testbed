# Phase 19 — Advanced Queries (Suggest, Autocomplete, Fuzzy)

**API:** Data plane `2025-11-01-preview`  
**Result:** 12/12 passed

Exercises the Suggest and Autocomplete APIs on the hotels index using the `sg` suggester (analyzingInfixMatching on Address/City, Address/Country, Rooms/Type, Rooms/Tags). Covers fuzzy matching, highlighting, filters, and edge cases.

---

## ADV-01: Fuzzy suggest returns results for misspelling

| | |
|---|---|
| **Operation** | Suggest with fuzzy=true on a misspelled city name |
| **Request** | `POST /indexes/{index}/docs/suggest` with `search: "New Yrok", fuzzy: true` |
| **Verified** | Status 200; >= 1 suggestion returned |
| **Result** | PASS |

---

## ADV-02: Suggest with filter narrows results

| | |
|---|---|
| **Operation** | Suggest with OData filter |
| **Request** | `POST /indexes/{index}/docs/suggest` with `filter: "Rating ge 4"` |
| **Verified** | Status 200; all suggestions have Rating >= 4 |
| **Result** | PASS |

---

## ADV-03: Suggest top=2 limits count

| | |
|---|---|
| **Operation** | Suggest with top parameter |
| **Request** | `POST /indexes/{index}/docs/suggest` with `top: 2` |
| **Verified** | Status 200; <= 2 suggestions returned |
| **Result** | PASS |

---

## ADV-04: Suggest with highlight tags

| | |
|---|---|
| **Operation** | Suggest with highlightPreTag and highlightPostTag |
| **Request** | `POST /indexes/{index}/docs/suggest` with highlight tags `<em>` / `</em>` |
| **Verified** | Status 200; @search.text values contain `<em>` highlight markers |
| **Result** | PASS |

---

## ADV-05: Autocomplete oneterm mode

| | |
|---|---|
| **Operation** | Autocomplete in oneterm mode |
| **Request** | `POST /indexes/{index}/docs/autocomplete` with `autocompleteMode: "oneTerm"` |
| **Verified** | Status 200; >= 1 result; each result.text is a single word (no spaces) |
| **Result** | PASS |

---

## ADV-06: Fuzzy autocomplete returns results

| | |
|---|---|
| **Operation** | Autocomplete with fuzzy=true on misspelled input |
| **Request** | `POST /indexes/{index}/docs/autocomplete` with `search: "Nw", fuzzy: true` |
| **Verified** | Status 200; response structure valid (value array present) |
| **Result** | PASS |

---

## ADV-07: Autocomplete twoTerms mode

| | |
|---|---|
| **Operation** | Autocomplete in twoTerms mode |
| **Request** | `POST /indexes/{index}/docs/autocomplete` with `autocompleteMode: "twoTerms"` |
| **Verified** | Status 200; >= 1 result |
| **Result** | PASS |

---

## ADV-08: Suggest with $select limits fields

| | |
|---|---|
| **Operation** | Suggest with select to return only specific fields |
| **Request** | `POST /indexes/{index}/docs/suggest` with `select: "HotelName,Rating"` |
| **Verified** | Status 200; results contain HotelName and Rating; no Address or other fields |
| **Result** | PASS |

---

## ADV-09: Suggest with $orderby

| | |
|---|---|
| **Operation** | Suggest with orderby on Rating desc |
| **Request** | `POST /indexes/{index}/docs/suggest` with `orderby: "Rating desc"` |
| **Verified** | Status 200; ratings in weakly descending order |
| **Result** | PASS |

---

## ADV-10: Suggest minimum coverage

| | |
|---|---|
| **Operation** | Suggest with minimumCoverage=80 |
| **Request** | `POST /indexes/{index}/docs/suggest` with `minimumCoverage: 80` |
| **Verified** | Status 200; @search.coverage >= 80 |
| **Result** | PASS |

---

## ADV-11: Autocomplete with filter

| | |
|---|---|
| **Operation** | Autocomplete with OData filter |
| **Request** | `POST /indexes/{index}/docs/autocomplete` with `filter: "Rating ge 4"` |
| **Verified** | Status 200; valid response structure |
| **Result** | PASS |

---

## ADV-12: Suggest empty query returns zero results

| | |
|---|---|
| **Operation** | Suggest with empty search string |
| **Request** | `POST /indexes/{index}/docs/suggest` with `search: ""` |
| **Verified** | Status 200; empty value array |
| **Result** | PASS |
