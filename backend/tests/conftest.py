import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="cicd-platform-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["ARTIFACT_ROOT"] = str(_tmp / "artifacts")
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["EXECUTION_INLINE"] = "true"
os.environ["PLATFORM_API_KEY"] = "test-operator"
os.environ["PLATFORM_VIEWER_KEY"] = "test-viewer"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["GITHUB_TOKEN"] = ""
os.environ["GITHUB_REPOSITORY"] = ""
os.environ["AZURE_ORG"] = ""
os.environ["AZURE_PROJECT"] = ""
os.environ["AZURE_PAT"] = ""
os.environ["NOTIFY_WEBHOOK_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import reset_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

OPERATOR = {"X-API-Key": "test-operator"}
VIEWER = {"X-API-Key": "test-viewer"}


@pytest.fixture
def client():
    reset_settings()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session(client):
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
