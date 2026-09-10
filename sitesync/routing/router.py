"""
SiteSync AI — Routing Engine

Decision logic:
  confidence >= threshold (default 0.85): auto-update schedule + write EventLog
  confidence <  threshold OR contradiction: write ReviewQueueItem (PENDING)
  ALL events are logged — nothing is silently dropped.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from rich.console import Console

from sitesync.config import settings
from sitesync.db.models import EventLog, ReviewQueueItem, ScheduleActivity
from sitesync.db.session import get_db
from sitesync.linking.matcher import LinkingResult

console = Console()


def _detect_contradiction(
    activity: ScheduleActivity,
    new_progress: float,
) -> bool:
    """
    Detect contradictions: e.g., new progress is significantly LOWER
    than the current recorded progress (regression without reason).
    Threshold: more than 10 percentage points lower.
    """
    current = activity.progress_pct or 0.0
    return new_progress < (current - 10.0)


def route(linking_result: LinkingResult, source_file: Optional[str] = None) -> EventLog:
    """
    Route a linking result to either auto-apply or the review queue.

    Returns:
        The EventLog record created (always).
    """
    update = linking_result.update
    best = linking_result.best_match

    with get_db() as db:
        # ── Build EventLog (always created) ──────────────────────────────
        event = EventLog(
            raw_input=update.activity_description,
            source_file=source_file,
            evidence_type=update.evidence_type,
            extracted_json=json.dumps(update.model_dump(mode="json")),
            matched_activity_id=best.activity_id if best else None,
            semantic_score=best.semantic_score if best else None,
            evidence_weight=best.evidence_weight if best else None,
            temporal_score=best.temporal_score if best else None,
            confidence_score=best.confidence if best else None,
        )

        # ── Case 1: No match at all ────────────────────────────────────────
        if linking_result.is_unmatched or best is None:
            event.sent_to_review = True
            db.add(event)
            db.flush()

            queue_item = ReviewQueueItem(
                event_log_fk=event.id,
                status="PENDING",
                planner_notes="No confident schedule match found — review and remap.",
            )
            db.add(queue_item)
            console.print(
                f"[yellow]📋 REVIEW QUEUE (no match): {update.activity_description[:60]}[/yellow]"
            )
            db.flush()
            db.refresh(event)
            db.expunge(event)
            return event

        # ── Load matched schedule activity ─────────────────────────────────
        activity = (
            db.query(ScheduleActivity)
            .filter(ScheduleActivity.activity_id == best.activity_id)
            .first()
        )
        if activity:
            event.activity_fk = activity.id

        # ── Check for contradiction ────────────────────────────────────────
        contradiction = False
        if activity and activity.progress_pct is not None:
            contradiction = _detect_contradiction(activity, update.actual_progress_pct)

        # ── Case 2: High confidence, no contradiction → auto-apply ────────
        if best.confidence >= settings.confidence_threshold and not contradiction:
            event.auto_applied = True
            db.add(event)

            if activity:
                # Update schedule
                old_pct = activity.progress_pct
                activity.progress_pct = max(activity.progress_pct or 0.0, update.actual_progress_pct)
                if not activity.actual_start and update.actual_progress_pct > 0:
                    activity.actual_start = update.date
                if update.actual_progress_pct >= 100.0:
                    activity.actual_end = update.date

                console.print(
                    f"[green]✅ AUTO-APPLIED: {best.activity_id} "
                    f"({old_pct:.0f}% → {activity.progress_pct:.0f}%) "
                    f"conf={best.confidence:.3f}[/green]"
                )
            db.flush()
            db.refresh(event)
            db.expunge(event)
            return event

        # ── Case 3: Low confidence or contradiction → review queue ─────────
        event.sent_to_review = True
        db.add(event)
        db.flush()

        reason = "Contradiction detected (progress regression)" if contradiction else \
                 f"Confidence {best.confidence:.2f} < threshold {settings.confidence_threshold}"

        queue_item = ReviewQueueItem(
            event_log_fk=event.id,
            status="PENDING",
            planner_notes=f"Manual review required. Reason: {reason}",
        )
        db.add(queue_item)

        console.print(
            f"[yellow]📋 REVIEW QUEUE: {update.activity_description[:50]} "
            f"→ {best.activity_id} conf={best.confidence:.3f} | {reason}[/yellow]"
        )
        db.flush()
        db.refresh(event)
        db.expunge(event)
        return event
