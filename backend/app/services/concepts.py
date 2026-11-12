"""Frequently-asked-concept extraction for the faculty view. Pure Python, no database access.

Privacy rule: a term is only reported if at least `min_students` DIFFERENT students asked about it, so a
faculty member can never infer what one particular student has been asking.
"""
import re
from collections import defaultdict

STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being between both but by can
could did do does doing down during each few for from further had has have having he her here hers him his how i
if in into is it its just me more most my no nor not now of off on once only or other our out over own same she
should so some such than that the their them then there these they this those through to too under until up very
was we were what when where which while who whom why will with would you your
explain define describe difference differences between give example examples write short note notes tell
please help understand meaning mean works work use used using get make find show solve question answer
""".split())
_TOKEN = re.compile(r"[a-z][a-z0-9+#.\-]*[a-z0-9+#]|[a-z]")


def _terms(question: str) -> tuple[set[str], set[str]]:
    toks = [t.strip(".-") for t in _TOKEN.findall(question.lower())]
    toks = [t for t in toks if t]
    keep = [t if t not in STOPWORDS and len(t) >= 3 else None for t in toks]
    unigrams = {t for t in keep if t}
    bigrams = {f"{a} {b}" for a, b in zip(keep, keep[1:]) if a and b}
    return unigrams, bigrams


def frequent_terms(rows: list[tuple[int, str]], min_students: int = 2, top: int = 15) -> list[dict]:
    """rows = [(student_id, question)]. Returns [{term, questions, students}], most common first."""
    questions: dict[str, int] = defaultdict(int)
    students: dict[str, set[int]] = defaultdict(set)
    for sid, q in rows:
        uni, bi = _terms(q)
        for term in uni | bi:
            questions[term] += 1
            students[term].add(sid)

    ranked = [
        {"term": t, "questions": questions[t], "students": len(students[t])}
        for t in questions if len(students[t]) >= min_students
    ]
    ranked.sort(key=lambda r: (-r["students"], -r["questions"], -len(r["term"].split()), r["term"]))

    # A phrase like "binary search" makes its own words ("binary", "search") redundant noise.
    phrases = [r for r in ranked if " " in r["term"]]
    out = []
    for r in ranked:
        if " " not in r["term"] and any(
            r["term"] in p["term"].split() and p["questions"] >= 0.8 * r["questions"] for p in phrases
        ):
            continue
        out.append(r)
    return out[:top]
