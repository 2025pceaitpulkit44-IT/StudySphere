from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ai import RelevanceOut, SourceOut
from app.schemas.documents import SubjectOut


class SubjectOverview(SubjectOut):
    material_count: int
    doubts_count: int
    quizzes_taken: int
    avg_score: float | None


class DoubtSummary(BaseModel):
    id: int
    question: str
    subject_id: int | None
    subject: str | None
    topic: str
    mode: str
    answerable: bool
    preview: str
    created_at: datetime


class DoubtDetail(DoubtSummary):
    answer: str
    explanation: str
    key_points: list[str]
    relevance: RelevanceOut | None
    sources: list[SourceOut]


class QuizStart(BaseModel):
    subject_id: int
    topic: str = Field(default="", max_length=160)
    num_questions: int = Field(default=5, ge=3, le=10)


class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: list[str]


class QuizStarted(BaseModel):
    attempt_id: int
    subject: str
    topic: str
    questions: list[QuizQuestionOut]


class AnswerIn(BaseModel):
    question_id: int
    chosen_index: int | None = None


class QuizSubmit(BaseModel):
    attempt_id: int
    answers: list[AnswerIn] = Field(max_length=20)


class QuizReviewItem(BaseModel):
    question: str
    options: list[str]
    chosen_index: int | None
    correct_index: int
    correct: bool
    explanation: str
    source: str | None


class QuizResult(BaseModel):
    attempt_id: int
    subject: str
    topic: str
    score: int
    total: int
    percent: float
    review: list[QuizReviewItem]


class AttemptSummary(BaseModel):
    id: int
    subject: str
    topic: str
    score: int | None
    total: int
    percent: float | None
    submitted_at: datetime | None
    created_at: datetime


class TopicProgress(BaseModel):
    subject_id: int
    subject: str
    topic: str
    doubts_count: int
    quizzes_taken: int
    avg_score: float | None
    status: str
    label: str


class Recommendation(BaseModel):
    kind: str            # practice | read
    title: str
    subtitle: str
    link: str


class Dashboard(BaseModel):
    name: str
    doubts_total: int
    quizzes_taken: int
    avg_score: float | None
    streak_days: int
    recent_doubts: list[DoubtSummary]
    weak_topics: list[TopicProgress]
    recommended: list[Recommendation]
    subjects: list[SubjectOverview]


class SearchDoc(BaseModel):
    document_id: int
    title: str
    subject_id: int
    subject: str
    topic: str
    unit: str
    version: int
    score: float | None
    snippet: str


class SearchResults(BaseModel):
    query: str
    semantic: bool        # False if vector search was unavailable and only title/topic matching ran
    documents: list[SearchDoc]
    subjects: list[SubjectOut]
    topics: list[dict]
