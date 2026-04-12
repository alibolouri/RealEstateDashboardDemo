from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import ORMBaseModel
from app.schemas.realtor import RealtorResponse


class LeadCreateRequest(ORMBaseModel):
    user_name: str = Field(min_length=1, max_length=120)
    user_email: EmailStr
    user_phone: str = Field(min_length=7, max_length=32)
    user_question: str = Field(min_length=3, max_length=1000)
    desired_city: str | None = Field(default=None, max_length=80)
    desired_budget: float | None = Field(default=None, ge=0)
    property_id: int | None = Field(default=None, ge=1)


class LeadRouteResponse(ORMBaseModel):
    lead_id: int
    fixed_contact_number: str
    assigned_realtor: RealtorResponse
    routing_reason: str


class LeadResponse(ORMBaseModel):
    id: int
    user_name: str
    user_email: EmailStr
    user_phone: str
    user_question: str
    desired_city: str | None
    desired_budget: float | None
    property_id: int | None
    assigned_realtor_id: int
    fixed_contact_number: str
    status: str
    created_at: datetime
