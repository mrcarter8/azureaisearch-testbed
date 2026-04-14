# Serverless Bug Bash — Test Results

**Last updated:** 2026-04-14 22:04 UTC

| | Count |
|---|---|
| **Total tests run** | 326 |
| **Passed** | 296 |
| **Failed** | 26 |
| **Skipped** | 3 |
| **Xfail** | 1 |

## Phase 1 — Control Plane (14/18 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SVC-01 | `PUT` | Create serverless service (minimal) | PASS | 2026-04-14 21:45 UTC | — |
| SVC-02 | `GET` | Read service (validate serverless SKU) | PASS | 2026-04-14 21:45 UTC | — |
| SVC-03 | `GET` | Read service | PASS | 2026-04-14 21:45 UTC | — |
| SVC-04 | `GET` | List services in resource group | PASS | 2026-04-14 21:45 UTC | — |
| SVC-05 | `GET` | List services in subscription (paginated) | **FAIL** | 2026-04-14 21:45 UTC | [Bug](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/5175978) |
| SVC-06 | `POST` | List admin keys | PASS | 2026-04-14 21:45 UTC | — |
| SVC-07 | `POST` | Regenerate primary admin key | PASS | 2026-04-14 21:45 UTC | — |
| SVC-08 | `POST` | Regenerate secondary admin key | PASS | 2026-04-14 21:45 UTC | — |
| SVC-09 | `POST` | Create query key | PASS | 2026-04-14 21:45 UTC | — |
| SVC-10 | `POST` | List query keys | PASS | 2026-04-14 21:45 UTC | — |
| SVC-11 | `POST DELETE GET` | Create + delete + verify query key | PASS | 2026-04-14 21:45 UTC | — |
| SVC-12 | `PATCH GET` | Update auth options + verify | PASS | 2026-04-14 21:45 UTC | — |
| SVC-13 | `PATCH` | Update semanticSearch property | PASS | 2026-04-14 21:45 UTC | — |
| SVC-14 | `PATCH` | Update CORS options | **FAIL** | 2026-04-14 21:45 UTC | — |
| SVC-15 | `PATCH` | Enable system-assigned managed identity | PASS | 2026-04-14 21:45 UTC | — |
| SVC-16 | `GET` | Read service (validate all properties) | PASS | 2026-04-14 21:45 UTC | — |
| SVC-17 | — | CheckNameAvailability for a very unlikely name returns av... | **FAIL** | 2026-04-14 21:45 UTC | — |
| SVC-18 | — | CheckNameAvailability for existing service returns unavai... | **FAIL** | 2026-04-14 21:45 UTC | — |

## Phase 2 — Negative / Limits (15/15 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| NEG-01 | `PATCH` | Update replicaCount (rejected) | PASS | 2026-04-14 21:45 UTC | [Bug](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/4907459) |
| NEG-02 | `PATCH` | Update partitionCount (rejected) | PASS | 2026-04-14 21:45 UTC | [Bug](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/4907459) |
| NEG-03 | `PUT` | Create service with invalid SKU (rejected) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-04 | `PUT` | Create service in invalid region (rejected) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-05 | `PUT` | Create service with existing name (idempotent) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-06 | `PATCH` | Update with invalid authOptions | PASS | 2026-04-14 21:45 UTC | — |
| NEG-07 | `GET` | Read service (check quotas) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-08 | `PUT GET DELETE GET` | Create + wait + delete + verify service | PASS | 2026-04-14 21:45 UTC | — |
| NEG-09 | `PATCH` | Update IP firewall rules (discover + restore) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-10 | `GET` | List shared private link resources | PASS | 2026-04-14 21:45 UTC | — |
| NEG-11 | `GET` | Read service (check CMK encryption) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-12 | `PATCH PATCH` | Disable + re-enable publicNetworkAccess | PASS | 2026-04-14 21:45 UTC | — |
| NEG-13 | `PATCH` | Enable managed identity (discovery) | PASS | 2026-04-14 21:45 UTC | — |
| NEG-14 | `GET PUT GET DELETE` | Create index with CMK encryptionKey + verify + delete | PASS | 2026-04-14 21:45 UTC | — |
| NEG-15 | `PUT DELETE` | Create synonym map with CMK + delete | PASS | 2026-04-14 21:45 UTC | — |

## Phase 3 — Authentication (10/10 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SEC-01 | `GET` | List indexes (admin key auth) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-02 | `PUT DELETE` | Create + delete index (admin key auth) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-03 | `POST` | Search docs (query key auth) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-04 | `PUT` | Create index (query key, rejected 403) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-05 | `GET` | List indexes (Entra auth) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-06 | `PUT DELETE` | Create + delete index (Entra auth) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-07 | `GET` | List indexes (no auth, rejected) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-08 | `GET` | List indexes (invalid API key, rejected) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-09 | `GET` | List indexes (expired token, rejected) | PASS | 2026-04-14 21:45 UTC | — |
| SEC-10 | `POST` | Search docs (Entra RBAC) | PASS | 2026-04-14 21:45 UTC | — |

## Phase 4 — Index Management (16/16 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| IDX-01 | `PUT PUT` | Create synonym map + full-featured index | PASS | 2026-04-14 21:45 UTC | — |
| IDX-02 | `GET` | Read index | PASS | 2026-04-14 21:45 UTC | — |
| IDX-03 | `GET` | List indexes | PASS | 2026-04-14 21:45 UTC | — |
| IDX-04 | `GET PUT GET` | Update index (add field) + verify | PASS | 2026-04-14 21:45 UTC | — |
| IDX-05 | `GET` | Read index statistics | PASS | 2026-04-14 21:45 UTC | — |
| IDX-06 | `PUT DELETE GET` | Create + delete + verify index gone | PASS | 2026-04-14 21:45 UTC | — |
| IDX-07 | `GET` | Read index (verify vector config) | PASS | 2026-04-14 21:45 UTC | — |
| IDX-08 | `GET` | Read index (verify semantic config) | PASS | 2026-04-14 21:45 UTC | — |
| IDX-09 | `GET` | Read index (verify scoring profiles) | PASS | 2026-04-14 21:45 UTC | — |
| IDX-10 | `GET` | Read index (verify suggesters) | PASS | 2026-04-14 21:45 UTC | — |
| IDX-11 | `GET` | Read index (verify CORS options) | PASS | 2026-04-14 21:45 UTC | — |
| IDX-12 | `PUT GET DELETE` | Create index with custom analyzer + verify + delete | PASS | 2026-04-14 21:45 UTC | — |
| IDX-13 | `PUT` | Create simple index | PASS | 2026-04-14 21:45 UTC | — |
| IDX-14 | `PUT GET DELETE` | Create index with all EDM types + verify + delete | PASS | 2026-04-14 21:45 UTC | — |
| IDX-15 | `GET` | List aliases (expect empty, quota=0) | PASS | 2026-04-14 21:45 UTC | — |
| IDX-16 | `PUT` | Create alias (rejected, quota=0) | PASS | 2026-04-14 21:45 UTC | [Bug](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/5177274) |

## Phase 5 — Document CRUD (29/30 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| DOC-01 | `POST` | Upload 25 documents (batch) | PASS | 2026-04-14 21:45 UTC | — |
| DOC-02 | `GET` | Lookup document by key | PASS | 2026-04-14 21:45 UTC | — |
| DOC-03 | `GET` | Document count | PASS | 2026-04-14 21:45 UTC | — |
| DOC-04 | `POST` | Merge document (update single field) | PASS | 2026-04-14 21:45 UTC | — |
| DOC-05 | `POST` | MergeOrUpload existing document | PASS | 2026-04-14 21:45 UTC | — |
| DOC-06 | `POST` | MergeOrUpload new document | PASS | 2026-04-14 21:45 UTC | — |
| DOC-07 | `POST GET` | Delete document + verify 404 | PASS | 2026-04-14 21:45 UTC | — |
| DOC-08 | `POST GET` | Upload document with vector field + verify | PASS | 2026-04-14 21:45 UTC | — |
| DOC-09 | `POST` | Upload large document (~300KB) | PASS | 2026-04-14 21:45 UTC | — |
| DOC-10 | `POST GET` | Upload unicode doc (CJK/emoji) + verify | PASS | 2026-04-14 21:45 UTC | — |
| DOC-11 | `POST` | Batch upload 1000 documents | PASS | 2026-04-14 21:45 UTC | — |
| DOC-12 | `POST` | Upload doc with empty string fields | PASS | 2026-04-14 21:45 UTC | — |
| DOC-13 | `POST GET` | Merge multiple fields simultaneously | PASS | 2026-04-14 21:45 UTC | — |
| DOC-14 | `POST` | Merge on non-existent doc — item 404 | PASS | 2026-04-14 21:45 UTC | — |
| DOC-15 | `POST POST GET` | Upload overwrites existing doc | PASS | 2026-04-14 21:45 UTC | — |
| DOC-16 | `POST POST` | Batch mixed actions (upload+merge+delete) | PASS | 2026-04-14 21:45 UTC | — |
| DOC-17 | `GET` | Lookup with $select restriction | PASS | 2026-04-14 21:45 UTC | — |
| DOC-18 | `GET` | Lookup non-existent key — 404 | PASS | 2026-04-14 21:45 UTC | — |
| DOC-19 | `GET POST GET` | Count unchanged after merge | **FAIL** | 2026-04-14 21:45 UTC | — |
| DOC-20 | `POST GET` | Upload fully populated complex types | PASS | 2026-04-14 21:45 UTC | — |
| DOC-21 | `POST GET` | Upload with empty Rooms collection | PASS | 2026-04-14 21:45 UTC | — |
| DOC-22 | `POST GET` | Merge replaces entire collection | PASS | 2026-04-14 21:45 UTC | — |
| DOC-23 | `POST` | Delete non-existent doc — silent success | PASS | 2026-04-14 21:45 UTC | — |
| DOC-24 | `POST POST GET` | Re-upload deleted document | PASS | 2026-04-14 21:45 UTC | — |
| DOC-25 | `POST` | Batch with 1 invalid — 207 partial | PASS | 2026-04-14 21:45 UTC | — |
| DOC-26 | `POST POST GET` | Merge preserves unmentioned fields | PASS | 2026-04-14 21:45 UTC | — |
| DOC-27 | `POST GET` | Upload with special characters | PASS | 2026-04-14 21:45 UTC | — |
| DOC-28 | `POST GET` | Upload with explicit null fields | PASS | 2026-04-14 21:45 UTC | — |
| DOC-29 | `POST` | Empty batch — graceful handling | PASS | 2026-04-14 21:45 UTC | — |
| DOC-30 | `POST` | Search correctness after mutations | PASS | 2026-04-14 21:45 UTC | — |

## Phase 6 — Synonym Maps (6/6 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SYN-01 | `PUT` | Create synonym map (Solr rules) | PASS | 2026-04-14 21:45 UTC | — |
| SYN-02 | `GET` | Read synonym map | PASS | 2026-04-14 21:45 UTC | — |
| SYN-03 | `GET` | List synonym maps | PASS | 2026-04-14 21:45 UTC | — |
| SYN-04 | `PUT GET` | Update synonym map + verify | PASS | 2026-04-14 21:45 UTC | — |
| SYN-05 | `PUT DELETE GET` | Create + delete + verify synonym map | PASS | 2026-04-14 21:45 UTC | — |
| SYN-06 | `POST` | Search 'inn' expands to 'hotel' via synonyms | PASS | 2026-04-14 21:45 UTC | — |

## Phase 7 — Queries (36/38 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| QRY-01 | `POST` | Simple keyword search | PASS | 2026-04-14 21:45 UTC | — |
| QRY-02 | `POST` | Lucene boolean query (AND) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-03 | `POST` | Lucene wildcard query (lux*) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-04 | `POST` | Lucene regex query | PASS | 2026-04-14 21:45 UTC | — |
| QRY-05 | `POST` | Filter: Rating ge 4 | PASS | 2026-04-14 21:45 UTC | — |
| QRY-06 | `POST` | Filter: geo.distance <= 10km | PASS | 2026-04-14 21:45 UTC | — |
| QRY-07 | `POST` | Filter: ParkingIncluded eq true | PASS | 2026-04-14 21:45 UTC | — |
| QRY-08 | `POST` | Filter: Category eq 'Boutique' | PASS | 2026-04-14 21:45 UTC | — |
| QRY-09 | `POST` | Filter: Tags/any(t: t eq 'pool') | PASS | 2026-04-14 21:45 UTC | — |
| QRY-10 | `POST` | Filter: LastRenovationDate gt 2020 | PASS | 2026-04-14 21:45 UTC | — |
| QRY-11 | `POST` | Filter: Address/City eq 'New York' | PASS | 2026-04-14 21:45 UTC | — |
| QRY-12 | `POST` | Combined AND/OR filter | PASS | 2026-04-14 21:45 UTC | — |
| QRY-13 | `POST` | OrderBy Rating desc | PASS | 2026-04-14 21:45 UTC | — |
| QRY-14 | `POST` | OrderBy geo.distance asc | PASS | 2026-04-14 21:45 UTC | — |
| QRY-15 | `POST` | Facets: Category | **FAIL** | 2026-04-14 21:45 UTC | — |
| QRY-16 | `POST` | Facets: Rating interval:1 | PASS | 2026-04-14 21:45 UTC | — |
| QRY-17 | `POST` | Facets: Tags collection | PASS | 2026-04-14 21:45 UTC | — |
| QRY-18 | `POST` | Highlight @search.highlights | PASS | 2026-04-14 21:45 UTC | — |
| QRY-19 | `POST` | Select restricts returned fields | PASS | 2026-04-14 21:45 UTC | — |
| QRY-20 | `POST` | Top + Skip pagination (no overlap) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-21 | `POST` | $count=true returns @odata.count | PASS | 2026-04-14 21:45 UTC | — |
| QRY-22 | `POST` | Semantic search (rerankerScore) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-23 | `POST` | Semantic search with extractive answers | PASS | 2026-04-14 21:45 UTC | — |
| QRY-24 | `POST` | Pure vector search (pre-computed) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-25 | `POST` | Integrated vectorization (kind:text) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-26 | `POST` | Hybrid search (keyword + vector) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-27 | `POST` | Multi-vector query (2 vectorQueries) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-28 | `POST` | Vector search with filter | PASS | 2026-04-14 21:45 UTC | — |
| QRY-29 | `POST` | Suggest with partial input | PASS | 2026-04-14 21:45 UTC | — |
| QRY-30 | `GET` | Autocomplete oneTermWithContext | PASS | 2026-04-14 21:45 UTC | — |
| QRY-31 | `GET` | Autocomplete twoTerms | PASS | 2026-04-14 21:45 UTC | — |
| QRY-32 | `POST` | Scoring profile boosts higher-rated | PASS | 2026-04-14 21:45 UTC | — |
| QRY-33 | `POST` | searchFields constrains search | **FAIL** | 2026-04-14 21:45 UTC | — |
| QRY-34 | `POST` | minimumCoverage parameter | PASS | 2026-04-14 21:45 UTC | — |
| QRY-35 | `POST` | Spell correction (lexicon speller) | PASS | 2026-04-14 21:45 UTC | — |
| QRY-36 | `POST` | queryLanguage parameter | PASS | 2026-04-14 21:45 UTC | — |
| QRY-37 | `POST` | searchMode all vs any | PASS | 2026-04-14 21:45 UTC | — |
| QRY-38 | `POST` | Wildcard '*' returns all documents | PASS | 2026-04-14 21:45 UTC | — |

## Phase 8 — Misc Operations (10/11 passed, 1 xfail)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| MSC-01 | `GET` | Service statistics (counters) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-02 | `POST` | Analyze API (standard.lucene) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-03 | `POST` | Analyze API (en.microsoft) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-04 | `GET` | Bad API version (rejected 400) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-05 | `GET` | Very old API version (rejected) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-06 | `GET PUT` | PUT with stale ETag (rejected 412) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-07 | `PUT` | PUT with If-None-Match:* (rejected 412) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-08 | `POST` | Malformed JSON body (rejected 400) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-09 | `POST` | Select nonexistent field (rejected) | PASS | 2026-04-14 21:45 UTC | — |
| MSC-10 | `GET` | Serverless stats limits check | PASS | 2026-04-14 21:45 UTC | — |
| MSC-11 | — | GET /indexStatsSummary returns per-index document counts ... | **XFAIL** | 2026-04-14 21:45 UTC | — |

## Phase 9 — Indexers (12/24 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| IXR-01 | `PUT` | Create Blob data source | PASS | 2026-04-14 21:45 UTC | — |
| IXR-02 | `PUT` | Create Cosmos DB data source | PASS | 2026-04-14 21:45 UTC | — |
| IXR-03 | `PUT` | Create Azure SQL data source | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-04 | `GET` | Read data source (masked creds) | PASS | 2026-04-14 21:45 UTC | — |
| IXR-05 | `GET` | List data sources | PASS | 2026-04-14 21:45 UTC | — |
| IXR-06 | `PUT` | Create Blob indexer + skillset | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-07 | `POST` | Run Blob indexer + poll status | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-08 | `POST` | Verify indexed docs have vectors | PASS | 2026-04-14 21:45 UTC | — |
| IXR-09 | `PUT` | Create Cosmos DB indexer | PASS | 2026-04-14 21:45 UTC | — |
| IXR-10 | `POST` | Run Cosmos DB indexer + poll | PASS | 2026-04-14 21:45 UTC | — |
| IXR-11 | `PUT` | Create Azure SQL indexer | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-12 | `POST` | Run Azure SQL indexer + poll | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-13 | `GET` | Indexer status (lastResult) | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-14 | `POST` | Reset indexer | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-14b | — | Reset specific documents for re-processing. | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-14c | — | Reset skills on an indexer for re-enrichment. | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-15 | `GET PUT GET` | Update indexer schedule + verify | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-16 | `GET` | Verify field mappings present | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-17 | `GET` | Verify output field mappings | **FAIL** | 2026-04-14 21:45 UTC | — |
| IXR-18 | `PUT DELETE` | Indexer jsonArray parsing mode | PASS | 2026-04-14 21:45 UTC | — |
| IXR-19 | `PUT DELETE` | Indexer jsonLines parsing mode | PASS | 2026-04-14 21:45 UTC | — |
| IXR-20 | `GET` | List indexers | PASS | 2026-04-14 21:45 UTC | — |
| IXR-21 | `DELETE` | Delete Blob indexer | PASS | 2026-04-14 21:45 UTC | — |
| IXR-22 | `DELETE` | Delete Blob data source | PASS | 2026-04-14 21:45 UTC | — |

## Phase 10 — Skillsets (14/16 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SKL-01 | `PUT` | Create skillset (AOAI embedding) | PASS | 2026-04-14 21:45 UTC | — |
| SKL-02 | `GET PUT` | Update skillset + SplitSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-03 | `PUT DELETE` | EntityRecognitionSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-04 | `PUT DELETE` | KeyPhraseExtractionSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-05 | `PUT DELETE` | LanguageDetectionSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-06 | `PUT DELETE` | OcrSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-07 | `PUT DELETE` | ImageAnalysisSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-08 | `PUT DELETE` | DocumentLayoutSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-09 | `PUT DELETE` | ShaperSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-10 | `PUT DELETE` | MergeSkill | PASS | 2026-04-14 21:45 UTC | — |
| SKL-11 | `PUT DELETE` | WebApiSkill (custom endpoint) | SKIP | 2026-04-14 21:45 UTC | — |
| SKL-12 | `PUT GET DELETE` | Multi-skill pipeline (split+embed+entity) | PASS | 2026-04-14 21:45 UTC | — |
| SKL-13 | `GET` | E2E enrichment indexer verification | SKIP | 2026-04-14 21:45 UTC | — |
| SKL-14 | `PUT GET DELETE` | Knowledge store projections | PASS | 2026-04-14 21:45 UTC | — |
| SKL-15 | `GET` | List skillsets | PASS | 2026-04-14 21:45 UTC | — |
| SKL-16 | `DELETE` | Delete primary skillset | PASS | 2026-04-14 21:45 UTC | — |

## Phase 11 — Vectorization (20/20 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| VEC-01 | `PUT GET DELETE` | HNSW algorithm round-trip | PASS | 2026-04-14 21:45 UTC | — |
| VEC-02 | `PUT GET DELETE` | ExhaustiveKnn algorithm round-trip | PASS | 2026-04-14 21:45 UTC | — |
| VEC-03 | `PUT GET DELETE` | Azure OpenAI vectorizer round-trip | PASS | 2026-04-14 21:45 UTC | — |
| VEC-04 | `PUT GET DELETE` | Profile links algorithm + vectorizer | PASS | 2026-04-14 21:45 UTC | — |
| VEC-05 | `PUT DELETE` | Chunking + embedding index creation | PASS | 2026-04-14 21:45 UTC | — |
| VEC-06 | `PUT GET DELETE` | Scalar quantization round-trip | PASS | 2026-04-14 21:45 UTC | — |
| VEC-07 | `PUT GET DELETE` | Binary quantization round-trip | PASS | 2026-04-14 21:45 UTC | — |
| VEC-08 | `PUT GET DELETE` | Vector field stored:false round-trip | PASS | 2026-04-14 21:45 UTC | — |
| VEC-09 | `PUT GET DELETE` | Multiple vector profiles on fields | PASS | 2026-04-14 21:45 UTC | — |
| VEC-10 | `DELETE PUT GET` | Create index with AOAI vectorizer | PASS | 2026-04-14 21:45 UTC | — |
| VEC-11 | `POST (×10)` | Embed + upload 1000 tech articles | PASS | 2026-04-14 21:45 UTC | — |
| VEC-12 | `POST` | Vector query kind:text (integrated vectorization) | PASS | 2026-04-14 21:45 UTC | — |
| VEC-13 | `POST` | Hybrid keyword + kind:text vector query | PASS | 2026-04-14 21:45 UTC | — |
| VEC-14 | `POST` | Vector kind:text query with $filter | PASS | 2026-04-14 21:45 UTC | — |
| VEC-15 | `POST` | Vector kind:text query with $select | PASS | 2026-04-14 21:45 UTC | — |
| VEC-16 | `POST POST` | Vector kind:text query with top/skip pagination | PASS | 2026-04-14 21:45 UTC | — |
| VEC-17 | `POST` | Multiple kind:text vectorQueries | PASS | 2026-04-14 21:45 UTC | — |
| VEC-18 | `DELETE PUT POST POST DELETE` | Scalar quantization + AOAI vectorizer query | PASS | 2026-04-14 21:45 UTC | — |
| VEC-19 | `GET` | Verify E2E index populated (cleanup deferred to Phase 18) | PASS | 2026-04-14 21:45 UTC | — |

## Phase 12 — Agentic Retrieval (22/22 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| AGT-01 | `PUT` | Create search-index knowledge source | PASS | 2026-04-14 21:45 UTC | — |
| AGT-02 | `GET` | Read knowledge source | PASS | 2026-04-14 21:45 UTC | — |
| AGT-03 | `GET` | List knowledge sources | PASS | 2026-04-14 21:45 UTC | — |
| AGT-04 | `PUT` | Create knowledge base with LLM | PASS | 2026-04-14 21:45 UTC | — |
| AGT-05 | `GET` | Read knowledge base | PASS | 2026-04-14 21:45 UTC | — |
| AGT-06 | `GET` | List knowledge bases | PASS | 2026-04-14 21:45 UTC | — |
| AGT-07 | `POST` | Retrieve extractiveData mode | PASS | 2026-04-14 21:45 UTC | — |
| AGT-08 | `POST` | Retrieve answerSynthesis mode | PASS | 2026-04-14 21:45 UTC | — |
| AGT-09 | `POST` | Retrieve with multi-turn chat history | PASS | 2026-04-14 21:45 UTC | — |
| AGT-10 | `POST (×4)` | Retrieve with reasoningEffort levels | PASS | 2026-04-14 21:45 UTC | — |
| AGT-11 | `POST` | Retrieve — activity query planning | PASS | 2026-04-14 21:45 UTC | — |
| AGT-12 | `GET` | MCP endpoint responds | PASS | 2026-04-14 21:45 UTC | — |
| AGT-13 | `DELETE` | Delete knowledge base | PASS | 2026-04-14 21:45 UTC | — |
| AGT-14 | `DELETE` | Delete knowledge source | PASS | 2026-04-14 21:45 UTC | — |
| AGT-15 | `POST` | Retrieve extractive — reference structure | PASS | 2026-04-14 21:45 UTC | — |
| AGT-16 | `POST` | Retrieve with minimal query | PASS | 2026-04-14 21:45 UTC | — |
| AGT-17 | `POST` | Retrieve with long complex query | PASS | 2026-04-14 21:45 UTC | — |
| AGT-18 | `POST` | Retrieve answerSynthesis — answer validation | PASS | 2026-04-14 21:45 UTC | — |
| AGT-19 | `POST` | Retrieve with non-existent KB — 404 | PASS | 2026-04-14 21:45 UTC | — |
| AGT-20 | `POST` | Retrieve with system message | PASS | 2026-04-14 21:45 UTC | — |
| AGT-21 | `POST` | Multi-turn extractive follow-up | PASS | 2026-04-14 21:45 UTC | — |
| AGT-22 | `POST` | Retrieve empty messages — 400 | PASS | 2026-04-14 21:45 UTC | — |

## Phase 13 — Serverless Behavior (8/12 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SLS-01 | `POST` | Cold start query latency < 30s | PASS | 2026-04-14 21:45 UTC | — |
| SLS-02 | `PUT DELETE` | Index creation latency < 30s | PASS | 2026-04-14 21:45 UTC | — |
| SLS-03 | `GET` | Blob indexer E2E timing | SKIP | 2026-04-14 21:45 UTC | — |
| SLS-04 | `POST (×20)` | 20 parallel search queries — no 5xx | **FAIL** | 2026-04-14 21:45 UTC | — |
| SLS-05 | `PUT (×5) DELETE (×5)` | 5 parallel index creates — no 5xx | **FAIL** | 2026-04-14 21:45 UTC | — |
| SLS-06 | `GET` | Service stats counters present | PASS | 2026-04-14 21:45 UTC | — |
| SLS-07 | `POST` | Request top=1000 — 200 or 400 | PASS | 2026-04-14 21:45 UTC | — |
| SLS-08 | `PUT POST POST DELETE` | Create → upload → search → delete | PASS | 2026-04-14 21:45 UTC | — |
| SLS-09 | `GET (×3)` | Older API versions — 200 or clear error | PASS | 2026-04-14 21:45 UTC | — |
| SLS-10 | `GET POST` | Error responses have code + message | PASS | 2026-04-14 21:45 UTC | — |
| SLS-11 | `GET POST GET` | x-ms-request-id in all responses | PASS | 2026-04-14 21:45 UTC | — |
| SLS-12 | `POST (×60)` | 429 includes Retry-After header | **FAIL** | 2026-04-14 21:45 UTC | — |

## Phase 14 — Serverless Limits (14/14 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| LIM-01 | `GET` | indexesCount quota >= serverless minimum | PASS | 2026-04-14 21:45 UTC | — |
| LIM-02 | `GET` | indexersCount quota >= serverless minimum | PASS | 2026-04-14 21:45 UTC | — |
| LIM-03 | `GET` | dataSourcesCount quota >= serverless minimum | PASS | 2026-04-14 21:45 UTC | — |
| LIM-04 | `GET` | skillsetCount quota >= serverless minimum | PASS | 2026-04-14 21:45 UTC | — |
| LIM-05 | `GET` | synonymMaps quota == 20 | PASS | 2026-04-14 21:45 UTC | — |
| LIM-06 | `GET` | aliasesCount quota == 0 (not supported) | PASS | 2026-04-14 21:45 UTC | — |
| LIM-07 | `GET` | maxStoragePerIndex > 0 in limits section | PASS | 2026-04-14 21:45 UTC | — |
| LIM-08 | `GET` | maxFieldsPerIndex >= 1000 | PASS | 2026-04-14 21:45 UTC | — |
| LIM-09 | `GET` | vectorIndexSize quota ~30% of total storage | PASS | 2026-04-14 21:45 UTC | — |
| LIM-10 | `DELETE PUT GET DELETE` | Index stats: documentCount, storageSize, vectorIndexSize | PASS | 2026-04-14 21:45 UTC | — |
| LIM-11 | `GET` | Index stats reflect docs + storage > 0 | PASS | 2026-04-14 21:45 UTC | — |
| LIM-12 | `GET PUT GET DELETE` | indexesCount.usage increments on create | PASS | 2026-04-14 21:45 UTC | — |
| LIM-13 | `GET (×30)` | Rapid-fire GET /indexes — observe 429 throttle | PASS | 2026-04-14 21:45 UTC | — |
| LIM-14 | `GET (×30)` | Rapid-fire GET /servicestats — observe 429 throttle | PASS | 2026-04-14 21:45 UTC | — |

## Phase 15 — Advanced Filters (19/20 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| FLT-01 | `POST` | search.in() comma delimiter | PASS | 2026-04-14 21:45 UTC | — |
| FLT-02 | `POST` | search.in() pipe delimiter | PASS | 2026-04-14 21:45 UTC | — |
| FLT-03 | `POST` | Rooms/any(r: r/BaseRate lt 200) | PASS | 2026-04-14 21:45 UTC | — |
| FLT-04 | `POST` | Rooms/all(r: not r/SmokingAllowed) | PASS | 2026-04-14 21:45 UTC | — |
| FLT-05 | `POST` | Rooms/any(r: r/Tags/any(t: t eq 'suite')) | PASS | 2026-04-14 21:45 UTC | — |
| FLT-06 | `POST` | not Rooms/any() — empty collection | PASS | 2026-04-14 21:45 UTC | — |
| FLT-07 | `POST` | Tags/any(t: search.in(t, ...)) | PASS | 2026-04-14 21:45 UTC | — |
| FLT-08 | `POST` | Category ne 'Boutique' | PASS | 2026-04-14 21:45 UTC | — |
| FLT-09 | `POST` | not (Rating gt 4) — negation | PASS | 2026-04-14 21:45 UTC | — |
| FLT-10 | `POST` | Rating ge 2 and Rating le 3 | PASS | 2026-04-14 21:45 UTC | — |
| FLT-11 | `POST` | Description_fr ne null | PASS | 2026-04-14 21:45 UTC | — |
| FLT-12 | `POST` | geo.distance le 5km — NYC only | PASS | 2026-04-14 21:45 UTC | — |
| FLT-13 | `POST` | search.ismatch in filter | PASS | 2026-04-14 21:45 UTC | — |
| FLT-14 | `POST` | search.ismatchscoring + Rating filter | PASS | 2026-04-14 21:45 UTC | — |
| FLT-15 | `POST` | Address/StateProvince eq 'NY' | PASS | 2026-04-14 21:45 UTC | — |
| FLT-16 | `POST` | Address/Country + City ne filter | PASS | 2026-04-14 21:45 UTC | — |
| FLT-17 | `POST` | LastRenovationDate date range | PASS | 2026-04-14 21:45 UTC | — |
| FLT-18 | `POST POST POST` | ParkingIncluded + count cross-check | PASS | 2026-04-14 21:45 UTC | — |
| FLT-19 | `POST` | Filter + orderby Rating desc | **FAIL** | 2026-04-14 21:45 UTC | — |
| FLT-20 | `POST` | Keyword search + filter combo | PASS | 2026-04-14 21:45 UTC | — |

## Phase 16 — Scoring Profiles (13/14 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SCR-01 | `POST POST` | Scoring profile changes scores | PASS | 2026-04-14 21:45 UTC | — |
| SCR-02 | `POST` | Magnitude boost favors high Rating | PASS | 2026-04-14 21:45 UTC | — |
| SCR-03 | `POST POST` | Freshness boost changes ordering | PASS | 2026-04-14 21:45 UTC | — |
| SCR-04 | `POST` | Profile + filter together | PASS | 2026-04-14 21:45 UTC | — |
| SCR-05 | `POST` | orderby overrides profile | PASS | 2026-04-14 21:45 UTC | — |
| SCR-06 | `POST POST` | Profile does not change count | PASS | 2026-04-14 21:45 UTC | — |
| SCR-07 | `POST` | Invalid profile name — 400 | PASS | 2026-04-14 21:45 UTC | — |
| SCR-08 | `POST POST` | Profile + pagination no overlap | PASS | 2026-04-14 21:45 UTC | — |
| SCR-09 | `POST` | Profile with wildcard '*' search | PASS | 2026-04-14 21:45 UTC | — |
| SCR-10 | `POST` | Profile + searchMode all | PASS | 2026-04-14 21:45 UTC | — |
| SCR-11 | `POST` | Profile + select restriction | PASS | 2026-04-14 21:45 UTC | — |
| SCR-12 | `POST` | Profile + semantic reranking | PASS | 2026-04-14 21:45 UTC | — |
| SCR-13 | `PUT POST POST DELETE` | Tag scoring profile (temp index) | **FAIL** | 2026-04-14 21:45 UTC | — |
| SCR-14 | `PUT POST POST POST DELETE` | Text weights profile (temp index) | PASS | 2026-04-14 21:45 UTC | — |

## Phase 17 — Semantic Deep-Dive (12/12 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| SEM-01 | `POST` | Semantic rerankerScore descending | PASS | 2026-04-14 21:45 UTC | — |
| SEM-02 | `POST` | Extractive answers structure | PASS | 2026-04-14 21:45 UTC | — |
| SEM-03 | `POST` | Extractive captions on results | PASS | 2026-04-14 21:45 UTC | — |
| SEM-04 | `POST` | Answers + captions together | PASS | 2026-04-14 21:45 UTC | — |
| SEM-05 | `POST` | French semantic search | PASS | 2026-04-14 21:45 UTC | — |
| SEM-06 | `POST` | Semantic + filter combo | PASS | 2026-04-14 21:45 UTC | — |
| SEM-07 | `POST` | orderby overrides semantic ranking | PASS | 2026-04-14 21:45 UTC | — |
| SEM-08 | `POST POST` | maxTextRecallSize limits recall | PASS | 2026-04-14 21:45 UTC | — |
| SEM-09 | `POST` | Speller correction + semantic | PASS | 2026-04-14 21:45 UTC | — |
| SEM-10 | `POST` | Semantic + $count | PASS | 2026-04-14 21:45 UTC | — |
| SEM-11 | `POST` | Semantic + highlight + captions | PASS | 2026-04-14 21:45 UTC | — |
| SEM-12 | `POST POST` | Semantic top/skip no overlap | PASS | 2026-04-14 21:45 UTC | — |

## Phase 18 — Vector Queries (15/16 passed, 1 failed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| VQR-01 | `POST` | kind:text vector query — scores present | PASS | 2026-04-14 21:45 UTC | — |
| VQR-02 | `POST` | Hybrid with sparse vectors — keyword fallback | PASS | 2026-04-14 21:45 UTC | — |
| VQR-03 | `POST` | Vector + filter correctness | PASS | 2026-04-14 21:45 UTC | — |
| VQR-04 | `POST` | Tri-modal: keyword + vector + semantic | PASS | 2026-04-14 21:45 UTC | — |
| VQR-05 | `POST` | AI text → AI category dominant | PASS | 2026-04-14 21:45 UTC | — |
| VQR-06 | `POST` | Security text → Security category | PASS | 2026-04-14 21:45 UTC | — |
| VQR-07 | `POST POST` | Different queries → different #1 results | PASS | 2026-04-14 21:45 UTC | — |
| VQR-08 | `POST` | Vector scores descending order | PASS | 2026-04-14 21:45 UTC | — |
| VQR-09 | `POST` | Exhaustive KNN search | PASS | 2026-04-14 21:45 UTC | — |
| VQR-10 | `POST` | Vector oversampling parameter | **FAIL** | 2026-04-14 21:45 UTC | — |
| VQR-11 | `POST POST` | Vector weight affects hybrid scoring | PASS | 2026-04-14 21:45 UTC | — |
| VQR-12 | `POST` | orderby overrides vector ranking | PASS | 2026-04-14 21:45 UTC | — |
| VQR-13 | `POST` | k=50, top=3 returns exactly 3 | PASS | 2026-04-14 21:45 UTC | — |
| VQR-14 | `POST` | Vector + $count | PASS | 2026-04-14 21:45 UTC | — |
| VQR-15 | `POST` | Vector + category facets | PASS | 2026-04-14 21:45 UTC | — |
| VQR-16 | `POST` | Large k=500 substantial results | PASS | 2026-04-14 21:45 UTC | — |

## Phase 19 — Advanced Queries (11/12 passed)

| Test | HTTP | Operation | Result | Last Run | Bug |
|------|------|-----------|--------|----------|-----|
| ADV-01 | `POST` | Suggest fuzzy — misspelled input | PASS | 2026-04-14 21:45 UTC | — |
| ADV-02 | `POST` | Suggest with filter | PASS | 2026-04-14 21:45 UTC | — |
| ADV-03 | `POST` | Suggest @search.text structure | PASS | 2026-04-14 21:45 UTC | — |
| ADV-04 | `POST` | Suggest with $select | PASS | 2026-04-14 21:45 UTC | — |
| ADV-05 | `GET` | Autocomplete oneTerm — text + queryPlusText | PASS | 2026-04-14 21:45 UTC | — |
| ADV-06 | `GET` | Autocomplete fuzzy — misspelled input | PASS | 2026-04-14 21:45 UTC | — |
| ADV-07 | `POST` | Fuzzy search (~1) | PASS | 2026-04-14 21:45 UTC | — |
| ADV-08 | `POST` | Proximity search ("words"~5) | **FAIL** | 2026-04-14 21:45 UTC | — |
| ADV-09 | `POST` | Fielded search (Description:luxury) | PASS | 2026-04-14 21:45 UTC | — |
| ADV-10 | `POST POST` | Boosted term (luxury^5) | PASS | 2026-04-14 21:45 UTC | — |
| ADV-11 | `POST` | French text search on Description_fr | PASS | 2026-04-14 21:45 UTC | — |
| ADV-12 | `POST` | Regex /[Hh]otel/ validated | PASS | 2026-04-14 21:45 UTC | — |

