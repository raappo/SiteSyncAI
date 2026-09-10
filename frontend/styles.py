import streamlit as st

def apply_custom_css():
    st.markdown("""
    <style>
    /* Clean Header Cleanup */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .main .block-container { padding-top: 1rem; max-width: 1400px; }

    /* Card Containers */
    .card-container {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #F1F5F9;
        margin-bottom: 0.8rem;
    }

    /* Status Badges & Pills */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-auto {
        background-color: #052E16;
        border: 1px solid #166534;
        color: #4ADE80;
    }
    .badge-pending {
        background-color: #451A03;
        border: 1px solid #92400E;
        color: #FBBF24;
    }
    .badge-mismatch {
        background-color: #450A0A;
        border: 1px solid #991B1B;
        color: #F87171;
    }
    .badge-neutral {
        background-color: #1E293B;
        border: 1px solid #475569;
        color: #CBD5E1;
    }

    /* Chat Bubbles */
    .chat-user {
        background-color: #334155;
        border-radius: 12px 12px 0px 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        max-width: 85%;
        margin-left: auto;
        color: #F1F5F9;
        font-size: 0.95rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .chat-agent {
        background-color: #0F172A;
        border-radius: 12px 12px 12px 0px;
        border-left: 3px solid #38BDF8;
        padding: 1rem;
        margin: 0.5rem 0;
        max-width: 85%;
        color: #E2E8F0;
        font-size: 0.95rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    /* Data Tables */
    [data-testid="stDataFrame"] {
        background-color: #0B0F17;
    }
    [data-testid="stDataFrame"] th {
        background-color: #1E293B !important;
        color: #F1F5F9 !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #334155 !important;
    }
    [data-testid="stDataFrame"] td {
        background-color: #0B0F17 !important;
        color: #CBD5E1 !important;
        border-bottom: 1px solid #1E293B !important;
    }

    /* KPIs */
    .kpi-container {
        display: flex;
        flex-direction: column;
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .kpi-value {
        font-family: monospace;
        font-size: 2.2rem;
        font-weight: 700;
        color: #38BDF8;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)
