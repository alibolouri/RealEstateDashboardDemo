from typing import Annotated

from fastapi import Query

from app.schemas.common import ORMBaseModel


class PropertyResponse(ORMBaseModel):
    id: int
    title: str
    address: str
    city: str
    state: str
    zip_code: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: int
    property_type: str
    status: str
    short_description: str
    amenities: list[str]
    listing_agent_name: str
    listing_agent_phone: str
    realtor_id: int


class PropertyFilterParams(ORMBaseModel):
    city: str | None = None
    max_price: float | None = None
    min_price: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    property_type: str | None = None
    status: str | None = None


PropertyFiltersDependency = Annotated[
    PropertyFilterParams,
    Query(
        description="Optional filters for property search.",
    ),
]
