from datetime import datetime

from pydantic import BaseModel


class RecentUpload(BaseModel):
    id: int
    title: str
    subject: str
    status: str
    version: int
    created_at: datetime


class AdminDashboard(BaseModel):
    total_students: int
    total_documents: int
    indexed_documents: int
    archived_documents: int
    failed_documents: int
    processing_documents: int
    indexed_passages: int
    subjects_total: int
    subjects_covered: int
    total_doubts: int
    unanswered_doubts: int
    kb_status: str            # empty | healthy | updating | attention
    undertaking_completed: bool
    recent_uploads: list[RecentUpload]


class CountItem(BaseModel):
    label: str
    count: int


class SubjectDoubtStat(BaseModel):
    subject: str
    count: int
    unanswered: int


class TopicDoubtStat(BaseModel):
    subject: str
    topic: str
    count: int


class ConceptStat(BaseModel):
    term: str
    questions: int
    students: int


class UnansweredQuestion(BaseModel):
    question: str
    subject: str
    topic: str
    times_asked: int
    last_asked: datetime


class DoubtAnalytics(BaseModel):
    days: int
    total_questions: int
    unanswered: int
    answer_rate: float | None
    by_subject: list[SubjectDoubtStat]
    top_topics: list[TopicDoubtStat]
    frequent_concepts: list[ConceptStat]
    unanswered_questions: list[UnansweredQuestion]
    min_students_for_concepts: int


class DayPoint(BaseModel):
    date: str
    value: int


class QuizSubjectStat(BaseModel):
    subject: str
    attempts: int
    avg_percent: float


class Analytics(BaseModel):
    days: int
    active_students: int
    total_doubts: int
    doubts_per_day: list[DayPoint]
    uploads_per_day: list[DayPoint]
    kb_growth: list[DayPoint]          # cumulative number of documents
    top_subjects: list[CountItem]
    top_topics: list[CountItem]
    quiz_attempts: int
    quiz_avg_percent: float | None
    quiz_by_subject: list[QuizSubjectStat]
