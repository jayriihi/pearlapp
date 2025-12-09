import requests
from datetime import datetime, timedelta
from flask import render_template, request, session, jsonify, redirect, url_for
from app import app
from app.modules import wind_data_functionsc, tide_now, sesh_tide, tidal_data_retrieval
from app.modules.wind_data_functionsc import NoWindDataError
from app.modules.tide_now import NoTideDataError


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
        print(f"[tide] {e}")
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


def get_wind_dir_history():
    """
    3h wind direction history, JSON-friendly.
    Returns (labels, dirs) or ([], []) on error.
    """
    try:
        wd_labels_raw, wd_dirs_raw = wind_data_functionsc.wind_dir_3hours()
        wd_labels = [str(t) for t in wd_labels_raw]                 # ISO strings are fine
        wd_dirs = [float(d) for d in wd_dirs_raw if d is not None]  # 0–360 floats
        return wd_labels, wd_dirs
    except Exception as e:
        print(f"[wind_dir_vert] {e}")
        return [], []


def fetch_winds(hours: int):
    """
    Fetch wind data for the given window length (hours).
    Returns (labels, values, avg, maxv, minv, avg_dir, cur_dir, cur_spd).
    """
    if hours == 1:
        fn = wind_data_functionsc.pearl_1hr_quik
    elif hours == 3:
        fn = wind_data_functionsc.pearl_3hr_quik
    elif hours == 8:
        fn = wind_data_functionsc.pearl_8hr_quik
    else:
        fn = wind_data_functionsc.pearl_1hr_quik

    try:
        avg, maxv, minv, avg_dir, cur_dir, cur_spd, labels, series = fn()
    except NoWindDataError:
        raise
    except Exception as e:
        print(f"[fetch_winds] unexpected error: {e}")
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


@app.route("/winds/<int:hours>")
def winds(hours: int):
    wind_available = True
    wind_error = None

    labels = []
    values = []
    avg = maxv = minv = avg_dir = cur_dir = cur_spd = None

    try:
        labels, values, avg, maxv, minv, avg_dir, cur_dir, cur_spd = fetch_winds(hours)
    except NoWindDataError as e:
        wind_available = False
        wind_error = str(e)
    except Exception as e:
        print(f"[winds] unexpected wind error: {e}")
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
        print(f"[winds] unexpected tide error: {e}")
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
    wd_labels, wd_dirs = get_wind_dir_history()

    scalar_mean = None
    if hours == 3 and wd_dirs:
        scalar_mean = float(sum(wd_dirs) / len(wd_dirs))
        print(
            f"[winds] 3h vert-panel scalar mean = {scalar_mean}"
        )
        print(
            f"[winds] 3h vert-panel count = {len(wd_dirs)}, "
            f"min={min(wd_dirs)}, max={max(wd_dirs)}"
        )

    return render_template(
        "wind_tide_dir.html",
        hours=hours,
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

        return wind()

    return render_template("windput.html")


@app.route("/wind")
def wind():
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
        session["sessiondatetime"], session["duration"]
    )

    # Round and convert to integers for display
    avg_wind_spd = round(avg_wind_spd, 1)
    wind_max = int(round(wind_max, 0))
    wind_min = int(round(wind_min, 0))
    avg_wind_dir = int(round(avg_wind_dir, 0))

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
        print(f"[graph_temp] {e}")
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


@app.route("/error")
def error():
    return render_template("error.html")


@app.route("/error_2")
def error_2():
    # Fetch modeled data from pred_cres
    (
        avg_wind_spd,
        wind_max,
        wind_min,
        avg_wind_dir,
        date_time_index_series_str,
        wind_spd_series,
    ) = wind_data_functionsc.fetch_pred_cres_data()

    # Round and convert to integers for display
    avg_wind_spd = round(avg_wind_spd, 1)
    wind_max = int(round(wind_max, 0))
    wind_min = int(round(wind_min, 0))
    avg_wind_dir = int(round(avg_wind_dir, 0))

    # Fetch tide data
    (
        flow_state_beg,
        prev_peak_time,
        prev_peak_state,
        prev_peak_ht,
        next_peak_time,
        next_peak_state,
        next_peak_ht,
    ) = tide_now.get_tide_data_for_now()

    tide_state_full = "Low" if next_peak_state == "L" else "High"
    next_peak_time_formatted = _fmt_hhmm(next_peak_time)

    return render_template(
        "error_2.html",
        labels=date_time_index_series_str,
        values=wind_spd_series,
        past_hour_avg_wind_spd=avg_wind_spd,
        past_hour_avg_wind_min=wind_min,
        past_hour_avg_wind_max=wind_max,
        avg_wind_dir=avg_wind_dir,
        flow_state_beg=flow_state_beg,
        prev_peak_time=prev_peak_time,
        prev_peak_state=prev_peak_state,
        prev_peak_ht=prev_peak_ht,
        next_peak_time=next_peak_time_formatted,
        next_peak_state=tide_state_full,
        next_peak_ht=next_peak_ht,
        is_modeled=True,
    )


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
        print(f"[data] unexpected tide error: {e}")
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
    fixedMaxY = 0.35

    (
        flow_data_json,
        hilo_data_json,
        height_data_json,
        slope_data_json,
        thresholds_json,
        max_slope_json,
    ) = tidal_data_retrieval.get_dual_tide_plot_json(
        station_id, start_date, end_date, fixedMaxY
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
    api_key = "d6972ca477a08858bd2dbcb4bce19c55"  # Use your real API key
    lat, lon = "32.3078", "-64.7505"
    url = (
        "https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}"
        "&exclude=minutely,daily,alerts"
        f"&appid={api_key}&units=imperial"
    )
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        hourly_forecasts = [
            {
                "time": datetime.fromtimestamp(hour["dt"]).strftime("%Y-%m-%d %H:%M"),
                "dew_point": hour["dew_point"],
                "temp": hour.get("temp"),
                "humidity": hour.get("humidity"),
            }
            for hour in data["hourly"][:72]
        ]

        return render_template("dewpointplus.html", forecasts=hourly_forecasts)
    else:
        print(f"Failed to retrieve data with status code {response.status_code}")
        return (
            f"Failed to retrieve data with status code {response.status_code}",
            400,
        )
