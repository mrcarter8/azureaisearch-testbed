"""Investigate agentic retrieval against serverless SKU — capture raw HTTP responses."""
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.environ["SEARCH_ENDPOINT"]
API_KEY = os.environ["SEARCH_ADMIN_KEY"]
API_VERSION = os.environ.get("SEARCH_API_VERSION", "2025-11-01-preview")
AOAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AOAI_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AOAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
AOAI_MODEL = os.environ.get("AZURE_OPENAI_CHAT_MODEL", "gpt-4.1-mini")

HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}
INDEX_NAME = "smoke-agt-debug"
KS_NAME = "smoke-ks-debug"
KB_NAME = "smoke-kb-debug"

def url(path):
    return f"{ENDPOINT}{path}?api-version={API_VERSION}"

def pprint_response(label, resp):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  {resp.request.method} {resp.url}")
    print(f"  Status: {resp.status_code}")
    rid = resp.headers.get("x-ms-request-id", "—")
    print(f"  x-ms-request-id: {rid}")
    try:
        body = resp.json()
        print(f"  Body: {json.dumps(body, indent=2)[:2000]}")
    except Exception:
        print(f"  Body: {resp.text[:1000]}")
    print(f"{'='*70}")
    return resp


# --- Step 1: Create a small index with semantic config ---
print("\n>>> Step 1: Create index for agentic tests")
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
# Delete if exists
requests.delete(url(f"/indexes/{INDEX_NAME}"), headers=HEADERS)
time.sleep(1)
r = pprint_response("CREATE INDEX", requests.put(url(f"/indexes/{INDEX_NAME}"), headers=HEADERS, json=index_body))

# Upload docs
if r.status_code in (200, 201):
    docs = {"value": [
        {"@search.action": "upload", "id": "1", "title": "Grand Resort", "description": "Luxury hotel with pool and spa", "category": "Luxury"},
        {"@search.action": "upload", "id": "2", "title": "Budget Inn", "description": "Affordable hotel near airport", "category": "Budget"},
    ]}
    pprint_response("UPLOAD DOCS", requests.post(url(f"/indexes/{INDEX_NAME}/docs/index"), headers=HEADERS, json=docs))
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
pprint_response("CREATE KNOWLEDGE SOURCE", requests.put(url(f"/knowledgesources/{KS_NAME}"), headers=HEADERS, json=ks_body))


# --- Step 3: GET knowledge source ---
print("\n>>> Step 3: GET knowledge source")
pprint_response("GET KNOWLEDGE SOURCE", requests.get(url(f"/knowledgesources/{KS_NAME}"), headers=HEADERS))


# --- Step 4: Create knowledge base ---
print("\n>>> Step 4: Create knowledge base")
kb_body = {
    "name": KB_NAME,
    "description": "Debug KB for serverless investigation",
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
pprint_response("CREATE KNOWLEDGE BASE", requests.put(url(f"/knowledgebases/{KB_NAME}"), headers=HEADERS, json=kb_body))


# --- Step 5: GET knowledge base ---
print("\n>>> Step 5: GET knowledge base")
pprint_response("GET KNOWLEDGE BASE", requests.get(url(f"/knowledgebases/{KB_NAME}"), headers=HEADERS))


# --- Step 6: Retrieve (extractiveData) ---
print("\n>>> Step 6: Retrieve (extractiveData)")
retrieve_body = {
    "messages": [
        {"role": "user", "content": [{"type": "text", "text": "Find luxury hotels with pools"}]}
    ],
    "outputMode": "extractiveData",
}
pprint_response("RETRIEVE EXTRACTIVE", requests.post(url(f"/knowledgebases/{KB_NAME}/retrieve"), headers=HEADERS, json=retrieve_body))


# --- Step 7: Retrieve (answerSynthesis) ---
print("\n>>> Step 7: Retrieve (answerSynthesis)")
retrieve_body2 = {
    "messages": [
        {"role": "user", "content": [{"type": "text", "text": "What is the best hotel for families?"}]}
    ],
    "outputMode": "answerSynthesis",
}
pprint_response("RETRIEVE ANSWER SYNTHESIS", requests.post(url(f"/knowledgebases/{KB_NAME}/retrieve"), headers=HEADERS, json=retrieve_body2))


# --- Cleanup ---
print("\n>>> Cleanup")
pprint_response("DELETE KB", requests.delete(url(f"/knowledgebases/{KB_NAME}"), headers=HEADERS))
pprint_response("DELETE KS", requests.delete(url(f"/knowledgesources/{KS_NAME}"), headers=HEADERS))
pprint_response("DELETE INDEX", requests.delete(url(f"/indexes/{INDEX_NAME}"), headers=HEADERS))

print("\n\nDONE — review the responses above for serverless SKU behavior.")
