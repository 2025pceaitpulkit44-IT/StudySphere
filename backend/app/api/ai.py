from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import require_student
from app.database.session import get_db
from app.models import User
from app.ratelimit import limiter
from app.schemas.ai import AskRequest, AskResponse
from app.services.ai_service import answer_question

router = APIRouter(prefix="/ai", tags=["ai"])


def _handler(mode: str):
    @limiter.limit("30/minute")
    def endpoint(request: Request, body: AskRequest, user: User = Depends(require_student),
                 db: Session = Depends(get_db)) -> AskResponse:
        return answer_question(db, user, mode, body.question.strip(), body.subject_id, body.topic, body.save)
    endpoint.__name__ = f"ai_{mode}"
    return endpoint


for _mode in ("ask", "explain", "solve"):
    router.add_api_route(f"/{_mode}", _handler(_mode), methods=["POST"], response_model=AskResponse)
