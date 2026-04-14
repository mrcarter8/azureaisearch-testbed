"""
reporter.py — Failure report generator for the Serverless bug-bash test suite.

Collects every test failure with full HTTP context (request, response,
x-ms-request-id) and writes:
  - results/failure_report.json  (machine-readable, per-run failures only)
  - results/failure_summary.md   (human-readable failure details for latest run)
  - results/test_results.json    (persistent backing store — latest state of every test)
  - results/test_log.md          (consolidated dashboard — one row per test, by phase)

Designed to be used as a pytest plugin via conftest.py.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Phase registry ───────────────────────────────────────────────────────────
# Maps test file stems to (phase number, phase title).

PHASE_MAP: dict[str, tuple[int, str]] = {
    "test_01_service_mgmt":       (1, "Control Plane"),
    "test_02_service_negative":   (2, "Negative / Limits"),
    "test_03_auth":               (3, "Authentication"),
    "test_04_indexes":            (4, "Index Management"),
    "test_05_documents":          (5, "Document CRUD"),
    "test_06_synonym_maps":       (6, "Synonym Maps"),
    "test_07_queries":            (7, "Queries"),
    "test_08_misc":               (8, "Misc Operations"),
    "test_09_indexers":           (9, "Indexers"),
    "test_10_skillsets":          (10, "Skillsets"),
    "test_11_vectorization":      (11, "Vectorization"),
    "test_12_agentic":            (12, "Agentic Retrieval"),
    "test_13_serverless_behavior": (13, "Serverless Behavior"),
    "test_14_serverless_limits":     (14, "Serverless Limits"),
    "test_15_filters":               (15, "Advanced Filters"),
    "test_16_scoring":               (16, "Scoring Profiles"),
    "test_17_semantic":              (17, "Semantic Deep-Dive"),
    "test_18_vector_queries":        (18, "Vector Queries"),
    "test_19_advanced_queries":      (19, "Advanced Queries"),
}


# ── Test metadata ────────────────────────────────────────────────────────────
# Maps test function names to (http_verbs, operation_description).

TEST_METADATA: dict[str, tuple[str, str]] = {
    # ── Phase 1: Control Plane ───────────────────────────────────────────
    "test_svc_01_create_serverless_minimal":      ("PUT",               "Create serverless service (minimal)"),
    "test_svc_02_create_serverless_with_options":  ("GET",              "Read service (validate serverless SKU)"),
    "test_svc_03_get_service":                     ("GET",              "Read service"),
    "test_svc_04_list_services_in_rg":             ("GET",              "List services in resource group"),
    "test_svc_05_list_services_in_subscription":   ("GET",              "List services in subscription (paginated)"),
    "test_svc_06_get_admin_keys":                  ("POST",             "List admin keys"),
    "test_svc_07_regenerate_admin_key_primary":    ("POST",             "Regenerate primary admin key"),
    "test_svc_08_regenerate_admin_key_secondary":  ("POST",             "Regenerate secondary admin key"),
    "test_svc_09_create_query_key":                ("POST",             "Create query key"),
    "test_svc_10_list_query_keys":                 ("POST",             "List query keys"),
    "test_svc_11_delete_query_key":                ("POST DELETE GET",  "Create + delete + verify query key"),
    "test_svc_12_update_auth_options":             ("PATCH GET",        "Update auth options + verify"),
    "test_svc_13_update_semantic_search":          ("PATCH",            "Update semanticSearch property"),
    "test_svc_14_update_cors":                     ("PATCH",            "Update CORS options"),
    "test_svc_15_enable_managed_identity":         ("PATCH",            "Enable system-assigned managed identity"),
    "test_svc_16_validate_service_properties":     ("GET",              "Read service (validate all properties)"),
    # ── Phase 2: Negative / Limits ───────────────────────────────────────
    "test_neg_01_reject_replica_count":            ("PATCH",            "Update replicaCount (rejected)"),
    "test_neg_02_reject_partition_count":          ("PATCH",            "Update partitionCount (rejected)"),
    "test_neg_03_invalid_sku_name":                ("PUT",              "Create service with invalid SKU (rejected)"),
    "test_neg_04_invalid_location":                ("PUT",              "Create service in invalid region (rejected)"),
    "test_neg_05_duplicate_service_name":          ("PUT",              "Create service with existing name (idempotent)"),
    "test_neg_06_invalid_auth_options":            ("PATCH",            "Update with invalid authOptions"),
    "test_neg_07_serverless_quotas_present":       ("GET",              "Read service (check quotas)"),
    "test_neg_08_delete_disposable_service":       ("PUT GET DELETE GET", "Create + wait + delete + verify service"),
    "test_neg_09_ip_firewall_rules":               ("PATCH",            "Update IP firewall rules (discover + restore)"),
    "test_neg_10_private_endpoint":                ("GET",              "List shared private link resources"),
    "test_neg_11_cmk_encryption":                  ("GET",              "Read service (check CMK encryption)"),
    "test_neg_12_disable_public_access":           ("PATCH PATCH",      "Disable + re-enable publicNetworkAccess"),
    "test_neg_13_enable_identity_on_service":      ("PATCH",            "Enable managed identity (discovery)"),
    "test_neg_14_create_index_with_cmk":           ("GET PUT GET DELETE", "Create index with CMK encryptionKey + verify + delete"),
    "test_neg_15_create_synonym_map_with_cmk":     ("PUT DELETE",       "Create synonym map with CMK + delete"),
    # ── Phase 3: Authentication ──────────────────────────────────────────
    "test_sec_01_admin_key_read":                  ("GET",              "List indexes (admin key auth)"),
    "test_sec_02_admin_key_write":                 ("PUT DELETE",       "Create + delete index (admin key auth)"),
    "test_sec_03_query_key_search_allowed":        ("POST",             "Search docs (query key auth)"),
    "test_sec_04_query_key_write_rejected":        ("PUT",              "Create index (query key, rejected 403)"),
    "test_sec_05_entra_bearer_read":               ("GET",              "List indexes (Entra auth)"),
    "test_sec_06_entra_bearer_write":              ("PUT DELETE",       "Create + delete index (Entra auth)"),
    "test_sec_07_no_auth_rejected":                ("GET",              "List indexes (no auth, rejected)"),
    "test_sec_08_invalid_api_key":                 ("GET",              "List indexes (invalid API key, rejected)"),
    "test_sec_09_expired_bearer_token":            ("GET",              "List indexes (expired token, rejected)"),
    "test_sec_10_rbac_reader_search":              ("POST",             "Search docs (Entra RBAC)"),
    "test_sec_11_rbac_reader_write_fails":         ("—",               "Write with reader RBAC (skipped)"),
    # ── Phase 4: Index Management ────────────────────────────────────────
    "test_idx_01_create_full_index":               ("PUT PUT",          "Create synonym map + full-featured index"),
    "test_idx_02_get_index":                       ("GET",              "Read index"),
    "test_idx_03_list_indexes":                    ("GET",              "List indexes"),
    "test_idx_04_update_index_add_field":          ("GET PUT GET",      "Update index (add field) + verify"),
    "test_idx_05_index_statistics":                ("GET",              "Read index statistics"),
    "test_idx_06_delete_disposable_index":         ("PUT DELETE GET",   "Create + delete + verify index gone"),
    "test_idx_07_vector_config_roundtrip":         ("GET",              "Read index (verify vector config)"),
    "test_idx_08_semantic_config_roundtrip":       ("GET",              "Read index (verify semantic config)"),
    "test_idx_09_scoring_profile_roundtrip":       ("GET",              "Read index (verify scoring profiles)"),
    "test_idx_10_suggester_roundtrip":             ("GET",              "Read index (verify suggesters)"),
    "test_idx_11_cors_roundtrip":                  ("GET",              "Read index (verify CORS options)"),
    "test_idx_12_custom_analyzers_roundtrip":      ("PUT GET DELETE",   "Create index with custom analyzer + verify + delete"),
    "test_idx_13_simple_index":                    ("PUT",              "Create simple index"),
    "test_idx_14_all_edm_types":                   ("PUT GET DELETE",   "Create index with all EDM types + verify + delete"),
    "test_idx_15_alias_quota_is_zero":             ("GET",              "List aliases (expect empty, quota=0)"),
    "test_idx_16_alias_create_rejected_quota":     ("PUT",              "Create alias (rejected, quota=0)"),
    # ── Phase 5: Document CRUD ───────────────────────────────────────────
    "test_doc_01_upload_batch":                    ("POST",             "Upload 25 documents (batch)"),
    "test_doc_02_lookup_by_key":                    ("GET",              "Lookup document by key"),
    "test_doc_03_document_count":                   ("GET",              "Document count"),
    "test_doc_04_merge_document":                  ("POST",            "Merge document (update single field)"),
    "test_doc_05_merge_or_upload_existing":        ("POST",            "MergeOrUpload existing document"),
    "test_doc_06_merge_or_upload_new":             ("POST",            "MergeOrUpload new document"),
    "test_doc_07_delete_document":                 ("POST GET",        "Delete document + verify 404"),
    "test_doc_08_upload_with_vectors":              ("POST GET",        "Upload document with vector field + verify"),
    "test_doc_09_large_document":                  ("POST",            "Upload large document (~300KB)"),
    "test_doc_10_unicode_characters":              ("POST GET",        "Upload unicode doc (CJK/emoji) + verify"),
    "test_doc_11_batch_1000":                      ("POST",            "Batch upload 1000 documents"),
    "test_doc_12_empty_string_fields":              ("POST",            "Upload doc with empty string fields"),
    # ── Phase 5 (expanded): Document CRUD ────────────────────────────────
    "test_doc_13_merge_multiple_fields":            ("POST GET",        "Merge multiple fields simultaneously"),
    "test_doc_14_merge_nonexistent_doc":            ("POST",            "Merge on non-existent doc — item 404"),
    "test_doc_15_upload_overwrites_existing":       ("POST POST GET",   "Upload overwrites existing doc"),
    "test_doc_16_batch_mixed_actions":              ("POST POST",       "Batch mixed actions (upload+merge+delete)"),
    "test_doc_17_lookup_with_select":               ("GET",             "Lookup with $select restriction"),
    "test_doc_18_lookup_nonexistent_key":           ("GET",             "Lookup non-existent key — 404"),
    "test_doc_19_count_unchanged_after_merge":      ("GET POST GET",    "Count unchanged after merge"),
    "test_doc_20_upload_full_complex_type":         ("POST GET",        "Upload fully populated complex types"),
    "test_doc_21_upload_empty_rooms_collection":    ("POST GET",        "Upload with empty Rooms collection"),
    "test_doc_22_merge_replaces_collection":        ("POST GET",        "Merge replaces entire collection"),
    "test_doc_23_delete_nonexistent_silent_success": ("POST",           "Delete non-existent doc — silent success"),
    "test_doc_24_reupload_deleted_document":        ("POST POST GET",   "Re-upload deleted document"),
    "test_doc_25_batch_partial_failure":            ("POST",            "Batch with 1 invalid — 207 partial"),
    "test_doc_26_merge_preserves_unmentioned_fields": ("POST POST GET", "Merge preserves unmentioned fields"),
    "test_doc_27_upload_special_chars_in_fields":   ("POST GET",        "Upload with special characters"),
    "test_doc_28_upload_with_null_optional_fields": ("POST GET",        "Upload with explicit null fields"),
    "test_doc_29_empty_batch":                      ("POST",            "Empty batch — graceful handling"),
    "test_doc_30_search_after_mutations":           ("POST",            "Search correctness after mutations"),
    # ── Phase 6: Synonym Maps ───────────────────────────────────────────
    "test_syn_01_create_synonym_map":              ("PUT",              "Create synonym map (Solr rules)"),
    "test_syn_02_get_synonym_map":                 ("GET",              "Read synonym map"),
    "test_syn_03_list_synonym_maps":               ("GET",              "List synonym maps"),
    "test_syn_04_update_synonym_map":              ("PUT GET",          "Update synonym map + verify"),
    "test_syn_05_delete_disposable":               ("PUT DELETE GET",   "Create + delete + verify synonym map"),
    "test_syn_06_synonym_query_expansion":         ("POST",             "Search 'inn' expands to 'hotel' via synonyms"),
    # ── Phase 7: Queries ─────────────────────────────────────────────────
    "test_qry_01_simple_keyword":                  ("POST",             "Simple keyword search"),
    "test_qry_02_lucene_boolean":                  ("POST",             "Lucene boolean query (AND)"),
    "test_qry_03_lucene_wildcard":                 ("POST",             "Lucene wildcard query (lux*)"),
    "test_qry_04_lucene_regex":                    ("POST",             "Lucene regex query"),
    "test_qry_05_filter_comparison":               ("POST",             "Filter: Rating ge 4"),
    "test_qry_06_filter_geo_distance":             ("POST",             "Filter: geo.distance <= 10km"),
    "test_qry_07_filter_boolean":                  ("POST",             "Filter: ParkingIncluded eq true"),
    "test_qry_08_filter_string_eq":                ("POST",             "Filter: Category eq 'Boutique'"),
    "test_qry_09_filter_collection_any":           ("POST",             "Filter: Tags/any(t: t eq 'pool')"),
    "test_qry_10_filter_date_range":               ("POST",             "Filter: LastRenovationDate gt 2020"),
    "test_qry_11_filter_complex_type":             ("POST",             "Filter: Address/City eq 'New York'"),
    "test_qry_12_filter_combined":                 ("POST",             "Combined AND/OR filter"),
    "test_qry_13_orderby_desc":                    ("POST",             "OrderBy Rating desc"),
    "test_qry_14_orderby_geo":                     ("POST",             "OrderBy geo.distance asc"),
    "test_qry_15_facets_category":                 ("POST",             "Facets: Category"),
    "test_qry_16_facets_rating_interval":          ("POST",             "Facets: Rating interval:1"),
    "test_qry_17_facets_tags":                     ("POST",             "Facets: Tags collection"),
    "test_qry_18_highlight":                       ("POST",             "Highlight @search.highlights"),
    "test_qry_19_select_restriction":              ("POST",             "Select restricts returned fields"),
    "test_qry_20_top_and_skip":                    ("POST",             "Top + Skip pagination (no overlap)"),
    "test_qry_21_count":                           ("POST",             "$count=true returns @odata.count"),
    "test_qry_22_semantic_search":                 ("POST",             "Semantic search (rerankerScore)"),
    "test_qry_23_semantic_with_answers":           ("POST",             "Semantic search with extractive answers"),
    "test_qry_24_vector_search_pure":              ("POST",             "Pure vector search (pre-computed)"),
    "test_qry_25_vector_text_to_vector":           ("POST",             "Integrated vectorization (kind:text)"),
    "test_qry_26_hybrid_search":                   ("POST",             "Hybrid search (keyword + vector)"),
    "test_qry_27_multi_vector":                    ("POST",             "Multi-vector query (2 vectorQueries)"),
    "test_qry_28_vector_with_filter":              ("POST",             "Vector search with filter"),
    "test_qry_29_suggest":                         ("POST",             "Suggest with partial input"),
    "test_qry_30_autocomplete_one_term":           ("GET",              "Autocomplete oneTermWithContext"),
    "test_qry_31_autocomplete_two_terms":          ("GET",              "Autocomplete twoTerms"),
    "test_qry_32_scoring_profile":                 ("POST",             "Scoring profile boosts higher-rated"),
    "test_qry_33_search_fields":                   ("POST",             "searchFields constrains search"),
    "test_qry_34_minimum_coverage":                ("POST",             "minimumCoverage parameter"),
    "test_qry_35_spell_correction":                ("POST",             "Spell correction (lexicon speller)"),
    "test_qry_36_query_language":                  ("POST",             "queryLanguage parameter"),
    "test_qry_37_search_mode_all":                 ("POST",             "searchMode all vs any"),
    "test_qry_38_empty_wildcard_search":           ("POST",             "Wildcard '*' returns all documents"),
    # ── Phase 8: Misc Operations ─────────────────────────────────────────
    "test_msc_01_service_statistics":              ("GET",              "Service statistics (counters)"),
    "test_msc_02_analyze_standard_lucene":         ("POST",             "Analyze API (standard.lucene)"),
    "test_msc_03_analyze_en_microsoft":            ("POST",             "Analyze API (en.microsoft)"),
    "test_msc_04_bad_api_version":                 ("GET",              "Bad API version (rejected 400)"),
    "test_msc_05_unsupported_api_version":         ("GET",              "Very old API version (rejected)"),
    "test_msc_06_etag_concurrency":                ("GET PUT",          "PUT with stale ETag (rejected 412)"),
    "test_msc_07_if_none_match":                   ("PUT",              "PUT with If-None-Match:* (rejected 412)"),
    "test_msc_08_invalid_json":                    ("POST",             "Malformed JSON body (rejected 400)"),
    "test_msc_09_unknown_field_in_select":         ("POST",             "Select nonexistent field (rejected)"),
    "test_msc_10_serverless_stats_limits":         ("GET",              "Serverless stats limits check"),
    # ── Phase 9: Indexers ────────────────────────────────────────────────
    "test_ixr_01_create_datasource_blob":          ("PUT",              "Create Blob data source"),
    "test_ixr_02_create_datasource_cosmos":        ("PUT",              "Create Cosmos DB data source"),
    "test_ixr_03_create_datasource_sql":           ("PUT",              "Create Azure SQL data source"),
    "test_ixr_04_get_datasource":                  ("GET",              "Read data source (masked creds)"),
    "test_ixr_05_list_datasources":                ("GET",              "List data sources"),
    "test_ixr_06_create_indexer_blob":             ("PUT",              "Create Blob indexer + skillset"),
    "test_ixr_07_run_blob_indexer":                ("POST",             "Run Blob indexer + poll status"),
    "test_ixr_08_verify_vectorized_docs":          ("POST",             "Verify indexed docs have vectors"),
    "test_ixr_09_create_indexer_cosmos":            ("PUT",              "Create Cosmos DB indexer"),
    "test_ixr_10_run_cosmos_indexer":              ("POST",             "Run Cosmos DB indexer + poll"),
    "test_ixr_11_create_indexer_sql":              ("PUT",              "Create Azure SQL indexer"),
    "test_ixr_12_run_sql_indexer":                 ("POST",             "Run Azure SQL indexer + poll"),
    "test_ixr_13_indexer_status":                  ("GET",              "Indexer status (lastResult)"),
    "test_ixr_14_reset_indexer":                   ("POST",             "Reset indexer"),
    "test_ixr_15_scheduled_indexer":               ("GET PUT GET",      "Update indexer schedule + verify"),
    "test_ixr_16_field_mappings_validation":       ("GET",              "Verify field mappings present"),
    "test_ixr_17_output_field_mappings":           ("GET",              "Verify output field mappings"),
    "test_ixr_18_parsing_mode_json_array":         ("PUT DELETE",       "Indexer jsonArray parsing mode"),
    "test_ixr_19_parsing_mode_json_lines":         ("PUT DELETE",       "Indexer jsonLines parsing mode"),
    "test_ixr_20_list_indexers":                   ("GET",              "List indexers"),
    "test_ixr_21_delete_indexer":                  ("DELETE",           "Delete Blob indexer"),
    "test_ixr_22_delete_datasource":               ("DELETE",           "Delete Blob data source"),
    # ── Phase 10: Skillsets ──────────────────────────────────────────────
    "test_skl_01_aoai_embedding_skill":            ("PUT",              "Create skillset (AOAI embedding)"),
    "test_skl_02_text_split_skill":                ("GET PUT",          "Update skillset + SplitSkill"),
    "test_skl_03_entity_recognition_skill":        ("PUT DELETE",       "EntityRecognitionSkill"),
    "test_skl_04_key_phrase_extraction":            ("PUT DELETE",       "KeyPhraseExtractionSkill"),
    "test_skl_05_language_detection":              ("PUT DELETE",       "LanguageDetectionSkill"),
    "test_skl_06_ocr_skill":                       ("PUT DELETE",       "OcrSkill"),
    "test_skl_07_image_analysis_skill":            ("PUT DELETE",       "ImageAnalysisSkill"),
    "test_skl_08_document_layout_skill":           ("PUT DELETE",       "DocumentLayoutSkill"),
    "test_skl_09_shaper_skill":                    ("PUT DELETE",       "ShaperSkill"),
    "test_skl_10_text_merge_skill":                ("PUT DELETE",       "MergeSkill"),
    "test_skl_11_custom_web_api_skill":            ("PUT DELETE",       "WebApiSkill (custom endpoint)"),
    "test_skl_12_multi_skill_pipeline":            ("PUT GET DELETE",   "Multi-skill pipeline (split+embed+entity)"),
    "test_skl_13_e2e_enrichment_run":              ("GET",              "E2E enrichment indexer verification"),
    "test_skl_14_knowledge_store_projection":      ("PUT GET DELETE",   "Knowledge store projections"),
    "test_skl_15_list_skillsets":                  ("GET",              "List skillsets"),
    "test_skl_16_delete_skillset":                 ("DELETE",           "Delete primary skillset"),
    # Phase 11 — Vectorization
    "test_vec_01_hnsw_algorithm":                  ("PUT GET DELETE",   "HNSW algorithm round-trip"),
    "test_vec_02_exhaustive_knn":                  ("PUT GET DELETE",   "ExhaustiveKnn algorithm round-trip"),
    "test_vec_03_aoai_vectorizer":                 ("PUT GET DELETE",   "Azure OpenAI vectorizer round-trip"),
    "test_vec_04_vector_profile_linked":           ("PUT GET DELETE",   "Profile links algorithm + vectorizer"),
    "test_vec_05_chunking_embedding_index":        ("PUT DELETE",       "Chunking + embedding index creation"),
    "test_vec_06_scalar_quantization":             ("PUT GET DELETE",   "Scalar quantization round-trip"),
    "test_vec_07_binary_quantization":             ("PUT GET DELETE",   "Binary quantization round-trip"),
    "test_vec_08_stored_false":                    ("PUT GET DELETE",   "Vector field stored:false round-trip"),
    "test_vec_09_multiple_vector_profiles":        ("PUT GET DELETE",   "Multiple vector profiles on fields"),
    # Phase 11 — E2E Integrated Vectorization
    "test_vec_10_create_vectorizer_index":         ("DELETE PUT GET",   "Create index with AOAI vectorizer"),
    "test_vec_11_upload_1000_documents":           ("POST (×10)",       "Embed + upload 1000 tech articles"),
    "test_vec_12_text_to_vector_query":            ("POST",             "Vector query kind:text (integrated vectorization)"),
    "test_vec_13_hybrid_text_vector_query":        ("POST",             "Hybrid keyword + kind:text vector query"),
    "test_vec_14_filtered_vector_text_query":      ("POST",             "Vector kind:text query with $filter"),
    "test_vec_15_vector_query_select_fields":      ("POST",             "Vector kind:text query with $select"),
    "test_vec_16_vector_query_pagination":         ("POST POST",        "Vector kind:text query with top/skip pagination"),
    "test_vec_17_multi_text_vector_queries":       ("POST",             "Multiple kind:text vectorQueries"),
    "test_vec_18_quantization_with_vectorizer":    ("DELETE PUT POST POST DELETE", "Scalar quantization + AOAI vectorizer query"),
    "test_vec_19_cleanup_e2e_index":               ("DELETE GET",       "Delete E2E vectorization index + verify"),
    # ── Phase 14: Serverless Limits ───────────────────────────────────────
    "test_lim_01_servicestats_index_quota":          ("GET",              "indexesCount quota >= serverless minimum"),
    "test_lim_02_servicestats_indexer_quota":         ("GET",              "indexersCount quota >= serverless minimum"),
    "test_lim_03_servicestats_datasource_quota":      ("GET",              "dataSourcesCount quota >= serverless minimum"),
    "test_lim_04_servicestats_skillset_quota":        ("GET",              "skillsetCount quota >= serverless minimum"),
    "test_lim_05_servicestats_synonym_map_quota":     ("GET",              "synonymMaps quota == 20"),
    "test_lim_06_servicestats_alias_quota_zero":      ("GET",              "aliasesCount quota == 0 (not supported)"),
    "test_lim_07_max_storage_per_index":              ("GET",              "maxStoragePerIndex > 0 in limits section"),
    "test_lim_08_max_fields_per_index":               ("GET",              "maxFieldsPerIndex >= 1000"),
    "test_lim_09_vector_index_size_quota":            ("GET",              "vectorIndexSize quota ~30% of total storage"),
    "test_lim_10_index_stats_structure":              ("DELETE PUT GET DELETE", "Index stats: documentCount, storageSize, vectorIndexSize"),
    "test_lim_11_index_stats_after_docs":             ("GET",              "Index stats reflect docs + storage > 0"),
    "test_lim_12_usage_tracks_resource_count":        ("GET PUT GET DELETE", "indexesCount.usage increments on create"),
    "test_lim_13_list_indexes_throttle":              ("GET (×30)",        "Rapid-fire GET /indexes — observe 429 throttle"),
    "test_lim_14_servicestats_throttle":              ("GET (×30)",        "Rapid-fire GET /servicestats — observe 429 throttle"),
    # ── Phase 12: Agentic Retrieval ──────────────────────────────────────
    "test_agt_01_create_knowledge_source":            ("PUT",              "Create search-index knowledge source"),
    "test_agt_02_get_knowledge_source":               ("GET",              "Read knowledge source"),
    "test_agt_03_list_knowledge_sources":              ("GET",              "List knowledge sources"),
    "test_agt_04_create_knowledge_base":              ("PUT",              "Create knowledge base with LLM"),
    "test_agt_05_get_knowledge_base":                 ("GET",              "Read knowledge base"),
    "test_agt_06_list_knowledge_bases":               ("GET",              "List knowledge bases"),
    "test_agt_07_retrieve_extractive":                ("POST",             "Retrieve extractiveData mode"),
    "test_agt_08_retrieve_answer_synthesis":           ("POST",             "Retrieve answerSynthesis mode"),
    "test_agt_09_retrieve_with_chat_history":          ("POST",             "Retrieve with multi-turn chat history"),
    "test_agt_10_retrieve_reasoning_effort":           ("POST (×4)",        "Retrieve with reasoningEffort levels"),
    "test_agt_11_retrieve_query_rewrites":             ("POST",             "Retrieve — activity query planning"),
    "test_agt_12_mcp_endpoint":                       ("GET",              "MCP endpoint responds"),
    "test_agt_13_delete_knowledge_base":              ("DELETE",           "Delete knowledge base"),
    "test_agt_14_delete_knowledge_source":            ("DELETE",           "Delete knowledge source"),
    # ── Phase 12 (expanded): Agentic Retrieval ──────────────────────────
    "test_agt_15_retrieve_reference_structure":        ("POST",             "Retrieve extractive — reference structure"),
    "test_agt_16_retrieve_empty_query":                ("POST",             "Retrieve with minimal query"),
    "test_agt_17_retrieve_long_query":                 ("POST",             "Retrieve with long complex query"),
    "test_agt_18_retrieve_answer_synthesis_structure":  ("POST",             "Retrieve answerSynthesis — answer validation"),
    "test_agt_19_retrieve_invalid_kb_404":             ("POST",             "Retrieve with non-existent KB — 404"),
    "test_agt_20_retrieve_with_system_message":        ("POST",             "Retrieve with system message"),
    "test_agt_21_retrieve_multiple_turns_extractive":  ("POST",             "Multi-turn extractive follow-up"),
    "test_agt_22_retrieve_no_messages_400":            ("POST",             "Retrieve empty messages — 400"),
    # ── Phase 15: Advanced Filters ───────────────────────────────────────
    "test_flt_01_search_in_comma_delimiter":        ("POST",             "search.in() comma delimiter"),
    "test_flt_02_search_in_pipe_delimiter":         ("POST",             "search.in() pipe delimiter"),
    "test_flt_03_rooms_any_baserate":               ("POST",             "Rooms/any(r: r/BaseRate lt 200)"),
    "test_flt_04_rooms_all_non_smoking":            ("POST",             "Rooms/all(r: not r/SmokingAllowed)"),
    "test_flt_05_double_nested_any":                ("POST",             "Rooms/any(r: r/Tags/any(t: t eq 'suite'))"),
    "test_flt_06_not_rooms_any":                    ("POST",             "not Rooms/any() — empty collection"),
    "test_flt_07_search_in_collection":             ("POST",             "Tags/any(t: search.in(t, ...))"),
    "test_flt_08_ne_operator":                      ("POST",             "Category ne 'Boutique'"),
    "test_flt_09_not_with_precedence":              ("POST",             "not (Rating gt 4) — negation"),
    "test_flt_10_range_filter":                     ("POST",             "Rating ge 2 and Rating le 3"),
    "test_flt_11_not_null_comparison":              ("POST",             "Description_fr ne null"),
    "test_flt_12_geo_distance_validated":           ("POST",             "geo.distance le 5km — NYC only"),
    "test_flt_13_search_ismatch":                   ("POST",             "search.ismatch in filter"),
    "test_flt_14_search_ismatchscoring":            ("POST",             "search.ismatchscoring + Rating filter"),
    "test_flt_15_complex_type_eq":                  ("POST",             "Address/StateProvince eq 'NY'"),
    "test_flt_16_chained_complex_type":             ("POST",             "Address/Country + City ne filter"),
    "test_flt_17_date_range":                       ("POST",             "LastRenovationDate date range"),
    "test_flt_18_boolean_with_count":               ("POST POST POST",   "ParkingIncluded + count cross-check"),
    "test_flt_19_filter_plus_orderby":              ("POST",             "Filter + orderby Rating desc"),
    "test_flt_20_filter_plus_search":               ("POST",             "Keyword search + filter combo"),
    # ── Phase 16: Scoring Profiles ───────────────────────────────────────
    "test_scr_01_profile_changes_scores":           ("POST POST",        "Scoring profile changes scores"),
    "test_scr_02_magnitude_boost_favors_high_rating": ("POST",           "Magnitude boost favors high Rating"),
    "test_scr_03_freshness_boost_effect":           ("POST POST",        "Freshness boost changes ordering"),
    "test_scr_04_profile_plus_filter":              ("POST",             "Profile + filter together"),
    "test_scr_05_profile_plus_orderby":             ("POST",             "orderby overrides profile"),
    "test_scr_06_profile_count_unchanged":          ("POST POST",        "Profile does not change count"),
    "test_scr_07_invalid_profile_returns_400":      ("POST",             "Invalid profile name — 400"),
    "test_scr_08_profile_pagination_consistent":    ("POST POST",        "Profile + pagination no overlap"),
    "test_scr_09_profile_broad_keyword":            ("POST",             "Profile with wildcard '*' search"),
    "test_scr_10_profile_search_mode_all":          ("POST",             "Profile + searchMode all"),
    "test_scr_11_profile_select_restriction":       ("POST",             "Profile + select restriction"),
    "test_scr_12_profile_plus_semantic":            ("POST",             "Profile + semantic reranking"),
    "test_scr_13_tag_scoring_profile":              ("PUT POST POST DELETE", "Tag scoring profile (temp index)"),
    "test_scr_14_text_weights_profile":             ("PUT POST POST POST DELETE", "Text weights profile (temp index)"),
    # ── Phase 17: Semantic Deep-Dive ─────────────────────────────────────
    "test_sem_01_reranker_score_ordering":          ("POST",             "Semantic rerankerScore descending"),
    "test_sem_02_extractive_answers":               ("POST",             "Extractive answers structure"),
    "test_sem_03_extractive_captions":              ("POST",             "Extractive captions on results"),
    "test_sem_04_answers_and_captions_combined":    ("POST",             "Answers + captions together"),
    "test_sem_05_french_semantic_search":           ("POST",             "French semantic search"),
    "test_sem_06_semantic_plus_filter":             ("POST",             "Semantic + filter combo"),
    "test_sem_07_semantic_orderby_override":        ("POST",             "orderby overrides semantic ranking"),
    "test_sem_08_max_text_recall_size":             ("POST POST",        "maxTextRecallSize limits recall"),
    "test_sem_09_speller_correction":               ("POST",             "Speller correction + semantic"),
    "test_sem_10_semantic_with_count":              ("POST",             "Semantic + $count"),
    "test_sem_11_semantic_with_highlight":          ("POST",             "Semantic + highlight + captions"),
    "test_sem_12_semantic_pagination":              ("POST POST",        "Semantic top/skip no overlap"),
    # ── Phase 18: Vector Queries ─────────────────────────────────────────
    "test_vqr_01_kind_text_returns_scored_results": ("POST",             "kind:text vector query — scores present"),
    "test_vqr_02_hybrid_with_sparse_vectors":       ("POST",             "Hybrid with sparse vectors — keyword fallback"),
    "test_vqr_03_vector_filter_correctness":        ("POST",             "Vector + filter correctness"),
    "test_vqr_04_trimodal_hybrid_semantic":         ("POST",             "Tri-modal: keyword + vector + semantic"),
    "test_vqr_05_ai_query_returns_ai_category":     ("POST",             "AI text → AI category dominant"),
    "test_vqr_06_security_query_returns_security_category": ("POST",     "Security text → Security category"),
    "test_vqr_07_different_queries_different_top_result": ("POST POST",  "Different queries → different #1 results"),
    "test_vqr_08_scores_descending":                ("POST",             "Vector scores descending order"),
    "test_vqr_09_exhaustive_knn":                   ("POST",             "Exhaustive KNN search"),
    "test_vqr_10_oversampling":                     ("POST",             "Vector oversampling parameter"),
    "test_vqr_11_vector_weight":                    ("POST POST",        "Vector weight affects hybrid scoring"),
    "test_vqr_12_vector_orderby_override":          ("POST",             "orderby overrides vector ranking"),
    "test_vqr_13_k_vs_top_semantics":               ("POST",             "k=50, top=3 returns exactly 3"),
    "test_vqr_14_vector_with_count":                ("POST",             "Vector + $count"),
    "test_vqr_15_vector_with_facets":               ("POST",             "Vector + category facets"),
    "test_vqr_16_large_k_result_count":             ("POST",             "Large k=500 substantial results"),
    # ── Phase 19: Advanced Queries ───────────────────────────────────────
    "test_adv_01_suggest_fuzzy":                    ("POST",             "Suggest fuzzy — misspelled input"),
    "test_adv_02_suggest_with_filter":              ("POST",             "Suggest with filter"),
    "test_adv_03_suggest_response_structure":       ("POST",             "Suggest @search.text structure"),
    "test_adv_04_suggest_with_select":              ("POST",             "Suggest with $select"),
    "test_adv_05_autocomplete_one_term":            ("GET",              "Autocomplete oneTerm — text + queryPlusText"),
    "test_adv_06_autocomplete_fuzzy":               ("GET",              "Autocomplete fuzzy — misspelled input"),
    "test_adv_07_fuzzy_search":                     ("POST",             "Fuzzy search (~1)"),
    "test_adv_08_proximity_search":                 ("POST",             "Proximity search (\"words\"~5)"),
    "test_adv_09_fielded_search":                   ("POST",             "Fielded search (Description:luxury)"),
    "test_adv_10_boosted_term":                     ("POST POST",        "Boosted term (luxury^5)"),
    "test_adv_11_french_text_search":               ("POST",             "French text search on Description_fr"),
    "test_adv_12_regex_query_validated":            ("POST",             "Regex /[Hh]otel/ validated"),
    # ── Phase 13: Serverless Behavior ────────────────────────────────────
    "test_sls_01_cold_start_latency":                 ("POST",             "Cold start query latency < 30s"),
    "test_sls_02_index_creation_latency":             ("PUT DELETE",       "Index creation latency < 30s"),
    "test_sls_03_indexer_throughput":                  ("GET",              "Blob indexer E2E timing"),
    "test_sls_04_concurrent_queries":                 ("POST (×20)",       "20 parallel search queries — no 5xx"),
    "test_sls_05_concurrent_index_operations":         ("PUT (×5) DELETE (×5)", "5 parallel index creates — no 5xx"),
    "test_sls_06_service_stats_limits":               ("GET",              "Service stats counters present"),
    "test_sls_07_large_result_set":                   ("POST",             "Request top=1000 — 200 or 400"),
    "test_sls_08_rapid_sequential_operations":         ("PUT POST POST DELETE", "Create → upload → search → delete"),
    "test_sls_09_api_version_fallback":               ("GET (×3)",         "Older API versions — 200 or clear error"),
    "test_sls_10_error_message_quality":              ("GET POST",         "Error responses have code + message"),
    "test_sls_11_request_id_tracking":                ("GET POST GET",     "x-ms-request-id in all responses"),
    "test_sls_12_throttling_behavior":                ("POST (×60)",       "429 includes Retry-After header"),
}


@dataclass
class FailureEntry:
    test_id: str
    test_name: str
    description: str
    expected: str
    actual: str
    error_message: str
    # HTTP context (may be None if the failure was not HTTP-related)
    http_request: dict | None = None
    http_response: dict | None = None
    x_ms_request_id: str | None = None
    elapsed_ms: float | None = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "description": self.description,
            "expected": self.expected,
            "actual": self.actual,
            "error_message": self.error_message,
            "http_request": self.http_request,
            "http_response": self.http_response,
            "x_ms_request_id": self.x_ms_request_id,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class TestResult:
    """Lightweight record for every test (pass, fail, or skip)."""
    test_id: str
    description: str
    outcome: str          # "PASS", "FAIL", or "SKIP"
    bug_url: str = ""     # populated if a bug was filed for this failure
    node_id: str = ""     # full pytest node ID (e.g. tests/test_01_service_mgmt.py::Class::method)
    file_stem: str = ""   # test file stem (e.g. test_01_service_mgmt)


class FailureReporter:
    """Singleton collector for test failures.  Instantiated once per session."""

    def __init__(self, results_dir: str | Path = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.failures: list[FailureEntry] = []
        self.total_tests: int = 0
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        # Durable log: all test results from this session
        self.all_results: list[TestResult] = []
        # Map test_id -> bug URL for known bugs
        self.known_bugs: dict[str, str] = {}
        self._run_timestamp = datetime.now(timezone.utc)
        # Persistent store: loaded from test_results.json, merged + saved after run
        self._persistent: dict[str, dict] = self._load_persistent()

    def record_failure(self, entry: FailureEntry) -> None:
        self.failures.append(entry)

    def record_pass(self) -> None:
        self.passed += 1

    def record_skip(self) -> None:
        self.skipped += 1

    def record_result(self, test_id: str, description: str, outcome: str,
                      node_id: str = "") -> None:
        """Record any test outcome for the durable log."""
        bug_url = self.known_bugs.get(test_id, "")
        # Derive file_stem from node_id (e.g. "tests/test_01_service_mgmt.py::..." → "test_01_service_mgmt")
        file_stem = ""
        if node_id and "/" in node_id:
            file_part = node_id.split("::")[0].split("/")[-1]
            file_stem = file_part.replace(".py", "")

        self.all_results.append(TestResult(
            test_id=test_id,
            description=description,
            outcome=outcome,
            bug_url=bug_url,
            node_id=node_id,
            file_stem=file_stem,
        ))

    def register_bug(self, test_id: str, bug_url: str) -> None:
        """Associate a bug URL with a test ID for the durable log."""
        self.known_bugs[test_id] = bug_url

    # ── persistence ──────────────────────────────────────────────────────

    def _load_persistent(self) -> dict[str, dict]:
        """Load the persistent test results store (test_results.json)."""
        path = self.results_dir / "test_results.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_persistent(self) -> None:
        """Merge this session's results into the persistent store and save."""
        ts = self._run_timestamp.strftime("%Y-%m-%d %H:%M UTC")

        for r in self.all_results:
            entry = self._persistent.get(r.test_id, {})
            entry["test_id"] = r.test_id
            entry["description"] = r.description
            entry["result"] = r.outcome
            entry["last_run"] = ts
            entry["node_id"] = r.node_id
            entry["file_stem"] = r.file_stem
            # Determine phase from file_stem
            if r.file_stem and r.file_stem in PHASE_MAP:
                phase_num, phase_title = PHASE_MAP[r.file_stem]
                entry["phase_num"] = phase_num
                entry["phase_title"] = phase_title
                entry["phase"] = f"Phase {phase_num} — {phase_title}"
            # Bug URL: prefer known_bugs (latest), else keep existing
            bug = self.known_bugs.get(r.test_id, "")
            if bug:
                entry["bug_url"] = bug
            elif "bug_url" not in entry:
                entry["bug_url"] = ""
            # Test metadata (HTTP verbs, operation description)
            if r.test_id in TEST_METADATA:
                verbs, op = TEST_METADATA[r.test_id]
                entry["http_verbs"] = verbs
                entry["operation"] = op
            self._persistent[r.test_id] = entry

        # Also apply any known_bugs for tests not run this session
        for test_id, url in self.known_bugs.items():
            if test_id in self._persistent:
                self._persistent[test_id]["bug_url"] = url

        path = self.results_dir / "test_results.json"
        path.write_text(json.dumps(self._persistent, indent=2, default=str),
                        encoding="utf-8")

    # ── output ───────────────────────────────────────────────────────────

    def write_reports(self) -> None:
        """Write all reports to *results_dir*."""
        self._write_json()
        self._write_markdown()
        self._save_persistent()
        self._write_dashboard()

    def _write_json(self) -> None:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": self.total_tests,
                "passed": self.passed,
                "failed": len(self.failures),
                "skipped": self.skipped,
            },
            "failures": [f.to_dict() for f in self.failures],
        }
        path = self.results_dir / "failure_report.json"
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    def _write_markdown(self) -> None:
        lines: list[str] = []
        lines.append("# Serverless Bug Bash — Failure Summary\n")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        lines.append(f"**Total:** {self.total_tests} | **Passed:** {self.passed} | "
                      f"**Failed:** {len(self.failures)} | **Skipped:** {self.skipped}\n")

        if not self.failures:
            lines.append("\nAll tests passed.\n")
        else:
            lines.append("\n| # | Test ID | Status | x-ms-request-id | Error |\n")
            lines.append("|---|---------|--------|-----------------|-------|\n")
            for i, f in enumerate(self.failures, 1):
                req_id = f.x_ms_request_id or "—"
                error = f.error_message[:120].replace("\n", " ").replace("|", "\\|")
                lines.append(f"| {i} | {f.test_id} | {f.actual[:30]} | `{req_id}` | {error} |\n")

            lines.append("\n---\n\n## Detailed Failures\n")
            for i, f in enumerate(self.failures, 1):
                lines.append(f"\n### {i}. {f.test_id} — {f.test_name}\n")
                lines.append(f"- **Expected:** {f.expected}\n")
                lines.append(f"- **Actual:** {f.actual}\n")
                lines.append(f"- **x-ms-request-id:** `{f.x_ms_request_id or '—'}`\n")
                lines.append(f"- **Elapsed:** {f.elapsed_ms:.0f} ms\n" if f.elapsed_ms else "")
                lines.append(f"- **Timestamp:** {f.timestamp}\n")
                if f.http_request:
                    lines.append(f"\n**Request:** `{f.http_request.get('method', '?')} {f.http_request.get('url', '?')}`\n")
                    body = f.http_request.get("body")
                    if body:
                        lines.append(f"```json\n{json.dumps(body, indent=2)[:2000]}\n```\n")
                if f.http_response:
                    lines.append(f"\n**Response ({f.http_response.get('status_code', '?')}):**\n")
                    resp_body = f.http_response.get("body")
                    if resp_body:
                        if isinstance(resp_body, dict):
                            lines.append(f"```json\n{json.dumps(resp_body, indent=2)[:3000]}\n```\n")
                        else:
                            lines.append(f"```\n{str(resp_body)[:3000]}\n```\n")
                lines.append(f"\n**Error:**\n```\n{f.error_message[:3000]}\n```\n")

        path = self.results_dir / "failure_summary.md"
        path.write_text("".join(lines), encoding="utf-8")

    def _write_dashboard(self) -> None:
        """Render *test_log.md* — a consolidated dashboard of all test results.

        One row per test, grouped by phase.  Each row shows the latest result,
        when it was last run, a bug link if any, and a pointer to the failure
        details file for further investigation.
        """
        data = self._persistent
        if not data:
            return

        # Group entries by phase
        by_phase: dict[int, list[dict]] = {}
        for entry in data.values():
            pn = entry.get("phase_num", 99)
            by_phase.setdefault(pn, []).append(entry)

        # Sort entries within each phase by test_id
        for pn in by_phase:
            by_phase[pn].sort(key=lambda e: e.get("test_id", ""))

        # Counts
        total = len(data)
        passed = sum(1 for e in data.values() if e.get("result") == "PASS")
        failed = sum(1 for e in data.values() if e.get("result") == "FAIL")
        skipped = sum(1 for e in data.values() if e.get("result") == "SKIP")

        lines: list[str] = []
        lines.append("# Serverless Bug Bash — Test Results\n\n")
        lines.append(f"**Last updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        lines.append(f"| | Count |\n")
        lines.append(f"|---|---|\n")
        lines.append(f"| **Total tests run** | {total} |\n")
        lines.append(f"| **Passed** | {passed} |\n")
        lines.append(f"| **Failed** | {failed} |\n")
        lines.append(f"| **Skipped** | {skipped} |\n\n")

        for phase_num in sorted(by_phase.keys()):
            entries = by_phase[phase_num]
            phase_label = entries[0].get("phase", f"Phase {phase_num}")
            phase_passed = sum(1 for e in entries if e.get("result") == "PASS")
            phase_failed = sum(1 for e in entries if e.get("result") == "FAIL")
            phase_total = len(entries)

            lines.append(f"## {phase_label} ({phase_passed}/{phase_total} passed)\n\n")
            lines.append("| Test | HTTP | Operation | Result | Last Run | Bug |\n")
            lines.append("|------|------|-----------|--------|----------|-----|\n")

            for e in entries:
                tid = e.get("test_id", "?")
                # Extract short ID from description (e.g. "SVC-01: ..." → "SVC-01")
                desc = e.get("description", "").replace("|", "\\|").strip()
                short_id = desc.split(":")[0].strip() if ":" in desc else tid

                http_verbs = e.get("http_verbs", "")
                if not http_verbs and tid in TEST_METADATA:
                    http_verbs = TEST_METADATA[tid][0]
                verb_cell = f"`{http_verbs}`" if http_verbs else "—"

                operation = e.get("operation", "")
                if not operation and tid in TEST_METADATA:
                    operation = TEST_METADATA[tid][1]
                if not operation:
                    # Fall back to scenario from description
                    operation = desc.split(":", 1)[1].strip() if ":" in desc else desc
                if len(operation) > 60:
                    operation = operation[:57] + "..."

                result = e.get("result", "?")
                result_cell = {"PASS": "PASS", "FAIL": "**FAIL**", "SKIP": "SKIP"}.get(result, result)

                last_run = e.get("last_run", "—")

                bug_url = e.get("bug_url", "")
                bug_cell = f"[Bug]({bug_url})" if bug_url else "—"

                lines.append(f"| {short_id} | {verb_cell} | {operation} | {result_cell} | {last_run} | {bug_cell} |\n")

            lines.append("\n")

        path = self.results_dir / "test_log.md"
        path.write_text("".join(lines), encoding="utf-8")
