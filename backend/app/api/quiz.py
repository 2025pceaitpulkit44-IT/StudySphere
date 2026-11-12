from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_student
from app.database.session import get_db
from app.models import QuizAttempt, Subject, User
from app.ratelimit import limiter
from app.schemas.student import AttemptSummary, QuizResult, QuizStart, QuizStarted, QuizSubmit
from app.services.quiz_service import _review, load_attempt, start_quiz, submit_quiz

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/start", response_model=QuizStarted)
@limiter.limit("10/minute")
def quiz_start(request: Request, body: QuizStart, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return start_quiz(db, user, body.subject_id, body.topic, body.num_questions)


@router.post("/submit", response_model=QuizResult)
def quiz_submit(body: QuizSubmit, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return submit_quiz(db, user, body)


@router.get("/attempts", response_model=list[AttemptSummary])
def attempts(user: User = Depends(require_student), db: Session = Depends(get_db)):
    rows = db.execute(
        select(QuizAttempt, Subject.name).join(Subject, Subject.id == QuizAttempt.subject_id)
        .where(QuizAttempt.student_id == user.id, QuizAttempt.submitted_at.is_not(None))
        .order_by(QuizAttempt.submitted_at.desc()).limit(30))
    return [AttemptSummary(id=a.id, subject=name, topic=a.topic, score=a.score, total=a.total,
                           percent=round(a.score / a.total * 100, 1) if a.total else None,
                           submitted_at=a.submitted_at, created_at=a.created_at) for a, name in rows]


@router.get("/attempts/{attempt_id}", response_model=QuizResult)
def attempt_review(attempt_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    a = load_attempt(db, user, attempt_id)
    if not a.submitted_at:
        from fastapi import HTTPException
        raise HTTPException(409, "Submit the quiz to see the review.")
    return _review(db, a, db.get(Subject, a.subject_id).name)
