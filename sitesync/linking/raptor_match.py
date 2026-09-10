"""
SiteSync AI — Hybrid Activity Matcher (Semantic + RapidFuzz)

Extends the base semantic matcher with RapidFuzz token_sort_ratio
for construction-domain fuzzy string matching.

Hybrid score = 0.65 * semantic_cosine + 0.35 * fuzzy_ratio

Also includes a construction abbreviation expander to normalize
field jargon before matching.
"""
from __future__ import annotations

from typing import Optional

from sitesync.extraction.schemas import ActivityUpdate
from sitesync.linking.matcher import LinkingResult, MatchResult, get_matcher

# Construction domain abbreviation dictionary
ABBREV_MAP = {
    "rcc": "reinforced cement concrete",
    "pcc": "plain cement concrete",
    "wbs": "work breakdown structure",
    "mep": "mechanical electrical plumbing",
    "jcb": "excavator backhoe",
    "hse": "health safety environment",
    "cpm": "critical path method",
    "di": "ductile iron",
    "gi": "galvanized iron",
    "ms": "mild steel",
    "cs": "carbon steel",
    "ss": "stainless steel",
    "f/w": "formwork",
    "r/f": "reinforcement",
    "exc": "excavation",
    "backfill": "backfilling",
    "inst": "instrumentation",
    "elec": "electrical",
    "hvac": "heating ventilation air conditioning",
    "epc": "engineering procurement construction",
    "piping": "pipe pipeline piping",
    "spool": "prefabricated pipe spool",
}

def _expand_abbreviations(text: str) -> str:
    """Expand construction abbreviations in text."""
    words = text.lower().split()
    expanded = [ABBREV_MAP.get(w, w) for w in words]
    return " ".join(expanded)

def hybrid_match(
    update: ActivityUpdate,
    top_k: int = 3,
    min_semantic_score: float = 0.25,
) -> LinkingResult:
    """
    Hybrid activity matching: semantic similarity + RapidFuzz fuzzy matching.
    Falls back gracefully if rapidfuzz is not installed.
    """
    matcher = get_matcher()
    result = matcher.match(update, top_k=top_k * 2, min_semantic_score=min_semantic_score)

    if result.is_unmatched or not result.top_matches:
        return result

    try:
        from rapidfuzz import fuzz
        expanded_query = _expand_abbreviations(update.activity_description)

        enhanced_matches = []
        for match in result.top_matches:
            expanded_desc = _expand_abbreviations(match.description)
            fuzzy_score = fuzz.token_sort_ratio(expanded_query, expanded_desc) / 100.0

            # Hybrid score: 65% semantic + 35% fuzzy
            hybrid_score = 0.65 * match.semantic_score + 0.35 * fuzzy_score

            from sitesync.linking.confidence import compute_confidence
            conf, s, e, t = compute_confidence(
                semantic_score=hybrid_score,
                evidence_type=update.evidence_type,
                report_date=update.date,
                planned_start=match.planned_start,
                planned_end=match.planned_end,
            )

            enhanced_matches.append(MatchResult(
                activity_id=match.activity_id,
                description=match.description,
                discipline=match.discipline,
                location=match.location,
                planned_start=match.planned_start,
                planned_end=match.planned_end,
                wbs_code=match.wbs_code,
                semantic_score=hybrid_score,
                evidence_weight=e,
                temporal_score=t,
                confidence=conf,
                rank=0,
            ))

        enhanced_matches.sort(key=lambda m: m.confidence, reverse=True)
        for i, m in enumerate(enhanced_matches[:top_k], start=1):
            m.rank = i

        top_k_matches = enhanced_matches[:top_k]
        best = top_k_matches[0] if top_k_matches else None
        is_unmatched = best is None or best.confidence < 0.30

        return LinkingResult(
            update=update,
            top_matches=top_k_matches,
            best_match=best,
            is_unmatched=is_unmatched,
        )

    except ImportError:
        return result
