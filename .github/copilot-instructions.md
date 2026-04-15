# Azure AI Search Test Suite — Project Configuration

**Default Context:**
- Organization: msdata
- Project: Azure Search

## ADO Bug Fields

For all new bugs logged in this project, set the following fields:
- Area: Azure Search\vTeam\Unlimited
- Iteration: Before filing a bug, query ADO for the iterations under `Azure Search\Krypton` and select the iteration whose date range contains the current date. If no iteration covers today, pick the most recent one.
- Title: [Add specific title here]
- Tags: (set based on the SEARCH_SKU environment variable, e.g. #Basic, #Standard, #Standard2)

When searching for duplicates, filter to project `Azure Search`.

## Required Configuration Info in ADO Bugs Logged

Always include configuration information at the top of the Repro Steps:
- SKU: [Add SKU from SEARCH_SKU env var]
- Service name: [Add service name here]
- Subscription ID: [Add subscription ID here]
- Region: [Add region here]
- Index name: [Add index name here] (When the bug is related to any index level operation)
- AOAI Service name: [Add AOAI service name here] (Only if this is an Agentic retrieval related bug)
- AOAI Deployment name: [Add deployment name here] (Only if this is an Agentic retrieval related bug)
- Knowledge Base name: [Add knowledge base name here] (Only if this is an Agentic retrieval related bug)
- Knowledge Source name: [Add knowledge source name here] (Only if this is an Agentic retrieval related bug)

## Post-Run Failure Summary (MANDATORY)

After every test suite run, produce a **failure summary** before doing anything else. This summary must:

1. **Group failures by root cause** — cluster failures into categories (e.g., "PPE Semantic Ranker 206", "Agentic Retrieval blocked by semantic", "Indexer cascade", "SSL/TLS flakiness", "Control plane bugs", etc.)
2. **List affected tests** in each group with their test IDs
3. **Tag each group as known or unknown** — link to existing ADO bugs where applicable
4. **Provide a count table** at the bottom: Root Cause | Count | Known Issue?
5. **Call out the actionable number** — how many failures are potentially distinct vs. cascading/duplicates of known issues

This summary is the starting point for the investigation workflow below.

## Failure Investigation Workflow

After the summary is produced, every failure must be accounted for. No failure is allowed to go unresolved. For each failure (or failure group), apply this workflow:

1. **Known bug?** — Check `results/known_bugs.json` and the dashboard for existing ADO bug links. If the failure maps to a known bug, mark it and move on.
2. **Cascade?** — If the failure is a downstream consequence of another failure (e.g., indexer tests fail because data source creation failed), mark it as cascade and attribute it to the root failure.
3. **Flaky infrastructure?** — If the failure is an SSL EOF, connection reset, or similar transient error with no product cause, mark it as infra flake. If it recurs across multiple runs, consider filing a bug.
4. **Test issue?** — If the test logic itself is wrong (bad assertion, timing issue, missing setup), fix the test directly. If the test is rerun and now passes, update the bug draft as resolved and no longer track the bug draft as something we need to address. 
5. **New product bug** — If none of the above apply, investigate using the bug-investigation instructions (Kusto telemetry, ActivityId tracing, code navigation). Then:
   - Search ADO for duplicates (mandatory per ado-bug-filing instructions)
   - If duplicate found, link it
   - If no duplicate, create an **HTML bug draft** in `results/bug_drafts/` named `bug_draft_<TEST_ID>_<short_slug>.html`. Follow the Repro Steps HTML format from the ado-bug-filing instructions. Include a header comment with the proposed ADO fields (Title, Area, Iteration, Priority, Tags). Group related failures into a single draft when they share the same root cause.
   - **Never create the ADO work item until the operator explicitly approves.** Present the list of drafts and wait for the operator to review. The operator will approve, reject, or reclassify each draft.
6. **Update tracking** — After resolving each failure, update `results/known_bugs.json` with any new bug URLs and update the dashboard with bug links.

The goal: after investigation, every FAIL row in the dashboard has either a bug link, a "cascade" attribution, an "infra flake" note, or a "test fix" commit. Zero unexplained failures.

After the investigation for a failure is complete, remove any temporary files created during the investigation (e.g., Kusto query outputs, screenshots, notes) to keep the repo clean. The only artifacts that should remain are the final bug drafts and the updated `known_bugs.json`.

## Temporary File Hygiene

All throwaway scripts, data files, and diagnostic outputs created during investigation **must go in `smoke-tests/scratch/`**. This folder is gitignored and exists solely for ephemeral work. Never create `_debug_*`, `_check_*`, `_verify_*`, `_show_*`, `_probe_*`, or `_generate_*` scripts in the repo root or `smoke-tests/` directly.

Before moving on to the next failure or task, **delete the files you created in `scratch/`** (or wipe the folder). Do not accumulate stale scratch files across investigations.

The only persistent investigation artifacts are:
- `results/bug_drafts/*.html` — approved or pending bug drafts
- `results/known_bugs.json` — tracked known issues
- `results/test_log.md` — the dashboard

## Test Stability Rules

- **Admin key rotation**: The test `SVC-07` regenerates the primary admin key. After regenerating, the test **must** persist the new key to `.env` (via `dotenv.set_key`) and `os.environ` so subsequent runs don't fail with 403. This pattern applies to any test that mutates credentials or connection strings.
- **Test data assumptions**: When writing search queries in tests, verify the query terms actually exist in the test dataset (`sample_data/hotels_100.json`). For proximity searches, count the actual word distance — don't guess.