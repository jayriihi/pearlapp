import os

import requests

OPENWEATHER_TIMEOUT = 10


def get_forecast_dew_point(api_key=None):
    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set")

    lat, lon = "32.3078", "-64.7505"
    url = (
        "https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}"
        "&exclude=minutely,daily,alerts"
        f"&appid={api_key}&units=imperial"
    )

    response = requests.get(url, timeout=OPENWEATHER_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data.get("hourly", [])[:72]


if __name__ == "__main__":
    for hourly_data in get_forecast_dew_point():
        print(
            f"Time: {hourly_data['dt']}, Dew Point: {hourly_data['dew_point']}°F"
        )
