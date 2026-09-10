"""
SiteSync AI — Fuzzy Schedule-Linking Matcher

Loads all ScheduleActivity embeddings from SQLite into an in-memory numpy
matrix. For each extracted ActivityUpdate, computes cosine similarity
against all schedule nodes and returns the top-K matches with full
confidence scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from sitesync.config import settings
from sitesync.extraction.schemas import ActivityUpdate
from sitesync.linking.confidence import compute_confidence
from sitesync.linking.embedder import deserialize, embed_text


@dataclass
class MatchResult:
    """A single candidate match from the schedule DB."""
    activity_id: str
    description: str
    discipline: str
    location: Optional[str]
    planned_start: Optional[str]
    planned_end: Optional[str]
    wbs_code: Optional[str]
    semantic_score: float
    evidence_weight: float
    temporal_score: float
    confidence: float
    rank: int = 1


@dataclass
class LinkingResult:
    """Full output of the linking step for one ActivityUpdate."""
    update: ActivityUpdate
    top_matches: list[MatchResult] = field(default_factory=list)
    best_match: Optional[MatchResult] = None
    is_unmatched: bool = False  # True if no match found
    error: Optional[str] = None


class ScheduleMatcher:
    """
    In-memory cosine similarity matcher.

    The embedding matrix is built on first call and cached.
    Call refresh() to reload after a DB seed.
    """

    def __init__(self):
        self._activities: list = []  # list of ScheduleActivity ORM rows
        self._matrix: Optional[np.ndarray] = None  # (N, D) embedding matrix
        self._loaded = False

    def _load(self, force: bool = False):
        """Load all embeddings from SQLite into a numpy matrix."""
        if self._loaded and not force:
            return

        from sitesync.db.models import ScheduleActivity
        from sitesync.db.session import get_db

        with get_db() as db:
            self._activities = (
                db.query(ScheduleActivity)
                .filter(ScheduleActivity.embedding.isnot(None))
                .all()
            )
            # Detach from session so we can use after context closes
            db.expunge_all()

        if not self._activities:
            self._matrix = None
            self._loaded = True
            return

        vecs = np.stack([deserialize(a.embedding) for a in self._activities])
        self._matrix = vecs.astype(np.float32)
        self._loaded = True

    def refresh(self):
        """Force reload embeddings from DB (call after seed)."""
        self._loaded = False
        self._load(force=True)

    def match(
        self,
        update: ActivityUpdate,
        top_k: int = 3,
        min_semantic_score: float = 0.30,
    ) -> LinkingResult:
        """
        Match a single ActivityUpdate to the schedule.

        Args:
            update: Extracted field activity.
            top_k: Number of top candidates to return.
            min_semantic_score: Minimum cosine similarity to even consider.

        Returns:
            LinkingResult with ranked candidates and confidence scores.
        """
        self._load()

        if self._matrix is None or len(self._activities) == 0:
            return LinkingResult(
                update=update,
                error="No schedule activities loaded. Run the DB seed first.",
                is_unmatched=True,
            )

        # Embed the query
        query_vec = embed_text(update.activity_description).reshape(1, -1)

        # Cosine similarity against all schedule embeddings
        sims = cosine_similarity(query_vec, self._matrix)[0]  # shape (N,)

        # Get top-K indices sorted descending
        top_indices = np.argsort(sims)[::-1][:top_k]

        matches: list[MatchResult] = []
        for rank, idx in enumerate(top_indices, start=1):
            sem_score = float(sims[idx])
            if sem_score < min_semantic_score:
                break

            activity = self._activities[idx]
            conf, s, e, t = compute_confidence(
                semantic_score=sem_score,
                evidence_type=update.evidence_type,
                report_date=update.date,
                planned_start=activity.planned_start,
                planned_end=activity.planned_end,
            )

            matches.append(
                MatchResult(
                    activity_id=activity.activity_id,
                    description=activity.description,
                    discipline=activity.discipline,
                    location=activity.location,
                    planned_start=activity.planned_start,
                    planned_end=activity.planned_end,
                    wbs_code=activity.wbs_code,
                    semantic_score=s,
                    evidence_weight=e,
                    temporal_score=t,
                    confidence=conf,
                    rank=rank,
                )
            )

        best = matches[0] if matches else None
        is_unmatched = best is None or best.confidence < 0.30

        return LinkingResult(
            update=update,
            top_matches=matches,
            best_match=best,
            is_unmatched=is_unmatched,
        )

    def match_batch(
        self, updates: list[ActivityUpdate], top_k: int = 3
    ) -> list[LinkingResult]:
        """Match a batch of ActivityUpdates efficiently."""
        return [self.match(u, top_k=top_k) for u in updates]


# Module-level singleton
_matcher: Optional[ScheduleMatcher] = None


def get_matcher() -> ScheduleMatcher:
    global _matcher
    if _matcher is None:
        _matcher = ScheduleMatcher()
    return _matcher


def match(update: ActivityUpdate, top_k: int = 3) -> LinkingResult:
    """Convenience function."""
    return get_matcher().match(update, top_k=top_k)
