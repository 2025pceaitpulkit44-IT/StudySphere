from tests.conftest import UNDERTAKING, upload


def test_upload_blocked_without_undertaking(client, admin, subject):
    r = upload(client, admin, subject)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "undertaking_required"


def test_status_false_before_and_true_after(client, admin):
    assert client.get("/copyright-undertaking/status", headers=admin).json()["completed"] is False
    assert client.post("/copyright-undertaking", json=UNDERTAKING, headers=admin).status_code == 201
    st = client.get("/copyright-undertaking/status", headers=admin).json()
    assert st["completed"] is True and st["record"]["institution"] == "SVKM IT"
    assert "legitimate educational and study purposes" in st["declaration"]


def test_must_accept_declaration(client, admin):
    r = client.post("/copyright-undertaking", json={**UNDERTAKING, "accepted": False}, headers=admin)
    assert r.status_code == 400


def test_invalid_authorization_type_rejected(client, admin):
    r = client.post("/copyright-undertaking", json={**UNDERTAKING, "authorization_type": "whatever"}, headers=admin)
    assert r.status_code == 422


def test_student_cannot_use_undertaking_or_upload(client, student, subject):
    assert client.post("/copyright-undertaking", json=UNDERTAKING, headers=student).status_code == 403
    assert client.get("/copyright-undertaking/status", headers=student).status_code == 403
    assert upload(client, student, subject).status_code == 403


def test_undertaking_is_stored_with_declaration_text(client, admin):
    from sqlalchemy import select
    from app.database.session import SessionLocal
    from app.models import CopyrightUndertaking
    client.post("/copyright-undertaking", json=UNDERTAKING, headers=admin)
    with SessionLocal() as db:
        rec = db.scalar(select(CopyrightUndertaking))
        assert rec.status == "active" and rec.authorization_type == "owner"
        assert rec.declaration_text.startswith("I confirm that the academic material")


def test_resubmission_supersedes_previous(client, admin):
    from sqlalchemy import select
    from app.database.session import SessionLocal
    from app.models import CopyrightUndertaking
    client.post("/copyright-undertaking", json=UNDERTAKING, headers=admin)
    client.post("/copyright-undertaking", json={**UNDERTAKING, "authorization_type": "permission"}, headers=admin)
    with SessionLocal() as db:
        statuses = sorted(r.status for r in db.scalars(select(CopyrightUndertaking)))
    assert statuses == ["active", "superseded"]
