---
description: "Use when tracing bugs to source code, reading stack traces, navigating the AzureSearch codebase, finding code paths for telemetry operations, or proposing code fixes. Covers repo structure, component mapping, and how to browse code remotely via ADO."
---

# AzureSearch Code Navigation

## Repository

- ADO Org: msdata
- ADO Project: Azure Search
- Repo: AzureSearch
- URL: https://msdata.visualstudio.com/Azure%20Search/_git/AzureSearch
- Default branch: current
- Language: C# (.NET)

## Browsing Code Remotely

The user does not have the repo cloned locally. Use the Azure DevOps MCP tools to read source files:
- `repo_list_directory` — list folder contents to navigate the tree
- `search_code` — search for class names, method names, or string literals across the repo

When investigating a bug, use `search_code` with class or method names from stack traces to find the relevant source file, then use `repo_list_directory` to explore the surrounding context.

## Top-Level Source Structure

All product code lives under `/Source/`. Each top-level folder maps to a major architectural component:

| Folder | Component | Role |
|--------|-----------|------|
| `Source/ResourceProvider/` | **Resource Provider (RP)** | Control plane — handles ARM management API requests (create, update, delete, list services). The "front door" for all management operations. |
| `Source/StampController/` | **Stamp Controller** | Per-stamp orchestrator — manages service lifecycle within a stamp (provisioning, scaling, health monitoring). The RP delegates to stamp controllers. |
| `Source/Search/` | **Search Engine (Data Plane)** | Query and indexing engine — handles `Documents.Search`, `Documents.Index`, index CRUD, and all data-plane REST APIs. |
| `Source/Enrichment/` | **Enrichment / Indexers** | Content processing — indexers, skillsets, knowledge stores, AI enrichment pipeline. |
| `Source/IndexPlacement/` | **Index Placement** | Serverless/Unlimited index placement and routing logic. Key area for serverless bugs. |
| `Source/Common/` | **Shared Libraries** | Cross-cutting concerns shared by all components. |
| `Source/Runtime/` | **Node Runtime** | Node-level agents and host processes (bootstrap, setup, system services). |
| `Source/Hosting/` | **Hosting** | Service hosting infrastructure (Windows, multiplatform, local deploy). |
| `Source/Operations/` | **Operations / DevOps Tooling** | Operational tooling, Geneva actions, cluster management scripts. |
| `Source/Telemetry/` | **Telemetry** | Telemetry pipeline definitions and Kusto table schemas. |
| `Source/Oro/` | **Oro (Billing/Metering)** | Usage metering and billing instrumentation. |
| `Source/Java/` | **Java Components** | Java-based components (Elasticsearch layer). |
| `Source/Portal/` | **Azure Portal Extension** | Portal UX for Azure Search. |
| `FrontendRepo/` | **Frontend** | Frontend assets (separate from Portal). |

## Key Subfolders by Component

### Resource Provider (RP) — `Source/ResourceProvider/`

| Path | Purpose |
|------|---------|
| `Product/ResourceProvider/Controllers/` | API controller classes. Versioned subfolders (e.g., `2024-06-01-Preview/`) contain per-API-version controllers. Base classes (e.g., `SearchServiceResourceControllerBase.cs`) hold shared logic. |
| `Product/ResourceProvider/Controllers/SearchServiceResourceControllerBase.cs` | Core CRUD operations for search services — maps to `SearchServiceResource.*` operations in Kusto `OperationEvent`. |
| `Product/ResourceProvider/Controllers/AdminStampController.cs` | Admin operations that interact with stamp controllers. |
| `Product/ResourceProvider/Controllers/SharedPrivateLinkResourcesControllerBase.cs` | Shared private link operations. |
| `Product/ResourceProvider/Controllers/NetworkSecurityPerimeterAssociationProxyControllerBase.cs` | NSP proxy operations. |
| `Product/ResourceProvider/Controllers/PrivateEndpointConnectionProxyControllerBase.cs` | Private endpoint connection management. |
| `Product/ResourceProvider/Features/` | Feature flags and feature middleware. |
| `Product/ResourceProvider/Workers/` | Background workers (async operations, polling). |
| `Product/Management/` | Service metadata, quota management, telemetry events. Contains the C# definitions for Kusto tables like `RPServiceMetadataEventV2.cs`, `SubscriptionSkuEvent.cs`, `CapacityMetricEvent.cs`. |
| `Product/Management/Services/` | Service-level management operations. |
| `Product/Management/Jobs/` | Background management jobs. |
| `Product/ResourceProvider.Contracts/` | RP data models and API contracts. |
| `Product/ResourceProvider.Contracts/Models/` | ARM request/response model classes. |

### Stamp Controller — `Source/StampController/`

| Path | Purpose |
|------|---------|
| `Product/StampControllerCore/` | Core stamp controller logic — service provisioning, scaling, health checks. |
| `Product/StampControllerWebRole.AspNetCore/` | ASP.NET Core web host for the stamp controller API. |

### Search Engine (Data Plane) — `Source/Search/`

| Path | Purpose |
|------|---------|
| `Product/SearchCore/` | Core search engine — query execution, scoring, vector search, hybrid search. |
| `Product/SearchCore.Abstractions/` | Interfaces and abstractions for the search engine. |
| `Product/SearchCore.Classic/` | Legacy/classic search engine components. |
| `Product/SearchCore.Models/` | Data models for search operations. |
| `Product/SearchWebRole.AspNetCore/` | ASP.NET Core host for the data-plane API — routes requests to SearchCore. |
| `Product/SearchAgentCore/` | Agentic retrieval / search agent logic. |
| `Product/SemanticCore/` | Semantic ranking engine. |
| `Product/SemanticClient/` | Client for semantic ranking service. |
| `Product/Diagnostics/` | Data-plane health diagnostics. |

### Shared Libraries — `Source/Common/Product/`

| Path | Purpose |
|------|---------|
| `AzureSearch.Contracts/` | Shared data contracts across all components. |
| `AzureSearch.Http/` and `AzureSearch.Http.AspNetCore/` | HTTP pipeline, middleware, request handling. |
| `AzureSearch.Storage/` and `AzureSearch.Storage.Tables/` | Azure Storage client wrappers. |
| `AzureSearch.Diagnostics/` | Shared diagnostics and telemetry helpers. |
| `AzureSearch.Identity/` | Authentication and identity. |
| `AzureSearch.Indexes/` | Shared index definitions and operations. |
| `ClusterCore.*/` | Shared cluster management libraries used by both RP and stamp controller (`ClusterCore.Clusters`, `ClusterCore.ManagementPlane`, `ClusterCore.DataPlane`, `ClusterCore.SearchServices`, `ClusterCore.AzureResourceManager`). |

## Mapping Telemetry to Code

### OperationEvent.Name → Source Code

| Telemetry operation name pattern | Source location |
|----------------------------------|-----------------|
| `SearchServiceResource.CreateOrUpdate`, `SearchServiceResource.GetResource`, etc. | `Source/ResourceProvider/Product/ResourceProvider/Controllers/SearchServiceResourceControllerBase.cs` and versioned subfolders |
| `Documents.Search`, `Documents.Index`, `Documents.Count` | `Source/Search/Product/SearchWebRole.AspNetCore/` (API routing) → `Source/Search/Product/SearchCore/` (engine) |
| `Indexes.Create`, `Indexes.List`, `Indexes.Get` | `Source/Search/Product/SearchWebRole.AspNetCore/` (index management controllers) |
| `Indexer.ScheduledRun`, `Indexer.OnDemandRun` | `Source/Enrichment/` (indexer execution engine) |
| `Diagnostics.TestCluster`, `Diagnostics.SearchIndex` | `Source/Search/Product/Diagnostics/` |

### Stack Trace Navigation

When a stack trace appears in `CustomLogEvent.Message` or `ApplicationEvents.EventData`:
1. Extract the namespace and class name (e.g., `Microsoft.Azure.Search.ResourceProvider.Controllers.SearchServiceResourceController`)
2. Map the namespace prefix to the source folder:
   - `Microsoft.Azure.Search.ResourceProvider` → `Source/ResourceProvider/`
   - `Microsoft.Azure.Search.StampController` → `Source/StampController/`
   - `Microsoft.Azure.Search.SearchCore` → `Source/Search/Product/SearchCore/`
   - `Microsoft.Azure.Search.Enrichment` → `Source/Enrichment/`
   - `Microsoft.Azure.Search.Common` → `Source/Common/`
   - `Microsoft.Azure.Search.IndexPlacement` → `Source/IndexPlacement/`
3. Use `search_code` with the class name to find the exact file
4. Read the relevant method to understand the code path

### Serverless / Unlimited

Serverless (aka "Unlimited") is a hosting mode with distinct infrastructure. Key areas:
- `Source/IndexPlacement/` — Index placement and routing logic specific to serverless
- RP controllers handle `HostingMode` checks — look for `Unlimited` or `Serverless` in `Source/ResourceProvider/`
- Stamp controller has serverless-specific provisioning paths
- Search for `Unlimited` or `HostingMode` in the codebase to find serverless-specific branches

## Continuous Learning

After navigating code during an investigation, review whether new mappings were discovered. **Always ask the user before making changes.** Propose a specific edit and wait for approval.

Triggers — offer to update this file when you discover:
- A new `OperationEvent.Name` → source file/class mapping not in the table above
- A new namespace prefix → source folder mapping from a stack trace
- A new component, subfolder, or project not yet documented
- A correction to an existing mapping (e.g., a class was renamed or moved)
- A new code pattern for serverless/Unlimited that should be noted

Update target: The user-level copies in `{{VSCODE_USER_PROMPTS_FOLDER}}/` are the master files. If they exist there, update those. If only workspace copies exist, update the workspace copies and remind the user to sync.
