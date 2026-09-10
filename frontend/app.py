"""
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
