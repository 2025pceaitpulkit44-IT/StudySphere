import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import distinct, func, literal_column, select
from sqlalchemy.orm import Session

from app.api.undertaking import active_undertaking
from app.models import (
    ROLE_STUDENT, Doubt, Document, DocumentChunk, DocumentVersion, Event, QuizAttempt, Subject, User,
)
from app.models.academic import DOC_ARCHIVED, DOC_FAILED, DOC_INDEXED, DOC_PROCESSING, DOC_UPLOADED
from app.schemas.admin import (
    AdminDashboard, Analytics, ConceptStat, CountItem, DayPoint, DoubtAnalytics, QuizSubjectStat, RecentUpload,
    SubjectDoubtStat, TopicDoubtStat, UnansweredQuestion,
)
from app.services.concepts import frequent_terms

MIN_STUDENTS_FOR_CONCEPTS = 2
ACTIVITY_EVENTS = ("login", "ai_query", "quiz_submit")


def _count(db: Session, stmt) -> int:
    return db.scalar(stmt) or 0


def admin_dashboard(db: Session, user: User) -> AdminDashboard:
    by_status = dict(db.execute(select(Document.status, func.count()).group_by(Document.status)).all())
    total = sum(by_status.values())
    indexed = by_status.get(DOC_INDEXED, 0)
    failed = by_status.get(DOC_FAILED, 0)
    processing = by_status.get(DOC_UPLOADED, 0) + by_status.get(DOC_PROCESSING, 0)
    if total == 0:
        kb = "empty"
    elif failed:
        kb = "attention"
    elif processing:
        kb = "updating"
    else:
        kb = "healthy"

    passages = _count(db, select(func.count()).select_from(DocumentChunk)
                      .join(DocumentVersion, DocumentVersion.id == DocumentChunk.version_id)
                      .where(DocumentVersion.is_current.is_(True), DocumentVersion.status == DOC_INDEXED))
    recent = db.execute(
        select(Document, Subject.name).join(Subject, Subject.id == Document.subject_id)
        .order_by(Document.created_at.desc()).limit(5)).all()

    return AdminDashboard(
        total_students=_count(db, select(func.count()).select_from(User).where(User.role == ROLE_STUDENT, User.is_active.is_(True))),
        total_documents=total, indexed_documents=indexed, archived_documents=by_status.get(DOC_ARCHIVED, 0),
        failed_documents=failed, processing_documents=processing, indexed_passages=passages,
        subjects_total=_count(db, select(func.count()).select_from(Subject)),
        subjects_covered=_count(db, select(func.count(distinct(Document.subject_id))).where(Document.status == DOC_INDEXED)),
        total_doubts=_count(db, select(func.count()).select_from(Doubt)),
        unanswered_doubts=_count(db, select(func.count()).select_from(Doubt).where(Doubt.answerable.is_(False))),
        kb_status=kb, undertaking_completed=active_undertaking(db, user.id) is not None,
        recent_uploads=[RecentUpload(id=d.id, title=d.title, subject=sname, status=d.status,
                                     version=len(d.versions), created_at=d.created_at) for d, sname in recent],
    )


# ---------------- doubt analytics (anonymised) ----------------
def doubt_analytics(db: Session, days: int) -> DoubtAnalytics:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    window = Doubt.created_at >= since
    total = _count(db, select(func.count()).select_from(Doubt).where(window))
    unanswered = _count(db, select(func.count()).select_from(Doubt).where(window, Doubt.answerable.is_(False)))

    name = func.coalesce(Subject.name, literal_column("'All subjects'"))  # literal, not a bind param, so GROUP BY matches
    by_subject = [
        SubjectDoubtStat(subject=n, count=c, unanswered=u)
        for n, c, u in db.execute(
            select(name, func.count(), func.count().filter(Doubt.answerable.is_(False)))
            .select_from(Doubt).outerjoin(Subject, Subject.id == Doubt.subject_id)
            .where(window).group_by(name).order_by(func.count().desc()))
    ]
    top_topics = [
        TopicDoubtStat(subject=n, topic=t, count=c)
        for n, t, c in db.execute(
            select(name, Doubt.topic, func.count()).select_from(Doubt).outerjoin(Subject, Subject.id == Doubt.subject_id)
            .where(window, Doubt.topic != "").group_by(name, Doubt.topic).order_by(func.count().desc()).limit(10))
    ]

    rows = db.execute(select(Doubt.student_id, Doubt.question).where(window).order_by(Doubt.created_at.desc()).limit(3000)).all()
    concepts = [ConceptStat(**c) for c in frequent_terms([(sid, q) for sid, q in rows], MIN_STUDENTS_FOR_CONCEPTS)]

    # Unanswered questions are shown WITHOUT any student identity, grouped when several students ask the same thing.
    groups: dict[str, dict] = {}
    for q, subj, topic, ts in db.execute(
        select(Doubt.question, name, Doubt.topic, Doubt.created_at).select_from(Doubt)
        .outerjoin(Subject, Subject.id == Doubt.subject_id)
        .where(window, Doubt.answerable.is_(False)).order_by(Doubt.created_at.desc()).limit(1000)):
        key = " ".join(re.sub(r"[^a-z0-9 ]", " ", q.lower()).split())   # ignore case, punctuation, spacing
        g = groups.setdefault(key, {"question": q.strip(), "subject": subj, "topic": topic, "times_asked": 0, "last_asked": ts})
        g["times_asked"] += 1
    unanswered_list = sorted(groups.values(), key=lambda g: (-g["times_asked"], -g["last_asked"].timestamp()))[:50]

    return DoubtAnalytics(
        days=days, total_questions=total, unanswered=unanswered,
        answer_rate=round((total - unanswered) / total * 100, 1) if total else None,
        by_subject=by_subject, top_topics=top_topics, frequent_concepts=concepts,
        unanswered_questions=[UnansweredQuestion(**g) for g in unanswered_list],
        min_students_for_concepts=MIN_STUDENTS_FOR_CONCEPTS,
    )


# ---------------- analytics ----------------
def _series(db: Session, col, extra_where: list, since: datetime, days: int) -> list[DayPoint]:
    day = func.date_trunc(literal_column("'day'"), col)
    counts = {d.date(): c for d, c in db.execute(select(day, func.count()).where(col >= since, *extra_where).group_by(day))}
    start = since.date()
    return [DayPoint(date=(start + timedelta(days=i)).isoformat(), value=counts.get(start + timedelta(days=i), 0))
            for i in range(days + 1)]


def analytics(db: Session, days: int) -> Analytics:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    active = _count(db, select(func.count(distinct(Event.user_id))).join(User, User.id == Event.user_id)
                    .where(Event.created_at >= since, Event.event_type.in_(ACTIVITY_EVENTS), User.role == ROLE_STUDENT))

    # cumulative documents: everything before the window + daily creations inside it
    before = _count(db, select(func.count()).select_from(Document).where(Document.created_at < since))
    created = _series(db, Document.created_at, [], since, days)
    running, growth = before, []
    for p in created:
        running += p.value
        growth.append(DayPoint(date=p.date, value=running))

    name = func.coalesce(Subject.name, literal_column("'All subjects'"))  # literal, not a bind param, so GROUP BY matches
    top_subjects = [CountItem(label=n, count=c) for n, c in db.execute(
        select(name, func.count()).select_from(Doubt).outerjoin(Subject, Subject.id == Doubt.subject_id)
        .where(Doubt.created_at >= since).group_by(name).order_by(func.count().desc()).limit(8))]
    top_topics = [CountItem(label=t, count=c) for t, c in db.execute(
        select(Doubt.topic, func.count()).where(Doubt.created_at >= since, Doubt.topic != "")
        .group_by(Doubt.topic).order_by(func.count().desc()).limit(8))]

    qwin = (QuizAttempt.submitted_at.is_not(None), QuizAttempt.submitted_at >= since)
    pct = QuizAttempt.score * 100.0 / func.nullif(QuizAttempt.total, 0)
    quiz_by_subject = [QuizSubjectStat(subject=n, attempts=c, avg_percent=round(float(a or 0), 1)) for n, c, a in db.execute(
        select(Subject.name, func.count(), func.avg(pct)).join(Subject, Subject.id == QuizAttempt.subject_id)
        .where(*qwin).group_by(Subject.name).order_by(func.count().desc()))]
    q_total, q_avg = db.execute(select(func.count(), func.avg(pct)).where(*qwin)).one()

    return Analytics(
        days=days, active_students=active,
        total_doubts=_count(db, select(func.count()).select_from(Doubt).where(Doubt.created_at >= since)),
        doubts_per_day=_series(db, Doubt.created_at, [], since, days),
        uploads_per_day=_series(db, Event.created_at, [Event.event_type == "document_upload"], since, days),
        kb_growth=growth, top_subjects=top_subjects, top_topics=top_topics,
        quiz_attempts=q_total, quiz_avg_percent=round(float(q_avg), 1) if q_avg is not None else None,
        quiz_by_subject=quiz_by_subject,
    )
