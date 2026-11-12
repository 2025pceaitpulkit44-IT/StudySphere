from datetime import datetime, timezone

import pytest

from app.database.session import SessionLocal
from app.rag.retriever import retrieve
from tests.conftest import _register, upload
from tests.test_ai import StubLLM, ask, kb, stub  # noqa: F401
from tests.test_student import answers, quiz_llm, start  # noqa: F401


def doc_id(client, admin, title):
    return next(d["id"] for d in client.get("/documents", headers=admin).json() if d["title"] == title)


# ---------------- dashboard ----------------
def test_dashboard_reports_real_counts(client, admin_ready, student, kb):
    d = client.get("/admin/dashboard", headers=admin_ready).json()
    assert d["total_students"] == 1 and d["total_documents"] == 2 and d["indexed_documents"] == 2
    assert d["indexed_passages"] >= 2 and d["subjects_total"] == 1 and d["subjects_covered"] == 1
    assert d["kb_status"] == "healthy" and d["undertaking_completed"] is True
    assert {u["title"] for u in d["recent_uploads"]} == {"Searching Notes", "Graph Notes"}


def test_dashboard_empty_and_attention_states(client, admin, admin_ready, subject):
    assert client.get("/admin/dashboard", headers=admin_ready).json()["kb_status"] == "empty"
    upload(client, admin_ready, subject, content=b"tiny", filename="t.txt")            # fails: too little text
    d = client.get("/admin/dashboard", headers=admin_ready).json()
    assert d["kb_status"] == "attention" and d["failed_documents"] == 1 and d["indexed_passages"] == 0


def test_dashboard_without_undertaking_flags_it(client, admin):
    assert client.get("/admin/dashboard", headers=admin).json()["undertaking_completed"] is False


def test_admin_endpoints_are_admin_only(client, student):
    for path in ("/admin/dashboard", "/admin/doubts", "/admin/analytics"):
        assert client.get(path, headers=student).status_code == 403
        assert client.get(path).status_code == 401


# ---------------- archive / restore ----------------
def test_archive_removes_from_knowledge_base_and_restore_brings_it_back(client, admin_ready, student, kb):
    did = doc_id(client, admin_ready, "Searching Notes")
    r = client.post(f"/documents/{did}/archive", headers=admin_ready)
    assert r.status_code == 200 and r.json()["status"] == "archived"
    with SessionLocal() as db:
        assert retrieve(db, "binary search sorted array") == []                  # no longer used for answers
    assert "Searching Notes" not in [d["title"] for d in client.get("/documents", headers=student).json()]
    assert client.get(f"/documents/{did}/download", headers=student).status_code == 404
    assert client.get(f"/documents/{did}/download", headers=admin_ready).status_code == 200
    assert client.get("/admin/dashboard", headers=admin_ready).json()["archived_documents"] == 1
    assert client.post(f"/documents/{did}/archive", headers=admin_ready).status_code == 409

    r = client.post(f"/documents/{did}/restore", headers=admin_ready)
    assert r.status_code == 200 and r.json()["status"] == "indexed"
    with SessionLocal() as db:
        assert retrieve(db, "binary search sorted array")
    assert client.get(f"/documents/{did}/download", headers=student).status_code == 200
    assert client.post(f"/documents/{did}/restore", headers=admin_ready).status_code == 409   # not archived


def test_students_cannot_archive_restore_or_rollback(client, admin_ready, student, kb):
    did = doc_id(client, admin_ready, "Searching Notes")
    for path in (f"/documents/{did}/archive", f"/documents/{did}/restore", f"/documents/{did}/versions/1/restore"):
        assert client.post(path, headers=student).status_code == 403


# ---------------- version rollback ----------------
def test_rollback_makes_an_older_version_live_again(client, admin_ready, subject):
    v1 = upload(client, admin_ready, subject, title="Notes", content=b"Arrays store elements contiguously in memory. " * 30).json()
    upload(client, admin_ready, subject, title="Notes", content=b"Linked lists store nodes with pointers. " * 30)
    did = v1["id"]
    with SessionLocal() as db:
        assert retrieve(db, "arrays contiguous memory") == []

    r = client.post(f"/documents/{did}/versions/1/restore", headers=admin_ready)
    assert r.status_code == 202
    doc = client.get(f"/documents/{did}", headers=admin_ready).json()
    by_num = {v["version_number"]: v for v in doc["versions"]}
    assert by_num[1]["is_current"] and by_num[1]["status"] == "indexed"
    assert by_num[2]["status"] == "archived" and not by_num[2]["is_current"]
    with SessionLocal() as db:
        assert retrieve(db, "arrays contiguous memory")
        assert retrieve(db, "linked lists nodes pointers") == []

    assert client.post(f"/documents/{did}/versions/1/restore", headers=admin_ready).status_code == 409   # already live
    assert client.post(f"/documents/{did}/versions/9/restore", headers=admin_ready).status_code == 404


def test_admin_can_download_any_stored_version(client, admin_ready, student, subject):
    v1 = upload(client, admin_ready, subject, title="Notes", content=b"Arrays store elements contiguously. " * 30).json()
    upload(client, admin_ready, subject, title="Notes", content=b"Linked lists store nodes with pointers. " * 30)
    old = client.get(f"/documents/{v1['id']}/download?version=1", headers=admin_ready)
    new = client.get(f"/documents/{v1['id']}/download", headers=admin_ready)
    assert b"Arrays" in old.content and b"Linked" in new.content
    assert client.get(f"/documents/{v1['id']}/download?version=9", headers=admin_ready).status_code == 404
    # students always get the live version, whatever they put in the query string
    assert b"Linked" in client.get(f"/documents/{v1['id']}/download?version=1", headers=student).content


# ---------------- doubt analytics ----------------
@pytest.fixture
def busy_kb(client, student, kb, stub):
    s2, s3 = _register(client, "s2@example.edu"), _register(client, "s3@example.edu")
    ask(client, student, kb, question="Explain binary search on a sorted array", topic="Binary Search")
    ask(client, s2, kb, question="How does binary search work on a sorted array", topic="Binary Search")
    ask(client, s3, kb, question="binary search time complexity sorted array")
    ask(client, student, kb, question="What is photosynthesis in chloroplasts")        # not in the KB
    ask(client, s2, kb, question="what is photosynthesis in chloroplasts?")           # same question, other student
    return kb


def test_doubt_analytics_aggregates_without_identifying_students(client, admin_ready, busy_kb):
    r = client.get("/admin/doubts", headers=admin_ready)
    d = r.json()
    assert d["total_questions"] == 5 and d["unanswered"] == 2 and d["answer_rate"] == 60.0
    assert d["by_subject"][0] == {"subject": "Data Structures", "count": 5, "unanswered": 2}
    assert d["top_topics"][0] == {"subject": "Data Structures", "topic": "Binary Search", "count": 2}
    concept = next(c for c in d["frequent_concepts"] if c["term"] == "binary search")
    assert concept["students"] == 3
    gap = d["unanswered_questions"]
    assert len(gap) == 1 and "photosynthesis" in gap[0]["question"].lower() and gap[0]["times_asked"] == 2
    for secret in ("student@example.edu", "s2@example.edu", "s3@example.edu", "Test User", "student_id", "email"):
        assert secret not in r.text


def test_doubt_analytics_window_and_validation(client, admin_ready, busy_kb):
    assert client.get("/admin/doubts?days=7", headers=admin_ready).json()["total_questions"] == 5
    assert client.get("/admin/doubts?days=0", headers=admin_ready).status_code == 422
    empty = client.get("/admin/doubts", headers=_register(client, "other@example.edu", admin_invite_code="TEST-INVITE"))
    assert empty.status_code == 200 and empty.json()["total_questions"] == 5   # any admin sees the same school-wide view


# ---------------- analytics ----------------
def test_analytics_series_and_totals(client, admin_ready, busy_kb):
    a = client.get("/admin/analytics?days=7", headers=admin_ready).json()
    today = datetime.now(timezone.utc).date().isoformat()
    assert len(a["doubts_per_day"]) == 8 and sum(p["value"] for p in a["doubts_per_day"]) == a["total_doubts"] == 5
    assert a["active_students"] == 3
    assert sum(p["value"] for p in a["uploads_per_day"]) == 2
    growth = [p["value"] for p in a["kb_growth"]]
    assert growth == sorted(growth) and growth[-1] == 2
    assert a["top_subjects"][0] == {"label": "Data Structures", "count": 5}
    assert a["top_topics"][0]["label"] == "Binary Search"
    assert a["quiz_attempts"] == 0 and a["quiz_avg_percent"] is None and a["quiz_by_subject"] == []
    assert a["doubts_per_day"][-1] == {"date": today, "value": 5}


def test_analytics_includes_quiz_performance(client, admin_ready, student, kb, quiz_llm):
    s = start(client, student, kb).json()
    client.post("/quiz/submit", json={"attempt_id": s["attempt_id"], "answers": answers(s, 2)}, headers=student)
    a = client.get("/admin/analytics", headers=admin_ready).json()
    assert a["quiz_attempts"] == 1 and a["quiz_avg_percent"] == 66.7
    assert a["quiz_by_subject"] == [{"subject": "Data Structures", "attempts": 1, "avg_percent": 66.7}]


def test_analytics_days_validation(client, admin_ready):
    assert client.get("/admin/analytics?days=3", headers=admin_ready).status_code == 422
    assert client.get("/admin/analytics?days=500", headers=admin_ready).status_code == 422
