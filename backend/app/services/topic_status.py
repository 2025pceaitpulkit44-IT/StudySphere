"""Rules that turn practice data into a study-status label. Deliberately simple and explainable."""

LABELS = {
    "needs_revision": "Needs revision",
    "practice": "Practice recommended",
    "improving": "Improving",
    "good": "On track",
    "new": "Just started",
}
WEAK_STATUSES = ("needs_revision", "practice", "improving")


def classify_topic(doubts_count: int, quizzes_taken: int, avg_score: float | None,
                   recent_scores: list[float] | None = None) -> str:
    """avg_score and recent_scores are percentages (0-100); recent_scores is oldest -> newest.

    - improving:       latest topic quiz beat the previous one by 10+ points, but average is still under 80
    - needs_revision:  average quiz score under 50
    - practice:        average 50-69, or 3+ doubts asked with no quiz taken yet
    - good:            average 70+, or 3+ doubts with a good quiz average
    - new:             too little data to say anything
    """
    recent = recent_scores or []
    if quizzes_taken > 0 and avg_score is not None:
        if len(recent) >= 2 and recent[-1] - recent[-2] >= 10 and avg_score < 80:
            return "improving"
        if avg_score < 50:
            return "needs_revision"
        if avg_score < 70:
            return "practice"
        return "good"
    if doubts_count >= 3:
        return "practice"
    return "new"


def streak_days(active_dates: set, today) -> int:
    """Consecutive days of activity ending today (or yesterday, so the streak survives until midnight)."""
    from datetime import timedelta
    day = today if today in active_dates else today - timedelta(days=1)
    n = 0
    while day in active_dates:
        n += 1
        day -= timedelta(days=1)
    return n
