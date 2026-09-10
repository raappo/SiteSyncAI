"""
SiteSync AI — Review Queue UI
"""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from frontend.styles import apply_custom_css
from sitesync.db.session import get_db
from sitesync.db.models import ReviewQueueItem, ScheduleActivity

st.set_page_config(page_title="Review Queue", page_icon="📋", layout="wide")
apply_custom_css()

st.title("📋 Review Queue")
st.markdown("Manually review low-confidence updates, mismatches, or contradictions.")

def approve_item(item_id, activity_id, progress):
    with get_db() as db:
        item = db.query(ReviewQueueItem).get(item_id)
        if item:
            item.status = "APPROVED"
            item.reviewed_by = "admin_user"
            
            # Apply update to schedule
            activity = db.query(ScheduleActivity).filter_by(activity_id=activity_id).first()
            if activity:
                activity.progress_pct = progress
            db.commit()

def reject_item(item_id):
    with get_db() as db:
        item = db.query(ReviewQueueItem).get(item_id)
        if item:
            item.status = "REJECTED"
            item.reviewed_by = "admin_user"
            db.commit()

with get_db() as db:
    pending_items = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "PENDING").all()
    db.expunge_all()

if not pending_items:
    st.info("🎉 All caught up! The review queue is empty.")
else:
    for item in pending_items:
        with st.container():
            st.markdown(f"### Review ID: {item.id}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Reported Update**")
                st.code(f"Progress: {item.reported_progress}%\nNotes: {item.planner_notes}")
            with col2:
                st.markdown("**Matched Activity**")
                if item.suggested_activity_id:
                    st.code(f"Activity ID: {item.suggested_activity_id}\nConfidence: {item.confidence_score}")
                else:
                    st.error("No schedule activity matched.")
            
            col_a, col_b, col_c = st.columns([1, 1, 8])
            with col_a:
                if st.button("Approve", key=f"app_{item.id}", type="primary"):
                    approve_item(item.id, item.suggested_activity_id, item.reported_progress)
                    st.rerun()
            with col_b:
                if st.button("Reject", key=f"rej_{item.id}"):
                    reject_item(item.id)
                    st.rerun()
            st.divider()
