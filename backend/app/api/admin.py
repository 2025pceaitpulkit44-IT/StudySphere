from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.admin import AdminDashboard, Analytics, DoubtAnalytics
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboard)
def dashboard(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_service.admin_dashboard(db, user)


@router.get("/doubts", response_model=DoubtAnalytics)
def doubts(days: int = Query(30, ge=1, le=365), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Aggregated, anonymised view of student questions. No names, emails or user IDs are ever returned."""
    return admin_service.doubt_analytics(db, days)


@router.get("/analytics", response_model=Analytics)
def analytics(days: int = Query(30, ge=7, le=180), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return admin_service.analytics(db, days)
