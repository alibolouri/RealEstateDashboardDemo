from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.schemas.property import PropertyFilterParams


def build_property_query(filters: PropertyFilterParams) -> Select[tuple[Property]]:
    query = select(Property)

    if filters.city:
        query = query.where(Property.city.ilike(filters.city))
    if filters.min_price is not None:
        query = query.where(Property.price >= filters.min_price)
    if filters.max_price is not None:
        query = query.where(Property.price <= filters.max_price)
    if filters.bedrooms is not None:
        query = query.where(Property.bedrooms == filters.bedrooms)
    if filters.bathrooms is not None:
        query = query.where(Property.bathrooms >= filters.bathrooms)
    if filters.property_type:
        query = query.where(Property.property_type.ilike(filters.property_type))
    if filters.status:
        query = query.where(Property.status.ilike(filters.status))

    return query.order_by(Property.price.asc())


def list_properties(db: Session, filters: PropertyFilterParams) -> list[Property]:
    query = build_property_query(filters)
    return list(db.scalars(query).all())


def get_property_by_id(db: Session, property_id: int) -> Property | None:
    return db.get(Property, property_id)
