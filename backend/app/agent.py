import json
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from backend.app.config import config_optional_value, config_value
from backend.app.connectors import active_connector_summary, assistant_brand, brokerage_name
from backend.app.database import get_conversation_history, save_handoff, save_message
from backend.app.models import AgentAnalysis, AgentContext, AgentEnvelope
from backend.app.tools import (
    get_handoff_policy,
    get_listing_details,
    interpret_query,
    listing_cards,
    recommend_agent,
    search_guidance,
    search_listings,
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


SYSTEM_PROMPT = """You are a white-label real-estate concierge for a brokerage website.
Use listing sources, guidance sources, and routing policy to answer clearly.
Never invent listing facts. When human assistance is requested, provide the fixed brokerage number first and the recommended realtor second.
Keep responses concise, confident, and operationally useful.
"""


class AgentState(TypedDict):
    conversation_id: str
    user_message: str
    analysis: dict[str, Any]
    context: dict[str, Any]
    response: str
    sources: list[dict[str, Any]]
    listing_results: list[dict[str, Any]]
    handoff: dict[str, Any] | None
    data_status: str | None


def _llm_available() -> bool:
    return ChatOpenAI is not None and StateGraph is not None and bool(config_optional_value("OPENAI_API_KEY"))


def _analysis_node(state: AgentState) -> AgentState:
    history = get_conversation_history(state["conversation_id"])
    recent_user_context = " ".join(message["content"] for message in history[-4:] if message["role"] == "user")
    merged_message = f"{recent_user_context}\n{state['user_message']}" if recent_user_context else state["user_message"]
    state["analysis"] = interpret_query(merged_message)
    return state


def _source(type_: str, label: str, *, data_status: str = "demo", confidence: float = 1.0) -> dict[str, Any]:
    return {
        "type": type_,
        "label": label,
        "timestamp": None,
        "confidence": confidence,
        "data_status": data_status,
    }


def _tool_node(state: AgentState) -> AgentState:
    analysis = AgentAnalysis(**state["analysis"])
    connector_summary = active_connector_summary()
    listings: list[dict[str, Any]] = []
    listing_detail: dict[str, Any] | None = None
    guidance_hits: list[dict[str, Any]] = []
    handoff: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = []

    if analysis.intent in {"listing_search", "buying_guidance", "renting_guidance", "handoff_request"}:
        listings = search_listings(
            city=analysis.city,
            max_price=analysis.max_price,
            min_price=analysis.min_price,
            bedrooms=analysis.bedrooms,
            bathrooms=analysis.bathrooms,
            property_type=analysis.property_type,
            listing_type=analysis.listing_type,
            status=analysis.status,
        )
        if listings:
            sources.append(_source("listing_source", listings[0]["source"], data_status=listings[0]["data_status"]))

    if analysis.intent == "listing_detail":
        listing_id = analysis.listing_id or (listings[0]["id"] if listings else None)
        if listing_id:
            listing_detail = get_listing_details(listing_id)
            if listing_detail:
                listings = [listing_detail]
                sources.append(_source("listing_source", f"{listing_detail['source']} detail", data_status=listing_detail["data_status"]))

    if analysis.intent in {"buying_guidance", "renting_guidance", "selling_guidance", "area_question", "general_real_estate_qna"}:
        guidance_hits = search_guidance(state["user_message"], topic=analysis.topic)
        if guidance_hits:
            sources.append(
                _source(
                    "knowledge_source",
                    f"Guidance source: {connector_summary['knowledge']['active_mode']}",
                    confidence=0.92,
                )
            )

    if analysis.needs_handoff or analysis.intent == "handoff_request":
        listing_id = analysis.listing_id or (listings[0]["id"] if listings else None)
        city = analysis.city or (listings[0]["city"] if listings else None)
        realtor, reason = recommend_agent(city=city, listing_id=listing_id)
        policy = get_handoff_policy()
        handoff = {
            "fixed_contact_number": policy["fixed_contact_number"],
            "recommended_realtor": realtor,
            "reason": reason,
            "next_step_message": (
                f"Call {brokerage_name()} first at {policy['fixed_contact_number']}, "
                f"then ask for {realtor['name']} for local follow-up."
            ),
        }
        sources.append(
            _source(
                "routing_source",
                f"Routing source: {connector_summary['routing']['active_mode']}",
                confidence=1.0,
            )
        )

    data_status = "demo"
    if listings:
        data_status = listings[0]["data_status"]
    elif sources:
        data_status = sources[0]["data_status"]

    state["context"] = AgentContext(
        analysis=analysis,
        listings=listings,
        listing_detail=listing_detail,
        guidance_hits=guidance_hits,
        handoff=handoff,
    ).model_dump()
    state["sources"] = sources
    state["listing_results"] = listing_cards(listings)
    state["handoff"] = handoff
    state["data_status"] = data_status
    return state


def _deterministic_response(state: AgentState) -> str:
    analysis = AgentAnalysis(**state["analysis"])
    context = AgentContext(**state["context"])

    if context.listing_detail:
        detail = context.listing_detail
        price_text = f"${detail['price']}/night" if detail["listing_type"] == "short_stay" else f"${detail['price']:,}"
        return (
            f"{detail['title']} in {detail['city']} is an active {detail['listing_type'].replace('_', ' ')} listing from "
            f"{detail['source']}. It is a {detail['bedrooms']}-bedroom, {detail['bathrooms']}-bath {detail['property_type']} "
            f"priced at {price_text}. {detail['short_description']}"
        )

    if context.listings:
        intro = f"I found {len(context.listings)} relevant listing"
        intro += "s" if len(context.listings) != 1 else ""
        filters = []
        if analysis.city:
            filters.append(f"in {analysis.city}")
        if analysis.max_price:
            filters.append(f"under ${analysis.max_price:,}")
        if analysis.bedrooms:
            filters.append(f"with at least {analysis.bedrooms:g} bedrooms")
        lead = f"{intro} {' '.join(filters)}.".replace(" .", ".")
        highlights = " ".join(
            f"{row['title']} is {'$'+str(row['price'])+'/night' if row['listing_type']=='short_stay' else '$'+format(row['price'], ',')}."
            for row in context.listings[:3]
        )
        return f"{lead} {highlights}".strip()

    if context.guidance_hits:
        return " ".join(hit["content"] for hit in context.guidance_hits[:2])

    if analysis.needs_handoff and context.handoff:
        return (
            f"I can connect you with a human specialist. Start with {brokerage_name()}, "
            "then continue with the recommended local realtor."
        )

    return (
        "I can help with listing search, buying, renting, selling, neighborhood guidance, "
        "and human handoff. Ask for a city, budget, bedrooms, listing type, or request a realtor."
    )


def _respond_node(state: AgentState) -> AgentState:
    llm_response = None
    if _llm_available():
        model = ChatOpenAI(api_key=config_optional_value("OPENAI_API_KEY"), model=config_value("OPENAI_MODEL"), temperature=0)
        prompt = (
            f"{SYSTEM_PROMPT}\n\nAssistant brand: {assistant_brand()}\nBrokerage name: {brokerage_name()}\n\n"
            f"User message: {state['user_message']}\n\n"
            f"Structured context:\n{json.dumps(state['context'], indent=2, default=str)}\n\n"
            "Write a concise response. Mention source-backed facts only when they exist. "
            "If results are demo-backed, avoid calling them live MLS results."
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
        "listing_results": [],
        "handoff": None,
        "data_status": None,
    }
    if GRAPH is not None:
        return GRAPH.invoke(base_state)
    return _respond_node(_tool_node(_analysis_node(base_state)))


def _to_envelope(state: AgentState) -> AgentEnvelope:
    return AgentEnvelope(
        response=state["response"],
        sources=state["sources"],
        listing_results=state["listing_results"],
        handoff=state["handoff"],
        data_status=state["data_status"],
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
            listing_id=envelope.analysis.listing_id,
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
            listing_id=envelope.analysis.listing_id,
            fixed_contact_number=envelope.handoff.fixed_contact_number,
            recommended_realtor_id=envelope.handoff.recommended_realtor.id,
            reason=envelope.handoff.reason,
        )
    yield {"meta": envelope.model_dump(exclude={"response", "analysis"})}


def create_handoff(conversation_id: str | None, message: str | None, city: str | None, listing_id: str | None) -> dict[str, Any]:
    realtor, reason = recommend_agent(city=city, listing_id=listing_id)
    policy = get_handoff_policy()
    handoff = {
        "fixed_contact_number": policy["fixed_contact_number"],
        "recommended_realtor": realtor,
        "reason": reason,
        "next_step_message": f"Call {brokerage_name()} at {policy['fixed_contact_number']}, then continue with {realtor['name']}.",
    }
    handoff_id = save_handoff(
        conversation_id=conversation_id,
        user_message=message,
        city=city,
        listing_id=listing_id,
        fixed_contact_number=policy["fixed_contact_number"],
        recommended_realtor_id=realtor["id"],
        reason=reason,
    )
    return {"handoff_id": handoff_id, **handoff}
