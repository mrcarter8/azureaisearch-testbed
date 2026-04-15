"""Probe agentic retrieval on serverless — capture FULL response bodies via Entra auth."""
import json
import os
import subprocess
import time

import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.environ["SEARCH_ENDPOINT"]
API_VERSION = os.environ.get("SEARCH_API_VERSION", "2025-11-01-preview")
AOAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AOAI_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AOAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
AOAI_MODEL = os.environ.get("AZURE_OPENAI_CHAT_MODEL", "gpt-4.1-mini")

# Get Entra token
token = subprocess.check_output(
    ["powershell", "-Command", 'az account get-access-token --resource "https://search.azure.com" --query accessToken -o tsv']
).decode().strip()

HEADERS = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
INDEX_NAME = "smoke-agt-probe"
KS_NAME = "smoke-ks-probe"
KB_NAME = "smoke-kb-probe"


def url(path):
    return f"{ENDPOINT}{path}?api-version={API_VERSION}"


def probe(label, resp):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  {resp.request.method} ...{resp.request.path_url}")
    print(f"  Status: {resp.status_code}")
    rid = resp.headers.get("request-id", resp.headers.get("x-ms-request-id", "—"))
    print(f"  request-id: {rid}")
    try:
        body = resp.json()
        print(f"  Response JSON:\n{json.dumps(body, indent=2)[:3000]}")
    except Exception:
        print(f"  Response text: {resp.text[:1000]}")
    print(f"{'='*70}")
    return resp


# --- Step 1: Create index ---
print("\n>>> Step 1: Create index")
index_body = {
    "name": INDEX_NAME,
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
        {"name": "title", "type": "Edm.String", "searchable": True},
        {"name": "description", "type": "Edm.String", "searchable": True},
        {"name": "category", "type": "Edm.String", "searchable": True, "filterable": True},
    ],
    "semantic": {
        "configurations": [{
            "name": "agt-semantic-config",
            "prioritizedFields": {
                "prioritizedContentFields": [{"fieldName": "description"}],
                "titleField": {"fieldName": "title"},
                "prioritizedKeywordsFields": [{"fieldName": "category"}],
            },
        }],
    },
}
requests.delete(url(f"/indexes/{INDEX_NAME}"), headers=HEADERS)
time.sleep(1)
r = probe("CREATE INDEX", requests.put(url(f"/indexes/{INDEX_NAME}"), headers=HEADERS, json=index_body))

if r.status_code in (200, 201):
    docs = {"value": [
        {"@search.action": "upload", "id": "1", "title": "Grand Resort", "description": "Luxury hotel with pool and spa in downtown", "category": "Luxury"},
        {"@search.action": "upload", "id": "2", "title": "Budget Inn", "description": "Affordable hotel near airport with breakfast", "category": "Budget"},
    ]}
    probe("UPLOAD DOCS", requests.post(url(f"/indexes/{INDEX_NAME}/docs/index"), headers=HEADERS, json=docs))
    time.sleep(2)

# --- Step 2: Create knowledge source ---
print("\n>>> Step 2: Create knowledge source")
ks_body = {
    "name": KS_NAME,
    "kind": "searchIndex",
    "searchIndexParameters": {
        "searchIndexName": INDEX_NAME,
        "sourceDataFields": [{"name": "description"}, {"name": "category"}],
        "semanticConfigurationName": "agt-semantic-config",
    },
}
requests.delete(url(f"/knowledgesources/{KS_NAME}"), headers=HEADERS)
time.sleep(1)
probe("CREATE KS", requests.put(url(f"/knowledgesources/{KS_NAME}"), headers=HEADERS, json=ks_body))

# --- Step 3: Create knowledge base ---
print("\n>>> Step 3: Create knowledge base")
kb_body = {
    "name": KB_NAME,
    "knowledgeSources": [{"name": KS_NAME}],
    "models": [{
        "kind": "azureOpenAI",
        "azureOpenAIParameters": {
            "resourceUri": AOAI_ENDPOINT,
            "deploymentId": AOAI_DEPLOYMENT,
            "apiKey": AOAI_KEY,
            "modelName": AOAI_MODEL,
        },
    }],
}
requests.delete(url(f"/knowledgebases/{KB_NAME}"), headers=HEADERS)
time.sleep(1)
probe("CREATE KB", requests.put(url(f"/knowledgebases/{KB_NAME}"), headers=HEADERS, json=kb_body))

# --- Step 4: Retrieve extractiveData ---
print("\n>>> Step 4: Retrieve extractiveData")
body = {
    "messages": [{"role": "user", "content": [{"type": "text", "text": "Find luxury hotels with pools"}]}],
    "outputMode": "extractiveData",
}
probe("RETRIEVE EXTRACTIVE", requests.post(url(f"/knowledgebases/{KB_NAME}/retrieve"), headers=HEADERS, json=body))

# --- Step 5: Retrieve answerSynthesis ---
print("\n>>> Step 5: Retrieve answerSynthesis")
body2 = {
    "messages": [{"role": "user", "content": [{"type": "text", "text": "What is the best hotel for families?"}]}],
    "outputMode": "answerSynthesis",
}
probe("RETRIEVE ANSWER SYNTHESIS", requests.post(url(f"/knowledgebases/{KB_NAME}/retrieve"), headers=HEADERS, json=body2))

# --- Cleanup ---
print("\n>>> Cleanup")
requests.delete(url(f"/knowledgebases/{KB_NAME}"), headers=HEADERS)
requests.delete(url(f"/knowledgesources/{KS_NAME}"), headers=HEADERS)
requests.delete(url(f"/indexes/{INDEX_NAME}"), headers=HEADERS)
print("Done.")
