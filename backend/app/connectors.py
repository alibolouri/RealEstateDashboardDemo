import json
import os
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent / "data"


def _load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def brokerage_name() -> str:
    return os.getenv("BROKERAGE_NAME", "Summit Realty Group")


def assistant_brand() -> str:
    return os.getenv("ASSISTANT_BRAND_NAME", "Real Estate Concierge")


def listing_source_mode() -> str:
    return os.getenv("LISTING_SOURCE_MODE", "demo_json")


class ListingSource(ABC):
    @abstractmethod
    def search_listings(
        self,
        *,
        city: str | None = None,
        max_price: int | None = None,
        min_price: int | None = None,
        bedrooms: float | None = None,
        bathrooms: float | None = None,
        property_type: str | None = None,
        listing_type: str | None = None,
        status: str | None = "active",
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def known_cities(self) -> set[str]:
        raise NotImplementedError


class KnowledgeSource(ABC):
    @abstractmethod
    def search_guidance(self, query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        raise NotImplementedError


class RoutingSource(ABC):
    @abstractmethod
    def recommend_agent(self, city: str | None = None, listing_id: str | None = None) -> tuple[dict[str, Any], str]:
        raise NotImplementedError

    @abstractmethod
    def get_handoff_policy(self) -> dict[str, Any]:
        raise NotImplementedError


class JsonListingSource(ListingSource):
    def __init__(self, listings: list[dict[str, Any]]):
        self._listings = [self._normalize_listing(row) for row in listings]

    def _normalize_listing(self, row: dict[str, Any]) -> dict[str, Any]:
        comparable_price = row["nightly_rate"] if row["listing_type"] == "short_stay" else row["price"]
        timestamp = datetime.now(UTC)
        return {
            "id": row["id"],
            "source": "Demo MLS Connector",
            "external_id": row["id"],
            "title": row["title"],
            "address": row["address"],
            "city": row["city"],
            "state": row["state"],
            "zip_code": row["zip_code"],
            "price": comparable_price,
            "listing_type": row["listing_type"],
            "property_type": row["property_type"],
            "status": row["status"],
            "bedrooms": row["bedrooms"],
            "bathrooms": row["bathrooms"],
            "square_feet": row.get("square_feet"),
            "short_description": row["short_description"],
            "description": row["short_description"],
            "amenities": row.get("amenities", []),
            "photos": [row["image_url"]] if row.get("image_url") else [],
            "image_url": row.get("image_url"),
            "listing_agent_name": row["listing_agent_name"],
            "listing_agent_phone": row["listing_agent_phone"],
            "realtor_id": row["realtor_id"],
            "brokerage": brokerage_name(),
            "url": f"https://example-mls.test/listings/{row['id']}",
            "last_synced_at": timestamp,
            "provenance": "Demo JSON connector modeling an MLS/IDX/RESO-style listing feed.",
            "data_status": "demo",
            "nightly_rate": row.get("nightly_rate"),
            "max_guests": row.get("max_guests"),
            "minimum_nights": row.get("minimum_nights"),
            "neighborhood": row.get("neighborhood"),
        }

    def search_listings(
        self,
        *,
        city: str | None = None,
        max_price: int | None = None,
        min_price: int | None = None,
        bedrooms: float | None = None,
        bathrooms: float | None = None,
        property_type: str | None = None,
        listing_type: str | None = None,
        status: str | None = "active",
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in self._listings:
            if city and _normalize(item["city"]) != _normalize(city):
                continue
            if property_type and _normalize(item["property_type"]) != _normalize(property_type):
                continue
            if listing_type and _normalize(item["listing_type"]) != _normalize(listing_type):
                continue
            if status and _normalize(item["status"]) != _normalize(status):
                continue
            if max_price is not None and item["price"] > max_price:
                continue
            if min_price is not None and item["price"] < min_price:
                continue
            if bedrooms is not None and item["bedrooms"] < bedrooms:
                continue
            if bathrooms is not None and item["bathrooms"] < bathrooms:
                continue
            results.append(item)
        return results[:limit]

    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        return next((item for item in self._listings if item["id"] == listing_id), None)

    def known_cities(self) -> set[str]:
        return {item["city"] for item in self._listings}


class JsonKnowledgeSource(KnowledgeSource):
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs

    def search_guidance(self, query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        tokens = {token for token in re.findall(r"[a-zA-Z]{3,}", query.lower())}
        scored: list[tuple[int, dict[str, Any]]] = []
        for doc in self._docs:
            doc_tokens = set(doc["topics"]) | set(re.findall(r"[a-zA-Z]{3,}", doc["content"].lower()))
            score = len(tokens & doc_tokens)
            if topic and topic in doc["topics"]:
                score += 3
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [doc for _, doc in scored[:limit]]


class JsonRoutingSource(RoutingSource):
    def __init__(self, realtors: list[dict[str, Any]], listing_source: ListingSource):
        self._realtors = realtors
        self._listing_source = listing_source

    def recommend_agent(self, city: str | None = None, listing_id: str | None = None) -> tuple[dict[str, Any], str]:
        if listing_id:
            listing = self._listing_source.get_listing(listing_id)
            if listing:
                realtor = next((row for row in self._realtors if row["id"] == listing["realtor_id"]), None)
                if realtor:
                    return realtor, "Matched by listing specialist assignment"
        if city:
            realtor = next((row for row in self._realtors if city in row["cities_covered"]), None)
            if realtor:
                return realtor, f"Matched by city coverage in {city}"
        return self._realtors[0], "Default brokerage fallback realtor"

    def get_handoff_policy(self) -> dict[str, Any]:
        number = os.getenv("BROKERAGE_CONTACT_NUMBER", "+1-888-555-0199")
        return {
            "fixed_contact_number": number,
            "brokerage_name": brokerage_name(),
            "message": f"Start with {brokerage_name()} on the fixed line, then continue with the recommended local realtor.",
        }


@lru_cache(maxsize=1)
def get_listing_source() -> ListingSource:
    mode = listing_source_mode()
    if mode != "demo_json":
        raise NotImplementedError(f"Listing source mode '{mode}' is not implemented yet.")
    return JsonListingSource(_load_json("properties.json"))


@lru_cache(maxsize=1)
def get_knowledge_source() -> KnowledgeSource:
    return JsonKnowledgeSource(_load_json("knowledge.json"))


@lru_cache(maxsize=1)
def get_routing_source() -> RoutingSource:
    return JsonRoutingSource(_load_json("realtors.json"), get_listing_source())
