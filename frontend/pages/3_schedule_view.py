"""
SiteSync AI — Page 3: Live Schedule View

Displays baseline vs. actual progress for all L5/L6 activities.
Color-coded by discipline and confidence tier.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from frontend.styles import apply_custom_css

st.set_page_config(page_title="Schedule View | SiteSync AI", page_icon="📊", layout="wide")
apply_custom_css()

DISC_COLORS = {
    "Civil": "#f97316",
    "Piping": "#38bdf8",
    "Electrical": "#a78bfa",
    "Instrumentation": "#34d399",
    "HSE": "#f43f5e",
}

st.markdown("# 📊 Live Schedule View")
st.markdown("*Baseline plan vs. actual progress — updated in real time from field submissions.*")
st.divider()

try:
    from sitesync.db.models import EventLog, ScheduleActivity
    from sitesync.db.session import get_db

    with get_db() as db:
        activities = db.query(ScheduleActivity).order_by(
            ScheduleActivity.discipline, ScheduleActivity.activity_id
        ).all()
        db.expunge_all()

    if not activities:
        st.warning("No schedule activities found. Run: `uv run python -m sitesync.db.seed`")
        st.stop()

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    disciplines = sorted(list(set(a.discipline for a in activities)))
    with col_f1:
        disc_filter = st.multiselect("Filter Discipline", disciplines, default=disciplines)
    with col_f2:
        progress_filter = st.selectbox("Progress Filter", ["All", "Not Started", "In Progress", "Complete"])
    with col_f3:
        sort_by = st.selectbox("Sort By", ["Activity ID", "Discipline", "Progress % (low→high)", "Progress % (high→low)"])

    # Apply filters
    filtered = [a for a in activities if a.discipline in disc_filter]
    if progress_filter == "Not Started":
        filtered = [a for a in filtered if (a.progress_pct or 0) == 0]
    elif progress_filter == "In Progress":
        filtered = [a for a in filtered if 0 < (a.progress_pct or 0) < 100]
    elif progress_filter == "Complete":
        filtered = [a for a in filtered if (a.progress_pct or 0) >= 100]

    # Sort
    if sort_by == "Progress % (low→high)":
        filtered.sort(key=lambda a: a.progress_pct or 0)
    elif sort_by == "Progress % (high→low)":
        filtered.sort(key=lambda a: -(a.progress_pct or 0))
    elif sort_by == "Discipline":
        filtered.sort(key=lambda a: (a.discipline, a.activity_id))

    # ── Summary metrics ────────────────────────────────────────────────────────
    total = len(filtered)
    not_started = sum(1 for a in filtered if (a.progress_pct or 0) == 0)
    in_prog = sum(1 for a in filtered if 0 < (a.progress_pct or 0) < 100)
    complete = sum(1 for a in filtered if (a.progress_pct or 0) >= 100)
    avg_prog = sum(a.progress_pct or 0 for a in filtered) / max(total, 1)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{total}</div><div class="kpi-label">Total Activities</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{not_started}</div><div class="kpi-label">Not Started</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{in_prog}</div><div class="kpi-label">In Progress</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{complete}</div><div class="kpi-label">Complete</div></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{avg_prog:.1f}%</div><div class="kpi-label">Avg Progress</div></div>', unsafe_allow_html=True)
    st.divider()

    # ── Early Warning Strip ───────────────────────────────────────────────────
    # Simulating behind-schedule logic: Any activity < 20% progress but should be done.
    # In a real PMIS, this would check planned_end against today's date.
    behind_schedule = [a for a in filtered if (a.progress_pct or 0) < 20 and a.planned_end and a.planned_end < "2024-03-01"]
    if behind_schedule:
        st.error(f"⚠️ **Early Warning:** {len(behind_schedule)} activities are critically behind schedule and threatening the critical path.")
        with st.expander("View Critical Delays"):
            for act in behind_schedule[:5]:
                st.markdown(f"- **{act.activity_id}** ({act.discipline}): {act.description} | {act.progress_pct or 0}% completed vs planned end date {act.planned_end}")
    
    # ── Discipline overview chart ──────────────────────────────────────────────
    with st.expander("📈 Discipline Progress Overview", expanded=True):
        disc_data = {}
        for a in activities:
            if a.discipline not in disc_data:
                disc_data[a.discipline] = {"planned": 0, "actual": 0, "count": 0}
            disc_data[a.discipline]["count"] += 1
            disc_data[a.discipline]["actual"] += (a.progress_pct or 0)

        chart_df = pd.DataFrame([
            {
                "Discipline": disc,
                "Avg Progress %": vals["actual"] / vals["count"],
                "Activities": vals["count"]
            }
            for disc, vals in disc_data.items()
        ])
        st.bar_chart(chart_df.set_index("Discipline")["Avg Progress %"])

    # ── Activity cards ────────────────────────────────────────────────────────
    st.markdown(f"### Activities ({len(filtered)})")

    # Group by discipline
    by_disc: dict[str, list] = {}
    for a in filtered:
        by_disc.setdefault(a.discipline, []).append(a)

    for disc, acts in by_disc.items():
        color = DISC_COLORS.get(disc, "#94a3b8")
        st.markdown(f"<h4 style='color:{color}'>● {disc} ({len(acts)} activities)</h4>", unsafe_allow_html=True)

        for act in acts:
            pct = act.progress_pct or 0
            bar_color = color
            if pct >= 100:
                status_icon = "✅"
            elif pct > 0:
                status_icon = "🔄"
            else:
                status_icon = "⭕"
            
            st.markdown('<div class="card-container">', unsafe_allow_html=True)
            col_id, col_desc, col_dates, col_prog = st.columns([1.5, 4, 2, 2.5])
            with col_id:
                st.markdown(f"**`{act.activity_id}`**")
                if act.wbs_code:
                    st.caption(act.wbs_code)
            with col_desc:
                st.markdown(f"{status_icon} {act.description}")
                if act.location:
                    st.caption(f"📍 {act.location}")
            with col_dates:
                st.caption(f"Plan: {act.planned_start or '?'} → {act.planned_end or '?'}")
                if act.actual_start:
                    st.caption(f"Actual start: {act.actual_start}")
            with col_prog:
                # Custom progress bar
                bar_width = max(2, pct)
                st.markdown(
                    f"""<div style="margin-top:4px;">
                    <div style="font-size:0.85rem; font-weight:600; color:{bar_color}; margin-bottom:3px;">{pct:.1f}%</div>
                    <div style="background:#0F172A; border-radius:6px; height:8px; width:100%;">
                      <div style="background:{bar_color}; width:{bar_width}%; height:8px; border-radius:6px; transition:width 0.4s;"></div>
                    </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("### 📥 Export")
    export_data = [
        {
            "Activity ID": a.activity_id,
            "WBS Code": a.wbs_code,
            "Discipline": a.discipline,
            "Description": a.description,
            "Location": a.location,
            "Planned Start": a.planned_start,
            "Planned End": a.planned_end,
            "Progress %": a.progress_pct,
            "Actual Start": a.actual_start,
            "Actual End": a.actual_end,
        }
        for a in filtered
    ]
    df_export = pd.DataFrame(export_data)
    csv_bytes = df_export.to_csv(index=False).encode()
    st.download_button("⬇️ Download Schedule CSV", data=csv_bytes, file_name="sitesync_schedule.csv", mime="text/csv")

except Exception as e:
    st.error(f"Error loading schedule: {e}")
    import traceback
    st.code(traceback.format_exc())
