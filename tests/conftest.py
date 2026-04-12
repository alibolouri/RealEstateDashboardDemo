import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB_PATH = Path("test_real_estate.db").resolve()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["FIXED_CONTACT_NUMBER"] = "+1-555-123-4567"
os.environ["DEFAULT_REALTOR_ID"] = "1"
os.environ["APP_ENV"] = "test"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "secret-admin"
os.environ["SESSION_SECRET"] = "test-session-secret"
os.environ["COOKIE_SECURE"] = "false"
os.environ["TRUSTED_HOSTS"] = "testserver,localhost,127.0.0.1"

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402


def extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token not found in HTML response"
    return match.group(1)


def login_dashboard(client: TestClient) -> None:
    login_page = client.get("/dashboard/login")
    csrf_token = extract_csrf_token(login_page.text)
    response = client.post(
        "/dashboard/login",
        data={
            "username": "admin",
            "password": "secret-admin",
            "csrf_token": csrf_token,
            "next_path": "/dashboard",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.fixture()
def client() -> TestClient:
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def authenticated_client(client: TestClient) -> TestClient:
    login_dashboard(client)
    return client
