"""Decision categorization logic for warranty claims.

Thresholds:
  AUTO_APPROVE  — all per-part scores > 0.8
  FLAG          — any per-part score < 0.3
  REVIEW        — everything else
"""

from __future__ import annotations

from typing import List, Tuple


def categorize_claim(scores: List[float]) -> Tuple[str, float]:
    """Return (decision_category, overall_score) for a list of per-part relevance scores.

    Parameters
    ----------
    scores : list[float]
        Non-empty list of relevance scores, each in [0.0, 1.0].

    Returns
    -------
    tuple[str, float]
        A 2-tuple of (decision_category, overall_score).
        decision_category is one of "AUTO_APPROVE", "REVIEW", "FLAG".
        overall_score is the arithmetic mean of *scores*.
    """
    if not scores:
        raise ValueError("scores must be a non-empty list")

    overall_score = sum(scores) / len(scores)

    # FLAG takes priority — any suspicious part flags the whole claim
    if any(s < 0.3 for s in scores):
        return "FLAG", overall_score

    if all(s > 0.8 for s in scores):
        return "AUTO_APPROVE", overall_score

    return "REVIEW", overall_score
