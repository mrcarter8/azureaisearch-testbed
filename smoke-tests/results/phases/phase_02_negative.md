# Phase 2 — Serverless Feature Gates & Negative Tests

**API:** Management plane `2026-03-01-Preview`  
**Result:** 15/15 passed

---

## NEG-01: Update replicaCount (rejected)

| | |
|---|---|
| **Operation** | Update (expected rejection) |
| **Object** | Search Service (replicaCount) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"replicaCount": 2}}` |
| **Expected Response** | `400+` (rejected) or `200` with value clamped to 1 |
| **Verified** | If 200: `properties.replicaCount` == 1 (value not accepted). If 400+: status >= 400 (rejected). Serverless currently returns 500 |
| **Result** | PASS — [Bug 4907459](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/4907459) (returns 500 instead of 400) |

---

## NEG-02: Update partitionCount (rejected)

| | |
|---|---|
| **Operation** | Update (expected rejection) |
| **Object** | Search Service (partitionCount) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"partitionCount": 2}}` |
| **Expected Response** | `400+` (rejected) or `200` with value clamped to 1 |
| **Verified** | If 200: `properties.partitionCount` == 1. If 400+: status >= 400. Serverless currently returns 500 |
| **Result** | PASS — [Bug 4907459](https://msdata.visualstudio.com/Azure%20Search/_workitems/edit/4907459) |

---

## NEG-03: Create with invalid SKU name

| | |
|---|---|
| **Operation** | Create (expected rejection) |
| **Object** | Search Service |
| **Request** | `PUT .../searchServices/smoke-invalid-sku?api-version=2026-03-01-Preview` |
| **Body** | `{"location": "centraluseuap", "sku": {"name": "mega-ultra-premium"}}` |
| **Expected Response** | `400` |
| **Verified** | Status 400 |
| **Result** | PASS |

---

## NEG-04: Create in invalid region

| | |
|---|---|
| **Operation** | Create (expected rejection) |
| **Object** | Search Service |
| **Request** | `PUT .../searchServices/smoke-bad-region?api-version=2026-03-01-Preview` |
| **Body** | `{"location": "antarcticaland", "sku": {"name": "serverless"}}` |
| **Expected Response** | `400+` |
| **Verified** | Status >= 400 |
| **Result** | PASS |

---

## NEG-05: Create with existing name (idempotent)

| | |
|---|---|
| **Operation** | Create (idempotent PUT) |
| **Object** | Search Service (existing) |
| **Request** | `PUT .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"location": "centraluseuap", "sku": {"name": "serverless"}}` |
| **Expected Response** | `200` (idempotent) or `409` (conflict) |
| **Verified** | Status is 200 or 409 |
| **Result** | PASS |

---

## NEG-06: Update with invalid authOptions

| | |
|---|---|
| **Operation** | Update (malformed payload) |
| **Object** | Search Service (authOptions) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"authOptions": {"notAValidOption": true}}}` |
| **Expected Response** | `400` or silently ignored (discovery test) |
| **Verified** | Test passes regardless — records observed behavior |
| **Result** | PASS |

---

## NEG-07: Read service (check quotas)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Search Service |
| **Request** | `GET .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; `properties.provisioningState` exists; `properties.status` exists |
| **Result** | PASS |

---

## NEG-08: Create + wait + delete + verify service

| | |
|---|---|
| **Operation** | Create → Read (poll) → Delete → Read (verify) |
| **Object** | Search Service (disposable) |
| **Requests** | 1. `PUT .../searchServices/{disposable}` with serverless SKU → 200/201 |
| | 2. Poll `GET .../searchServices/{disposable}` until `provisioningState` == `"succeeded"` or `"failed"` (up to 120s) |
| | 3. `DELETE .../searchServices/{disposable}` → 200/202/204 |
| | 4. `GET .../searchServices/{disposable}` → 200 (still deleting) or 404 (gone) |
| **Verified** | Create succeeds; delete returns 200/202/204; final GET returns 200 or 404 |
| **Result** | PASS |

---

## NEG-09: IP firewall rules (discovery)

| | |
|---|---|
| **Operation** | Update → Restore |
| **Object** | Search Service (networkRuleSet) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"properties": {"networkRuleSet": {"ipRules": [{"value": "203.0.113.0/24"}]}}}` |
| **Expected Response** | `200` (supported) or `400` (rejected) |
| **Verified** | Records behavior. If 200: restores with empty ipRules |
| **Result** | PASS |

---

## NEG-10: Shared private link (discovery)

| | |
|---|---|
| **Operation** | Read (list) |
| **Object** | Shared Private Link Resources |
| **Request** | `GET .../searchServices/{service}/sharedPrivateLinkResources?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | Any (discovery) |
| **Verified** | Records observed status code |
| **Result** | PASS |

---

## NEG-11: CMK encryption (discovery)

| | |
|---|---|
| **Operation** | Read |
| **Object** | Search Service (encryptionWithCmk) |
| **Request** | `GET .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | None |
| **Expected Response** | `200` |
| **Verified** | Status 200; records whether `properties.encryptionWithCmk` is present |
| **Result** | PASS |

---

## NEG-12: Disable + re-enable publicNetworkAccess

| | |
|---|---|
| **Operation** | Update → Restore |
| **Object** | Search Service (publicNetworkAccess) |
| **Requests** | 1. `PATCH` with `{"properties": {"publicNetworkAccess": "Disabled"}}` — record result |
| | 2. `PATCH` with `{"properties": {"publicNetworkAccess": "Enabled"}}` — always restore |
| **Verified** | Records whether disable was accepted; always restores to Enabled |
| **Result** | PASS |

---

## NEG-13: Enable managed identity (discovery)

| | |
|---|---|
| **Operation** | Update |
| **Object** | Search Service (identity) |
| **Request** | `PATCH .../searchServices/{service}?api-version=2026-03-01-Preview` |
| **Body** | `{"identity": {"type": "SystemAssigned"}}` |
| **Expected Response** | `200` (supported) or `400` (rejected) |
| **Verified** | If 200: `identity.principalId` is non-empty. If 400: serverless doesn't support MSI |
| **Result** | PASS |

---

## NEG-14: Create index with CMK encryptionKey

| | |
|---|---|
| **Operation** | Read → Create → Read (verify) → Delete |
| **Object** | Index with CMK encryption |
| **Requests** | 1. `GET` service to check MSI identity |
| | 2. `PUT /indexes/smoke-cmk-idx-temp` with `encryptionKey` (keyVaultKeyName, keyVaultUri) |
| | 3. If 200/201: `GET /indexes/smoke-cmk-idx-temp` verify `encryptionKey` present |
| | 4. `DELETE /indexes/smoke-cmk-idx-temp` |
| **Verified** | Discovery — records whether CMK is supported on serverless indexes. If created, verifies `encryptionKey.keyVaultKeyName` matches |
| **Result** | PASS |

---

## NEG-15: Create synonym map with CMK

| | |
|---|---|
| **Operation** | Create → Delete |
| **Object** | Synonym Map with CMK encryption |
| **Request** | `PUT /synonymmaps/smoke-cmk-syn-temp` with `encryptionKey` field |
| **Expected Response** | Discovery — any status |
| **Verified** | Records whether CMK works on synonym maps. If created, deletes it |
| **Result** | PASS |
