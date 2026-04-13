import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent / "data"


def _load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_properties() -> list[dict[str, Any]]:
    return _load_json("properties.json")


@lru_cache(maxsize=1)
def load_realtors() -> list[dict[str, Any]]:
    return _load_json("realtors.json")


@lru_cache(maxsize=1)
def load_knowledge() -> list[dict[str, Any]]:
    return _load_json("knowledge.json")


def get_doorviser_contact() -> dict[str, str]:
    number = os.getenv("DOORVISER_CONTACT_NUMBER", "+1-888-DOORVISER")
    return {
        "fixed_contact_number": number,
        "message": "Doorviser can take over once you are ready for deeper assistance, touring, or strategy.",
    }


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _known_cities() -> set[str]:
    return {property_row["city"] for property_row in load_properties()}


def property_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for row in rows:
        cards.append(
            {
                "id": row["id"],
                "title": row["title"],
                "city": row["city"],
                "state": row["state"],
                "price": row["nightly_rate"] if row["listing_type"] == "short_stay" else row["price"],
                "listing_type": row["listing_type"],
                "property_type": row["property_type"],
                "bedrooms": row["bedrooms"],
                "bathrooms": row["bathrooms"],
                "short_description": row["short_description"],
                "image_url": row.get("image_url"),
            }
        )
    return cards


def search_properties(
    *,
    city: str | None = None,
    max_price: int | None = None,
    min_price: int | None = None,
    bedrooms: float | None = None,
    bathrooms: float | None = None,
    property_type: str | None = None,
    status: str | None = "active",
    listing_type: str | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in load_properties():
        comparable_price = item["nightly_rate"] if item["listing_type"] == "short_stay" else item["price"]
        if city and _normalize(item["city"]) != _normalize(city):
            continue
        if property_type and _normalize(item["property_type"]) != _normalize(property_type):
            continue
        if listing_type and _normalize(item["listing_type"]) != _normalize(listing_type):
            continue
        if status and _normalize(item["status"]) != _normalize(status):
            continue
        if max_price is not None and comparable_price > max_price:
            continue
        if min_price is not None and comparable_price < min_price:
            continue
        if bedrooms is not None and item["bedrooms"] < bedrooms:
            continue
        if bathrooms is not None and item["bathrooms"] < bathrooms:
            continue
        results.append(item)
    return results[:limit]


def get_property_details(property_id: str) -> dict[str, Any] | None:
    return next((item for item in load_properties() if item["id"] == property_id), None)


def search_market_knowledge(query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    tokens = {token for token in re.findall(r"[a-zA-Z]{3,}", query.lower())}
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in load_knowledge():
        doc_tokens = set(doc["topics"]) | set(re.findall(r"[a-zA-Z]{3,}", doc["content"].lower()))
        score = len(tokens & doc_tokens)
        if topic and topic in doc["topics"]:
            score += 3
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [doc for _, doc in scored[:limit]]


def recommend_realtor(city: str | None = None, property_id: str | None = None) -> tuple[dict[str, Any], str]:
    if property_id:
        property_row = get_property_details(property_id)
        if property_row:
            realtor = next((row for row in load_realtors() if row["id"] == property_row["realtor_id"]), None)
            if realtor:
                return realtor, "Matched by property listing specialist"
    if city:
        realtor = next((row for row in load_realtors() if city in row["cities_covered"]), None)
        if realtor:
            return realtor, f"Matched by city coverage in {city}"
    return load_realtors()[0], "Default Doorviser fallback realtor"


PROPERTY_TYPE_ALIASES = {
    "condo": "condo",
    "apartment": "apartment",
    "house": "house",
    "townhome": "townhome",
    "loft": "loft",
    "suite": "suite",
}

LISTING_TYPE_HINTS = {
    "buy": "sale",
    "sale": "sale",
    "home": "sale",
    "rent": "lease",
    "lease": "lease",
    "short stay": "short_stay",
    "vacation": "short_stay",
    "travel": "short_stay",
    "stay": "short_stay",
}


def interpret_query(message: str) -> dict[str, Any]:
    lower = message.lower()
    city = next((known for known in _known_cities() if known.lower() in lower), None)
    beds_match = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(?:bed|bedroom|bd)", lower)
    baths_match = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(?:bath|bathroom|ba)", lower)
    max_budget_match = re.search(r"(?:under|below|max(?:imum)?|up to)\s*\$?(\d[\d,]*)", lower)
    min_budget_match = re.search(r"(?:over|above|min(?:imum)?|from)\s*\$?(\d[\d,]*)", lower)
    property_id_match = re.search(r"(prop-\d{3})", lower)
    property_type = next((value for hint, value in PROPERTY_TYPE_ALIASES.items() if hint in lower), None)
    listing_type = next((value for hint, value in LISTING_TYPE_HINTS.items() if hint in lower), None)
    needs_handoff = any(term in lower for term in ["contact", "connect", "call", "speak to", "human", "realtor", "agent"])
    intent = "general_real_estate_qna"
    topic = None

    if property_id_match or "tell me about" in lower or "details" in lower:
        intent = "property_detail"
    elif any(term in lower for term in ["find", "show", "looking for", "search", "available"]):
        intent = "property_search"
    elif "sell" in lower or "list my" in lower:
        intent = "selling_guidance"
        topic = "sell"
    elif any(term in lower for term in ["rent", "lease", "apartment"]):
        intent = "renting_guidance" if intent == "general_real_estate_qna" else intent
        topic = "rent"
    elif any(term in lower for term in ["buy", "offer", "mortgage", "inspection"]):
        intent = "buying_guidance"
        topic = "buy"
    elif any(term in lower for term in ["area", "neighborhood", "school", "commute"]):
        intent = "area_question"
        topic = "neighborhood"

    if needs_handoff and intent == "general_real_estate_qna":
        intent = "contact_request"

    return {
        "intent": intent,
        "city": city,
        "max_price": int(max_budget_match.group(1).replace(",", "")) if max_budget_match else None,
        "min_price": int(min_budget_match.group(1).replace(",", "")) if min_budget_match else None,
        "bedrooms": float(beds_match.group(1)) if beds_match else None,
        "bathrooms": float(baths_match.group(1)) if baths_match else None,
        "property_type": property_type,
        "listing_type": listing_type,
        "status": "active",
        "property_id": property_id_match.group(1) if property_id_match else None,
        "needs_handoff": needs_handoff,
        "topic": topic,
    }
