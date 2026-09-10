"""
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
