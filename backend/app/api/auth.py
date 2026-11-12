import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.database.session import get_db
from app.models import ROLE_ADMIN, ROLE_STUDENT, Admin, Event, Student, User
from app.ratelimit import limiter
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash used to keep login timing similar when the email doesn't exist.
_DUMMY_HASH = hash_password("not-a-real-password-1")


def user_out(user: User) -> UserOut:
    out = UserOut(id=user.id, name=user.full_name, email=user.email, role=user.role)
    if user.student:
        out.department, out.year, out.semester = user.student.department, user.student.year, user.student.semester
    if user.admin:
        out.department, out.designation = user.admin.department, user.admin.designation
    return out


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    s = get_settings()
    email = body.email.lower()

    if s.email_domain_list and email.split("@")[-1] not in s.email_domain_list:
        raise HTTPException(400, "Please register with your college email address.")
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")

    wants_admin = bool(body.admin_invite_code)
    if wants_admin:
        # Admin signup is disabled entirely unless an invite code is configured.
        if not s.admin_invite_code or not secrets.compare_digest(body.admin_invite_code, s.admin_invite_code):
            raise HTTPException(403, "Invalid invitation code.")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.name.strip(),
        role=ROLE_ADMIN if wants_admin else ROLE_STUDENT,
    )
    if wants_admin:
        user.admin = Admin(department=body.department)
    else:
        user.student = Student(department=body.department, year=body.year, semester=body.year * 2 - 1)
    db.add(user)
    db.flush()
    db.add(Event(user_id=user.id, event_type="register", payload={"role": user.role}))
    db.commit()
    db.refresh(user)

    token, ttl = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, expires_in=ttl, user=user_out(user))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise HTTPException(401, "Invalid email or password.")

    db.add(Event(user_id=user.id, event_type="login", payload={}))
    db.commit()
    token, ttl = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, expires_in=ttl, user=user_out(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user)):
    # JWTs are stateless: the client discards the token. It simply expires after
    # JWT_EXPIRE_MINUTES. (A server-side denylist can be added if you need instant revocation.)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)
