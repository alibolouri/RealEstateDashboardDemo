import os
from collections import defaultdict
from functools import lru_cache
from typing import Any

from backend.app.database import get_settings_map, upsert_settings


SETTINGS_GROUPS = [
    {
        "id": "branding",
        "label": "Brokerage and branding",
        "description": "These values control the visible assistant and brokerage identity shown to end users.",
    },
    {
        "id": "llm",
        "label": "LLM configuration",
        "description": "Model configuration applies on the next request. The chat stays usable without a key through deterministic fallback.",
    },
    {
        "id": "listing_source",
        "label": "Listing source configuration",
        "description": "Configure the active listing connector and the credentials it will need when live source integration is enabled.",
    },
    {
        "id": "knowledge_source",
        "label": "Knowledge source configuration",
        "description": "Guidance answers can come from embedded docs, local markdown libraries, or a remote knowledge API.",
    },
    {
        "id": "routing_source",
        "label": "Routing source configuration",
        "description": "Control how realtor recommendations and human handoff policies are resolved.",
    },
    {
        "id": "enrichment",
        "label": "Enrichment APIs",
        "description": "Optional APIs for geocoding, schools, and financing intelligence.",
    },
]


SETTING_FIELDS = [
    {
        "key": "BROKERAGE_NAME",
        "label": "Brokerage name",
        "group": "branding",
        "kind": "text",
        "required": True,
        "secret": False,
        "placeholder": "Summit Realty Group",
        "help_text": "Used in handoff messaging, the sidebar, and workspace title metadata.",
        "default": "Summit Realty Group",
    },
    {
        "key": "BROKERAGE_CONTACT_NUMBER",
        "label": "Brokerage contact number",
        "group": "branding",
        "kind": "text",
        "required": True,
        "secret": False,
        "placeholder": "+1-888-555-0199",
        "help_text": "Always shown first when the user requests human assistance.",
        "default": "+1-888-555-0199",
    },
    {
        "key": "ASSISTANT_BRAND_NAME",
        "label": "Assistant brand name",
        "group": "branding",
        "kind": "text",
        "required": True,
        "secret": False,
        "placeholder": "Real Estate Concierge",
        "help_text": "The primary assistant title shown in the UI and API health metadata.",
        "default": "Real Estate Concierge",
    },
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API key",
        "group": "llm",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "sk-...",
        "help_text": "When present, the LangGraph/OpenAI path is active. Without it, the deterministic fallback stays available.",
        "default": "",
    },
    {
        "key": "OPENAI_MODEL",
        "label": "OpenAI model",
        "group": "llm",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "gpt-4o-mini",
        "help_text": "Model name used for live LLM responses.",
        "default": "gpt-4o-mini",
    },
    {
        "key": "LISTING_SOURCE_MODE",
        "label": "Listing source mode",
        "group": "listing_source",
        "kind": "select",
        "required": True,
        "secret": False,
        "placeholder": "demo_json",
        "help_text": "Current implementation ships with demo_json. Additional connectors can be configured without changing the UI.",
        "default": "demo_json",
        "options": [
            {"value": "demo_json", "label": "Sample listings"},
            {"value": "broker_feed", "label": "Broker feed"},
            {"value": "har_mls", "label": "HAR / MLS"},
            {"value": "reso_web_api", "label": "RESO Web API"},
            {"value": "bridge_interactive", "label": "Bridge Interactive"},
            {"value": "generic_json_api", "label": "Generic JSON API"},
            {"value": "idx_web_proxy", "label": "IDX proxy"},
        ],
    },
    {
        "key": "LISTING_FALLBACK_MODES",
        "label": "Listing fallback modes",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "broker_feed,demo_json",
        "help_text": "Comma-separated fallback chain used when the primary listing connector is unavailable.",
        "default": "demo_json",
    },
    {
        "key": "LISTING_CONNECTOR_NAME",
        "label": "Listing connector display name",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "Demo MLS Connector",
        "help_text": "Optional operator-facing name for the current listing connector.",
        "default": "Demo MLS Connector",
    },
    {
        "key": "LISTING_CACHE_TTL_SECONDS",
        "label": "Listing cache TTL",
        "group": "listing_source",
        "kind": "number",
        "required": False,
        "secret": False,
        "placeholder": "900",
        "help_text": "Reserved for live connector caching. Stored now so the runtime contract is stable.",
        "default": "900",
    },
    {
        "key": "LISTING_SEARCH_PATH",
        "label": "Listing search path",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "/listings",
        "help_text": "Relative search path used by generic MLS and RESO-style connectors.",
        "default": "/listings",
    },
    {
        "key": "LISTING_DETAIL_PATH",
        "label": "Listing detail path",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "/listings/{listing_id}",
        "help_text": "Relative detail path with `{listing_id}` placeholder for generic MLS and RESO-style connectors.",
        "default": "/listings/{listing_id}",
    },
    {
        "key": "MLS_API_BASE_URL",
        "label": "MLS API base URL",
        "group": "listing_source",
        "kind": "url",
        "required": False,
        "secret": False,
        "placeholder": "https://api.example-mls.com",
        "help_text": "Base URL for an official MLS / RESO feed when it is enabled.",
        "default": "",
    },
    {
        "key": "MLS_API_KEY",
        "label": "MLS API key",
        "group": "listing_source",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "API key",
        "help_text": "Primary MLS/RESO API credential when your provider uses key-based auth.",
        "default": "",
    },
    {
        "key": "MLS_CLIENT_ID",
        "label": "MLS client ID",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "Client ID",
        "help_text": "Optional OAuth-style client identifier for MLS integrations.",
        "default": "",
    },
    {
        "key": "MLS_CLIENT_SECRET",
        "label": "MLS client secret",
        "group": "listing_source",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "Client secret",
        "help_text": "Optional OAuth-style client secret for MLS integrations.",
        "default": "",
    },
    {
        "key": "MLS_PARTNER_ID",
        "label": "MLS partner ID",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "Partner ID",
        "help_text": "Partner or account identifier when required by the MLS or vendor.",
        "default": "",
    },
    {
        "key": "BROKER_FEED_API_BASE_URL",
        "label": "Broker feed API base URL",
        "group": "listing_source",
        "kind": "url",
        "required": False,
        "secret": False,
        "placeholder": "https://broker-feed.example.com",
        "help_text": "Optional direct broker feed endpoint.",
        "default": "",
    },
    {
        "key": "BROKER_FEED_API_KEY",
        "label": "Broker feed API key",
        "group": "listing_source",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "Broker feed API key",
        "help_text": "Credential for a broker-approved listing feed.",
        "default": "",
    },
    {
        "key": "BROKER_FEED_SEARCH_PATH",
        "label": "Broker feed search path",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "/listings",
        "help_text": "Relative search path for direct broker-feed integrations.",
        "default": "/listings",
    },
    {
        "key": "BROKER_FEED_DETAIL_PATH",
        "label": "Broker feed detail path",
        "group": "listing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "/listings/{listing_id}",
        "help_text": "Relative detail path for direct broker-feed integrations.",
        "default": "/listings/{listing_id}",
    },
    {
        "key": "KNOWLEDGE_SOURCE_MODE",
        "label": "Knowledge source mode",
        "group": "knowledge_source",
        "kind": "select",
        "required": True,
        "secret": False,
        "placeholder": "demo_json",
        "help_text": "Choose where process guidance and brokerage knowledge should come from.",
        "default": "demo_json",
        "options": [
            {"value": "demo_json", "label": "Embedded guidance"},
            {"value": "local_markdown", "label": "Local markdown docs"},
            {"value": "remote_json", "label": "Remote knowledge API"},
        ],
    },
    {
        "key": "KNOWLEDGE_FALLBACK_MODES",
        "label": "Knowledge fallback modes",
        "group": "knowledge_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "local_markdown,demo_json",
        "help_text": "Comma-separated fallback chain used when the primary knowledge source is unavailable.",
        "default": "demo_json",
    },
    {
        "key": "KNOWLEDGE_LOCAL_PATH",
        "label": "Knowledge local path",
        "group": "knowledge_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "D:\\brokerage-docs",
        "help_text": "Directory containing markdown docs that should be used as structured brokerage guidance.",
        "default": "",
    },
    {
        "key": "KNOWLEDGE_REMOTE_URL",
        "label": "Knowledge remote base URL",
        "group": "knowledge_source",
        "kind": "url",
        "required": False,
        "secret": False,
        "placeholder": "https://knowledge.example.com",
        "help_text": "Base URL for a remote knowledge API.",
        "default": "",
    },
    {
        "key": "KNOWLEDGE_REMOTE_API_KEY",
        "label": "Knowledge remote API key",
        "group": "knowledge_source",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "Knowledge API key",
        "help_text": "Credential for a remote knowledge service.",
        "default": "",
    },
    {
        "key": "KNOWLEDGE_REMOTE_SEARCH_PATH",
        "label": "Knowledge remote search path",
        "group": "knowledge_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "/search",
        "help_text": "Relative search path for the remote knowledge API.",
        "default": "/search",
    },
    {
        "key": "ROUTING_SOURCE_MODE",
        "label": "Routing source mode",
        "group": "routing_source",
        "kind": "select",
        "required": True,
        "secret": False,
        "placeholder": "demo_roster",
        "help_text": "Choose whether realtor recommendations come from the embedded roster or an external source.",
        "default": "demo_roster",
        "options": [
            {"value": "demo_roster", "label": "Embedded roster"},
            {"value": "external_roster", "label": "External roster API"},
        ],
    },
    {
        "key": "ROUTING_FALLBACK_MODES",
        "label": "Routing fallback modes",
        "group": "routing_source",
        "kind": "text",
        "required": False,
        "secret": False,
        "placeholder": "demo_roster",
        "help_text": "Comma-separated fallback chain for realtor recommendation and handoff routing.",
        "default": "demo_roster",
    },
    {
        "key": "EXTERNAL_ROSTER_URL",
        "label": "External roster URL",
        "group": "routing_source",
        "kind": "url",
        "required": False,
        "secret": False,
        "placeholder": "https://roster.example.com",
        "help_text": "Base URL for an external roster or assignment service.",
        "default": "",
    },
    {
        "key": "EXTERNAL_ROSTER_API_KEY",
        "label": "External roster API key",
        "group": "routing_source",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "Roster API key",
        "help_text": "Credential for an external roster or agent-assignment service.",
        "default": "",
    },
    {
        "key": "GOOGLE_MAPS_API_KEY",
        "label": "Google Maps API key",
        "group": "enrichment",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "Google Maps key",
        "help_text": "For geocoding, address normalization, and later route intelligence.",
        "default": "",
    },
    {
        "key": "GREATSCHOOLS_API_KEY",
        "label": "GreatSchools API key",
        "group": "enrichment",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "GreatSchools key",
        "help_text": "For school-aware area questions and district comparisons.",
        "default": "",
    },
    {
        "key": "FRED_API_KEY",
        "label": "FRED API key",
        "group": "enrichment",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "FRED key",
        "help_text": "For future financing and mortgage-rate intelligence.",
        "default": "",
    },
    {
        "key": "ATTOM_API_KEY",
        "label": "ATTOM API key",
        "group": "enrichment",
        "kind": "password",
        "required": False,
        "secret": True,
        "placeholder": "ATTOM key",
        "help_text": "For future property intelligence, public-record, and valuation enrichment.",
        "default": "",
    },
]


FIELD_MAP = {field["key"]: field for field in SETTING_FIELDS}
SECRET_KEYS = {field["key"] for field in SETTING_FIELDS if field.get("secret")}


def _masked_secret(value: str | None) -> str | None:
    if not value:
        return None
    return "Configured"


@lru_cache(maxsize=1)
def _env_snapshot() -> dict[str, str]:
    return {field["key"]: os.getenv(field["key"], "") for field in SETTING_FIELDS}


@lru_cache(maxsize=1)
def _db_snapshot() -> dict[str, str]:
    return get_settings_map()


def refresh_runtime_config() -> None:
    _env_snapshot.cache_clear()
    _db_snapshot.cache_clear()


class ConfigService:
    def get(self, key: str) -> str:
        field = FIELD_MAP[key]
        db_values = _db_snapshot()
        value = db_values.get(key)
        if value is not None and value != "":
            return value
        env_value = _env_snapshot().get(key, "")
        if env_value:
            return env_value
        return str(field.get("default", ""))

    def get_optional(self, key: str) -> str | None:
        value = self.get(key).strip()
        return value or None

    def get_int(self, key: str) -> int:
        raw_value = self.get(key).strip()
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return int(FIELD_MAP[key].get("default", 0) or 0)

    def schema(self) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for field in SETTING_FIELDS:
            field_payload = {key: value for key, value in field.items() if key != "default"}
            groups[field["group"]].append(field_payload)
        return [
            {
                **group,
                "fields": groups[group["id"]],
            }
            for group in SETTINGS_GROUPS
        ]

    def read(self) -> dict[str, Any]:
        values = []
        for field in SETTING_FIELDS:
            raw_value = self.get(field["key"])
            values.append(
                {
                    "key": field["key"],
                    "value": _masked_secret(raw_value) if field["secret"] else raw_value,
                    "is_set": bool(raw_value),
                    "is_secret": field["secret"],
                }
            )
        return {
            "groups": self.schema(),
            "values": values,
        }

    def update(self, values: dict[str, str | None]) -> None:
        cleaned: dict[str, str | None] = {}
        for key, value in values.items():
            if key not in FIELD_MAP:
                continue
            field = FIELD_MAP[key]
            if field["secret"] and value in {None, "", "Configured"}:
                continue
            if value is None:
                cleaned[key] = None
                continue
            if isinstance(value, str):
                cleaned[key] = value.strip()
            else:
                cleaned[key] = str(value)
        if cleaned:
            upsert_settings(cleaned)
        refresh_runtime_config()


def get_config_service() -> ConfigService:
    return ConfigService()


def config_value(key: str) -> str:
    return get_config_service().get(key)


def config_optional_value(key: str) -> str | None:
    return get_config_service().get_optional(key)


def config_int_value(key: str) -> int:
    return get_config_service().get_int(key)
