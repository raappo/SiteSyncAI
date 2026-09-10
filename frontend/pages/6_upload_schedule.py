"""
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
