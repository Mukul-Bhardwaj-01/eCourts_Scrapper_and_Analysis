"""
home.py
──────────────
Page 1 — Welcome screen.
Collects the advocate's name and email, stores them in session_state,
then routes to the CNR input page.
"""

import re
from datetime import datetime

import streamlit as st


EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


def render():

    # ─────────────────────────────────────────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding:2rem 0 1rem 0;">
            <h1 style="font-size:2.6rem; color:#1F4E79; margin-bottom:0.2rem;">
                ⚖️ eCourts Legal Analytics
            </h1>
            <p style="color:#555; font-size:1.05rem; margin-top:0;">
                Automated case intelligence for practicing advocates
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # FEATURES
    # ─────────────────────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("##### 🔍 Auto-Scraping")
        st.caption(
            "Fetches case details from eCourts for any number of CNR numbers automatically."
        )

    with col_b:
        st.markdown("##### 🤖 AI Summaries")
        st.caption(
            "Groq LLaMA3 analyzes the latest court order and extracts outcomes, actions, and key parties."
        )

    with col_c:
        st.markdown("##### 📊 Dashboard")
        st.caption(
            "Visual analytics including case distribution, urgency tracking, and hearing trends."
        )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # FORM
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Enter your details to get started")

    st.caption(
        "Your details are used only for report generation and optional email delivery."
    )

    # Welcome returning user
    if st.session_state.get("user_name"):
        st.info(
            f"Welcome back, {st.session_state['user_name']}."
        )

    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:

        name = st.text_input(
            "Full Name",
            placeholder="Adv. Rajesh Kumar",
            value=st.session_state.get("user_name", ""),
            max_chars=100,
        )

        email = st.text_input(
            "Email ID",
            placeholder="advocate@lawfirm.com",
            value=st.session_state.get("user_email", ""),
            max_chars=150,
        )

        st.write("")

        if st.button(
            "Continue →",
            type="primary",
            use_container_width=True,
        ):

            # Clean input
            name = " ".join(name.strip().split())
            email = email.strip()

            # Validation
            if not name:
                st.error("Please enter your full name.")
                return

            if len(name) < 2:
                st.error("Please enter a valid name.")
                return

            if not re.match(EMAIL_REGEX, email):
                st.error("Please enter a valid email address.")
                return

            try:
                # Store user details
                st.session_state["user_name"] = name
                st.session_state["user_email"] = email
                st.session_state["login_time"] = datetime.now()

                # Reset stale values from previous sessions
                st.session_state["cases"] = []
                st.session_state["excel_path"] = None
                st.session_state["scraping_done"] = False
                st.session_state["ai_caseload_para"] = None

                # Navigate
                st.session_state["page"] = "case_input"
                st.rerun()

            except Exception as e:
                st.error(
                    f"Failed to initialize session: {e}"
                )