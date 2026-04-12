from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.integration_config import IntegrationConfig
from app.models.lead import Lead
from app.models.property import Property
from app.models.realtor import Realtor
from app.schemas.property import PropertyFilterParams
from app.services.property_service import list_properties


def paginate_items(items: list, *, page: int, page_size: int) -> tuple[list, int]:
    total_pages = max(1, ceil(len(items) / page_size)) if items else 1
    normalized_page = max(1, min(page, total_pages))
    start = (normalized_page - 1) * page_size
    end = start + page_size
    return items[start:end], total_pages


def get_dashboard_metrics(db: Session) -> dict[str, int]:
    total_properties = db.scalar(select(func.count(Property.id))) or 0
    active_properties = db.scalar(
        select(func.count(Property.id)).where(Property.status.in_(["for_sale", "for_rent"]))
    ) or 0
    total_leads = db.scalar(select(func.count(Lead.id))) or 0
    total_realtors = db.scalar(select(func.count(Realtor.id))) or 0
    enabled_integrations = db.scalar(
        select(func.count(IntegrationConfig.id)).where(IntegrationConfig.enabled.is_(True))
    ) or 0
    return {
        "total_properties": total_properties,
        "active_properties": active_properties,
        "total_leads": total_leads,
        "total_realtors": total_realtors,
        "enabled_integrations": enabled_integrations,
    }


def get_dashboard_properties(
    db: Session,
    *,
    filters: PropertyFilterParams,
    page: int,
    page_size: int,
) -> tuple[list[Property], int]:
    properties = list_properties(db, filters)
    return paginate_items(properties, page=page, page_size=page_size)


def get_dashboard_leads(
    db: Session,
    *,
    status: str | None,
    city: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Lead], int]:
    statement = (
        select(Lead)
        .options(joinedload(Lead.assigned_realtor), joinedload(Lead.property))
        .order_by(Lead.created_at.desc(), Lead.id.desc())
    )
    if status:
        statement = statement.where(Lead.status.ilike(status))
    if city:
        statement = statement.where(
            or_(
                Lead.desired_city.ilike(city),
                Lead.property.has(Property.city.ilike(city)),
            )
        )
    leads = list(db.scalars(statement).unique().all())
    return paginate_items(leads, page=page, page_size=page_size)


def get_dashboard_realtors(
    db: Session,
    *,
    city: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Realtor], int]:
    statement = select(Realtor).order_by(Realtor.name.asc())
    realtors = list(db.scalars(statement).all())
    if city:
        realtors = [
            realtor
            for realtor in realtors
            if any(covered.lower() == city.lower() for covered in realtor.cities_covered)
        ]
    return paginate_items(realtors, page=page, page_size=page_size)
