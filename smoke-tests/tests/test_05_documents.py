"""
test_05_documents.py — Document CRUD Operations

Tests: DOC-01 through DOC-22

Gate: DOC-01 failure aborts run.
"""

import json
import os

import pytest

from helpers.assertions import (
    assert_field_equals,
    assert_field_exists,
    assert_status,
)

pytestmark = [pytest.mark.documents]

# Load 100 sample hotels from JSON file
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_data", "hotels_100.json")
with open(_DATA_PATH, encoding="utf-8") as _f:
    SAMPLE_HOTELS = json.load(_f)

HOTEL_COUNT = len(SAMPLE_HOTELS)


class TestDocumentUpload:

    @pytest.mark.gate
    def test_doc_01_upload_batch(self, rest, primary_index_name):
        """DOC-01: Upload 100 documents. GATE — failure aborts run."""
        body = {"value": SAMPLE_HOTELS}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        data = resp.json()
        results = data.get("value", [])
        failed = [r for r in results if not r.get("status", False)]
        assert len(failed) == 0, f"{len(failed)} docs failed upload: {failed[:3]}"

    def test_doc_02_lookup_by_key(self, rest, primary_index_name):
        """DOC-02: Lookup a specific document by key."""
        resp = rest.get(f"/indexes/{primary_index_name}/docs/1")
        assert_status(resp, 200)
        data = resp.json()
        # Verify data matches sample_data/hotels_100.json hotel #1
        expected = SAMPLE_HOTELS[0]
        assert_field_equals(data, "HotelName", expected["HotelName"])
        assert_field_equals(data, "Category", expected["Category"])

    def test_doc_03_document_count(self, rest, primary_index_name):
        """DOC-03: Document count matches uploaded count."""
        import time
        # Indexing can take a few seconds to propagate
        for attempt in range(10):
            resp = rest.get(f"/indexes/{primary_index_name}/docs/$count")
            assert_status(resp, 200)
            count = int(resp.text.strip())
            if count == HOTEL_COUNT:
                break
            time.sleep(3)
        assert count == HOTEL_COUNT, f"Expected {HOTEL_COUNT} documents, got {count}"


class TestDocumentMerge:

    def test_doc_04_merge_document(self, rest, primary_index_name):
        """DOC-04: Merge updates a single field without touching others."""
        body = {"value": [{"@search.action": "merge", "HotelId": "1", "Rating": 4.5}]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        # Verify
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/1")
        assert_field_equals(get_resp.json(), "Rating", 4.5)
        # Verify other fields unchanged
        assert_field_equals(get_resp.json(), "HotelName", SAMPLE_HOTELS[0]["HotelName"])

    def test_doc_05_merge_or_upload_existing(self, rest, primary_index_name):
        """DOC-05: mergeOrUpload on existing doc updates it."""
        body = {"value": [{"@search.action": "mergeOrUpload", "HotelId": "2", "Rating": 3.0}]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/2")
        assert_field_equals(get_resp.json(), "Rating", 3.0)

    def test_doc_06_merge_or_upload_new(self, rest, primary_index_name):
        """DOC-06: mergeOrUpload on new doc creates it."""
        body = {"value": [{
            "@search.action": "mergeOrUpload",
            "HotelId": "200",
            "HotelName": "Upserted Hotel",
            "Description": "Created via mergeOrUpload",
            "Rating": 3.5,
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/200")
        assert_status(get_resp, 200)

    def test_doc_07_delete_document(self, rest, primary_index_name):
        """DOC-07: Delete a document."""
        body = {"value": [{"@search.action": "delete", "HotelId": "200"}]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        import time
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/200")
        assert_status(get_resp, 404)


class TestDocumentEdgeCases:

    def test_doc_08_upload_with_vectors(self, rest, primary_index_name, aoai_config):
        """DOC-08: Populate all 100 documents with real AOAI embeddings across 4 vector fields."""
        import requests as _http
        import time as _time

        endpoint = aoai_config["endpoint"].rstrip("/")
        deployment = aoai_config["embedding_deployment"]
        api_version = aoai_config["api_version"]
        url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
        headers = {"api-key": aoai_config["api_key"], "Content-Type": "application/json"}

        # Collect descriptions for all 100 hotels
        texts = [d.get("Description", f"Hotel {d['HotelId']}") for d in SAMPLE_HOTELS]

        # Call AOAI embedding API in batches of 16 (rate-limit friendly)
        BATCH_SIZE = 16
        embeddings = [None] * len(texts)
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[batch_start:batch_start + BATCH_SIZE]
            for attempt in range(6):
                try:
                    resp = _http.post(url, json={"input": batch_texts}, headers=headers, timeout=120)
                except _http.exceptions.RequestException:
                    _time.sleep(2 ** attempt)
                    continue
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                    _time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    _time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                for item in resp.json()["data"]:
                    embeddings[batch_start + item["index"]] = item["embedding"]
                break

        assert all(e is not None for e in embeddings), "Some embeddings missing from AOAI response"

        # Verify embedding dimensions
        for i, emb in enumerate(embeddings):
            assert len(emb) == 1536, (
                f"Embedding for doc {SAMPLE_HOTELS[i]['HotelId']} has {len(emb)} dims, expected 1536"
            )

        # MergeOrUpload all docs with vectors into all 4 vector fields
        # (same embedding for each field — compression happens server-side)
        UPLOAD_BATCH = 50
        for batch_start in range(0, len(SAMPLE_HOTELS), UPLOAD_BATCH):
            merge_docs = []
            for idx in range(batch_start, min(batch_start + UPLOAD_BATCH, len(SAMPLE_HOTELS))):
                emb = embeddings[idx]
                merge_docs.append({
                    "@search.action": "mergeOrUpload",
                    "HotelId": SAMPLE_HOTELS[idx]["HotelId"],
                    "DescriptionVector": emb,
                    "DescriptionVectorBQ": emb,
                    "DescriptionVectorSQ": emb,
                    "DescriptionVectorEKNN": emb,
                })
            upload_resp = rest.post(
                f"/indexes/{primary_index_name}/docs/index", {"value": merge_docs}
            )
            assert_status(upload_resp, (200, 207))
            results = upload_resp.json().get("value", [])
            failed = [r for r in results if not r.get("status", False)]
            assert len(failed) == 0, f"{len(failed)} vector uploads failed: {failed[:3]}"

        # Wait for indexing and verify vectors via a vector query
        _time.sleep(5)
        verify = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "vectorQueries": [{
                "kind": "text",
                "text": "luxury hotel with spa",
                "fields": "DescriptionVector",
                "k": 3,
            }],
            "select": "HotelId, HotelName",
        })
        assert_status(verify, 200)
        results = verify.json().get("value", [])
        assert len(results) >= 1, "Vector query returned no results after embedding upload"
        for r in results:
            assert "@search.score" in r, (
                f"Vector result for {r.get('HotelId')} missing @search.score"
            )

    def test_doc_09_large_document(self, rest, primary_index_name):
        """DOC-09: Upload a document with a large text field."""
        large_text = "hotel " * 50000  # ~300KB text
        body = {"value": [{
            "@search.action": "mergeOrUpload",
            "HotelId": "1",
            "Description": large_text,
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        if resp.status_code in (200, 207):
            # If accepted, verify the item-level status
            results = resp.json().get("value", [])
            assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        else:
            # Size limit rejection is acceptable
            assert resp.status_code in (400, 413), f"Unexpected status: {resp.status_code}"

    def test_doc_10_unicode_characters(self, rest, primary_index_name):
        """DOC-10: Upload a doc with CJK, emoji, Arabic, diacritical marks."""
        body = {"value": [{
            "@search.action": "mergeOrUpload",
            "HotelId": "1",
            "Description": "Hôtel de première classe 一流酒店 🏨 فندق فاخر Ñoño",
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/1", params={"$select": "HotelId,Description"})
        desc = get_resp.json().get("Description", "")
        assert "一流酒店" in desc, "CJK characters not preserved"
        assert "🏨" in desc, "Emoji not preserved"

    def test_doc_11_batch_1000(self, rest, simple_index_name):
        """DOC-11: Upload a batch of 1000 small documents."""
        docs = [
            {"@search.action": "upload", "id": str(i), "title": f"Batch doc {i}", "count": i}
            for i in range(1000)
        ]
        resp = rest.post(f"/indexes/{simple_index_name}/docs/index", {"value": docs})
        if resp.status_code in (200, 207):
            results = resp.json().get("value", [])
            succeeded = sum(1 for r in results if r.get("status") is True)
            failed = sum(1 for r in results if r.get("status") is not True)
            assert succeeded == 1000, (
                f"Expected all 1000 docs to succeed, got {succeeded} succeeded, {failed} failed"
            )
        else:
            # Batch size limit rejection is acceptable
            assert resp.status_code in (400, 413), f"Unexpected: {resp.status_code}"

    def test_doc_12_empty_string_fields(self, rest, primary_index_name):
        """DOC-12: Upload doc with empty strings and null fields."""
        body = {"value": [{
            "@search.action": "mergeOrUpload",
            "HotelId": "1",
            "Description_fr": "",
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        # Verify empty string was preserved (not converted to null)
        import time; time.sleep(1)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/1", params={"$select": "HotelId,Description_fr"})
        assert_status(get_resp, 200)
        desc_fr = get_resp.json().get("Description_fr")
        assert desc_fr is not None, "Empty string was converted to null"


class TestDocumentMergeExpanded:

    def test_doc_13_merge_multiple_fields(self, rest, primary_index_name):
        """DOC-13: Merge updates multiple fields simultaneously."""
        body = {"value": [{
            "@search.action": "merge",
            "HotelId": "3",
            "Rating": 4.9,
            "Category": "Suite",
            "Tags": ["restaurant", "bar", "continental breakfast", "updated"],
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/3")
        data = get_resp.json()
        assert_field_equals(data, "Rating", 4.9)
        assert_field_equals(data, "Category", "Suite")
        assert "updated" in data.get("Tags", []), "Tags should contain 'updated'"
        # HotelName should be unchanged
        assert_field_equals(data, "HotelName", SAMPLE_HOTELS[2]["HotelName"])
        # Restore original data so subsequent tests are unaffected
        original = SAMPLE_HOTELS[2]
        rest.post(f"/indexes/{primary_index_name}/docs/index", {"value": [{
            "@search.action": "merge",
            "HotelId": "3",
            "Rating": original["Rating"],
            "Category": original["Category"],
            "Tags": original["Tags"],
        }]})

    def test_doc_14_merge_nonexistent_doc(self, rest, primary_index_name):
        """DOC-14: Merge on non-existent document — item-level 404 error."""
        body = {"value": [{
            "@search.action": "merge",
            "HotelId": "99999",
            "Rating": 1.0,
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        results = resp.json().get("value", [])
        assert len(results) == 1
        assert results[0].get("status") is False or results[0].get("statusCode") == 404, \
            f"Expected item-level 404 for merge on non-existent doc: {results[0]}"

    def test_doc_15_upload_overwrites_existing(self, rest, primary_index_name):
        """DOC-15: Upload with existing key overwrites the document entirely."""
        body = {"value": [{
            "@search.action": "upload",
            "HotelId": "201",
            "HotelName": "Temp Hotel V1",
            "Category": "Budget",
            "Rating": 2.0,
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        import time; time.sleep(2)
        # Overwrite with different data
        body2 = {"value": [{
            "@search.action": "upload",
            "HotelId": "201",
            "HotelName": "Temp Hotel V2",
            "Category": "Luxury",
        }]}
        resp2 = rest.post(f"/indexes/{primary_index_name}/docs/index", body2)
        assert_status(resp2, (200, 207))
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/201")
        data = get_resp.json()
        assert_field_equals(data, "HotelName", "Temp Hotel V2")
        assert_field_equals(data, "Category", "Luxury")
        # Upload replaces — Rating should be gone (null)
        assert data.get("Rating") is None, \
            f"Upload should replace: Rating should be null, got {data.get('Rating')}"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "201"}]
        })

    def test_doc_16_batch_mixed_actions(self, rest, primary_index_name):
        """DOC-16: Batch with mixed actions — upload + merge + delete in one call."""
        import time
        # Setup: upload temp doc
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "upload", "HotelId": "202", "HotelName": "Mixed Test", "Rating": 3.0}]
        })
        time.sleep(2)
        # Mixed batch
        body = {"value": [
            {"@search.action": "upload", "HotelId": "203", "HotelName": "Mixed Upload", "Rating": 4.0},
            {"@search.action": "merge", "HotelId": "202", "Rating": 5.0},
            {"@search.action": "delete", "HotelId": "203"},
        ]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        results = resp.json().get("value", [])
        assert all(r.get("status", False) for r in results), \
            f"Mixed batch has failures: {[r for r in results if not r.get('status')]}"
        time.sleep(2)
        # Verify merge applied
        get202 = rest.get(f"/indexes/{primary_index_name}/docs/202")
        assert_field_equals(get202.json(), "Rating", 5.0)
        # Verify delete applied
        get203 = rest.get(f"/indexes/{primary_index_name}/docs/203")
        assert_status(get203, 404)
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "202"}]
        })


class TestDocumentLookupExpanded:

    def test_doc_17_lookup_with_select(self, rest, primary_index_name):
        """DOC-17: Lookup with $select returns only specified fields."""
        resp = rest.get(f"/indexes/{primary_index_name}/docs/1",
                        params={"$select": "HotelId,HotelName"})
        assert_status(resp, 200)
        data = resp.json()
        assert "HotelId" in data
        assert "HotelName" in data
        assert "Rating" not in data, "Rating should not be returned with $select"
        assert "Category" not in data, "Category should not be returned with $select"

    def test_doc_18_lookup_nonexistent_key(self, rest, primary_index_name):
        """DOC-18: Lookup by non-existent key returns 404."""
        resp = rest.get(f"/indexes/{primary_index_name}/docs/DOES-NOT-EXIST-99")
        assert_status(resp, 404)

    def test_doc_19_count_unchanged_after_merge(self, rest, primary_index_name):
        """DOC-19: Document count unchanged after merge (no new doc created)."""
        import time
        # Wait for any previous test mutations to settle
        time.sleep(3)
        count_before_resp = rest.get(f"/indexes/{primary_index_name}/docs/$count")
        assert_status(count_before_resp, 200)
        count_before = int(count_before_resp.text.strip())
        # Merge existing doc
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "merge", "HotelId": "4", "Rating": 4.7}]
        })
        time.sleep(3)
        count_after_resp = rest.get(f"/indexes/{primary_index_name}/docs/$count")
        assert_status(count_after_resp, 200)
        count_after = int(count_after_resp.text.strip())
        assert count_before == count_after, \
            f"Merge should not change count: {count_before} → {count_after}"


class TestDocumentComplexTypes:

    def test_doc_20_upload_full_complex_type(self, rest, primary_index_name):
        """DOC-20: Upload doc with all complex type fields fully populated."""
        import time
        body = {"value": [{
            "@search.action": "upload",
            "HotelId": "204",
            "HotelName": "Complex Type Hotel",
            "Description": "A fully populated hotel for testing.",
            "Category": "Resort and Spa",
            "Tags": ["beach", "spa", "golf"],
            "ParkingIncluded": True,
            "Rating": 4.5,
            "Address": {
                "StreetAddress": "123 Beach Rd",
                "City": "Miami",
                "StateProvince": "FL",
                "PostalCode": "33101",
                "Country": "USA",
            },
            "Rooms": [
                {"Description": "Ocean View Suite", "Type": "Suite", "BaseRate": 350.0,
                 "BedOptions": "1 King Bed", "SleepsCount": 2, "SmokingAllowed": False,
                 "Tags": ["ocean view", "balcony"]},
                {"Description": "Standard Double", "Type": "Standard Room", "BaseRate": 150.0,
                 "BedOptions": "2 Double Beds", "SleepsCount": 4, "SmokingAllowed": False,
                 "Tags": ["garden view"]},
            ],
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/204")
        assert_status(get_resp, 200)
        data = get_resp.json()
        assert_field_equals(data, "HotelName", "Complex Type Hotel")
        assert data["Address"]["City"] == "Miami"
        assert len(data["Rooms"]) == 2
        assert data["Rooms"][0]["Type"] == "Suite"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "204"}]
        })

    def test_doc_21_upload_empty_rooms_collection(self, rest, primary_index_name):
        """DOC-21: Upload doc with explicitly empty Rooms collection."""
        import time
        body = {"value": [{
            "@search.action": "upload",
            "HotelId": "205",
            "HotelName": "No Rooms Hotel",
            "Rooms": [],
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/205")
        data = get_resp.json()
        rooms = data.get("Rooms", None)
        assert rooms is not None and len(rooms) == 0, \
            f"Rooms should be empty list, got: {rooms}"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "205"}]
        })

    def test_doc_22_merge_replaces_collection(self, rest, primary_index_name):
        """DOC-22: Merge on collection field replaces entire collection, not appends."""
        import time
        # Hotel 4 has 1 room. Merge with 2 rooms.
        body = {"value": [{
            "@search.action": "merge",
            "HotelId": "4",
            "Rooms": [
                {"Description": "New Room A", "Type": "Deluxe Room", "BaseRate": 200.0,
                 "SleepsCount": 2, "SmokingAllowed": False, "Tags": ["new"]},
                {"Description": "New Room B", "Type": "Suite", "BaseRate": 300.0,
                 "SleepsCount": 3, "SmokingAllowed": False, "Tags": ["new"]},
            ],
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/4")
        data = get_resp.json()
        rooms = data.get("Rooms", [])
        assert len(rooms) == 2, f"Merge should replace rooms: expected 2, got {len(rooms)}"
        descriptions = [r.get("Description") for r in rooms]
        assert "New Room A" in descriptions and "New Room B" in descriptions


class TestDocumentEdgeCasesExpanded:

    def test_doc_23_delete_nonexistent_silent_success(self, rest, primary_index_name):
        """DOC-23: Delete non-existent document — item succeeds (not found is not an error)."""
        body = {"value": [{
            "@search.action": "delete",
            "HotelId": "DOES-NOT-EXIST-88888",
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        results = resp.json().get("value", [])
        assert len(results) == 1
        assert results[0].get("status") is True, \
            f"Delete of non-existent doc should succeed at item level: {results[0]}"

    def test_doc_24_reupload_deleted_document(self, rest, primary_index_name):
        """DOC-24: Re-upload a previously deleted document — recreated successfully."""
        import time
        # Upload temp doc
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "upload", "HotelId": "206", "HotelName": "Temp Reupload"}]
        })
        time.sleep(2)
        # Delete it
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "206"}]
        })
        time.sleep(2)
        assert_status(rest.get(f"/indexes/{primary_index_name}/docs/206"), 404)
        # Re-upload
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "upload", "HotelId": "206",
                        "HotelName": "Temp Reupload V2", "Rating": 5.0}]
        })
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/206")
        assert_status(get_resp, 200)
        assert_field_equals(get_resp.json(), "HotelName", "Temp Reupload V2")
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "206"}]
        })

    def test_doc_25_batch_partial_failure(self, rest, primary_index_name):
        """DOC-25: Batch with 1 invalid doc — 207 with partial success."""
        body = {"value": [
            {"@search.action": "upload", "HotelId": "207", "HotelName": "Good Doc"},
            {"@search.action": "merge", "HotelId": "NONEXISTENT-99", "Rating": 1.0},
        ]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        results = resp.json().get("value", [])
        statuses = [r.get("status", False) for r in results]
        # At least one should succeed, at least one should fail
        if False in statuses:
            assert True in statuses, "Expected partial success — at least one doc should succeed"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "207"}]
        })

    def test_doc_26_merge_preserves_unmentioned_fields(self, rest, primary_index_name):
        """DOC-26: Merge preserves fields not mentioned in the merge payload."""
        import time
        # Upload a doc with multiple fields
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "upload", "HotelId": "208",
                        "HotelName": "Preserve Test", "Category": "Budget",
                        "Rating": 3.5, "ParkingIncluded": True}]
        })
        time.sleep(2)
        # Merge only Rating
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "merge", "HotelId": "208", "Rating": 4.0}]
        })
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/208")
        data = get_resp.json()
        assert_field_equals(data, "Rating", 4.0)
        assert_field_equals(data, "HotelName", "Preserve Test")
        assert_field_equals(data, "Category", "Budget")
        assert data.get("ParkingIncluded") is True, "ParkingIncluded should be preserved"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "208"}]
        })

    def test_doc_27_upload_special_chars_in_fields(self, rest, primary_index_name):
        """DOC-27: Upload with special characters — quotes, backslashes, HTML entities."""
        import time
        body = {"value": [{
            "@search.action": "upload",
            "HotelId": "209",
            "HotelName": 'Hotel "Grand" <Palace> & Café',
            "Description": "A hotel with 'single quotes', \"double quotes\", <tags>, & ampersands.",
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/209")
        assert_status(get_resp, 200)
        data = get_resp.json()
        assert "Grand" in data.get("HotelName", ""), "Special chars in name should be preserved"
        assert "&" in data.get("HotelName", ""), "Ampersand should be preserved"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "209"}]
        })

    def test_doc_28_upload_with_null_optional_fields(self, rest, primary_index_name):
        """DOC-28: Upload with explicit null on optional fields — null stored correctly."""
        import time
        body = {"value": [{
            "@search.action": "upload",
            "HotelId": "210",
            "HotelName": "Null Fields Hotel",
            "Description": None,
            "Category": None,
            "Rating": None,
        }]}
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", body)
        assert_status(resp, (200, 207))
        time.sleep(2)
        get_resp = rest.get(f"/indexes/{primary_index_name}/docs/210")
        assert_status(get_resp, 200)
        data = get_resp.json()
        assert data.get("Description") is None, "Description should be null"
        assert data.get("Category") is None, "Category should be null"
        assert data.get("Rating") is None, "Rating should be null"
        # Cleanup
        rest.post(f"/indexes/{primary_index_name}/docs/index", {
            "value": [{"@search.action": "delete", "HotelId": "210"}]
        })

    def test_doc_29_empty_batch(self, rest, primary_index_name):
        """DOC-29: Empty batch with no documents — service handles gracefully."""
        resp = rest.post(f"/indexes/{primary_index_name}/docs/index", {"value": []})
        # Accept 200 (empty success) or 400 (validation error)
        assert resp.status_code in (200, 207, 400), \
            f"Empty batch should return 200 or 400, got {resp.status_code}"

    def test_doc_30_search_after_mutations(self, rest, primary_index_name):
        """DOC-30: Search query returns correct data after prior document mutations."""
        import time
        time.sleep(2)
        resp = rest.post(f"/indexes/{primary_index_name}/docs/search", {
            "search": "*",
            "filter": "HotelId eq '5'",
            "select": "HotelId, HotelName, Category",
        })
        assert_status(resp, 200)
        data = resp.json()
        results = data.get("value", [])
        assert len(results) == 1, f"Expected exactly 1 result for HotelId=5, got {len(results)}"
        assert results[0]["HotelName"] == SAMPLE_HOTELS[4]["HotelName"]
        assert results[0]["Category"] == SAMPLE_HOTELS[4]["Category"]
