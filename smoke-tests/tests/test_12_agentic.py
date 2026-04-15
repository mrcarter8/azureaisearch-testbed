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


def _validate_retrieve_response(data, mode="extractiveData"):
    """Shared validation for retrieve response structure per API docs.

    Every retrieve response MUST contain:
    - activity: non-empty array with typed entries (token counts > 0 where applicable)
    - references: array with type, id fields when docs are found
    - response: array with content nodes containing type + text
    For answerSynthesis: content text is LLM-generated prose (non-trivial)
    For extractiveData: content text is JSON array of extracted chunks
    """
    errors = []

    # --- activity validation ---
    activity = data.get("activity", [])
    if not activity:
        errors.append(f"activity array is empty or missing (keys: {list(data.keys())})")
    else:
        for i, a in enumerate(activity):
            if not a.get("type"):
                errors.append(f"activity[{i}] missing 'type': {a}")

    # --- references validation ---
    # Check if searchIndex activity found results
    search_count = 0
    for a in activity:
        if a.get("type") == "searchIndex":
            search_count = a.get("count", 0)
    refs = data.get("references", [])
    if search_count > 0 and not refs:
        errors.append(
            f"searchIndex returned {search_count} docs but references is empty "
            f"(keys: {list(data.keys())})"
        )
    elif not refs and search_count == 0:
        errors.append(
            f"searchIndex returned 0 documents — no references available. "
            f"Verify the knowledge source index has data."
        )
    else:
        for i, r in enumerate(refs):
            if not r.get("type"):
                errors.append(f"references[{i}] missing 'type': {list(r.keys())}")
            if not r.get("id") and r.get("id") != 0:
                errors.append(f"references[{i}] missing 'id': {list(r.keys())}")

            # --- content nodes on each reference ---
            ref_content = r.get("content")
            if ref_content is None:
                errors.append(
                    f"references[{i}] missing 'content' array: {list(r.keys())}"
                )
            elif not isinstance(ref_content, list):
                errors.append(
                    f"references[{i}].content should be a list, "
                    f"got {type(ref_content).__name__}"
                )
            elif len(ref_content) == 0:
                errors.append(f"references[{i}].content is an empty array")
            else:
                for ci, node in enumerate(ref_content):
                    node_type = node.get("type")
                    if not node_type:
                        errors.append(
                            f"references[{i}].content[{ci}] missing 'type': "
                            f"{list(node.keys())}"
                        )
                    elif node_type != "text":
                        errors.append(
                            f"references[{i}].content[{ci}].type should be "
                            f"'text', got '{node_type}'"
                        )
                    node_text = node.get("text")
                    if node_text is None:
                        errors.append(
                            f"references[{i}].content[{ci}] missing 'text': "
                            f"{list(node.keys())}"
                        )
                    elif not isinstance(node_text, str) or len(node_text.strip()) == 0:
                        errors.append(
                            f"references[{i}].content[{ci}].text is empty or "
                            f"not a string"
                        )

    # --- response + content node validation ---
    response = data.get("response", [])
    if not response:
        errors.append(f"response array is empty or missing (keys: {list(data.keys())})")
    else:
        first = response[0]
        content = first.get("content", [])
        if not content:
            errors.append(f"response[0].content is empty")
        else:
            # --- deep content node validation ---
            for ci, item in enumerate(content):
                # Each content item must have a type field
                item_type = item.get("type")
                if not item_type:
                    errors.append(
                        f"response[0].content[{ci}] missing 'type': {list(item.keys())}"
                    )
                elif item_type != "text":
                    errors.append(
                        f"response[0].content[{ci}].type should be 'text', "
                        f"got '{item_type}'"
                    )

                # Validate text field exists
                text_val = item.get("text")
                if text_val is None:
                    errors.append(
                        f"response[0].content[{ci}] missing 'text' field: "
                        f"{list(item.keys())}"
                    )

            # Mode-specific content validation
            primary_text = str(content[0].get("text", ""))
            import json as _json

            if mode == "answerSynthesis":
                # LLM-generated answer should be substantive prose
                if len(primary_text) < 30:
                    errors.append(
                        f"answerSynthesis text too short for LLM answer "
                        f"({len(primary_text)} chars): {primary_text[:200]}"
                    )
            elif mode == "extractiveData":
                # Extractive content is a JSON array of chunks
                try:
                    chunks = _json.loads(primary_text)
                    if not isinstance(chunks, list):
                        errors.append(
                            f"extractiveData text is not a JSON array: "
                            f"type={type(chunks).__name__}"
                        )
                    elif len(chunks) == 0:
                        errors.append(
                            "extractiveData returned empty chunk array — "
                            "no documents were extracted"
                        )
                    else:
                        for j, chunk in enumerate(chunks):
                            if isinstance(chunk, dict):
                                if not chunk.get("content") and not chunk.get("text"):
                                    errors.append(
                                        f"extractive chunk[{j}] missing "
                                        f"'content'/'text': {list(chunk.keys())}"
                                    )
                except (ValueError, TypeError):
                    # Not valid JSON — flag it
                    errors.append(
                        f"extractiveData text is not valid JSON: "
                        f"{primary_text[:200]}"
                    )

    assert not errors, "Retrieve response validation failed:\n  " + "\n  ".join(errors)


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
    time.sleep(5)  # Allow indexing + semantic config activation


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
        _validate_retrieve_response(data, mode="extractiveData")

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
        _validate_retrieve_response(data, mode="answerSynthesis")
        # answerSynthesis should have modelAnswerSynthesis in activity
        types = [a.get("type", "") for a in data.get("activity", [])]
        assert "modelAnswerSynthesis" in types, f"No modelAnswerSynthesis in activity: {types}"

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
        _validate_retrieve_response(data, mode="extractiveData")

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
            if resp.status_code == 400:
                # Known bug: reasoningEffort OData parameter rejection.
                # Log but fail — this is a real service defect, not expected.
                error_msg = resp.json().get("error", {}).get("message", "")
                pytest.fail(
                    f"reasoningEffort={level} returned 400: {error_msg}. "
                    f"Known issue: OData rejects 'reasoningEffort' as invalid parameter."
                )
            assert_status(resp, 200)
            _validate_retrieve_response(resp.json(), mode="extractiveData")

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
        _validate_retrieve_response(data, mode="extractiveData")
        # Additionally verify query planning activity
        activity = data.get("activity", [])
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
        """AGT-15: Retrieve extractive — validate references contain actual document data."""
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
        _validate_retrieve_response(data, mode="extractiveData")
        # Deep-validate references: each should link back to actual docs
        refs = data.get("references", [])
        assert len(refs) >= 1, "Expected at least 1 reference for 'Hotels with best ratings'"
        for i, ref in enumerate(refs):
            assert ref.get("type") == "AzureSearchDoc", (
                f"references[{i}].type should be 'AzureSearchDoc', got '{ref.get('type')}'"
            )
            # docKey should be present and non-empty
            assert ref.get("docKey"), f"references[{i}] missing docKey: {list(ref.keys())}"
            # Each reference must carry content nodes with actual document text
            ref_content = ref.get("content", [])
            assert len(ref_content) >= 1, (
                f"references[{i}] has no content nodes: {list(ref.keys())}"
            )
            for ci, node in enumerate(ref_content):
                assert node.get("type") == "text", (
                    f"references[{i}].content[{ci}].type should be 'text', "
                    f"got '{node.get('type')}'"
                )
                text_val = node.get("text", "")
                assert isinstance(text_val, str) and len(text_val.strip()) > 0, (
                    f"references[{i}].content[{ci}].text is empty or missing"
                )
        # Validate activity has searchIndex step
        types = [a.get("type", "") for a in data["activity"]]
        assert "searchIndex" in types, f"No searchIndex step in activity: {types}"

    def test_agt_16_retrieve_empty_query(self, rest, knowledge_base_name, aoai_config):
        """AGT-16: Retrieve with minimal query — still returns valid structure."""
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
        _validate_retrieve_response(data, mode="extractiveData")

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
        _validate_retrieve_response(data, mode="extractiveData")

    def test_agt_18_retrieve_answer_synthesis_structure(self, rest, knowledge_base_name, aoai_config):
        """AGT-18: AnswerSynthesis mode — validate full response and activity structure."""
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
        _validate_retrieve_response(data, mode="answerSynthesis")
        # answerSynthesis must have modelAnswerSynthesis in activity
        activity = data.get("activity", [])
        types = [a.get("type", "") for a in activity]
        assert "modelAnswerSynthesis" in types, f"No modelAnswerSynthesis in activity: {types}"
        # Verify answer text has non-trivial content referencing hotels
        answer_text = data["response"][0]["content"][0]["text"]
        assert len(answer_text) >= 30, (
            f"Answer text too short for synthesis ({len(answer_text)} chars): {answer_text[:100]}"
        )

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
        if resp.status_code == 400:
            # System message may not be supported — validate error is descriptive
            error = resp.json().get("error", {})
            assert error.get("message"), "400 response missing error message"
            pytest.skip(f"System message not supported: {error.get('message', '')[:100]}")
        assert_status(resp, 200)
        _validate_retrieve_response(resp.json(), mode="answerSynthesis")

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
        _validate_retrieve_response(data, mode="extractiveData")

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
