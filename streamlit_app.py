"""
streamlit_app.py
Phone-friendly front end for the MLB home-run model.
Tap to run tonight's board -> flyer + table. Predictions log themselves to a
Google Sheet (see SETUP_LOGGING.md); accuracy grades straight from that log.
"""
import datetime as dt
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import hr_model as hm
import store
from flyer import build_flyer

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "logo.png")
st.set_page_config(page_title="HR Board",
                   page_icon=LOGO if os.path.exists(LOGO) else "\u26be",
                   layout="centered")

SEASON = 2026
DISPLAY_COLS = ["player", "team", "opp_SP", "slot", "p_HR_%",
                "fair_odds", "season_HR", "season_PA", "flags"]


@st.cache_data(ttl=600, show_spinner=False)
def run_board(date_str, season, top_n):
    return hm.run(date_str, season, top_n)


if os.path.exists(LOGO):
    hc1, hc2 = st.columns([1, 5], vertical_alignment="center")
    hc1.image(LOGO, width=76)
    hc2.title("Tonight's Home Run Board")
else:
    st.title("Tonight's Home Run Board")

c1, c2 = st.columns([2, 1])
date = c1.date_input("Slate date", dt.date.today())
if c2.button("Refresh data", use_container_width=True):
    run_board.clear()
    st.rerun()

d = date.isoformat()
with st.spinner("Pulling the slate and season stats\u2026"):
    df = run_board(d, SEASON, 40)

if df is None or len(df) == 0:
    st.warning("No games or no rankable batters for this date yet.")
    st.stop()

# Auto-log tonight's top 10 (replaces an earlier same-day run).
if store.logging_available():
    try:
        store.log_board(df, d, top_n=10)
        st.caption("\u2713 Logged tonight's top 10 for accuracy tracking.")
    except Exception as exc:  # noqa: BLE001
        st.caption(f"(Couldn't write to the log sheet: {exc})")

# Flyer is the headline view.
components.html(build_flyer(df, d, top_n=10), height=1550, scrolling=True)

with st.expander("Full ranked board (all matchups)"):
    st.dataframe(df[[c for c in DISPLAY_COLS if c in df.columns]],
                 use_container_width=True, hide_index=True)

st.download_button("Download board (CSV)", df.to_csv(index=False),
                   file_name=f"hr_board_{d}.csv", mime="text/csv")
st.caption("Tip: run after lineups post (1\u20133 hrs before first pitch). "
           "Rows flagged no_lineup are projected and will shift.")

# ---------------------------------------------------------------- accuracy
st.divider()
st.subheader("Accuracy")


def _show_grades(log):
    with st.spinner("Scoring against final box scores\u2026"):
        per_date, calib, overall = hm.grade_log(log)
    if overall is None:
        st.info("No finished dates in the log yet \u2014 grade after games go final.")
        return
    m1, m2, m3 = st.columns(3)
    m1.metric("Nights", overall["nights"])
    m2.metric("Top-list hit rate", f"{overall['hit_rate']}%")
    m3.metric("Brier", overall["brier"])
    st.write("**By night**")
    st.dataframe(per_date, use_container_width=True, hide_index=True)
    st.write("**Calibration** (predicted vs. actual HR rate by bucket)")
    st.dataframe(calib, use_container_width=True, hide_index=True)


if store.logging_available():
    st.caption("Reads your own log automatically \u2014 no uploads.")
    if st.button("Grade my logged picks"):
        try:
            log = store.load_log()
            if len(log) == 0:
                st.info("Nothing logged yet. Run a board or two first.")
            else:
                _show_grades(log)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Couldn't read the log: {exc}")
else:
    st.caption("Self-logging isn't set up yet (see SETUP_LOGGING.md). "
               "You can still grade by uploading a log CSV:")
    up = st.file_uploader("Prediction log CSV", type="csv", label_visibility="collapsed")
    if up is not None:
        try:
            _show_grades(pd.read_csv(up))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Couldn't read/grade that file: {exc}")
