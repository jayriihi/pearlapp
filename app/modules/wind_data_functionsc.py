# breaking out get_sesh_wind() into logical separate functions

import pandas as pd
import datetime as dt
from datetime import timedelta, datetime
import pytz
from collections import Counter

# Define timezones globally
bda_tz = pytz.timezone('Atlantic/Bermuda')
uk_tz = pytz.timezone('Europe/London')

def is_stale_wind(series, window=5, threshold=3, decimals=1):
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
        
    if  (wind_dir_series > 330 ).any() or (wind_dir_series < 30).any():
        
        low_test = wind_dir_series.where(wind_dir_series<180)
        rollovers = (low_test+360)
        hi_test = wind_dir_series.where(wind_dir_series>180)
        all360_test = rollovers.fillna(0) + hi_test.fillna(0)
        avg_n_wind_dir = all360_test.mean()
        avg_n_wind_dir = round(avg_n_wind_dir)

        if avg_n_wind_dir >360:
            avg_n_wind_dir = (avg_n_wind_dir-360)

        #print("The average wind direction for this session is ", avg_n_wind_dir)
        return avg_n_wind_dir  
    else:
        nn_avg_wind_dir = wind_dir_series.mean()
        nn_avg_wind_dir = round(nn_avg_wind_dir, 0) 
        #print("The average wind direction for this session is  ", nn_avg_wind_dir)
        return nn_avg_wind_dir

def get_wind_speed_data(sesh):
    # get avg wind speed during session time and round to one decimal place
    avg_wind_spd = sesh["wind_spd"].mean()
    avg_wind_spd = round(avg_wind_spd, 1) 
    #print("The avg wind speed for this session is ",avg_wind_spd)
 
    #get max wind speed during session time
    wind_max=sesh['wind_max'].max()
    #print("The max wind speed for this session is ",wind_max)

    #get min wind speed during session time
    wind_min=sesh['wind_spd'].min()
    #print("The min wind speed for this session is ",wind_min)

    avg_wind_dir = get_avg_wind_dir(sesh['wind_dir'])
    avg_wind_dir = round(avg_wind_dir, 0)
  
    return (avg_wind_spd, wind_max, wind_min,avg_wind_dir)

def format_date_time(datetimelocal_str, duration_str):
    # Parse datetime-local string and set it as a timezone-aware datetime in Bermuda time
    sesh_start_datetime_naive = datetime.strptime(datetimelocal_str, '%Y-%m-%dT%H:%M')
    sesh_start_datetime = bda_tz.localize(sesh_start_datetime_naive)

    # Convert session start time to the server's timezone (UK)
    #sesh_start_uk = sesh_start_datetime.astimezone(uk_tz)

    # Convert to date and start time strings using Bermuda time
    sesh_start_date_str = sesh_start_datetime.strftime('%d %b')
    sesh_start_time_str = sesh_start_datetime.strftime('%-I:%M %p')

    # Break duration string into hours and minutes
    duration_split = duration_str.split(':')
    h = int(duration_split[0])
    m = int(duration_split[1])

    # Add duration to start time to get end time
    sesh_duration = timedelta(hours=h, minutes=m)
    sesh_end_time_bda = sesh_start_datetime + sesh_duration

    # Format time strings for start and end times
    string_start_time = sesh_start_datetime.strftime("%Y-%m-%d %H:%M")
    string_end_time = sesh_end_time_bda.strftime("%Y-%m-%d %H:%M")

    return string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str




def fetch_pred_cres_data(string_start_time=None, string_end_time=None, sheet_name="pred_cresc"):
    if string_start_time is None or string_end_time is None:
        now_utc = datetime.now(pytz.utc)
        now_bda = now_utc.astimezone(bda_tz)
        one_hour_ago_bda = now_bda - timedelta(hours=1)
        string_start_time = one_hour_ago_bda.strftime("%Y-%m-%d %H:%M")
        string_end_time   = now_bda.strftime("%Y-%m-%d %H:%M")

    gsheetid  = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    num_rows  = 2016
    gsheet_url = (
        f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq"
        f"?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"
    )

    try:
        df = pd.read_csv(gsheet_url, skiprows=3, names=["Date/Time", "wind_spd", "wind_max", "wind_dir"])
    except Exception as e:
        print(f"Error fetching {sheet_name} data: {e}")
        return None, None, None, None, [], []

    df.set_index('Date/Time', inplace=True)
    df.rename(columns={'Date/Time':'date_time'}, inplace=True)  
    df.index = pd.to_datetime(df.index)

    start_time_dt = pd.to_datetime(string_start_time)
    end_time_dt   = pd.to_datetime(string_end_time)

    sesh = df[(df.index >= start_time_dt - pd.Timedelta(minutes=5)) &
              (df.index <= end_time_dt   + pd.Timedelta(minutes=5))].sort_index()

    if sesh.empty:
        print(f"No data available for {sheet_name} in {string_start_time} → {string_end_time}")
        return None, None, None, None, [], []

    avg_wind_spd, wind_max, wind_min, avg_wind_dir = get_wind_speed_data(sesh)
    labels = [t.strftime("%H:%M") for t in sesh.index]
    series = sesh["wind_spd"].tolist()
    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series

# ---- toggle (top of wind_data_functionsc.py is fine) ----
USE_PRED_ONLY = False   # set False when Pearl is healthy again


def fetch_auto_pearl_then_pred(start=None, end=None):
    import pandas as pd

    def as_naive(ts):
        if ts is None:
            return None
        t = pd.to_datetime(ts, errors="coerce")
        if pd.isna(t):
            return None
        return t.tz_localize(None) if getattr(t, "tzinfo", None) else t

    now = pd.Timestamp.utcnow()
    end = as_naive(end or now)
    start = as_naive(start or (end - pd.Timedelta(hours=8)))

    def ok(res):
        return (
            isinstance(res, tuple) and len(res) == 6 and
            res[0] is not None and res[5] and len(res[5]) > 0
        )

    if USE_PRED_ONLY:
        res = fetch_pred_cres_data(start, end, sheet_name="Pearl")
        return (res if ok(res) else (None, None, None, None, [], [])), "Pearl"

    res = fetch_pred_cres_data(start, end, sheet_name="Pearl")
    if ok(res) and not is_stale_wind(res[5]):
        return res, "Pearl"

    res2 = fetch_pred_cres_data(start, end, sheet_name="pred_cresc")
    return (res2 if ok(res2) else (None, None, None, None, [], [])), "pred_cresc"


def get_sesh_wind(datetimelocal_str, duration_str):
    string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str = \
        format_date_time(datetimelocal_str, duration_str)

    (avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series), _source = \
        fetch_auto_pearl_then_pred(string_start_time, string_end_time)

    if any(x is None for x in [avg_wind_spd, wind_max, wind_min, avg_wind_dir]) or not series:
        return (string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str,
                None, None, None, None, [], [])

    return (string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str,
            avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series)


def get_timezone_now():
    # Get current UTC time and convert to server (UK) and Bermuda times
    now_utc = datetime.now(pytz.utc)
    now = now_utc.astimezone(uk_tz)  # Current time in UK timezone
    now_bda = now.astimezone(bda_tz)  # Convert to Bermuda timezone
    return now_bda

def _pearl_quik(hours):
    now_bda = get_timezone_now()
    start_bda = now_bda - timedelta(hours=hours)

    start = start_bda.strftime("%Y-%m-%d %H:%M")
    end   = now_bda.strftime("%Y-%m-%d %H:%M")

    (avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series), _ = (
        fetch_auto_pearl_then_pred(start, end)
    )
    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series

def pearl_1hr_quik():
    return _pearl_quik(1)

def pearl_3hr_quik():
    return _pearl_quik(3)

def pearl_8hr_quik():
    return _pearl_quik(8)

# Direction specific functions
def fetch_sheet_window_df(string_start_time=None, string_end_time=None, sheet_name="pred_cresc"):
    """
    Return a time-sliced DataFrame with index=datetime and columns:
    wind_spd, wind_max, wind_dir. Default uses pred_cresc; pass sheet_name="Pearl" later if needed.
    """
    if string_start_time is None or string_end_time is None:
        now_utc = datetime.now(pytz.utc)
        now_bda = now_utc.astimezone(bda_tz)
        one_hour_ago_bda = now_bda - timedelta(hours=1)
        string_start_time = one_hour_ago_bda.strftime("%Y-%m-%d %H:%M")
        string_end_time   = now_bda.strftime("%Y-%m-%d %H:%M")

    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    num_rows = 2016
    url = (f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq"
           f"?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}")

    df = pd.read_csv(url, skiprows=3, names=["Date/Time", "wind_spd", "wind_max", "wind_dir"])
    df["Date/Time"] = pd.to_datetime(df["Date/Time"], errors="coerce")
    df = df.dropna(subset=["Date/Time"]).set_index("Date/Time").sort_index()

    start_dt = pd.to_datetime(string_start_time)
    end_dt   = pd.to_datetime(string_end_time)
    sesh = df[(df.index >= start_dt - pd.Timedelta(minutes=5)) &
              (df.index <= end_dt   + pd.Timedelta(minutes=5))].copy()
    return sesh.sort_index()

# 3 hour df for wind_dir.html / wind_dir_vert.html chart
def wind_dir_3hours():
    # Bermuda window
    now_bda = get_timezone_now()
    start = (now_bda - timedelta(hours=3, minutes=5)).strftime("%Y-%m-%d %H:%M")
    end   = now_bda.strftime("%Y-%m-%d %H:%M")

    print(f"[wind_dir_3hours] window BDA: {start} → {end}")

    df = fetch_sheet_window_df(start, end, sheet_name="pred_cresc").sort_index()
    print(f"[wind_dir_3hours] fetched rows: {len(df)}")
    if df.empty:
        print("[wind_dir_3hours] empty slice")
        return [], []

    # keep only rows with a numeric wind_dir
    df = df[pd.to_numeric(df["wind_dir"], errors="coerce").notna()].copy()
    df["wind_dir"] = df["wind_dir"].astype(float)

    # timestamps → strict ISO in UTC (…Z) so Chart.js parses reliably
    labels = [
        ts.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        for ts in df.index.to_pydatetime()
    ]
    wind_dirs = df["wind_dir"].tolist()

    return labels, wind_dirs

    # Force numeric ONCE and build a mask so labels & data stay aligned
    wd = pd.to_numeric(df["wind_dir"], errors="coerce")
    mask = wd.notna()
    kept = int(mask.sum())
    print(f"[wind_dir_3hours] numeric wind_dir kept: {kept} / {len(df)}")

    if kept == 0:
        print("[wind_dir_3hours] all wind_dir are non-numeric; tail:\n", df.tail(3))
        return [], []

    timestamps = [t.strftime("%H:%M") for t in df.index[mask]]
    wind_directions = wd[mask].astype(float).tolist()

    print(f"[wind_dir_3hours] emitting {len(wind_directions)} pts "
          f"{timestamps[0]} → {timestamps[-1]}  "
          f"min/max {min(wind_directions):.1f}/{max(wind_directions):.1f}")

    return timestamps, wind_directions



# The functions below are for the wind dir clocks
def wind_direction_change_1hour():
    now = datetime.now()
    start = (now - timedelta(hours=1, minutes=15)).strftime("%Y-%m-%d %H:%M")
    end   = now.strftime("%Y-%m-%d %H:%M")
    df = fetch_sheet_window_df(start, end, sheet_name="pred_cresc")
    if df.empty or len(df) < 2:
        return "No data available"
    initial_dir = float(df["wind_dir"].iloc[0])
    final_dir   = float(df["wind_dir"].iloc[-1])
    return _dir_delta(initial_dir, final_dir)

def wind_direction_change_3hour():
    now = datetime.now()
    start = (now - timedelta(hours=3, minutes=30)).strftime("%Y-%m-%d %H:%M")
    end   = now.strftime("%Y-%m-%d %H:%M")
    df = fetch_sheet_window_df(start, end, sheet_name="pred_cresc")
    if df.empty or len(df) < 2:
        return "No data available"
    initial_dir = float(df["wind_dir"].iloc[0])
    final_dir   = float(df["wind_dir"].iloc[-1])
    return _dir_delta(initial_dir, final_dir)

def wind_direction_change_6hour():
    now = datetime.now()
    start = (now - timedelta(hours=6, minutes=30)).strftime("%Y-%m-%d %H:%M")
    end   = now.strftime("%Y-%m-%d %H:%M")
    df = fetch_sheet_window_df(start, end, sheet_name="pred_cresc")
    if df.empty or len(df) < 2:
        return "No data available"
    initial_dir = float(df["wind_dir"].iloc[0])
    final_dir   = float(df["wind_dir"].iloc[-1])
    return _dir_delta(initial_dir, final_dir)









