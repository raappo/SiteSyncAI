"""
SiteSync AI — Page 4: Institutional Memory Query

Semantic search over ChromaDB project memory.
Query examples: "piping delays due to material shortage",
"civil foundation actual duration", "MCC electrical loop check"
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from frontend.styles import apply_custom_css

st.set_page_config(page_title="Memory Query | SiteSync AI", page_icon="🧠", layout="wide")
apply_custom_css()

st.markdown("""
<style>
.similarity-high   { color: #34d399; font-weight: 700; }
.similarity-medium { color: #f59e0b; font-weight: 700; }
.similarity-low    { color: #f87171; font-weight: 700; }
.memory-doc { font-size: 0.95rem; color: #cbd5e1; font-style: italic; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🧠 Institutional Memory Query")
st.markdown(
    "*Semantic search over all finalized project execution events. "
    "Learn from past delays, durations, and productivity patterns.*"
)
st.divider()

try:
    from sitesync.memory.chroma_store import memory_stats, query_memory

    # ── Stats banner ──────────────────────────────────────────────────────────
    stats = memory_stats()
    c1, c2 = st.columns([1, 4])
    with c1:
        total = stats.get("total_events", 0)
        st.markdown(
            f'<div class="kpi-container">'
            f'<div class="kpi-value">{total}</div>'
            f'<div class="kpi-label">MEMORY RECORDS</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("""
        **What is Institutional Memory?**

        Every time an event is auto-applied or planner-approved, it's stored in a ChromaDB vector database
        as a rich narrative document. Future projects can query: *"How long did piping spools take on similar
        hot oil lines?"* or *"What bottlenecks occurred during civil foundations?"* — turning individual
        project experience into organizational knowledge.
        """)

    st.divider()

    # ── Query interface ───────────────────────────────────────────────────────
    col_q, col_disc, col_n = st.columns([4, 2, 1])
    with col_q:
        query = st.text_input(
            "Search memory",
            placeholder="e.g., piping delays due to material shortage on hot oil lines",
            label_visibility="collapsed",
        )
    with col_disc:
        disciplines = ["All", "Civil", "Piping", "Electrical", "Instrumentation", "HSE"]
        disc_filter = st.selectbox("Discipline", disciplines, label_visibility="collapsed")
    with col_n:
        n_results = st.number_input("Results", min_value=1, max_value=20, value=5, label_visibility="collapsed")

    search_btn = st.button("🔍 Search Memory", type="primary", use_container_width=False)

    # ── Example queries ────────────────────────────────────────────────────────
    st.markdown("**Try these example queries:**")
    example_cols = st.columns(4)
    examples = [
        "piping weld joint erection progress",
        "civil concrete pour foundation",
        "electrical MCC cable termination",
        "material shortage delay constraints",
    ]
    example_clicked = None
    for i, ex in enumerate(examples):
        with example_cols[i]:
            if st.button(f"💡 {ex}", key=f"ex_{i}"):
                example_clicked = ex

    if example_clicked:
        query = example_clicked
        search_btn = True

    st.divider()

    # ── Results ────────────────────────────────────────────────────────────────
    if search_btn and query:
        with st.spinner(f"Searching memory for: *{query}*..."):
            results = query_memory(
                query_text=query,
                discipline_filter=None if disc_filter == "All" else disc_filter,
                n_results=n_results,
            )

        if not results:
            st.info("No matching records found. Submit some field updates via the Time Agent first.")
        else:
            st.markdown(f"### 🔍 Found {len(results)} result(s)")

            for i, r in enumerate(results, 1):
                sim = r["similarity"]
                meta = r["metadata"]
                doc = r["document"]

                if sim >= 0.75:
                    sim_class = "similarity-high"
                    sim_label = "High"
                elif sim >= 0.50:
                    sim_class = "similarity-medium"
                    sim_label = "Medium"
                else:
                    sim_class = "similarity-low"
                    sim_label = "Low"

                st.markdown(f'<div class="card-container">', unsafe_allow_html=True)

                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    st.markdown(f"**#{i}** · `{meta.get('activity_id', '?')}` · **{meta.get('discipline', '?')}**")
                    st.markdown(f'<div class="memory-doc">{doc}</div>', unsafe_allow_html=True)
                with rc2:
                    st.markdown(
                        f'<div style="text-align:right;">'
                        f'<span class="{sim_class}">{sim:.1%}</span><br>'
                        f'<span style="font-size:0.7rem; color:#64748b;">{sim_label} match</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Metadata details
                with st.expander("📊 Details"):
                    m_cols = st.columns(4)
                    m_cols[0].metric("Progress %", f"{meta.get('actual_progress_pct', 0):.1f}%")
                    m_cols[1].metric("Evidence", meta.get("evidence_type", "?"))
                    m_cols[2].metric("Confidence", f"{meta.get('confidence_score', 0):.1%}")
                    if meta.get("actual_duration_days"):
                        m_cols[3].metric("Duration", f"{meta['actual_duration_days']} days")
                    st.caption(f"Report date: {meta.get('report_date','?')} | Indexed: {meta.get('indexed_at','?')[:10]}")
                    constraints = json.loads(meta.get("constraints", "[]"))
                    if constraints:
                        st.warning(f"⚠️ Constraints recorded: {', '.join(constraints)}")

                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("")

            # ── Export results ────────────────────────────────────────────────
            export_rows = [
                {
                    "Rank": i + 1,
                    "Similarity": r["similarity"],
                    "Activity ID": r["metadata"].get("activity_id"),
                    "Discipline": r["metadata"].get("discipline"),
                    "Progress %": r["metadata"].get("actual_progress_pct"),
                    "Date": r["metadata"].get("report_date"),
                    "Evidence": r["metadata"].get("evidence_type"),
                    "Document": r["document"],
                }
                for i, r in enumerate(results)
            ]
            df_export = pd.DataFrame(export_rows)
            csv_bytes = df_export.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Export Results CSV",
                data=csv_bytes,
                file_name="memory_query_results.csv",
                mime="text/csv",
            )

except Exception as e:
    st.error(f"Memory query error: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.info("Ensure ChromaDB is initialized: submit events via Time Agent, then retry.")
