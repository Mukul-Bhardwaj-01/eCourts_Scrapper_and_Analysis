"""
app.py
───────
Main Streamlit entry point.

Run with:
    streamlit run app.py

Routing is done entirely through st.session_state["page"].

Page flow:
    home → case_input → scraping → results → dashboard
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="eCourts Legal Analytics",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STYLES
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

.block-container{
    padding-top:1.5rem;
}

[data-testid="stMetricLabel"]{
    font-size:0.9rem;
}

[data-testid="stSidebarNav"]{
    display:none;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    # navigation
    "page": "home",

    # user
    "user_name": "",
    "user_email": "",
    "login_time": None,

    # cnrs
    "cnr_list": [],
    "invalid_cnrs": [],

    # scraping output
    "cases": [],
    "excel_path": None,

    # workflow
    "scraping_done": False,
    "show_email_form": False,

    # ai
    "ai_caseload_para": None,

    # analytics
    "successful_cases": 0,
    "failed_cases": 0,
    "ai_failures": 0,
    "errors": [],

    # future config
    "groq_api_key": None,
}

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────

page = st.session_state["page"]

try:

    # HOME
    if page == "home":
        from home import render
        render()

    # CNR ENTRY
    elif page == "case_input":

        if not st.session_state.get("user_name"):
            st.session_state["page"] = "home"
            st.rerun()

        from case_input import render
        render()

    # SCRAPING
    elif page == "scraping":

        if not st.session_state.get("cnr_list"):
            st.session_state["page"] = "case_input"
            st.rerun()

        from scraping import render
        render()

    # RESULTS
    elif page == "results":

        if not st.session_state.get("cases"):
            st.session_state["page"] = "scraping"
            st.rerun()

        from results import render
        render()

    # DASHBOARD
    elif page == "dashboard":

        if not st.session_state.get("cases"):
            st.session_state["page"] = "results"
            st.rerun()

        from dashboard import render
        render()

    # FALLBACK
    else:
        st.session_state["page"] = "home"
        st.rerun()

except Exception as e:
    st.error(f"Application error: {e}")

    if st.button("Restart Application"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()