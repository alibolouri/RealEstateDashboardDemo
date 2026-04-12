from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.realtor import Realtor
from app.schemas.realtor import RealtorResponse


router = APIRouter(prefix="/realtors", tags=["realtors"])


@router.get("", response_model=list[RealtorResponse])
def get_realtors(db: Session = Depends(get_db)) -> list[RealtorResponse]:
    realtors = db.scalars(select(Realtor).order_by(Realtor.id.asc())).all()
    return [RealtorResponse.model_validate(realtor) for realtor in realtors]
