from app.auth.dependencies import require_admin, require_student
from app.main import app

STUDENT = {"name": "Test Student", "email": "s1@example.edu", "password": "Passw0rd123",
           "department": "CSE", "year": 2}


def register(client, **over):
    return client.post("/auth/register", json={**STUDENT, **over})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me(client):
    r = register(client)
    assert r.status_code == 201 and r.json()["user"]["role"] == "student"
    r = client.post("/auth/login", json={"email": STUDENT["email"], "password": STUDENT["password"]})
    assert r.status_code == 200
    me = client.get("/auth/me", headers=auth(r.json()["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == STUDENT["email"]


def test_wrong_password_is_rejected(client):
    register(client)
    r = client.post("/auth/login", json={"email": STUDENT["email"], "password": "WrongPass123"})
    assert r.status_code == 401


def test_duplicate_email_rejected(client):
    register(client)
    assert register(client).status_code == 409


def test_passwords_are_hashed(client):
    from sqlalchemy import select
    from app.database.session import SessionLocal
    from app.models import User
    register(client)
    with SessionLocal() as db:
        u = db.scalar(select(User))
        assert u.password_hash != STUDENT["password"] and u.password_hash.startswith("$argon2")


def test_nobody_becomes_admin_with_wrong_code(client):
    assert register(client, admin_invite_code="guess").status_code == 403


def test_admin_signup_with_valid_invite(client):
    r = register(client, email="fac@example.edu", admin_invite_code="TEST-INVITE")
    assert r.status_code == 201 and r.json()["user"]["role"] == "admin"


def test_no_token_is_401(client):
    assert client.get("/auth/me").status_code == 401


def test_garbage_token_is_401(client):
    assert client.get("/auth/me", headers=auth("not.a.jwt")).status_code == 401


def test_role_guards(client):
    """Student tokens must be refused on admin-only routes, and vice versa."""
    from fastapi import Depends

    @app.get("/_t/admin-only")
    def a(user=Depends(require_admin)):
        return {"ok": True}

    @app.get("/_t/student-only")
    def s(user=Depends(require_student)):
        return {"ok": True}

    st = register(client).json()["access_token"]
    ad = register(client, email="fac@example.edu", admin_invite_code="TEST-INVITE").json()["access_token"]
    assert client.get("/_t/admin-only", headers=auth(st)).status_code == 403
    assert client.get("/_t/admin-only", headers=auth(ad)).status_code == 200
    assert client.get("/_t/student-only", headers=auth(ad)).status_code == 403
    assert client.get("/_t/student-only", headers=auth(st)).status_code == 200
