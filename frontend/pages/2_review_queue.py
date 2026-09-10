"""
SiteSync AI — Page 2: Planner Review Queue

Shows all PENDING low-confidence / contradictory events.
Planner can: APPROVE (auto-apply), REJECT (discard), or REMAP (link to different activity).
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from frontend.styles import apply_custom_css

st.set_page_config(page_title="Review Queue | SiteSync AI", page_icon="📋", layout="wide")
apply_custom_css()


def status_badge(status: str) -> str:
    if status == "PENDING":
        return '<span class="badge badge-pending">⏳ PENDING</span>'
    elif status == "APPROVED":
        return '<span class="badge badge-auto">✅ APPROVED</span>'
    elif status == "REJECTED":
        return '<span class="badge badge-mismatch">🚫 REJECTED</span>'
    elif status == "REMAPPED":
        return '<span class="badge badge-neutral">🔄 REMAPPED</span>'
    return f'<span class="badge">{status}</span>'


st.markdown("# 📋 Planner Review Queue")
st.markdown("*Review low-confidence or contradictory field updates. Approve, reject, or remap to the correct activity.*")
st.divider()

try:
    from sitesync.db.models import EventLog, ReviewQueueItem, ScheduleActivity
    from sitesync.db.session import get_db

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        status_filter = st.selectbox("Filter by Status", ["ALL", "PENDING", "APPROVED", "REJECTED", "REMAPPED"])
    with col_f2:
        refresh = st.button("🔄 Refresh", type="secondary")

    # ── Metrics ───────────────────────────────────────────────────────────────
    with get_db() as db:
        all_items = db.query(ReviewQueueItem).order_by(ReviewQueueItem.created_at.desc()).all()
        all_events = {e.id: e for e in db.query(EventLog).all()}
        all_activities = {a.activity_id: a for a in db.query(ScheduleActivity).all()}

        # Detach
        for item in all_items:
            db.expunge(item)
        for ev in all_events.values():
            db.expunge(ev)

    pending = [i for i in all_items if i.status == "PENDING"]
    approved = [i for i in all_items if i.status == "APPROVED"]
    rejected = [i for i in all_items if i.status == "REJECTED"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏳ Pending", len(pending))
    m2.metric("✅ Approved", len(approved))
    m3.metric("🚫 Rejected", len(rejected))
    m4.metric("📋 Total", len(all_items))
    st.divider()

    if status_filter != "ALL":
        display_items = [i for i in all_items if i.status == status_filter]
    else:
        display_items = all_items

    if not display_items:
        st.info("🎉 No items in queue matching the filter.")
    else:
        st.markdown(f"**Showing {len(display_items)} item(s)**")

        for item in display_items:
            ev = all_events.get(item.event_log_fk)
            if not ev:
                continue

            extracted = json.loads(ev.extracted_json) if ev.extracted_json else {}

            with st.container():
                st.markdown(f'<div class="card-container">', unsafe_allow_html=True)

                top_row = st.columns([4, 2, 2])
                with top_row[0]:
                    st.markdown(
                        f"**#{item.id}** {status_badge(item.status)}  "
                        f"`{extracted.get('discipline','?')}` · `{ev.matched_activity_id or 'UNMATCHED'}`",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"📝 {extracted.get('activity_description', ev.raw_input)[:80]}")
                with top_row[1]:
                    conf = ev.confidence_score or 0
                    st.metric("Confidence", f"{conf:.1%}")
                with top_row[2]:
                    st.markdown(f"**Date:** `{extracted.get('date','?')}`")
                    st.markdown(f"**Evidence:** `{ev.evidence_type}`")

                if item.status == "PENDING":
                    with st.expander("📂 Full details & actions"):
                        d1, d2 = st.columns(2)
                        with d1:
                            st.markdown("**Extracted JSON**")
                            st.json(extracted)
                        with d2:
                            st.markdown("**Multi-Signal Confidence Breakdown**")
                            
                            def make_bar(label: str, val: float, color: str):
                                w = max(2, int(val * 100))
                                return f"""
                                <div style="margin-bottom:8px;">
                                    <div style="font-size:0.8rem; color:#cbd5e1; margin-bottom:2px;">{label} ({val:.3f})</div>
                                    <div style="background:#0f172a; border-radius:4px; height:6px; width:100%;">
                                        <div style="background:{color}; width:{w}%; height:6px; border-radius:4px;"></div>
                                    </div>
                                </div>
                                """
                            
                            st.markdown(make_bar("Semantic Score", ev.semantic_score or 0, "#38bdf8"), unsafe_allow_html=True)
                            st.markdown(make_bar("Evidence Weight", ev.evidence_weight or 0, "#a78bfa"), unsafe_allow_html=True)
                            st.markdown(make_bar("Temporal Plausibility", ev.temporal_score or 0, "#34d399"), unsafe_allow_html=True)
                            st.markdown(make_bar("Final Confidence", ev.confidence_score or 0, "#facc15"), unsafe_allow_html=True)

                            if item.planner_notes:
                                st.warning(f"⚠️ {item.planner_notes}")

                        st.markdown("<br>", unsafe_allow_html=True)
                        a1, a2, a3 = st.columns(3)
                        with a1:
                            if st.button(f"✅ Approve #{item.id}", key=f"approve_{item.id}", type="primary", use_container_width=True):
                                with get_db() as db2:
                                    qi = db2.query(ReviewQueueItem).filter(ReviewQueueItem.id == item.id).first()
                                    ei = db2.query(EventLog).filter(EventLog.id == item.event_log_fk).first()
                                    if qi and ei:
                                        qi.status = "APPROVED"
                                        qi.reviewed_at = datetime.utcnow()
                                        ei.auto_applied = True
                                        # Apply to schedule if matched
                                        if ei.matched_activity_id:
                                            act = db2.query(ScheduleActivity).filter(
                                                ScheduleActivity.activity_id == ei.matched_activity_id
                                            ).first()
                                            if act and extracted.get("actual_progress_pct"):
                                                act.progress_pct = max(
                                                    act.progress_pct or 0,
                                                    float(extracted["actual_progress_pct"])
                                                )
                                        # Upsert to memory
                                        try:
                                            from sitesync.memory.chroma_store import upsert_event
                                            upsert_event(
                                                event_id=ei.id,
                                                activity_id=ei.matched_activity_id or "UNMATCHED",
                                                discipline=extracted.get("discipline", ""),
                                                activity_description=extracted.get("activity_description", ""),
                                                actual_progress_pct=extracted.get("actual_progress_pct", 0),
                                                report_date=extracted.get("date", ""),
                                                evidence_type=ei.evidence_type,
                                                confidence_score=ei.confidence_score,
                                            )
                                        except Exception:
                                            pass
                                st.success(f"✅ Item #{item.id} approved and applied!")
                                st.rerun()

                        with a2:
                            if st.button(f"🚫 Reject #{item.id}", key=f"reject_{item.id}"):
                                with get_db() as db2:
                                    qi = db2.query(ReviewQueueItem).filter(ReviewQueueItem.id == item.id).first()
                                    if qi:
                                        qi.status = "REJECTED"
                                        qi.reviewed_at = datetime.utcnow()
                                st.warning(f"🚫 Item #{item.id} rejected.")
                                st.rerun()

                        with a3:
                            new_act_id = st.text_input(
                                "Remap to Activity ID",
                                placeholder="e.g., PIP-002",
                                key=f"remap_input_{item.id}",
                            )
                            if st.button(f"🔄 Remap #{item.id}", key=f"remap_{item.id}"):
                                if new_act_id:
                                    with get_db() as db2:
                                        qi = db2.query(ReviewQueueItem).filter(ReviewQueueItem.id == item.id).first()
                                        ei = db2.query(EventLog).filter(EventLog.id == item.event_log_fk).first()
                                        if qi and ei:
                                            qi.status = "REMAPPED"
                                            qi.remapped_activity_id = new_act_id.strip()
                                            qi.reviewed_at = datetime.utcnow()
                                            ei.matched_activity_id = new_act_id.strip()
                                            # Apply to schedule
                                            act = db2.query(ScheduleActivity).filter(
                                                ScheduleActivity.activity_id == new_act_id.strip()
                                            ).first()
                                            if act and extracted.get("actual_progress_pct"):
                                                act.progress_pct = max(
                                                    act.progress_pct or 0,
                                                    float(extracted["actual_progress_pct"])
                                                )
                                    st.success(f"🔄 Item #{item.id} remapped to {new_act_id}")
                                    st.rerun()
                                else:
                                    st.error("Enter an Activity ID to remap to.")

                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("")

except Exception as e:
    st.error(f"Database error: {e}")
    st.info("Make sure you've run: `uv run python -m sitesync.db.seed`")
