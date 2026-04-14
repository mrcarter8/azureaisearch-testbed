# Azure AI Search — Serverless Test Suite

Automated smoke tests for Azure AI Search **Serverless SKU** covering control plane, data plane, indexers, skillsets, vectorization, agentic retrieval, and serverless-specific behavior.

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
| 13 | Serverless Behavior | SLS-01–12 | Latency, concurrency, throttling, API compat |
| 14 | Serverless Limits | LIM-01–14 | Quotas, stats, usage tracking |
| 15 | Advanced Filters | FLT-01–20 | Lambda, geo, complex types, search.in, negation |
| 16 | Scoring Profiles | SCR-01–14 | Magnitude, freshness, tag, text weights |
| 17 | Semantic Search | SEM-01–12 | Reranking, answers, captions, speller |
| 18 | Vector Queries | VQR-01–16 | Relevance, modes, hybrid, scoring, facets |
| 19 | Advanced Queries | ADV-01–12 | Suggest, autocomplete, fuzzy, proximity, regex |

**~325 tests** across 19 phases.

## Results Dashboard

Test results are tracked in [`smoke-tests/results/test_log.md`](smoke-tests/results/test_log.md) — a Markdown table showing every test with its result, last run timestamp, and linked ADO bug (if filed). This is the single source of truth for current test status.

Additional result files (generated per run, gitignored):
- `results/junit.xml` — JUnit XML for CI integration
- `results/failure_report.json` — Structured failure data with HTTP context
- `results/failure_summary.md` — Human-readable failure summary
- `results/test_results.json` — Full test results

## Prerequisites

### Required

- **Python 3.12+** (tested on 3.14)
- **Azure AI Search service** — Serverless SKU
- **Azure OpenAI resource** — with `text-embedding-3-small` and `gpt-4.1-mini` deployments
- **Azure subscription** — with Contributor access for management plane tests
- **Azure CLI** or **azure-identity** credentials — for Entra token acquisition

### Optional (for indexer tests)

- **Azure Blob Storage** — container with hotel JSON documents
- **Azure Cosmos DB** — NoSQL database with hotel documents
- **Azure SQL Database** — table with hotel records
- **Azure Key Vault** — for CMK encryption tests

## Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/mrcarter8/azureaisearch-testbed.git
cd azureaisearch-testbed/smoke-tests
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

Copy the template and fill in your values:

```bash
cp .env.template .env
```

**Required variables** (minimum for core tests):

| Variable | Description |
|----------|-------------|
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

### 3. Provision external resources (optional)

If you need Blob, Cosmos DB, and SQL backends for indexer tests:

```powershell
pip install -r requirements-setup.txt
python setup_resources.py setup
```

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
4. Install the [Kusto MCP server](https://github.com/nicholasgriffintn/kusto-mcp) for telemetry queries

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
- Instruction files in VS Code user prompts — bug filing format, investigation workflows, code navigation

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

## Project Structure

```
.github/
  copilot-instructions.md     # Copilot project context & ADO bug templates
smoke-tests/
  .env.template               # Environment variable template (copy to .env)
  conftest.py                 # Pytest fixtures, auth, resource naming, ensure_fresh
  run_smoke.ps1               # Test runner script
  setup_resources.py          # Provision/teardown external resources
  setup_cosmos.py             # Cosmos DB setup helper
  requirements.txt            # Test dependencies
  requirements-setup.txt      # Setup-only dependencies
  helpers/
    rest_client.py            # HTTP client for Search data + management plane
    assertions.py             # Common assertion helpers
    reporter.py               # Failure capture & reporting
    wait.py                   # Polling utilities for async operations
  tests/
    test_01_service_mgmt.py   # Phase 1: Control plane
    test_02_service_negative.py # Phase 2: Negative tests
    ...                       # Phases 3–19
  results/
    test_log.md               # ✅ Results dashboard (committed)
    known_bugs.json           # ✅ ADO bug links (committed)
    phases/                   # ✅ Phase notes (committed)
    junit.xml                 # Runtime output (gitignored)
    failure_report.json       # Runtime output (gitignored)
    failure_summary.md        # Runtime output (gitignored)
    test_results.json         # Runtime output (gitignored)
  sample_data/
    synonyms.txt              # Synonym rules for SYN tests
  custom_skill/
    function_app.py           # Azure Function for custom skill tests
```

## API Versions

- **Data plane**: `2025-11-01-preview`
- **Management plane**: `2026-03-01-Preview`

Configure via `SEARCH_API_VERSION` and `SEARCH_MGMT_API_VERSION` in `.env`.
