import requests
from datetime import datetime, timedelta

#this function is a simple request to get the current dewpoint for Bermuda from the openweather api results are printed in the terminal

'''def get_dew_point(api_key):
    # Coordinates for Bermuda
    lat, lon = "32.3078", "-64.7505"
    
    # Corrected API URL to use One Call API
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={api_key}&units=imperial"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # The 'current' key now should exist with the correct endpoint
        dew_point = data['current']['dew_point']
        print(f"Current dew point in Bermuda: {dew_point}°f")
    else:
        print("Failed to retrieve data:", response.status_code, response.text)

# Use your actual OpenWeatherMap API key
api_key = 'd6972ca477a08858bd2dbcb4bce19c55'  # Replace YOUR_API_KEY with your actual API key
get_dew_point(api_key)

#this function is a request to get the forecast dewpoints for Bermuda for the next 3 days from the openweather api results are printed in the terminal'''

def get_forecast_dew_point(api_key):
    # Coordinates for Bermuda
    lat, lon = "32.3078", "-64.7505"
    
    # One Call API URL for forecast data including dew point
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,daily,alerts&appid={api_key}&units=imperial"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Print forecast dew points for the next 3 days
        print("Forecast Dew Points for the next 3 days:")
        for hourly_data in data['hourly'][:72]:  # 24 hours * 3 days
            time = hourly_data['dt']
            dew_point = hourly_data['dew_point']
            print(f"Time: {time}, Dew Point: {dew_point}°F")
    else:
        print("Failed to retrieve data:", response.status_code, response.text)

api_key = 'd6972ca477a08858bd2dbcb4bce19c55'  # Replace YOUR_API_KEY with your actual API key
get_forecast_dew_point(api_key)







