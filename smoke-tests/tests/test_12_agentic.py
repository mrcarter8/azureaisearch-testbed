"""
test_12_agentic.py — Agentic Retrieval: Knowledge Sources, Knowledge Bases, Retrieve

Tests: AGT-01 through AGT-22
Uses api-version=2025-11-01-preview
"""

import os
import time

import pytest

from conftest import ensure_fresh
from helpers.assertions import assert_field_exists, assert_status

pytestmark = [pytest.mark.agentic]


def _skip_if_no_aoai(aoai_config):
    if not aoai_config.get("endpoint"):
        pytest.skip("AOAI not configured")


# ---------------------------------------------------------------------------
# Helpers — self-contained index for agentic retrieval
# ---------------------------------------------------------------------------

_AGT_INDEX_NAME = "smoke-agt-index"


def _ensure_agentic_index(rest):
    """Create a small index with semantic config and sample docs for agentic tests."""
    body = {
        "name": _AGT_INDEX_NAME,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True},
            {"name": "description", "type": "Edm.String", "searchable": True},
            {"name": "category", "type": "Edm.String", "searchable": True, "filterable": True},
            {"name": "rating", "type": "Edm.Double", "filterable": True, "sortable": True},
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
    ensure_fresh(rest, f"/indexes/{_AGT_INDEX_NAME}")
    resp = rest.put(f"/indexes/{_AGT_INDEX_NAME}", body)
    assert resp.status_code in (200, 201), f"Index create failed: {resp.status_code}: {resp.text[:300]}"

    # Upload sample docs
    docs = {"value": [
        {"@search.action": "upload", "id": "1", "title": "Grand Resort & Spa",
         "description": "A luxury hotel with pool, spa, and fine dining in downtown Nashville.",
         "category": "Luxury", "rating": 4.8},
        {"@search.action": "upload", "id": "2", "title": "Budget Inn Express",
         "description": "Affordable family-friendly hotel near the airport with free breakfast.",
         "category": "Budget", "rating": 3.5},
        {"@search.action": "upload", "id": "3", "title": "Boutique Hotel & Suites",
         "description": "Charming boutique hotel with rooftop bar and city views.",
         "category": "Boutique", "rating": 4.3},
        {"@search.action": "upload", "id": "4", "title": "Mountain Lodge Retreat",
         "description": "Rustic mountain retreat with hiking trails and hot springs.",
         "category": "Resort", "rating": 4.6},
        {"@search.action": "upload", "id": "5", "title": "Seaside Family Resort",
         "description": "Beachfront resort with kids club, pools, and water sports.",
         "category": "Family", "rating": 4.1},
    ]}
    resp = rest.post(f"/indexes/{_AGT_INDEX_NAME}/docs/index", docs)
    assert_status(resp, 200)
    time.sleep(2)  # Allow indexing to propagate


# ---------------------------------------------------------------------------
# Knowledge Source CRUD
# ---------------------------------------------------------------------------


class TestKnowledgeSources:

    def test_agt_01_create_knowledge_source(self, rest, knowledge_source_name,
                                             primary_index_name):
        """AGT-01: Create search-index knowledge source."""
        _ensure_agentic_index(rest)
        body = {
            "name": knowledge_source_name,
            "kind": "searchIndex",
            "searchIndexParameters": {
                "searchIndexName": _AGT_INDEX_NAME,
                "sourceDataFields": [{"name": "description"}, {"name": "category"}],
                "semanticConfigurationName": "agt-semantic-config",
            },
        }
        ensure_fresh(rest, f"/knowledgesources/{knowledge_source_name}")
        resp = rest.put(f"/knowledgesources/{knowledge_source_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}: {resp.text[:300]}"

    def test_agt_02_get_knowledge_source(self, rest, knowledge_source_name):
        """AGT-02: GET knowledge source — properties match."""
        resp = rest.get(f"/knowledgesources/{knowledge_source_name}")
        assert_status(resp, 200)
        data = resp.json()
        assert data.get("kind") == "searchIndex", f"Expected kind=searchIndex, got {data.get('kind')}"

    def test_agt_03_list_knowledge_sources(self, rest, knowledge_source_name):
        """AGT-03: List knowledge sources — source present."""
        resp = rest.get("/knowledgesources")
        assert_status(resp, 200)
        names = [ks["name"] for ks in resp.json().get("value", [])]
        assert knowledge_source_name in names, f"{knowledge_source_name} not in {names}"


# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------


class TestKnowledgeBases:

    def test_agt_04_create_knowledge_base(self, rest, knowledge_base_name,
                                           knowledge_source_name, aoai_config):
        """AGT-04: Create knowledge base with LLM and knowledge source refs."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "name": knowledge_base_name,
            "description": "Smoke test knowledge base",
            "knowledgeSources": [{"name": knowledge_source_name}],
            "models": [{
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": aoai_config["endpoint"],
                    "deploymentId": aoai_config["chat_deployment"],
                    "apiKey": aoai_config["api_key"],
                    "modelName": aoai_config["chat_model"],
                },
            }],
        }
        ensure_fresh(rest, f"/knowledgebases/{knowledge_base_name}")
        resp = rest.put(f"/knowledgebases/{knowledge_base_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}: {resp.text[:300]}"

    def test_agt_05_get_knowledge_base(self, rest, knowledge_base_name):
        """AGT-05: GET knowledge base — properties match."""
        resp = rest.get(f"/knowledgebases/{knowledge_base_name}")
        assert_status(resp, 200)
        data = resp.json()
        assert data.get("name") == knowledge_base_name

    def test_agt_06_list_knowledge_bases(self, rest, knowledge_base_name):
        """AGT-06: List knowledge bases — KB present."""
        resp = rest.get("/knowledgebases")
        assert_status(resp, 200)
        names = [kb["name"] for kb in resp.json().get("value", [])]
        assert knowledge_base_name in names, f"{knowledge_base_name} not in {names}"


# ---------------------------------------------------------------------------
# Retrieve Operations
# ---------------------------------------------------------------------------


class TestRetrieve:

    def test_agt_07_retrieve_extractive(self, rest, knowledge_base_name, aoai_config):
        """AGT-07: Retrieve with extractiveData mode — valid response structure."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Find luxury hotels with pools"}]}
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        assert "activity" in data, f"Missing 'activity' in response: {list(data.keys())}"
        assert "references" in data or "response" in data, (
            f"Missing 'references' or 'response' in response: {list(data.keys())}"
        )

    def test_agt_08_retrieve_answer_synthesis(self, rest, knowledge_base_name, aoai_config):
        """AGT-08: Retrieve with answerSynthesis mode — response text present."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "What is the best hotel for families?"}]}
            ],
            "outputMode": "answerSynthesis",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        # Response should contain text content
        response_items = data.get("response", [])
        assert len(response_items) >= 1, f"No response items: {list(data.keys())}"
        content = response_items[0].get("content", [])
        assert len(content) >= 1, f"No content in response: {response_items[0]}"
        assert content[0].get("text"), f"Empty text in response content: {content[0]}"

    def test_agt_09_retrieve_with_chat_history(self, rest, knowledge_base_name, aoai_config):
        """AGT-09: Retrieve with multi-turn chat history."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Find hotels in Nashville"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "I found several hotels in Nashville."}]},
                {"role": "user", "content": [{"type": "text", "text": "Which ones have the best rating?"}]},
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        assert "activity" in data, f"Missing 'activity' in response: {list(data.keys())}"

    def test_agt_10_retrieve_reasoning_effort(self, rest, knowledge_base_name, aoai_config):
        """AGT-10: Retrieve with different reasoningEffort levels."""
        _skip_if_no_aoai(aoai_config)
        for level in ("minimal", "low", "medium"):
            body = {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Hotels with spa amenities"}]}
                ],
                "outputMode": "extractiveData",
                "reasoningEffort": {"kind": level},
            }
            resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
            # 200 = supported, 400 = not yet supported for this level
            assert resp.status_code in (200, 400), (
                f"reasoningEffort={level}: unexpected {resp.status_code}"
            )

    def test_agt_11_retrieve_query_rewrites(self, rest, knowledge_base_name, aoai_config):
        """AGT-11: Retrieve — check activity for modelQueryPlanning / subqueries."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Compare budget and luxury hotels near downtown"}]}
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        activity = data.get("activity", [])
        assert len(activity) >= 1, f"No activity entries in response"
        types = [a.get("type", "") for a in activity]
        assert any("query" in t.lower() or "plan" in t.lower() for t in types), (
            f"No query planning in activity types: {types}"
        )


# ---------------------------------------------------------------------------
# MCP Endpoint
# ---------------------------------------------------------------------------


class TestMCPEndpoint:

    def test_agt_12_mcp_endpoint(self, rest, knowledge_base_name, aoai_config):
        """AGT-12: MCP endpoint responds (SSE or JSON)."""
        _skip_if_no_aoai(aoai_config)
        resp = rest.get(f"/knowledgebases/{knowledge_base_name}/mcp")
        # MCP may return 200 for SSE stream setup, 405 if not supported, or 404
        assert resp.status_code in (200, 405, 404), (
            f"Unexpected MCP status: {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Expanded Retrieve Tests
# ---------------------------------------------------------------------------


class TestRetrieveExpanded:

    def test_agt_15_retrieve_reference_structure(self, rest, knowledge_base_name, aoai_config):
        """AGT-15: Retrieve extractive — validate response and activity structure."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Hotels with best ratings"}]}
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        # Validate required response keys
        assert "activity" in data, f"Missing 'activity': {list(data.keys())}"
        assert "references" in data, f"Missing 'references': {list(data.keys())}"
        # Validate activity has searchIndex step
        types = [a.get("type", "") for a in data["activity"]]
        assert "searchIndex" in types, f"No searchIndex step in activity: {types}"

    def test_agt_16_retrieve_empty_query(self, rest, knowledge_base_name, aoai_config):
        """AGT-16: Retrieve with minimal query — still returns 200."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "hotel"}]}
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        assert "activity" in data, f"Missing 'activity': {list(data.keys())}"

    def test_agt_17_retrieve_long_query(self, rest, knowledge_base_name, aoai_config):
        """AGT-17: Retrieve with a long, complex query — handles gracefully."""
        _skip_if_no_aoai(aoai_config)
        long_query = (
            "I am looking for a hotel that has excellent amenities including a pool, "
            "spa, fitness center, free breakfast, and rooftop bar. It should be located "
            "near downtown with good public transit access. The hotel should have high "
            "ratings from previous guests and offer both luxury suites and budget-friendly "
            "options for families traveling with children."
        )
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": long_query}]}
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        assert "activity" in data, f"Missing 'activity': {list(data.keys())}"

    def test_agt_18_retrieve_answer_synthesis_structure(self, rest, knowledge_base_name, aoai_config):
        """AGT-18: AnswerSynthesis mode — validate response content structure."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Which hotel is best for a romantic getaway?"}]}
            ],
            "outputMode": "answerSynthesis",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        response_items = data.get("response", [])
        assert len(response_items) >= 1, f"No response items: {list(data.keys())}"
        # answerSynthesis should include a modelAnswerSynthesis activity step
        activity = data.get("activity", [])
        types = [a.get("type", "") for a in activity]
        assert "modelAnswerSynthesis" in types, f"No modelAnswerSynthesis in activity: {types}"

    def test_agt_19_retrieve_invalid_kb_404(self, rest, aoai_config):
        """AGT-19: Retrieve with non-existent knowledge base — 404."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "test"}]}
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post("/knowledgebases/nonexistent-kb-99999/retrieve", body)
        assert_status(resp, 404)

    def test_agt_20_retrieve_with_system_message(self, rest, knowledge_base_name, aoai_config):
        """AGT-20: Retrieve with system message — system context is accepted."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": "You are a hotel concierge. Be concise."}]},
                {"role": "user", "content": [{"type": "text", "text": "Find a luxury hotel"}]},
            ],
            "outputMode": "answerSynthesis",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        # 200 = accepted, 400 = system message not supported
        assert resp.status_code in (200, 400), f"Unexpected: {resp.status_code}"

    def test_agt_21_retrieve_multiple_turns_extractive(self, rest, knowledge_base_name, aoai_config):
        """AGT-21: Multi-turn extractive — follow-up returns valid response."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "What hotels do you have?"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "We have several hotels including Grand Resort, Budget Inn, and others."}]},
                {"role": "user", "content": [{"type": "text", "text": "Which one is the cheapest?"}]},
            ],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert_status(resp, 200)
        data = resp.json()
        assert "activity" in data, f"Missing 'activity': {list(data.keys())}"

    def test_agt_22_retrieve_no_messages_400(self, rest, knowledge_base_name, aoai_config):
        """AGT-22: Retrieve with empty messages array — 400 validation error."""
        _skip_if_no_aoai(aoai_config)
        body = {
            "messages": [],
            "outputMode": "extractiveData",
        }
        resp = rest.post(f"/knowledgebases/{knowledge_base_name}/retrieve", body)
        assert resp.status_code in (400, 422), \
            f"Empty messages should fail validation, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestAgenticCleanup:

    def test_agt_13_delete_knowledge_base(self, rest, knowledge_base_name):
        """AGT-13: Delete knowledge base."""
        resp = rest.delete(f"/knowledgebases/{knowledge_base_name}")
        assert resp.status_code in (204, 404), f"Expected 204/404, got {resp.status_code}"

    def test_agt_14_delete_knowledge_source(self, rest, knowledge_source_name):
        """AGT-14: Delete knowledge source."""
        resp = rest.delete(f"/knowledgesources/{knowledge_source_name}")
        assert resp.status_code in (204, 404), f"Expected 204/404, got {resp.status_code}"
