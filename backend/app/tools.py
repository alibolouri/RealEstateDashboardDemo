import re
from datetime import UTC, datetime
from typing import Any

from backend.app.connectors import (
    assistant_brand,
    get_knowledge_source,
    get_listing_source,
    get_routing_source,
)


PROPERTY_TYPE_ALIASES = {
    "condo": "condo",
    "apartment": "apartment",
    "house": "house",
    "townhome": "townhome",
    "loft": "loft",
    "suite": "suite",
    "villa": "house",
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


def search_listings(**filters: Any) -> list[dict[str, Any]]:
    return get_listing_source().search_listings(**filters)


def get_listing_details(listing_id: str) -> dict[str, Any] | None:
    return get_listing_source().get_listing(listing_id)


def search_guidance(query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    return get_knowledge_source().search_guidance(query=query, topic=topic, limit=limit)


def recommend_agent(city: str | None = None, listing_id: str | None = None) -> tuple[dict[str, Any], str]:
    return get_routing_source().recommend_agent(city=city, listing_id=listing_id)


def get_handoff_policy() -> dict[str, Any]:
    return get_routing_source().get_handoff_policy()


def listing_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for row in rows:
        cards.append(
            {
                "id": row["id"],
                "source": row["source"],
                "external_id": row["external_id"],
                "title": row["title"],
                "address": row["address"],
                "city": row["city"],
                "state": row["state"],
                "zip_code": row["zip_code"],
                "price": row["price"],
                "listing_type": row["listing_type"],
                "property_type": row["property_type"],
                "status": row["status"],
                "bedrooms": row["bedrooms"],
                "bathrooms": row["bathrooms"],
                "square_feet": row.get("square_feet"),
                "short_description": row["short_description"],
                "image_url": row.get("image_url"),
                "brokerage": row.get("brokerage"),
                "url": row.get("url"),
                "last_synced_at": row.get("last_synced_at") or datetime.now(UTC),
                "provenance": row["provenance"],
                "data_status": row.get("data_status", "demo"),
            }
        )
    return cards


def _known_cities() -> set[str]:
    return get_listing_source().known_cities()


def interpret_query(message: str) -> dict[str, Any]:
    lower = message.lower()
    city = next((known for known in _known_cities() if known.lower() in lower), None)
    beds_match = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(?:bed|bedroom|bd)", lower)
    baths_match = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(?:bath|bathroom|ba)", lower)
    max_budget_match = re.search(r"(?:under|below|max(?:imum)?|up to)\s*\$?(\d[\d,]*)", lower)
    min_budget_match = re.search(r"(?:over|above|min(?:imum)?|from)\s*\$?(\d[\d,]*)", lower)
    listing_id_match = re.search(r"(prop-\d{3})", lower)
    property_type = next((value for hint, value in PROPERTY_TYPE_ALIASES.items() if hint in lower), None)
    listing_type = next((value for hint, value in LISTING_TYPE_HINTS.items() if hint in lower), None)
    needs_handoff = any(term in lower for term in ["contact", "connect", "call", "speak to", "human", "realtor", "agent"])
    intent = "general_real_estate_qna"
    topic = None

    if listing_id_match or "tell me about" in lower or "details" in lower:
        intent = "listing_detail"
    elif any(term in lower for term in ["find", "show", "looking for", "search", "available"]):
        intent = "listing_search"
    elif "sell" in lower or "list my" in lower:
        intent = "selling_guidance"
        topic = "sell"
    elif any(term in lower for term in ["rent", "lease", "apartment"]):
        if intent == "general_real_estate_qna":
            intent = "renting_guidance"
        topic = "rent"
    elif any(term in lower for term in ["buy", "offer", "mortgage", "inspection"]):
        intent = "buying_guidance"
        topic = "buy"
    elif any(term in lower for term in ["area", "neighborhood", "school", "commute"]):
        intent = "area_question"
        topic = "neighborhood"

    if needs_handoff and intent == "general_real_estate_qna":
        intent = "handoff_request"

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
        "listing_id": listing_id_match.group(1) if listing_id_match else None,
        "needs_handoff": needs_handoff,
        "topic": topic,
        "assistant_brand": assistant_brand(),
    }
