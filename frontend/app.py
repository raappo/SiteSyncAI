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

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏗️ SiteSync AI")
    st.markdown("**SIH 2024 · Problem ID 26122**")
    st.markdown("*Oil India Limited*")
    st.divider()

    st.markdown("**Navigate to:**")
    pages = {
        "🤖 Time Agent": "pages/1_time_agent.py",
        "📋 Review Queue": "pages/2_review_queue.py",
        "📊 Schedule View": "pages/3_schedule_view.py",
        "🧠 Memory Query": "pages/4_memory_query.py",
    }
    for label in pages:
        st.page_link(pages[label], label=label)

    st.divider()
    st.caption("Built with LangChain · sentence-transformers · ChromaDB · Azure DI")


from frontend.styles import apply_custom_css
apply_custom_css()

# ── Dashboard Home ─────────────────────────────────────────────────────────────
st.title("🏗️ SiteSync AI — Dashboard")
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

    mem = memory_stats()
    memory_count = mem.get("total_events", 0)

    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{total_activities}</div><div class="kpi-label">Schedule Activities</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{total_events}</div><div class="kpi-label">Events Processed</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value">{auto_applied}</div><div class="kpi-label">Auto-Applied</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value" style="color:#FBBF24;">{pending_review}</div><div class="kpi-label">Pending Review</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="kpi-container"><div class="kpi-value" style="color:#A78BFA;">{memory_count}</div><div class="kpi-label">Memory Records</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Database not seeded yet. Run: `uv run python -m sitesync.db.seed` | Error: {e}")
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, label in zip(
        [col1, col2, col3, col4, col5],
        ["Schedule Activities", "Events Processed", "Auto-Applied", "Pending Review", "Memory Records"]
    ):
        with col:
            st.markdown(f'<div class="kpi-container"><div class="kpi-value">—</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

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
