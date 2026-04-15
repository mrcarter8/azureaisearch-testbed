# Azure AI Search — Test Suite

Automated smoke tests for Azure AI Search covering control plane, data plane, indexers, skillsets, vectorization, agentic retrieval, and SKU-specific behavior. Runs against **any SKU** — basic, standard, standard2, standard3, free.

## Test Coverage

| Phase | Area | Tests | Description |
|-------|------|-------|-------------|
| 1 | Control Plane | SVC-01–18 | Service CRUD, keys, updates, checkNameAvailability |
| 2 | Negative / Limits | NEG-01–15 | Scaling rejection, invalid creation, feature gates, CMK |
| 3 | Authentication | SEC-01–10 | API key, Entra ID, RBAC, no-auth rejection |
| 4 | Index Management | IDX-01–16 | Index CRUD, round-trips, variants, aliases |
| 5 | Document CRUD | DOC-01–30 | Upload, merge, delete, complex types, edge cases |
| 6 | Synonym Maps | SYN-01–06 | CRUD and query expansion |
| 7 | Queries | QRY-01–38 | Filters, facets, semantic, vector, suggest, autocomplete |
| 8 | Misc Operations | MSC-01–11 | Analyze API, versioning, ETags, stats |
| 9 | Indexers | IXR-01–22 | Blob, Cosmos DB, SQL data sources and indexers |
| 10 | Skillsets | SKL-01–16 | Individual skills, pipelines, knowledge store |
| 11 | Vectorization | VEC-01–19 | Algorithms, profiles, quantization, E2E integrated vectorization |
| 12 | Agentic Retrieval | AGT-01–22 | Knowledge sources/bases, retrieve modes, MCP |
| 13 | Service Behavior | SLS-01–12 | Latency, concurrency, throttling, API compat |
| 14 | Service Limits | LIM-01–14 | Quotas, stats, usage tracking |
| 15 | Advanced Filters | FLT-01–20 | Lambda, geo, complex types, search.in, negation |
| 16 | Scoring Profiles | SCR-01–14 | Magnitude, freshness, tag, text weights |
| 17 | Semantic Search | SEM-01–12 | Reranking, answers, captions, speller |
| 18 | Vector Queries | VQR-01–16 | Relevance, modes, hybrid, scoring, facets |
| 19 | Advanced Queries | ADV-01–12 | Suggest, autocomplete, fuzzy, proximity, regex |

**~325 tests** across 19 phases.

## Per-SKU Results Dashboard

Test results are tracked per SKU in `smoke-tests/results/{sku}/test_log.md`. Set `SEARCH_SKU=basic` in your `.env`, run tests, and the dashboard updates at `results/basic/test_log.md`. Switch to `SEARCH_SKU=standard`, re-run, and `results/standard/test_log.md` gets its own dashboard. Each SKU maintains independent result history.

Result files generated per SKU (gitignored — generated on the client):

| File | Description |
|------|-------------|
| `results/{sku}/test_log.md` | Results dashboard — every test with result, timestamp, and linked ADO bug |
| `results/{sku}/known_bugs.json` | ADO bug links for tracked failures |
| `results/{sku}/junit.xml` | JUnit XML for CI integration |
| `results/{sku}/failure_report.json` | Structured failure data with HTTP context |
| `results/{sku}/failure_summary.md` | Human-readable failure summary |
| `results/{sku}/test_results.json` | Full test results |

Phase-level notes are shared across SKUs in `results/phases/`.

## Prerequisites

### Required

- **Python 3.12+** (tested on 3.14)
- **Azure subscription** with Contributor access
- **Azure CLI** (`az`) logged in

### Everything else is provisioned automatically

The `setup_resources.py` script provisions ALL dependencies from a single subscription. If a resource already exists, setup reuses it.

| # | Azure Service | SKU / Tier | What's Created | Docs |
|---|---------------|------------|----------------|------|
| 1 | **Azure AI Search** | Configurable via `SEARCH_SKU` (default: `basic`) | Search service with system-assigned managed identity, AAD+API key auth, free semantic search | [Azure AI Search](https://learn.microsoft.com/azure/search/search-what-is-azure-search) |
| 2 | **Azure OpenAI** | S0 (Standard) | Cognitive Services account + `text-embedding-3-small` (120 TPM) and `gpt-4.1-mini` (80 TPM) deployments | [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/overview) |
| 3 | **Azure Blob Storage** | Standard_LRS | Storage account + `hotels` container + 10 hotel JSON blobs | [Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/storage-blobs-overview) |
| 4 | **Azure Cosmos DB** | Serverless (NoSQL) | Cosmos DB account (serverless capacity) + `hotels-db` database + `hotels` container + 10 hotel documents | [Azure Cosmos DB for NoSQL](https://learn.microsoft.com/azure/cosmos-db/nosql/) |
| 5 | **Azure SQL Database** | Serverless General Purpose (Gen5, 1 vCore) | SQL server + `hotelsdb` database with auto-pause at 60 min, change tracking enabled + `Hotels` table + 10 rows | [Azure SQL Database](https://learn.microsoft.com/azure/azure-sql/database/serverless-tier-overview) |
| 6 | **Azure Functions** | Consumption (Linux, Python 3.11) | Function app running a custom skill (`analyze`) for skillset tests | [Azure Functions](https://learn.microsoft.com/azure/azure-functions/functions-overview) |
| 7 | **Azure Key Vault** | _(existing vault)_ | RBAC role assignment granting the search service's MSI `Key Vault Crypto Officer` — used for CMK encryption tests | [Azure Key Vault](https://learn.microsoft.com/azure/key-vault/general/overview) |

Resources are split across two resource groups:
- **Search RG** (`AZURE_RESOURCE_GROUP`) — contains only the Azure AI Search service
- **Support RG** (`SUPPORT_RESOURCE_GROUP`) — contains all other resources (Storage, Cosmos, SQL, Functions, AOAI)

## Setup

### 1. Clone and install dependencies

```powershell
# Clone the repo
git clone https://github.com/mrcarter8/azureaisearch-testbed.git
cd azureaisearch-testbed\smoke-tests

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install test dependencies
pip install -r requirements.txt

# Install setup/provisioning dependencies (only needed for setup_resources.py)
pip install -r requirements-setup.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

If you see `python : The term 'python' is not recognized`, install Python from https://www.python.org/downloads/ (3.12+) and ensure it's on your PATH.

### 2. Configure environment

Copy the template and fill in your values:

```bash
cp .env.template .env
```

**Required variables:**

| Variable | Description |
|----------|-------------|
| `SEARCH_SKU` | SKU under test: `basic`, `standard`, `standard2`, `standard3`, `free` |
| `SEARCH_ENDPOINT` | Full URL, e.g. `https://myservice.search.windows.net` |
| `SEARCH_ADMIN_KEY` | Admin API key |
| `AZURE_SUBSCRIPTION_ID` | Subscription containing the search service |
| `AZURE_RESOURCE_GROUP` | Resource group containing the search service |
| `SEARCH_SERVICE_NAME` | Service name (without domain) |
| `AZURE_TENANT_ID` | AAD tenant ID |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |

**Optional variables** — see [`.env.template`](smoke-tests/.env.template) for the full list including Blob, Cosmos DB, SQL, CMK, and custom skill configuration.

> **Security**: The `.env` file contains secrets and is gitignored. Never commit it.

### 3. Provision all dependencies (recommended for first run)

```powershell
pip install -r requirements-setup.txt
python setup_resources.py setup
```

This creates all external resources and writes `.env` with all connection strings. You only need an Azure subscription — everything else is provisioned automatically.

## Running Tests

### Mode 1: Command Line

Run the full suite:

```powershell
cd smoke-tests
.\run_smoke.ps1
```

Run a specific phase or test file:

```powershell
.\run_smoke.ps1 -TestFile "tests/test_07_queries.py"
```

Run by marker:

```powershell
.\run_smoke.ps1 -Markers "auth or indexes"
```

With resource setup/teardown:

```powershell
.\run_smoke.ps1 -Setup              # provision resources, then run
.\run_smoke.ps1 -Teardown           # run, then clean up resources
.\run_smoke.ps1 -Setup -Teardown    # full lifecycle
```

### Mode 2: VS Code + GitHub Copilot

Use GitHub Copilot as a test orchestrator, bug investigator, and telemetry explorer.

**Setup:**
1. Open the repo root in VS Code
2. Ensure the [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) and [GitHub Copilot Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat) extensions are installed
3. Install the [Azure DevOps MCP server](https://github.com/nicholasgriffintn/azure-devops-mcp) for bug filing
4. Install the [Azure MCP extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.azure-mcp) — provides Kusto telemetry queries, resource lookups, and more

**What Copilot can do in this repo:**

| Workflow | Example prompt |
|----------|----------------|
| **Run tests** | "Run the smoke tests" or "Run just Phase 7 queries" |
| **Analyze failures** | "Analyze the test failures and update the dashboard" |
| **Investigate bugs** | "Investigate the SVC-05 failure using Kusto telemetry" |
| **File bugs** | "File a bug for the SVC-14 CORS failure" |
| **Check duplicates** | "Is there already a bug for the checkNameAvailability issue?" |
| **Update dashboard** | "Update test_log.md with the latest results" |
| **Trace code paths** | "Find the code path for the subscription list operation" |

Copilot is configured via:
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md) — project context, ADO defaults, bug field templates
- [`.github/ado-bug-filing.instructions.md`](.github/ado-bug-filing.instructions.md) — bug filing format, duplicate detection, repro steps HTML structure
- [`.github/bug-investigation.instructions.md`](.github/bug-investigation.instructions.md) — Kusto telemetry workflows, table catalog, ActivityId tracing
- [`.github/code-navigation.instructions.md`](.github/code-navigation.instructions.md) — AzureSearch repo structure, telemetry-to-code mapping

## Test Execution Model

Tests follow a **non-destructive** pattern:

1. **Before creating** a resource, check if it already exists (from a prior run)
2. If it exists, **delete it and wait 10 seconds** for the service to settle
3. **Create the resource** and run assertions
4. **Leave the resource in place** after the test completes

This means:
- After a run, all test indexes, synonym maps, skillsets, etc. remain on the service for manual inspection and diagnosis
- Re-running the suite is safe — each test cleans up its own predecessor before creating fresh
- Resource names are prefixed with `smoke-` for easy identification

To manually clean up all test resources:

```powershell
.\run_smoke.ps1 -Teardown
```

## Tearing Down Azure Resources

The test suite creates Azure resources via `setup_resources.py`. To **delete all provisioned infrastructure** (not just data plane objects), use the standalone teardown script:

```powershell
cd smoke-tests
python teardown_resources.py
```

This interactively prompts for confirmation, then deletes: the Azure AI Search service, Function App, OpenAI account, Cosmos DB account, SQL server, and Storage account. Resource groups are left in place (the script prints `az group delete` commands if you want to remove those too).

To skip the confirmation prompt (e.g. in CI):

```powershell
python teardown_resources.py --confirm
```

> **Note**: `teardown_resources.py` is a manual script — it is never called by `run_smoke.ps1` or the test suite. The data plane teardown (`run_smoke.ps1 -Teardown`) only removes `smoke-*` indexes, indexers, skillsets, etc. from the search service.

## Project Structure

```
.github/
  copilot-instructions.md       # Copilot project context & ADO bug templates
smoke-tests/
  .env.template                 # Environment variable template (copy to .env)
  conftest.py                   # Pytest fixtures, auth, resource naming, ensure_fresh
  run_smoke.ps1                 # Test runner script
  setup_resources.py            # Provision/teardown external resources
  teardown_resources.py         # Delete ALL provisioned Azure resources
  setup_cosmos.py               # Cosmos DB setup helper
  requirements.txt              # Test dependencies
  requirements-setup.txt        # Setup-only dependencies
  helpers/
    rest_client.py              # HTTP client for Search data + management plane
    assertions.py               # Common assertion helpers
    reporter.py                 # Failure capture & reporting
    wait.py                     # Polling utilities for async operations
  tests/
    test_01_service_mgmt.py     # Phase 1:  Control plane
    test_02_service_negative.py # Phase 2:  Negative tests
    test_03_auth.py             # Phase 3:  Authentication
    test_04_indexes.py          # Phase 4:  Index management
    test_05_documents.py        # Phase 5:  Document CRUD
    test_06_synonym_maps.py     # Phase 6:  Synonym maps
    test_07_queries.py          # Phase 7:  Queries
    test_08_misc.py             # Phase 8:  Misc operations
    test_09_indexers.py         # Phase 9:  Indexers
    test_10_skillsets.py        # Phase 10: Skillsets
    test_11_vectorization.py    # Phase 11: Vectorization
    test_12_agentic.py          # Phase 12: Agentic retrieval
    test_13_service_behavior.py # Phase 13: Service behavior
    test_14_service_limits.py   # Phase 14: Service limits
    test_15_filters.py          # Phase 15: Advanced filters
    test_16_scoring.py          # Phase 16: Scoring profiles
    test_17_semantic.py         # Phase 17: Semantic search
    test_18_vector_queries.py   # Phase 18: Vector queries
    test_19_advanced_queries.py # Phase 19: Advanced queries
  results/
    phases/                     # ✅ Phase notes (committed, shared across SKUs)
    {sku}/                      # Per-SKU results (gitignored)
      test_log.md               #   Results dashboard
      known_bugs.json           #   ADO bug links
      junit.xml                 #   JUnit XML
      failure_report.json       #   Structured failure data
      failure_summary.md        #   Failure summary
      test_results.json         #   Full test results
  sample_data/
    synonyms.txt                # Synonym rules for SYN tests
  custom_skill/
    function_app.py             # Azure Function for custom skill tests
```

## API Versions

- **Data plane**: `2025-11-01-preview`
- **Management plane**: `2026-03-01-Preview`

Configure via `SEARCH_API_VERSION` and `SEARCH_MGMT_API_VERSION` in `.env`.
