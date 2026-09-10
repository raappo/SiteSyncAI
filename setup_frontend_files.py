import os
from pathlib import Path

files = {}

files["frontend/styles.py"] = '''"""
SiteSync AI — Central Stylesheet (Oil & Gas Dark Theme)
"""
import streamlit as st

def apply_custom_css():
    css = """
    <style>
    /* === COLOR PALETTE (Oil & Gas Industrial Dark) === */
    :root {
        --bg-primary: #0D1117;
        --bg-secondary: #161B22;
        --bg-tertiary: #21262D;
        --border-color: #30363D;
        --text-primary: #E6EDF3;
        --text-secondary: #8B949E;
        --accent: #F0A500;
        --accent-hover: #D69300;
        --success: #2EA043;
        --warning: #D29922;
        --danger: #DA3633;
        --info: #388BFD;
    }

    /* === GLOBAL STYLES === */
    .stApp {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 { color: var(--text-primary) !important; font-weight: 600 !important; }
    h1 { font-size: 2.2rem !important; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; margin-bottom: 1.5rem; }

    /* === SIDEBAR === */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-color);
    }
    [data-testid="stSidebar"] .stMarkdown p { color: var(--text-secondary); }

    /* === CARDS === */
    .metric-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        border-color: var(--accent);
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
    .metric-label { font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem; }

    /* === CHAT MESSAGES === */
    .chat-user {
        background: var(--bg-tertiary);
        border-radius: 12px 12px 0px 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        max-width: 85%;
        margin-left: auto;
        color: var(--text-primary);
        font-size: 0.95rem;
    }
    .chat-agent {
        background: var(--bg-secondary);
        border-radius: 12px 12px 12px 0px;
        border-left: 3px solid var(--info);
        padding: 1rem;
        margin: 0.5rem 0;
        max-width: 85%;
        color: var(--text-primary);
        font-size: 0.95rem;
    }

    /* === EARLY WARNING STRIP === */
    .early-warning-strip {
        background: linear-gradient(135deg, #2D1216, #1A0A0C);
        border: 1px solid var(--danger);
        border-left: 4px solid var(--danger);
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        animation: pulse-border 2s ease-in-out infinite;
    }
    @keyframes pulse-border {
        0%, 100% { border-left-color: var(--danger); }
        50% { border-left-color: #FF6B6B; }
    }

    /* === STATUS INDICATORS === */
    .status-badge {
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .status-ok { background: rgba(46, 160, 67, 0.2); color: var(--success); }
    .status-warn { background: rgba(210, 153, 34, 0.2); color: var(--warning); }
    .status-err { background: rgba(218, 54, 51, 0.2); color: var(--danger); }
    
    /* === STREAMLIT OVERRIDES === */
    .stButton > button {
        background: transparent;
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        border-radius: 6px;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    .stButton > button:hover {
        background: var(--bg-tertiary);
        border-color: var(--accent);
        color: var(--accent);
    }
    .stButton > button[kind="primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #000 !important;
        font-weight: 600;
    }
    .stTextInput input, .stSelectbox select, .stTextArea textarea {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        border-radius: 6px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(240, 165, 0, 0.125) !important;
    }
    .stDataFrame { background: var(--bg-secondary); border-radius: 8px; }
    [data-testid="stDataFrame"] th {
        background-color: var(--bg-tertiary) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        border-bottom: 1px solid var(--border-color) !important;
    }
    [data-testid="stDataFrame"] td {
        background-color: var(--bg-secondary) !important;
        color: var(--text-secondary) !important;
        border-bottom: 1px solid var(--border-color) !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
'''

files["frontend/app.py"] = '''"""
SiteSync AI — Main Application Entry Point
"""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.styles import apply_custom_css
from sitesync.analytics.kpi_engine import compute_kpis

st.set_page_config(
    page_title="SiteSync AI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3201/3201521.png", width=60)
    st.title("SiteSync AI")
    st.caption("Intelligent Planning-to-Execution Bridge")
    st.divider()

    st.markdown("### System Status")
    
    from sitesync.config import settings
    # Check LLMs
    llm_status = "ok" if settings.active_models else "err"
    llm_icon = "✅" if llm_status == "ok" else "❌"
    st.markdown(f"{llm_icon} **LLM API:** <span class='status-{llm_status}'>{'Connected' if llm_status == 'ok' else 'Offline (Mock Mode)'}</span>", unsafe_allow_html=True)
    
    # Check Voice
    from sitesync.ingestion.voice_agent import is_voice_available
    voice_status = "ok" if is_voice_available() else "warn"
    voice_icon = "✅" if voice_status == "ok" else "⚠️"
    st.markdown(f"{voice_icon} **Voice:** <span class='status-{voice_status}'>{'Available' if voice_status == 'ok' else 'Unavailable'}</span>", unsafe_allow_html=True)

# Main Dashboard
st.title("🏗️ Project Overview")

# Compute real KPIs
kpis = compute_kpis()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(label="Overall Progress", value=f"{kpis.overall_progress}%")
with col2:
    st.metric(label="SPI", value=f"{kpis.spi:.2f}")
with col3:
    st.metric(label="On Track", value=kpis.on_track_count)
with col4:
    st.metric(label="Behind Schedule", value=kpis.behind_count, delta="-critical" if kpis.behind_count > 0 else "")
with col5:
    st.metric(label="Pending Reviews", value=kpis.pending_review_count)

st.divider()

st.markdown("""
### 🚀 Welcome to SiteSync AI

This prototype bridges the gap between macro-level planning schedules and micro-level field execution.

**Getting Started:**
1. Use **Upload Schedule** to ingest a baseline XER or CSV.
2. Use **Time Agent** to log daily field updates via voice or text.
3. Review flagged activities in the **Review Queue**.
4. View real-time delays in **Schedule View** & **Analytics**.
""")
'''

files["frontend/pages/1_time_agent.py"] = '''"""
SiteSync AI — Time Agent UI
"""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from frontend.styles import apply_custom_css
from sitesync.ingestion.text_agent import build_time_agent_chain, parse_ready_signal
from sitesync.ingestion.doc_parser import parse_file
from sitesync.extraction.extractor import get_extractor
from sitesync.linking.matcher import get_matcher
from sitesync.routing.router import route

st.set_page_config(page_title="Time Agent", page_icon="🤖", layout="wide")
apply_custom_css()

st.title("🤖 Time Agent")
st.markdown("Interact with the conversational agent to log field updates, or upload a document.")

# Initialize session state for agent
if "time_agent" not in st.session_state:
    st.session_state.time_agent = build_time_agent_chain()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = []

tab1, tab2 = st.tabs(["💬 Conversational Input (Voice/Text)", "📄 Document Upload"])

def run_pipeline(text: str, evidence_type: str = "text", file_path: str = None):
    with st.spinner("Processing through SiteSync Pipeline..."):
        extractor = get_extractor()
        result = extractor.extract(text, evidence_type=evidence_type)
        
        if result.error:
            st.error(f"Extraction failed: {result.error}")
            return
            
        matcher = get_matcher()
        for update in result.updates:
            linking_res = matcher.match(update)
            event = route(linking_res, source_file=file_path, model_used=result.model_used)
            
            st.session_state.pipeline_results.append({
                "update": update,
                "event": event,
                "linking": linking_res
            })
        st.success(f"Processed {len(result.updates)} activity update(s).")

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Chat")
        # Display chat
        for msg in st.session_state.chat_history:
            role = "user" if msg["role"] == "user" else "agent"
            st.markdown(f"<div class='chat-{role}'>{msg['content']}</div>", unsafe_allow_html=True)
            
        user_input = st.chat_input("Type your update here...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.rerun()

        # Handle latest input
        if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
            latest_input = st.session_state.chat_history[-1]["content"]
            agent_response = st.session_state.time_agent.send(latest_input)
            st.session_state.chat_history.append({"role": "agent", "content": agent_response})
            
            ready_summary = parse_ready_signal(agent_response)
            if ready_summary:
                st.info("Agent has gathered enough information. Running extraction pipeline...")
                run_pipeline(ready_summary, "text")
            
            st.rerun()
            
    with col2:
        st.subheader("Results")
        if not st.session_state.pipeline_results:
            st.info("No updates processed yet.")
        else:
            for res in reversed(st.session_state.pipeline_results):
                with st.expander(f"✅ {res['update'].activity_description[:30]}...", expanded=True):
                    st.write(f"**Discipline:** {res['update'].discipline}")
                    st.write(f"**Progress:** {res['update'].actual_progress_pct}%")
                    if res['event'].auto_applied:
                        st.success("Auto-applied to schedule (High Confidence)")
                    else:
                        st.warning("Sent to Review Queue (Low Confidence / Contradiction)")

with tab2:
    st.subheader("Document / Image Upload")
    uploaded_file = st.file_uploader("Upload Daily Report, Excel, or Whiteboard Photo", type=["txt", "csv", "xlsx", "pdf", "png", "jpg"])
    
    if uploaded_file and st.button("Process Document"):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
            
        with st.spinner("Parsing document..."):
            parsed_doc = parse_file(tmp_path)
            
        if parsed_doc.error:
            st.error(f"Failed to parse document: {parsed_doc.error}")
        elif not parsed_doc.raw_text.strip():
            st.warning("No text extracted from document.")
        else:
            run_pipeline(parsed_doc.raw_text, evidence_type=parsed_doc.evidence_type, file_path=uploaded_file.name)
            st.success("Document processed successfully!")
'''

files["frontend/pages/2_review_queue.py"] = '''"""
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
                st.code(f"Progress: {item.reported_progress}%\\nNotes: {item.planner_notes}")
            with col2:
                st.markdown("**Matched Activity**")
                if item.suggested_activity_id:
                    st.code(f"Activity ID: {item.suggested_activity_id}\\nConfidence: {item.confidence_score}")
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
'''

files["frontend/pages/3_schedule_view.py"] = '''"""
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
'''

files["frontend/pages/5_analytics.py"] = '''"""
SiteSync AI — Analytics Dashboard
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from frontend.styles import apply_custom_css
from sitesync.analytics.kpi_engine import compute_kpis
from sitesync.analytics.forecaster import compute_forecast

st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")
apply_custom_css()

st.title("📈 Project Analytics & Forecasting")

kpis = compute_kpis()
forecast = compute_forecast()

# Top row metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Schedule Performance Index (SPI)", f"{kpis.spi:.2f}", 
              delta=f"{((kpis.spi - 1.0) * 100):.1f}%" if kpis.spi != 1.0 else None)
with col2:
    delay_str = f"{forecast.delay_days} days" if forecast.delay_days > 0 else "On Time"
    st.metric("Projected Delay", delay_str, delta="-critical" if forecast.delay_days > 0 else "normal")
with col3:
    st.metric("Est. Completion", forecast.estimated_completion_date or "N/A")
with col4:
    st.metric("Total Activities", kpis.total_activities)

st.divider()

col_charts1, col_charts2 = st.columns(2)

with col_charts1:
    st.subheader("Discipline Progress")
    if kpis.disciplines:
        df_disc = pd.DataFrame([
            {"Discipline": d.discipline, "Avg Progress": d.avg_progress}
            for d in kpis.disciplines
        ])
        fig1 = px.bar(df_disc, x="Discipline", y="Avg Progress", color="Discipline", 
                      range_y=[0, 100], template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No discipline data available.")

with col_charts2:
    st.subheader("Activity Health")
    df_health = pd.DataFrame({
        "Status": ["On Track", "At Risk", "Behind"],
        "Count": [kpis.on_track_count, kpis.at_risk_count, kpis.behind_count]
    })
    fig2 = px.pie(df_health, values="Count", names="Status", 
                  color="Status", 
                  color_discrete_map={"On Track": "#2EA043", "At Risk": "#D29922", "Behind": "#DA3633"},
                  template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("🚨 Critical Activities Delay (Top 10)")
if forecast.critical_activities:
    df_crit = pd.DataFrame([
        {
            "Activity ID": c.activity_id,
            "Description": c.description,
            "Delay (Days)": c.delay_days,
            "Progress": f"{c.current_progress:.1f}%",
            "Est. Completion": c.estimated_completion
        }
        for c in forecast.critical_activities
    ])
    st.dataframe(df_crit, use_container_width=True)
else:
    st.success("No critical delays detected!")
'''

files["frontend/pages/6_upload_schedule.py"] = '''"""
SiteSync AI — Schedule Upload UI
"""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from frontend.styles import apply_custom_css
from sitesync.ingestion.primavera_parser import parse_xer_to_dataframe
from sitesync.db.seed import seed_from_dataframe

st.set_page_config(page_title="Upload Schedule", page_icon="📤", layout="wide")
apply_custom_css()

st.title("📤 Upload Baseline Schedule")
st.markdown("Import a Primavera P6 `.xer` file or `.csv` baseline to seed the SiteSync database.")

uploaded_file = st.file_uploader("Upload XER or CSV file", type=["xer", "csv"])

if uploaded_file and st.button("Process & Seed Database", type="primary"):
    with st.spinner("Parsing schedule file..."):
        df = parse_xer_to_dataframe(uploaded_file)
        if df is not None and not df.empty:
            st.success(f"Successfully parsed {len(df)} activities.")
            
            with st.spinner("Seeding database (extracting embeddings)..."):
                try:
                    seed_from_dataframe(df, overwrite=True)
                    st.success("Database seeded successfully! You can now view the schedule.")
                except Exception as e:
                    st.error(f"Error seeding database: {e}")
        else:
            st.error("Could not parse file. Ensure it is a valid format.")
'''

# Now write them
base_dir = Path(r"C:\Users\prish\.gemini\antigravity\scratch\SiteSyncAI")
for filepath, content in files.items():
    p = base_dir / filepath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"Created/Modified: {p}")
