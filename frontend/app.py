"""
SiteSync AI — Streamlit Main App Entry Point

4-page application:
  1. 🤖 Time Agent       — Chat + File Upload ingestion
  2. 📋 Review Queue     — Planner approval/rejection UI
  3. 📊 Schedule View    — Live baseline vs actual progress
  4. 🧠 Memory Query     — Semantic institutional memory search
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="SiteSync AI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/sitesyncai",
        "About": "SiteSync AI — SIH 2024 | Problem ID 26122 | Oil India Limited",
    },
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* Main background */
.main .block-container {
    padding-top: 1.5rem;
    max-width: 1400px;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
}
.metric-value { font-size: 2rem; font-weight: 700; color: #38bdf8; }
.metric-label { font-size: 0.8rem; color: #94a3b8; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }

/* Confidence badges */
.badge-high   { background: #166534; color: #bbf7d0; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-medium { background: #854d0e; color: #fef08a; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-low    { background: #7f1d1d; color: #fecaca; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }

/* Chat messages */
.chat-user    { background: #1e3a5f; border-radius: 12px 12px 2px 12px; padding: 0.8rem 1rem; margin: 0.4rem 0; max-width: 80%; margin-left: auto; color: #e0f2fe; }
.chat-agent   { background: #1e293b; border-radius: 12px 12px 12px 2px; padding: 0.8rem 1rem; margin: 0.4rem 0; max-width: 80%; border-left: 3px solid #38bdf8; color: #e2e8f0; }

/* Progress bars in schedule view */
.prog-bar-outer { background: #1e293b; border-radius: 6px; height: 10px; width: 100%; }
.prog-bar-inner { background: linear-gradient(90deg, #38bdf8, #818cf8); border-radius: 6px; height: 10px; transition: width 0.4s; }

/* Streamlit button overrides */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}

/* Remove default streamlit branding padding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 1.5rem 0;">
        <div style="font-size: 2.5rem;">🏗️</div>
        <div style="font-size: 1.3rem; font-weight: 700; color: #38bdf8;">SiteSync AI</div>
        <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">SIH 2024 · Problem ID 26122</div>
        <div style="font-size: 0.7rem; color: #475569; margin-top: 2px;">Oil India Limited</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Navigate to:**")

    pages = {
        "🤖 Time Agent": "pages/1_time_agent.py",
        "📋 Review Queue": "pages/2_review_queue.py",
        "📊 Schedule View": "pages/3_schedule_view.py",
        "🧠 Memory Query": "pages/4_memory_query.py",
    }
    for label in pages:
        st.page_link(pages[label], label=label)

    st.markdown("---")
    st.markdown("<div style='font-size:0.7rem; color: #475569;'>Built with LangChain · sentence-transformers · ChromaDB · Azure DI</div>", unsafe_allow_html=True)


# ── Dashboard Home ─────────────────────────────────────────────────────────────
st.markdown("## 🏗️ SiteSync AI — Dashboard")
st.markdown("*Intelligent Data Capture & Schedule-Linking for Infrastructure Projects*")
st.divider()

# Live stats
try:
    from sitesync.db.models import EventLog, ReviewQueueItem, ScheduleActivity
    from sitesync.db.session import get_db
    from sitesync.memory.chroma_store import memory_stats

    with get_db() as db:
        total_activities = db.query(ScheduleActivity).count()
        total_events = db.query(EventLog).count()
        auto_applied = db.query(EventLog).filter(EventLog.auto_applied == True).count()
        pending_review = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "PENDING").count()
        avg_progress = db.query(ScheduleActivity).all()
        avg_pct = sum(a.progress_pct or 0 for a in avg_progress) / max(len(avg_progress), 1)

    mem = memory_stats()
    memory_count = mem.get("total_events", 0)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_activities}</div><div class="metric-label">Schedule Activities</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_events}</div><div class="metric-label">Events Processed</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{auto_applied}</div><div class="metric-label">Auto-Applied</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#f59e0b">{pending_review}</div><div class="metric-label">Pending Review</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#a78bfa">{memory_count}</div><div class="metric-label">Memory Records</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Database not seeded yet. Run: `uv run python -m sitesync.db.seed` | Error: {e}")
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, label, val in zip(
        [col1, col2, col3, col4, col5],
        ["Schedule Activities", "Events Processed", "Auto-Applied", "Pending Review", "Memory Records"],
        ["—", "—", "—", "—", "—"]
    ):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{val}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown("")
st.divider()

# ── Feature overview ───────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    ### 🏗️ How SiteSync AI Works

    **1. Ingest** → Site supervisors submit updates via:
    - 💬 Chat (Time Agent)
    - 📁 File upload (PDF, XLSX, TXT)

    **2. Extract** → LLM (NVIDIA NIM / ExpLabs) converts messy field text into a structured JSON payload

    **3. Link** → Semantic cosine similarity matches field descriptions to L5/L6 schedule nodes using sentence-transformers

    **4. Route** → Confidence ≥ 85%: auto-update. < 85%: Planner Review Queue

    **5. Remember** → All finalized events stored in ChromaDB for institutional memory
    """)

with c2:
    st.markdown("""
    ### 📐 Multi-Signal Confidence Formula

    ```
    Confidence = (0.60 × Semantic Score)
               + (0.25 × Evidence Weight)
               + (0.15 × Temporal Score)
    ```

    | Evidence Type | Weight |
    |---|---|
    | 📸 Photo | 1.00 |
    | 📊 Spreadsheet | 0.85 |
    | 📄 Scanned Document | 0.75 |
    | 💬 Text / Chat | 0.60 |

    **Auto-apply threshold:** 85%
    **Review queue:** Everything below threshold — nothing dropped!
    """)

st.divider()
st.markdown(
    "<div style='text-align:center; color:#475569; font-size:0.75rem;'>"
    "SiteSync AI · Smart India Hackathon 2024 · Problem ID 26122 · Oil India Limited"
    "</div>",
    unsafe_allow_html=True,
)
