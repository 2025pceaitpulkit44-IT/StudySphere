import json
import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Doubt, Event, StudentProgress, Subject, User
from app.rag.embeddings import EmbeddingError
from app.rag.llm import LLMError, cited_numbers, get_llm, parse_llm_json, strip_invalid_citations
from app.rag.prompts import build_messages
from app.rag.retriever import RetrievedChunk, retrieve
from app.schemas.ai import AskResponse, RelevanceOut, SourceOut

logger = logging.getLogger("studysphere.ai")

NOT_FOUND_MESSAGE = "I couldn't find enough information about this topic in the current StudySphere knowledge base."
HIGH, MEDIUM = 0.55, 0.40  # similarity bands for the relevance indicator


def _relevance(score: float) -> RelevanceOut:
    level = "high" if score >= HIGH else "medium" if score >= MEDIUM else "low"
    return RelevanceOut(level=level, score=round(score, 3))


def _sources(chunks: list[RetrievedChunk], cited: set[int]) -> list[SourceOut]:
    """Built only from chunks that were really retrieved - the LLM cannot add or rename a source."""
    by_doc: dict[int, SourceOut] = {}
    for n, c in enumerate(chunks, start=1):
        src = by_doc.get(c.document_id)
        if src is None:
            by_doc[c.document_id] = SourceOut(
                document_id=c.document_id, title=c.title, filename=c.filename, subject=c.subject_name,
                topic=c.topic, unit=c.unit, version=c.version, refs=[n], cited=n in cited,
                score=round(c.score, 3), snippet=c.content[:260].strip(),
            )
        else:
            src.refs.append(n)
            src.cited = src.cited or n in cited
    return sorted(by_doc.values(), key=lambda s: (not s.cited, -s.score))


def _record_progress(db: Session, user: User, subject_id: int | None, topic: str) -> None:
    if not (subject_id and topic.strip()):
        return
    topic = topic.strip()
    row = db.scalar(select(StudentProgress).where(
        StudentProgress.student_id == user.id, StudentProgress.subject_id == subject_id, StudentProgress.topic == topic))
    if row:
        row.doubts_count += 1
    else:
        db.add(StudentProgress(student_id=user.id, subject_id=subject_id, topic=topic, doubts_count=1))


def answer_question(db: Session, user: User, mode: str, question: str, subject_id: int | None,
                    topic: str, save: bool) -> AskResponse:
    department = user.student.department if user.student else None
    subject = db.get(Subject, subject_id) if subject_id else None
    if subject_id and (subject is None or subject.department != department):
        raise HTTPException(404, "Subject not found.")

    topic = topic.strip()
    try:
        chunks = retrieve(db, f"{topic}. {question}" if topic else question,
                          subject_id=subject_id, department=department)
    except EmbeddingError:
        logger.exception("Embedding failed during retrieval")
        raise HTTPException(503, "The knowledge base is unavailable right now. Please try again shortly.")

    answer = explanation = ""
    key_points: list[str] = []
    answerable, sources, relevance = False, [], None

    if chunks:
        system, user_msg = build_messages(mode, subject.name if subject else None, topic, question, chunks)
        try:
            raw = get_llm().generate(system, user_msg)
        except LLMError:
            logger.exception("LLM call failed")
            raise HTTPException(503, "StudySphere AI is unavailable right now. Please try again in a moment.")
        parsed = parse_llm_json(raw)
        if parsed["supported"] and parsed["answer"]:
            n = len(chunks)
            answer = strip_invalid_citations(parsed["answer"], n)
            explanation = strip_invalid_citations(parsed["explanation"], n)
            key_points = [strip_invalid_citations(p, n) for p in parsed["key_points"]]
            answerable = True
            sources = _sources(chunks, cited_numbers(answer, explanation, *key_points))
            relevance = _relevance(max(c.score for c in chunks))

    if not answerable:
        answer = NOT_FOUND_MESSAGE

    doubt_id = None
    if save:
        doubt = Doubt(
            student_id=user.id, subject_id=subject_id, topic=topic, mode=mode, question=question,
            # `answer` holds the structured reply as JSON so the history page can show every part.
            answer=json.dumps({"answer": answer, "explanation": explanation, "key_points": key_points,
                               "relevance": relevance.model_dump() if relevance else None}),
            sources=[s.model_dump() for s in sources], answerable=answerable,
        )
        db.add(doubt)
        db.flush()
        doubt_id = doubt.id
        _record_progress(db, user, subject_id, topic)
    db.add(Event(user_id=user.id, event_type="ai_query",
                 payload={"subject_id": subject_id, "mode": mode, "answerable": answerable}))
    db.commit()

    return AskResponse(mode=mode, answerable=answerable, answer=answer, explanation=explanation,
                       key_points=key_points, sources=sources, relevance=relevance,
                       doubt_id=doubt_id, saved=doubt_id is not None)
