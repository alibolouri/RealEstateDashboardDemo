from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.chat_service import handle_chat_query


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def query_chat(payload: ChatQueryRequest, db: Session = Depends(get_db)) -> ChatQueryResponse:
    return handle_chat_query(db, payload)
