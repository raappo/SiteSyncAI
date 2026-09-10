"""
SiteSync AI — Multi-Signal Confidence Scorer

Formula:
    confidence = (0.6 × semantic_score)
               + (0.25 × evidence_weight)
               + (0.15 × temporal_score)

Semantic score  : cosine similarity (0–1) between extracted description and schedule node
Evidence weight : photo=1.0, spreadsheet=0.85, scanned_doc=0.75, text=0.60
Temporal score  : 1.0 if report date within planned window, linearly decays up to 30-day offset
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional


def compute_temporal_score(
    report_date: Optional[str],
    planned_start: Optional[str],
    planned_end: Optional[str],
    max_offset_days: int = 30,
) -> float:
    """
    Score 1.0 if report date is within [planned_start, planned_end].
    Linearly decays to 0.0 at max_offset_days outside that window.
    Returns 0.5 (neutral) if dates are missing.
    """
    if not report_date or not planned_start or not planned_end:
        return 0.5  # neutral — cannot penalize what we don't know

    def _parse(d: str) -> Optional[date]:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(d, fmt).date()
            except ValueError:
                continue
        return None

    r_date = _parse(report_date)
    p_start = _parse(planned_start)
    p_end = _parse(planned_end)

    if not r_date or not p_start or not p_end:
        return 0.5

    if p_start <= r_date <= p_end:
        return 1.0

    # Outside window — compute offset
    if r_date < p_start:
        offset = (p_start - r_date).days
    else:
        offset = (r_date - p_end).days

    score = max(0.0, 1.0 - (offset / max_offset_days))
    return round(score, 4)


def compute_confidence(
    semantic_score: float,
    evidence_type: str,
    report_date: Optional[str] = None,
    planned_start: Optional[str] = None,
    planned_end: Optional[str] = None,
    evidence_weights: Optional[dict[str, float]] = None,
) -> tuple[float, float, float, float]:
    """
    Compute the multi-signal confidence score.

    Returns:
        (confidence, semantic_score, evidence_weight, temporal_score)
    """
    from sitesync.config import settings
    weights = evidence_weights or settings.evidence_weights
    evidence_weight = weights.get(evidence_type, 0.60)

    temporal_score = compute_temporal_score(report_date, planned_start, planned_end)

    confidence = (
        (0.6 * semantic_score)
        + (0.25 * evidence_weight)
        + (0.15 * temporal_score)
    )
    confidence = round(min(1.0, max(0.0, confidence)), 4)

    return confidence, round(semantic_score, 4), round(evidence_weight, 4), round(temporal_score, 4)
