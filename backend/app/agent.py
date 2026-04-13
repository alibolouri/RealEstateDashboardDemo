import json
import os
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from backend.app.database import get_conversation_history, save_handoff, save_message
from backend.app.models import AgentAnalysis, AgentContext, AgentEnvelope
from backend.app.tools import (
    get_doorviser_contact,
    get_property_details,
    interpret_query,
    property_cards,
    recommend_realtor,
    search_market_knowledge,
    search_properties,
)

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    END = None
    StateGraph = None

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None


SYSTEM_PROMPT = """You are Doorviser AI, a high-trust real-estate concierge.
Use property data and Doorviser knowledge to answer questions clearly.
Never invent listing facts. If human assistance is requested, give the Doorviser number first and the realtor second.
"""


class AgentState(TypedDict):
    conversation_id: str
    user_message: str
    analysis: dict[str, Any]
    context: dict[str, Any]
    response: str
    sources: list[dict[str, str]]
    property_results: list[dict[str, Any]]
    handoff: dict[str, Any] | None


def _llm_available() -> bool:
    return ChatOpenAI is not None and StateGraph is not None and bool(os.getenv("OPENAI_API_KEY"))


def _analysis_node(state: AgentState) -> AgentState:
    history = get_conversation_history(state["conversation_id"])
    recent_user_context = " ".join(message["content"] for message in history[-4:] if message["role"] == "user")
    merged_message = f"{recent_user_context}\n{state['user_message']}" if recent_user_context else state["user_message"]
    state["analysis"] = interpret_query(merged_message)
    return state


def _tool_node(state: AgentState) -> AgentState:
    analysis = AgentAnalysis(**state["analysis"])
    properties: list[dict[str, Any]] = []
    property_detail: dict[str, Any] | None = None
    knowledge_hits: list[dict[str, Any]] = []
    handoff: dict[str, Any] | None = None
    sources: list[dict[str, str]] = []

    if analysis.intent in {"property_search", "buying_guidance", "renting_guidance", "contact_request"}:
        properties = search_properties(
            city=analysis.city,
            max_price=analysis.max_price,
            min_price=analysis.min_price,
            bedrooms=analysis.bedrooms,
            bathrooms=analysis.bathrooms,
            property_type=analysis.property_type,
            listing_type=analysis.listing_type,
            status=analysis.status,
        )
        if properties:
            sources.append({"type": "property_data", "label": "Matched property dataset"})

    if analysis.intent == "property_detail":
        property_id = analysis.property_id or (properties[0]["id"] if properties else None)
        if property_id:
            property_detail = get_property_details(property_id)
            if property_detail:
                properties = [property_detail]
                sources.append({"type": "property_data", "label": f"Property detail for {property_id}"})

    if analysis.intent in {"buying_guidance", "renting_guidance", "selling_guidance", "area_question", "general_real_estate_qna"}:
        knowledge_hits = search_market_knowledge(state["user_message"], topic=analysis.topic)
        if knowledge_hits:
            sources.append({"type": "market_knowledge", "label": "Doorviser guidance knowledge"})

    if analysis.needs_handoff or analysis.intent == "contact_request":
        property_id = analysis.property_id or (properties[0]["id"] if properties else None)
        city = analysis.city or (properties[0]["city"] if properties else None)
        realtor, reason = recommend_realtor(city=city, property_id=property_id)
        contact = get_doorviser_contact()
        handoff = {
            "fixed_contact_number": contact["fixed_contact_number"],
            "recommended_realtor": realtor,
            "reason": reason,
            "next_step_message": f"Start with Doorviser at {contact['fixed_contact_number']}, then ask for {realtor['name']} for focused follow-up.",
        }
        sources.append({"type": "routing_policy", "label": "Doorviser routing policy"})

    state["context"] = AgentContext(
        analysis=analysis,
        properties=properties,
        property_detail=property_detail,
        knowledge_hits=knowledge_hits,
        handoff=handoff,
    ).model_dump()
    state["sources"] = sources
    state["property_results"] = property_cards(properties)
    state["handoff"] = handoff
    return state


def _deterministic_response(state: AgentState) -> str:
    analysis = AgentAnalysis(**state["analysis"])
    context = AgentContext(**state["context"])

    if context.property_detail:
        detail = context.property_detail
        price_text = f"${detail['nightly_rate']}/night" if detail["listing_type"] == "short_stay" else f"${detail['price']:,}"
        return (
            f"{detail['title']} in {detail['city']} is an active {detail['listing_type'].replace('_', ' ')} listing. "
            f"It is a {detail['bedrooms']}-bedroom, {detail['bathrooms']}-bath {detail['property_type']} priced at {price_text}. "
            f"{detail['short_description']}"
        )

    if context.properties:
        intro = f"I found {len(context.properties)} relevant option"
        intro += "s" if len(context.properties) != 1 else ""
        filters = []
        if analysis.city:
            filters.append(f"in {analysis.city}")
        if analysis.max_price:
            filters.append(f"under ${analysis.max_price:,}")
        if analysis.bedrooms:
            filters.append(f"with at least {analysis.bedrooms:g} bedrooms")
        lead = f"{intro} {' '.join(filters)}.".replace(" .", ".")
        highlights = " ".join(
            f"{row['title']} is {'$'+str(row['nightly_rate'])+'/night' if row['listing_type']=='short_stay' else '$'+format(row['price'], ',')}."
            for row in context.properties[:3]
        )
        return f"{lead} {highlights}".strip()

    if context.knowledge_hits:
        return " ".join(hit["content"] for hit in context.knowledge_hits[:2])

    if analysis.needs_handoff and context.handoff:
        return "I can connect you with a human specialist. Start with Doorviser, then continue with the recommended local realtor."

    return "I can help with buying, renting, selling, area guidance, and specific property questions. Try asking for a city, budget, beds, or whether you want a sale, lease, or short stay."


def _respond_node(state: AgentState) -> AgentState:
    llm_response = None
    if _llm_available():
        model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
        prompt = (
            f"{SYSTEM_PROMPT}\n\nUser message: {state['user_message']}\n\n"
            f"Structured context:\n{json.dumps(state['context'], indent=2)}\n\n"
            "Write a concise, practical response for the user."
        )
        try:
            llm_response = model.invoke(prompt).content
        except Exception:
            llm_response = None
    state["response"] = llm_response or _deterministic_response(state)
    return state


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("analyze", _analysis_node)
    graph.add_node("tools", _tool_node)
    graph.add_node("respond", _respond_node)
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "tools")
    graph.add_edge("tools", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


GRAPH = _build_graph() if StateGraph is not None else None


def _run_state(conversation_id: str, user_message: str) -> AgentState:
    base_state: AgentState = {
        "conversation_id": conversation_id,
        "user_message": user_message,
        "analysis": {},
        "context": {},
        "response": "",
        "sources": [],
        "property_results": [],
        "handoff": None,
    }
    if GRAPH is not None:
        return GRAPH.invoke(base_state)
    return _respond_node(_tool_node(_analysis_node(base_state)))


def _to_envelope(state: AgentState) -> AgentEnvelope:
    return AgentEnvelope(
        response=state["response"],
        sources=state["sources"],
        property_results=state["property_results"],
        handoff=state["handoff"],
        analysis=state["analysis"],
    )


def run_agent(conversation_id: str, user_message: str) -> AgentEnvelope:
    save_message(conversation_id, "user", user_message)
    state = _run_state(conversation_id, user_message)
    envelope = _to_envelope(state)
    save_message(conversation_id, "assistant", envelope.response, meta=envelope.model_dump(exclude={"response", "analysis"}))
    if envelope.handoff:
        save_handoff(
            conversation_id=conversation_id,
            user_message=user_message,
            city=envelope.analysis.city,
            property_id=envelope.analysis.property_id,
            fixed_contact_number=envelope.handoff.fixed_contact_number,
            recommended_realtor_id=envelope.handoff.recommended_realtor.id,
            reason=envelope.handoff.reason,
        )
    return envelope


async def stream_agent(conversation_id: str, user_message: str) -> AsyncIterator[dict[str, Any]]:
    save_message(conversation_id, "user", user_message)
    state = _run_state(conversation_id, user_message)
    envelope = _to_envelope(state)
    for word in envelope.response.split():
        yield {"chunk": f"{word} "}
    save_message(conversation_id, "assistant", envelope.response, meta=envelope.model_dump(exclude={"response", "analysis"}))
    if envelope.handoff:
        save_handoff(
            conversation_id=conversation_id,
            user_message=user_message,
            city=envelope.analysis.city,
            property_id=envelope.analysis.property_id,
            fixed_contact_number=envelope.handoff.fixed_contact_number,
            recommended_realtor_id=envelope.handoff.recommended_realtor.id,
            reason=envelope.handoff.reason,
        )
    yield {"meta": envelope.model_dump(exclude={"response", "analysis"})}


def create_handoff(conversation_id: str | None, message: str | None, city: str | None, property_id: str | None) -> dict[str, Any]:
    realtor, reason = recommend_realtor(city=city, property_id=property_id)
    contact = get_doorviser_contact()
    handoff = {
        "fixed_contact_number": contact["fixed_contact_number"],
        "recommended_realtor": realtor,
        "reason": reason,
        "next_step_message": f"Start with Doorviser at {contact['fixed_contact_number']}, then continue with {realtor['name']}.",
    }
    handoff_id = save_handoff(
        conversation_id=conversation_id,
        user_message=message,
        city=city,
        property_id=property_id,
        fixed_contact_number=contact["fixed_contact_number"],
        recommended_realtor_id=realtor["id"],
        reason=reason,
    )
    return {"handoff_id": handoff_id, **handoff}
