"""
SiteSync AI — Page 1: Time Agent

Dual-mode input:
  - Chat interface: Conversational LangChain Time Agent
  - File upload: PDF, XLSX, TXT → extraction pipeline
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Time Agent | SiteSync AI", page_icon="🤖", layout="wide")

# ── Apply global styles ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
.main .block-container { padding-top: 1.5rem; max-width: 1400px; }
.chat-user  { background: #1e3a5f; border-radius: 12px 12px 2px 12px; padding: 0.8rem 1rem; margin: 0.4rem 0; max-width: 85%; margin-left: auto; color: #e0f2fe; }
.chat-agent { background: #1e293b; border-radius: 12px 12px 12px 2px; padding: 0.8rem 1rem; margin: 0.4rem 0; max-width: 85%; border-left: 3px solid #38bdf8; color: #e2e8f0; }
.result-card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 1rem; margin: 0.5rem 0; }
.badge-high   { background:#166534; color:#bbf7d0; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-medium { background:#854d0e; color:#fef08a; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-low    { background:#7f1d1d; color:#fecaca; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
#MainMenu{visibility:hidden} footer{visibility:hidden}
</style>
""", unsafe_allow_html=True)


def get_confidence_badge(conf: float) -> str:
    if conf >= 0.85:
        return f'<span class="badge-high">✅ {conf:.0%} AUTO-APPLY</span>'
    elif conf >= 0.60:
        return f'<span class="badge-medium">⚠️ {conf:.0%} REVIEW</span>'
    else:
        return f'<span class="badge-low">❌ {conf:.0%} LOW</span>'


def run_pipeline(raw_text: str, evidence_type: str, source_file: str = ""):
    """Run the full extraction → linking → routing pipeline."""
    results = []
    status_placeholder = st.empty()

    with status_placeholder.container():
        with st.spinner("🧠 Extracting with LLM..."):
            from sitesync.extraction.extractor import extract
            extraction = extract(raw_text, evidence_type=evidence_type)

        if extraction.error:
            st.error(f"Extraction failed: {extraction.error}")
            return

        st.success(f"✅ Extracted **{len(extraction.updates)}** activity update(s) via `{extraction.model_used}` in {extraction.extraction_ms:.0f}ms")

        for i, update in enumerate(extraction.updates, 1):
            with st.spinner(f"🔗 Linking activity {i}/{len(extraction.updates)}..."):
                from sitesync.linking.matcher import match
                link_result = match(update, top_k=3)

            with st.spinner("🚦 Routing..."):
                from sitesync.routing.router import route
                event = route(link_result, source_file=source_file or None)

            # If auto-applied, upsert to memory
            if event.auto_applied and link_result.best_match:
                try:
                    from sitesync.memory.chroma_store import upsert_event
                    upsert_event(
                        event_id=event.id,
                        activity_id=link_result.best_match.activity_id,
                        discipline=update.discipline,
                        activity_description=update.activity_description,
                        actual_progress_pct=update.actual_progress_pct,
                        report_date=update.date,
                        evidence_type=update.evidence_type,
                        planned_start=link_result.best_match.planned_start,
                        planned_end=link_result.best_match.planned_end,
                        constraints=update.constraints,
                        confidence_score=event.confidence_score,
                    )
                except Exception:
                    pass

            results.append((update, link_result, event))

    status_placeholder.empty()

    # ── Display results ────────────────────────────────────────────────────────
    st.markdown("### 📊 Pipeline Results")
    for update, link_result, event in results:
        best = link_result.best_match
        with st.container():
            cols = st.columns([3, 2])
            with cols[0]:
                st.markdown(f'<div class="result-card">', unsafe_allow_html=True)
                st.markdown(f"**🏷️ Extracted Activity**")
                st.markdown(f"- **Discipline:** `{update.discipline}`")
                st.markdown(f"- **Location:** {update.location}")
                st.markdown(f"- **Description:** {update.activity_description}")
                st.markdown(f"- **Progress:** `{update.actual_progress_pct:.1f}%`")
                st.markdown(f"- **Date:** `{update.date}`")
                st.markdown(f"- **Evidence:** `{update.evidence_type}`")
                if update.constraints:
                    st.markdown(f"- **⚠️ Constraints:** {', '.join(update.constraints)}")
                st.markdown('</div>', unsafe_allow_html=True)

            with cols[1]:
                st.markdown(f'<div class="result-card">', unsafe_allow_html=True)
                if best:
                    badge = get_confidence_badge(best.confidence)
                    st.markdown(f"**🎯 Best Match** {badge}", unsafe_allow_html=True)
                    st.markdown(f"- **Activity ID:** `{best.activity_id}`")
                    st.markdown(f"- **Schedule Desc:** {best.description[:60]}...")
                    st.markdown(f"- **Semantic:** `{best.semantic_score:.3f}`")
                    st.markdown(f"- **Evidence wt:** `{best.evidence_weight:.2f}`")
                    st.markdown(f"- **Temporal:** `{best.temporal_score:.2f}`")
                    st.markdown(f"- **Confidence:** `{best.confidence:.3f}`")
                    if event.auto_applied:
                        st.success("✅ Auto-applied to schedule")
                    else:
                        st.warning("📋 Sent to Review Queue")
                else:
                    st.error("❌ No match found — sent to Review Queue")
                st.markdown('</div>', unsafe_allow_html=True)

        if link_result.top_matches and len(link_result.top_matches) > 1:
            with st.expander("🔍 All candidate matches"):
                for m in link_result.top_matches:
                    st.markdown(f"**#{m.rank}** `{m.activity_id}` — {m.description[:70]} — conf=`{m.confidence:.3f}`")


# ── Page Layout ────────────────────────────────────────────────────────────────
st.markdown("# 🤖 Time Agent")
st.markdown("*Submit field progress — via chat or file upload — and SiteSync AI will extract, link, and update the schedule.*")
st.divider()

tab_chat, tab_upload = st.tabs(["💬 Chat Interface", "📁 File Upload"])

# ── TAB 1: Chat ────────────────────────────────────────────────────────────────
with tab_chat:
    st.markdown("**Talk to the Time Agent.** Describe what your crew completed today. The agent will guide you if anything is missing.")

    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chain" not in st.session_state:
        st.session_state.chain = None
    if "ready_to_extract" not in st.session_state:
        st.session_state.ready_to_extract = None

    # Render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">👷 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-agent">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

    # Chat input
    col_input, col_send = st.columns([5, 1])
    with col_input:
        user_msg = st.text_input(
            "Your message",
            placeholder="e.g., Spool erected on 6 inch line near hot oil tank, 3 joints done today...",
            label_visibility="collapsed",
            key="chat_input",
        )
    with col_send:
        send = st.button("Send →", use_container_width=True, type="primary")

    col_reset, col_process = st.columns(2)
    with col_reset:
        if st.button("🗑️ Reset Chat"):
            st.session_state.chat_history = []
            st.session_state.chain = None
            st.session_state.ready_to_extract = None
            st.rerun()
    with col_process:
        process_chat = st.button(
            "⚡ Process & Link",
            disabled=st.session_state.ready_to_extract is None,
            type="primary",
        )

    if send and user_msg:
        # Build chain lazily
        if st.session_state.chain is None:
            try:
                from sitesync.ingestion.text_agent import build_time_agent_chain
                st.session_state.chain = build_time_agent_chain()
            except Exception as e:
                st.error(f"Could not initialize Time Agent: {e}")
                st.stop()

        st.session_state.chat_history.append({"role": "user", "content": user_msg})

        with st.spinner("Agent thinking..."):
            try:
                response = st.session_state.chain.predict(input=user_msg)
            except Exception as e:
                response = f"⚠️ LLM error: {e}. Check your API key in .env"

        st.session_state.chat_history.append({"role": "agent", "content": response})

        # Check for ready signal
        from sitesync.ingestion.text_agent import parse_ready_signal
        summary = parse_ready_signal(response)
        if summary:
            st.session_state.ready_to_extract = summary
            st.success(f"✅ Ready to process: `{summary}`")

        st.rerun()

    if process_chat and st.session_state.ready_to_extract:
        run_pipeline(
            st.session_state.ready_to_extract,
            evidence_type="text",
            source_file="chat_time_agent",
        )

# ── TAB 2: File Upload ────────────────────────────────────────────────────────
with tab_upload:
    st.markdown("**Upload a field report** (site diary, piping spreadsheet, PDF scan). SiteSync AI will parse and process it automatically.")

    uploaded = st.file_uploader(
        "Upload file",
        type=["txt", "pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"],
        label_visibility="collapsed",
    )

    ev_type_override = st.selectbox(
        "Evidence type (auto-detected, override if needed)",
        ["auto-detect", "text", "spreadsheet", "scanned_doc", "photo"],
        index=0,
    )

    if uploaded:
        st.info(f"📄 File: `{uploaded.name}` ({uploaded.size / 1024:.1f} KB)")

        if st.button("⚡ Parse & Extract", type="primary", key="upload_process"):
            with st.spinner("Parsing document..."):
                from sitesync.ingestion.doc_parser import parse_file
                file_bytes = uploaded.read()
                parsed = parse_file(file_bytes, uploaded.name)

            if parsed.error:
                st.error(f"Parse error: {parsed.error}")
            else:
                st.success(f"✅ Parsed with `{parsed.parser_used}` — {len(parsed.raw_text)} chars extracted")

                ev = ev_type_override if ev_type_override != "auto-detect" else parsed.evidence_type

                with st.expander("📄 Raw extracted text (preview)"):
                    st.text(parsed.raw_text[:2000] + ("..." if len(parsed.raw_text) > 2000 else ""))

                if parsed.tables:
                    with st.expander(f"📊 Extracted tables ({len(parsed.tables)} table(s))"):
                        for i, tbl in enumerate(parsed.tables[:3]):
                            st.markdown(f"**Table {i+1}**")
                            if tbl and len(tbl) > 0:
                                import pandas as pd
                                df = pd.DataFrame(tbl[1:], columns=tbl[0] if tbl[0] else None)
                                st.dataframe(df, use_container_width=True)

                run_pipeline(parsed.raw_text, evidence_type=ev, source_file=uploaded.name)

    st.divider()
    st.markdown("**Or try a sample:**")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("📝 Load Site Diary Sample"):
            diary_path = Path(__file__).parent.parent.parent / "data" / "site_diary_text.txt"
            if diary_path.exists():
                sample_text = diary_path.read_text()
                run_pipeline(sample_text, evidence_type="text", source_file="site_diary_text.txt")
            else:
                st.error("Sample not found. Run the seed script first.")
    with col_s2:
        if st.button("📊 Load Piping Spreadsheet Sample"):
            xlsx_path = Path(__file__).parent.parent.parent / "data" / "piping_progress.xlsx"
            if xlsx_path.exists():
                from sitesync.ingestion.doc_parser import parse_file
                parsed = parse_file(xlsx_path.read_bytes(), "piping_progress.xlsx")
                run_pipeline(parsed.raw_text, evidence_type="spreadsheet", source_file="piping_progress.xlsx")
            else:
                st.error("Sample not found. Run: uv run python scripts/generate_xlsx.py")
