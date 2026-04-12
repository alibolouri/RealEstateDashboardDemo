from sqlalchemy.orm import Session

from app.models.property import Property
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse, NextStepResponse
from app.schemas.property import PropertyFilterParams, PropertyResponse
from app.schemas.realtor import RealtorResponse
from app.services.property_service import get_property_by_id, list_properties
from app.services.routing_service import decide_realtor
from app.services.settings_service import get_runtime_settings
from app.utils.parser import detect_intent, extract_filters


def _build_summary(intent: str, filters: dict, matched_properties: list[Property]) -> str:
    if intent == "property_search":
        if matched_properties:
            city = filters.get("city")
            city_fragment = f" in {city}" if city else ""
            return f"I found {len(matched_properties)} matching propert{'y' if len(matched_properties) == 1 else 'ies'}{city_fragment} based on your request."
        return "I could not find matching properties with the current filters, but I can still connect you with a realtor to refine the search."

    if intent == "property_detail":
        if matched_properties:
            property_record = matched_properties[0]
            return f"{property_record.title} is available as a {property_record.property_type} in {property_record.city} with {property_record.bedrooms} bedrooms and {property_record.bathrooms} bathrooms."
        return "I need a property ID or a more specific listing reference to provide property details."

    if intent == "contact_request":
        if matched_properties:
            property_record = matched_properties[0]
            return f"I can connect you to the contact flow for {property_record.title} and recommend the best realtor for follow-up."
        return "I can connect you to our platform contact number and assign a realtor even without a specific listing."

    return "I can help with property search, listing details, and routing you to the right realtor."


def _build_next_step_message(intent: str, realtor_name: str) -> str:
    if intent == "property_search":
        return f"Start with the fixed platform line, then {realtor_name} can help narrow down the best options."
    if intent in {"property_detail", "contact_request"}:
        return f"Call the fixed platform number first, and {realtor_name} will assist with the listing follow-up."
    return f"Call the fixed platform number first, and {realtor_name} can help with the next step."


def _resolve_matched_properties(
    db: Session,
    intent: str,
    filters: dict,
) -> list[Property]:
    property_id = filters.get("property_id")
    if property_id is not None and intent in {"property_detail", "contact_request"}:
        property_record = get_property_by_id(db, property_id)
        return [property_record] if property_record is not None else []

    non_property_filters = {
        key: value for key, value in filters.items() if key != "property_id" and value is not None
    }
    if intent in {"property_detail", "contact_request"} and not non_property_filters:
        return []

    property_filters = PropertyFilterParams(
        city=filters.get("city"),
        max_price=filters.get("max_price"),
        min_price=filters.get("min_price"),
        bedrooms=filters.get("bedrooms"),
        bathrooms=filters.get("bathrooms"),
        property_type=filters.get("property_type"),
        status=filters.get("status"),
    )
    return list_properties(db, property_filters)


def handle_chat_query(db: Session, payload: ChatQueryRequest) -> ChatQueryResponse:
    runtime_settings = get_runtime_settings(db)
    intent = detect_intent(payload.message)
    filters = extract_filters(payload.message)

    matched_properties = _resolve_matched_properties(db, intent, filters) if intent != "general_inquiry" else []
    matched_properties = matched_properties[: runtime_settings.chat_result_limit]
    routing_property_id = matched_properties[0].id if matched_properties else filters.get("property_id")
    routing_city = (
        filters.get("city")
        or (matched_properties[0].city if matched_properties else None)
        or runtime_settings.default_desired_city_fallback
    )
    routing = decide_realtor(db, property_id=routing_property_id, city=routing_city)

    next_step = NextStepResponse(
        fixed_contact_number=runtime_settings.fixed_contact_number,
        recommended_realtor=RealtorResponse.model_validate(routing.realtor),
        message=_build_next_step_message(intent, routing.realtor.name),
    )

    return ChatQueryResponse(
        intent=intent,
        filters_detected=filters,
        matched_properties=[PropertyResponse.model_validate(item) for item in matched_properties],
        assistant_summary=_build_summary(intent, filters, matched_properties),
        next_step=next_step,
    )
