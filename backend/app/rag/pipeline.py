"""Document processing pipeline: extract -> clean -> chunk -> embed -> index.

Runs in a FastAPI background task with its own DB session. The current stage is written to the
database after every step so the UI shows real progress. A version only becomes searchable
(status "indexed", is_current) once every chunk has an embedding.
"""
import logging
from pathlib import Path

from sqlalchemy import delete, select

from app.config import get_settings
from app.database.session import SessionLocal
from app.models.academic import (
    DOC_ARCHIVED, DOC_FAILED, DOC_INDEXED, DOC_PROCESSING, Document, DocumentChunk, DocumentVersion,
)
from app.rag.chunker import chunk_text
from app.rag.cleaner import clean_text
from app.rag.embeddings import EmbeddingError, check_dimension, get_embedder
from app.rag.extractors import ExtractionError, extract_text

logger = logging.getLogger("studysphere.pipeline")
MIN_CHARS = 20
EMBED_BATCH = 32


def upload_root() -> Path:
    return Path(get_settings().upload_dir).resolve()


def _stage(db, version: DocumentVersion, stage: str) -> None:
    version.stage = stage
    version.status = DOC_PROCESSING
    db.commit()


def refresh_document_status(doc: Document) -> None:
    """Document status follows its live version, so a failed re-upload doesn't hide the working one."""
    current = next((v for v in doc.versions if v.is_current), None)
    if current:
        doc.status = current.status
    elif doc.versions:
        doc.status = doc.versions[-1].status


def _fail(db, version_id: int, message: str) -> None:
    db.rollback()
    version = db.get(DocumentVersion, version_id)
    if version is None:
        return
    version.status = DOC_FAILED  # `stage` is left as-is so the UI can show where it failed
    version.error_message = message
    refresh_document_status(version.document)
    db.commit()


def process_version(version_id: int) -> None:
    db = SessionLocal()
    try:
        version = db.get(DocumentVersion, version_id)
        if version is None:
            return
        doc = version.document
        path = upload_root() / version.stored_path
        if not path.exists():
            raise ExtractionError("The stored file is missing. Please upload it again.")

        _stage(db, version, "extracting")
        raw = extract_text(path, Path(version.stored_path).suffix)

        _stage(db, version, "cleaning")
        text = clean_text(raw)
        if len(text) < MIN_CHARS:
            raise ExtractionError("This file contains too little readable text to index.")

        _stage(db, version, "chunking")
        pieces = chunk_text(text)
        db.execute(delete(DocumentChunk).where(DocumentChunk.version_id == version.id))
        db.add_all(
            DocumentChunk(document_id=doc.id, version_id=version.id, subject_id=doc.subject_id,
                          chunk_index=i, content=piece, token_count=len(piece.split()))
            for i, piece in enumerate(pieces)
        )
        db.commit()

        _stage(db, version, "embedding")
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.version_id == version.id).order_by(DocumentChunk.chunk_index)
        ).all()
        embedder = get_embedder()
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[i:i + EMBED_BATCH]
            vectors = embedder.embed_documents([c.content for c in batch])
            check_dimension(vectors)
            for chunk, vec in zip(batch, vectors):
                chunk.embedding = vec
        db.commit()

        _stage(db, version, "indexing")
        # Only now, with the new version fully embedded, retire the previous live version.
        for old in doc.versions:
            if old.id != version.id and old.is_current:
                db.execute(delete(DocumentChunk).where(DocumentChunk.version_id == old.id))
                old.is_current = False
                old.status = DOC_ARCHIVED
                old.chunk_count = 0
        version.is_current = True
        version.chunk_count = len(chunks)
        version.stage = "indexed"
        version.status = DOC_INDEXED
        version.error_message = ""
        refresh_document_status(doc)
        db.commit()
    except (ExtractionError, EmbeddingError) as exc:
        _fail(db, version_id, str(exc))
    except Exception:
        logger.exception("Processing failed for version %s", version_id)
        _fail(db, version_id, "Processing failed. Please try again or upload the file again.")
    finally:
        db.close()
