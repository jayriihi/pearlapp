import requests
import pandas as pd
from datetime import datetime, timedelta
import json
from scipy.signal import argrelextrema
import numpy as np
import pytz

# Global thresholds
thresholds = [0.118, 0.176, 0.204, 0.228, 0.268]
thresholds.sort()

# Global timezone set
bermuda_tz = pytz.timezone('Atlantic/Bermuda')

# Flow strength classifier
def classify_flow_strength(s):
    abs_s = abs(s)
    if abs_s < thresholds[0]:
        return "very weak"
    elif abs_s < thresholds[1]:
        return "weak"
    elif abs_s < thresholds[2]:
        return "moderate"
    elif abs_s < thresholds[3]:
        return "strong"
    elif abs_s < thresholds[4]:
        return "very strong"
    else:
        return "extreme"

def fetch_hilo_tide_predictions(station_id, start_date, end_date):
    """Fetch high and low tide predictions."""
    params = {
        "station": station_id,
        "begin_date": start_date.strftime("%Y%m%d"),
        "end_date": end_date.strftime("%Y%m%d"),
        "product": "predictions",
        "datum": "MLLW",
        "interval": "hilo",
        "units": "metric",
        "time_zone": "gmt",
        "format": "json",
    }
    response = requests.get("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter", params=params)
    data = response.json()
    hilo_predictions = pd.DataFrame(data["predictions"])
    hilo_predictions['t'] = pd.to_datetime(hilo_predictions['t'], errors='coerce')  # ⬅️ make sure it's datetime
    hilo_predictions['t'] = hilo_predictions['t'].dt.tz_localize('UTC').dt.tz_convert('Atlantic/Bermuda')

    hilo_predictions['v'] = pd.to_numeric(hilo_predictions['v'])
    return hilo_predictions

def get_detailed_tide_predictions(station_id, start_date, end_date):
    """Fetch detailed tide predictions at 15-minute intervals."""
    params = {
        "station": station_id,
        "begin_date": start_date.strftime("%Y%m%d"),
        "end_date": end_date.strftime("%Y%m%d"),
        "product": "predictions",
        "datum": "MLLW",
        "interval": "15",  # Consider changing to "5" for finer detail if needed
        "units": "metric",
        "time_zone": "gmt",
        "format": "json",
    }
    response = requests.get("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter", params=params)
    data = response.json()
    detailed_predictions = pd.DataFrame(data["predictions"])
    detailed_predictions['t'] = pd.to_datetime(detailed_predictions['t'], errors='coerce')
    detailed_predictions['t'] = detailed_predictions['t'].dt.tz_localize('UTC').dt.tz_convert('Atlantic/Bermuda')

    detailed_predictions['v'] = pd.to_numeric(detailed_predictions['v'])
    return detailed_predictions

def assign_normalized_tide_positions(df):
    """
    Adds 'normalized_in_tide', 'flow_id', and 'flow_strength' columns to the DataFrame.
    Each tide segment (between highs/lows) is given:
      - a normalized position (0 at start, 1 at end)
      - a flow_id to group by
      - a strength label based on the max absolute slope in that tide
    """
    df['v'] = df['v'].astype(float)
    df = df.sort_values('t')

    # Detect turning points (highs and lows)
    v_array = df['v'].values
    max_idx = argrelextrema(v_array, np.greater)[0]
    min_idx = argrelextrema(v_array, np.less)[0]
    turn_idx = np.sort(np.concatenate([max_idx, min_idx]))

    # Initialize new columns
    df['normalized_in_tide'] = np.nan
    df['flow_id'] = np.nan

    # Tag each tide segment
    for i in range(len(turn_idx) - 1):
        start_idx = turn_idx[i]
        end_idx = turn_idx[i + 1]
        if end_idx > start_idx:
            segment_indices = df.index[start_idx:end_idx + 1]
            df.loc[segment_indices, 'normalized_in_tide'] = np.linspace(0, 1, len(segment_indices))
            df.loc[segment_indices, 'flow_id'] = i  # integer flow ID

    # Convert flow_id to integer (optional but helpful)
    df['flow_id'] = df['flow_id'].astype('Int64')

    '''def classify_flow_strength(s):
        abs_s = abs(s)
        if abs_s < thresholds[0]:
            return "very weak"
        elif abs_s < thresholds[1]:
            return "weak"
        elif abs_s < thresholds[2]:
            return "moderate"
        elif abs_s < thresholds[3]:
            return "strong"
        else:
            return "very strong"'''

    # Classify each segment by its max absolute slope
    flow_strengths = df.groupby('flow_id')['slope'].agg(lambda s: classify_flow_strength(s.abs().max()))
    df['flow_strength'] = df['flow_id'].map(flow_strengths)

    return df


def calculate_intermediate_times(hilo_predictions):
    """Calculate six evenly spaced times between each high and low tide."""
    intermediate_times = []

    for i in range(len(hilo_predictions) - 1):
        start_time = hilo_predictions.iloc[i]['t']
        end_time = hilo_predictions.iloc[i + 1]['t']

        # Safety check (you can log or assert here if needed)
        assert start_time.tzinfo is not None and end_time.tzinfo is not None, "Timestamps must be tz-aware"

        interval_duration = (end_time - start_time) / 7

        for j in range(1, 7):
            intermediate_time = start_time + interval_duration * j
            intermediate_times.append(intermediate_time)

    return intermediate_times





def find_forecast_at_times(detailed_predictions, times):
    """Find the closest forecast tide height for each specified time."""
    forecast_tides = []
    for time in times:
        closest_prediction = detailed_predictions.iloc[(detailed_predictions['t'] - time).abs().argsort()[:1]]
        forecast_tides.append(closest_prediction.iloc[0]['v'])
    return forecast_tides

def get_dual_tide_plot_json(station_id, buffered_start, buffered_end, start_date, end_date, fixedMaxY=0.35):
    hilo_predictions = fetch_hilo_tide_predictions(station_id, start_date, end_date)
    detailed_predictions = get_detailed_tide_predictions(station_id, start_date, end_date)

    # Flow delta between tide turning points
    intermediate_times = calculate_intermediate_times(hilo_predictions)
    forecast_tides = find_forecast_at_times(detailed_predictions, intermediate_times)
    differences = [forecast_tides[i + 1] - forecast_tides[i] for i in range(len(forecast_tides) - 1)]

    flow_data_json = json.dumps([
        {"time": intermediate_times[i].isoformat(), "difference": differences[i]}
        for i in range(len(differences))
    ])

    hilo_data_json = json.dumps([
        {"time": t.astimezone(bermuda_tz).isoformat(), "height": v}
        for t, v in zip(hilo_predictions['t'], hilo_predictions['v'])
    ])

    # 1. Slope calculation
    df = detailed_predictions.copy()
    df['slope'] = df['v'].diff() / (15 * 60) * 3600  # m/hr
    df = df.dropna()
    df = assign_normalized_tide_positions(df)
    df = df.dropna(subset=['normalized_in_tide', 'slope'])


    # Ensure comparison datetimes are timezone-aware
    start_date = bermuda_tz.localize(start_date) if start_date.tzinfo is None else start_date.astimezone(bermuda_tz)
    end_date = bermuda_tz.localize(end_date) if end_date.tzinfo is None else end_date.astimezone(bermuda_tz)


    # Trim to visible time window **before** generating slope/tide chart data
    df = df[(df['t'] >= start_date) & (df['t'] <= end_date)]
    detailed_predictions = detailed_predictions[
        (detailed_predictions['t'] >= start_date) & (detailed_predictions['t'] <= end_date)
    ]

    # Interpolate + scale tide height to slope timestamps
    slope_times = df['t']
    min_h = detailed_predictions['v'].min()
    max_h = detailed_predictions['v'].max()
    flow_range = fixedMaxY

    height_interp = []
    for t in slope_times:
        idx = (detailed_predictions['t'] - t).abs().argsort().iloc[0]
        matched_height = detailed_predictions['v'].iloc[idx]
        scaled_height = ((matched_height - min_h) / (max_h - min_h) * 2 - 1) * flow_range
        height_interp.append({
            "time": t.isoformat(),
            "height": scaled_height
        })

    height_data_json = json.dumps(height_interp)

    # Classify strength
    df['strength'] = df['slope'].apply(classify_flow_strength)
    thresholds_json = json.dumps(thresholds)
    max_slope_json = json.dumps(abs(df['slope']).max())
    # Just before json.dumps...
    '''
    print("Remaining NaNs in slope JSON?", df[['t', 'slope', 'normalized_in_tide']].isna().sum())
    print("Sample row with NaN (if any):", df[df.isna().any(axis=1)].head())'''


    slope_data_json = json.dumps([
        {
            "time": t.astimezone(bermuda_tz).isoformat(),
            "slope": s,
            "strength": classify_flow_strength(s),
            "normalized_in_tide": n
        }
        for t, s, n in zip(df['t'], df['slope'], df['normalized_in_tide'])
    ])

    # Optional print check
    print("Thresholds (sorted):", thresholds)
    print("Sample slope classifications:")
    for s in df['slope'].head(10):
        print(f"{s:.3f} → {classify_flow_strength(s)}")

    return flow_data_json, hilo_data_json, height_data_json, slope_data_json, thresholds_json, max_slope_json




def calculate_tide_slope(detailed_predictions):
    # Calculate slope (delta height / delta time in seconds)
    detailed_predictions = detailed_predictions.copy()
    detailed_predictions['slope'] = detailed_predictions['v'].diff() / (15 * 60)  # height change per second
    # Optional: convert to m/hr or m/15-min for interpretability
    detailed_predictions['slope'] *= 3600  # Convert to meters/hour
    return detailed_predictions[['t', 'slope']]

def get_dual_tide_plot_with_slope_json(station_id, start_date, end_date):
    hilo_predictions = fetch_hilo_tide_predictions(station_id, start_date, end_date)
    detailed_predictions = get_detailed_tide_predictions(station_id, start_date, end_date)
    tide_slope = calculate_tide_slope(detailed_predictions)

    # Chart-ready format
    slope_data = [{"time": t.astimezone(bermuda_tz).isoformat(), "slope": s} for t, s in zip(tide_slope['t'], tide_slope['slope'])]
    height_data = [{"time": t.astimezone(bermuda_tz).isoformat(), "height": v} for t, v in zip(detailed_predictions['t'], detailed_predictions['v'])]
    hilo_data = [{"time": t.astimezone(bermuda_tz).isoformat(), "height": v} for t, v in zip(hilo_predictions['t'], hilo_predictions['v'])]

    return json.dumps(slope_data), json.dumps(height_data), json.dumps(hilo_data)


def get_tidal_flow_differences_json(station_id, start_date, end_date):
    # Fetch high and low tide predictions
    hilo_predictions = fetch_hilo_tide_predictions(station_id, start_date, end_date)
    
    # Calculate intermediate times between high and low tides
    intermediate_times = calculate_intermediate_times(hilo_predictions)
    
    # Fetch detailed tide predictions for the specified period
    detailed_predictions = get_detailed_tide_predictions(station_id, start_date, end_date)
    
    # Find forecast tide heights at intermediate times
    forecast_tides = find_forecast_at_times(detailed_predictions, intermediate_times)
    
    # Calculate differences between successive forecast tides for analysis
    differences = [forecast_tides[i + 1] - forecast_tides[i] for i in range(len(forecast_tides) - 1)]
    
    # Convert intermediate_times to ISO format strings within flow_data preparation
    flow_data = [{"time": intermediate_times[i].isoformat(), "difference": differences[i]} for i in range(len(differences))]
    
    # Convert the hilo_predictions to a suitable format for JSON conversion
    hilo_data = [{"time": t.astimezone(bermuda_tz).isoformat(), "height": v} for t, v in zip(hilo_predictions['t'], hilo_predictions['v'])]
    
    # Separate JSON strings for flow data and hilo data
    flow_data_json = json.dumps(flow_data)
    hilo_data_json = json.dumps(hilo_data)
    
    #print(flow_data_json, hilo_data_json)
    return flow_data_json, hilo_data_json

# Example usage
station_id = 2695540  # Bermuda, St George's
start_date = datetime.now() - timedelta(days=1)
end_date = datetime.now()
flow_data_json, hilo_data_json = get_tidal_flow_differences_json(station_id, start_date, end_date)

# Depending on how you handle the response in Flask, you might send these JSON strings directly
# or encapsulate them in a response object if needed.




