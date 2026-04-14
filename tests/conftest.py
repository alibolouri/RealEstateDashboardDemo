import importlib
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(monkeypatch):
    runtime_dir = ROOT / ".test-runtime"
    runtime_dir.mkdir(exist_ok=True)
    db_path = runtime_dir / f"{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BROKERAGE_CONTACT_NUMBER", "+1-800-TEST")
    monkeypatch.setenv("BROKERAGE_NAME", "Test Brokerage")
    monkeypatch.setenv("ASSISTANT_BRAND_NAME", "Test Concierge")
    monkeypatch.setenv("LISTING_SOURCE_MODE", "demo_json")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-pass")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    for module_name in list(sys.modules):
        if module_name.startswith("backend.app"):
            sys.modules.pop(module_name)

    app_module = importlib.import_module("backend.app.main")
    with TestClient(app_module.app) as test_client:
        yield test_client
    database_module = importlib.import_module("backend.app.database")
    database_module.engine.dispose()
    if db_path.exists():
        db_path.unlink(missing_ok=True)
