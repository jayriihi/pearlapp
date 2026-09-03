import os
import hmac
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import render_template, request, session, jsonify, redirect, url_for, send_from_directory
from app import app
from app.modules import wind_data_functionsc, tide_now, sesh_tide, tidal_data_retrieval
from app.modules.wind_data_functionsc import NoWindDataError
from app.modules.tide_now import NoTideDataError
from app.modules.logging_utils import log

OPENWEATHER_TIMEOUT = 10
BERMUDA_TZ = ZoneInfo("Atlantic/Bermuda")

# Shared by the current-conditions card and compact legend. Chart.js receives
# this same configuration from the template for its display-only bands.
DEW_POINT_COMFORT_BANDS = (
    {"minimum": 80, "maximum": None, "range": "80+", "description": "Indoors, AC on", "color": "#3f454c", "chart_color": "#eef0f2", "text_color": "#ffffff"},
    {"minimum": 75, "maximum": 80, "range": "75–80", "description": "Extremely uncomfortable", "color": "#7a2731", "text_color": "#ffffff"},
    {"minimum": 70, "maximum": 75, "range": "70–74", "description": "Very uncomfortable", "color": "#d9554d", "text_color": "#212529"},
    {"minimum": 65, "maximum": 70, "range": "65–69", "description": "Moderately uncomfortable", "color": "#e8a34c", "text_color": "#212529"},
    {"minimum": 60, "maximum": 65, "range": "60–64", "description": "Slightly uncomfortable", "color": "#eee28a", "text_color": "#212529"},
    {"minimum": 55, "maximum": 60, "range": "55–59", "description": "Comfortable", "color": "#75ad87", "text_color": "#212529"},
    {"minimum": 50, "maximum": 55, "range": "50–54", "description": "Very comfortable", "color": "#7398ca", "text_color": "#ffffff"},
    {"minimum": -999, "maximum": 50, "range": "0–50", "description": "Dry, Superhuman", "color": "#eef0f2", "text_color": "#212529"},
)


def _dew_point_comfort_band(dew_point):
    """Return the shared category definition for a dew-point reading."""
    return next(band for band in DEW_POINT_COMFORT_BANDS if dew_point >= band["minimum"])


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "icons"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


# ------------------------
# Helpers
# ------------------------

def _as_dt(x):
    """Coerce pandas.Timestamp to datetime for strftime."""
    try:
        import pandas as pd
        if isinstance(x, pd.Timestamp):
            return x.to_pydatetime()
    except Exception:
        pass
    return x


def _fmt_hhmm(x):
    """Format a datetime-like value as HH:MM, or a fallback dash."""
    x = _as_dt(x)
    try:
        return x.strftime("%H:%M")
    except Exception:
        return "–"


def _has_session_values(*keys):
    return all(session.get(key) for key in keys)


API_CLIENT_ENV_VARS = {
    "sailflow": "SAILFLOW_API_KEY",
    "bws": "BWS_API_KEY",
    "cameron": "CAMERON_KEY",
}


def _client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def _forbidden_api_response(client, reason):
    log(f"[api_auth] denied client={client!r} ip={_client_ip()} reason={reason}")
    return jsonify({"error": "forbidden"}), 403


def _format_api_timestamp(dt_value):
    dt_value = _as_dt(dt_value)
    if dt_value is None:
        return None

    if dt_value.tzinfo is None:
        dt_value = wind_data_functionsc.bda_tz.localize(dt_value)

    dt_utc = dt_value.astimezone(timezone.utc).replace(second=0, microsecond=0)
    return dt_utc.strftime("%Y-%m-%dT%H:%MZ")


def _latest_pearl_payload():
    station_key = "pearl"
    _, values, avg, maxv, minv, avg_dir, cur_dir, cur_spd = fetch_winds(
        1,
        station_key=station_key,
    )
    if not values:
        raise NoWindDataError("No wind data available for the requested period")

    start, end = wind_data_functionsc.get_window_strings(1)
    df = wind_data_functionsc.fetch_sheet_window_df(
        start,
        end,
        sheet_name=wind_data_functionsc.get_station_sheet(station_key),
    ).sort_index()

    if df.empty:
        raise NoWindDataError("No wind data available for the requested period")

    latest_timestamp = df.index.max()
    latest_timestamp = _format_api_timestamp(latest_timestamp)

    return {
        "station": "pearl",
        "timestamp": latest_timestamp,
        "wind_avg_kts": round(float(avg), 1) if avg is not None else None,
        "wind_gust_kts": round(float(maxv), 1) if maxv is not None else None,
        "wind_min_kts": round(float(minv), 1) if minv is not None else None,
        "wind_dir_deg": int(round(cur_dir if cur_dir is not None else avg_dir)) if (cur_dir is not None or avg_dir is not None) else None,
        "wind_current_kts": round(float(cur_spd), 1) if cur_spd is not None else None,
        "status": "ok",
    }


def get_tide_snapshot():
    """
    Fetch tide snapshot for 'now' with safe defaults.
    Returns a dict with:
      tide_ok, tide_error_msg,
      flow_state_beg,
      prev_peak_time_disp, prev_peak_state_disp, prev_peak_ht,
      next_peak_time_disp, next_peak_state_disp, next_peak_ht
    """
    tide_ok = True
    tide_error_msg = None

    try:
        (
            flow_state_beg,
            prev_peak_time,
            prev_peak_state,
            prev_peak_ht,
            next_peak_time,
            next_peak_state,
            next_peak_ht,
        ) = tide_now.get_tide_data_for_now()

        prev_peak_time_disp = _fmt_hhmm(prev_peak_time)
        next_peak_time_disp = _fmt_hhmm(next_peak_time)

        def _state_full(s):
            if s == "H":
                return "High"
            if s == "L":
                return "Low"
            return str(s)

        prev_peak_state_disp = _state_full(prev_peak_state)
        next_peak_state_disp = _state_full(next_peak_state)

    except Exception as e:
        log(f"[tide] {e}")
        tide_ok = False
        tide_error_msg = "Tide data temporarily unavailable."

        flow_state_beg = None
        prev_peak_time_disp = None
        prev_peak_state_disp = None
        prev_peak_ht = None
        next_peak_time_disp = None
        next_peak_state_disp = None
        next_peak_ht = None

    return {
        "tide_ok": tide_ok,
        "tide_error_msg": tide_error_msg,
        "flow_state_beg": flow_state_beg,
        "prev_peak_time_disp": prev_peak_time_disp,
        "prev_peak_state_disp": prev_peak_state_disp,
        "prev_peak_ht": prev_peak_ht,
        "next_peak_time_disp": next_peak_time_disp,
        "next_peak_state_disp": next_peak_state_disp,
        "next_peak_ht": next_peak_ht,
    }


def get_wind_dir_history(station_key=None):
    """
    3h wind direction history, JSON-friendly.
    Returns (labels, dirs) or ([], []) on error.
    """
    try:
        wd_labels_raw, wd_dirs_raw = wind_data_functionsc.wind_dir_3hours(
            station_key=station_key
        )
        wd_labels = [str(t) for t in wd_labels_raw]                 # ISO strings are fine
        wd_dirs = [float(d) for d in wd_dirs_raw if d is not None]  # 0–360 floats
        return wd_labels, wd_dirs
    except Exception as e:
        log(f"[wind_dir_vert] {e}")
        return [], []


def fetch_winds(hours: int, station_key=None):
    """
    Fetch wind data for the given window length (hours).
    Returns (labels, values, avg, maxv, minv, avg_dir, cur_dir, cur_spd).
    """
    try:
        (
            avg,
            maxv,
            minv,
            avg_dir,
            cur_dir,
            cur_spd,
            labels,
            series,
        ) = wind_data_functionsc.get_wind_data(hours, station_key=station_key)
    except NoWindDataError:
        raise
    except Exception as e:
        log(f"[fetch_winds] unexpected error: {e}")
        raise NoWindDataError("Unexpected error retrieving wind data") from e

    if labels is None or series is None or not len(series):
        raise NoWindDataError("No wind data available for the requested period")

    return labels, series, avg, maxv, minv, avg_dir, cur_dir, cur_spd




# ------------------------
# Routes
# ------------------------

@app.route("/")
@app.route("/home")
def homepage():
    # unified wind/tide view, default 1 hour
    return redirect("/winds/1")


@app.route("/api/pearl/latest")
def api_pearl_latest():
    client = (request.args.get("client") or "").strip().lower()
    token = request.args.get("token") or ""

    env_var_name = API_CLIENT_ENV_VARS.get(client)
    if env_var_name is None:
        return _forbidden_api_response(client, "unknown_client")

    expected_token = os.getenv(env_var_name, "")
    if not token or not expected_token or not hmac.compare_digest(token, expected_token):
        return _forbidden_api_response(client, "bad_token")

    try:
        return jsonify(_latest_pearl_payload())
    except NoWindDataError as e:
        log(f"[api_pearl_latest] unavailable client={client!r} ip={_client_ip()} error={e}")
        return jsonify({"error": "data_unavailable", "status": "unavailable"}), 503
    except Exception as e:
        log(f"[api_pearl_latest] unexpected client={client!r} ip={_client_ip()} error={e}")
        return jsonify({"error": "internal_error", "status": "error"}), 500


@app.route("/winds/<int:hours>")
def winds(hours: int):
    raw_station = request.args.get("station")
    station_key = wind_data_functionsc.resolve_station_key(raw_station)
    station_param = raw_station if raw_station in wind_data_functionsc.STATIONS else None
    station_label = wind_data_functionsc.STATIONS[station_key]["label"]
    stations = [
        {"key": key, "label": wind_data_functionsc.STATIONS[key]["label"]}
        for key in ("pearl", "nmb", "model", "crescent")
    ]

    wind_available = True
    wind_error = None

    labels = []
    values = []
    avg = maxv = minv = avg_dir = cur_dir = cur_spd = None

    try:
        labels, values, avg, maxv, minv, avg_dir, cur_dir, cur_spd = fetch_winds(
            hours,
            station_key=station_key,
        )
    except NoWindDataError as e:
        wind_available = False
        wind_error = str(e)
    except Exception as e:
        log(f"[winds] unexpected wind error: {e}")
        wind_available = False
        wind_error = "Unexpected error retrieving wind data"

    # current wind speed: last point in the speed series if available,
    # otherwise fall back to the computed "cur_spd" from fetch_winds
    cur_wind_spd = None
    cur_wind_dir = None
    if wind_available:
        cur_wind_spd = values[-1] if values else None
        if cur_wind_spd is None and cur_spd is not None:
            cur_wind_spd = cur_spd
        if cur_wind_spd is not None:
            cur_wind_spd = round(cur_wind_spd, 1)

        # current wind direction: prefer cur_dir, fall back to avg_dir
        if cur_dir is not None:
            cur_wind_dir = int(round(cur_dir))
        elif avg_dir is not None:
            cur_wind_dir = int(round(avg_dir))

    # tide snapshot
    tide = get_tide_snapshot()

    tide_available = True
    tide_error = None
    tide_labels = []
    tide_values = []

    try:
        tide_labels, tide_values = tide_now.fetch_tide_predictions()
    except NoTideDataError as e:
        tide_available = False
        tide_error = str(e)
    except Exception as e:
        log(f"[winds] unexpected tide error: {e}")
        tide_available = False
        tide_error = "Unexpected error retrieving tide data"

    # Optional test switch to simulate tide outage without waiting for a real one
    simulate_tide_down = request.args.get("simulate_tide_down", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if simulate_tide_down:
        tide_available = False
        tide_error = "Simulated tide outage"
        tide_labels = []
        tide_values = []
        # also suppress the tide summary when simulating an outage
        tide["tide_ok"] = False
        tide["tide_error_msg"] = tide_error
        tide["flow_state_beg"] = None
        tide["prev_peak_time_disp"] = None
        tide["prev_peak_state_disp"] = None
        tide["next_peak_time_disp"] = None
        tide["next_peak_state_disp"] = None

    # 3h wind direction history for the vertical chart
    wd_labels, wd_dirs = get_wind_dir_history(station_key=station_key)

    scalar_mean = None
    if hours == 3 and wd_dirs:
        scalar_mean = float(sum(wd_dirs) / len(wd_dirs))
        log(f"[winds] 3h vert-panel scalar mean = {scalar_mean}")
        log(
            f"[winds] 3h vert-panel count = {len(wd_dirs)}, "
            f"min={min(wd_dirs)}, max={max(wd_dirs)}"
        )

    return render_template(
        "wind_tide_dir.html",
        hours=hours,
        station_key=station_key,
        station_label=station_label,
        station_param=station_param,
        stations=stations,
        labels=labels,
        values=values,
        past_hour_avg_wind_spd=avg,
        past_hour_avg_wind_max=maxv,
        past_hour_avg_wind_min=minv,

        # NEW: current + average for cards
        cur_wind_spd=cur_wind_spd,
        avg_wind_dir=avg_dir,
        cur_wind_dir=cur_wind_dir,

        tide_ok=tide["tide_ok"],
        tide_error_msg=tide["tide_error_msg"],
        flow_state_beg=tide["flow_state_beg"],
        prev_peak_time=tide["prev_peak_time_disp"],
        prev_peak_state=tide["prev_peak_state_disp"],
        next_peak_time=tide["next_peak_time_disp"],
        next_peak_state=tide["next_peak_state_disp"],
        is_modeled=False,   # Pearl real data
        wd_labels=wd_labels,
        wd_dirs=wd_dirs,
        wind_available=wind_available,
        wind_error=wind_error,
        tide_available=tide_available,
        tide_error=tide_error,
        tide_labels=tide_labels,
        tide_values=tide_values,
    )






# legacy links mapped to the unified view
@app.route("/graph_3hr")
def graph_3hr():
    return winds(3)


@app.route("/graph_8hr")
def graph_8hr():
    return winds(8)


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


@app.route("/windput", methods=["POST", "GET"])
def windput():
    pearl_station_key = wind_data_functionsc.DEFAULT_STATION_KEY
    stations = [
        {"key": key, "label": meta["label"]}
        for key, meta in wind_data_functionsc.STATIONS.items()
    ]

    if request.method == "POST":
        dt_raw = request.form.get("sessiondatetime", "").strip()
        dt = _parse_dt(dt_raw)
        if not dt:
            dt = datetime.now()

        session["sessiondatetime"] = dt.strftime("%Y-%m-%dT%H:%M")

        dur_raw = request.form.get("duration", "0:00")
        try:
            h_str, m_str = dur_raw.split(":", 1)
            h, m = int(h_str), int(m_str)
        except Exception:
            h, m = 0, 0
        m = max(0, min(59, m))
        session["duration"] = f"{h}:{m:02d}"
        session["duration_minutes"] = h * 60 + m
        session["station_key"] = wind_data_functionsc.resolve_station_key(
            request.form.get("station")
        )

        return wind()

    return render_template(
        "windput.html",
        station_key=pearl_station_key,
        stations=stations,
    )


@app.route("/wind")
def wind():
    if not _has_session_values("sessiondatetime", "duration"):
        return redirect(url_for("windput"))

    station_key = wind_data_functionsc.resolve_station_key(
        session.get("station_key")
    )
    station_label = wind_data_functionsc.STATIONS[station_key]["label"]

    try:
        (
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
            date_time_index_series_str,
            wind_spd_series,
        ) = wind_data_functionsc.get_sesh_wind(
            session["sessiondatetime"],
            session["duration"],
            station_key=session.get("station_key"),
        )
    except Exception as e:
        log(f"[wind] session wind fetch failed: {e}")
        return render_template(
            "session_error.html",
            message="Session wind data is temporarily unavailable.",
        ), 503

    if any(value is None for value in (avg_wind_spd, wind_max, wind_min, avg_wind_dir)):
        return render_template(
            "session_error.html",
            message="No session data found for the selected range.",
        ), 404

    # Round and convert to integers for display
    avg_wind_spd = round(avg_wind_spd, 1)
    wind_max = int(round(wind_max, 0))
    wind_min = int(round(wind_min, 0))
    avg_wind_dir = int(round(avg_wind_dir, 0))

    try:
        (
            flow_state_beg,
            flow_state_end,
            prev_peak_time,
            prev_peak_state,
            next_peak_time,
            next_peak_state,
        ) = sesh_tide.get_tide_data_for_session(
            session["sessiondatetime"], session["duration"]
        )
    except Exception as e:
        log(f"[wind] session tide fetch failed: {e}")
        flow_state_beg = "Slack"
        flow_state_end = "Slack"
        prev_peak_time = None
        prev_peak_state = None
        next_peak_time = None
        next_peak_state = None

    return render_template(
        "sesh_wind.html",
        value_avg=avg_wind_spd,
        value_max=wind_max,
        value_min=wind_min,
        value_date=sesh_start_date_str,
        value_time=sesh_start_time_str,
        value_hours=h,
        value_minutes=m,
        value_avg_wind_dir=avg_wind_dir,
        station_label=station_label,
        labels=date_time_index_series_str,
        values=wind_spd_series,
        flow_state_beg=flow_state_beg,
        flow_state_end=flow_state_end,
        prev_peak_time=prev_peak_time,
        prev_peak_state=prev_peak_state,
        next_peak_time=next_peak_time,
        next_peak_state=next_peak_state,
    )


@app.route("/graph_temp")
def graph_temp():
    try:
        (
            avg_wind_spd,
            wind_max,
            wind_min,
            avg_wind_dir,
            cur_wind_dir,
            cur_wind_spd,
            date_time_index_series_str,
            wind_spd_series,
        ) = wind_data_functionsc.pearl_1hr_quik()
    except NoWindDataError as e:
        log(f"[graph_temp] {e}")
        avg_wind_spd = wind_max = wind_min = avg_wind_dir = None
        cur_wind_dir = cur_wind_spd = None
        date_time_index_series_str = []
        wind_spd_series = []


    return render_template(
        "graph_temp.html",
        labels=date_time_index_series_str,
        values=wind_spd_series,
        past_hour_avg_wind_spd=avg_wind_spd,
        past_hour_avg_wind_min=wind_min,
        past_hour_avg_wind_max=wind_max,
        avg_wind_dir=avg_wind_dir,
    )



@app.route("/crescent")
def crescent_descr():
    return render_template("crescent_descr.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/upwindsports")
def upwindsports():
    return render_template("upwindsports.html")


@app.route("/tide")
def tide_home():
    return render_template("chart.html")


@app.route("/data")
def data():
    try:
        times, values = tide_now.fetch_tide_predictions()
        return jsonify({"values": values, "times": times})
    except NoTideDataError as e:
        return jsonify({"error": str(e)})
    except Exception as e:
        log(f"[data] unexpected tide error: {e}")
        return jsonify({"error": "No tide data available"})


@app.route("/wind_dir")
def wind_dir():
    timestamps, wind_directions = wind_data_functionsc.wind_dir_3hours()
    return render_template(
        "wind_dir.html",
        labels=timestamps,
        wind_dirs=wind_directions,
    )


@app.route("/wind_dir_vert")
def wind_dir_vert():
    labels, wind_directions = wind_data_functionsc.wind_dir_3hours()
    return render_template(
        "wind_dir_vert.html",
        labels=labels,
        wind_dirs=wind_directions,
    )


@app.route("/tidal_difference")
def tidal_difference():
    today = datetime.now().date()
    start_date = today - timedelta(days=1)
    end_date = today + timedelta(days=1)

    flow_data_json, hilo_data_json = tidal_data_retrieval.get_tidal_flow_differences_json(
        2695540, start_date, end_date
    )

    return render_template(
        "tidal_difference.html",
        flow_data_json=flow_data_json,
        hilo_data_json=hilo_data_json,
    )


@app.route("/dual_tide_plot")
def dual_tide_plot():
    station_id = 2695540
    start_date = datetime.now()
    end_date = datetime.now() + timedelta(days=2)
    buffer = timedelta(hours=1)
    buffered_start = start_date - buffer
    buffered_end = end_date + buffer
    fixedMaxY = 0.35

    (
        flow_data_json,
        hilo_data_json,
        height_data_json,
        slope_data_json,
        thresholds_json,
        max_slope_json,
    ) = tidal_data_retrieval.get_dual_tide_plot_json(
        station_id, buffered_start, buffered_end, start_date, end_date, fixedMaxY
    )

    return render_template(
        "dual_tide_plot.html",
        flow_data_json=flow_data_json,
        hilo_data_json=hilo_data_json,
        height_data_json=height_data_json,
        slope_data_json=slope_data_json,
        thresholds_json=thresholds_json,
        max_slope_json=max_slope_json,
    )


@app.route("/tidal_flow")
def tidal_flow():
    station_id = 2695540
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=3)

    visible_start = datetime.now()
    visible_end = visible_start + timedelta(days=3)

    buffer = timedelta(hours=1)
    buffered_start = start_date - buffer
    buffered_end = end_date + buffer

    fixedMaxY = 0.35

    (
        flow_data_json,
        hilo_data_json,
        height_data_json,
        slope_data_json,
        thresholds_json,
        max_slope_json,
    ) = tidal_data_retrieval.get_dual_tide_plot_json(
        station_id, buffered_start, buffered_end, start_date, end_date, fixedMaxY
    )

    return render_template(
        "tidal_flow.html",
        flow_data_json=flow_data_json,
        hilo_data_json=hilo_data_json,
        height_data_json=height_data_json,
        slope_data_json=slope_data_json,
        thresholds_json=thresholds_json,
        max_slope_json=max_slope_json,
    )


@app.route("/dewpointplus")
def dewpoint():
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        log("[dewpointplus] OPENWEATHER_API_KEY is not set")
        return "Dew point data temporarily unavailable.", 503

    lat, lon = "32.3078", "-64.7505"
    url = (
        "https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}"
        "&exclude=minutely,daily,alerts"
        f"&appid={api_key}&units=imperial"
    )
    try:
        response = requests.get(url, timeout=OPENWEATHER_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        hourly_forecasts = [
            {
                "time": datetime.fromtimestamp(
                    hour["dt"], tz=timezone.utc
                ).astimezone(BERMUDA_TZ).strftime("%Y-%m-%d %H:%M"),
                "dew_point": hour["dew_point"],
                "temp": hour.get("temp"),
                "humidity": hour.get("humidity"),
            }
            for hour in data.get("hourly", [])[:72]
            if "dt" in hour and "dew_point" in hour
        ]
    except (requests.RequestException, ValueError, TypeError, KeyError) as e:
        log(f"[dewpointplus] failed to retrieve forecast: {e}")
        return "Dew point data temporarily unavailable.", 503

    if not hourly_forecasts:
        log("[dewpointplus] no hourly forecast data returned")
        return "Dew point data temporarily unavailable.", 503

    try:
        dew_point = float(current["dew_point"])
        current_conditions = {
            # This independent payload lets a garden station replace the current
            # source later without changing the template or forecast feed.
            "source": "OpenWeather",
            "temperature": float(current["temp"]),
            "humidity": float(current["humidity"]),
            "dew_point": dew_point,
            "updated": datetime.fromtimestamp(current["dt"], tz=timezone.utc)
            .astimezone(BERMUDA_TZ)
            .strftime("%-I:%M %p"),
        }
        current_conditions["comfort"] = _dew_point_comfort_band(dew_point)
    except (KeyError, TypeError, ValueError, OSError, OverflowError):
        # The hourly response is still useful if OpenWeather omits current data.
        current_conditions = None

    return render_template(
        "dewpointplus.html",
        forecasts=hourly_forecasts,
        current_conditions=current_conditions,
        comfort_bands=DEW_POINT_COMFORT_BANDS,
    )
