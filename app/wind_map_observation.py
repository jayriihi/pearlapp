"""Small read adapter over the dashboard's authoritative Pearl sheet reader."""
from datetime import datetime, timedelta, timezone
import math
from threading import Lock
import time

import pandas as pd

from app.modules import wind_data_functionsc as wind

POLL_SECONDS = 60  # Published Pearl rows are five minutes apart.
STALE_SECONDS = 360  # Same six-minute freshness window as fetch_sheet_csv.
FUTURE_TOLERANCE_SECONDS = 120


def utc_now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_latest_pearl():
    """One frame, one row: never pair measurements with a second fetch's time."""
    start, end = wind.get_window_strings(1)
    frame = wind.fetch_sheet_window_df(start, end, sheet_name=wind.get_station_sheet("pearl"))
    if frame is None or frame.empty:
        raise wind.NoWindDataError("No published Pearl observation")
    frame = frame.sort_index()
    latest = frame.iloc[-1]
    speed, direction = float(latest["wind_spd"]), float(latest["wind_dir"])
    if not (math.isfinite(speed) and speed >= 0 and math.isfinite(direction) and 0 <= direction <= 360):
        raise wind.NoWindDataError("Invalid latest Pearl measurement")
    observed = pd.Timestamp(frame.index[-1]).to_pydatetime()
    if pd.isna(observed):
        raise wind.NoWindDataError("Missing observation time")
    if observed.tzinfo is None:
        # Sheet timestamps are Bermuda wall time, as in the existing dashboard.
        # Reject ambiguous/nonexistent DST times instead of guessing an age.
        observed = wind.bda_tz.localize(observed, is_dst=None)
    observed = observed.astimezone(timezone.utc)
    if observed > utc_now() + timedelta(seconds=FUTURE_TOLERANCE_SECONDS):
        raise wind.NoWindDataError("Observation time is in the future")
    numeric = frame[["wind_spd", "wind_dir"]].apply(pd.to_numeric, errors="coerce").dropna()
    if wind.is_stale_wind(numeric["wind_spd"].tolist(), numeric["wind_dir"].tolist()):
        raise wind.NoWindDataError("Pearl feed is flatlined")
    return {"station": "pearl", "direction_deg": direction % 360,
            "speed_kts": round(speed, 1), "observed_at": iso(observed)}


class ObservationCache:
    """Per-worker request coalescing; cache age never determines LIVE freshness."""
    def __init__(self):
        self.lock = Lock()
        self.expires = 0
        self.observation = None

    def get(self):
        with self.lock:
            if time.monotonic() >= self.expires:
                try:
                    self.observation = read_latest_pearl()
                except Exception:
                    # Public endpoint does not expose upstream URLs or errors.
                    self.observation = None
                self.expires = time.monotonic() + (POLL_SECONDS if self.observation else 30)
            observation = self.observation
        now = utc_now()
        status = "unavailable"
        if observation:
            observed = datetime.fromisoformat(observation["observed_at"].replace("Z", "+00:00"))
            age = (now - observed).total_seconds()
            if age < -FUTURE_TOLERANCE_SECONDS:
                observation = None
            else:
                status = "stale" if age >= STALE_SECONDS else "live"
        return {"status": status, "observation": observation, "server_time": iso(now),
                "stale_after_seconds": STALE_SECONDS, "poll_interval_seconds": POLL_SECONDS}


observations = ObservationCache()
