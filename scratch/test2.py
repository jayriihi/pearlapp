import pandas as pd
import pytz
import datetime as dt
from datetime import datetime, timedelta



# Main function for fetching and filtering wind data
def fetch_wind_data():
    # Set the timezone to Bermuda
    bermuda_tz = pytz.timezone('Atlantic/Bermuda')

    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    num_rows = 2016  # Assuming each row is an hourly record for the last 288 hours
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    df = pd.read_csv(gsheet_url, skiprows=2)

    df.rename(columns={
        df.columns[0]: 'date_time',
        df.columns[1]: 'wind_spd',
        df.columns[2]: 'wind_max',
        df.columns[3]: 'wind_dir',
    }, inplace=True)

    # Parse the date_time column without specifying a format
    df['date_time'] = pd.to_datetime(df['date_time'], errors='coerce')
    df.set_index('date_time', inplace=True)

    # Ensure the DataFrame is sorted by the datetime index
    df = df.sort_index()

    # Define session start time as 'now' and a duration of 3 hours (example scenario)
    now = datetime.now(bermuda_tz)
    now1 = now-timedelta(hours=.5)

    string_now1 = dt.datetime.strftime(now1,"%Y-%m-%d %H:%M")
    string_now = dt.datetime.strftime(now,"%Y-%m-%d %H:%M")

    print(f"Session Start Time: {string_now1}")
    print(f"Session End Time: {string_now}")

    # Check the earliest and latest datetime in the index
    print(f"Data time range: {df.index.min()} to {df.index.max()}")

    # Use .loc to filter the DataFrame based on the string representation of the time
    df_filtered = df.loc[string_now1:string_now]

    # Return filtered DataFrame
    return df_filtered

# Fetch and display the filtered wind data
df = fetch_wind_data()

if not df.empty:
    print(df)
else:
    print("No data available for the specified time range.")
