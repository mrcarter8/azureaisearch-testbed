---
description: "Use when diagnosing Azure Search issues, investigating failures, querying Kusto telemetry, or performing root cause analysis. Covers Kusto table catalog, investigation workflows, and ActivityId tracing."
---

# Bug Investigation & Kusto Diagnostics

## Kusto Cluster

- Cluster URI: https://azsearch.kusto.windows.net
- Database: AzureSearch

**Sovereign cloud clusters (use when investigating issues in these environments):**
- Fairfax: https://azsearchfairfax.kusto.usgovcloudapi.net (database: AzureSearch)
- Mooncake: https://azsearchmooncake.chinaeast2.kusto.chinacloudapi.cn (database: AzureSearch)

**External clusters for cross-service investigation:**
- ARM Production: https://armprod.kusto.windows.net (database: ARMProd) — ARM request logs; use `correlationId` to join with Search `OperationEvent.AdditionalInfo.armCorrelationId`
- Azure Compute: https://azcrp.kusto.windows.net (database: crp_allprod) — VM deployment errors, disk operations
- Azure Compute Manager: https://azurecm.kusto.windows.net (database: AzureCM) — Compute platform telemetry, useful for VMSS/node debugging

## Key Tables for Azure Search Diagnostics

- `OperationEvent` — Core table for all service operations (queries, indexing, management). Most useful for diagnosing failures.
  - Key fields: `TIMESTAMP`, `ServiceName`, `SubscriptionId`, `Name` (operation name), `Category`, `Status` (HTTP status code), `ErrorMessage`, `Failed`, `TimedOut`, `DurationMilliseconds`, `ActivityId`, `ThrottleType`, `IsThrottled`, `ApiVersion`, `UserAgent`, `IndexName`, `StatusCode`
  - **Data-plane operations** have `Name` values like `Indexes.List`, `Documents.Search`, `SynonymMaps.List`, etc.
  - **RP / management-plane operations** have `Name` values starting with `SearchServiceResource.` (e.g., `SearchServiceResource.GetResource`, `SearchServiceResource.GetResources`, `SearchServiceResource.GetSubscriptionResources`). The `Description` field contains the full request path. These entries have an empty `ServiceName` for list operations and the `AdditionalInfo` field contains `armCorrelationId` which maps to the `x-ms-request-id` returned to the caller.
  - For paginated responses (e.g., subscription-level list), each page generates a separate `OperationEvent` entry with a distinct `ActivityId` but the same `armCorrelationId` in `AdditionalInfo`.

- `SearchUsageEvent` — Periodic snapshot of service/index state. Use for SKU, capacity, and storage info. There is always a row with an empty `IndexName` for service-level metrics, such as storage. Ignore this row if you are trying to look at stats at the index level.
  - Key fields: `TIMESTAMP`, `ServiceName`, `SubscriptionId`, `ServiceType`, `Status`, `IndexName`, `DocumentCount`, `StorageSize`, `SearchUnitSize`, `SearchUnitCount`, `ReplicaCount`, `SemanticSearch`, `VectorIndexSize`, `Tags`

- `SearchLatencyMetricEvent` — Per-service search latency metrics (average/min/max/p95).
  - Key fields: `TIMESTAMP`, `Tenant` (service resource ID), `subscriptionId`, `regionName`, `metricName`, `average`, `minimum`, `maximum`, `total`, `count`, `timeGrain`

- `ThrottledSearchQueriesPercentageMetricEvent` — Throttling rate metrics per service.
  - Key fields: `TIMESTAMP`, `Tenant` (service resource ID), `subscriptionId`, `regionName`, `average`, `minimum`, `maximum`, `total`, `count`, `timeGrain`

- `SearchQueriesPerSecondMetricEvent` — QPS metrics per service.
  - Key fields: `TIMESTAMP`, `Tenant`, `subscriptionId`, `regionName`, `average`, `minimum`, `maximum`, `total`, `count`

- `IndexerUsageEvent` — Indexer health and execution stats.
  - Key fields: `TIMESTAMP`, `ServiceName`, `SubscriptionId`, `IndexerName`, `Status`, `TopLevelErrorMessage`, `FirstItemErrorMessage`, `DataSourceName`, `DataSourceType`, `TargetIndexName`, `ItemCount`, `StartTime`, `MinutesInProgress`, `Disabled`, `IsCognitiveIndexer`

- `IndexerInvocationEvent` — Detailed per-invocation indexer execution data. More granular than `IndexerUsageEvent`. Use for investigating specific indexer runs.
  - Key fields: `TIMESTAMP`, `Stamp`, `Role`, `SubscriptionId`, `ServiceName`, `IndexerName`, `Duration`, `TopLevelErrorMessage`
  - Filter by `Role == "ContentProcessor"` for content processor execution details.

- `IndexerQueueUsageEvent` — Content Processor queue depth and processing delay metrics. Use to detect if indexer workloads are bottlenecked.
  - Key fields: `TIMESTAMP`, `Stamp`, `Role`, `RoleInstance`, `MaxWorkItemProcessingDelayInSeconds`, `AvgWorkItemProcessingDelayInSeconds`, `PeekMessageCount`
  - Filter by `Role == "StampController"` for queue metrics.

- `SubscriptionSkuEvent` — SKU quota limits per subscription/region. Use to check free/unlimited quota state.
  - Key fields: `TIMESTAMP`, `SubscriptionId`, `Region`, `SkuQuotaLimits`, `LastUpdated`

- `CapacityMetricEvent` — Stamp-level capacity metrics.
  - Key fields: `TIMESTAMP`, `Stamp`, `Tenant`, `Role`

- `CustomLogEvent` — Detailed RP-level request logs. Contains the full internal processing trace for management-plane operations (stamp controller calls, service enumeration, errors during list operations). Filter by `Role == 'ResourceProvider'` and use `ActivityId` to correlate with `OperationEvent` entries. The `Message` field contains timestamped log lines with request paths, status codes, and stack traces for failures.

- `RPServiceMetadataEventV2` — RP metadata snapshots for each service. Contains the authoritative RP record including `Sku`, `HostingMode`, `StampName`, `GeoRegion`, `CloudServiceName` (resource group), and a `Metadata` JSON field with full service metadata. Useful for verifying how the RP tracks a service internally.

- `ApplicationEvents` — Low-level platform/application events on nodes.
  - Key fields: `TIMESTAMP`, `Stamp`, `Tenant`, `Role`, `RoleInstance`, `EventDescription`, `EventData`

## Common Diagnostic Queries

When investigating issues:
1. Use `OperationEvent` filtered by `ServiceName` or `SubscriptionId` as the primary starting point
2. Filter by `Failed == true` or non-2xx `StatusCode` to find errors
3. Use `ThrottledSearchQueriesPercentageMetricEvent` to detect throttling spikes
4. Cross-reference `ActivityId` across tables to correlate events
5. Use `SubscriptionSkuEvent` to check quota limits for free/unlimited SKU issues

## Typical Investigation Steps

1. Query `OperationEvent` for failures in the last 2 hours filtered by a service name or subscription
2. For RP/management-plane operations, filter `OperationEvent` by `Name startswith 'SearchServiceResource.'` and use the `Description` field to find the request path. Use `AdditionalInfo.armCorrelationId` to correlate with the `x-ms-request-id` from the HTTP response.
3. Query `CustomLogEvent` with the `ActivityId` from the `OperationEvent` entry to get the full internal processing trace (stamp controller calls, service-by-service enumeration, internal errors)
4. Identify top error messages/status codes
5. Check `ThrottledSearchQueriesPercentageMetricEvent` for throttling
6. Check `SearchLatencyMetricEvent` for latency anomalies
7. Correlate with `SubscriptionSkuEvent` if SKU limits are suspected
8. Check `RPServiceMetadataEventV2` to verify how the RP internally tracks the service (SKU, stamp, hosting mode)

## ActivityId-Based Tracing Workflow (Critical for thorough diagnosis)

When a REST request returns an error or unexpected result:
1. **Run the failing request** and look for the `x-ms-request-id` header in the response and `ActivityId` in telemetry
2. **Extract the ActivityId** — this unique identifier traces the request through all backend systems
3. **Query Kusto** with this ActivityId to find all related events:
   ```
   OperationEvent 
   | where ActivityId == "YOUR-ACTIVITY-ID-HERE"
   | project TIMESTAMP, Name, Category, Status, ErrorMessage, DurationMilliseconds
   ```
4. **Cross-reference other tables** for the same ActivityId:
   - `ApplicationEvents` — low-level platform events
   - `IndexerUsageEvent` — if indexing was involved
   - `CustomLogEvent` or `ElasticSearchLogEvent` — for additional context
5. **Timeline analysis** — sort events by TIMESTAMP to understand the sequence of failures and determine root cause

This ActivityId correlation is essential because a single user-facing error often generates multiple backend events across different components. The ActivityId ties them all together into a coherent narrative of what failed and why.

## Cross-Service ARM Correlation

When investigating management-plane failures, correlate Search RP events with ARM logs:

1. Get the `armCorrelationId` from the Search `OperationEvent`:
   ```
   OperationEvent
   | where TIMESTAMP > ago(2h)
   | where AdditionalInfo has "armCorrelationId"
   | project TIMESTAMP, Name, Description, Status, ErrorMessage, ArmCorrelationId=AdditionalInfo["armCorrelationId"], ActivityId
   | where ArmCorrelationId == "YOUR-CORRELATION-ID"
   ```

2. Look up the same correlationId in ARM Production logs:
   ```
   cluster('armprod').database('ARMProd').HttpIncomingRequests
   | where TIMESTAMP > ago(2h)
   | where correlationId == "YOUR-CORRELATION-ID"
   | project PreciseTimeStamp, operationName, httpStatusCode, targetUri, exceptionMessage, errorCode, failureCause, serviceRequestId, correlationId
   ```

This reveals what ARM saw on its side — including whether the request failed before it reached the Search RP, or if ARM retried/rejected it.

## Mandatory Kusto Investigation Before Filing Bugs

Before filing any bug, always perform a Kusto investigation and include the findings in the **Additional Details** section:
1. Look up the request's `x-ms-request-id` in `OperationEvent` — for RP operations, match via `AdditionalInfo.armCorrelationId`
2. For RP operations (`SearchServiceResource.*`), get the `ActivityId` and query `CustomLogEvent` for the full internal trace
3. Check `RPServiceMetadataEventV2` to confirm how the RP tracks the resource
4. Include key telemetry findings: operation names, durations, internal status codes, and any internal errors or anomalies

## Extracting Context from URLs

- Extract the subscription ID from the resource URL path (e.g., `/subscriptions/{subscriptionId}/...`).
- Extract the service name from the URL path (e.g., `/searchServices/{serviceName}`) or from the user's context.
- Extract the region from `RPServiceMetadataEventV2` by querying with the service name and reading the `GeoRegion` field.

## Continuous Learning

After each investigation, review whether anything was discovered that should be captured in the instructions. **Always ask the user before making changes.** Propose a specific edit and wait for approval.

Triggers — offer to update this file when you discover:
- A Kusto table or field not listed above that proved useful for diagnosis
- A new query pattern that was effective (e.g., a join between tables not documented here)
- A correction to an existing table description, field name, or query pattern
- A new external Kusto cluster or database that was needed for cross-service investigation
- A new investigation workflow step that should be standard

Also offer to update **code-navigation.instructions.md** when you discover:
- A new telemetry operation name → source code mapping
- A new namespace → source folder mapping from a stack trace
- A new component or subfolder not yet documented

Update target: The user-level copies in `{{VSCODE_USER_PROMPTS_FOLDER}}/` are the master files. If they exist there, update those. If only workspace copies exist, update the workspace copies and remind the user to sync.
