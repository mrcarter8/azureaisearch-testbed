"""
Custom Web API Skill — Text Analyzer

Azure AI Search calls this function as a WebApiSkill during enrichment.
It receives batches of records and returns enriched fields for each:

  - word_count: integer count of words
  - keywords: top 5 most frequent meaningful words (>3 chars)
  - has_amenity_mentions: boolean — whether text mentions common hotel amenities

Input contract (from Azure AI Search):
    { "values": [ { "recordId": "1", "data": { "text": "..." } }, ... ] }

Output contract (back to Azure AI Search):
    { "values": [ { "recordId": "1", "data": { "word_count": 42,
        "keywords": ["hotel", "pool", ...], "has_amenity_mentions": true },
        "errors": [], "warnings": [] }, ... ] }
"""

import json
import logging
import re
from collections import Counter

import azure.functions as func

app = func.FunctionApp()

# Common hotel amenities for detection
AMENITIES = {
    "pool", "spa", "wifi", "parking", "gym", "restaurant", "bar",
    "breakfast", "concierge", "laundry", "shuttle", "fitness",
    "sauna", "jacuzzi", "minibar", "balcony", "terrace", "garden",
}

STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "has",
    "was", "were", "are", "been", "being", "will", "would", "could",
    "should", "may", "might", "can", "shall", "its", "our", "their",
    "your", "not", "but", "also", "all", "into", "over", "more",
    "most", "very", "just", "than", "then", "when", "what", "which",
}


def _analyze_text(text: str) -> dict:
    """Analyze a text string and return enrichment fields."""
    if not text:
        return {"word_count": 0, "keywords": [], "has_amenity_mentions": False}

    words = re.findall(r"[a-zA-Z]+", text.lower())
    word_count = len(words)

    # Filter to meaningful words (>3 chars, not stop words)
    meaningful = [w for w in words if len(w) > 3 and w not in STOP_WORDS]
    top_keywords = [w for w, _ in Counter(meaningful).most_common(5)]

    # Check for amenity mentions
    word_set = set(words)
    has_amenity = bool(word_set & AMENITIES)

    return {
        "word_count": word_count,
        "keywords": top_keywords,
        "has_amenity_mentions": has_amenity,
    }


@app.function_name(name="analyze")
@app.route(route="analyze", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def analyze(req: func.HttpRequest) -> func.HttpResponse:
    """Process a batch of records from Azure AI Search."""
    logging.info("Custom skill invoked")

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"values": [], "errors": ["Invalid JSON body"]}),
            status_code=400,
            mimetype="application/json",
        )

    values = body.get("values", [])
    results = []

    for record in values:
        record_id = record.get("recordId", "")
        data = record.get("data", {})
        text = data.get("text", "")

        try:
            enriched = _analyze_text(text)
            results.append({
                "recordId": record_id,
                "data": enriched,
                "errors": [],
                "warnings": [],
            })
        except Exception as exc:
            results.append({
                "recordId": record_id,
                "data": {},
                "errors": [{"message": str(exc)}],
                "warnings": [],
            })

    return func.HttpResponse(
        json.dumps({"values": results}),
        status_code=200,
        mimetype="application/json",
    )
