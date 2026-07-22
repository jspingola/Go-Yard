"""
streamlit_app.py
Phone-friendly front end for the MLB home-run model.
Tap to run tonight's board -> see the flyer, the full table, and (optionally)
your accuracy by uploading the prediction log from the Colab notebook.
"""
import datetime as dt

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import hr_model as hm
from flyer import build_flyer

st.set_page_config(page_title="HR Board", page_icon="\u26be", layout="centered")

SEASON = 2026
DISPLAY_COLS = ["player", "team", "opp_SP", "slot", "p_HR_%",
                "fair_odds", "season_HR", "season_PA", "flags"]


@st.cache_data(ttl=600, show_spinner=False)
def run_board(date_str, season, top_n):
    """Cached so tapping around doesn't re-pull the API for 10 minutes."""
    return hm.run(date_str, season, top_n)


st.title("\u26be Tonight's Home Run Board")

c1, c2 = st.columns([2, 1])
date = c1.date_input("Slate date", dt.date.today())
if c2.button("Refresh data", use_container_width=True):
    run_board.clear()
    st.rerun()

d = date.isoformat()
with st.spinner("Pulling the slate and season stats\u2026"):
    df = run_board(d, SEASON, 40)

if df is None or len(df) == 0:
    st.warning("No games or no rankable batters for this date yet. "
               "Try again once lineups or stats are available.")
    st.stop()

# The flyer (auto-generated) is the headline view.
components.html(build_flyer(df, d, top_n=10), height=1550, scrolling=True)

with st.expander("Full ranked board (all matchups)"):
    st.dataframe(df[[c for c in DISPLAY_COLS if c in df.columns]],
                 use_container_width=True, hide_index=True)

st.download_button("Download board (CSV)", df.to_csv(index=False),
                   file_name=f"hr_board_{d}.csv", mime="text/csv")

st.caption("Tip: run this after lineups post (1\u20133 hrs before first pitch). "
           "Rows flagged no_lineup are projected and will shift.")

# ---------------------------------------------------------------- accuracy
st.divider()
st.subheader("Accuracy check")
st.caption("Upload the prediction log the notebook saves to your Google Drive "
           "(hr_model_log.csv) to grade past picks against who actually homered.")

up = st.file_uploader("Prediction log CSV", type="csv", label_visibility="collapsed")
if up is not None:
    try:
        log = pd.read_csv(up)
        with st.spinner("Scoring against final box scores\u2026"):
            per_date, calib, overall = hm.grade_log(log)
        if overall is None:
            st.info("No finished dates in that log yet \u2014 grade after games go final.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Nights", overall["nights"])
            m2.metric("Top-list hit rate", f"{overall['hit_rate']}%")
            m3.metric("Brier", overall["brier"])
            st.write("**By night**")
            st.dataframe(per_date, use_container_width=True, hide_index=True)
            st.write("**Calibration** (predicted vs. actual HR rate by bucket)")
            st.dataframe(calib, use_container_width=True, hide_index=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Couldn't read/grade that file: {exc}")
