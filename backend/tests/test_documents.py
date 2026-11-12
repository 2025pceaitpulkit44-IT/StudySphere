from pathlib import Path

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models import DocumentChunk
from tests.conftest import upload


def chunk_count(**filters):
    with SessionLocal() as db:
        q = select(func.count()).select_from(DocumentChunk)
        for k, v in filters.items():
            q = q.where(getattr(DocumentChunk, k) == v)
        return db.scalar(q)


def test_upload_is_extracted_chunked_and_indexed(client, admin_ready, subject):
    r = upload(client, admin_ready, subject)
    assert r.status_code == 201
    doc = client.get(f"/documents/{r.json()['id']}", headers=admin_ready).json()
    assert doc["status"] == "indexed" and doc["stage"] == "indexed"
    assert doc["version"] == 1 and doc["chunk_count"] > 0
    assert chunk_count(document_id=doc["id"]) == doc["chunk_count"]


def test_bad_uploads_are_rejected_with_clear_messages(client, admin_ready, subject):
    assert upload(client, admin_ready, subject, filename="x.exe").status_code == 400
    assert upload(client, admin_ready, subject, content=b"", filename="e.txt").status_code == 400
    assert upload(client, admin_ready, subject, content=b"not a pdf", filename="f.pdf").status_code == 400
    assert upload(client, admin_ready, subject, material_type="Gossip").status_code == 400
    assert upload(client, admin_ready, 9999).status_code == 404
    assert client.get("/documents", headers=admin_ready).json() == []


def test_too_little_text_fails_gracefully(client, admin_ready, subject):
    r = upload(client, admin_ready, subject, content=b"hi", filename="tiny.txt")
    doc = client.get(f"/documents/{r.json()['id']}", headers=admin_ready).json()
    assert doc["status"] == "failed" and "too little" in doc["error_message"]
    assert chunk_count(document_id=doc["id"]) == 0


def test_new_version_replaces_old_chunks(client, admin_ready, subject):
    v1 = upload(client, admin_ready, subject, content=b"Version one text about arrays. " * 50).json()
    v2 = upload(client, admin_ready, subject, content=b"Version two text about linked lists. " * 50).json()
    assert v2["id"] == v1["id"] and v2["version"] == 2
    doc = client.get(f"/documents/{v1['id']}", headers=admin_ready).json()
    by_num = {v["version_number"]: v for v in doc["versions"]}
    assert by_num[2]["is_current"] and not by_num[1]["is_current"]
    assert by_num[1]["status"] == "archived" and by_num[1]["chunk_count"] == 0
    with SessionLocal() as db:
        texts = " ".join(db.scalars(select(DocumentChunk.content)))
    assert "linked lists" in texts and "arrays" not in texts


def test_identical_reupload_is_rejected(client, admin_ready, subject):
    upload(client, admin_ready, subject)
    assert upload(client, admin_ready, subject).status_code == 409


def test_delete_removes_chunks_and_file(client, admin_ready, subject):
    doc = upload(client, admin_ready, subject).json()
    root = Path(__import__("os").environ["UPLOAD_DIR"])
    assert any(root.iterdir())
    assert chunk_count() > 0
    assert client.delete(f"/documents/{doc['id']}", headers=admin_ready).status_code == 204
    assert chunk_count() == 0
    assert not any(p for p in root.iterdir() if p.suffix == ".txt")
    assert client.get(f"/documents/{doc['id']}", headers=admin_ready).status_code == 404


def test_students_cannot_see_unindexed_documents_or_admin_routes(client, admin_ready, student, subject):
    doc = upload(client, admin_ready, subject).json()
    assert client.get("/documents", headers=student).json() == []
    assert client.get(f"/documents/{doc['id']}", headers=student).status_code == 403
    assert client.delete(f"/documents/{doc['id']}", headers=student).status_code == 403


def test_documents_require_login(client):
    assert client.get("/documents").status_code == 401
    assert client.post("/documents/upload").status_code == 401
