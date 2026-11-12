from app.services.concepts import frequent_terms

ROWS = [(1, "Explain binary search"), (2, "how does binary search work"), (3, "what is binary search on sorted array"),
        (1, "quicksort pivot choice"), (1, "quicksort pivot again"), (2, "What is a stack"), (4, "stack vs queue difference")]


def test_phrases_beat_their_words_and_stopwords_are_ignored():
    terms = {r["term"] for r in frequent_terms(ROWS)}
    assert {"binary search", "stack"} <= terms
    assert "binary" not in terms and "search" not in terms and "what" not in terms


def test_terms_from_a_single_student_are_withheld():
    terms = {r["term"] for r in frequent_terms(ROWS)}
    assert not any("quicksort" in t or "pivot" in t for t in terms)
    assert frequent_terms([(1, "binary search"), (1, "binary search again")]) == []


def test_threshold_is_configurable():
    out = frequent_terms(ROWS, min_students=3)
    assert [r["term"] for r in out] == ["binary search"] and out[0]["students"] == 3
