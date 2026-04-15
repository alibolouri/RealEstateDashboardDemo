from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DataStatus = Literal["live", "cached", "demo"]
SourceType = Literal["listing_source", "knowledge_source", "routing_source"]


class SourceCitation(BaseModel):
    type: SourceType
    label: str
    url: str | None = None
    timestamp: datetime | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    data_status: DataStatus = "demo"


class RealtorCard(BaseModel):
    id: str
    name: str
    phone: str
    email: str
    specialty: str
    cities_covered: list[str]
    brokerage: str


class ListingCard(BaseModel):
    id: str
    source: str
    external_id: str
    title: str
    address: str
    city: str
    state: str
    zip_code: str
    price: int
    listing_type: str
    property_type: str
    status: str
    bedrooms: float
    bathrooms: float
    square_feet: int | None = None
    short_description: str
    image_url: str | None = None
    brokerage: str | None = None
    url: str | None = None
    last_synced_at: datetime | None = None
    provenance: str
    data_status: DataStatus = "demo"


class HandoffCard(BaseModel):
    fixed_contact_number: str
    recommended_realtor: RealtorCard
    reason: str
    next_step_message: str


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    response: str
    conversation_id: str
    sources: list[SourceCitation] = Field(default_factory=list)
    listing_results: list[ListingCard] = Field(default_factory=list)
    handoff: HandoffCard | None = None
    data_status: DataStatus | None = None


class ConversationResponse(BaseModel):
    conversation_id: str


class MessageHistory(BaseModel):
    role: str
    content: str
    created_at: datetime
    sources: list[SourceCitation] = Field(default_factory=list)
    listing_results: list[ListingCard] = Field(default_factory=list)
    handoff: HandoffCard | None = None
    data_status: DataStatus | None = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[MessageHistory]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    listing_source_mode: str
    assistant_brand: str
    brokerage_name: str
    active_listing_mode: str | None = None
    active_knowledge_mode: str | None = None
    active_routing_mode: str | None = None
    listing_fallback_modes: list[str] = Field(default_factory=list)
    knowledge_fallback_modes: list[str] = Field(default_factory=list)
    routing_fallback_modes: list[str] = Field(default_factory=list)
    connector_status: dict[str, Any] = Field(default_factory=dict)


class HandoffRequest(BaseModel):
    conversation_id: str | None = None
    message: str | None = None
    city: str | None = None
    listing_id: str | None = None


class HandoffResponse(BaseModel):
    handoff_id: str
    fixed_contact_number: str
    recommended_realtor: RealtorCard
    reason: str
    next_step_message: str


class AgentAnalysis(BaseModel):
    intent: str
    city: str | None = None
    max_price: int | None = None
    min_price: int | None = None
    bedrooms: float | None = None
    bathrooms: float | None = None
    property_type: str | None = None
    listing_type: str | None = None
    status: str | None = None
    listing_id: str | None = None
    needs_handoff: bool = False
    topic: str | None = None


class AgentEnvelope(BaseModel):
    response: str
    sources: list[SourceCitation] = Field(default_factory=list)
    listing_results: list[ListingCard] = Field(default_factory=list)
    handoff: HandoffCard | None = None
    data_status: DataStatus | None = None
    analysis: AgentAnalysis


class AgentContext(BaseModel):
    analysis: AgentAnalysis
    listings: list[dict[str, Any]] = Field(default_factory=list)
    listing_detail: dict[str, Any] | None = None
    guidance_hits: list[dict[str, Any]] = Field(default_factory=list)
    handoff: dict[str, Any] | None = None


class SettingOption(BaseModel):
    value: str
    label: str


class SettingField(BaseModel):
    key: str
    label: str
    group: str
    kind: str
    required: bool = False
    secret: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    options: list[SettingOption] = Field(default_factory=list)


class SettingGroup(BaseModel):
    id: str
    label: str
    description: str | None = None
    fields: list[SettingField] = Field(default_factory=list)


class SettingValue(BaseModel):
    key: str
    value: str | None = None
    is_set: bool
    is_secret: bool


class SettingsSchemaResponse(BaseModel):
    groups: list[SettingGroup]


class SettingsReadResponse(BaseModel):
    groups: list[SettingGroup]
    values: list[SettingValue]


class SettingsUpdateRequest(BaseModel):
    values: dict[str, str | None] = Field(default_factory=dict)


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminSessionResponse(BaseModel):
    authenticated: bool
    username: str | None = None
    role: str | None = None
    can_manage_settings: bool = False
