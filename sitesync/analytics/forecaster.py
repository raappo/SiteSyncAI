"""
SiteSync AI — Schedule Forecaster

Provides earned-value-based forecasting:
- Estimate completion date based on current SPI
- Identify critical activities that are behind
- Generate delay pattern insights
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from sitesync.db.models import ScheduleActivity
from sitesync.db.session import get_db

@dataclass
class ActivityForecast:
    activity_id: str
    description: str
    discipline: str
    planned_end: Optional[str]
    current_progress: float
    estimated_completion: Optional[str]
    delay_days: int
    is_critical: bool

@dataclass
class ProjectForecast:
    estimated_completion_date: Optional[str]
    baseline_completion_date: Optional[str]
    delay_days: int
    spi: float
    critical_activities: list[ActivityForecast]
    at_risk_activities: list[ActivityForecast]
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.datetime.now().isoformat()

def compute_forecast() -> ProjectForecast:
    """Compute project-level schedule forecast."""
    today = datetime.date.today()
    today_str = today.isoformat()

    with get_db() as db:
        activities = db.query(ScheduleActivity).all()
        db.expunge_all()

    if not activities:
        return ProjectForecast(
            estimated_completion_date=None,
            baseline_completion_date=None,
            delay_days=0,
            spi=1.0,
            critical_activities=[],
            at_risk_activities=[],
        )

    # Find project baseline end
    planned_ends = [a.planned_end for a in activities if a.planned_end]
    baseline_end = max(planned_ends) if planned_ends else None

    critical = []
    at_risk = []

    for a in activities:
        pct = a.progress_pct or 0.0
        if pct >= 100 or not a.planned_start or not a.planned_end:
            continue

        try:
            ps = datetime.date.fromisoformat(a.planned_start)
            pe = datetime.date.fromisoformat(a.planned_end)
        except ValueError:
            continue

        total_days = max((pe - ps).days, 1)
        elapsed = max((today - ps).days, 0)

        # Expected progress by today
        expected_pct = min((elapsed / total_days) * 100, 100)

        # Estimate completion based on current velocity
        remaining_pct = 100 - pct
        if pct > 0 and elapsed > 0:
            daily_rate = pct / elapsed
            days_to_complete = remaining_pct / daily_rate if daily_rate > 0 else total_days * 2
        else:
            days_to_complete = total_days * 2

        est_completion = today + datetime.timedelta(days=int(days_to_complete))
        delay_days = max((est_completion - pe).days, 0)

        forecast = ActivityForecast(
            activity_id=a.activity_id,
            description=a.description[:60],
            discipline=a.discipline,
            planned_end=a.planned_end,
            current_progress=pct,
            estimated_completion=est_completion.isoformat(),
            delay_days=delay_days,
            is_critical=(a.planned_end and a.planned_end < today_str and pct < 100),
        )

        variance = pct - expected_pct
        if variance < -20 or (a.planned_end and a.planned_end < today_str):
            critical.append(forecast)
        elif variance < -10:
            at_risk.append(forecast)

    # Project SPI
    planned_sum, earned_sum = 0.0, 0.0
    for a in activities:
        if a.planned_start and a.planned_end:
            try:
                ps = datetime.date.fromisoformat(a.planned_start)
                pe = datetime.date.fromisoformat(a.planned_end)
                total_days = max((pe - ps).days, 1)
                elapsed = max(min((today - ps).days, total_days), 0)
                planned_sum += (elapsed / total_days) * 100
                earned_sum += a.progress_pct or 0.0
            except Exception:
                pass
    spi = round(earned_sum / planned_sum, 3) if planned_sum > 0 else 1.0

    # Estimate project completion
    if baseline_end and spi > 0:
        try:
            be = datetime.date.fromisoformat(baseline_end)
            total_project_days = max((be - datetime.date(2025, 1, 1)).days, 1)
            projected_days = int(total_project_days / spi)
            est_project_completion = (datetime.date(2025, 1, 1) + datetime.timedelta(days=projected_days)).isoformat()
        except Exception:
            est_project_completion = None
    else:
        est_project_completion = None

    try:
        delay_days = max((datetime.date.fromisoformat(est_project_completion) - datetime.date.fromisoformat(baseline_end)).days, 0) if est_project_completion and baseline_end else 0
    except Exception:
        delay_days = 0

    return ProjectForecast(
        estimated_completion_date=est_project_completion,
        baseline_completion_date=baseline_end,
        delay_days=delay_days,
        spi=spi,
        critical_activities=sorted(critical, key=lambda x: x.delay_days, reverse=True)[:10],
        at_risk_activities=sorted(at_risk, key=lambda x: x.delay_days, reverse=True)[:10],
    )
