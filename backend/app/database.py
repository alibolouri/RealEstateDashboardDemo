import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


def _running_on_vercel() -> bool:
    return os.getenv("VERCEL") == "1"


def _normalize_database_url(database_url: str) -> str:
    if not database_url:
        return database_url
    if _running_on_vercel() and database_url.startswith("sqlite:///./"):
        filename = database_url.replace("sqlite:///./", "", 1)
        return f"sqlite:////tmp/{filename}"
    return database_url


def _default_database_url() -> str:
    return _normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./real_estate_concierge.db"))


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


DATABASE_URL = _default_database_url()
engine = create_engine(DATABASE_URL, **_engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Handoff(Base):
    __tablename__ = "handoffs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    listing_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fixed_contact_number: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_realtor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite:///./"):
        Path(DATABASE_URL.replace("sqlite:///", "")).touch(exist_ok=True)
    elif DATABASE_URL.startswith("sqlite:////tmp/"):
        Path(DATABASE_URL.replace("sqlite:////", "/")).touch(exist_ok=True)
    Base.metadata.create_all(bind=engine)


def create_conversation() -> str:
    with SessionLocal() as db:
        conversation = Conversation()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation.id


def conversation_exists(conversation_id: str) -> bool:
    with SessionLocal() as db:
        return db.get(Conversation, conversation_id) is not None


def save_message(conversation_id: str, role: str, content: str, meta: dict | None = None) -> bool:
    with SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            return False
        conversation.updated_at = datetime.now(UTC)
        if role == "user" and conversation.title is None:
            conversation.title = content[:60]
        db.add(
            Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                meta_json=json.dumps(meta, default=str) if meta else None,
            )
        )
        db.commit()
        return True


def get_conversation_history(conversation_id: str, limit: int = 100) -> list[dict]:
    with SessionLocal() as db:
        rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at,
                "meta": json.loads(row.meta_json) if row.meta_json else {},
            }
            for row in rows
        ]


def list_conversations(limit: int = 50) -> list[dict]:
    with SessionLocal() as db:
        rows = db.query(Conversation).order_by(Conversation.updated_at.desc()).limit(limit).all()
        return [
            {
                "id": row.id,
                "title": row.title or "New conversation",
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]


def save_handoff(
    conversation_id: str | None,
    user_message: str | None,
    city: str | None,
    listing_id: str | None,
    fixed_contact_number: str,
    recommended_realtor_id: str,
    reason: str,
) -> str:
    with SessionLocal() as db:
        handoff = Handoff(
            conversation_id=conversation_id,
            user_message=user_message,
            city=city,
            listing_id=listing_id,
            fixed_contact_number=fixed_contact_number,
            recommended_realtor_id=recommended_realtor_id,
            reason=reason,
        )
        db.add(handoff)
        db.commit()
        db.refresh(handoff)
        return handoff.id


def get_settings_map() -> dict[str, str]:
    with SessionLocal() as db:
        try:
            rows = db.query(Setting).all()
        except OperationalError:
            return {}
        return {row.key: row.value for row in rows if row.value is not None}


def get_setting(key: str) -> str | None:
    with SessionLocal() as db:
        row = db.get(Setting, key)
        return row.value if row else None


def upsert_settings(values: dict[str, str | None]) -> None:
    with SessionLocal() as db:
        now = datetime.now(UTC)
        for key, value in values.items():
            row = db.get(Setting, key)
            if row is None:
                row = Setting(key=key, value=value, updated_at=now)
                db.add(row)
            else:
                row.value = value
                row.updated_at = now
        db.commit()
