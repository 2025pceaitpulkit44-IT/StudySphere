from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_student
from app.database.session import get_db
from app.models import ROLE_STUDENT, Subject, User
from app.schemas.documents import SubjectOut
from app.schemas.student import SubjectOverview
from app.services.student_service import subject_overview

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectOut])
def list_subjects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Subject).order_by(Subject.semester, Subject.name)
    if user.role == ROLE_STUDENT and user.student:
        q = q.where(Subject.department == user.student.department)
    return db.scalars(q).all()


@router.get("/overview", response_model=list[SubjectOverview])
def overview(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Subjects with material count and the student's own doubt/quiz numbers (declared before /{subject_id})."""
    return subject_overview(db, user)


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subject = db.get(Subject, subject_id)
    if not subject or (user.role == ROLE_STUDENT and user.student and subject.department != user.student.department):
        raise HTTPException(404, "Subject not found.")
    return subject
