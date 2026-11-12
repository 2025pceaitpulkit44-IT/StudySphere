from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models import CopyrightUndertaking, Event, User
from app.schemas.undertaking import UndertakingIn, UndertakingRecord, UndertakingStatus

router = APIRouter(prefix="/copyright-undertaking", tags=["copyright"])

# The server owns the exact wording; the stored record keeps a copy of the text that was accepted.
DECLARATION_TEXT = (
    "I confirm that the academic material I upload to StudySphere is owned by the institution/uploader "
    "or is being used with appropriate permission. I confirm that the material is uploaded for legitimate "
    "educational and study purposes within the institution. I understand that StudySphere should not be "
    "used to distribute material without the required rights or authorization."
)


def active_undertaking(db: Session, user_id: int) -> CopyrightUndertaking | None:
    return db.scalar(
        select(CopyrightUndertaking)
        .where(CopyrightUndertaking.user_id == user_id, CopyrightUndertaking.status == "active")
        .order_by(CopyrightUndertaking.accepted_at.desc())
    )


def require_undertaking(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> User:
    """Dependency for upload endpoints: admins may upload only after a completed undertaking."""
    if not active_undertaking(db, user.id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "undertaking_required", "message": "Copyright undertaking required before uploading material."},
        )
    return user


@router.get("/status", response_model=UndertakingStatus)
def undertaking_status(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rec = active_undertaking(db, user.id)
    return UndertakingStatus(
        completed=rec is not None,
        declaration=DECLARATION_TEXT,
        record=UndertakingRecord.model_validate(rec, from_attributes=True) if rec else None,
    )


@router.post("", response_model=UndertakingStatus, status_code=status.HTTP_201_CREATED)
def submit_undertaking(
    request: Request, body: UndertakingIn, user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    if not body.accepted:
        raise HTTPException(400, "You must accept the undertaking to continue.")

    # A new submission supersedes earlier ones.
    db.execute(
        update(CopyrightUndertaking)
        .where(CopyrightUndertaking.user_id == user.id, CopyrightUndertaking.status == "active")
        .values(status="superseded")
    )
    rec = CopyrightUndertaking(
        user_id=user.id,
        institution=body.institution.strip(),
        faculty_name=body.faculty_name.strip(),
        designation=body.designation.strip(),
        email=body.email.lower(),
        department=body.department.strip(),
        authorization_type=body.authorization_type,
        declaration_text=DECLARATION_TEXT,
        # IP is kept as an audit trail of who accepted the undertaking; disclose this in your privacy notice.
        ip_address=request.client.host if request.client else "",
        status="active",
    )
    db.add(rec)
    db.add(Event(user_id=user.id, event_type="undertaking_accepted", payload={"type": body.authorization_type}))
    db.commit()
    db.refresh(rec)
    return UndertakingStatus(
        completed=True,
        declaration=DECLARATION_TEXT,
        record=UndertakingRecord.model_validate(rec, from_attributes=True),
    )
