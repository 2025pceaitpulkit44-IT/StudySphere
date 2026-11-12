from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document, DocumentChunk, DocumentVersion, Subject
from app.models.academic import DOC_INDEXED
from app.rag.embeddings import get_embedder


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    title: str
    filename: str
    subject_id: int
    subject_name: str
    topic: str
    unit: str
    version: int
    content: str
    score: float  # cosine similarity, 1.0 = identical direction


def retrieve(
    db: Session, query: str, *, subject_id: int | None = None, department: str | None = None,
    top_k: int | None = None, min_score: float | None = None,
) -> list[RetrievedChunk]:
    """Nearest chunks to the query among CURRENT, INDEXED document versions only.
    Archived, failed, deleted or half-processed material can never be returned."""
    s = get_settings()
    top_k = top_k or s.retrieval_top_k
    min_score = s.retrieval_min_score if min_score is None else min_score

    qvec = get_embedder().embed_query(query)
    dist = DocumentChunk.embedding.cosine_distance(qvec).label("distance")
    q = (
        select(DocumentChunk, Document, DocumentVersion, Subject, dist)
        .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Subject, Document.subject_id == Subject.id)
        .where(
            DocumentVersion.is_current.is_(True),
            DocumentVersion.status == DOC_INDEXED,
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(dist)
        .limit(top_k)
    )
    if subject_id:
        q = q.where(Document.subject_id == subject_id)
    if department:
        q = q.where(Document.department == department)

    out = []
    for chunk, doc, ver, subj, d in db.execute(q):
        score = 1.0 - float(d)
        if score >= min_score:
            out.append(RetrievedChunk(
                chunk_id=chunk.id, document_id=doc.id, title=doc.title, filename=ver.original_filename,
                subject_id=subj.id, subject_name=subj.name, topic=doc.topic, unit=doc.unit,
                version=ver.version_number, content=chunk.content, score=score,
            ))
    return out


def sample_chunks(db: Session, *, subject_id: int, department: str | None, n: int = 8) -> list[RetrievedChunk]:
    """Random chunks from current, indexed material of a subject (used when a quiz has no specific topic)."""
    from sqlalchemy import func
    q = (
        select(DocumentChunk, Document, DocumentVersion, Subject)
        .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Subject, Document.subject_id == Subject.id)
        .where(DocumentVersion.is_current.is_(True), DocumentVersion.status == DOC_INDEXED, Document.subject_id == subject_id)
        .order_by(func.random())
        .limit(n)
    )
    if department:
        q = q.where(Document.department == department)
    return [
        RetrievedChunk(chunk_id=c.id, document_id=d.id, title=d.title, filename=v.original_filename,
                       subject_id=s.id, subject_name=s.name, topic=d.topic, unit=d.unit,
                       version=v.version_number, content=c.content, score=1.0)
        for c, d, v, s in db.execute(q)
    ]
