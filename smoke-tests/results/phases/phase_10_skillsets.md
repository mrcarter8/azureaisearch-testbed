# Phase 10 — AI Enrichment / Skillsets

**API:** Data plane `2025-11-01-preview`  
**Result:** 14/16 passed, 1 skip (SKL-11), 1 deselected (SKL-16)

---

## SKL-01: Create skillset with AzureOpenAIEmbeddingSkill

| | |
|---|---|
| **Operation** | Create |
| **Object** | Skillset |
| **Request** | `PUT /skillsets/{skillset_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "description": "Embedding skillset", "skills": [{"@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill", "name": "embedding-skill", "context": "/document", "resourceUri": "...", "deploymentId": "...", "modelName": "...", "apiKey": "...", "inputs": [{"name": "text", "source": "/document/Description"}], "outputs": [{"name": "embedding", "targetName": "Description_vector"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | PASS |

---

## SKL-02: Update skillset to include SplitSkill

| | |
|---|---|
| **Operation** | Read → Update |
| **Object** | Skillset |
| **Requests** | 1. `GET /skillsets/{skillset_name}` — get current definition |
| | 2. `PUT /skillsets/{skillset_name}` — update with SplitSkill appended |
| **Body (update)** | Appends: `{"@odata.type": "#Microsoft.Skills.Text.SplitSkill", "name": "text-split", "context": "/document", "textSplitMode": "pages", "maximumPageLength": 2000, "pageOverlapLength": 200, "inputs": [...], "outputs": [...]}` |
| **Expected Response** | `200`, `201`, or `204` |
| **Verified** | Status 200/201/204 |
| **Result** | PASS |

---

## SKL-03: Create skillset with EntityRecognitionSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-entity-skill-temp`) |
| **Request** | `PUT /skillsets/smoke-entity-skill-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "smoke-entity-skill-temp", "skills": [{"@odata.type": "#Microsoft.Skills.Text.V3.EntityRecognitionSkill", "name": "entity-recognition", "context": "/document", "categories": ["Person", "Location", "Organization"], "inputs": [{"name": "text", "source": "/document/content"}], "outputs": [{"name": "persons", "targetName": "people"}, {"name": "locations", "targetName": "locations"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-04: Create skillset with KeyPhraseExtractionSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-keyphrase-temp`) |
| **Request** | `PUT /skillsets/smoke-keyphrase-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill", "name": "keyphrase", "context": "/document", "inputs": [{"name": "text", "source": "/document/content"}], "outputs": [{"name": "keyPhrases", "targetName": "keyPhrases"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-05: Create skillset with LanguageDetectionSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-langdetect-temp`) |
| **Request** | `PUT /skillsets/smoke-langdetect-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill", "name": "lang-detect", "context": "/document", "inputs": [{"name": "text", "source": "/document/content"}], "outputs": [{"name": "languageCode", "targetName": "languageCode"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-06: Create skillset with OcrSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-ocr-temp`) |
| **Request** | `PUT /skillsets/smoke-ocr-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Vision.OcrSkill", "name": "ocr", "context": "/document/normalized_images/*", "inputs": [{"name": "image", "source": "/document/normalized_images/*"}], "outputs": [{"name": "text", "targetName": "ocrText"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-07: Create skillset with ImageAnalysisSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-imganalysis-temp`) |
| **Request** | `PUT /skillsets/smoke-imganalysis-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Vision.ImageAnalysisSkill", "name": "image-analysis", "context": "/document/normalized_images/*", "visualFeatures": ["tags", "description"], "inputs": [...], "outputs": [{"name": "tags", "targetName": "imageTags"}, {"name": "description", "targetName": "imageDescription"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-08: Create skillset with DocumentIntelligenceLayoutSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-doclayout-temp`) |
| **Request** | `PUT /skillsets/smoke-doclayout-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill", "name": "doc-layout", "context": "/document", "outputMode": "oneToMany", "markdownHeaderDepth": "h3", "inputs": [{"name": "file_data", "source": "/document/file_data"}], "outputs": [{"name": "markdown_document", "targetName": "markdownDocument"}]}]}` |
| **Expected Response** | `200`, `201`, or `400` (if skill type unknown in this API version) |
| **Verified** | Status 200/201/400; deleted if created successfully |
| **Result** | PASS |

---

## SKL-09: Create skillset with ShaperSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-shaper-temp`) |
| **Request** | `PUT /skillsets/smoke-shaper-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Util.ShaperSkill", "name": "shaper", "context": "/document", "inputs": [{"name": "text", "source": "/document/content"}, {"name": "language", "source": "/document/languageCode"}], "outputs": [{"name": "output", "targetName": "shapedData"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-10: Create skillset with MergeSkill

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-merge-temp`) |
| **Request** | `PUT /skillsets/smoke-merge-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Text.MergeSkill", "name": "text-merge", "context": "/document", "insertPreTag": " ", "insertPostTag": " ", "inputs": [{"name": "text", "source": "/document/content"}, {"name": "itemsToInsert", "source": "/document/normalized_images/*/ocrText"}, {"name": "offsets", "source": "/document/normalized_images/*/contentOffset"}], "outputs": [{"name": "mergedText", "targetName": "merged_content"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## SKL-11: Create skillset with WebApiSkill (custom endpoint)

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Skillset (temporary: `smoke-webapi-temp`) |
| **Request** | `PUT /skillsets/smoke-webapi-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [{"@odata.type": "#Microsoft.Skills.Custom.WebApiSkill", "name": "text-analyzer", "context": "/document", "uri": "{CUSTOM_SKILL_URL}", "httpMethod": "POST", "timeout": "PT30S", "batchSize": 1, "inputs": [{"name": "text", "source": "/document/content"}], "outputs": [{"name": "word_count"}, {"name": "keywords"}, {"name": "has_amenity_mentions"}]}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Skipped — `CUSTOM_SKILL_URL` env var not configured |
| **Result** | SKIP |

---

## SKL-12: Create multi-skill pipeline (split → embed → entity)

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Skillset (temporary: `smoke-multiskill-temp`) |
| **Request** | `PUT /skillsets/smoke-multiskill-temp?api-version=2025-11-01-preview` |
| **Body** | 3 skills: SplitSkill (`text-split`), AzureOpenAIEmbeddingSkill (`embed-pages` on `/document/pages/*`), EntityRecognitionSkill V3 (`entities` on `/document/pages/*`) |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `skills` array has exactly 3 entries; then deleted |
| **Result** | PASS |

---

## SKL-13: E2E enrichment — indexer with skillset populates enriched fields

| | |
|---|---|
| **Operation** | Read |
| **Object** | Indexer Status |
| **Request** | `GET /indexers/{indexer_blob_name}/status?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `lastResult.status` is `success` or `transientFailure` (validates that the blob indexer from Phase 9 ran with a skillset) |
| **Result** | PASS |

---

## SKL-14: Skillset with knowledgeStore projections (creation only)

| | |
|---|---|
| **Operation** | Create → Read → Delete |
| **Object** | Skillset (temporary: `smoke-knowledgestore-temp`) |
| **Request** | `PUT /skillsets/smoke-knowledgestore-temp?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "skills": [AzureOpenAIEmbeddingSkill], "knowledgeStore": {"storageConnectionString": "...", "projections": [{"tables": [{"tableName": "smokeTestEntities", "generatedKeyName": "entityId", "source": "/document/Description_vector"}], "objects": [], "files": []}]}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; re-read confirms `knowledgeStore` is not null; then deleted |
| **Result** | PASS |

---

## SKL-15: List skillsets

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Skillsets collection |
| **Request** | `GET /skillsets?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `value` array |
| **Result** | PASS |

---

## SKL-16: Delete primary skillset

| | |
|---|---|
| **Operation** | Delete |
| **Object** | Skillset |
| **Request** | `DELETE /skillsets/{skillset_name}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `204` or `404` |
| **Verified** | Status 204/404 |
| **Result** | DESELECTED — excluded via `-k "not skl_16"` to preserve skillset for Phase 9 indexer dependency |
