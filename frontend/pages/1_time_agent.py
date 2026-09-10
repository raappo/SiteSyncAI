"""
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
            parsed_doc = parse_file(Path(tmp_path).read_bytes(), uploaded_file.name)
            
        if parsed_doc.error:
            st.error(f"Failed to parse document: {parsed_doc.error}")
        elif not parsed_doc.raw_text.strip():
            st.warning("No text extracted from document.")
        else:
            run_pipeline(parsed_doc.raw_text, evidence_type=parsed_doc.evidence_type, file_path=uploaded_file.name)
            st.success("Document processed successfully!")
