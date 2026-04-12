from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.services.integration_service import (
    SECRET_FIELD_TYPES,
    get_non_secret_field_value,
    has_secret_value,
)


BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def format_datetime(value) -> str:
    if not value:
        return "Not available"
    return value.strftime("%Y-%m-%d %I:%M %p")


def status_tone(value: str | None) -> str:
    normalized = (value or "").lower()
    if normalized in {"configured", "for_sale", "for_rent", "ok", "routed"}:
        return "good"
    if normalized in {"pending", "needs_attention", "saved_disabled"}:
        return "warn"
    if normalized in {"not_configured", "disabled", "sold"}:
        return "muted"
    return "neutral"


templates.env.filters["datetime"] = format_datetime
templates.env.filters["status_tone"] = status_tone
templates.env.globals["secret_field_types"] = SECRET_FIELD_TYPES
templates.env.globals["has_secret_value"] = has_secret_value
templates.env.globals["get_non_secret_field_value"] = get_non_secret_field_value
