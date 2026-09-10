"""
SiteSync AI — Schedule View UI
"""
import sys
import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from frontend.styles import apply_custom_css
from sitesync.db.session import get_db
from sitesync.db.models import ScheduleActivity

st.set_page_config(page_title="Schedule View", page_icon="📅", layout="wide")
apply_custom_css()

st.title("📅 Project Schedule")

with get_db() as db:
    activities = db.query(ScheduleActivity).all()
    db.expunge_all()

if not activities:
    st.warning("No activities found in the database. Please run the seed script.")
    st.stop()

# Convert to DataFrame
data = []
for a in activities:
    data.append({
        "ID": a.activity_id,
        "Discipline": a.discipline,
        "Description": a.description,
        "Location": a.location,
        "Start": a.planned_start,
        "End": a.planned_end,
        "Progress (%)": a.progress_pct or 0.0,
    })
df = pd.DataFrame(data)

# Filtering
col1, col2, col3 = st.columns(3)
with col1:
    disc_filter = st.selectbox("Filter by Discipline", ["All"] + sorted(df["Discipline"].unique().tolist()))
with col2:
    status_filter = st.selectbox("Status", ["All", "Behind Schedule", "Completed", "Not Started"])
with col3:
    search_query = st.text_input("Search Description")

# Apply filters
if disc_filter != "All":
    df = df[df["Discipline"] == disc_filter]

today = datetime.date.today().isoformat()
if status_filter == "Completed":
    df = df[df["Progress (%)"] >= 100]
elif status_filter == "Not Started":
    df = df[df["Progress (%)"] == 0]
elif status_filter == "Behind Schedule":
    # Activity is behind if end date is past and progress < 100
    df = df[(df["End"] < today) & (df["Progress (%)"] < 100)]

if search_query:
    df = df[df["Description"].str.contains(search_query, case=False, na=False)]

tab1, tab2 = st.tabs(["📊 Table View", "📈 Gantt Chart"])

with tab1:
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    from sitesync.analytics.gantt_builder import build_gantt
    fig = build_gantt(discipline_filter=None if disc_filter == "All" else disc_filter)
    st.plotly_chart(fig, use_container_width=True)
