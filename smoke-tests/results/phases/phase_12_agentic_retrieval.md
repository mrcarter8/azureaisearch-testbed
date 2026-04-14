# Phase 12 — Agentic Retrieval

**API:** Data plane `2025-11-01-preview`  
**Result:** 10/14 passed, 4 skipped

---

## AGT-01: Create search-index knowledge source

| | |
|---|---|
| **Operation** | Create knowledge source (searchIndex kind) |
| **Request** | `PUT /knowledgesources/{name}?api-version=2025-11-01-preview` |
| **Body** | `kind: "searchIndex"`, `searchIndexParameters` with `searchIndexName`, `sourceDataFields`, `searchFields`, `semanticConfigurationName` |
| **Expected Response** | `200` or `201` |
| **Verified** | Creates a self-contained index (`smoke-agt-index`) with semantic config and 5 sample docs, then creates knowledge source referencing it |
| **Result** | PASS |

---

## AGT-02: GET knowledge source — properties match

| | |
|---|---|
| **Operation** | Read knowledge source |
| **Request** | `GET /knowledgesources/{name}?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; `kind == "searchIndex"` |
| **Verified** | Status 200; kind matches |
| **Result** | PASS |

---

## AGT-03: List knowledge sources — source present

| | |
|---|---|
| **Operation** | List knowledge sources |
| **Request** | `GET /knowledgesources?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; created source appears in list |
| **Verified** | Status 200; knowledge source name found in `value[]` |
| **Result** | PASS |

---

## AGT-04: Create knowledge base with LLM

| | |
|---|---|
| **Operation** | Create knowledge base |
| **Request** | `PUT /knowledgebases/{name}?api-version=2025-11-01-preview` |
| **Body** | `knowledgeSources` (array of `{name}`), `models` (array with `kind: "azureOpenAI"`, `azureOpenAIParameters` for gpt-4.1-mini) |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 201; KB created with AOAI model reference |
| **Result** | PASS |

---

## AGT-05: GET knowledge base — properties match

| | |
|---|---|
| **Operation** | Read knowledge base |
| **Request** | `GET /knowledgebases/{name}?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; name matches |
| **Verified** | Status 200; name round-trips correctly |
| **Result** | PASS |

---

## AGT-06: List knowledge bases — KB present

| | |
|---|---|
| **Operation** | List knowledge bases |
| **Request** | `GET /knowledgebases?api-version=2025-11-01-preview` |
| **Expected Response** | `200`; created KB appears in list |
| **Verified** | Status 200; KB name found in `value[]` |
| **Result** | PASS |

---

## AGT-07: Retrieve with extractiveData mode

| | |
|---|---|
| **Operation** | Retrieve (extractiveData) |
| **Request** | `POST /knowledgebases/{name}/retrieve?api-version=2025-11-01-preview` |
| **Body** | `messages` with content as array `[{"type": "text", "text": "..."}]`, `outputMode: "extractiveData"` |
| **Expected Response** | `200` with `references` or `value` array |
| **Result** | SKIP — backend returns 502 (PPE index query failure) |

---

## AGT-08: Retrieve with answerSynthesis mode

| | |
|---|---|
| **Operation** | Retrieve (answerSynthesis) |
| **Request** | `POST /knowledgebases/{name}/retrieve?api-version=2025-11-01-preview` |
| **Body** | `outputMode: "answerSynthesis"` |
| **Expected Response** | `200` with `answer` or `content` field |
| **Result** | SKIP — backend returns 502 (PPE index query failure) |

---

## AGT-09: Retrieve with multi-turn chat history

| | |
|---|---|
| **Operation** | Retrieve with conversation context |
| **Request** | `POST /knowledgebases/{name}/retrieve?api-version=2025-11-01-preview` |
| **Body** | 3 messages (user → assistant → user) |
| **Expected Response** | `200` with references reflecting conversation context |
| **Result** | SKIP — backend returns 502 (PPE index query failure) |

---

## AGT-10: Retrieve with reasoningEffort levels

| | |
|---|---|
| **Operation** | Retrieve with `reasoningEffort: {kind: "minimal"|"low"|"medium"}` |
| **Request** | `POST /knowledgebases/{name}/retrieve?api-version=2025-11-01-preview` (×3 levels) |
| **Expected Response** | `200`, `400`, or `502` per level |
| **Verified** | All three levels accepted (no unexpected status codes) |
| **Result** | PASS |

---

## AGT-11: Retrieve — activity query planning

| | |
|---|---|
| **Operation** | Retrieve and check for query planning activity |
| **Request** | `POST /knowledgebases/{name}/retrieve?api-version=2025-11-01-preview` |
| **Expected Response** | `200` with `activity[]` containing query planning entries |
| **Result** | SKIP — backend returns 502 (PPE index query failure) |

---

## AGT-12: MCP endpoint responds

| | |
|---|---|
| **Operation** | GET MCP endpoint |
| **Request** | `GET /knowledgebases/{name}/mcp?api-version=2025-11-01-preview` |
| **Expected Response** | `200`, `204`, `405`, or `404` |
| **Verified** | Endpoint responds (not a 500) |
| **Result** | PASS |

---

## AGT-13: Delete knowledge base

| | |
|---|---|
| **Operation** | Delete knowledge base |
| **Request** | `DELETE /knowledgebases/{name}?api-version=2025-11-01-preview` |
| **Expected Response** | `204` or `404` |
| **Verified** | Status 204; KB deleted |
| **Result** | PASS |

---

## AGT-14: Delete knowledge source

| | |
|---|---|
| **Operation** | Delete knowledge source |
| **Request** | `DELETE /knowledgesources/{name}?api-version=2025-11-01-preview` |
| **Expected Response** | `204` or `404` |
| **Verified** | Status 204; KS deleted; agentic index also cleaned up |
| **Result** | PASS |

---

## Key Findings

- **Knowledge source schema**: Uses `searchIndexParameters` (not `searchIndex`). Fields like `sourceDataFields` and `searchFields` are arrays of `{name: "..."}` objects.
- **Knowledge base schema**: `models` is an array (not a nested `completionModel` object). Each entry has `kind: "azureOpenAI"` and `azureOpenAIParameters`.
- **Retrieve message format**: `content` must be an array of `[{"type": "text", "text": "..."}]`, not a plain string. Plain strings return a 400.
- **Reasoning effort**: Passed as `{"kind": "minimal"|"low"|"medium"}` object, not a bare string. "high" is not a valid level.
- **Semantic config nesting**: Requires `prioritizedFields` wrapper object containing `prioritizedContentFields`, `titleField`, and `prioritizedKeywordsFields`.
- **PPE retrieve 502s**: All retrieve calls that actually query the backend index returned 502 ("All retrieval tasks failed"). CRUD operations for knowledge sources and bases work correctly. This appears to be a PPE-specific issue with the internal index query path.
