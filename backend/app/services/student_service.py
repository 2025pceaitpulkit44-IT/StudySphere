import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Doubt, Document, QuizAttempt, StudentProgress, Subject, User
from app.models.academic import DOC_INDEXED
from app.rag.embeddings import EmbeddingError
from app.rag.retriever import retrieve
from app.schemas.ai import RelevanceOut, SourceOut
from app.schemas.documents import SubjectOut
from app.schemas.student import (
    Dashboard, DoubtDetail, DoubtSummary, Recommendation, SearchDoc, SearchResults, SubjectOverview, TopicProgress,
)
from app.services.topic_status import LABELS, WEAK_STATUSES, classify_topic, streak_days

SEVERITY = {"needs_revision": 0, "practice": 1, "improving": 2, "good": 3, "new": 4}


def student_department(user: User) -> str:
    if not user.student:
        raise HTTPException(403, "This feature is for students.")
    return user.student.department


# ---------------- doubts ----------------
def _parsed_answer(raw: str) -> dict:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {"answer": raw or "", "explanation": "", "key_points": [], "relevance": None}


def doubt_summary(d: Doubt, subject_name: str | None) -> DoubtSummary:
    answer = _parsed_answer(d.answer).get("answer", "")
    return DoubtSummary(
        id=d.id, question=d.question, subject_id=d.subject_id, subject=subject_name, topic=d.topic, mode=d.mode,
        answerable=d.answerable, preview=answer[:160], created_at=d.created_at,
    )


def doubt_detail(d: Doubt, subject_name: str | None) -> DoubtDetail:
    p = _parsed_answer(d.answer)
    rel = p.get("relevance")
    return DoubtDetail(
        **doubt_summary(d, subject_name).model_dump(),
        answer=p.get("answer", ""), explanation=p.get("explanation", ""), key_points=p.get("key_points", []),
        relevance=RelevanceOut(**rel) if rel else None,
        sources=[SourceOut(**s) for s in (d.sources or [])],
    )


# ---------------- subjects overview ----------------
def subject_overview(db: Session, user: User) -> list[SubjectOverview]:
    dept = student_department(user)
    subjects = db.scalars(select(Subject).where(Subject.department == dept).order_by(Subject.semester, Subject.name)).all()
    materials = dict(db.execute(
        select(Document.subject_id, func.count()).where(Document.status == DOC_INDEXED, Document.department == dept)
        .group_by(Document.subject_id)).all())
    doubts = dict(db.execute(
        select(Doubt.subject_id, func.count()).where(Doubt.student_id == user.id).group_by(Doubt.subject_id)).all())
    quiz = {sid: (n, avg) for sid, n, avg in db.execute(
        select(QuizAttempt.subject_id, func.count(),
               func.avg(QuizAttempt.score * 100.0 / func.nullif(QuizAttempt.total, 0)))
        .where(QuizAttempt.student_id == user.id, QuizAttempt.submitted_at.is_not(None))
        .group_by(QuizAttempt.subject_id))}
    out = []
    for s in subjects:
        n, avg = quiz.get(s.id, (0, None))
        out.append(SubjectOverview(
            **SubjectOut.model_validate(s, from_attributes=True).model_dump(),
            material_count=materials.get(s.id, 0), doubts_count=doubts.get(s.id, 0),
            quizzes_taken=n, avg_score=round(float(avg), 1) if avg is not None else None))
    return out


# ---------------- progress / weak topics ----------------
def topic_progress(db: Session, user: User) -> list[TopicProgress]:
    rows = db.execute(
        select(StudentProgress, Subject.name).join(Subject, Subject.id == StudentProgress.subject_id)
        .where(StudentProgress.student_id == user.id)).all()
    recent: dict[tuple, list[float]] = defaultdict(list)
    for sid, topic, score, total in db.execute(
        select(QuizAttempt.subject_id, QuizAttempt.topic, QuizAttempt.score, QuizAttempt.total)
        .where(QuizAttempt.student_id == user.id, QuizAttempt.submitted_at.is_not(None), QuizAttempt.topic != "")
        .order_by(QuizAttempt.submitted_at)):
        if total:
            recent[(sid, topic)].append(score / total * 100)

    out = []
    for p, sname in rows:
        status = classify_topic(p.doubts_count, p.quizzes_taken, p.avg_score, recent.get((p.subject_id, p.topic)))
        out.append(TopicProgress(
            subject_id=p.subject_id, subject=sname, topic=p.topic, doubts_count=p.doubts_count,
            quizzes_taken=p.quizzes_taken, avg_score=round(p.avg_score, 1) if p.avg_score is not None else None,
            status=status, label=LABELS[status]))
    out.sort(key=lambda t: (SEVERITY[t.status], -t.doubts_count, t.topic))
    return out


# ---------------- dashboard ----------------
def build_dashboard(db: Session, user: User) -> Dashboard:
    dept = student_department(user)
    doubts_total = db.scalar(select(func.count()).select_from(Doubt).where(Doubt.student_id == user.id)) or 0
    quizzes, avg = db.execute(
        select(func.count(), func.avg(QuizAttempt.score * 100.0 / func.nullif(QuizAttempt.total, 0)))
        .where(QuizAttempt.student_id == user.id, QuizAttempt.submitted_at.is_not(None))).one()

    recent = db.execute(
        select(Doubt, Subject.name).outerjoin(Subject, Subject.id == Doubt.subject_id)
        .where(Doubt.student_id == user.id).order_by(Doubt.created_at.desc()).limit(5)).all()

    weak = [t for t in topic_progress(db, user) if t.status in WEAK_STATUSES][:4]

    recommended = [
        Recommendation(kind="practice", title=f"Practice {t.topic}", subtitle=f"{t.subject} · {t.label}",
                       link=f"/quiz?subject={t.subject_id}&topic={quote(t.topic)}")
        for t in weak[:3]
    ]
    newest = db.execute(
        select(Document, Subject.name).join(Subject, Subject.id == Document.subject_id)
        .where(Document.status == DOC_INDEXED, Document.department == dept)
        .order_by(Document.created_at.desc()).limit(3)).all()
    recommended += [
        Recommendation(kind="read", title=d.title, subtitle=f"{sname} · {d.material_type}", link=f"/subjects/{d.subject_id}")
        for d, sname in newest
    ]

    since = datetime.now(timezone.utc) - timedelta(days=90)
    dates = {d.date() for (d,) in db.execute(select(Doubt.created_at).where(Doubt.student_id == user.id, Doubt.created_at >= since))}
    dates |= {d.date() for (d,) in db.execute(
        select(QuizAttempt.submitted_at).where(QuizAttempt.student_id == user.id, QuizAttempt.submitted_at >= since))}

    return Dashboard(
        name=user.full_name, doubts_total=doubts_total, quizzes_taken=quizzes or 0,
        avg_score=round(float(avg), 1) if avg is not None else None,
        streak_days=streak_days(dates, datetime.now(timezone.utc).date()),
        recent_doubts=[doubt_summary(d, sname) for d, sname in recent],
        weak_topics=weak, recommended=recommended, subjects=subject_overview(db, user))


# ---------------- global search ----------------
def search_knowledge_base(db: Session, user: User, q: str, subject_id: int | None) -> SearchResults:
    dept = user.student.department if user.student else None
    semantic = True
    try:
        hits = retrieve(db, q, subject_id=subject_id, department=dept, top_k=12)
    except EmbeddingError:
        hits, semantic = [], False

    docs: dict[int, SearchDoc] = {}
    for h in hits:
        if h.document_id not in docs:
            docs[h.document_id] = SearchDoc(
                document_id=h.document_id, title=h.title, subject_id=h.subject_id, subject=h.subject_name,
                topic=h.topic, unit=h.unit, version=h.version, score=round(h.score, 3), snippet=h.content[:240].strip())

    # Plain title/topic matches, so an exact name always finds its document even if the vector match is weak.
    base = (select(Document, Subject.name).join(Subject, Subject.id == Document.subject_id)
            .where(Document.status == DOC_INDEXED))
    if dept:
        base = base.where(Document.department == dept)
    if subject_id:
        base = base.where(Document.subject_id == subject_id)
    lexical = base.where(Document.title.icontains(q, autoescape=True) | Document.topic.icontains(q, autoescape=True))
    for d, sname in db.execute(lexical.limit(20)):
        docs.setdefault(d.id, SearchDoc(document_id=d.id, title=d.title, subject_id=d.subject_id, subject=sname,
                                        topic=d.topic, unit=d.unit, version=len(d.versions), score=None, snippet=""))

    subj_q = select(Subject).where(Subject.name.icontains(q, autoescape=True) | Subject.code.icontains(q, autoescape=True))
    if dept:
        subj_q = subj_q.where(Subject.department == dept)
    subjects = [SubjectOut.model_validate(s, from_attributes=True) for s in db.scalars(subj_q.limit(10))]

    topics = [{"subject_id": sid, "subject": sname, "topic": t} for t, sid, sname in db.execute(
        select(Document.topic, Document.subject_id, Subject.name).join(Subject, Subject.id == Document.subject_id)
        .where(Document.status == DOC_INDEXED, Document.topic != "", Document.topic.icontains(q, autoescape=True),
               *( [Document.department == dept] if dept else [] ))
        .distinct().limit(10))]

    ordered = sorted(docs.values(), key=lambda d: (d.score is None, -(d.score or 0)))
    return SearchResults(query=q, semantic=semantic, documents=ordered, subjects=subjects, topics=topics)
