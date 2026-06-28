"""
dashboard.py
───────────────────
Page 5 — Analytics Dashboard.

Layout:
  Row 1 : Pie — Case Types  |  AI Caseload Paragraph
  Row 2 : Bar — Case Stage  |  Urgent Hearings Callout (≤7 days)
  Row 3 : Full-width Upcoming Hearings Table (colour-coded)
  Row 4 : Bar — Hearings per Case  |  Stalled Cases Callout (≥3 adj.)
  Row 5 : Bar — Court Workload  |  Line — Monthly Filing Trends  |  Bar — Judge Distribution
  Row 6 : Bar — Opposite Party Portfolio  |  Avg Time Between Hearings metric
"""

import re
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from collections import Counter
from datetime import date, datetime, timedelta


# ─────────────────────────────────────────────────────────────────────────────
#  DATE HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _parse_date(raw) -> date | None:
    """
    Parse eCourts date strings to a Python date.
    Handles: '02nd November 2026', '03-05-2025', '29-04-2026', '03 May 2025'
    """
    if not raw:
        return None
    s = str(raw).strip()
    # Remove ordinal suffixes: 1st→1, 2nd→2, 3rd→3, 4th→4 …
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)
    for fmt in ("%d %B %Y", "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _done(cases):
    return [c for c in cases if c.get("status") == "done"]


def _d(result, key, default=""):
    """Safely get a field from result['data']."""
    return result.get("data", {}).get(key, default) or default


# ─────────────────────────────────────────────────────────────────────────────
#  CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_PALETTE = px.colors.qualitative.Bold

_LAYOUT = dict(
    margin=dict(t=40, b=20, l=20, r=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Calibri, sans-serif", size=12),
)


def _pie(labels, values, title):
    fig = px.pie(
        names=labels, values=values,
        title=title, color_discrete_sequence=_PALETTE,
        hole=0.35,
    )
    fig.update_traces(textinfo="label+percent", pull=[0.03] * len(labels))
    fig.update_layout(**_LAYOUT)
    return fig


def _bar_h(labels, values, title, xlabel="Count", colour="#2E75B6"):
    df = pd.DataFrame({"label": labels, "value": values}).sort_values("value")
    fig = px.bar(
        df, x="value", y="label", orientation="h",
        title=title, labels={"value": xlabel, "label": ""},
        color_discrete_sequence=[colour],
    )
    fig.update_layout(**_LAYOUT, yaxis=dict(automargin=True))
    return fig


def _line(x, y, title, xlabel="", ylabel=""):
    fig = px.line(
        x=x, y=y, markers=True,
        title=title, labels={"x": xlabel, "y": ylabel},
        color_discrete_sequence=["#1F4E79"],
    )
    fig.update_layout(**_LAYOUT)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    cases = st.session_state.get("cases", [])

    if not cases:
        st.error("No data available. Please run the scraper first.")
        if st.button("← Back to Results"):
            st.session_state["page"] = "results"
            st.rerun()
        return

    done_cases = _done(cases)

    if not done_cases:
        st.warning("All CNRs failed to scrape. No data to visualise.")
        if st.button("← Back to Results"):
            st.session_state["page"] = "results"
            st.rerun()
        return

    # ── Top bar ───────────────────────────────────────────────────────────────
    st.markdown(
        f"<h2 style='color:#1F4E79;'>📊 Analytics Dashboard"
        f" <span style='font-size:1rem;color:#777;'>"
        f"— {st.session_state.get('user_name','Advocate')} · "
        f"{len(done_cases)} case(s)</span></h2>",
        unsafe_allow_html=True,
    )

    col_back, _, col_results = st.columns([1, 4, 1])
    with col_back:
        if st.button("← Results"):
            st.session_state["page"] = "results"
            st.rerun()

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  ROW 1 — Case Type Pie  |  AI Caseload Paragraph
    # ─────────────────────────────────────────────────────────────────────────
    r1_left, r1_right = st.columns([3, 2])

    with r1_left:
        types = [_d(c, "case_type") or "Unknown" for c in done_cases]
        tc = Counter(types)
        st.plotly_chart(
            _pie(list(tc.keys()), list(tc.values()), "Case Type Distribution"),
            use_container_width=True,
        )

    with r1_right:
        st.markdown("#### 🤖 AI Caseload Analysis")

        # Cache the AI paragraph so it isn't regenerated on every rerun
        if not st.session_state.get("ai_caseload_para"):
            with st.spinner("Generating AI analysis…"):
                from groq_summary import summarise_caseload
                para = summarise_caseload([
                    {
                        "cnr_number":      _d(c, "cnr_number"),
                        "case_type":       _d(c, "case_type"),
                        "case_stage":      _d(c, "case_stage"),
                        "next_hearing_date": _d(c, "next_hearing_date"),
                        "consecutive_adjournments": _d(c, "consecutive_adjournments", 0),
                    }
                    for c in done_cases
                ])
            st.session_state["ai_caseload_para"] = para

        st.info(st.session_state["ai_caseload_para"])

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  ROW 2 — Case Stage Bar  |  Urgent Hearings Callout
    # ─────────────────────────────────────────────────────────────────────────
    r2_left, r2_right = st.columns([3, 2])

    with r2_left:
        stages = [_d(c, "case_stage") or "Unknown" for c in done_cases]
        sc = Counter(stages)
        st.plotly_chart(
            _bar_h(list(sc.keys()), list(sc.values()), "Case Stage Breakdown", colour="#2E75B6"),
            use_container_width=True,
        )

    with r2_right:
        st.markdown("#### 🚨 Urgent Hearings (≤ 7 days)")
        today  = date.today()
        urgent = []
        for c in done_cases:
            nd = _parse_date(_d(c, "next_hearing_date"))
            if nd and 0 <= (nd - today).days <= 7:
                urgent.append(c)

        if not urgent:
            st.success("No hearings in the next 7 days. 🎉")
        else:
            for c in urgent:
                nd  = _parse_date(_d(c, "next_hearing_date"))
                gap = (nd - today).days
                st.error(
                    f"**`{_d(c,'cnr_number')}`**  \n"
                    f"{_d(c,'case_type')} · {_d(c,'opposite_party')}  \n"
                    f"📅 **{_d(c,'next_hearing_date')}** ({gap} day(s) away)"
                )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  ROW 3 — Upcoming Hearings Table (colour-coded)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 📅 Upcoming Hearings — Sorted Nearest First")

    upcoming = []
    for c in done_cases:
        nd = _parse_date(_d(c, "next_hearing_date"))
        if nd and nd >= today:
            gap  = (nd - today).days
            upcoming.append({
                "CNR":            _d(c, "cnr_number"),
                "Case Type":      _d(c, "case_type"),
                "Opposite Party": _d(c, "opposite_party"),
                "Next Hearing":   _d(c, "next_hearing_date"),
                "Stage":          _d(c, "case_stage"),
                "Days Away":      gap,
                "_gap":           gap,   # used for styling
            })

    if not upcoming:
        st.info("No upcoming hearings found in the scraped data.")
    else:
        upcoming.sort(key=lambda x: x["_gap"])

        def _row_style(row):
            g = row["_gap"]
            colour = (
                "background-color: #FFD6D6" if g <= 7 else
                "background-color: #FFF4CC" if g <= 30 else
                "background-color: #D6F0D6"
            )
            return [colour] * len(row)

        df_up = pd.DataFrame(upcoming).drop(columns=["_gap"])
        styled = df_up.style.apply(_row_style, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

        with st.expander("🟥 Red = ≤7 days  🟨 Yellow = ≤30 days  🟩 Green = >30 days"):
            pass

    # ── Mini timeline popup on row click ─────────────────────────────────────
    if upcoming:
        st.write("")
        selected_cnr = st.selectbox(
            "View hearing timeline for CNR:",
            options=["— select —"] + [u["CNR"] for u in upcoming],
        )
        if selected_cnr != "— select —":
            # Find matching case
            matched = next((c for c in done_cases if _d(c, "cnr_number") == selected_cnr), None)
            if matched:
                history = matched.get("data", {}).get("case_history", [])
                if history:
                    timeline_df = pd.DataFrame(history)[["hearing_date", "purpose", "judge"]]
                    timeline_df.columns = ["Hearing Date", "Purpose", "Judge"]
                    st.dataframe(timeline_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No hearing history available for this case.")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  ROW 4 — Hearings Per Case Bar  |  Stalled Cases
    # ─────────────────────────────────────────────────────────────────────────
    r4_left, r4_right = st.columns([3, 2])

    with r4_left:
        hpc_cnrs   = [_d(c, "cnr_number") or c.get("cnr", "") for c in done_cases]
        hpc_counts = [int(_d(c, "hearing_count") or 0) for c in done_cases]
        paired     = sorted(zip(hpc_counts, hpc_cnrs), reverse=True)
        hpc_counts, hpc_cnrs = zip(*paired) if paired else ([], [])
        st.plotly_chart(
            _bar_h(list(hpc_cnrs), list(hpc_counts), "Hearings per Case", "Hearings", "#1F4E79"),
            use_container_width=True,
        )

    with r4_right:
        st.markdown("#### ⚠️ Stalled Cases (≥ 3 Consecutive Adjournments)")
        stalled = [
            c for c in done_cases
            if int(_d(c, "consecutive_adjournments") or 0) >= 3
        ]
        if not stalled:
            st.success("No stalled cases detected.")
        else:
            for c in stalled:
                adj = _d(c, "consecutive_adjournments")
                st.warning(
                    f"**`{_d(c,'cnr_number')}`**  \n"
                    f"{_d(c,'case_type')} · {_d(c,'opposite_party')}  \n"
                    f"🔁 **{adj} consecutive adjournments**"
                )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  ROW 5 — Court Workload | Monthly Filing Trends | Judge Distribution
    # ─────────────────────────────────────────────────────────────────────────
    r5a, r5b, r5c = st.columns(3)

    with r5a:
        courts = [_d(c, "court_name") or "Unknown" for c in done_cases]
        # Shorten long court names for readability
        courts = [ct[:30] + "…" if len(ct) > 30 else ct for ct in courts]
        cc = Counter(courts)
        st.plotly_chart(
            _bar_h(list(cc.keys()), list(cc.values()), "Court-wise Workload", colour="#5B9BD5"),
            use_container_width=True,
        )

    with r5b:
        # Monthly filing trends
        filing_months = []
        for c in done_cases:
            fd = _parse_date(_d(c, "filing_date"))
            if fd:
                filing_months.append(fd.strftime("%b %Y"))

        if filing_months:
            mc = Counter(filing_months)
            # Sort chronologically
            all_months = sorted(mc.keys(), key=lambda m: datetime.strptime(m, "%b %Y"))
            st.plotly_chart(
                _line(
                    all_months,
                    [mc[m] for m in all_months],
                    "Monthly Filing Trends",
                    "Month",
                    "Cases Filed",
                ),
                use_container_width=True,
            )
        else:
            st.info("No filing dates available for trend analysis.")

    with r5c:
        judges = [_d(c, "court_judge") or "Unknown" for c in done_cases]
        judges = [j[:25] + "…" if len(j) > 25 else j for j in judges]
        jc = Counter(judges)
        st.plotly_chart(
            _bar_h(list(jc.keys()), list(jc.values()), "Judge-wise Distribution", colour="#70AD47"),
            use_container_width=True,
        )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  ROW 6 — Client Portfolio  |  Avg Time Between Hearings
    # ─────────────────────────────────────────────────────────────────────────
    r6_left, r6_right = st.columns([3, 2])

    with r6_left:
        parties = [_d(c, "opposite_party") or "Unknown" for c in done_cases]
        parties = [p[:30] + "…" if len(p) > 30 else p for p in parties]
        pc = Counter(parties)
        st.plotly_chart(
            _bar_h(
                list(pc.keys()), list(pc.values()),
                "Client / Opposite Party Portfolio", colour="#ED7D31",
            ),
            use_container_width=True,
        )

    with r6_right:
        st.markdown("#### ⏱️ Average Time Between Hearings")

        gaps_all = []
        for c in done_cases:
            history = c.get("data", {}).get("case_history", [])
            dates   = sorted(
                filter(None, [_parse_date(h.get("hearing_date")) for h in history])
            )
            for i in range(1, len(dates)):
                gaps_all.append((dates[i] - dates[i - 1]).days)

        if gaps_all:
            avg_gap = sum(gaps_all) / len(gaps_all)
            min_gap = min(gaps_all)
            max_gap = max(gaps_all)

            m1, m2, m3 = st.columns(3)
            m1.metric("Avg Gap",  f"{avg_gap:.0f} days")
            m2.metric("Min Gap",  f"{min_gap} days")
            m3.metric("Max Gap",  f"{max_gap} days")

            # Distribution histogram
            fig_hist = px.histogram(
                x=gaps_all, nbins=15,
                title="Gap Distribution (days between hearings)",
                labels={"x": "Days Between Hearings", "y": "Frequency"},
                color_discrete_sequence=["#1F4E79"],
            )
            fig_hist.update_layout(**_LAYOUT)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Not enough hearing history to calculate gaps.")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    #  PENDING VS DISPOSED  +  AVERAGE HEARINGS PER TYPE
    # ─────────────────────────────────────────────────────────────────────────
    r7_left, r7_right = st.columns(2)

    with r7_left:
        st.markdown("#### ⚖️ Pending vs Disposed")
        disposed_kw = ("disposed", "decided", "acquitted", "convicted", "dismissed", "settled")
        disposed = sum(1 for c in done_cases if any(kw in _d(c, "case_stage").lower() for kw in disposed_kw))
        pending  = len(done_cases) - disposed
        fig_pv = px.pie(
            names=["Pending", "Disposed"],
            values=[pending, disposed],
            color_discrete_sequence=["#ED7D31", "#70AD47"],
            hole=0.4,
            title="Pending vs Disposed",
        )
        fig_pv.update_layout(**_LAYOUT)
        st.plotly_chart(fig_pv, use_container_width=True)

    with r7_right:
        st.markdown("#### 📌 Average Hearings per Case Type")
        type_hearings: dict[str, list] = {}
        for c in done_cases:
            ct = _d(c, "case_type") or "Unknown"
            hc = int(_d(c, "hearing_count") or 0)
            type_hearings.setdefault(ct, []).append(hc)

        if type_hearings:
            avgs   = {t: sum(v) / len(v) for t, v in type_hearings.items()}
            labels = list(avgs.keys())
            values = [round(v, 1) for v in avgs.values()]
            fig_avg = px.bar(
                x=labels, y=values,
                title="Avg Hearings per Case Type",
                labels={"x": "Case Type", "y": "Avg Hearings"},
                color_discrete_sequence=["#2E75B6"],
            )
            fig_avg.update_layout(**_LAYOUT)
            st.plotly_chart(fig_avg, use_container_width=True)
        else:
            st.info("Not enough data.")