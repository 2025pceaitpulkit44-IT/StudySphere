import os

# Must be set before app modules import settings.
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only-0123456789")
os.environ.setdefault("ADMIN_INVITE_CODE", "TEST-INVITE")
os.environ.setdefault("ALLOWED_EMAIL_DOMAINS", "")
os.environ["EMBEDDING_PROVIDER"] = "hashing"   # offline, deterministic; real model is not downloaded in tests
os.environ["RETRIEVAL_MIN_SCORE"] = "0.10"
import tempfile
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="studysphere_test_uploads_")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://studysphere:studysphere@localhost:5432/studysphere_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.base import Base
from app.database.session import engine
from app.main import app
import app.models  # noqa: F401
from app.ratelimit import limiter


@pytest.fixture(autouse=True)
def fresh_db():
    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.reset()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---------- shared helpers ----------
from app.models import Subject  # noqa: E402

PW = "Passw0rd123"


def _register(client, email, **extra):
    r = client.post("/auth/register", json={"name": "Test User", "email": email, "password": PW,
                                            "department": "CSE", "year": 2, **extra})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def student(client):
    return _register(client, "student@example.edu")


@pytest.fixture
def admin(client):
    return _register(client, "faculty@example.edu", admin_invite_code="TEST-INVITE")


@pytest.fixture
def subject():
    from app.database.session import SessionLocal
    with SessionLocal() as db:
        s = Subject(code="CS201", name="Data Structures", department="CSE", semester=3, units=5)
        db.add(s)
        db.commit()
        return s.id


UNDERTAKING = {
    "institution": "SVKM IT", "faculty_name": "Dr Test", "designation": "Professor",
    "email": "faculty@example.edu", "department": "CSE", "authorization_type": "owner", "accepted": True,
}


@pytest.fixture
def admin_ready(client, admin):
    """An admin who has completed the copyright undertaking."""
    assert client.post("/copyright-undertaking", json=UNDERTAKING, headers=admin).status_code == 201
    return admin


def upload(client, headers, subject_id, content=b"Binary search halves the search range each step. " * 40,
           filename="notes.txt", title="Searching Notes", **over):
    data = {"subject_id": subject_id, "semester": 3, "department": "CSE", "academic_year": "2026-27",
            "material_type": "Lecture Notes", "topic": "Searching", "unit": "Unit 1", "title": title, **over}
    return client.post("/documents/upload", data=data, files={"file": (filename, content)}, headers=headers)
