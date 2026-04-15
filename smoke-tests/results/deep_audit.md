# Deep Audit: Azure AI Search Smoke Test Suite

**Date**: 2025-07-17  
**Scope**: All 19 test phases (325+ tests)  
**Methodology**: Each test reviewed against Azure REST API documentation for expected response schemas, field semantics, and edge case behavior.

---

## Severity Key

| Rating | Meaning |
|--------|---------|
| 🔴 **CRITICAL** | Test can pass when the feature is fundamentally broken — false confidence |
| 🟠 **HIGH** | Test misses important validation that could hide real bugs |
| 🟡 **MEDIUM** | Test could be stronger but catches most failures |
| 🟢 **GOOD** | Solid assertions — only minor improvements possible |
| ✅ **EXCELLENT** | Gold standard — validates content, not just structure |

---

## Phase 1: Service Management (`test_01`) — 🟢 GOOD

**18 tests (SVC-01 to SVC-18)** — Management plane CRUD.

| Test | What it checks | Gap | Rating |
|------|---------------|-----|--------|
| SVC-01 | Service GET — validates name, SKU, status | None | ✅ |
| SVC-02 | List services — our service present | None | 🟢 |
| SVC-03 | Admin keys — validates keys returned | Doesn't check key format (32-char hex) | 🟡 |
| SVC-04 | Regenerate admin key — key changed | Good round-trip | ✅ |
| SVC-05 | Query keys — validates key & name present | None | 🟢 |
| SVC-06 | Create/delete query key | Good lifecycle test | 🟢 |
| SVC-07 | Update auth options | Round-trip validated | ✅ |
| SVC-08 | Semantic search config | Round-trip validated | ✅ |
| SVC-09 | CORS update | Round-trip validated | ✅ |
| SVC-10 | Managed identity | Validates principalId present | 🟢 |
| SVC-11 | CheckNameAvailability (taken) | Validates nameAvailable=false + reason | ✅ |
| SVC-12 | CheckNameAvailability (unique) | Validates nameAvailable=true | ✅ |
| SVC-13 | Public network access toggle | Round-trip validated | ✅ |
| SVC-14 | Disable local auth | Round-trip validated with revert | ✅ |
| SVC-15 | E-tag on service | Validates @odata.etag present | 🟢 |
| SVC-16 | Encryption enforcement | Round-trip validated | ✅ |
| SVC-17 | Semantic ranker update | Round-trip validated | ✅ |
| SVC-18 | Tags update | Round-trip validated | ✅ |

**Summary**: Well-written phase. No critical gaps.

---

## Phase 2: Negative Tests (`test_02`) — 🟢 GOOD

**~13 tests (NEG-01 to NEG-12+)** — Feature gate / negative path tests.

All tests appropriately accept multiple status code outcomes (e.g., 400/403/404) because serverless may reject certain operations differently than provisioned SKUs. Feature gate testing logic is sound.

**Summary**: Well-structured. No action needed.

---

## Phase 3: Auth (`test_03`) — 🟢 GOOD

**10 tests (SEC-01 to SEC-10)** — Authentication coverage.

| Test | What it checks | Gap | Rating |
|------|---------------|-----|--------|
| SEC-01 | Admin key reads index | Status 200 | 🟢 |
| SEC-02 | Admin key writes | Index PUT succeeds | 🟢 |
| SEC-03 | Query key searches | Status 200 | 🟢 |
| SEC-04 | Query key write rejected | 403 or 401 | 🟢 |
| SEC-05 | Entra bearer reads | Status 200 | 🟢 |
| SEC-06 | Entra bearer writes | PUT succeeds | 🟢 |
| SEC-07 | No auth rejected | 401 or 403 | 🟢 |
| SEC-08 | Invalid API key | 401 or 403 | 🟡 |
| SEC-09 | Expired bearer | 401 or 403 | 🟡 |
| SEC-10 | RBAC reader search | Status 200 | 🟢 |

**Summary**: Good coverage. SEC-08/09 could validate error body contains `"code"` and `"message"`.

---

## Phase 4: Indexes (`test_04`) — 🟢 GOOD

**~10 tests (IDX-01 to IDX-07+)** — Index CRUD with comprehensive schema.

`_full_index_body()` creates a full-featured index with all field types, vector config, suggesters, scoring profiles, semantic config, and CORS. Round-trip validation on GET after PUT. Field count validation. Statistics endpoint checked.

**Summary**: Well-structured. No critical gaps.

---

## Phase 5: Documents (`test_05`) — 🟢 MOSTLY GOOD

**22 tests (DOC-01 to DOC-22)** — Document CRUD operations.

| Test | What it checks | Gap | Rating |
|------|---------------|-----|--------|
| DOC-01 | Upload 25 — all item statuses succeeded | None | ✅ |
| DOC-02 | Lookup — validates specific field values | None | ✅ |
| DOC-03 | Count == 25 with retry | None | ✅ |
| DOC-04/05 | Merge — field updated AND others unchanged | None | ✅ |
| DOC-08 | Vector upload | Only verifies doc accessible via lookup, not that vector data is usable for search | 🟡 |
| DOC-10 | Unicode — CJK + emoji preserved | None | ✅ |
| DOC-11 | Batch 1000 | Checks `succeeded > 0` — should verify ALL 1000 succeeded | 🟠 |
| DOC-12 to 22 | Various merge/complex types | Generally thorough | 🟢 |

**Fixes needed**:
- DOC-11: Assert `succeeded == 1000` not just `> 0`

---

## Phase 6: Synonyms (`test_06`) — 🟡 MEDIUM

**6 tests (SYN-01 to SYN-06)** — Synonym map CRUD + expansion.

| Test | What it checks | Gap | Rating |
|------|---------------|-----|--------|
| SYN-01 | Create synonym map | Status only — no round-trip GET | 🟡 |
| SYN-02 | GET synonym map | Validates "hotel" in synonyms text | 🟢 |
| SYN-03 | List includes our map | Name present in list | 🟢 |
| SYN-04 | Update with new rule | Verifies "ocean" in updated rules | ✅ |
| SYN-05 | Create + delete lifecycle | 404 on GET after delete | ✅ |
| SYN-06 | Query expansion ("inn" → "hotel") | **Only checks results >= 1** — doesn't verify a hotel-related result was actually returned via synonym expansion | 🟠 |

**Fixes needed**:
- SYN-06: After searching "inn", verify results actually contain "hotel" in HotelName or Description — proving the synonym expansion worked

---

## Phase 7: Queries (`test_07`) — 🟡 MIXED

**38 tests (QRY-01 to QRY-38)** — Core query functionality.

| Test | What it checks | Gap | Severity |
|------|---------------|-----|----------|
| QRY-01 | Simple search + @search.score | Score present but not > 0 | 🟡 |
| QRY-02 | Lucene AND | **Only `assert_search_results` — no content validation** | 🟠 |
| QRY-03 | Lucene OR | **Same — no content validation** | 🟠 |
| QRY-04 | Lucene NOT | **Same — no content validation** | 🟠 |
| QRY-05–12 | Filter tests | `assert_all_match` on actual field values | ✅ |
| QRY-13 | OrderBy desc | Validates sort order | ✅ |
| QRY-14 | Geo orderby | **Only checks results >= 1 — should verify nearest location first** | 🟠 |
| QRY-15/16/17 | Facets | **Check facet key exists but not counts > 0 or bucket structure** | 🟠 |
| QRY-18 | Highlights | **Checks `@search.highlights` found but not `<em>` tags** | 🟡 |
| QRY-19 | Select | Field restriction validated | ✅ |
| QRY-20 | Pagination | No overlap verified | ✅ |
| QRY-21 | Count | @odata.count validated | ✅ |
| QRY-22 | Semantic | rerankerScore on 200, semanticPartialResponseReason on 206 | 🟢 |
| QRY-23 | Semantic answers | **Checks `@search.answers` key exists on 200 — not answer content** | 🟠 |
| QRY-24–28 | Vector queries | @search.score present, filter checks | 🟢 |
| QRY-29–31 | Suggest/Autocomplete | Structure fields validated | 🟢 |
| QRY-32 | Scoring profile | Top result Rating >= 4 | ✅ |
| QRY-33 | searchFields | Tags contain "pool" | ✅ |
| QRY-34 | minimumCoverage | @search.coverage == 100 | ✅ |
| QRY-35 | Speller | **Only checks results >= 1 — should verify correction worked** | 🟠 |

**Fixes needed** (priority order):
1. QRY-02/03/04: Validate actual result content matches Lucene operator semantics
2. QRY-14: Verify geo sort — first result should be nearest to reference point
3. QRY-15/16/17: Verify facet buckets have `count > 0` and expected structure
4. QRY-23: Validate answer content has `text`, `key`, `score` fields
5. QRY-35: Verify misspelled query still returns relevant results

---

## Phase 8: Misc (`test_08`) — 🟢 GOOD

**11 tests (MSC-01 to MSC-11)** — Service operations, error handling.

| Test | What it checks | Gap | Rating |
|------|---------------|-----|--------|
| MSC-01 | /servicestats counters | Counters key present | 🟢 |
| MSC-02/03 | Analyze API | tokens > 0 returned | 🟢 |
| MSC-04/05 | Bad API version | Error status codes | 🟢 |
| MSC-06 | ETag concurrency (412) | None | ✅ |
| MSC-07 | If-None-Match (412) | None | ✅ |
| MSC-08 | Invalid JSON (400) | None | ✅ |
| MSC-09 | Unknown field → error | None | 🟢 |
| MSC-10 | Stats limits | Counter keys present | 🟢 |
| MSC-11 | Index stats summary | xfail — appropriate | 🟢 |

**Summary**: Well-structured. No critical gaps.

---

## Phase 9: Indexers (`test_09`) — 🟢 GOOD

**22 tests (IXR-01 to IXR-22)** — Data source CRUD + indexer pipeline.

All CRUD operations include round-trip validation. Indexer run polls to success. Connection string masking verified. Field mappings validated. Parsing modes round-tripped.

| Test | Gap | Rating |
|------|-----|--------|
| IXR-08 | Vector doc verification only checks `has_data` — doesn't validate vectors were actually indexed | 🟡 |
| All others | Solid round-trip validation | 🟢 |

**Summary**: Mostly well-written. IXR-08 is a minor gap (hard to validate vector content without a vector search).

---

## Phase 10: Skillsets (`test_10`) — 🟢 GOOD

**16 tests (SKL-01 to SKL-16)** — AI enrichment skill registration.

Every skill creation validates `@odata.type` round-trip on GET. Multi-skill pipeline validates count. Knowledge store validates config round-trip. Good lifecycle coverage.

**Summary**: Well-written phase. No gaps.

---

## Phase 11: Vectorization (`test_11`) — ✅ EXCELLENT

**19 tests (VEC-01 to VEC-19)** — Vector schema CRUD + E2E integrated vectorization.

| Highlight | Detail |
|-----------|--------|
| VEC-01–09 | Schema CRUD with full round-trip: algorithms, profiles, quantization, stored flag, multi-profile |
| VEC-10 | Create vectorizer index — validates vectorizer AND profile linkage round-trip |
| VEC-11 | Upload 1000 docs with AOAI embeddings — validates count reaches 1000 |
| VEC-12 | kind:text query — validates AI category appears in results (semantic relevance) |
| VEC-13 | Hybrid query — validates Cloud category (content relevance) |
| VEC-14 | Filter + vector — validates EVERY result satisfies filter predicate |
| VEC-15 | Select restriction — validates field exclusion |
| VEC-16 | Pagination — no overlap check |
| VEC-17 | Multi-vector queries — validates diverse categories from diverse queries |
| VEC-18 | Quantization + vectorizer — validates search works through quantized profile |

**Summary**: One of the best-written phases alongside Phase 15 (Filters). Content relevance checks go beyond status codes.

---

## Phase 12: Agentic Retrieval (`test_12`) — 🔴 CRITICAL

**22 tests (AGT-01 to AGT-22)** — Agentic retrieval CRUD + retrieve operations.

This is the **worst-validated phase** in the suite. Multiple tests can pass when the feature is fundamentally broken.

| Test | What it checks now | What it SHOULD check (per API docs) | Severity |
|------|-------------------|--------------------------------------|----------|
| AGT-01–03 | Knowledge source CRUD | Status codes + round-trip | 🟢 |
| AGT-04–06 | Knowledge base CRUD | Status codes + round-trip | 🟢 |
| AGT-07 | Basic retrieve | **Only `"activity" in data`** — empty array passes | 🔴 |
| AGT-08 | Answer synthesis | Checks `content[0].get("text")` truthy | **Should validate**: (1) `response[0].role == "assistant"`, (2) content text is non-trivial (>20 chars), (3) text contains `[ref_id:N]` citation markers, (4) `references` array has matching entries | 🔴 |
| AGT-09 | Filter parameter | **Only `"activity" in data`** | 🔴 |
| AGT-10 | reasoningEffort | **Accepts 400 as valid** — hides OData parameter bug | 🔴 |
| AGT-11 | Activity types | Checks "query" or "plan" in type names — weak | 🟠 |
| AGT-12 | MCP endpoint | **Accepts 404/405** — MCP may not be deployed but test shouldn't pass silently | 🟠 |
| AGT-13/14 | Cleanup | Delete operations — fine | 🟢 |
| AGT-15 | References validation | Checks "searchIndex" in activity types — **doesn't validate references contain actual document data** | 🔴 |
| AGT-16 | ExtractedData mode | **Only `"activity" in data`** | 🔴 |
| AGT-17 | History context | **Only `"activity" in data`** | 🔴 |
| AGT-18 | Answer synthesis types | Checks "modelAnswerSynthesis" in activity — **doesn't validate answer text quality** | 🟠 |
| AGT-19 | Max output size | Checks response exists — weak | 🟡 |
| AGT-20 | Invalid KB | **Accepts 400 as valid** — test should expect specific error | 🟠 |
| AGT-21 | Multi-source | **Only `"activity" in data`** | 🔴 |
| AGT-22 | Cleanup all | Delete lifecycle — fine | 🟢 |

**Expected response schema (from docs)**:
```json
{
  "response": [{"role": "assistant", "content": [{"type": "text", "text": "answer with [ref_id:1] citations"}]}],
  "activity": [
    {"type": "modelQueryPlanning", "inputTokens": N, "outputTokens": N, "elapsedMs": N},
    {"type": "searchIndex", "knowledgeSourceName": "...", "count": N, "elapsedMs": N},
    {"type": "modelAnswerSynthesis", "inputTokens": N, "outputTokens": N, "elapsedMs": N}
  ],
  "references": [{"type": "AzureSearchDoc", "id": "[ref_id:1]", "docKey": "...", "sourceData": {...}}]
}
```

**What EVERY retrieve test should validate**:
1. `response` array is non-empty
2. `response[0].role == "assistant"`
3. `response[0].content[0].text` is non-trivial (length > 20)
4. `activity` array contains expected typed entries with non-zero token counts
5. `references` array is non-empty with valid `type`, `id`, `docKey` fields
6. For AnswerSynthesis: citations in text (`[ref_id:N]`) match references

---

## Phase 13: Serverless Behavior (`test_13`) — 🟡 MEDIUM

**12 tests (SLS-01 to SLS-12)** — Serverless-specific behavioral tests.

| Test | Gap | Rating |
|------|-----|--------|
| SLS-01/02 | 30s latency threshold is extremely generous | 🟡 |
| SLS-04 | Concurrent queries — no 500s | ✅ |
| SLS-05 | Parallel index creation — no 500s | ✅ |
| SLS-08 | Rapid operations — doesn't verify docs are actually searchable after upload | 🟡 |
| SLS-12 | Throttling — skips if no 429s | Appropriate | 🟢 |
| Others | Status code checks | 🟢 |

**Summary**: Acceptable for behavioral tests. Latency thresholds could be tightened.

---

## Phase 14: Serverless Limits (`test_14`) — 🟢 GOOD

**14 tests (LIM-01 to LIM-14)** — Quota validation.

Validates service-level quotas against documented minimums. Index stats structure validated. Counter tracking verified. Throttle observation tests are appropriately non-strict.

**Summary**: Well-written phase. No gaps.

---

## Phase 15: Filters (`test_15`) — ✅ EXCELLENT

**20 tests (FLT-01 to FLT-20)** — Filter query validation.

**GOLD STANDARD for the suite.** Every single test validates actual field values in returned documents using `assert_all_match()`. Covers: eq, ne, gt, lt, ge, le, `search.in()`, `any()` lambda, `all()` lambda, double-nested lambdas, `not()`, null, range, `geo.distance()`, `search.ismatch()`, `search.ismatchscoring()`, complex types, date range, boolean cross-check, filter+orderby, filter+search.

**Summary**: The benchmark that all other query-testing phases should aspire to.

---

## Phase 16: Scoring (`test_16`) — 🟢 MOSTLY GOOD

**14 tests (SCR-01 to SCR-14)**

| Test | Gap | Rating |
|------|-----|--------|
| SCR-01–08 | Score validation, magnitude boost, freshness, filter combos | ✅ |
| SCR-09 | Wildcard + profile — **only checks @search.score exists** | 🟠 |
| SCR-10 | searchMode "all" — **only checks 200 status** | 🟠 |
| SCR-11–14 | Field restriction, semantic combo, tag scoring, text weights | ✅ |

**Fixes needed**:
- SCR-09: Verify wildcard returns results AND scores reflect profile boost
- SCR-10: Verify searchMode "all" returns fewer results than "any" for multi-term query

---

## Phase 17: Semantic Search (`test_17`) — 🟠 HIGH PRIORITY

**12 tests (SEM-01 to SEM-12)**

| Test | What it checks | Gap | Severity |
|------|---------------|-----|----------|
| SEM-01 | rerankerScore descending | Good — but bails on 206 | 🟢 |
| SEM-02 | @search.answers | **Empty answers array passes silently** — no assert on len > 0 | 🔴 |
| SEM-03 | @search.captions | captions_found >= 1 | 🟢 |
| SEM-04 | rerankerScore on results | **Doesn't verify captions OR answers** | 🟠 |
| SEM-05 | French search | **Only checks results >= 1 — doesn't verify French content** | 🟠 |
| SEM-06 | Filter + semantic | Filter + rerankerScore | ✅ |
| SEM-07 | orderby + semantic → 400 | Error message validated | ✅ |
| SEM-08 | semanticMaxTextRecallSize | 400 expected | ✅ |
| SEM-09 | Speller | **Only checks results >= 1** | 🟠 |
| SEM-10 | Count | @odata.count >= 1 | 🟢 |
| SEM-11 | Highlights + captions | **Checks at least ONE feature present — should verify BOTH** | 🟠 |
| SEM-12 | Pagination no overlap | Good | ✅ |

**Fixes needed**:
1. SEM-02: Assert `len(answers) >= 1` and validate answer structure (`key`, `text`, `score`)
2. SEM-04: Add captions check alongside rerankerScore
3. SEM-05: Verify results contain French text in `Description_fr`
4. SEM-09: Verify misspelled query returns relevant results
5. SEM-11: Assert BOTH highlights and captions are present

---

## Phase 18: Vector Queries (`test_18`) — 🟢 GOOD

**16 tests (VQR-01 to VQR-16)**

Strong phase with excellent relevance checks (VQR-05/06 validate >= 5/10 match expected category). Filter predicate validated on all results. Score ordering verified. Minor gap on VQR-02 (hybrid only checks results >= 1).

**Summary**: Well-written. Minor improvement on VQR-02.

---

## Phase 19: Advanced Queries (`test_19`) — 🟢 MOSTLY GOOD

**12 tests (ADV-01 to ADV-12)**

| Test | Gap | Rating |
|------|-----|--------|
| ADV-01–06 | Suggest/autocomplete structure | 🟢 |
| ADV-07 | Fuzzy search — **only checks results >= 1** | 🟡 |
| ADV-08 | Proximity search — **only checks results >= 1** | 🟡 |
| ADV-09 | Fielded search — validates "luxury" in Description | ✅ |
| ADV-10 | Boosted term — validates scores differ | ✅ |
| ADV-11 | French — results >= 1 + Description_fr not null | 🟢 |
| ADV-12 | Regex — count >= 5 | 🟢 |

---

## Priority Fix Matrix

| Priority | Phase | Tests | Issue | Impact |
|----------|-------|-------|-------|--------|
| **P0** | 12 (Agentic) | AGT-07,08,09,10,15,16,17,18,20,21 | Retrieve tests validate nothing meaningful | All 10 retrieve tests are false positives |
| **P1** | 17 (Semantic) | SEM-02,04,05,09,11 | Empty answers pass, missing content checks | Semantic bugs hidden |
| **P2** | 7 (Queries) | QRY-02,03,04,14,15,16,17,23,35 | No content validation on Lucene/facets/answers | 9 tests are rubber stamps |
| **P3** | 16 (Scoring) | SCR-09,10 | Status-only checks | 2 tests don't validate behavior |
| **P4** | 5 (Documents) | DOC-11 | Batch checks `> 0` not `== 1000` | Could miss partial failures |
| **P5** | 6 (Synonyms) | SYN-06 | Doesn't verify expansion worked | 1 test is a rubber stamp |
