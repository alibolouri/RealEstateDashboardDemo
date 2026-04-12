from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.property import PropertyFilterParams, PropertyResponse
from app.services.property_service import get_property_by_id, list_properties


router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyResponse])
def get_properties(
    city: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    bedrooms: int | None = None,
    bathrooms: float | None = None,
    property_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[PropertyResponse]:
    filters = PropertyFilterParams(
        city=city,
        max_price=max_price,
        min_price=min_price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        property_type=property_type,
        status=status,
    )
    return [PropertyResponse.model_validate(item) for item in list_properties(db, filters)]


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(property_id: int, db: Session = Depends(get_db)) -> PropertyResponse:
    property_record = get_property_by_id(db, property_id)
    if property_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return PropertyResponse.model_validate(property_record)
