"""
ranker.py — Composite suggestion ranking for PredictionAgent.
Score = confidence×0.35 + learned_weight×0.35 + context_fit×0.20 + diversity×0.10
Spam prevention: same action penalised if shown < 5 min ago.
"""
import time
from typing import Optional

MIN_THRESHOLD = 0.45
SPAM_WINDOW_S = 300  # 5 minutes

_shown_history: dict[str, float] = {}  # action -> last shown timestamp

CONTEXT_FIT: dict[str, dict[str, float]] = {
    "suggest_sleep":      {"late_night": 1.0, "exhausted": 0.9, "night": 0.8},
    "offer_break":        {"high_stress": 1.0, "tired": 0.8, "high": 0.7},
    "follow_up_question": {"medium": 0.8, "fresh": 0.9, "morning": 0.7},
    "suggest_focus":      {"morning": 0.9, "fresh": 1.0, "low": 0.6},
    "suggest_music":      {"evening": 0.8, "tired": 0.7, "neutral": 0.6},
}

def _context_fit_score(action: str, context: dict) -> float:
    fits = CONTEXT_FIT.get(action, {})
    if not fits:
        return 0.5
    signals = [
        context.get("time_of_day", ""),
        context.get("fatigue_level", ""),
        context.get("user_activity_state", ""),
    ]
    score = 0.5
    for sig in signals:
        if sig in fits:
            score = max(score, fits[sig])
    return score


def _recency_penalty(action: str) -> float:
    last = _shown_history.get(action, 0.0)
    elapsed = time.time() - last
    if elapsed < SPAM_WINDOW_S:
        return 1.0 - (elapsed / SPAM_WINDOW_S)
    return 0.0


def _diversity_bonus(action: str, shown_count: int) -> float:
    if shown_count == 0:
        return 0.1
    return max(0.0, 0.1 - shown_count * 0.02)


def score_candidate(
    candidate: dict,
    context: dict,
    learned_weights: dict,
    shown_counts: dict,
) -> float:
    action = candidate.get("action", "")
    base_conf = float(candidate.get("confidence", 0.5))
    learned = float(learned_weights.get(action, 0.5))
    ctx_fit = _context_fit_score(action, context)
    shown = shown_counts.get(action, 0)
    diversity = _diversity_bonus(action, shown)
    penalty = _recency_penalty(action)

    raw = (
        base_conf * 0.35 +
        learned   * 0.35 +
        ctx_fit   * 0.20 +
        diversity * 0.10
    ) * (1.0 - penalty * 0.8)
    return round(raw, 4)


def choose_best(
    candidates: list[dict],
    context_snapshot: dict,
    learned_weights: Optional[dict] = None,
    shown_counts: Optional[dict] = None,
) -> Optional[dict]:
    """
    Pick the highest-scoring candidate above MIN_THRESHOLD.
    Returns None if no candidate qualifies.
    Updates _shown_history on selection.
    """
    learned_weights = learned_weights or {}
    shown_counts = shown_counts or {}

    best = None
    best_score = MIN_THRESHOLD

    for c in candidates:
        s = score_candidate(c, context_snapshot, learned_weights, shown_counts)
        if s > best_score:
            best_score = s
            best = c

    if best:
        action = best.get("action", "")
        _shown_history[action] = time.time()
        best = dict(best)
        best["final_score"] = best_score

    return best
