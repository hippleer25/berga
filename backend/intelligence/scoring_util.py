"""
intelligence/scoring_util.py — Pure scoring functions for the RSS ranking engine.

Every function is stateless and deterministic — no DB calls, no I/O.
All magic numbers live in the module docstring of recommendations.py;
this module just implements the math.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np


# ── Contrast score ─────────────────────────────────────────────────────────────

def contrast_score(sim_pos: float, sim_neg: float) -> float:
    """
    How much an article aligns with the user's positive profile
    *relative to* the negative profile.

        contrast = max(0, sim_pos − 0.5 × sim_neg)

    The 0.5 coefficient means a "dislike" signal needs to be roughly
    twice as strong as a "like" signal to fully cancel it out.
    """
    return max(0.0, sim_pos - 0.5 * sim_neg)


# ── Cosine similarity ─────────────────────────────────────────────────────────

def cosine_similarity(vec_a, vec_b) -> float:
    """
    Cosine similarity between two vectors (lists or numpy arrays).

    Returns a value in [-1, 1], or 0.0 if either vector has zero magnitude.
    """
    a = np.asarray(vec_a, dtype=np.float64)
    b = np.asarray(vec_b, dtype=np.float64)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


# ── Publisher engagement ──────────────────────────────────────────────────────

def publisher_engagement(
    likes: float,
    dislikes: float,
    exponent: float = 1.1,
) -> float:
    """
    Ratio-based engagement signal for a publisher.

        raw   = (likes + 1)^0.5  /  (dislikes + 1)^0.6
        score = raw ^ exponent

    The +1 avoids division by zero and dampens the effect of tiny counts.
    The 0.5 / 0.6 exponents compress the ratio; the outer exponent
    (default 1.1) slightly amplifies the spread so the signal isn't
    compressed to a narrow band near 1.0.

    A publisher with 0 likes and 0 dislikes returns 1.0  (neutral).
    """
    raw = (likes + 1.0) ** 0.5 / (dislikes + 1.0) ** 0.6
    return raw ** exponent


# ── Article popularity ────────────────────────────────────────────────────────

def article_popularity(
    likes: int = 0,
    views: int = 0,
    saved: int = 0,
    reads: int = 0,
) -> float:
    """
    Global popularity of a single article.

        score = 1 + log(1 + 3·likes + 2·saved + 1.0·reads + 0.1·views)

    Weights reflect engagement depth:
        like  = 3   (explicit positive signal)
        saved = 2   (strong intent to return)
        read  = 1.0 (1/3 of a like — moderate engagement)
        view  = 0.1 (low-signal impression)

    The +1 outside the log guarantees the minimum is 1.0 (no popularity
    bonus for zero-interaction articles).  The log compresses the long
    tail so viral articles don't completely dominate.
    """
    weighted = 3.0 * likes + 2.0 * saved + 1.0 * reads + 0.1 * views
    return 1.0 + math.log1p(weighted)


# ── Publisher frequency bonus ─────────────────────────────────────────────────

def publisher_frequency_bonus(
    freq_days: float,
    ref_days: float = 30.0,
    exponent: float = 0.5,
    cap: float = 3.0,
) -> float:
    """
    Bonus for publishers that publish *less* frequently.

        bonus = min( (ref_days / max(freq_days, 1)) ^ exponent ,  cap )

    A daily publisher (freq=1) over 30 days gets  (30/1)^0.5 ≈ 5.5,
    capped to 3.0.
    A weekly publisher (freq=7) gets  (30/7)^0.5 ≈ 2.1.
    A monthly publisher (freq=30) gets (30/30)^0.5 = 1.0  (no bonus).

    Rationale: rare posts from a publisher you follow are more likely
    to be noteworthy than the 12th daily article.
    """
    raw = (ref_days / max(freq_days, 1.0)) ** exponent
    return min(raw, cap)


# ── Time decay multiplier ────────────────────────────────────────────────────

def time_decay_multiplier(
    pub_timestamp: float,
    now_timestamp: float,
    time_const: float = 180.0,
    gravity: float = 0.35,
) -> float:
    """
    Recency decay based on article age in minutes.

        age_min = (now − pub_timestamp) / 60
        decay   = 1 / (age_min + time_const) ^ gravity

    Default constants (tune via env vars in recommendations.py):
        time_const = 180  → the half-life anchor is ~3 hours
        gravity    = 0.35 → gentle decay; articles stay relevant for days

    A brand-new article (age=0) scores  1 / 180^0.35 ≈ 0.12.
    A 1-day-old article (age=1440) scores  1 / 1620^0.35 ≈ 0.054.
    The ratio between them is ~2.2×, enough to surface fresh content
    without instantly burying older stories.
    """
    if pub_timestamp is None:
        return 1.0 / (0.0 + time_const) ** gravity

    age_seconds = max(now_timestamp - pub_timestamp, 0.0)
    age_minutes = age_seconds / 60.0

    return 1.0 / (age_minutes + time_const) ** gravity


# ── EMA blend and normalise ───────────────────────────────────────────────────

def ema_blend_and_normalise(
    existing_vec: Optional[np.ndarray],
    new_vec: np.ndarray,
    strength: float,
) -> np.ndarray:
    """
    Exponential moving average blend followed by L2 normalisation.

        result = (1 − strength) × existing + strength × new
        result = result / ‖result‖

    If *existing_vec* is None, *new_vec* is simply normalised and returned.
    Used by the affinity engine to incrementally blend preference vectors
    while keeping them on the unit hypersphere.
    """
    new = np.asarray(new_vec, dtype=np.float32)

    if existing_vec is None:
        blended = new
    else:
        existing = np.asarray(existing_vec, dtype=np.float32)
        blended = (1.0 - strength) * existing + strength * new

    norm = np.linalg.norm(blended)
    if norm > 0:
        blended = blended / norm

    return blended


# ── Vector blending ───────────────────────────────────────────────────────────

def blend_vectors(
    primary: list[float],
    secondary: Optional[list[float]],
    weight: float = 0.4,
) -> list[float]:
    """
    Blend a primary vector with an optional secondary vector, then
    L2-normalise the result for cosine-search compatibility.

    result = (1 − weight) × primary + weight × secondary
    result = result / ‖result‖

    If *secondary* is None, returns *primary* unchanged.
    If dimensions mismatch, returns *primary* unchanged.

    Used to combine interaction vectors (primary) with affinity /
    category-preference vectors (secondary). Default weight 0.4 gives
    the affinity signal meaningful influence without overwhelming
    observed behaviour.
    """
    if secondary is None or weight <= 0.0:
        return list(primary)

    if weight >= 1.0:
        norm = np.linalg.norm(secondary)
        if norm > 0:
            return (np.asarray(secondary, dtype=np.float32) / norm).tolist()
        return list(secondary)

    b = np.asarray(primary, dtype=np.float32)
    a = np.asarray(secondary, dtype=np.float32)

    if len(b) != len(a):
        return list(primary)

    blended = (1.0 - weight) * b + weight * a
    norm = np.linalg.norm(blended)
    if norm > 0:
        blended = blended / norm

    return blended.tolist()


# ── Score normalisation ──────────────────────────────────────────────────────

def normalize_scores(
    scores: list[float],
    floor: float = 0.0,
    ceiling: float = 1.0,
) -> list[float]:
    """
    Min-max normalise a list of raw scores to [floor, ceiling].

    Edge cases:
      • Empty list        → []
      • All scores equal  → evenly spaced from ceiling down to ~floor
                            (prevents zero-range division and gives the
                             caller a deterministic, monotonically
                             decreasing sequence to work with)
    """
    n = len(scores)
    if n == 0:
        return []

    min_s = min(scores)
    max_s = max(scores)
    span = max_s - min_s

    if span > 0:
        return [
            floor + (ceiling - floor) * (s - min_s) / span
            for s in scores
        ]

    # All identical — assign evenly spaced descending values
    if n == 1:
        return [ceiling]

    step = (ceiling - floor) / (n - 1) if n > 1 else 0.0
    return [ceiling - i * step for i in range(n)]