from hmac import compare_digest
from secrets import token_urlsafe

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


settings = get_settings()

SESSION_AUTH_KEY = "admin_authenticated"
SESSION_USERNAME_KEY = "admin_username"
SESSION_CSRF_KEY = "csrf_token"
SESSION_FLASH_KEY = "flash_message"


def is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get(SESSION_AUTH_KEY))


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


def validate_csrf_token(request: Request, submitted_token: str | None) -> None:
    session_token = request.session.get(SESSION_CSRF_KEY)
    if not submitted_token or not session_token or not compare_digest(str(submitted_token), str(session_token)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


def authenticate_admin(username: str, password: str) -> bool:
    return compare_digest(username, settings.admin_username) and compare_digest(
        password,
        settings.admin_password,
    )


def login_admin(request: Request) -> None:
    request.session.clear()
    request.session[SESSION_AUTH_KEY] = True
    request.session[SESSION_USERNAME_KEY] = settings.admin_username
    ensure_csrf_token(request)


def logout_admin(request: Request) -> None:
    request.session.clear()


def set_flash_message(request: Request, kind: str, message: str) -> None:
    request.session[SESSION_FLASH_KEY] = {"kind": kind, "message": message}


def pop_flash_message(request: Request) -> dict[str, str] | None:
    return request.session.pop(SESSION_FLASH_KEY, None)


def require_admin_api(request: Request) -> None:
    if not is_admin_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
