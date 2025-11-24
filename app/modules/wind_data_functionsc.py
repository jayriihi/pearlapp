import pandas as pd
import datetime as dt
from datetime import timedelta, datetime
import pytz
from collections import Counter

# Define timezones globally
bda_tz = pytz.timezone("Atlantic/Bermuda")
uk_tz = pytz.timezone("Europe/London")

# ---- data source config ----
SHEET_PRIMARY = "Pearl"
SHEET_FALLBACK = "pred_cresc"   # keep as a manual backup option
ACTIVE_SHEET = SHEET_PRIMARY    # change this line to swap sources


def get_active_sheet():
    """
    Single source of truth for which sheet all wind calcs should use.
    For now: no auto-fallback; just set ACTIVE_SHEET above.
    """
    return ACTIVE_SHEET


def is_stale_wind(series, window=5, threshold=3, decimals=1):
    """
    Kept around for future automation if you want to detect 'flatlined'
    wind series. Currently unused.
    """
    if not series or len(series) < window:
        return False
    tail = [round(float(x), decimals) for x in series[-window:] if x is not None]
    if len(tail) < window:
        return False
    return Counter(tail).most_common(1)[0][1] >= threshold


def _dir_delta(a, b):
    d = (b - a + 360) % 360
    return d - 360 if d > 180 else d


def get_avg_wind_dir(wind_dir_series):
    """
    Compute an average wind direction, handling wrap-around near north.
    """
    if (wind_dir_series > 330).any() or (wind_dir_series < 30).any():
        low_test = wind_dir_series.where(wind_dir_series < 180)
        rollovers = low_test + 360
        hi_test = wind_dir_series.where(wind_dir_series > 180)
        all360_test = rollovers.fillna(0) + hi_test.fillna(0)
        avg_n_wind_dir = all360_test.mean()
        avg_n_wind_dir = round(avg_n_wind_dir)

        if avg_n_wind_dir > 360:
            avg_n_wind_dir = avg_n_wind_dir - 360

        return avg_n_wind_dir
    else:
        nn_avg_wind_dir = wind_dir_series.mean()
        nn_avg_wind_dir = round(nn_avg_wind_dir, 0)
        return nn_avg_wind_dir


def get_wind_speed_data(sesh):
    """
    Given a session DataFrame (wind_spd, wind_max, wind_dir),
    return avg, max, min speed and avg direction.
    """
    avg_wind_spd = sesh["wind_spd"].mean()
    avg_wind_spd = round(avg_wind_spd, 1)

    wind_max = sesh["wind_max"].max()
    wind_min = sesh["wind_spd"].min()

    avg_wind_dir = int(round(get_avg_wind_dir(sesh["wind_dir"])))

    return avg_wind_spd, wind_max, wind_min, avg_wind_dir


def format_date_time(datetimelocal_str, duration_str):
    """
    Convert a HTML datetime-local string + duration into:
    start/end strings in BDA time plus some display helpers.
    """
    sesh_start_datetime_naive = datetime.strptime(datetimelocal_str, "%Y-%m-%dT%H:%M")
    sesh_start_datetime = bda_tz.localize(sesh_start_datetime_naive)

    sesh_start_date_str = sesh_start_datetime.strftime("%d %b")
    sesh_start_time_str = sesh_start_datetime.strftime("%-I:%M %p")

    duration_split = duration_str.split(":")
    h = int(duration_split[0])
    m = int(duration_split[1])

    sesh_duration = timedelta(hours=h, minutes=m)
    sesh_end_time_bda = sesh_start_datetime + sesh_duration

    string_start_time = sesh_start_datetime.strftime("%Y-%m-%d %H:%M")
    string_end_time = sesh_end_time_bda.strftime("%Y-%m-%d %H:%M")

    return string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str


def fetch_pred_cres_data(string_start_time=None, string_end_time=None, sheet_name=None):
    """
    Fetch summary stats + wind speed series for a time window from the
    configured sheet. If sheet_name is given, it overrides ACTIVE_SHEET.
    """
    if sheet_name is None:
        sheet_name = get_active_sheet()

    if string_start_time is None or string_end_time is None:
        now_utc = datetime.now(pytz.utc)
        now_bda = now_utc.astimezone(bda_tz)
        one_hour_ago_bda = now_bda - timedelta(hours=1)
        string_start_time = one_hour_ago_bda.strftime("%Y-%m-%d %H:%M")
        string_end_time = now_bda.strftime("%Y-%m-%d %H:%M")

    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    num_rows = 2016
    gsheet_url = (
        f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq"
        f"?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"
    )

    try:
        df = pd.read_csv(
            gsheet_url,
            skiprows=3,
            names=["Date/Time", "wind_spd", "wind_max", "wind_dir"],
        )
    except Exception as e:
        print(f"Error fetching {sheet_name} data: {e}")
        return None, None, None, None, [], []

    df["Date/Time"] = pd.to_datetime(df["Date/Time"], errors="coerce")
    df = df.dropna(subset=["Date/Time"]).set_index("Date/Time").sort_index()

    start_time_dt = pd.to_datetime(string_start_time)
    end_time_dt = pd.to_datetime(string_end_time)

    sesh = df[
        (df.index >= start_time_dt - pd.Timedelta(minutes=5))
        & (df.index <= end_time_dt + pd.Timedelta(minutes=5))
    ].copy()

    if sesh.empty:
        print(f"No data available for {sheet_name} in {string_start_time} → {string_end_time}")
        return None, None, None, None, [], []

    avg_wind_spd, wind_max, wind_min, avg_wind_dir = get_wind_speed_data(sesh)
    labels = [t.strftime("%H:%M") for t in sesh.index]
    series = sesh["wind_spd"].tolist()
    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series


def get_sesh_wind(datetimelocal_str, duration_str):
    """
    Main API used by the session card.
    """
    (
        string_start_time,
        string_end_time,
        h,
        m,
        sesh_start_date_str,
        sesh_start_time_str,
    ) = format_date_time(datetimelocal_str, duration_str)

    avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series = fetch_pred_cres_data(
        string_start_time, string_end_time
    )

    if any(x is None for x in [avg_wind_spd, wind_max, wind_min, avg_wind_dir]) or not series:
        return (
            string_start_time,
            string_end_time,
            h,
            m,
            sesh_start_date_str,
            sesh_start_time_str,
            None,
            None,
            None,
            None,
            [],
            [],
        )

    return (
        string_start_time,
        string_end_time,
        h,
        m,
        sesh_start_date_str,
        sesh_start_time_str,
        avg_wind_spd,
        wind_max,
        wind_min,
        avg_wind_dir,
        labels,
        series,
    )


def get_timezone_now():
    """
    Get current time in Bermuda, via UTC → UK → BDA to match legacy behavior.
    """
    now_utc = datetime.now(pytz.utc)
    now = now_utc.astimezone(uk_tz)  # Current time in UK timezone
    now_bda = now.astimezone(bda_tz)  # Convert to Bermuda timezone
    return now_bda


def get_window_strings(hours):
    """
    Helper: return start/end strings for a trailing window in Bermuda time.
    """
    now_bda = get_timezone_now()
    start_bda = now_bda - timedelta(hours=hours)
    start = start_bda.strftime("%Y-%m-%d %H:%M")
    end = now_bda.strftime("%Y-%m-%d %H:%M")
    return start, end


def _pearl_quik(hours):
    """
    Shared helper for 1/3/8hr cards.

    Returns:
      avg_wind_spd, wind_max, wind_min,
      avg_wind_dir, cur_wind_dir,
      cur_wind_spd,
      labels, series
    """
    start, end = get_window_strings(hours)
    sheet = get_active_sheet()

    # Use the same window + sheet as everything else
    sesh = fetch_sheet_window_df(start, end, sheet_name=sheet)

    if sesh.empty:
        print(f"[_pearl_quik] empty slice for {hours}h, {start} → {end}, sheet={sheet}")
        return None, None, None, None, None, None, [], []

    # Reuse existing averaging logic
    avg_wind_spd, wind_max, wind_min, avg_wind_dir = get_wind_speed_data(sesh)

    # Current direction & speed = last valid row in this window
    cur_wind_dir = float(sesh["wind_dir"].iloc[-1])
    cur_wind_spd = float(sesh["wind_spd"].iloc[-1])

    labels = [t.strftime("%H:%M") for t in sesh.index]
    series = sesh["wind_spd"].tolist()

    return (
        avg_wind_spd,
        wind_max,
        wind_min,
        avg_wind_dir,
        cur_wind_dir,
        cur_wind_spd,
        labels,
        series,
    )


def pearl_1hr_quik():
    return _pearl_quik(1)


def pearl_3hr_quik():
    return _pearl_quik(3)


def pearl_8hr_quik():
    return _pearl_quik(8)




def fetch_sheet_window_df(string_start_time=None, string_end_time=None, sheet_name=None):
    """
    Return a time-sliced DataFrame with index=datetime and columns:
    wind_spd, wind_max, wind_dir. Uses the active sheet by default.
    """
    if sheet_name is None:
        sheet_name = get_active_sheet()

    if string_start_time is None or string_end_time is None:
        now_utc = datetime.now(pytz.utc)
        now_bda = now_utc.astimezone(bda_tz)
        one_hour_ago_bda = now_bda - timedelta(hours=1)
        string_start_time = one_hour_ago_bda.strftime("%Y-%m-%d %H:%M")
        string_end_time = now_bda.strftime("%Y-%m-%d %H:%M")

    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    num_rows = 2016
    url = (
        f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq"
        f"?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"
    )

    df = pd.read_csv(url, skiprows=3, names=["Date/Time", "wind_spd", "wind_max", "wind_dir"])
    df["Date/Time"] = pd.to_datetime(df["Date/Time"], errors="coerce")
    df = df.dropna(subset=["Date/Time"]).set_index("Date/Time").sort_index()

    start_dt = pd.to_datetime(string_start_time)
    end_dt = pd.to_datetime(string_end_time)
    sesh = df[
        (df.index >= start_dt - pd.Timedelta(minutes=5))
        & (df.index <= end_dt + pd.Timedelta(minutes=5))
    ].copy()
    return sesh.sort_index()


def wind_dir_3hours():
    """
    Returns (labels, wind_dirs) for the vertical 3-hr direction history chart.
    Uses the same sheet + window as the 3-hr speed card.
    """
    start, end = get_window_strings(3)
    sheet = get_active_sheet()
    print(f"[wind_dir_3hours] window BDA: {start} → {end}, sheet={sheet}")

    df = fetch_sheet_window_df(start, end, sheet_name=sheet).sort_index()
    print(f"[wind_dir_3hours] fetched rows: {len(df)}")
    if df.empty:
        print("[wind_dir_3hours] empty slice")
        return [], []

    df = df[pd.to_numeric(df["wind_dir"], errors="coerce").notna()].copy()
    df["wind_dir"] = df["wind_dir"].astype(float)

    labels = [
        ts.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        for ts in df.index.to_pydatetime()
    ]
    wind_dirs = df["wind_dir"].tolist()

    return labels, wind_dirs
