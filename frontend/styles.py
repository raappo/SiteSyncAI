"""
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
