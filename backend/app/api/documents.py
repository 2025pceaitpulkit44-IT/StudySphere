import logging
import re
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user, require_admin
from app.api.undertaking import require_undertaking
from app.config import get_settings
from app.database.session import get_db
from app.models import ROLE_ADMIN, Document, DocumentVersion, Event, Subject, User
from app.models.academic import DOC_ARCHIVED, DOC_INDEXED, DOC_PROCESSING, DOC_UPLOADED
from app.rag.pipeline import process_version, refresh_document_status, upload_root
from app.ratelimit import limiter
from app.schemas.documents import DocumentOut, SubjectOut, VersionOut
from app.services.document_service import MATERIAL_TYPES, UploadError, delete_stored_file, store_upload

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger("studysphere.documents")


def to_out(doc: Document) -> DocumentOut:
    latest = doc.versions[-1] if doc.versions else None
    current = next((v for v in doc.versions if v.is_current), None)
    return DocumentOut(
        id=doc.id, title=doc.title, subject=SubjectOut.model_validate(doc.subject, from_attributes=True),
        material_type=doc.material_type, topic=doc.topic, unit=doc.unit, department=doc.department,
        semester=doc.semester, academic_year=doc.academic_year,
        status=latest.status if latest else doc.status,
        stage=latest.stage if latest else "",
        error_message=latest.error_message if latest else "",
        version=latest.version_number if latest else 0,
        chunk_count=current.chunk_count if current else 0,
        uploader_name=doc.uploader.full_name if doc.uploader else "",
        original_filename=latest.original_filename if latest else "",
        created_at=doc.created_at,
        versions=[VersionOut.model_validate(v, from_attributes=True) for v in doc.versions],
    )


def _load(db: Session, doc_id: int) -> Document:
    doc = db.scalar(
        select(Document).where(Document.id == doc_id)
        .options(selectinload(Document.versions), selectinload(Document.subject))
        .execution_options(populate_existing=True)  # never serve a stale version list from the session cache
    )
    if not doc:
        raise HTTPException(404, "Document not found.")
    return doc


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/hour")
def upload_document(
    request: Request,
    background: BackgroundTasks,
    subject_id: int = Form(...),
    semester: int = Form(..., ge=1, le=8),
    department: str = Form(..., min_length=2, max_length=120),
    academic_year: str = Form(..., pattern=r"^\d{4}-\d{2}$"),
    material_type: str = Form(...),
    topic: str = Form("", max_length=160),
    unit: str = Form("", max_length=32),
    title: str = Form("", max_length=255),
    file: UploadFile = File(...),
    user: User = Depends(require_undertaking),
    db: Session = Depends(get_db),
):
    if material_type not in MATERIAL_TYPES:
        raise HTTPException(400, "Unknown material type.")
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "Subject not found.")

    settings = get_settings()
    try:
        stored = store_upload(file.file, file.filename or "", settings.max_upload_mb * 1024 * 1024, upload_root())
    except UploadError as exc:
        raise HTTPException(400, str(exc))

    title = re.sub(r"\s+", " ", title).strip() or Path(stored.original_filename).stem

    # Same subject + title + type = a new version of the same material.
    doc = db.scalar(
        select(Document).where(
            Document.subject_id == subject_id,
            func.lower(Document.title) == title.lower(),
            Document.material_type == material_type,
        ).options(selectinload(Document.versions))
    )
    if doc and any(v.sha256 == stored.sha256 and v.is_current for v in doc.versions):
        delete_stored_file(upload_root(), stored.stored_path)
        raise HTTPException(409, "This exact file is already the current version of this material.")

    if doc is None:
        doc = Document(
            subject_id=subject_id, uploader_id=user.id, title=title, material_type=material_type,
            topic=topic.strip(), unit=unit.strip(), department=department.strip(), semester=semester,
            academic_year=academic_year, status=DOC_UPLOADED,
        )
        db.add(doc)
        db.flush()
        number = 1
    else:
        doc.topic, doc.unit, doc.academic_year = topic.strip() or doc.topic, unit.strip() or doc.unit, academic_year
        number = max(v.version_number for v in doc.versions) + 1

    version = DocumentVersion(
        document_id=doc.id, version_number=number, original_filename=stored.original_filename,
        stored_path=stored.stored_path, mime_type=stored.mime_type, size_bytes=stored.size_bytes,
        sha256=stored.sha256, stage="uploaded", status=DOC_UPLOADED, is_current=False,
    )
    db.add(version)
    db.add(Event(user_id=user.id, event_type="document_upload",
                 payload={"subject_id": subject_id, "version": number}))
    db.commit()

    background.add_task(process_version, version.id)
    db.refresh(doc)
    return to_out(_load(db, doc.id))


@router.get("", response_model=list[DocumentOut])
def list_documents(
    subject_id: int | None = None,
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (select(Document).options(selectinload(Document.versions), selectinload(Document.subject))
         .order_by(Document.created_at.desc()).limit(200))
    if subject_id:
        q = q.where(Document.subject_id == subject_id)
    if user.role != ROLE_ADMIN:
        # Students only ever see finished, indexed material from their own department.
        q = q.where(Document.status == DOC_INDEXED, Document.department == (user.student.department if user.student else ""))
    elif status_filter:
        q = q.where(Document.status == status_filter)
    docs = db.scalars(q).all()
    return [to_out(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return to_out(_load(db, doc_id))


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = _load(db, doc_id)
    paths = [v.stored_path for v in doc.versions]
    # ON DELETE CASCADE removes versions and their chunks (and embeddings) in the same transaction.
    db.delete(doc)
    db.add(Event(user_id=user.id, event_type="document_delete", payload={"document_id": doc_id}))
    db.commit()
    for p in paths:
        try:
            delete_stored_file(upload_root(), p)
        except OSError:
            logger.warning("Could not remove stored file %s", p)


@router.post("/{doc_id}/reindex", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def reindex_document(doc_id: int, background: BackgroundTasks, user: User = Depends(require_admin),
                     db: Session = Depends(get_db)):
    """Re-run the whole pipeline (extract, chunk, embed) on the newest version, e.g. after a failure
    or after switching the embedding model."""
    doc = _load(db, doc_id)
    latest = doc.versions[-1]
    if latest.status in (DOC_UPLOADED, DOC_PROCESSING):
        raise HTTPException(409, "This document is already being processed.")
    latest.status, latest.stage, latest.error_message = DOC_UPLOADED, "uploaded", ""
    db.add(Event(user_id=user.id, event_type="document_reindex", payload={"document_id": doc_id}))
    db.commit()
    background.add_task(process_version, latest.id)
    return to_out(_load(db, doc_id))


@router.get("/{doc_id}/download")
def download_document(doc_id: int, version_no: int | None = Query(None, alias="version", ge=1),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Original file. Students: the live, indexed version of material from their own department.
    Admins: the live version, or any stored version via ?version=N."""
    doc = _load(db, doc_id)
    current = next((v for v in doc.versions if v.is_current), None)
    if user.role != ROLE_ADMIN:
        dept = user.student.department if user.student else ""
        if current is None or current.status != DOC_INDEXED or doc.department != dept:
            raise HTTPException(404, "Document not found.")
        chosen = current
    elif version_no is not None:
        chosen = next((v for v in doc.versions if v.version_number == version_no), None)
        if chosen is None:
            raise HTTPException(404, "Version not found.")
    else:
        chosen = current or doc.versions[-1]
    path = (upload_root() / chosen.stored_path).resolve()
    if upload_root() not in path.parents or not path.is_file():
        raise HTTPException(404, "The file is no longer available.")
    db.add(Event(user_id=user.id, event_type="document_download", payload={"document_id": doc_id}))
    db.commit()
    return FileResponse(path, media_type=chosen.mime_type, filename=chosen.original_filename,
                        headers={"X-Content-Type-Options": "nosniff"}, content_disposition_type="attachment")


def _busy(doc: Document) -> bool:
    return any(v.status in (DOC_UPLOADED, DOC_PROCESSING) for v in doc.versions)


@router.post("/{doc_id}/archive", response_model=DocumentOut)
def archive_document(doc_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Take the live version out of the knowledge base without deleting it. Passages are kept, so it can be restored."""
    doc = _load(db, doc_id)
    current = next((v for v in doc.versions if v.is_current), None)
    if _busy(doc):
        raise HTTPException(409, "This document is being processed. Try again in a moment.")
    if current is None or current.status == DOC_ARCHIVED:
        raise HTTPException(409, "There is no live version to archive.")
    current.status = DOC_ARCHIVED
    refresh_document_status(doc)
    db.add(Event(user_id=user.id, event_type="document_archive", payload={"document_id": doc_id}))
    db.commit()
    return to_out(_load(db, doc_id))


@router.post("/{doc_id}/restore", response_model=DocumentOut)
def restore_document(doc_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = _load(db, doc_id)
    current = next((v for v in doc.versions if v.is_current), None)
    if current is None or current.status != DOC_ARCHIVED:
        raise HTTPException(409, "This document is not archived.")
    if current.chunk_count == 0:
        raise HTTPException(409, "Nothing to restore from; use Re-index instead.")
    current.status, current.stage = DOC_INDEXED, "indexed"
    refresh_document_status(doc)
    db.add(Event(user_id=user.id, event_type="document_restore", payload={"document_id": doc_id}))
    db.commit()
    return to_out(_load(db, doc_id))


@router.post("/{doc_id}/versions/{number}/restore", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def rollback_version(doc_id: int, number: int, background: BackgroundTasks, user: User = Depends(require_admin),
                     db: Session = Depends(get_db)):
    """Make an older version live again by re-processing its stored file. The version being replaced is archived
    only after the older one has been fully re-indexed."""
    doc = _load(db, doc_id)
    version = next((v for v in doc.versions if v.version_number == number), None)
    if version is None:
        raise HTTPException(404, "Version not found.")
    if _busy(doc):
        raise HTTPException(409, "This document is being processed. Try again in a moment.")
    if version.is_current and version.status != "failed":
        raise HTTPException(409, "That version is already live.")
    version.status, version.stage, version.error_message = DOC_UPLOADED, "uploaded", ""
    db.add(Event(user_id=user.id, event_type="document_rollback", payload={"document_id": doc_id, "version": number}))
    db.commit()
    background.add_task(process_version, version.id)
    return to_out(_load(db, doc_id))
