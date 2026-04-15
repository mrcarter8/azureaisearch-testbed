# Phase 1 — Control Plane: Service Provisioning & Lifecycle

**API:** Management plane `2026-03-01-Preview`  
**Result:** 15/16 passed, 1 failed (SVC-05)

---

## SVC-01: Create search service (minimal)

| | |
|---|---|
| **Operation** | Create |
| **Object** | Search Service |
| **Request** | `PUT https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Search/searchServices/{disposable-name}?api-version=2026-03-01-Preview` |
| **Body** | `{"location": "centraluseuap", "sku": {"name": "{sku}"}}` |
| **Expected Response** | `200` or `201` |
| **Verified** | Status code is 200 or 201 |
| **Result** | PASS |

---

## SVC-02: Read service (validate SKU)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Search Service |
| **Request** | `GET https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Search/searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status code 200; `sku.name` matches configured SKU |
| **Result** | PASS |

---

## SVC-03: Read service (status)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Search Service |
| **Request** | `GET https://management.azure.com/.../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `sku.name` matches configured SKU; `properties.status` == `"running"` |
| **Result** | PASS |

---

## SVC-04: List services in resource group

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Search Services collection |
| **Request** | `GET https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Search/searchServices?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `value[].name` contains our service name |
| **Result** | PASS |

---

## SVC-05: List services in subscription (paginated)

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Search Services collection (subscription-level) |
| **Request** | `GET https://management.azure.com/subscriptions/{sub}/providers/Microsoft.Search/searchServices?api-version=2026-03-01-Preview` (follows `nextLink` for pagination) |
| **Body** | None |
| **Expected Response** | `200` per page |
| **Verified** | Each page returns 200; combined `value[].name` across all pages contains our service name |
| **Result** | **FAIL** — [Bug 5175978](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/5175978) |
| **Failure** | Service not found in paginated subscription listing |

---

## SVC-06: List admin keys

| | |
|---|---|
| **Operation** | Read |
| **Object** | Admin Keys |
| **Request** | `POST https://management.azure.com/.../searchServices/{service}/listAdminKeys?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `primaryKey` and `secondaryKey` |
| **Result** | PASS |

---

## SVC-07: Regenerate primary admin key

| | |
|---|---|
| **Operation** | Update |
| **Object** | Admin Key (primary) |
| **Request** | `POST https://management.azure.com/.../searchServices/{service}/regenerateAdminKey/primary?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `primaryKey`; RestClient headers updated with new key for subsequent tests |
| **Result** | PASS |

---

## SVC-08: Regenerate secondary admin key

| | |
|---|---|
| **Operation** | Update |
| **Object** | Admin Key (secondary) |
| **Request** | `POST https://management.azure.com/.../searchServices/{service}/regenerateAdminKey/secondary?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `secondaryKey` |
| **Result** | PASS |

---

## SVC-09: Create query key

| | |
|---|---|
| **Operation** | Create |
| **Object** | Query Key |
| **Request** | `POST https://management.azure.com/.../searchServices/{service}/createQueryKey/smoke-test-qk?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; response contains `key` and `name` |
| **Result** | PASS |

---

## SVC-10: List query keys

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Query Keys collection |
| **Request** | `POST https://management.azure.com/.../searchServices/{service}/listQueryKeys?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `value[].name` contains `"smoke-test-qk"` |
| **Result** | PASS |

---

## SVC-11: Create + delete + verify query key

| | |
|---|---|
| **Operation** | Create → Delete → Read (verify) |
| **Object** | Query Key |
| **Requests** | 1. `POST .../createQueryKey/smoke-throwaway-qk` → 200, capture `key` value |
| | 2. `DELETE .../deleteQueryKey/{key}` → 200 or 204 |
| | 3. `GET .../listQueryKeys` → verify `"smoke-throwaway-qk"` absent |
| **Verified** | Create returns 200 with key; delete returns 200/204; list no longer includes the deleted key name |
| **Result** | PASS |

---

## SVC-12: Update auth options

| | |
|---|---|
| **Operation** | Update → Read (verify) |
| **Object** | Search Service (authOptions) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"authOptions": {"aadOrApiKey": {"aadAuthFailureMode": "http403"}}}}` |
| **Expected Response** | `200` |
| **Verified** | PATCH returns 200; follow-up GET confirms `properties.authOptions` contains `"aadOrApiKey"` |
| **Result** | PASS |

---

## SVC-13: Update semanticSearch property

| | |
|---|---|
| **Operation** | Update |
| **Object** | Search Service (semanticSearch) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"semanticSearch": "free"}}` |
| **Expected Response** | `200` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## SVC-14: Update CORS options

| | |
|---|---|
| **Operation** | Update |
| **Object** | Search Service (corsOptions) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"corsOptions": {"allowedOrigins": ["https://smoke-test.example.com"], "maxAgeInSeconds": 300}}}` |
| **Expected Response** | `200` |
| **Verified** | Status 200 |
| **Result** | PASS |

---

## SVC-15: Enable system-assigned managed identity

| | |
|---|---|
| **Operation** | Update |
| **Object** | Search Service (identity) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"identity": {"type": "SystemAssigned"}}` |
| **Expected Response** | `200` |
| **Verified** | Status 200; `identity.principalId` is present and non-empty |
| **Result** | PASS |

---

## SVC-16: Read service (validate all properties)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Search Service |
| **Request** | `GET .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `sku.name` exists; `properties.provisioningState` exists; `properties.status` exists |
| **Result** | PASS |
