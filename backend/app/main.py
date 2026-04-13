import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.app.agent import create_handoff, run_agent, stream_agent
from backend.app.connectors import assistant_brand, brokerage_name, listing_source_mode
from backend.app.database import conversation_exists, create_conversation, get_conversation_history, init_db, list_conversations
from backend.app.models import ConversationHistoryResponse, ConversationResponse, HealthResponse, HandoffRequest, HandoffResponse, MessageHistory, MessageRequest, MessageResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="White-Label Real-Estate Concierge API",
    description="Streaming conversational assistant for listing discovery, guidance, and brokerage handoff",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/", include_in_schema=False)
async def serve_frontend_root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        listing_source_mode=listing_source_mode(),
        assistant_brand=assistant_brand(),
        brokerage_name=brokerage_name(),
    )


@app.get("/conversations")
async def conversations_index():
    return {"conversations": list_conversations()}


@app.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_new_conversation() -> ConversationResponse:
    return ConversationResponse(conversation_id=create_conversation())


@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, request: MessageRequest) -> MessageResponse:
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    envelope = run_agent(conversation_id, request.message)
    return MessageResponse(
        response=envelope.response,
        conversation_id=conversation_id,
        sources=envelope.sources,
        listing_results=envelope.listing_results,
        handoff=envelope.handoff,
        data_status=envelope.data_status,
    )


@app.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(conversation_id: str, request: MessageRequest):
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_generator():
        async for payload in stream_agent(conversation_id, request.message):
            yield f"data: {json.dumps(payload, default=str)}\n\n"
        yield f"data: {json.dumps({'done': True}, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_history(conversation_id: str, limit: int = 100) -> ConversationHistoryResponse:
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    rows = get_conversation_history(conversation_id, limit=limit)
    messages = [
        MessageHistory(
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
            sources=row["meta"].get("sources", []),
            listing_results=row["meta"].get("listing_results", []),
            handoff=row["meta"].get("handoff"),
            data_status=row["meta"].get("data_status"),
        )
        for row in rows
    ]
    return ConversationHistoryResponse(conversation_id=conversation_id, messages=messages)


@app.post("/handoff", response_model=HandoffResponse, status_code=status.HTTP_201_CREATED)
async def request_handoff(request: HandoffRequest) -> HandoffResponse:
    return HandoffResponse(
        **create_handoff(
            conversation_id=request.conversation_id,
            message=request.message,
            city=request.city,
            listing_id=request.listing_id,
        )
    )
