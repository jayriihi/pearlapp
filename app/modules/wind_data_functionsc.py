import pandas as pd
import datetime as dt
from datetime import timedelta, datetime
import pytz
from collections import Counter
import requests
import io
from app.modules.logging_utils import log

# Shared Google Sheet config
GSHEET_ID = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
NUM_ROWS = 2016
# Pearl tab gid copied from sheet URL (?gid=1815185817)
SHEET_GIDS = {"Pearl": 1815185817}  # known gid mapping; others fall back to gviz


class NoWindDataError(Exception):
    """Raised when no wind data is available for the requested period."""
    pass

# Define timezones globally
bda_tz = pytz.timezone("Atlantic/Bermuda")
uk_tz = pytz.timezone("Europe/London")

# ---- station mapping ----
STATIONS = {
    "pearl": {"label": "Porch", "sheet": "Pearl"},
    "crescent": {"label": "Crescent", "sheet": "Sheet1"},
    "nmb": {"label": "NMB", "sheet": "NMB_data"},
    "model": {"label": "Cresc. model", "sheet": "pred_cresc"},
}
DEFAULT_STATION_KEY = "pearl"

def resolve_station_key(station_key):
    if not station_key:
        return DEFAULT_STATION_KEY
    key = str(station_key).lower()
    return key if key in STATIONS else DEFAULT_STATION_KEY

def get_station_sheet(station_key=None):
    key = resolve_station_key(station_key)
    return STATIONS[key]["sheet"]


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
    configured sheet. If sheet_name is given, it overrides the default station.
    """
    if sheet_name is None:
        sheet_name = get_station_sheet(DEFAULT_STATION_KEY)

    if string_start_time is None or string_end_time is None:
        now_utc = datetime.now(pytz.utc)
        now_bda = now_utc.astimezone(bda_tz)
        one_hour_ago_bda = now_bda - timedelta(hours=1)
        string_start_time = one_hour_ago_bda.strftime("%Y-%m-%d %H:%M")
        string_end_time = now_bda.strftime("%Y-%m-%d %H:%M")

    try:
        df = fetch_sheet_csv(sheet_name)
    except Exception as e:
        log(f"Error fetching {sheet_name} data: {e}")
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
        log(f"No data available for {sheet_name} in {string_start_time} → {string_end_time}")
        return None, None, None, None, [], []

    avg_wind_spd, wind_max, wind_min, avg_wind_dir = get_wind_speed_data(sesh)
    labels = [t.strftime("%H:%M") for t in sesh.index]
    series = sesh["wind_spd"].tolist()
    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series


def get_sesh_wind(datetimelocal_str, duration_str, station_key=None):
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

    sheet_name = get_station_sheet(station_key)
    avg_wind_spd, wind_max, wind_min, avg_wind_dir, labels, series = fetch_pred_cres_data(
        string_start_time,
        string_end_time,
        sheet_name=sheet_name,
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


def _pearl_quik(hours, station_key=None):
    """
    Shared helper for 1/3/8hr cards.

    Returns:
      avg_wind_spd, wind_max, wind_min,
      avg_wind_dir, cur_wind_dir,
      cur_wind_spd,
      labels, series
    """
    start, end = get_window_strings(hours)
    sheet = get_station_sheet(station_key)

    # Use the same window + sheet as everything else
    sesh = fetch_sheet_window_df(start, end, sheet_name=sheet)

    if sesh is None or sesh.empty:
        log(f"[_pearl_quik] empty slice for {hours}h, {start} → {end}, sheet={sheet}")
        raise NoWindDataError("No wind data available for the requested period")

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


def pearl_1hr_quik(station_key=None):
    return _pearl_quik(1, station_key=station_key)


def pearl_3hr_quik(station_key=None):
    return _pearl_quik(3, station_key=station_key)


def pearl_8hr_quik(station_key=None):
    return _pearl_quik(8, station_key=station_key)


def get_wind_data(hours, station_key=None):
    return _pearl_quik(hours, station_key=station_key)


def _gviz_url(sheet_name, num_rows=NUM_ROWS):
    cache_bust = int(datetime.now(pytz.utc).timestamp() * 1000)
    return (
        f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}&cb={cache_bust}"
    )


def _export_url(sheet_name, num_rows=NUM_ROWS):
    gid = SHEET_GIDS.get(sheet_name)
    if gid is None:
        return None
    cache_bust = int(datetime.now(pytz.utc).timestamp() * 1000)
    # export uses gid instead of sheet name
    return f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/export?format=csv&gid={gid}&range=A1:D{num_rows}&cb={cache_bust}"


def fetch_sheet_csv(sheet_name, num_rows=NUM_ROWS):
    """
    Fetch the sheet via HTTP with explicit no-cache headers and return a DataFrame.
    Tries gviz first, then export (gid-based) if the first pull looks stale.
    """
    headers = {
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "pearlapp-fetch",
    }

    urls = [("gviz", _gviz_url(sheet_name, num_rows))]
    export_url = _export_url(sheet_name, num_rows)
    if export_url:
        urls.append(("export", export_url))

    last_exc = None
    best_df = None
    best_latest = None
    best_source = None
    for source, url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            df = pd.read_csv(
                io.StringIO(resp.text),
                skiprows=3,
                names=["Date/Time", "wind_spd", "wind_max", "wind_dir"],
            )
            latest_ts = pd.to_datetime(df["Date/Time"], errors="coerce").max()
            # Normalize latest_ts to BDA tz so timedelta math is safe
            if latest_ts is not None and latest_ts.tzinfo is None:
                latest_ts = bda_tz.localize(latest_ts)
            now_bda = get_timezone_now()

            # Track the best (freshest) pull seen so far
            if latest_ts is not None and (best_latest is None or latest_ts > best_latest):
                best_latest = latest_ts
                best_df = df
                best_source = source

            # If the latest row is within 6 minutes of "now", trust this fetch.
            if latest_ts is not None and (now_bda - latest_ts) <= timedelta(minutes=6):
                return df
            # Otherwise try the next URL
        except Exception as e:
            last_exc = e
            log(f"[sheet fetch error] source={source} {e}")
            continue

    # If we got a usable (though possibly stale) df, return the freshest one
    if best_df is not None:
        return best_df

    # If all attempts failed, raise the last exception
    if last_exc:
        raise last_exc
    raise RuntimeError("Sheet fetch failed without exception")


def fetch_sheet_window_df(string_start_time=None, string_end_time=None, sheet_name=None):
    """
    Return a time-sliced DataFrame with index=datetime and columns:
    wind_spd, wind_max, wind_dir. Uses the default station by default.
    """
    if sheet_name is None:
        sheet_name = get_station_sheet(DEFAULT_STATION_KEY)

    if string_start_time is None or string_end_time is None:
        now_utc = datetime.now(pytz.utc)
        now_bda = now_utc.astimezone(bda_tz)
        one_hour_ago_bda = now_bda - timedelta(hours=1)
        string_start_time = one_hour_ago_bda.strftime("%Y-%m-%d %H:%M")
        string_end_time = now_bda.strftime("%Y-%m-%d %H:%M")

    df = fetch_sheet_csv(sheet_name)
    df["Date/Time"] = pd.to_datetime(df["Date/Time"], errors="coerce")
    df = df.dropna(subset=["Date/Time"]).set_index("Date/Time").sort_index()

    start_dt = pd.to_datetime(string_start_time)
    end_dt = pd.to_datetime(string_end_time)

    # If sheet has newer rows than our computed end, slide the end forward
    latest_ts = df.index.max() if not df.empty else None
    if latest_ts is not None and latest_ts > end_dt:
        end_dt = latest_ts

    sesh = df[
        (df.index >= start_dt - pd.Timedelta(minutes=5))
        & (df.index <= end_dt + pd.Timedelta(minutes=5))
    ].copy()

    return sesh.sort_index()


def wind_dir_3hours(station_key=None):
    """
    Returns (labels, wind_dirs) for the vertical 3-hr direction history chart.
    Uses the same sheet + window as the 3-hr speed card.
    """
    start, end = get_window_strings(3)
    sheet = get_station_sheet(station_key)
    log(f"[wind_dir_3hours] window BDA: {start} → {end}, sheet={sheet}")

    df = fetch_sheet_window_df(start, end, sheet_name=sheet).sort_index()
    log(f"[wind_dir_3hours] fetched rows: {len(df)}")
    if df.empty:
        log("[wind_dir_3hours] empty slice")
        return [], []

    df = df[pd.to_numeric(df["wind_dir"], errors="coerce").notna()].copy()
    df["wind_dir"] = df["wind_dir"].astype(float)

    labels = [
        ts.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        for ts in df.index.to_pydatetime()
    ]
    wind_dirs = df["wind_dir"].tolist()

    return labels, wind_dirs
