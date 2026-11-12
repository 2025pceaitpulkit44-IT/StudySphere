import json

import pytest
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models import Doubt, DocumentChunk
from app.rag.llm import LLMError
from app.rag.retriever import retrieve
from tests.conftest import upload

BINARY = ("Binary search repeatedly halves a sorted array. It compares the target with the middle element "
          "of the sorted array and discards half of the range each step. Binary search runs in O(log n) time. ") * 6
GRAPH = ("Breadth first search traverses a graph level by level using a queue. Depth first search goes deep "
         "along each branch using a stack. Graph traversal visits every vertex and edge once. ") * 6


class StubLLM:
    def __init__(self, reply=None, error=None):
        self.calls, self.reply, self.error = [], reply, error

    def generate(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.reply or json.dumps({
            "supported": True, "answer": "Binary search halves the range each step [1].",
            "explanation": "It compares with the middle element [1].", "key_points": ["Needs sorted input [1]"],
        })


@pytest.fixture
def stub(monkeypatch):
    llm = StubLLM()
    monkeypatch.setattr("app.services.ai_service.get_llm", lambda: llm)
    return llm


@pytest.fixture
def kb(client, admin_ready, subject):
    """Subject with two indexed documents (binary search, graph traversal)."""
    upload(client, admin_ready, subject, content=BINARY.encode(), title="Searching Notes", topic="Binary Search")
    upload(client, admin_ready, subject, content=GRAPH.encode(), title="Graph Notes", topic="Graphs")
    return subject


def ask(client, student, subject_id, question="Explain binary search on a sorted array", mode="ask", **extra):
    return client.post(f"/ai/{mode}", json={"question": question, "subject_id": subject_id, **extra}, headers=student)


# ---------------- indexing ----------------
def test_upload_generates_embeddings_for_every_chunk(client, kb):
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(DocumentChunk))
        embedded = db.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.embedding.is_not(None)))
    assert total > 0 and total == embedded


def test_new_document_becomes_searchable_after_indexing(client, admin_ready, subject):
    with SessionLocal() as db:
        assert retrieve(db, "quicksort pivot partition") == []
    upload(client, admin_ready, subject, title="Sorting",
           content=(b"Quicksort picks a pivot and partitions the array around the pivot. " * 30))
    with SessionLocal() as db:
        hits = retrieve(db, "quicksort pivot partition")
    assert hits and hits[0].title == "Sorting"


# ---------------- retrieval ----------------
def test_retrieval_ranks_relevant_document_first(client, kb):
    with SessionLocal() as db:
        hits = retrieve(db, "how does binary search work on a sorted array")
    assert hits[0].title == "Searching Notes"
    with SessionLocal() as db:
        hits = retrieve(db, "depth first search with a stack")
    assert hits[0].title == "Graph Notes"


def test_deleted_documents_leave_the_knowledge_base(client, admin_ready, kb):
    doc_id = client.get("/documents", headers=admin_ready).json()
    sid = next(d["id"] for d in doc_id if d["title"] == "Searching Notes")
    with SessionLocal() as db:
        assert any(h.document_id == sid for h in retrieve(db, "binary search sorted array"))
    assert client.delete(f"/documents/{sid}", headers=admin_ready).status_code == 204
    with SessionLocal() as db:
        assert not any(h.document_id == sid for h in retrieve(db, "binary search sorted array"))


def test_old_versions_are_not_retrievable(client, admin_ready, subject):
    upload(client, admin_ready, subject, title="Notes", content=b"Arrays store elements contiguously in memory. " * 30)
    upload(client, admin_ready, subject, title="Notes", content=b"Linked lists store nodes with pointers. " * 30)
    with SessionLocal() as db:
        assert retrieve(db, "arrays contiguous memory") == []
        assert retrieve(db, "linked lists nodes pointers")


def test_failed_documents_are_not_retrievable(client, admin_ready, subject):
    upload(client, admin_ready, subject, content=b"tiny", filename="t.txt")  # fails: too little text
    with SessionLocal() as db:
        assert retrieve(db, "tiny") == []


def test_subject_filter_is_applied(client, admin_ready, kb):
    from app.models import Subject
    with SessionLocal() as db:
        other = Subject(code="PH1", name="Physics", department="CSE", semester=3, units=5)
        db.add(other); db.commit(); other_id = other.id
        assert retrieve(db, "binary search sorted array", subject_id=other_id) == []
        assert retrieve(db, "binary search sorted array", subject_id=kb)


# ---------------- /ai endpoints ----------------
def test_answer_uses_retrieved_material_and_cites_real_sources(client, student, kb, stub):
    r = ask(client, student, kb)
    assert r.status_code == 200
    body = r.json()
    assert body["answerable"] and "[1]" in body["answer"]
    # The model really received the retrieved passage text.
    system, user = stub.calls[0]
    assert "Binary search repeatedly halves" in user and "Searching Notes" in user
    # Every source corresponds to a document that exists and was retrieved.
    titles = {s["title"] for s in body["sources"]}
    assert "Searching Notes" in titles and titles <= {"Searching Notes", "Graph Notes"}
    assert body["sources"][0]["title"] == "Searching Notes" and body["sources"][0]["cited"]
    assert body["relevance"]["level"] in {"high", "medium", "low"} and body["relevance"]["score"] > 0


def test_sources_cannot_be_fabricated_by_the_model(client, student, kb, monkeypatch):
    reply = json.dumps({"supported": True, "answer": "See 'Secret Textbook' [1][99].",
                        "explanation": "", "key_points": []})
    monkeypatch.setattr("app.services.ai_service.get_llm", lambda: StubLLM(reply))
    body = ask(client, student, kb).json()
    assert "[99]" not in body["answer"]
    assert all(s["title"] != "Secret Textbook" for s in body["sources"])


def test_no_relevant_material_means_no_llm_call(client, student, kb, stub):
    body = ask(client, student, kb, question="Explain photosynthesis in chloroplasts").json()
    assert body["answerable"] is False and body["sources"] == [] and body["relevance"] is None
    assert "couldn't find enough information" in body["answer"]
    assert stub.calls == []


def test_model_can_decline_unsupported_questions(client, student, kb, monkeypatch):
    monkeypatch.setattr("app.services.ai_service.get_llm",
                        lambda: StubLLM(json.dumps({"supported": False, "answer": "", "explanation": "", "key_points": []})))
    body = ask(client, student, kb).json()
    assert body["answerable"] is False and body["sources"] == []


@pytest.mark.parametrize("mode", ["ask", "explain", "solve"])
def test_all_modes_work_and_use_mode_specific_instructions(client, student, kb, stub, mode):
    assert ask(client, student, kb, mode=mode).status_code == 200
    assert f"Mode {mode.upper()}" in stub.calls[-1][0]


def test_doubt_is_saved_with_sources_and_progress(client, student, kb, stub):
    body = ask(client, student, kb, topic="Binary Search").json()
    assert body["saved"] and body["doubt_id"]
    with SessionLocal() as db:
        d = db.scalar(select(Doubt))
        assert d.question.startswith("Explain binary search") and d.answerable and d.sources[0]["title"] == "Searching Notes"
        assert json.loads(d.answer)["answer"].startswith("Binary search")
        from app.models import StudentProgress
        assert db.scalar(select(StudentProgress.doubts_count)) == 1


def test_unanswerable_doubts_are_saved_too(client, student, kb, stub):
    ask(client, student, kb, question="Explain photosynthesis in chloroplasts")
    with SessionLocal() as db:
        assert db.scalar(select(Doubt.answerable)) is False


def test_save_false_stores_nothing(client, student, kb, stub):
    body = ask(client, student, kb, save=False).json()
    assert body["saved"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Doubt)) == 0


def test_llm_outage_returns_friendly_503(client, student, kb, monkeypatch):
    monkeypatch.setattr("app.services.ai_service.get_llm", lambda: StubLLM(error=LLMError("HTTP 500: secret details")))
    r = ask(client, student, kb)
    assert r.status_code == 503
    assert "secret" not in r.text and "unavailable" in r.json()["detail"]


def test_missing_api_key_is_a_friendly_503(client, student, kb, monkeypatch):
    def boom():
        raise LLMError("GEMINI_API_KEY is not set.")
    monkeypatch.setattr("app.services.ai_service.get_llm", boom)
    r = ask(client, student, kb)
    assert r.status_code == 503 and "GEMINI" not in r.text


def test_access_control(client, admin_ready, student, kb, stub):
    assert ask(client, admin_ready, kb).status_code == 403          # admins don't get student features
    assert client.post("/ai/ask", json={"question": "binary search"}).status_code == 401
    assert ask(client, student, 9999).status_code == 404            # unknown subject
    assert client.post("/ai/ask", json={"question": "x"}, headers=student).status_code == 422


def test_reindex_keeps_document_searchable(client, admin_ready, kb):
    doc = next(d for d in client.get("/documents", headers=admin_ready).json() if d["title"] == "Searching Notes")
    r = client.post(f"/documents/{doc['id']}/reindex", headers=admin_ready)
    assert r.status_code == 202
    after = client.get(f"/documents/{doc['id']}", headers=admin_ready).json()
    assert after["status"] == "indexed" and after["chunk_count"] == doc["chunk_count"]
    with SessionLocal() as db:
        assert retrieve(db, "binary search sorted array")
