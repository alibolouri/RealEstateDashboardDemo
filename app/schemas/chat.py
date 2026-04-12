from typing import Any

from pydantic import EmailStr, Field

from app.schemas.common import ORMBaseModel
from app.schemas.property import PropertyResponse
from app.schemas.realtor import RealtorResponse


class ChatQueryRequest(ORMBaseModel):
    message: str = Field(min_length=3, max_length=1000)
    user_name: str = Field(min_length=1, max_length=120)
    user_email: EmailStr
    user_phone: str = Field(min_length=7, max_length=32)


class NextStepResponse(ORMBaseModel):
    fixed_contact_number: str
    recommended_realtor: RealtorResponse
    message: str


class ChatQueryResponse(ORMBaseModel):
    intent: str
    filters_detected: dict[str, Any]
    matched_properties: list[PropertyResponse]
    assistant_summary: str
    next_step: NextStepResponse
