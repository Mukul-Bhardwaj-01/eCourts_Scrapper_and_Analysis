"""
results.py
─────────────────
Page 4 — Results preview.
"""

import os
import re

import pandas as pd
import streamlit as st


EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


TABLE_COLS = [
    ("CNR Number",
     lambda r: r.get("data", {}).get(
         "cnr_number",
         r.get("cnr", "")
     )),

    ("Case Type",
     lambda r: r.get("data", {}).get(
         "case_type", ""
     )),

    ("Case Stage",
     lambda r: r.get("data", {}).get(
         "case_stage", ""
     )),

    ("Court",
     lambda r: r.get("data", {}).get(
         "court_name", ""
     )),

    ("Next Hearing",
     lambda r: r.get("data", {}).get(
         "next_hearing_date", ""
     )),

    ("Lawyer",
     lambda r: r.get("data", {}).get(
         "lawyer", ""
     )),

    ("Opposite Party",
     lambda r: r.get("data", {}).get(
         "opposite_party", ""
     )),

    ("PDF Pages",
     lambda r: r.get(
         "pdf_pages", ""
     )),

    ("Time (s)",
     lambda r: r.get(
         "processing_time", ""
     )),

    ("AI Outcome",
     lambda r: r.get(
         "ai_outcome", ""
     )),

    ("AI Next Action",
     lambda r: r.get(
         "ai_next_action", ""
     )),

    ("Status",
     lambda r:
        "✅ Done"
        if r.get("status") == "done"
        else "❌ Failed"),
]


def _build_dataframe(cases):

    rows = []

    for result in cases:

        row = {}

        for label, extractor in TABLE_COLS:

            try:

                value = extractor(result)

                row[label] = (
                    str(value)
                    if value is not None
                    else ""
                )

            except Exception:

                row[label] = ""

        rows.append(row)

    return pd.DataFrame(rows)


def render():

    cases = st.session_state.get(
        "cases",
        [],
    )

    if not cases:

        st.error(
            "No data found."
        )

        if st.button(
            "← Back"
        ):

            st.session_state[
                "page"
            ] = "case_input"

            st.rerun()

        return

    # header
    st.markdown(
        """
        <h2 style='color:#1F4E79;'>
        📋 Results Preview
        </h2>
        """,
        unsafe_allow_html=True,
    )

    # metrics
    done_cases = [
        c for c in cases
        if c.get(
            "status"
        ) == "done"
    ]

    failed_cases = [
        c for c in cases
        if c.get(
            "status"
        ) == "failed"
    ]

    avg_time = round(
        sum(
            c.get(
                "processing_time",
                0,
            )
            for c in cases
        )
        / max(
            len(cases),
            1,
        ),
        2,
    )

    success_pct = round(
        len(done_cases)
        * 100
        / max(
            len(cases),
            1,
        ),
        1,
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total",
        len(cases),
    )

    c2.metric(
        "Success",
        len(done_cases),
    )

    c3.metric(
        "Failed",
        len(failed_cases),
    )

    c4.metric(
        "Success %",
        f"{success_pct}%",
    )

    st.caption(
        f"Average processing time: "
        f"{avg_time}s"
    )

    if failed_cases:

        with st.expander(
            f"❌ {len(failed_cases)} Failed Cases"
        ):

            for r in failed_cases:

                st.write(
                    f"• `{r.get('cnr')}`"
                    f" — "
                    f"{r.get('error','Unknown')}"
                )

    st.divider()

    # dataframe
    df = _build_dataframe(
        cases
    )

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "AI Outcome":
                st.column_config.TextColumn(
                    width="large"
                ),

            "AI Next Action":
                st.column_config.TextColumn(
                    width="large"
                ),

            "Court":
                st.column_config.TextColumn(
                    width="medium"
                ),
        },
    )

    st.divider()

    # buttons
    col_dl, col_mail, col_dash = (
        st.columns(3)
    )

    excel_path = (
        st.session_state.get(
            "excel_path"
        )
    )

    # download
    with col_dl:

        if (
            excel_path
            and
            os.path.exists(
                excel_path
            )
        ):

            with open(
                excel_path,
                "rb",
            ) as f:

                data = f.read()

            st.download_button(
                "⬇️ Download Excel",
                data=data,
                file_name=os.path.basename(
                    excel_path
                ),
                mime=(
                    "application/"
                    "vnd.openxmlformats-"
                    "officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        else:

            st.button(
                "⬇️ Download Excel",
                disabled=True,
                use_container_width=True,
            )

    # email
    with col_mail:

        if st.button(
            "📧 Mail this to me",
            use_container_width=True,
        ):

            st.session_state[
                "show_email_form"
            ] = True

    # dashboard
    with col_dash:

        if st.button(
            "📊 View Dashboard",
            type="primary",
            use_container_width=True,
        ):

            st.session_state[
                "page"
            ] = "dashboard"

            st.rerun()

    # email form
    if st.session_state.get(
        "show_email_form"
    ):

        st.write("")

        with st.container(
            border=True
        ):

            st.subheader(
                "📧 Send Report"
            )

            email_to = (
                st.text_input(
                    "Recipient",
                    value=st.session_state.get(
                        "user_email",
                        "",
                    ),
                    key="email_to",
                )
            )

            c1, c2 = st.columns(
                [1, 3]
            )

            with c1:

                if st.button(
                    "Send",
                    type="primary",
                ):

                    if not re.match(
                        EMAIL_REGEX,
                        email_to,
                    ):

                        st.error(
                            "Invalid email."
                        )

                    elif (
                        not excel_path
                        or
                        not os.path.exists(
                            excel_path
                        )
                    ):

                        st.error(
                            "Excel file missing."
                        )

                    else:

                        from email_sender import (
                            send_excel_report
                        )

                        with st.spinner(
                            "Sending..."
                        ):

                            ok, msg = (
                                send_excel_report(
                                    recipient_email=email_to,
                                    recipient_name=st.session_state.get(
                                        "user_name",
                                        "Advocate",
                                    ),
                                    excel_path=excel_path,
                                )
                            )

                        if ok:

                            st.success(
                                msg
                            )

                            st.session_state.pop(
                                "show_email_form",
                                None,
                            )

                        else:

                            st.error(
                                msg
                            )

            with c2:

                if st.button(
                    "Cancel"
                ):

                    st.session_state.pop(
                        "show_email_form",
                        None,
                    )

                    st.rerun()