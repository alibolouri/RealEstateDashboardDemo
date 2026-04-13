from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    type: Literal["property_data", "market_knowledge", "routing_policy"]
    label: str


class RealtorCard(BaseModel):
    id: str
    name: str
    phone: str
    email: str
    specialty: str
    cities_covered: list[str]
    brokerage: str


class PropertyCard(BaseModel):
    id: str
    title: str
    city: str
    state: str
    price: int
    listing_type: str
    property_type: str
    bedrooms: float
    bathrooms: float
    short_description: str
    image_url: str | None = None


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
    property_results: list[PropertyCard] = Field(default_factory=list)
    handoff: HandoffCard | None = None


class ConversationResponse(BaseModel):
    conversation_id: str


class MessageHistory(BaseModel):
    role: str
    content: str
    created_at: datetime
    sources: list[SourceCitation] = Field(default_factory=list)
    property_results: list[PropertyCard] = Field(default_factory=list)
    handoff: HandoffCard | None = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[MessageHistory]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class HandoffRequest(BaseModel):
    conversation_id: str | None = None
    message: str | None = None
    city: str | None = None
    property_id: str | None = None


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
    property_id: str | None = None
    needs_handoff: bool = False
    topic: str | None = None


class AgentEnvelope(BaseModel):
    response: str
    sources: list[SourceCitation] = Field(default_factory=list)
    property_results: list[PropertyCard] = Field(default_factory=list)
    handoff: HandoffCard | None = None
    analysis: AgentAnalysis


class AgentContext(BaseModel):
    analysis: AgentAnalysis
    properties: list[dict[str, Any]] = Field(default_factory=list)
    property_detail: dict[str, Any] | None = None
    knowledge_hits: list[dict[str, Any]] = Field(default_factory=list)
    handoff: dict[str, Any] | None = None
