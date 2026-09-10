"""
SiteSync AI — Gantt Chart Builder

Builds a professional Plotly Gantt chart with:
- Planned bars (transparent)
- Actual progress overlay
- Today's date line
- Status color coding (On Track / At Risk / Behind)
- Discipline grouping
"""
from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from sitesync.db.models import ScheduleActivity
from sitesync.db.session import get_db

def _get_status(activity: ScheduleActivity, today_str: str) -> str:
    pct = activity.progress_pct or 0.0
    if pct >= 100:
        return "Completed"
    if activity.planned_end and activity.planned_end < today_str:
        return "Behind" if pct < 80 else "At Risk"
    if activity.planned_end and activity.planned_end <= (datetime.date.today() + datetime.timedelta(days=7)).isoformat():
        if pct < 50:
            return "At Risk"
    return "On Track"

def build_gantt(
    discipline_filter: Optional[str] = None,
    max_activities: int = 40,
) -> go.Figure:
    """
    Build and return a Plotly Gantt figure.
    
    Args:
        discipline_filter: Optional discipline to filter by.
        max_activities: Max number of activities to display.
    
    Returns:
        Plotly Figure object.
    """
    today = datetime.date.today()
    today_str = today.isoformat()

    with get_db() as db:
        query = db.query(ScheduleActivity)
        if discipline_filter:
            query = query.filter(ScheduleActivity.discipline == discipline_filter)
        activities = query.limit(max_activities).all()
        db.expunge_all()

    if not activities:
        fig = go.Figure()
        fig.add_annotation(
            text="No schedule activities found. Please seed the database first.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#8B949E")
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0D1117",
            plot_bgcolor="#0D1117",
            height=400,
        )
        return fig

    status_colors = {
        "On Track": "#2EA043",
        "At Risk": "#D29922",
        "Behind": "#DA3633",
        "Completed": "#388BFD",
    }

    # Build planned bars
    planned_bars = []
    actual_bars = []

    for a in activities:
        if not a.planned_start or not a.planned_end:
            continue

        try:
            ps = datetime.date.fromisoformat(a.planned_start)
            pe = datetime.date.fromisoformat(a.planned_end)
        except ValueError:
            continue

        status = _get_status(a, today_str)
        color = status_colors.get(status, "#58A6FF")
        label = f"{a.activity_id}: {a.description[:35]}..."
        pct = a.progress_pct or 0.0

        # Planned bar (semi-transparent)
        planned_bars.append(dict(
            task=label,
            start=str(ps),
            finish=str(pe),
            status=status,
            discipline=a.discipline,
            progress=pct,
            activity_id=a.activity_id,
            color=color,
        ))

        # Actual progress bar
        total_days = max((pe - ps).days, 1)
        actual_days = int(total_days * pct / 100)
        actual_end = ps + datetime.timedelta(days=actual_days)
        actual_bars.append(dict(
            task=label,
            start=str(ps),
            finish=str(min(actual_end, pe)),
            progress=pct,
            color=color,
        ))

    if not planned_bars:
        fig = go.Figure()
        fig.add_annotation(text="No activities with planned dates found.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    df_planned = pd.DataFrame(planned_bars)
    df_actual = pd.DataFrame(actual_bars)

    tasks = df_planned["task"].tolist()

    fig = go.Figure()

    # Add planned bars (light/transparent)
    for _, row in df_planned.iterrows():
        fig.add_trace(go.Bar(
            name=row["status"],
            x=[(pd.to_datetime(row["finish"]) - pd.to_datetime(row["start"])).days],
            y=[row["task"]],
            orientation="h",
            base=[pd.to_datetime(row["start"]).timestamp() * 1000],
            marker=dict(
                color=row["color"],
                opacity=0.25,
                line=dict(color=row["color"], width=1),
            ),
            hovertemplate=(
                f"<b>{row['activity_id']}</b><br>"
                f"Planned: {row['start']} → {row['finish']}<br>"
                f"Progress: {row['progress']:.0f}%<br>"
                f"Status: {row['status']}<extra></extra>"
            ),
            showlegend=False,
        ))

    # Add actual bars (solid)
    for _, row in df_actual.iterrows():
        dur = (pd.to_datetime(row["finish"]) - pd.to_datetime(row["start"])).days
        if dur <= 0:
            continue
        fig.add_trace(go.Bar(
            name="Actual",
            x=[dur],
            y=[row["task"]],
            orientation="h",
            base=[pd.to_datetime(row["start"]).timestamp() * 1000],
            marker=dict(
                color=row["color"],
                opacity=0.85,
            ),
            hovertemplate=f"Actual progress: {row['progress']:.0f}%<extra></extra>",
            showlegend=False,
        ))

    # Today's line
    today_ms = pd.to_datetime(today_str).timestamp() * 1000
    fig.add_shape(
        type="line",
        x0=today_ms, x1=today_ms,
        y0=-0.5, y1=len(tasks) - 0.5,
        line=dict(color="#F0A500", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=today_ms, y=len(tasks) - 0.5,
        text="Today",
        showarrow=False,
        font=dict(color="#F0A500", size=11),
        yshift=10,
    )

    # Layout
    fig.update_layout(
        title=dict(
            text="📅 Project Schedule — Planned vs Actual",
            font=dict(size=16, color="#E6EDF3"),
        ),
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        height=max(400, len(tasks) * 28 + 100),
        xaxis=dict(
            type="date",
            tickformat="%b %Y",
            gridcolor="#21262D",
            showgrid=True,
            title="",
            rangeslider=dict(visible=True, thickness=0.05),
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=10),
            gridcolor="#21262D",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=20, r=20, t=60, b=40),
        hoverlabel=dict(
            bgcolor="#1C2128",
            bordercolor="#30363D",
            font=dict(color="#E6EDF3"),
        ),
    )

    return fig
