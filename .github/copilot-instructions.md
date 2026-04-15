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

## Required Configuration Info

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