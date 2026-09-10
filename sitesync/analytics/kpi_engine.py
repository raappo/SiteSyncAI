"""
SiteSync AI — KPI Engine

Computes project performance KPIs from the schedule database:
- Overall % complete
- Schedule Performance Index (SPI)
- Activities by status (on-track / at-risk / behind)
- Discipline-wise breakdown
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import datetime

from sitesync.db.models import ScheduleActivity
from sitesync.db.session import get_db

@dataclass
class DisciplineKPI:
    discipline: str
    total_activities: int
    avg_progress: float
    on_track: int
    at_risk: int
    behind: int
    completed: int

@dataclass
class KPIReport:
    overall_progress: float
    total_activities: int
    completed_activities: int
    on_track_count: int
    at_risk_count: int
    behind_count: int
    auto_applied_count: int
    pending_review_count: int
    spi: float  # Schedule Performance Index
    disciplines: list[DisciplineKPI] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.datetime.now().isoformat()

def compute_kpis() -> KPIReport:
    """
    Query the database and compute all KPIs.
    Returns a KPIReport dataclass.
    """
    today_str = datetime.date.today().isoformat()

    with get_db() as db:
        activities = db.query(ScheduleActivity).all()
        db.expunge_all()

    if not activities:
        return KPIReport(
            overall_progress=0.0,
            total_activities=0,
            completed_activities=0,
            on_track_count=0,
            at_risk_count=0,
            behind_count=0,
            auto_applied_count=0,
            pending_review_count=0,
            spi=1.0,
        )

    total = len(activities)
    progresses = [a.progress_pct or 0.0 for a in activities]
    overall_progress = sum(progresses) / total if total > 0 else 0.0
    completed = sum(1 for p in progresses if p >= 100.0)

    on_track, at_risk, behind = 0, 0, 0
    for a in activities:
        pct = a.progress_pct or 0.0
        if pct >= 100:
            on_track += 1
        elif a.planned_end and a.planned_end < today_str:
            # Overdue — check severity
            if pct >= 80:
                at_risk += 1
            else:
                behind += 1
        elif a.planned_end and a.planned_end > today_str:
            on_track += 1
        else:
            at_risk += 1

    # SPI: earned value / planned value (simplified)
    planned_progress = 0.0
    earned = 0.0
    for a in activities:
        if a.planned_start and a.planned_end:
            try:
                ps = datetime.date.fromisoformat(a.planned_start)
                pe = datetime.date.fromisoformat(a.planned_end)
                today = datetime.date.today()
                total_days = max((pe - ps).days, 1)
                elapsed = max(min((today - ps).days, total_days), 0)
                planned_pct = (elapsed / total_days) * 100.0
                planned_progress += planned_pct
                earned += a.progress_pct or 0.0
            except Exception:
                pass
    spi = (earned / planned_progress) if planned_progress > 0 else 1.0
    spi = round(min(spi, 2.0), 3)  # cap at 2.0

    # Discipline breakdown
    disc_map: dict[str, list[ScheduleActivity]] = {}
    for a in activities:
        disc_map.setdefault(a.discipline, []).append(a)

    discipline_kpis = []
    for disc, acts in disc_map.items():
        d_progresses = [a.progress_pct or 0.0 for a in acts]
        d_on_track, d_at_risk, d_behind = 0, 0, 0
        for a in acts:
            pct = a.progress_pct or 0.0
            if pct >= 100:
                d_on_track += 1
            elif a.planned_end and a.planned_end < today_str:
                if pct >= 80:
                    d_at_risk += 1
                else:
                    d_behind += 1
            else:
                d_on_track += 1
        discipline_kpis.append(DisciplineKPI(
            discipline=disc,
            total_activities=len(acts),
            avg_progress=sum(d_progresses) / len(d_progresses),
            on_track=d_on_track,
            at_risk=d_at_risk,
            behind=d_behind,
            completed=sum(1 for p in d_progresses if p >= 100),
        ))

    # Get event counts from DB
    from sitesync.db.models import EventLog, ReviewQueueItem
    with get_db() as db:
        auto_applied = db.query(EventLog).filter(EventLog.auto_applied == True).count()
        pending_review = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "PENDING").count()

    return KPIReport(
        overall_progress=round(overall_progress, 1),
        total_activities=total,
        completed_activities=completed,
        on_track_count=on_track,
        at_risk_count=at_risk,
        behind_count=behind,
        auto_applied_count=auto_applied,
        pending_review_count=pending_review,
        spi=spi,
        disciplines=sorted(discipline_kpis, key=lambda d: d.discipline),
    )
