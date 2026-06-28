"""
scraping.py
──────────────────
Page 3 — Live scraping progress.
"""

import time
import streamlit as st


_ICONS = {
    "pending": "⏳",
    "opening": "🌐",
    "captcha": "⏸️",
    "extract": "📋",
    "pdf": "📄",
    "ai": "🤖",
    "done": "✅",
    "failed": "❌",
}


def _render_status_table(placeholder, statuses):

    with placeholder.container():

        for cnr, s in statuses.items():

            cols = st.columns([0.08, 0.3, 0.62])

            cols[0].write(
                _ICONS.get(
                    s["state"],
                    "⏳",
                )
            )

            cols[1].write(
                f"`{cnr}`"
            )

            cols[2].write(
                s["msg"]
            )


def render():

    cnr_list = st.session_state.get(
        "cnr_list",
        [],
    )

    if not cnr_list:

        st.error(
            "No CNR numbers found."
        )

        if st.button(
            "← Back"
        ):
            st.session_state[
                "page"
            ] = "case_input"

            st.rerun()

        return

    # already finished
    if st.session_state.get(
        "scraping_done"
    ):

        st.success(
            f"✅ Scraping complete — "
            f"{len(st.session_state.get('cases', []))} "
            f"CNR(s) processed."
        )

        if st.button(
            "View Results →",
            type="primary",
        ):
            st.session_state[
                "page"
            ] = "results"

            st.rerun()

        return

    # header
    st.markdown(
        """
        <h2 style="color:#1F4E79;">
        Scraping in Progress
        </h2>
        """,
        unsafe_allow_html=True,
    )

    st.warning(
        f"Processing "
        f"{len(cnr_list)} CNR(s).\n\n"
        "A Chrome window will open. "
        "Whenever a CAPTCHA appears, "
        "solve it and press Search.",
        icon="⚠️",
    )

    st.divider()

    statuses = {
        cnr: {
            "state": "pending",
            "msg": "Pending",
        }
        for cnr in cnr_list
    }

    placeholder = st.empty()

    _render_status_table(
        placeholder,
        statuses,
    )

    # imports
    from selenium_handler import (
        setup_driver,
        open_search_page,
        enter_cnr_number,
        wait_for_case_results,
        extract_case_data,
        download_latest_order,
    )

    from pdf_extractor import (
        extract_order_text,
        get_pdf_metadata,
    )

    from groq_summary import (
        summarise_order,
    )

    from excel_generator import (
        generate_excel,
    )

    results = []

    # launch browser
    try:

        driver, download_dir = (
            setup_driver()
        )

    except Exception as e:

        st.error(
            f"Chrome launch failed:\n\n{e}"
        )

        return

    try:

        for cnr in cnr_list:

            start = time.time()

            result = {
                "cnr": cnr,
                "status": "pending",
                "data": {},
                "pdf_path": None,
                "pdf_pages": 0,
                "pdf_size_kb": 0,
                "processing_time": 0,
                "ai_outcome": "",
                "ai_next_action": "",
                "ai_key_parties": "",
                "error": None,
            }

            try:

                # open page
                statuses[cnr] = {
                    "state": "opening",
                    "msg":
                    "Opening eCourts...",
                }

                _render_status_table(
                    placeholder,
                    statuses,
                )

                open_search_page(
                    driver
                )

                enter_cnr_number(
                    driver,
                    cnr,
                )

                # captcha
                statuses[cnr] = {
                    "state": "captcha",
                    "msg":
                    "Waiting for CAPTCHA..."
                }

                _render_status_table(
                    placeholder,
                    statuses,
                )

                solved = (
                    wait_for_case_results(
                        driver,
                        timeout=120,
                    )
                )

                if not solved:
                    raise TimeoutError(
                        "CAPTCHA timeout."
                    )

                # extraction
                statuses[cnr] = {
                    "state": "extract",
                    "msg":
                    "Extracting case data..."
                }

                _render_status_table(
                    placeholder,
                    statuses,
                )

                result["data"] = (
                    extract_case_data(
                        driver
                    )
                )

                # pdf
                statuses[cnr] = {
                    "state": "pdf",
                    "msg":
                    "Downloading order..."
                }

                _render_status_table(
                    placeholder,
                    statuses,
                )

                pdf_path = (
                    download_latest_order(
                        driver,
                        download_dir,
                        cnr,
                    )
                )

                result[
                    "pdf_path"
                ] = pdf_path

                if pdf_path:

                    meta = (
                        get_pdf_metadata(
                            pdf_path
                        )
                    )

                    result[
                        "pdf_pages"
                    ] = meta[
                        "pages"
                    ]

                    result[
                        "pdf_size_kb"
                    ] = meta[
                        "size_kb"
                    ]

                # ai
                statuses[cnr] = {
                    "state": "ai",
                    "msg":
                    "Generating AI summary..."
                }

                _render_status_table(
                    placeholder,
                    statuses,
                )

                order_text = ""

                if pdf_path:
                    order_text = (
                        extract_order_text(
                            pdf_path
                        )
                    )

                ai = (
                    summarise_order(
                        order_text,
                        cnr,
                    )
                )

                result[
                    "ai_outcome"
                ] = ai[
                    "ai_outcome"
                ]

                result[
                    "ai_next_action"
                ] = ai[
                    "ai_next_action"
                ]

                result[
                    "ai_key_parties"
                ] = ai[
                    "ai_key_parties"
                ]

                result[
                    "status"
                ] = "done"

                statuses[cnr] = {
                    "state": "done",
                    "msg":
                    "Complete",
                }

                st.session_state[
                    "successful_cases"
                ] += 1

            except Exception as e:

                result[
                    "status"
                ] = "failed"

                result[
                    "error"
                ] = str(e)

                statuses[cnr] = {
                    "state": "failed",
                    "msg":
                    str(e)[:80],
                }

                st.session_state[
                    "failed_cases"
                ] += 1

                st.session_state[
                    "errors"
                ].append(
                    {
                        "cnr": cnr,
                        "error": str(e),
                    }
                )

            result[
                "processing_time"
            ] = round(
                time.time()
                - start,
                2,
            )

            results.append(
                result
            )

            _render_status_table(
                placeholder,
                statuses,
            )

            time.sleep(0.5)

    finally:

        try:
            driver.quit()
        except Exception:
            pass

    # excel
    excel_path = None

    try:

        excel_path = (
            generate_excel(
                results,
                st.session_state.get(
                    "user_name",
                    "Advocate",
                ),
            )
        )

    except Exception as e:

        st.warning(
            f"Excel generation failed:\n{e}"
        )

    # store
    st.session_state[
        "cases"
    ] = results

    st.session_state[
        "excel_path"
    ] = excel_path

    st.session_state[
        "scraping_done"
    ] = True

    done = sum(
        1
        for r in results
        if r["status"] == "done"
    )

    failed = (
        len(results)
        - done
    )

    st.divider()

    if failed:

        st.warning(
            f"✅ {done} succeeded "
            f"| ❌ {failed} failed"
        )

    else:

        st.success(
            f"✅ All "
            f"{done} CNR(s) "
            f"processed."
        )

    if st.button(
        "View Results →",
        type="primary",
    ):

        st.session_state[
            "page"
        ] = "results"

        st.rerun()