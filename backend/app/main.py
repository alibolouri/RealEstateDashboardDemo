import json
import os
from hmac import compare_digest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.app.agent import create_handoff, run_agent, stream_agent
from backend.app.config import get_config_service
from backend.app.connectors import active_connector_summary, assistant_brand, brokerage_name, invalidate_source_caches, listing_source_mode
from backend.app.database import conversation_exists, create_conversation, get_conversation_history, init_db, list_conversations
from backend.app.models import (
    AdminLoginRequest,
    AdminSessionResponse,
    ConversationHistoryResponse,
    ConversationResponse,
    HealthResponse,
    HandoffRequest,
    HandoffResponse,
    MessageHistory,
    MessageRequest,
    MessageResponse,
    SettingsReadResponse,
    SettingsSchemaResponse,
    SettingsUpdateRequest,
)
from backend.app.tools import get_listing_details, listing_cards


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme-demo-only")
SESSION_SECRET = os.getenv("SESSION_SECRET", "local-demo-session-secret")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

LEGACY_SOURCE_MAP = {
    "property_data": "listing_source",
    "market_knowledge": "knowledge_source",
    "routing_policy": "routing_source",
}


def _normalize_sources(sources: list[dict]) -> list[dict]:
    normalized = []
    for source in sources:
        source_type = LEGACY_SOURCE_MAP.get(source.get("type"), source.get("type", "knowledge_source"))
        normalized.append(
            {
                "type": source_type,
                "label": source.get("label", "Unknown source"),
                "timestamp": source.get("timestamp"),
                "confidence": source.get("confidence", 1.0),
                "data_status": source.get("data_status", "demo"),
            }
        )
    return normalized


def _normalize_listing_results(meta: dict) -> list[dict]:
    listing_results = meta.get("listing_results")
    if listing_results:
        return listing_results

    property_results = meta.get("property_results") or []
    if not property_results:
        return []

    enriched = []
    for property_result in property_results:
        listing_id = property_result.get("id")
        if not listing_id:
            continue
        listing = get_listing_details(listing_id)
        if listing:
            enriched.extend(listing_cards([listing]))
    return enriched


def _normalize_handoff(handoff: dict | None) -> dict | None:
    if not handoff:
        return None

    next_step_message = handoff.get("next_step_message", "")
    if "Doorviser" in next_step_message:
        recommended = handoff.get("recommended_realtor", {})
        handoff = {
            **handoff,
            "next_step_message": (
                f"Start with {brokerage_name()} at {handoff.get('fixed_contact_number', '')}, "
                f"then continue with {recommended.get('name', 'the recommended realtor')}."
            ).strip()
        }
    return handoff


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
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=False)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept


def _frontend_entry() -> FileResponse | RedirectResponse:
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


def _require_admin(request: Request) -> str:
    username = request.session.get("admin_username")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required")
    return username


def _config():
    return get_config_service()


@app.get("/", include_in_schema=False)
async def serve_frontend_root():
    return _frontend_entry()


@app.get("/settings", response_model=SettingsReadResponse)
async def settings_index(request: Request):
    if _wants_html(request):
        return _frontend_entry()
    _require_admin(request)
    return SettingsReadResponse.model_validate(_config().read())


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    summary = active_connector_summary()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        listing_source_mode=listing_source_mode(),
        assistant_brand=assistant_brand(),
        brokerage_name=brokerage_name(),
        active_listing_mode=summary["listing"]["active_mode"],
        active_knowledge_mode=summary["knowledge"]["active_mode"],
        active_routing_mode=summary["routing"]["active_mode"],
        listing_fallback_modes=summary["listing"]["fallback_modes"],
        knowledge_fallback_modes=summary["knowledge"]["fallback_modes"],
        routing_fallback_modes=summary["routing"]["fallback_modes"],
        connector_status=summary,
    )


@app.get("/settings/schema", response_model=SettingsSchemaResponse)
async def settings_schema(request: Request) -> SettingsSchemaResponse:
    _require_admin(request)
    return SettingsSchemaResponse.model_validate({"groups": _config().schema()})


@app.put("/settings", response_model=SettingsReadResponse)
async def update_settings(request: Request, payload: SettingsUpdateRequest) -> SettingsReadResponse:
    _require_admin(request)
    _config().update(payload.values)
    invalidate_source_caches()
    return SettingsReadResponse.model_validate(_config().read())


@app.post("/admin/login", response_model=AdminSessionResponse)
async def admin_login(request: Request, credentials: AdminLoginRequest) -> AdminSessionResponse:
    if not compare_digest(credentials.username, ADMIN_USERNAME) or not compare_digest(credentials.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
    request.session["admin_username"] = credentials.username
    return AdminSessionResponse(authenticated=True, username=credentials.username)


@app.post("/admin/logout", response_model=AdminSessionResponse)
async def admin_logout(request: Request) -> AdminSessionResponse:
    request.session.clear()
    return AdminSessionResponse(authenticated=False, username=None)


@app.get("/admin/session", response_model=AdminSessionResponse)
async def admin_session(request: Request) -> AdminSessionResponse:
    username = request.session.get("admin_username")
    return AdminSessionResponse(authenticated=bool(username), username=username)


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
            sources=_normalize_sources(row["meta"].get("sources", [])),
            listing_results=_normalize_listing_results(row["meta"]),
            handoff=_normalize_handoff(row["meta"].get("handoff")),
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
