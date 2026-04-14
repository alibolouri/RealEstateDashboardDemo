import json
import re
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from backend.app.config import config_int_value, config_optional_value, config_value


DATA_DIR = Path(__file__).parent / "data"

LISTING_SOURCE_LABELS = {
    "demo_json": "Sample listings",
    "broker_feed": "Broker feed",
    "har_mls": "HAR / MLS",
    "reso_web_api": "RESO Web API",
    "bridge_interactive": "Bridge Interactive",
    "generic_json_api": "Generic JSON API",
    "idx_web_proxy": "IDX proxy",
}

KNOWLEDGE_SOURCE_LABELS = {
    "demo_json": "Embedded guidance",
    "local_markdown": "Local markdown docs",
    "remote_json": "Remote knowledge API",
}

ROUTING_SOURCE_LABELS = {
    "demo_roster": "Embedded routing roster",
    "external_roster": "External roster API",
}

LISTING_VALUE_ALIASES = {
    "id": ["id", "listing_id", "listingId", "ListingKey", "ListingId", "ListingKeyNumeric", "external_id"],
    "title": ["title", "headline", "public_remarks_title", "address", "street", "street_address", "UnparsedAddress"],
    "address": ["address", "street_address", "UnparsedAddress", "full_address"],
    "city": ["city", "City", "city_name"],
    "state": ["state", "StateOrProvince", "state_code"],
    "zip_code": ["zip_code", "postal_code", "PostalCode", "zip"],
    "price": ["price", "list_price", "ListPrice", "StandardPrice", "Amount"],
    "listing_type": ["listing_type", "listingType", "TransactionType", "transaction_type"],
    "property_type": ["property_type", "PropertyType", "propertyType"],
    "status": ["status", "StandardStatus", "listing_status"],
    "bedrooms": ["bedrooms", "beds", "BedroomsTotal", "bedroom_count"],
    "bathrooms": ["bathrooms", "baths", "BathroomsTotalDecimal", "bathroom_count"],
    "square_feet": ["square_feet", "sqft", "LivingArea", "living_area"],
    "short_description": ["short_description", "remarks", "PublicRemarks", "description"],
    "description": ["description", "PublicRemarks", "remarks"],
    "image_url": ["image_url", "primary_photo", "photo", "image", "MediaURL"],
    "listing_agent_name": ["listing_agent_name", "ListAgentFullName", "agent_name", "agentName"],
    "listing_agent_phone": ["listing_agent_phone", "ListAgentDirectPhone", "agent_phone", "agentPhone"],
    "url": ["url", "ListingURL", "detail_url"],
    "realtor_id": ["realtor_id", "agent_id", "agentId"],
}


def _load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _mode_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _coerce_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    cleaned = re.sub(r"[^\d.]", "", str(value))
    if not cleaned:
        return None
    return int(float(cleaned))


def _coerce_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.]", "", str(value))
    if not cleaned:
        return None
    return float(cleaned)


def _pick_alias(row: dict[str, Any], aliases: list[str]) -> Any:
    for alias in aliases:
        if alias in row and row[alias] not in {None, ""}:
            return row[alias]
    lowered = {str(key).lower(): value for key, value in row.items()}
    for alias in aliases:
        lowered_alias = alias.lower()
        if lowered_alias in lowered and lowered[lowered_alias] not in {None, ""}:
            return lowered[lowered_alias]
    return None


def brokerage_name() -> str:
    return config_value("BROKERAGE_NAME")


def assistant_brand() -> str:
    return config_value("ASSISTANT_BRAND_NAME")


def listing_source_mode() -> str:
    return config_value("LISTING_SOURCE_MODE")


def listing_connector_name() -> str:
    return config_value("LISTING_CONNECTOR_NAME")


def knowledge_source_mode() -> str:
    return config_value("KNOWLEDGE_SOURCE_MODE")


def routing_source_mode() -> str:
    return config_value("ROUTING_SOURCE_MODE")


class SourceUnavailableError(RuntimeError):
    pass


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
    def __init__(self, listings: list[dict[str, Any]], *, source_mode: str, connector_name: str):
        self._source_mode = source_mode
        self._connector_name = connector_name
        self._listings = [self._normalize_listing(row) for row in listings]

    def _normalize_listing(self, row: dict[str, Any]) -> dict[str, Any]:
        comparable_price = row["nightly_rate"] if row["listing_type"] == "short_stay" else row["price"]
        timestamp = datetime.now(UTC)
        source_label = self._connector_name or "Demo MLS Connector"
        provenance = "Demo JSON connector modeling an MLS/IDX/RESO-style listing feed."
        if self._source_mode != "demo_json":
            provenance = (
                f"Configured listing mode '{self._source_mode}' is not wired yet, so the app is serving sample listings "
                "through the demo JSON connector."
            )
        return {
            "id": row["id"],
            "source": source_label,
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
            "provenance": provenance,
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


class BaseRemoteJsonListingSource(ListingSource):
    def __init__(
        self,
        *,
        mode: str,
        label: str,
        base_url: str | None,
        api_key: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        partner_id: str | None = None,
        search_path: str = "/listings",
        detail_path: str = "/listings/{listing_id}",
    ):
        self.mode = mode
        self.label = label
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.partner_id = partner_id
        self.search_path = search_path
        self.detail_path = detail_path
        self._known_cities_cache: set[str] = set()

    def _ensure_ready(self) -> None:
        if not self.base_url:
            raise SourceUnavailableError(f"{self.label} is not configured.")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        if self.client_id:
            headers["X-Client-Id"] = self.client_id
        if self.client_secret:
            headers["X-Client-Secret"] = self.client_secret
        if self.partner_id:
            headers["X-Partner-Id"] = self.partner_id
        return headers

    def _request(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        self._ensure_ready()
        try:
            response = httpx.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self._headers(),
                timeout=12.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise SourceUnavailableError(f"{self.label} request failed.") from exc

    def _extract_rows(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ["results", "items", "data", "value", "listings", "records"]:
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
            if all(isinstance(value, dict) for value in payload.values()):
                return [value for value in payload.values() if isinstance(value, dict)]
        return []

    def _normalize_listing(self, row: dict[str, Any]) -> dict[str, Any]:
        listing_id = _pick_alias(row, LISTING_VALUE_ALIASES["id"])
        if not listing_id:
            raise SourceUnavailableError(f"{self.label} payload is missing a listing identifier.")
        city = _pick_alias(row, LISTING_VALUE_ALIASES["city"]) or "Unknown"
        state = _pick_alias(row, LISTING_VALUE_ALIASES["state"]) or "TX"
        title = _pick_alias(row, LISTING_VALUE_ALIASES["title"]) or f"Listing {listing_id}"
        address = _pick_alias(row, LISTING_VALUE_ALIASES["address"]) or title
        self._known_cities_cache.add(str(city))
        return {
            "id": str(listing_id),
            "source": self.label,
            "external_id": str(_pick_alias(row, LISTING_VALUE_ALIASES["id"]) or listing_id),
            "title": str(title),
            "address": str(address),
            "city": str(city),
            "state": str(state),
            "zip_code": str(_pick_alias(row, LISTING_VALUE_ALIASES["zip_code"]) or ""),
            "price": _coerce_int(_pick_alias(row, LISTING_VALUE_ALIASES["price"])) or 0,
            "listing_type": str(_pick_alias(row, LISTING_VALUE_ALIASES["listing_type"]) or "sale"),
            "property_type": str(_pick_alias(row, LISTING_VALUE_ALIASES["property_type"]) or "house"),
            "status": str(_pick_alias(row, LISTING_VALUE_ALIASES["status"]) or "active"),
            "bedrooms": _coerce_float(_pick_alias(row, LISTING_VALUE_ALIASES["bedrooms"])) or 0.0,
            "bathrooms": _coerce_float(_pick_alias(row, LISTING_VALUE_ALIASES["bathrooms"])) or 0.0,
            "square_feet": _coerce_int(_pick_alias(row, LISTING_VALUE_ALIASES["square_feet"])),
            "short_description": str(_pick_alias(row, LISTING_VALUE_ALIASES["short_description"]) or "No listing description provided."),
            "description": str(_pick_alias(row, LISTING_VALUE_ALIASES["description"]) or _pick_alias(row, LISTING_VALUE_ALIASES["short_description"]) or "No listing description provided."),
            "amenities": row.get("amenities", []),
            "photos": row.get("photos", []),
            "image_url": _pick_alias(row, LISTING_VALUE_ALIASES["image_url"]),
            "listing_agent_name": str(_pick_alias(row, LISTING_VALUE_ALIASES["listing_agent_name"]) or ""),
            "listing_agent_phone": str(_pick_alias(row, LISTING_VALUE_ALIASES["listing_agent_phone"]) or ""),
            "realtor_id": str(_pick_alias(row, LISTING_VALUE_ALIASES["realtor_id"]) or ""),
            "brokerage": brokerage_name(),
            "url": _pick_alias(row, LISTING_VALUE_ALIASES["url"]),
            "last_synced_at": datetime.now(UTC),
            "provenance": f"Live listing feed via {self.label}.",
            "data_status": "live",
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
        payload = self._request(
            self.search_path,
            params={
                "city": city,
                "max_price": max_price,
                "min_price": min_price,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "property_type": property_type,
                "listing_type": listing_type,
                "status": status,
                "limit": limit,
            },
        )
        return [self._normalize_listing(row) for row in self._extract_rows(payload)[:limit]]

    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        payload = self._request(self.detail_path.format(listing_id=listing_id))
        if isinstance(payload, dict):
            if any(isinstance(value, list) for value in payload.values()):
                rows = self._extract_rows(payload)
                if rows:
                    return self._normalize_listing(rows[0])
            return self._normalize_listing(payload)
        rows = self._extract_rows(payload)
        return self._normalize_listing(rows[0]) if rows else None

    def known_cities(self) -> set[str]:
        return self._known_cities_cache


class ResoWebApiListingSource(BaseRemoteJsonListingSource):
    def __init__(self):
        super().__init__(
            mode="reso_web_api",
            label="RESO Web API",
            base_url=config_optional_value("MLS_API_BASE_URL"),
            api_key=config_optional_value("MLS_API_KEY"),
            client_id=config_optional_value("MLS_CLIENT_ID"),
            client_secret=config_optional_value("MLS_CLIENT_SECRET"),
            partner_id=config_optional_value("MLS_PARTNER_ID"),
            search_path=config_value("LISTING_SEARCH_PATH"),
            detail_path=config_value("LISTING_DETAIL_PATH"),
        )


class HarMlsListingSource(BaseRemoteJsonListingSource):
    def __init__(self):
        super().__init__(
            mode="har_mls",
            label="HAR / MLS",
            base_url=config_optional_value("MLS_API_BASE_URL"),
            api_key=config_optional_value("MLS_API_KEY"),
            client_id=config_optional_value("MLS_CLIENT_ID"),
            client_secret=config_optional_value("MLS_CLIENT_SECRET"),
            partner_id=config_optional_value("MLS_PARTNER_ID"),
            search_path=config_value("LISTING_SEARCH_PATH"),
            detail_path=config_value("LISTING_DETAIL_PATH"),
        )


class BrokerFeedListingSource(BaseRemoteJsonListingSource):
    def __init__(self):
        super().__init__(
            mode="broker_feed",
            label="Broker feed",
            base_url=config_optional_value("BROKER_FEED_API_BASE_URL"),
            api_key=config_optional_value("BROKER_FEED_API_KEY"),
            search_path=config_value("BROKER_FEED_SEARCH_PATH"),
            detail_path=config_value("BROKER_FEED_DETAIL_PATH"),
        )


class BridgeInteractiveListingSource(BaseRemoteJsonListingSource):
    def __init__(self):
        super().__init__(
            mode="bridge_interactive",
            label="Bridge Interactive",
            base_url=config_optional_value("MLS_API_BASE_URL"),
            api_key=config_optional_value("MLS_API_KEY"),
            client_id=config_optional_value("MLS_CLIENT_ID"),
            client_secret=config_optional_value("MLS_CLIENT_SECRET"),
            partner_id=config_optional_value("MLS_PARTNER_ID"),
            search_path=config_value("LISTING_SEARCH_PATH"),
            detail_path=config_value("LISTING_DETAIL_PATH"),
        )


class GenericJsonApiListingSource(BaseRemoteJsonListingSource):
    def __init__(self):
        super().__init__(
            mode="generic_json_api",
            label="Generic JSON API",
            base_url=config_optional_value("MLS_API_BASE_URL") or config_optional_value("BROKER_FEED_API_BASE_URL"),
            api_key=config_optional_value("MLS_API_KEY") or config_optional_value("BROKER_FEED_API_KEY"),
            client_id=config_optional_value("MLS_CLIENT_ID"),
            client_secret=config_optional_value("MLS_CLIENT_SECRET"),
            partner_id=config_optional_value("MLS_PARTNER_ID"),
            search_path=config_value("LISTING_SEARCH_PATH"),
            detail_path=config_value("LISTING_DETAIL_PATH"),
        )


class CachedListingSource(ListingSource):
    def __init__(self, source: ListingSource, ttl_seconds: int):
        self._source = source
        self._ttl_seconds = max(ttl_seconds, 0)
        self._search_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._detail_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}

    def _fresh(self, timestamp: float) -> bool:
        return self._ttl_seconds <= 0 or (time.time() - timestamp) < self._ttl_seconds

    def search_listings(self, **filters: Any) -> list[dict[str, Any]]:
        cache_key = json.dumps(filters, sort_keys=True, default=str)
        cached = self._search_cache.get(cache_key)
        if cached and self._fresh(cached[0]):
            return cached[1]
        rows = self._source.search_listings(**filters)
        self._search_cache[cache_key] = (time.time(), rows)
        return rows

    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        cached = self._detail_cache.get(listing_id)
        if cached and self._fresh(cached[0]):
            return cached[1]
        row = self._source.get_listing(listing_id)
        self._detail_cache[listing_id] = (time.time(), row)
        return row

    def known_cities(self) -> set[str]:
        return self._source.known_cities()


class CompositeListingSource(ListingSource):
    def __init__(self, providers: list[tuple[str, ListingSource]]):
        self._providers = providers

    def _try(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for _, provider in self._providers:
            try:
                return getattr(provider, method_name)(*args, **kwargs)
            except SourceUnavailableError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise SourceUnavailableError("No listing providers are configured.")

    def search_listings(self, **filters: Any) -> list[dict[str, Any]]:
        return self._try("search_listings", **filters)

    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        return self._try("get_listing", listing_id)

    def known_cities(self) -> set[str]:
        cities: set[str] = set()
        for _, provider in self._providers:
            try:
                cities |= provider.known_cities()
            except SourceUnavailableError:
                continue
        return cities


class JsonKnowledgeSource(KnowledgeSource):
    def __init__(self, docs: list[dict[str, Any]], *, label: str = "Embedded guidance"):
        self._docs = docs
        self.label = label

    def search_guidance(self, query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        tokens = {token for token in re.findall(r"[a-zA-Z]{3,}", query.lower())}
        scored: list[tuple[int, dict[str, Any]]] = []
        for doc in self._docs:
            doc_tokens = set(doc.get("topics", [])) | set(re.findall(r"[a-zA-Z]{3,}", doc.get("content", "").lower()))
            score = len(tokens & doc_tokens)
            if topic and topic in doc.get("topics", []):
                score += 3
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [doc for _, doc in scored[:limit]]


class LocalMarkdownKnowledgeSource(KnowledgeSource):
    def __init__(self, directory: str | None):
        self._directory = Path(directory) if directory else None

    def _docs(self) -> list[dict[str, Any]]:
        if not self._directory or not self._directory.exists():
            raise SourceUnavailableError("Local knowledge path is not configured.")
        docs = []
        for file_path in sorted(self._directory.glob("*.md")):
            content = file_path.read_text(encoding="utf-8")
            docs.append(
                {
                    "id": file_path.stem,
                    "title": file_path.stem.replace("_", " ").title(),
                    "topics": re.findall(r"[a-zA-Z]{4,}", file_path.stem.lower()),
                    "content": content,
                }
            )
        return docs

    def search_guidance(self, query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        return JsonKnowledgeSource(self._docs(), label="Local markdown docs").search_guidance(query=query, topic=topic, limit=limit)


class RemoteJsonKnowledgeSource(KnowledgeSource):
    def __init__(self):
        self._url = config_optional_value("KNOWLEDGE_REMOTE_URL")
        self._api_key = config_optional_value("KNOWLEDGE_REMOTE_API_KEY")
        self._search_path = config_value("KNOWLEDGE_REMOTE_SEARCH_PATH")

    def search_guidance(self, query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        if not self._url:
            raise SourceUnavailableError("Remote knowledge source is not configured.")
        try:
            response = httpx.get(
                f"{self._url.rstrip('/')}{self._search_path}",
                params={"query": query, "topic": topic, "limit": limit},
                headers={"Accept": "application/json", **({"Authorization": f"Bearer {self._api_key}"} if self._api_key else {})},
                timeout=12.0,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise SourceUnavailableError("Remote knowledge source request failed.") from exc

        rows = payload if isinstance(payload, list) else payload.get("results", payload.get("items", []))
        normalized = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            normalized.append(
                {
                    "id": row.get("id") or row.get("slug") or "remote-doc",
                    "title": row.get("title") or "Remote guidance",
                    "topics": row.get("topics") or [],
                    "content": row.get("content") or row.get("summary") or "",
                }
            )
        return normalized


class CompositeKnowledgeSource(KnowledgeSource):
    def __init__(self, providers: list[tuple[str, KnowledgeSource]]):
        self._providers = providers

    def search_guidance(self, query: str, topic: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        for _, provider in self._providers:
            try:
                results = provider.search_guidance(query=query, topic=topic, limit=limit)
                if results:
                    return results
            except SourceUnavailableError:
                continue
        return []


class JsonRoutingSource(RoutingSource):
    def __init__(self, realtors: list[dict[str, Any]], listing_source: ListingSource):
        self._realtors = realtors
        self._listing_source = listing_source

    def recommend_agent(self, city: str | None = None, listing_id: str | None = None) -> tuple[dict[str, Any], str]:
        if listing_id:
            listing = self._listing_source.get_listing(listing_id)
            if listing:
                realtor = next((row for row in self._realtors if row["id"] == listing.get("realtor_id")), None)
                if realtor:
                    return realtor, "Matched by listing specialist assignment"
        if city:
            realtor = next((row for row in self._realtors if city in row["cities_covered"]), None)
            if realtor:
                return realtor, f"Matched by city coverage in {city}"
        return self._realtors[0], "Default brokerage fallback realtor"

    def get_handoff_policy(self) -> dict[str, Any]:
        number = config_value("BROKERAGE_CONTACT_NUMBER")
        return {
            "fixed_contact_number": number,
            "brokerage_name": brokerage_name(),
            "message": f"Start with {brokerage_name()} on the fixed line, then continue with the recommended local realtor.",
        }


class RemoteRosterRoutingSource(RoutingSource):
    def __init__(self):
        self._url = config_optional_value("EXTERNAL_ROSTER_URL")
        self._api_key = config_optional_value("EXTERNAL_ROSTER_API_KEY")

    def _ensure(self) -> None:
        if not self._url:
            raise SourceUnavailableError("External roster source is not configured.")

    def recommend_agent(self, city: str | None = None, listing_id: str | None = None) -> tuple[dict[str, Any], str]:
        self._ensure()
        try:
            response = httpx.get(
                f"{self._url.rstrip('/')}/recommend",
                params={"city": city, "listing_id": listing_id},
                headers={"Accept": "application/json", **({"Authorization": f"Bearer {self._api_key}"} if self._api_key else {})},
                timeout=12.0,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise SourceUnavailableError("External roster request failed.") from exc
        return payload["realtor"], payload.get("reason", "Matched by external roster")

    def get_handoff_policy(self) -> dict[str, Any]:
        return {
            "fixed_contact_number": config_value("BROKERAGE_CONTACT_NUMBER"),
            "brokerage_name": brokerage_name(),
            "message": f"Start with {brokerage_name()} on the fixed line, then continue with the recommended local realtor.",
        }


class CompositeRoutingSource(RoutingSource):
    def __init__(self, providers: list[tuple[str, RoutingSource]]):
        self._providers = providers

    def recommend_agent(self, city: str | None = None, listing_id: str | None = None) -> tuple[dict[str, Any], str]:
        last_error: Exception | None = None
        for _, provider in self._providers:
            try:
                return provider.recommend_agent(city=city, listing_id=listing_id)
            except SourceUnavailableError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise SourceUnavailableError("No routing source is configured.")

    def get_handoff_policy(self) -> dict[str, Any]:
        for _, provider in self._providers:
            try:
                return provider.get_handoff_policy()
            except SourceUnavailableError:
                continue
        raise SourceUnavailableError("No routing source is configured.")


def _listing_modes() -> list[str]:
    primary = listing_source_mode()
    fallbacks = _mode_list(config_optional_value("LISTING_FALLBACK_MODES"))
    ordered = [primary, *fallbacks]
    if "demo_json" not in ordered:
        ordered.append("demo_json")
    return list(dict.fromkeys(ordered))


def _knowledge_modes() -> list[str]:
    primary = knowledge_source_mode()
    fallbacks = _mode_list(config_optional_value("KNOWLEDGE_FALLBACK_MODES"))
    ordered = [primary, *fallbacks]
    if "demo_json" not in ordered:
        ordered.append("demo_json")
    return list(dict.fromkeys(ordered))


def _routing_modes() -> list[str]:
    primary = routing_source_mode()
    fallbacks = _mode_list(config_optional_value("ROUTING_FALLBACK_MODES"))
    ordered = [primary, *fallbacks]
    if "demo_roster" not in ordered:
        ordered.append("demo_roster")
    return list(dict.fromkeys(ordered))


def _build_listing_provider(mode: str) -> ListingSource:
    if mode == "demo_json":
        return JsonListingSource(_load_json("properties.json"), source_mode=mode, connector_name=listing_connector_name())
    if mode == "broker_feed":
        return BrokerFeedListingSource()
    if mode == "har_mls":
        return HarMlsListingSource()
    if mode == "reso_web_api":
        return ResoWebApiListingSource()
    if mode == "bridge_interactive":
        return BridgeInteractiveListingSource()
    if mode in {"generic_json_api", "idx_web_proxy"}:
        return GenericJsonApiListingSource()
    raise SourceUnavailableError(f"Unsupported listing source mode '{mode}'.")


def _build_knowledge_provider(mode: str) -> KnowledgeSource:
    if mode == "demo_json":
        return JsonKnowledgeSource(_load_json("knowledge.json"))
    if mode == "local_markdown":
        return LocalMarkdownKnowledgeSource(config_optional_value("KNOWLEDGE_LOCAL_PATH"))
    if mode == "remote_json":
        return RemoteJsonKnowledgeSource()
    raise SourceUnavailableError(f"Unsupported knowledge source mode '{mode}'.")


def _build_routing_provider(mode: str) -> RoutingSource:
    if mode == "demo_roster":
        return JsonRoutingSource(_load_json("realtors.json"), get_listing_source())
    if mode == "external_roster":
        return RemoteRosterRoutingSource()
    raise SourceUnavailableError(f"Unsupported routing source mode '{mode}'.")


@lru_cache(maxsize=8)
def _listing_source_for(signature: str) -> ListingSource:
    providers = []
    for mode in signature.split("|"):
        providers.append((mode, CachedListingSource(_build_listing_provider(mode), config_int_value("LISTING_CACHE_TTL_SECONDS"))))
    return CompositeListingSource(providers)


def get_listing_source() -> ListingSource:
    return _listing_source_for("|".join(_listing_modes()))


@lru_cache(maxsize=8)
def _knowledge_source_for(signature: str) -> KnowledgeSource:
    providers = [(mode, _build_knowledge_provider(mode)) for mode in signature.split("|")]
    return CompositeKnowledgeSource(providers)


def get_knowledge_source() -> KnowledgeSource:
    return _knowledge_source_for("|".join(_knowledge_modes()))


@lru_cache(maxsize=8)
def _routing_source_for(signature: str) -> RoutingSource:
    providers = [(mode, _build_routing_provider(mode)) for mode in signature.split("|")]
    return CompositeRoutingSource(providers)


def get_routing_source() -> RoutingSource:
    return _routing_source_for("|".join(_routing_modes()))


def _readiness_entry(mode: str, source_type: str, label: str, *, configured: bool, ready: bool, reason: str | None) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "mode": mode,
        "label": label,
        "configured": configured,
        "ready": ready,
        "reason": reason,
    }


def listing_source_status() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for mode in _listing_modes():
        configured = True
        ready = True
        reason = None
        if mode in {"har_mls", "reso_web_api", "bridge_interactive", "generic_json_api", "idx_web_proxy"}:
            configured = bool(config_optional_value("MLS_API_BASE_URL"))
            ready = configured
            reason = None if ready else "MLS API base URL is not configured."
        elif mode == "broker_feed":
            configured = bool(config_optional_value("BROKER_FEED_API_BASE_URL"))
            ready = configured
            reason = None if ready else "Broker feed API base URL is not configured."
        statuses.append(_readiness_entry(mode, "listing_source", LISTING_SOURCE_LABELS.get(mode, mode), configured=configured, ready=ready, reason=reason))
    return statuses


def knowledge_source_status() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for mode in _knowledge_modes():
        configured = True
        ready = True
        reason = None
        if mode == "local_markdown":
            configured = bool(config_optional_value("KNOWLEDGE_LOCAL_PATH"))
            ready = configured
            reason = None if ready else "Knowledge local path is not configured."
        elif mode == "remote_json":
            configured = bool(config_optional_value("KNOWLEDGE_REMOTE_URL"))
            ready = configured
            reason = None if ready else "Remote knowledge URL is not configured."
        statuses.append(_readiness_entry(mode, "knowledge_source", KNOWLEDGE_SOURCE_LABELS.get(mode, mode), configured=configured, ready=ready, reason=reason))
    return statuses


def routing_source_status() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for mode in _routing_modes():
        configured = True
        ready = True
        reason = None
        if mode == "external_roster":
            configured = bool(config_optional_value("EXTERNAL_ROSTER_URL"))
            ready = configured
            reason = None if ready else "External roster URL is not configured."
        statuses.append(_readiness_entry(mode, "routing_source", ROUTING_SOURCE_LABELS.get(mode, mode), configured=configured, ready=ready, reason=reason))
    return statuses


def active_connector_summary() -> dict[str, Any]:
    listing_status = listing_source_status()
    knowledge_status = knowledge_source_status()
    routing_status = routing_source_status()
    return {
        "listing": {
            "configured_mode": listing_source_mode(),
            "fallback_modes": _listing_modes()[1:],
            "active_mode": next((row["mode"] for row in listing_status if row["ready"]), "demo_json"),
            "connectors": listing_status,
        },
        "knowledge": {
            "configured_mode": knowledge_source_mode(),
            "fallback_modes": _knowledge_modes()[1:],
            "active_mode": next((row["mode"] for row in knowledge_status if row["ready"]), "demo_json"),
            "connectors": knowledge_status,
        },
        "routing": {
            "configured_mode": routing_source_mode(),
            "fallback_modes": _routing_modes()[1:],
            "active_mode": next((row["mode"] for row in routing_status if row["ready"]), "demo_roster"),
            "connectors": routing_status,
        },
    }


def invalidate_source_caches() -> None:
    _listing_source_for.cache_clear()
    _knowledge_source_for.cache_clear()
    _routing_source_for.cache_clear()
