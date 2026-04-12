from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.property import Property
from app.models.realtor import Realtor
from app.schemas.lead import LeadCreateRequest
from app.services.settings_service import get_runtime_settings
from app.utils.constants import LEAD_STATUS_ROUTED
from app.utils.parser import normalize_city


@dataclass
class RoutingDecision:
    realtor: Realtor
    reason: str


def get_default_realtor(db: Session) -> Realtor:
    runtime_settings = get_runtime_settings(db)
    realtor = db.get(Realtor, runtime_settings.default_realtor_id)
    if realtor is not None:
        return realtor

    fallback = db.scalar(select(Realtor).order_by(Realtor.id.asc()))
    if fallback is None:
        raise ValueError("No realtors available for routing.")
    return fallback


def _match_realtor_by_city(db: Session, city: str | None) -> Realtor | None:
    runtime_settings = get_runtime_settings(db)
    normalized_city = normalize_city(city or runtime_settings.default_desired_city_fallback)
    if not normalized_city:
        return None

    realtors = db.scalars(select(Realtor).order_by(Realtor.id.asc())).all()
    for realtor in realtors:
        if any(covered.lower() == normalized_city.lower() for covered in realtor.cities_covered):
            return realtor
    return None


def decide_realtor(
    db: Session,
    *,
    property_id: int | None = None,
    city: str | None = None,
) -> RoutingDecision:
    if property_id is not None:
        property_record = db.get(Property, property_id)
        if property_record is not None:
            realtor = db.get(Realtor, property_record.realtor_id)
            if realtor is not None:
                return RoutingDecision(realtor=realtor, reason="Matched by property realtor_id")

    city_realtor = _match_realtor_by_city(db, city)
    if city_realtor is not None:
        return RoutingDecision(realtor=city_realtor, reason="Matched by city coverage")

    return RoutingDecision(realtor=get_default_realtor(db), reason="Assigned default realtor")


def create_routed_lead(db: Session, payload: LeadCreateRequest) -> Lead:
    if payload.property_id is not None and db.get(Property, payload.property_id) is None:
        raise ValueError("Property not found")

    runtime_settings = get_runtime_settings(db)
    decision = decide_realtor(db, property_id=payload.property_id, city=payload.desired_city)
    lead = Lead(
        user_name=payload.user_name,
        user_email=str(payload.user_email),
        user_phone=payload.user_phone,
        user_question=payload.user_question,
        desired_city=normalize_city(payload.desired_city),
        desired_budget=payload.desired_budget,
        property_id=payload.property_id,
        assigned_realtor_id=decision.realtor.id,
        fixed_contact_number=runtime_settings.fixed_contact_number,
        status=LEAD_STATUS_ROUTED,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead
