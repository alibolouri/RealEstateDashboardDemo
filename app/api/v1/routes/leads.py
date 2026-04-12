from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin_api
from app.models.lead import Lead
from app.schemas.lead import LeadCreateRequest, LeadResponse, LeadRouteResponse
from app.schemas.realtor import RealtorResponse
from app.services.routing_service import create_routed_lead, decide_realtor
from app.services.settings_service import ensure_lead_routing_enabled


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/route", response_model=LeadRouteResponse)
def route_lead(
    payload: LeadCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LeadRouteResponse:
    require_admin_api(request)
    try:
        ensure_lead_routing_enabled(db)
        lead = create_routed_lead(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    routing = decide_realtor(db, property_id=lead.property_id, city=lead.desired_city)
    return LeadRouteResponse(
        lead_id=lead.id,
        fixed_contact_number=lead.fixed_contact_number,
        assigned_realtor=RealtorResponse.model_validate(routing.realtor),
        routing_reason=routing.reason,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadResponse:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return LeadResponse.model_validate(lead)
