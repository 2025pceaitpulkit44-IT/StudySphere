import logging
import random
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Document, DocumentChunk, Event, QuizAttempt, QuizQuestion, StudentProgress, Subject, User
from app.rag.embeddings import EmbeddingError
from app.rag.llm import LLMError, get_llm
from app.rag.quiz_gen import build_quiz_messages, parse_quiz
from app.rag.retriever import retrieve, sample_chunks
from app.schemas.student import QuizQuestionOut, QuizResult, QuizReviewItem, QuizStarted, QuizSubmit
from app.services.student_service import student_department

logger = logging.getLogger("studysphere.quiz")


def start_quiz(db: Session, user: User, subject_id: int, topic: str, n: int) -> QuizStarted:
    dept = student_department(user)
    subject = db.get(Subject, subject_id)
    if not subject or subject.department != dept:
        raise HTTPException(404, "Subject not found.")
    topic = topic.strip()

    try:
        chunks = (retrieve(db, topic, subject_id=subject_id, department=dept, top_k=8) if topic
                  else sample_chunks(db, subject_id=subject_id, department=dept, n=8))
    except EmbeddingError:
        logger.exception("Embedding failed while building a quiz")
        raise HTTPException(503, "The knowledge base is unavailable right now. Please try again shortly.")
    if not chunks:
        raise HTTPException(422, "There isn't enough indexed material for this subject or topic to build a quiz yet.")

    system, user_msg = build_quiz_messages(subject.name, topic, chunks, n)
    try:
        raw = get_llm().generate(system, user_msg)
    except LLMError:
        logger.exception("LLM call failed while building a quiz")
        raise HTTPException(503, "StudySphere AI is unavailable right now. Please try again in a moment.")
    items = parse_quiz(raw, max_source=len(chunks), limit=n)
    if not items:
        raise HTTPException(422, "A quiz couldn't be built from the available material. Try another topic.")

    attempt = QuizAttempt(student_id=user.id, subject_id=subject_id, topic=topic, total=len(items))
    for it in items:
        correct_text = it["options"][it["correct_index"]]
        options = it["options"][:]
        random.shuffle(options)  # models tend to put the right answer first
        attempt.questions.append(QuizQuestion(
            question=it["question"], options=options, correct_index=options.index(correct_text),
            explanation=it["explanation"], source_chunk_id=chunks[it["source"] - 1].chunk_id))
    db.add(attempt)
    db.add(Event(user_id=user.id, event_type="quiz_start", payload={"subject_id": subject_id, "n": len(items)}))
    db.commit()
    db.refresh(attempt)
    # Correct answers and explanations are NOT sent until the quiz is submitted.
    return QuizStarted(attempt_id=attempt.id, subject=subject.name, topic=topic,
                       questions=[QuizQuestionOut(id=q.id, question=q.question, options=q.options) for q in attempt.questions])


def _review(db: Session, attempt: QuizAttempt, subject_name: str) -> QuizResult:
    titles = dict(db.execute(
        select(DocumentChunk.id, Document.title).join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_([q.source_chunk_id for q in attempt.questions if q.source_chunk_id]))))
    review = [
        QuizReviewItem(question=q.question, options=q.options, chosen_index=q.chosen_index, correct_index=q.correct_index,
                       correct=q.chosen_index == q.correct_index, explanation=q.explanation,
                       source=titles.get(q.source_chunk_id))
        for q in attempt.questions
    ]
    score = attempt.score or 0
    return QuizResult(attempt_id=attempt.id, subject=subject_name, topic=attempt.topic, score=score, total=attempt.total,
                      percent=round(score / attempt.total * 100, 1) if attempt.total else 0.0, review=review)


def load_attempt(db: Session, user: User, attempt_id: int) -> QuizAttempt:
    attempt = db.scalar(select(QuizAttempt).where(QuizAttempt.id == attempt_id, QuizAttempt.student_id == user.id)
                        .options(selectinload(QuizAttempt.questions)))
    if not attempt:
        raise HTTPException(404, "Quiz not found.")
    return attempt


def submit_quiz(db: Session, user: User, body: QuizSubmit) -> QuizResult:
    attempt = load_attempt(db, user, body.attempt_id)
    if attempt.submitted_at:
        raise HTTPException(409, "This quiz has already been submitted.")
    by_id = {q.id: q for q in attempt.questions}
    for a in body.answers:
        q = by_id.get(a.question_id)
        if q is None:
            raise HTTPException(422, "An answer refers to a question that is not part of this quiz.")
        if a.chosen_index is not None and not 0 <= a.chosen_index < len(q.options):
            raise HTTPException(422, "An answer refers to an option that does not exist.")
        q.chosen_index = a.chosen_index

    attempt.score = sum(1 for q in attempt.questions if q.chosen_index == q.correct_index)
    attempt.submitted_at = datetime.now(timezone.utc)

    # Per-topic progress: each question counts toward the topic of the document it came from.
    topic_of = dict(db.execute(
        select(DocumentChunk.id, Document.topic).join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_([q.source_chunk_id for q in attempt.questions if q.source_chunk_id]))))
    per_topic: dict[str, list[bool]] = {}
    for q in attempt.questions:
        topic = (topic_of.get(q.source_chunk_id) or attempt.topic or "General").strip() or "General"
        per_topic.setdefault(topic, []).append(q.chosen_index == q.correct_index)
    for topic, results in per_topic.items():
        pct = sum(results) / len(results) * 100
        row = db.scalar(select(StudentProgress).where(
            StudentProgress.student_id == user.id, StudentProgress.subject_id == attempt.subject_id,
            StudentProgress.topic == topic))
        if row is None:
            db.add(StudentProgress(student_id=user.id, subject_id=attempt.subject_id, topic=topic,
                                   quizzes_taken=1, avg_score=pct))
        else:
            n = row.quizzes_taken
            row.avg_score = pct if row.avg_score is None or n == 0 else (row.avg_score * n + pct) / (n + 1)
            row.quizzes_taken = n + 1
    db.add(Event(user_id=user.id, event_type="quiz_submit",
                 payload={"subject_id": attempt.subject_id, "score": attempt.score, "total": attempt.total}))
    db.commit()
    return _review(db, attempt, db.get(Subject, attempt.subject_id).name)
