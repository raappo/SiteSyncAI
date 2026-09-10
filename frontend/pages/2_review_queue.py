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

st.set_page_config(page_title="Review Queue | SiteSync AI", page_icon="📋", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
.main .block-container { padding-top: 1.5rem; max-width: 1400px; }
.queue-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.2rem; margin: 0.6rem 0; }
.badge-pending  { background:#7f1d1d; color:#fecaca; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-approved { background:#166534; color:#bbf7d0; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-rejected { background:#374151; color:#9ca3af; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-remapped { background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
#MainMenu{visibility:hidden} footer{visibility:hidden}
</style>
""", unsafe_allow_html=True)


def status_badge(status: str) -> str:
    badges = {
        "PENDING": '<span class="badge-pending">⏳ PENDING</span>',
        "APPROVED": '<span class="badge-approved">✅ APPROVED</span>',
        "REJECTED": '<span class="badge-rejected">🚫 REJECTED</span>',
        "REMAPPED": '<span class="badge-remapped">🔄 REMAPPED</span>',
    }
    return badges.get(status, status)


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
                st.markdown(f'<div class="queue-card">', unsafe_allow_html=True)

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
                            st.markdown("**Match Scores**")
                            st.markdown(f"- Semantic: `{ev.semantic_score or 0:.3f}`")
                            st.markdown(f"- Evidence weight: `{ev.evidence_weight or 0:.2f}`")
                            st.markdown(f"- Temporal: `{ev.temporal_score or 0:.2f}`")
                            st.markdown(f"- **Confidence: `{ev.confidence_score or 0:.3f}`**")
                            if item.planner_notes:
                                st.warning(item.planner_notes)

                        a1, a2, a3 = st.columns(3)
                        with a1:
                            if st.button(f"✅ Approve #{item.id}", key=f"approve_{item.id}", type="primary"):
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
