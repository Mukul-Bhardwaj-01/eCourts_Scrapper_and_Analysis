"""
case_input.py
────────────────────
Page 2 — CNR number entry.
Accepts bulk CNR input (comma-separated or one per line),
validates the format, and routes to the scraping page.
"""

import re
import streamlit as st

MAX_CNRS = 100


def _validate_cnr(cnr: str) -> bool:
    """
    eCourts CNR format:
    Example: HRAM030050242025
    """
    cnr = cnr.upper().strip()
    return bool(re.fullmatch(r"[A-Z]{2}[A-Z0-9]{14}", cnr))


def render():

    user_name = st.session_state.get("user_name", "Advocate")

    st.markdown(
        f"""
        <h2 style="color:#1F4E79;">Welcome, {user_name}</h2>
        <p style="color:#555;">
            Enter the CNR numbers you want to fetch from eCourts.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "**CNR format:** 16 characters, e.g. `HRAM030050242025`\n\n"
        "• Enter multiple CNRs separated by commas or new lines.\n"
        "• Duplicate CNRs will automatically be removed.\n"
        "• Maximum allowed in one run: 100."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # INPUT
    # ─────────────────────────────────────────────────────────────────────────
    raw_input = st.text_area(
        "CNR Numbers",
        height=200,
        placeholder=(
            "HRAM030050242025\n"
            "MHAU019999992015\n"
            "DLNE010123452024"
        ),
        value="\n".join(
            st.session_state.get("cnr_list", [])
        ),
        help="One CNR per line or comma-separated.",
    )

    valid = []
    invalid = []

    if raw_input.strip():

        # Normalize separators
        raw_input = raw_input.replace(";", "\n")

        cnrs = [
            c.strip().upper()
            for c in re.split(r"[\n,]+", raw_input)
            if c.strip()
        ]

        # Cap size
        if len(cnrs) > MAX_CNRS:
            st.warning(
                f"Only the first {MAX_CNRS} CNRs will be processed."
            )
            cnrs = cnrs[:MAX_CNRS]

        # Remove duplicates
        unique_cnrs = list(
            dict.fromkeys(cnrs)
        )

        duplicate_count = (
            len(cnrs)
            - len(unique_cnrs)
        )

        valid = [
            c for c in unique_cnrs
            if _validate_cnr(c)
        ]

        invalid = [
            c for c in unique_cnrs
            if not _validate_cnr(c)
        ]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Valid CNRs",
            len(valid)
        )

        col2.metric(
            "Invalid CNRs",
            len(invalid)
        )

        col3.metric(
            "Duplicates Removed",
            duplicate_count
        )

        if invalid:
            st.warning(
                "These CNRs do not match the required format:\n\n"
                + "\n".join(
                    f"• {x}"
                    for x in invalid
                )
            )

        if valid:
            st.success(
                f"{len(valid)} CNR(s) ready for processing."
            )

            with st.expander(
                f"Preview — {len(valid)} CNR(s)"
            ):
                for i, cnr in enumerate(valid, 1):
                    st.write(
                        f"{i}. `{cnr}`"
                    )

    st.write("")

    # ─────────────────────────────────────────────────────────────────────────
    # BUTTONS
    # ─────────────────────────────────────────────────────────────────────────
    col_back, _, col_fetch = st.columns(
        [1, 3, 1]
    )

    with col_back:
        if st.button("← Back"):

            st.session_state["page"] = "home"
            st.rerun()

    with col_fetch:

        fetch_clicked = st.button(
            "Fetch from eCourts →",
            type="primary",
            disabled=(len(valid) == 0),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # START SCRAPING
    # ─────────────────────────────────────────────────────────────────────────
    if fetch_clicked:

        if not valid:
            st.error(
                "Please enter at least one valid CNR."
            )
            return

        try:

            # Reset previous run
            reset_keys = [
                "cases",
                "excel_path",
                "scraping_done",
                "successful_cases",
                "failed_cases",
                "ai_failures",
                "errors",
                "ai_caseload_para",
                "show_email_form",
            ]

            for key in reset_keys:
                st.session_state.pop(
                    key,
                    None,
                )

            # Initialize analytics
            st.session_state[
                "successful_cases"
            ] = 0

            st.session_state[
                "failed_cases"
            ] = 0

            st.session_state[
                "ai_failures"
            ] = 0

            st.session_state[
                "errors"
            ] = []

            # Store CNRs
            st.session_state[
                "cnr_list"
            ] = valid

            st.session_state[
                "invalid_cnrs"
            ] = invalid

            # Navigate
            st.session_state[
                "page"
            ] = "scraping"

            st.rerun()

        except Exception as e:
            st.error(
                f"Failed to initialize scraping: {e}"
            )