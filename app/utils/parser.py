import re
from typing import Any

from app.utils.constants import CITIES, PROPERTY_TYPES


DETAIL_HINTS = ("tell me about", "details", "detail", "learn more")
CONTACT_HINTS = ("contact", "who do i contact", "call", "reach", "agent", "listing agent")
SEARCH_HINTS = (
    "show me",
    "find",
    "available",
    "looking for",
    "homes",
    "properties",
    "condos",
    "rent",
    "buy",
)


def normalize_city(city: str | None) -> str | None:
    if not city:
        return None
    normalized = city.strip().lower()
    for known_city in CITIES:
        if known_city.lower() == normalized:
            return known_city
    return city.strip().title()


def detect_intent(message: str) -> str:
    lowered = message.lower()
    if any(hint in lowered for hint in CONTACT_HINTS):
        return "contact_request"
    if any(hint in lowered for hint in DETAIL_HINTS):
        return "property_detail"
    if any(hint in lowered for hint in SEARCH_HINTS):
        return "property_search"
    return "general_inquiry"


def extract_filters(message: str) -> dict[str, Any]:
    lowered = message.lower()
    filters: dict[str, Any] = {}

    for city in CITIES:
        if city.lower() in lowered:
            filters["city"] = city
            break

    bed_match = re.search(r"(\d+)[-\s]?(?:bed|bedroom)", lowered)
    if bed_match:
        filters["bedrooms"] = int(bed_match.group(1))

    bath_match = re.search(r"(\d+(?:\.\d+)?)[-\s]?(?:bath|bathroom)", lowered)
    if bath_match:
        filters["bathrooms"] = float(bath_match.group(1))

    under_match = re.search(r"(?:under|below|max)\s*\$?\s*([\d,]+)(?:k)?", lowered)
    if under_match:
        raw_value = under_match.group(1).replace(",", "")
        value = int(raw_value)
        if "k" in under_match.group(0):
            value *= 1000
        filters["max_price"] = value

    between_match = re.search(r"(?:between|min)\s*\$?\s*([\d,]+)(?:k)?", lowered)
    if between_match and "min_price" not in filters:
        raw_value = between_match.group(1).replace(",", "")
        value = int(raw_value)
        if "k" in between_match.group(0):
            value *= 1000
        filters["min_price"] = value

    explicit_amounts = re.findall(r"\$?\s*([\d,]{3,})(k)?", lowered)
    if explicit_amounts and "max_price" not in filters:
        amount, suffix = explicit_amounts[0]
        value = int(amount.replace(",", ""))
        if suffix:
            value *= 1000
        filters["max_price"] = value

    for property_type in PROPERTY_TYPES:
        if property_type in lowered:
            filters["property_type"] = property_type
            break

    if "rent" in lowered:
        filters["status"] = "for_rent"
    elif "sale" in lowered or "buy" in lowered or "home" in lowered or "house" in lowered:
        filters.setdefault("status", "for_sale")

    property_id_match = re.search(r"(?:property|listing)\s+#?\s*(\d+)", lowered)
    if property_id_match:
        filters["property_id"] = int(property_id_match.group(1))

    return filters
