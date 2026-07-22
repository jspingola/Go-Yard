"""
store.py
Durable, self-contained prediction logging via a Google Sheet the user owns.
No notebook needed: the app writes each night's board here and reads it back to
grade accuracy. If credentials aren't set up yet, logging_available() returns
False and the app falls back to manual CSV upload.

Setup (one time) is in SETUP_LOGGING.md. It relies on two Streamlit secrets:
  - [gcp_service_account]  (the service-account JSON)
  - log_sheet_url          (the URL of your Google Sheet)
"""
import pandas as pd
import streamlit as st

LOG_COLUMNS = ["pred_date", "mlbam_id", "player", "team", "p_HR_%"]


def logging_available():
    """True only if both secrets are present, so the app degrades gracefully."""
    try:
        return "gcp_service_account" in st.secrets and "log_sheet_url" in st.secrets
    except Exception:
        return False


def _worksheet():
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes)
    gc = gspread.authorize(creds)
    ws = gc.open_by_url(st.secrets["log_sheet_url"]).sheet1
    if not ws.get_all_values():                       # empty sheet -> write header
        ws.update(range_name="A1", values=[LOG_COLUMNS])
    return ws


def load_log(ws=None):
    ws = ws or _worksheet()
    df = pd.DataFrame(ws.get_all_records())
    return df if len(df) else pd.DataFrame(columns=LOG_COLUMNS)


def log_board(df, date_str, top_n=10, ws=None):
    """Save the top-N as this date's record; replaces any earlier same-day run."""
    ws = ws or _worksheet()
    existing = load_log(ws)
    if len(existing):
        existing = existing[existing["pred_date"].astype(str) != date_str]
    top = df.head(top_n)[["mlbam_id", "player", "team", "p_HR_%"]].copy()
    top.insert(0, "pred_date", date_str)
    combined = (pd.concat([existing[LOG_COLUMNS], top[LOG_COLUMNS]], ignore_index=True)
                if len(existing) else top[LOG_COLUMNS])
    body = [LOG_COLUMNS] + combined.astype(object).values.tolist()
    ws.clear()
    ws.update(range_name="A1", values=body)
    return len(combined)
