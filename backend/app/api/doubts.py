from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_student
from app.database.session import get_db
from app.models import Doubt, Subject, User
from app.schemas.student import DoubtDetail, DoubtSummary
from app.services.student_service import doubt_detail, doubt_summary

router = APIRouter(prefix="/doubts", tags=["doubts"])


def _own(db: Session, user: User, doubt_id: int) -> tuple[Doubt, str | None]:
    row = db.execute(
        select(Doubt, Subject.name).outerjoin(Subject, Subject.id == Doubt.subject_id)
        .where(Doubt.id == doubt_id, Doubt.student_id == user.id)).first()
    if not row:
        raise HTTPException(404, "Doubt not found.")  # same answer whether it doesn't exist or belongs to someone else
    return row


@router.get("", response_model=list[DoubtSummary])
def list_doubts(
    q: str | None = Query(None, max_length=200), subject_id: int | None = None,
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
    user: User = Depends(require_student), db: Session = Depends(get_db),
):
    stmt = (select(Doubt, Subject.name).outerjoin(Subject, Subject.id == Doubt.subject_id)
            .where(Doubt.student_id == user.id).order_by(Doubt.created_at.desc()).limit(limit).offset(offset))
    if q:
        stmt = stmt.where(Doubt.question.icontains(q, autoescape=True))
    if subject_id:
        stmt = stmt.where(Doubt.subject_id == subject_id)
    return [doubt_summary(d, name) for d, name in db.execute(stmt)]


@router.get("/{doubt_id}", response_model=DoubtDetail)
def get_doubt(doubt_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    d, name = _own(db, user, doubt_id)
    return doubt_detail(d, name)


@router.delete("/{doubt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doubt(doubt_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    d, _ = _own(db, user, doubt_id)
    db.delete(d)
    db.commit()
