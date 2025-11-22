
'''import pandas as pd
from datetime import datetime, timedelta

#this section generates the data for the wind_dir.html graph
def fetch_wind_data():
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    num_rows = 2016  # Number of rows to fetch, assuming each row is an hourly record of the last 288 hours
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    # Read specific columns (assuming columns are fixed and known)
    cols = ['Date/Time', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3']
    df = pd.read_csv(gsheet_url, usecols=cols, skiprows=2)

    # Rename columns immediately after loading
    df.rename(columns={
        'Date/Time': 'date_time',
        'Unnamed: 1': 'wind_spd',
        'Unnamed: 2': 'wind_max',
        'Unnamed: 3': 'wind_dir',
    }, inplace=True)

    # Convert 'date_time' to datetime
    df['date_time'] = pd.to_datetime(df['date_time'])

    # Filter for the last three hours
    now = datetime.now()
    three_hours_ago = now - timedelta(hours=3,minutes=5)# added 5 minutes to timedelta to ensure getting the reading from 1hour ago
    df = df[(df['date_time'] >= three_hours_ago) & (df['date_time'] <= now)]

    # Sort by date_time in ascending order to display from earliest to latest
    df.sort_values('date_time', ascending=True, inplace=True)
    #print(df)
    return df

def wind_dir_data(df):
    wind_data = df['wind_dir']
    #print(wind_data)
    return wind_data

# Main execution
df = fetch_wind_data()  # Call to fetch data
wind_data = wind_dir_data(df)  # Pass the fetched data to the function that needs it
#print(df)

#this section generates the wind_dir change for a one hour period
def fetch_wind_data_one_hour():
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    num_rows = 2016  # Number of rows to fetch, assuming each row is an hourly record of the last 288 hours
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    cols = ['Date/Time', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3']
    df = pd.read_csv(gsheet_url, usecols=cols, skiprows=2)
    df.rename(columns={
        'Date/Time': 'date_time',
        'Unnamed: 1': 'wind_spd',
        'Unnamed: 2': 'wind_max',
        'Unnamed: 3': 'wind_dir',
    }, inplace=True)
    df['date_time'] = pd.to_datetime(df['date_time'])

    # Adjust the timedelta for one hour
    now = datetime.now()
    print(now)
    one_hour_ago = now - timedelta(hours=1, minutes=5)
    print(one_hour_ago)
    df = df[(df['date_time'] >= one_hour_ago) & (df['date_time'] <= now)]
    df.sort_values('date_time', ascending=True, inplace=True)
    #print(df)
    return df

def wind_direction_change(df):
    if df.empty:
        return "No data available"

    df.sort_index(inplace=True)
    initial_dir = df['wind_dir'].iloc[0]
    final_dir = df['wind_dir'].iloc[-1]

    difference = (initial_dir - final_dir + 360) % 360
    if difference > 180:
        difference -= 360

    return difference

df_one_hour = fetch_wind_data_one_hour()
change_last_one_hour = wind_direction_change(df_one_hour)

#print(f"Change in wind direction in the last hour: {change_last_one_hour} degrees")

#this section generates the wind_dir change for a six hour period
def fetch_wind_data_six_hours():
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    num_rows = 2016  # Number of rows to fetch, assuming each row is an hourly record of the last 288 hours
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    cols = ['Date/Time', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3']
    df = pd.read_csv(gsheet_url, usecols=cols, skiprows=2)
    df.rename(columns={
        'Date/Time': 'date_time',
        'Unnamed: 1': 'wind_spd',
        'Unnamed: 2': 'wind_max',
        'Unnamed: 3': 'wind_dir',
    }, inplace=True)
    df['date_time'] = pd.to_datetime(df['date_time'])

    # Adjust the timedelta for six hours
    now = datetime.now()
    six_hours_ago = now - timedelta(hours=6, minutes=5)
    df = df[(df['date_time'] >= six_hours_ago) & (df['date_time'] <= now)]
    df.sort_values('date_time', ascending=True, inplace=True)
    print(df)
    return df

def wind_direction_change(df):
    if df.empty:
        return "No data available"

    df.sort_index(inplace=True)
    initial_dir = df['wind_dir'].iloc[4]
    final_dir = df['wind_dir'].iloc[0]

    difference = (initial_dir - final_dir + 360) % 360
    if difference > 180:
        difference -= 360

    return difference

# Fetch data for the last six hours and calculate the wind direction change
df_six_hours = fetch_wind_data_six_hours()
change_last_six_hours = wind_direction_change(df_six_hours)

print(f"Change in wind direction in the last six hours: {change_last_six_hours} degrees")'''

import pandas as pd
from datetime import datetime, timedelta

def fetch_wind_data():
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    num_rows = 2016
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    cols = ['Date/Time', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3']
    df = pd.read_csv(gsheet_url, usecols=cols, skiprows=2)

    df.rename(columns={
        'Date/Time': 'date_time',
        'Unnamed: 1': 'wind_spd',
        'Unnamed: 2': 'wind_max',
        'Unnamed: 3': 'wind_dir',
    }, inplace=True)

    df['date_time'] = pd.to_datetime(df['date_time'])
    now = datetime.now()
    six_hours_ago = now - timedelta(hours=6, minutes=5)  # Getting data from 6 hours ago
    df = df[(df['date_time'] >= six_hours_ago) & (df['date_time'] <= now)]
    df.sort_values('date_time', ascending=True, inplace=True)
    print("DataFrame after fetching and sorting:")
    print(df)
    return df

def wind_direction_change(df):
    if df.empty:
        return "No data available"

    # Earliest data point (last in the sorted DataFrame)
    initial_dir = df['wind_dir'].iloc[-4]
    # Most recent data point (first in the sorted DataFrame)
    final_dir = df['wind_dir'].iloc[-1]

    print(f"Initial direction (earliest): {initial_dir}")
    print(f"Final direction (most recent): {final_dir}")

    difference = (final_dir - initial_dir + 360) % 360
    if difference > 180:
        difference = 360 - difference  # Adjust to shortest path
        difference *= -1  # Make counterclockwise differences negative

    return difference


# Main execution
df = fetch_wind_data()
if not df.empty:
    direction_change = wind_direction_change(df)
    print(f"Change in wind direction: {direction_change} degrees")
else:
    print("No wind data available for calculation.")











