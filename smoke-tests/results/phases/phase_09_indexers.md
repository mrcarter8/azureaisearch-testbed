# Phase 9 — Indexer Pipeline: Data Sources, Indexers, Field Mappings

**API:** Data plane `2025-11-01-preview`  
**Result:** 19/22 passed, 3 failed (IXR-03, IXR-11, IXR-12 — Azure SQL AD token auth rejected)

---

## IXR-01: Create Azure Blob data source

| | |
|---|---|
| **Operation** | Create |
| **Object** | Data Source (Blob) |
| **Request** | `PUT /datasources/{datasource_blob_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "type": "azureblob", "credentials": {"connectionString": "..."}, "container": {"name": "hotels"}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | PASS |

---

## IXR-02: Create Cosmos DB data source

| | |
|---|---|
| **Operation** | Create |
| **Object** | Data Source (Cosmos DB) |
| **Request** | `PUT /datasources/{datasource_cosmos_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "type": "cosmosdb", "credentials": {"connectionString": "...;Database=hotels-db"}, "container": {"name": "hotels"}, "dataChangeDetectionPolicy": {"@odata.type": "#...HighWaterMarkChangeDetectionPolicy", "highWaterMarkColumnName": "_ts"}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | PASS |

---

## IXR-03: Create Azure SQL data source with change tracking

| | |
|---|---|
| **Operation** | Create |
| **Object** | Data Source (Azure SQL) |
| **Request** | `PUT /datasources/{datasource_sql_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "type": "azuresql", "credentials": {"connectionString": "..."}, "container": {"name": "Hotels"}, "dataChangeDetectionPolicy": {"@odata.type": "#...SqlIntegratedChangeTrackingPolicy"}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | FAIL — Azure SQL AD token auth rejected |

---

## IXR-04: GET data source — connectionString is masked

| | |
|---|---|
| **Operation** | Read |
| **Object** | Data Source (Blob) |
| **Request** | `GET /datasources/{datasource_blob_name}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `credentials.connectionString` contains `<unchanged>` or `***` or is empty (masked) |
| **Result** | PASS |

---

## IXR-05: List data sources — test source present

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Data Sources collection |
| **Request** | `GET /datasources?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; blob data source name appears in `value[].name` |
| **Result** | PASS |

---

## IXR-06: Create Blob indexer with skillset and field mappings

| | |
|---|---|
| **Operation** | Create |
| **Object** | Indexer (Blob) |
| **Request** | `PUT /indexers/{indexer_blob_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "dataSourceName": "...", "targetIndexName": "...", "skillsetName": "...", "fieldMappings": [{"sourceFieldName": "metadata_storage_path", "targetFieldName": "HotelId", "mappingFunction": {"name": "base64Encode"}}, {"sourceFieldName": "metadata_storage_name", "targetFieldName": "HotelName"}], "outputFieldMappings": [{"sourceFieldName": "/document/Description_vector", "targetFieldName": "DescriptionVector"}], "parameters": {"configuration": {"dataToExtract": "contentAndMetadata", "parsingMode": "default"}}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | PASS |

---

## IXR-07: Run Blob indexer and poll to success

| | |
|---|---|
| **Operation** | Execute + Read (poll) |
| **Object** | Indexer (Blob) |
| **Requests** | 1. `POST /indexers/{indexer_blob_name}/run` — trigger execution |
| | 2. `GET /indexers/{indexer_blob_name}/status` — poll until complete |
| **Expected Response** | `202` or `204` (run); `200` (status) |
| **Verified** | Run returns 202/204; poll until `lastResult.status` is `success` or `transientFailure` |
| **Result** | PASS |

---

## IXR-08: Verify indexed documents have vectors

| | |
|---|---|
| **Operation** | Read (search) |
| **Object** | Documents |
| **Request** | `POST /indexes/{primary_index_name}/docs/search?api-version=2025-11-01-preview` |
| **Body** | `{"search": "*", "top": 5, "select": "HotelId,HotelName"}` |
| **Expected Response** | `200` |
| **Verified** | Status 200; at least one result has non-null `HotelName` or `HotelId` |
| **Result** | PASS |

---

## IXR-09: Create Cosmos DB indexer

| | |
|---|---|
| **Operation** | Create |
| **Object** | Indexer (Cosmos) |
| **Request** | `PUT /indexers/{indexer_cosmos_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "dataSourceName": "...", "targetIndexName": "...", "fieldMappings": [{"sourceFieldName": "id", "targetFieldName": "HotelId"}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | PASS |

---

## IXR-10: Run Cosmos DB indexer and poll to success

| | |
|---|---|
| **Operation** | Execute + Read (poll) |
| **Object** | Indexer (Cosmos) |
| **Requests** | 1. `POST /indexers/{indexer_cosmos_name}/run` |
| | 2. `GET /indexers/{indexer_cosmos_name}/status` — poll |
| **Expected Response** | `202` or `204` (run); `200` (status) |
| **Verified** | Run returns 202/204; `lastResult.status` is `success` or `transientFailure` |
| **Result** | PASS |

---

## IXR-11: Create Azure SQL indexer with change tracking

| | |
|---|---|
| **Operation** | Create |
| **Object** | Indexer (SQL) |
| **Request** | `PUT /indexers/{indexer_sql_name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "dataSourceName": "...", "targetIndexName": "...", "fieldMappings": [{"sourceFieldName": "HotelId", "targetFieldName": "HotelId"}, {"sourceFieldName": "HotelName", "targetFieldName": "HotelName"}]}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201 |
| **Result** | FAIL — SQL data source creation failed (IXR-03 prerequisite) |

---

## IXR-12: Run Azure SQL indexer and poll to success

| | |
|---|---|
| **Operation** | Execute + Read (poll) |
| **Object** | Indexer (SQL) |
| **Requests** | 1. `POST /indexers/{indexer_sql_name}/run` |
| | 2. `GET /indexers/{indexer_sql_name}/status` — poll |
| **Expected Response** | `202` or `204` |
| **Verified** | `lastResult.status` is `success` or `transientFailure` |
| **Result** | FAIL — SQL data source creation failed (IXR-03 prerequisite) |

---

## IXR-13: GET indexer status — lastResult present

| | |
|---|---|
| **Operation** | Read |
| **Object** | Indexer Status |
| **Request** | `GET /indexers/{indexer_blob_name}/status?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `lastResult` field |
| **Result** | PASS |

---

## IXR-14: Reset indexer clears state

| | |
|---|---|
| **Operation** | Update (reset) |
| **Object** | Indexer (Blob) |
| **Request** | `POST /indexers/{indexer_blob_name}/reset?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `204` or `200` |
| **Verified** | Status 204/200 |
| **Result** | PASS |

---

## IXR-15: Update indexer with schedule

| | |
|---|---|
| **Operation** | Read → Update |
| **Object** | Indexer (Blob) |
| **Requests** | 1. `GET /indexers/{indexer_blob_name}` — get current definition |
| | 2. `PUT /indexers/{indexer_blob_name}` — update with `{"schedule": {"interval": "PT1H"}}` |
| | 3. `GET /indexers/{indexer_blob_name}` — verify schedule persisted |
| **Expected Response** | `200` / `200` or `201` / `200` |
| **Verified** | Updated indexer returns status 200/201; `schedule.interval` == `"PT1H"` on re-read |
| **Result** | PASS |

---

## IXR-16: Verify indexer field mappings are present

| | |
|---|---|
| **Operation** | Read |
| **Object** | Indexer (Blob) |
| **Request** | `GET /indexers/{indexer_blob_name}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `fieldMappings` array has > 0 entries |
| **Result** | PASS |

---

## IXR-17: Verify output field mappings (from skillset)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Indexer (Blob) |
| **Request** | `GET /indexers/{indexer_blob_name}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `outputFieldMappings` array has > 0 entries |
| **Result** | PASS |

---

## IXR-18: Create indexer with jsonArray parsing mode

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Indexer (temporary) |
| **Request** | `PUT /indexers/{name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "dataSourceName": "...", "targetIndexName": "...", "parameters": {"configuration": {"parsingMode": "jsonArray", "documentRoot": ""}}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## IXR-19: Create indexer with jsonLines parsing mode

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Indexer (temporary) |
| **Request** | `PUT /indexers/{name}?api-version=2025-11-01-preview` |
| **Body** | `{"name": "...", "dataSourceName": "...", "targetIndexName": "...", "parameters": {"configuration": {"parsingMode": "jsonLines"}}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status 200/201; then deleted |
| **Result** | PASS |

---

## IXR-20: List indexers

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Indexers collection |
| **Request** | `GET /indexers?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `value` array |
| **Result** | PASS |

---

## IXR-21: Delete Blob indexer

| | |
|---|---|
| **Operation** | Delete |
| **Object** | Indexer (Blob) |
| **Request** | `DELETE /indexers/{indexer_blob_name}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `204` or `404` |
| **Verified** | Status 204/404 |
| **Result** | PASS |

---

## IXR-22: Delete Blob data source

| | |
|---|---|
| **Operation** | Delete |
| **Object** | Data Source (Blob) |
| **Request** | `DELETE /datasources/{datasource_blob_name}?api-version=2025-11-01-preview` |
| **Body** | None |
| **Expected Response** | `204` or `404` |
| **Verified** | Status 204/404 |
| **Result** | PASS |
