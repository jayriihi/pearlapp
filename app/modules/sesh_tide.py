import requests
import pandas as pd
import datetime as dt
from datetime import timedelta, datetime

def format_date_time(datetimelocal_str, duration_str):
    # Parse start datetime from <input type="datetime-local">
    sesh_start_datetime = dt.datetime.strptime(datetimelocal_str, '%Y-%m-%dT%H:%M')

    # Pretty strings (kept for compatibility with existing callers)
    sesh_start_date_str = dt.datetime.strftime(sesh_start_datetime, '%d %b')
    sesh_start_time_str = dt.datetime.strftime(sesh_start_datetime, '%-I:%M %p')

    # Parse duration "H:MM"
    h, m = [int(x) for x in duration_str.split(':')]
    sesh_duration = timedelta(hours=h, minutes=m)
    sesh_end_time = sesh_start_datetime + sesh_duration

    string_start_time = dt.datetime.strftime(sesh_start_datetime, "%H:%M")
    string_end_time = dt.datetime.strftime(sesh_end_time, "%H:%M")
    sesh_date = datetime.date(sesh_start_datetime)

    return (
        string_start_time, string_end_time, h, m,
        sesh_start_date_str, sesh_start_time_str,
        sesh_start_datetime, sesh_duration, sesh_end_time, sesh_date
    )

def get_tide_data_for_session(datetimelocal_str, duration_str):
    (string_start_time, string_end_time, h, m,
     sesh_start_date_str, sesh_start_time_str,
     sesh_start_datetime, sesh_duration, sesh_end_time, sesh_date) = format_date_time(datetimelocal_str, duration_str)

    # Build a window that straddles midnight: yesterday → tomorrow
    sesh_date = datetime.date(sesh_start_datetime)
    prev_date_str = (sesh_date - timedelta(days=1)).strftime('%Y%m%d')
    next_date_str = (sesh_date + timedelta(days=1)).strftime('%Y%m%d')

    noaa_api_url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        "?product=predictions&application=NOS.COOPS.TAC.WL"
        f"&begin_date={prev_date_str}&end_date={next_date_str}"
        "&datum=MLLW&station=2695540&time_zone=lst_ldt&units=english"
        "&interval=hilo&format=json"
    )

    # Fetch + basic hardening
    resp = requests.get(noaa_api_url, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    preds = payload.get("predictions", [])

    if not preds:
        # Safe fallback if NOAA returns nothing
        return ("Slack", "Slack", None, None, None, None)

    # Build dataframe
    df = pd.DataFrame(preds)
    df.rename(columns={"t": "Datetime", "v": "Ht", "type": "Tide"}, inplace=True)
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df["Ht"] = pd.to_numeric(df["Ht"], errors="coerce")
    df.dropna(subset=["Datetime"], inplace=True)
    df.set_index("Datetime", inplace=True)
    tide_time_dict = df.to_dict(orient="index")

    time = sesh_start_datetime

    # ---------- helpers (defensive) ----------
    def get_prev_time_and_state(now, dct):
        candidates = [k for k in dct.keys() if k <= now]
        if not candidates:
            return None, None, None
        t = max(candidates)
        v = dct[t]
        ht = v.get("Ht")
        ht = round(float(ht), 1) if ht is not None else None
        return t, v.get("Tide"), ht

    def get_next_time_and_state(now, dct):
        candidates = [k for k in dct.keys() if k >= now]
        if not candidates:
            return None, None, None
        t = min(candidates)
        v = dct[t]
        ht = v.get("Ht")
        ht = round(float(ht), 1) if ht is not None else None
        return t, v.get("Tide"), ht

    def get_interval_qtr(lo, hi):
        return (hi - lo) / 4

    def is_my_time_slack(now, dct):
        prev_t, _, _ = get_prev_time_and_state(now, dct)
        next_t, _, _ = get_next_time_and_state(now, dct)
        if prev_t is None or next_t is None:
            return False
        q = get_interval_qtr(prev_t, next_t)
        return not ((now > prev_t + q) and (now < next_t - q))

    def what_is_flow_direction(prev_state):
        return "Ebb" if prev_state == "H" else "Flood"

    def get_flow_state(now, dct):
        if is_my_time_slack(now, dct):
            return "Slack"
        prev_t, prev_state, _ = get_prev_time_and_state(now, dct)
        if prev_state is None:
            return "Slack"
        return what_is_flow_direction(prev_state)

    # ---------- outputs ----------
    flow_state_beg = get_flow_state(sesh_start_datetime, tide_time_dict)
    flow_state_end = get_flow_state(sesh_end_time, tide_time_dict)
    prev_peak_time, prev_peak_state, prev_peak_ht = get_prev_time_and_state(time, tide_time_dict)
    next_peak_time, next_peak_state, next_peak_ht = get_next_time_and_state(time, tide_time_dict)

    return (flow_state_beg, flow_state_end, prev_peak_time, prev_peak_state, next_peak_time, next_peak_state)
