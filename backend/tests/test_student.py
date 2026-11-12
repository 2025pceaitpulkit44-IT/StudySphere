import json

import pytest
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import QuizQuestion, StudentProgress
from tests.conftest import _register
from tests.test_ai import StubLLM, kb, stub, ask  # noqa: F401  (shared fixtures/helpers)

QUIZ = {"questions": [
    {"question": "What does binary search do to the search range each step?", "options": ["Halves it", "Doubles it", "Sorts it", "Deletes it"],
     "correct_index": 0, "explanation": "It halves the range.", "source": 1},
    {"question": "Binary search requires the array to be which of these?", "options": ["Sorted", "Empty", "Circular", "Encrypted"],
     "correct_index": 0, "explanation": "It needs sorted input.", "source": 1},
    {"question": "What is the time complexity of binary search?", "options": ["O(log n)", "O(n)", "O(n squared)", "O(1)"],
     "correct_index": 0, "explanation": "Logarithmic.", "source": 1},
]}
RIGHT = {"What does binary search do to the search range each step?": "Halves it",
         "Binary search requires the array to be which of these?": "Sorted",
         "What is the time complexity of binary search?": "O(log n)"}


@pytest.fixture
def quiz_llm(monkeypatch):
    llm = StubLLM(json.dumps(QUIZ))
    monkeypatch.setattr("app.services.quiz_service.get_llm", lambda: llm)
    return llm


@pytest.fixture
def outsider(client):
    return _register(client, "mech@example.edu", department="Mechanical Engineering")


def start(client, h, subject_id, **extra):
    return client.post("/quiz/start", json={"subject_id": subject_id, "topic": "Binary Search", **extra}, headers=h)


def answers(started, right_count):
    out = []
    for i, q in enumerate(started["questions"]):
        correct_text = RIGHT[q["question"]]
        idx = q["options"].index(correct_text)
        if i >= right_count:
            idx = (idx + 1) % 4
        out.append({"question_id": q["id"], "chosen_index": idx})
    return out


# ---------------- doubts ----------------
def test_doubt_history_search_filter_detail_delete(client, student, kb, stub):
    ask(client, student, kb, question="Explain binary search on a sorted array", topic="Binary Search")
    ask(client, student, kb, question="What is photosynthesis in chloroplasts")  # unanswerable
    rows = client.get("/doubts", headers=student).json()
    assert len(rows) == 2 and rows[0]["question"].startswith("What is photosynthesis")
    assert [r["question"] for r in client.get("/doubts?q=BINARY", headers=student).json()] == ["Explain binary search on a sorted array"]
    assert len(client.get(f"/doubts?subject_id={kb}", headers=student).json()) == 2
    answered = next(r for r in rows if r["answerable"])
    d = client.get(f"/doubts/{answered['id']}", headers=student).json()
    assert d["sources"][0]["title"] == "Searching Notes" and d["answer"].startswith("Binary search") and d["key_points"]
    assert client.delete(f"/doubts/{answered['id']}", headers=student).status_code == 204
    assert client.get(f"/doubts/{answered['id']}", headers=student).status_code == 404


def test_doubts_are_private(client, student, outsider, kb, stub):
    ask(client, student, kb)
    did = client.get("/doubts", headers=student).json()[0]["id"]
    assert client.get(f"/doubts/{did}", headers=outsider).status_code == 404
    assert client.delete(f"/doubts/{did}", headers=outsider).status_code == 404
    assert client.get("/doubts", headers=outsider).json() == []
    assert client.get("/doubts").status_code == 401


# ---------------- subjects / documents / download ----------------
def test_subject_overview_and_student_document_list(client, student, admin_ready, kb):
    ov = client.get("/subjects/overview", headers=student).json()
    assert len(ov) == 1 and ov[0]["material_count"] == 2 and ov[0]["doubts_count"] == 0
    docs = client.get(f"/documents?subject_id={kb}", headers=student).json()
    assert {d["title"] for d in docs} == {"Searching Notes", "Graph Notes"}
    assert client.get("/subjects/overview", headers=admin_ready).status_code == 403


def test_download_rules(client, student, outsider, admin_ready, kb):
    docs = client.get("/documents", headers=student).json()
    did = docs[0]["id"]
    r = client.get(f"/documents/{did}/download", headers=student)
    assert r.status_code == 200 and r.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in r.headers["content-disposition"] and b"search" in r.content.lower()
    assert client.get(f"/documents/{did}/download", headers=outsider).status_code == 404   # other department
    assert client.get(f"/documents/{did}/download", headers=admin_ready).status_code == 200
    assert client.get(f"/documents/{did}/download").status_code == 401


# ---------------- search ----------------
def test_search(client, student, outsider, kb):
    r = client.get("/search?q=binary search sorted array", headers=student).json()
    assert r["semantic"] and r["documents"][0]["title"] == "Searching Notes"
    assert r["documents"][0]["snippet"]
    g = client.get("/search?q=Graph", headers=student).json()                   # title/topic match without vectors
    assert any(d["title"] == "Graph Notes" for d in g["documents"])
    assert any(t["topic"] == "Graphs" for t in g["topics"])
    assert [s["name"] for s in client.get("/search?q=Data Struct", headers=student).json()["subjects"]] == ["Data Structures"]
    o = client.get("/search?q=binary search", headers=outsider).json()
    assert o["documents"] == [] and o["subjects"] == []                          # department isolation
    assert client.get("/search?q=a", headers=student).status_code == 422
    assert client.get("/search?q=binary").status_code == 401
    assert client.get("/search?q=100%25_%25", headers=student).status_code == 200  # wildcards are escaped, not interpreted


# ---------------- quiz ----------------
def test_quiz_is_built_from_retrieved_material_and_hides_answers(client, student, kb, quiz_llm):
    r = start(client, student, kb)
    assert r.status_code == 200
    body = r.json()
    assert len(body["questions"]) == 3 and body["topic"] == "Binary Search"
    assert "correct" not in r.text and "explanation" not in r.text           # nothing leaks before submission
    assert "Binary search repeatedly halves" in quiz_llm.calls[0][1]          # real passages went to the model
    with SessionLocal() as db:
        assert all(q.source_chunk_id for q in db.scalars(select(QuizQuestion)))


def test_quiz_submit_scores_reviews_and_updates_progress(client, student, kb, quiz_llm):
    started = start(client, student, kb).json()
    res = client.post("/quiz/submit", json={"attempt_id": started["attempt_id"], "answers": answers(started, 2)}, headers=student).json()
    assert res["score"] == 2 and res["total"] == 3 and res["percent"] == 66.7
    assert sum(item["correct"] for item in res["review"]) == 2
    assert all(item["explanation"] and item["source"] == "Searching Notes" for item in res["review"])
    with SessionLocal() as db:
        p = db.scalar(select(StudentProgress).where(StudentProgress.topic == "Binary Search"))
        assert p.quizzes_taken == 1 and round(p.avg_score, 1) == 66.7
    hist = client.get("/quiz/attempts", headers=student).json()
    assert hist[0]["score"] == 2
    assert client.get(f"/quiz/attempts/{started['attempt_id']}", headers=student).json()["score"] == 2


def test_quiz_cannot_be_resubmitted_or_hijacked(client, student, outsider, kb, quiz_llm):
    started = start(client, student, kb).json()
    payload = {"attempt_id": started["attempt_id"], "answers": answers(started, 3)}
    assert client.post("/quiz/submit", json=payload, headers=outsider).status_code == 404
    assert client.post("/quiz/submit", json=payload, headers=student).status_code == 200
    assert client.post("/quiz/submit", json=payload, headers=student).status_code == 409
    again = start(client, student, kb).json()
    bad = {"attempt_id": again["attempt_id"], "answers": [{"question_id": 999999, "chosen_index": 0}]}
    assert client.post("/quiz/submit", json=bad, headers=student).status_code == 422
    bad = {"attempt_id": again["attempt_id"], "answers": [{"question_id": again["questions"][0]["id"], "chosen_index": 9}]}
    assert client.post("/quiz/submit", json=bad, headers=student).status_code == 422


def test_quiz_needs_material_and_valid_model_output(client, student, admin_ready, subject, kb, monkeypatch):
    from app.models import Subject
    with SessionLocal() as db:
        empty = Subject(code="EM1", name="Empty Subject", department="CSE", semester=3, units=5)
        db.add(empty); db.commit(); empty_id = empty.id
    assert start(client, student, empty_id, topic="").status_code == 422            # nothing indexed
    assert start(client, student, 9999).status_code == 404
    monkeypatch.setattr("app.services.quiz_service.get_llm", lambda: StubLLM('{"questions": [{"question": "bad"}]}'))
    assert start(client, student, kb).status_code == 422                            # invalid model output is rejected
    assert client.post("/quiz/start", json={"subject_id": kb}, headers=admin_ready).status_code == 403


# ---------------- weak topics + dashboard ----------------
def test_dashboard_empty_state(client, student):
    d = client.get("/dashboard", headers=student).json()
    assert d["doubts_total"] == 0 and d["quizzes_taken"] == 0 and d["avg_score"] is None and d["streak_days"] == 0
    assert d["recent_doubts"] == [] and d["weak_topics"] == [] and d["recommended"] == []


def test_poor_quiz_makes_a_weak_topic_and_a_recommendation(client, student, kb, quiz_llm, stub):
    started = start(client, student, kb).json()
    client.post("/quiz/submit", json={"attempt_id": started["attempt_id"], "answers": answers(started, 0)}, headers=student)
    topics = client.get("/progress", headers=student).json()
    assert topics[0]["topic"] == "Binary Search" and topics[0]["status"] == "needs_revision"
    ask(client, student, kb, topic="Graphs")
    d = client.get("/dashboard", headers=student).json()
    assert d["weak_topics"][0]["label"] == "Needs revision" and d["quizzes_taken"] == 1 and d["avg_score"] == 0.0
    assert d["streak_days"] == 1 and len(d["recent_doubts"]) == 1
    practice = [r for r in d["recommended"] if r["kind"] == "practice"]
    assert practice and practice[0]["link"].startswith("/quiz?subject=") and "Binary%20Search" in practice[0]["link"]
    assert d["subjects"][0]["quizzes_taken"] == 1 and d["subjects"][0]["doubts_count"] == 1


def test_improving_trend_is_detected(client, student, kb, quiz_llm):
    for right in (0, 2):
        s = start(client, student, kb).json()
        client.post("/quiz/submit", json={"attempt_id": s["attempt_id"], "answers": answers(s, right)}, headers=student)
    assert client.get("/progress", headers=student).json()[0]["status"] == "improving"


def test_student_endpoints_reject_admins(client, admin_ready):
    for path in ("/dashboard", "/progress", "/doubts", "/quiz/attempts"):
        assert client.get(path, headers=admin_ready).status_code == 403
