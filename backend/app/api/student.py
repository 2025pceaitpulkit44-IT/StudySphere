from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_student
from app.database.session import get_db
from app.models import User
from app.schemas.student import Dashboard, SearchResults, TopicProgress
from app.services.student_service import build_dashboard, search_knowledge_base, topic_progress

router = APIRouter(tags=["student"])


@router.get("/dashboard", response_model=Dashboard)
def dashboard(user: User = Depends(require_student), db: Session = Depends(get_db)):
    return build_dashboard(db, user)


@router.get("/progress", response_model=list[TopicProgress])
def progress(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Every topic the student has practised or asked about, most in need of attention first."""
    return topic_progress(db, user)


@router.get("/search", response_model=SearchResults)
def search(q: str = Query(min_length=2, max_length=200), subject_id: int | None = None,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return search_knowledge_base(db, user, q.strip(), subject_id)
