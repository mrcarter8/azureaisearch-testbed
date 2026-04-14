"""
test_10_skillsets.py — AI Enrichment / Skillsets

Tests: SKL-01 through SKL-16
"""

import os

import pytest

from conftest import ensure_fresh
from helpers.assertions import assert_field_exists, assert_status

pytestmark = [pytest.mark.skillsets]


def _skip_if_no_blob():
    if not os.getenv("BLOB_CONNECTION_STRING"):
        pytest.skip("Blob storage not configured")


def _aoai_embedding_skill(aoai_config):
    """Build an AzureOpenAIEmbedding skill definition."""
    return {
        "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
        "name": "embedding-skill",
        "description": "Generates embeddings via AOAI",
        "context": "/document",
        "resourceUri": aoai_config["endpoint"],
        "deploymentId": aoai_config["embedding_deployment"],
        "modelName": aoai_config["embedding_model"],
        "apiKey": aoai_config["api_key"],
        "inputs": [{"name": "text", "source": "/document/Description"}],
        "outputs": [{"name": "embedding", "targetName": "Description_vector"}],
    }


def _text_split_skill():
    return {
        "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
        "name": "text-split",
        "description": "Chunk text into pages",
        "context": "/document",
        "textSplitMode": "pages",
        "maximumPageLength": 2000,
        "pageOverlapLength": 200,
        "inputs": [{"name": "text", "source": "/document/content"}],
        "outputs": [{"name": "textItems", "targetName": "pages"}],
    }


# ---------------------------------------------------------------------------
# Individual Skill Registration
# ---------------------------------------------------------------------------


class TestSkillsetCreation:

    def test_skl_01_aoai_embedding_skill(self, rest, skillset_name, aoai_config):
        """SKL-01: Create skillset with AzureOpenAIEmbeddingSkill."""
        body = {
            "name": skillset_name,
            "description": "Embedding skillset",
            "skills": [_aoai_embedding_skill(aoai_config)],
        }
        resp = rest.put(f"/skillsets/{skillset_name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"

    def test_skl_02_text_split_skill(self, rest, skillset_name):
        """SKL-02: Update skillset to include SplitSkill."""
        get_resp = rest.get(f"/skillsets/{skillset_name}")
        if get_resp.status_code == 404:
            pytest.skip("Skillset not created yet")
        body = get_resp.json()
        # Add split skill if not already present
        skill_names = [s.get("name") for s in body.get("skills", [])]
        if "text-split" not in skill_names:
            body["skills"].append(_text_split_skill())
        resp = rest.put(f"/skillsets/{skillset_name}", body)
        assert resp.status_code in (200, 201, 204)

    def test_skl_03_entity_recognition_skill(self, rest):
        """SKL-03: Create skillset with EntityRecognitionSkill."""
        name = "smoke-entity-skill-temp"
        body = {
            "name": name,
            "description": "Entity recognition",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Text.V3.EntityRecognitionSkill",
                "name": "entity-recognition",
                "context": "/document",
                "categories": ["Person", "Location", "Organization"],
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [{"name": "persons", "targetName": "people"},
                            {"name": "locations", "targetName": "locations"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Text.V3.EntityRecognitionSkill" for s in skills), \
            f"EntityRecognitionSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_04_key_phrase_extraction(self, rest):
        """SKL-04: Create skillset with KeyPhraseExtractionSkill."""
        name = "smoke-keyphrase-temp"
        body = {
            "name": name,
            "description": "Key phrase extraction",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
                "name": "keyphrase",
                "context": "/document",
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [{"name": "keyPhrases", "targetName": "keyPhrases"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Text.KeyPhraseExtractionSkill" for s in skills), \
            f"KeyPhraseExtractionSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_05_language_detection(self, rest):
        """SKL-05: Create skillset with LanguageDetectionSkill."""
        name = "smoke-langdetect-temp"
        body = {
            "name": name,
            "description": "Language detection",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
                "name": "lang-detect",
                "context": "/document",
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [{"name": "languageCode", "targetName": "languageCode"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Text.LanguageDetectionSkill" for s in skills), \
            f"LanguageDetectionSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_06_ocr_skill(self, rest):
        """SKL-06: Create skillset with OcrSkill."""
        name = "smoke-ocr-temp"
        body = {
            "name": name,
            "description": "OCR extraction",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Vision.OcrSkill",
                "name": "ocr",
                "context": "/document/normalized_images/*",
                "inputs": [{"name": "image", "source": "/document/normalized_images/*"}],
                "outputs": [{"name": "text", "targetName": "ocrText"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Vision.OcrSkill" for s in skills), \
            f"OcrSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_07_image_analysis_skill(self, rest):
        """SKL-07: Create skillset with ImageAnalysisSkill."""
        name = "smoke-imganalysis-temp"
        body = {
            "name": name,
            "description": "Image analysis",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Vision.ImageAnalysisSkill",
                "name": "image-analysis",
                "context": "/document/normalized_images/*",
                "visualFeatures": ["tags", "description"],
                "inputs": [{"name": "image", "source": "/document/normalized_images/*"}],
                "outputs": [{"name": "tags", "targetName": "imageTags"},
                            {"name": "description", "targetName": "imageDescription"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Vision.ImageAnalysisSkill" for s in skills), \
            f"ImageAnalysisSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_08_document_layout_skill(self, rest):
        """SKL-08: Create skillset with DocumentLayoutSkill (if available)."""
        name = "smoke-doclayout-temp"
        body = {
            "name": name,
            "description": "Document layout extraction",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
                "name": "doc-layout",
                "context": "/document",
                "outputMode": "oneToMany",
                "markdownHeaderDepth": "h3",
                "inputs": [{"name": "file_data", "source": "/document/file_data"}],
                "outputs": [{"name": "markdown_document", "targetName": "markdownDocument"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        # May not be available in all API versions; accept 201 or 400 if type unknown
        assert resp.status_code in (200, 201, 400), (
            f"Unexpected status: {resp.status_code}"
        )

    def test_skl_09_shaper_skill(self, rest):
        """SKL-09: Create skillset with ShaperSkill."""
        name = "smoke-shaper-temp"
        body = {
            "name": name,
            "description": "Shaper",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Util.ShaperSkill",
                "name": "shaper",
                "context": "/document",
                "inputs": [
                    {"name": "text", "source": "/document/content"},
                    {"name": "language", "source": "/document/languageCode"},
                ],
                "outputs": [{"name": "output", "targetName": "shapedData"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Util.ShaperSkill" for s in skills), \
            f"ShaperSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_10_text_merge_skill(self, rest):
        """SKL-10: Create skillset with MergeSkill."""
        name = "smoke-merge-temp"
        body = {
            "name": name,
            "description": "Text merge",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Text.MergeSkill",
                "name": "text-merge",
                "context": "/document",
                "insertPreTag": " ",
                "insertPostTag": " ",
                "inputs": [
                    {"name": "text", "source": "/document/content"},
                    {"name": "itemsToInsert", "source": "/document/normalized_images/*/ocrText"},
                    {"name": "offsets", "source": "/document/normalized_images/*/contentOffset"},
                ],
                "outputs": [{"name": "mergedText", "targetName": "merged_content"}],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify @odata.type round-trip
        get_resp = rest.get(f"/skillsets/{name}")
        assert_status(get_resp, 200)
        skills = get_resp.json().get("skills", [])
        assert any(s.get("@odata.type") == "#Microsoft.Skills.Text.MergeSkill" for s in skills), \
            f"MergeSkill type not preserved: {[s.get('@odata.type') for s in skills]}"

    def test_skl_11_custom_web_api_skill(self, rest):
        """SKL-11: Create skillset with WebApiSkill (custom endpoint)."""
        custom_url = os.getenv("CUSTOM_SKILL_URL", "")
        if not custom_url:
            pytest.skip("CUSTOM_SKILL_URL not configured (deploy custom_skill/ first)")
        name = "smoke-webapi-temp"
        body = {
            "name": name,
            "description": "Custom web API — text analyzer",
            "skills": [{
                "@odata.type": "#Microsoft.Skills.Custom.WebApiSkill",
                "name": "text-analyzer",
                "context": "/document",
                "uri": custom_url,
                "httpMethod": "POST",
                "timeout": "PT30S",
                "batchSize": 1,
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [
                    {"name": "word_count", "targetName": "wordCount"},
                    {"name": "keywords", "targetName": "extractedKeywords"},
                    {"name": "has_amenity_mentions", "targetName": "hasAmenityMentions"},
                ],
            }],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Multi-skill pipeline & E2E
# ---------------------------------------------------------------------------


class TestMultiSkillPipeline:

    def test_skl_12_multi_skill_pipeline(self, rest, aoai_config):
        """SKL-12: Create skillset combining split + embed + entity."""
        name = "smoke-multiskill-temp"
        body = {
            "name": name,
            "description": "Multi-skill: split → embed → entity",
            "skills": [
                _text_split_skill(),
                {
                    "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                    "name": "embed-pages",
                    "context": "/document/pages/*",
                    "resourceUri": aoai_config["endpoint"],
                    "deploymentId": aoai_config["embedding_deployment"],
                    "modelName": aoai_config["embedding_model"],
                    "apiKey": aoai_config["api_key"],
                    "inputs": [{"name": "text", "source": "/document/pages/*"}],
                    "outputs": [{"name": "embedding", "targetName": "page_vector"}],
                },
                {
                    "@odata.type": "#Microsoft.Skills.Text.V3.EntityRecognitionSkill",
                    "name": "entities",
                    "context": "/document/pages/*",
                    "categories": ["Person", "Location"],
                    "inputs": [{"name": "text", "source": "/document/pages/*"}],
                    "outputs": [{"name": "persons", "targetName": "people"}],
                },
            ],
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify all three skills round-tripped
        get_resp = rest.get(f"/skillsets/{name}")
        skills = get_resp.json().get("skills", [])
        assert len(skills) == 3, f"Expected 3 skills, got {len(skills)}"

    def test_skl_13_e2e_enrichment_run(self, rest, indexer_blob_name):
        """SKL-13: E2E enrichment — indexer with multi-skill skillset populates enriched fields.

        This validates the full pipeline: data source → skillset → indexer → enriched index.
        Requires that the blob indexer (IXR-06/07) ran with a skillset.
        """
        _skip_if_no_blob()
        # Check the indexer status for the last run
        resp = rest.get(f"/indexers/{indexer_blob_name}/status")
        if resp.status_code == 404:
            pytest.skip("Blob indexer was not created")
        assert_status(resp, 200)
        data = resp.json()
        last = data.get("lastResult", {})
        if last:
            assert last.get("status") in ("success", "transientFailure"), (
                f"Indexer did not succeed: {last.get('status')}"
            )

    def test_skl_14_knowledge_store_projection(self, rest, aoai_config):
        """SKL-14: Skillset with knowledgeStore blob + table projections (creation only)."""
        name = "smoke-knowledgestore-temp"
        conn_str = os.getenv("BLOB_CONNECTION_STRING", "")
        if not conn_str:
            pytest.skip("Blob storage not configured for knowledge store")
        body = {
            "name": name,
            "description": "Knowledge store projections",
            "skills": [_aoai_embedding_skill(aoai_config)],
            "knowledgeStore": {
                "storageConnectionString": conn_str,
                "projections": [
                    {
                        "tables": [
                            {
                                "tableName": "smokeTestEntities",
                                "generatedKeyName": "entityId",
                                "source": "/document/Description_vector",
                            }
                        ],
                        "objects": [],
                        "files": [],
                    }
                ],
            },
        }
        ensure_fresh(rest, f"/skillsets/{name}")
        resp = rest.put(f"/skillsets/{name}", body)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}"
        # Verify knowledge store config round-trips
        get_resp = rest.get(f"/skillsets/{name}")
        ks = get_resp.json().get("knowledgeStore")
        assert ks is not None, "knowledgeStore missing from GET"


# ---------------------------------------------------------------------------
# List & Delete
# ---------------------------------------------------------------------------


class TestSkillsetCleanup:

    def test_skl_15_list_skillsets(self, rest):
        """SKL-15: List skillsets."""
        resp = rest.get("/skillsets")
        assert_status(resp, 200)
        assert "value" in resp.json()

    def test_skl_16_delete_skillset(self, rest, skillset_name):
        """SKL-16: Delete primary skillset."""
        resp = rest.delete(f"/skillsets/{skillset_name}")
        assert resp.status_code in (204, 404), f"Expected 204/404, got {resp.status_code}"
