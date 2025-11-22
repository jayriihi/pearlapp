# breaking out get_sesh_wind() into logical separate functions

import pandas as pd
import datetime as dt
from datetime import timedelta, datetime


def format_date_time(datetimelocal_str,duration_str):
    #create datetime objecet from datetime-local string from html input
    sesh_start_datetime = dt.datetime.strptime(datetimelocal_str, '%Y-%m-%dT%H:%M')
    #convert to date str and start time str
    sesh_start_date_str = dt.datetime.strftime(sesh_start_datetime, '%d %b')
    sesh_start_time_str = dt.datetime.strftime(sesh_start_datetime, '%-I:%M %p')
    #print (sesh_start_date_str)
    #print (sesh_start_time_str)

    #break the duration str up in to int for hours and munutes
    duration_split = duration_str.split(':')
    #print (duration_split)
    h = int(duration_split[0])
    #print (type(h))
    m = int(duration_split[1])
    #print (m)
    #add duration to start time to get end time
    sesh_duration = timedelta(hours=+(h), minutes=+(m))
    #print ('sesh_duration is', sesh_duration)

    #Fomatting time for sesh df
    sesh_start_datetime + sesh_duration
    sesh_end_time = sesh_start_datetime + sesh_duration
    #print('sesh_end_time is', sesh_end_time)
      
    string_start_time = dt.datetime.strftime(sesh_start_datetime,"%Y-%m-%d %H:%M")
    #print(string_start_time)
    string_end_time = dt.datetime.strftime(sesh_end_time,"%Y-%m-%d %H:%M")
    #print(string_end_time)

    return string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str

def data_frame_set(string_start_time, string_end_time):
    # Crescent gsheet (primary source)
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    num_rows = 2016
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    try:
        # Attempt to fetch data from Crescent
        df = pd.read_csv(gsheet_url, skiprows=2)
    except Exception as e:
        print(f"Error fetching Crescent data: {e}")
        return None, [], []  # Return empty values if fetching fails

    # Process Crescent data
    df.set_index('Date/Time', inplace=True)
    df.rename(columns={
        'Date/Time': 'date_time',
        'Unnamed: 1': 'wind_spd',
        'Unnamed: 2': 'wind_max',
        'Unnamed: 3': 'wind_dir'
    }, inplace=True)
    df.index = pd.to_datetime(df.index)

    # Extract session data for the requested time range
    sesh = df.sort_index().loc[string_start_time:string_end_time]

    if sesh.empty:
        print(f"No data available for the time range {string_start_time} to {string_end_time}")
        return None, None, None, None, [], []  # Handle empty session

        # Calculate statistics for the session
    avg_wind_spd, wind_max, wind_min, avg_wind_dir = get_wind_speed_data(sesh)

    # Process session data
    date_time_index_series = list(sesh.index)
    date_time_index_series_str = [t.strftime("%H:%M") for t in date_time_index_series]
    wind_spd_series = list(sesh["wind_spd"])

    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series


def fetch_pred_cres_data(string_start_time=None, string_end_time=None):
    if string_start_time is None or string_end_time is None:
        # Get beginning and ending times for the past hour and format to string
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        string_start_time = dt.datetime.strftime(one_hour_ago, "%Y-%m-%d %H:%M")
        string_end_time = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")

    # Fetch data specifically from pred_cres
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"  # Same ID, different sheet
    sheet_name = "pred_cresc"  # Specify pred_cres as the sheet name
    num_rows = 2016
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{gsheetid}/gviz/tq?tqx=out:csv&sheet={sheet_name}&range=A1:D{num_rows}"

    try:
        # Fetch data from pred_cres
        df = pd.read_csv(gsheet_url, skiprows=2)
    except Exception as e:
        print(f"Error fetching pred_cres data: {e}")
        return None, None, None, None, [], []

    # Process the fetched data
    df.set_index('Date/Time', inplace=True)
    df.rename(columns={
        'Date/Time': 'date_time',
        'Unnamed: 1': 'wind_spd',
        'Unnamed: 2': 'wind_max',
        'Unnamed: 3': 'wind_dir'
    }, inplace=True)
    df.index = pd.to_datetime(df.index)

    # Extract the session data using string_start_time and string_end_time
    sesh = df.sort_index().loc[string_start_time:string_end_time]

    if sesh.empty:
        print(f"No data available for the time range {string_start_time} to {string_end_time}")
        return None, None, None, None, [], []  # Handle empty session

    # Check if session data is empty
    if sesh.empty:
        print(f"No data available in pred_cres for the time range {string_start_time} to {string_end_time}.")
        return None, None, None, None, [], []

    # Calculate statistics for the session
    avg_wind_spd, wind_max, wind_min, avg_wind_dir = get_wind_speed_data(sesh)

    # Prepare series for graphing
    date_time_index_series = list(sesh.index)
    date_time_index_series_str = [t.strftime("%H:%M") for t in date_time_index_series]
    wind_spd_series = list(sesh["wind_spd"])

    #return sesh, date_time_index_series_str, wind_spd_series
    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series

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

    
def get_sesh_wind(datetimelocal_str,duration_str):
    string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str = format_date_time(datetimelocal_str,duration_str)

    avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series = data_frame_set(string_start_time, string_end_time)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    #avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
    #print(date_time_of_wind_speed,avg_wind_speeds_for_sesh)
    #date_time_index_series_str, wind_spd_series = get_sesh_series_for_graphs(sesh)
    #print(date_time_index_series, wind_spd_series)
    return string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str,avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series

    #print(get_sesh_wind('2024-05-11T13:10','2:0'))


def pearl_1hr_quik():
    # Get beginning and ending times for the past hour and format to string
    now = datetime.now()
    now1 = now - timedelta(hours=1)

    string_now1 = dt.datetime.strftime(now1, "%Y-%m-%d %H:%M")
    string_now = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")

    #avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)

    # Unpack all 7 returned values from data_frame_set
    avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series = data_frame_set(string_now1, string_now)

    # Return the same values
    return avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series

    #print(get_sesh_wind('2024-12-18T13:10','2,0'))  
    #pearl_1hr_quik()

def pearl_3hr_quik():
    now = datetime.now()
    now3 = now-timedelta(hours=3)

    string_now3 = dt.datetime.strftime(now3,"%Y-%m-%d %H:%M")
    string_now = dt.datetime.strftime(now,"%Y-%m-%d %H:%M")

    sesh, avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series = data_frame_set(string_now3, string_now)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    #avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
    #print(date_time_of_wind_speed,avg_wind_speeds_for_sesh)
    #date_time_index_series_str, wind_spd_series = get_sesh_series_for_graphs(sesh)
    #print(date_time_index_series, wind_spd_series)
    return avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series
    #print(get_sesh_wind('2022-05-11T13:10','2,0')) 
#pearl_1hr_quik()


def pearl_8hr_quik():
    now = datetime.now()
    now8 = now-timedelta(hours=8)

    string_now8 = dt.datetime.strftime(now8,"%Y-%m-%d %H:%M")
    string_now = dt.datetime.strftime(now,"%Y-%m-%d %H:%M")

    avg_wind_spd, wind_max, wind_min, avg_wind_dir, date_time_index_series_str, wind_spd_series = data_frame_set(string_now8, string_now)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    #avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
    #print(date_time_of_wind_speed,avg_wind_speeds_for_sesh)
    #date_time_index_series_str, wind_spd_series = get_sesh_series_for_graphs(sesh)
    #print(date_time_index_series, wind_spd_series)
    #print(get_sesh_wind('2024-05-11T13:10','2:0'))
    return avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series
    

# 3 hour df for wind_dir.html chart
def wind_dir_3hours():
    now = datetime.now()
    now3 = now - timedelta(hours=3, minutes=5)

    string_now = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")
    string_now3 = dt.datetime.strftime(now3, "%Y-%m-%d %H:%M")

    # Unpack the DataFrame and other data correctly
    df, date_time_index_series_str, wind_spd_series = data_frame_set(string_now3, string_now)
    
    if df.empty:
        return [], []  # Return empty lists if no data is available

    # Extract timestamps and wind directions
    timestamps = [time.strftime('%H:%M') for time in df.index]
    wind_directions = df['wind_dir'].tolist()

    return timestamps, wind_directions

#
def wind_direction_change_1hour():
    now = datetime.now()
    now1 = now - timedelta(hours=1, minutes=15)

    string_now = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")
    string_now1 = dt.datetime.strftime(now1, "%Y-%m-%d %H:%M")

    # Unpack the DataFrame and other data correctly
    df, date_time_index_series_str, wind_spd_series = data_frame_set(string_now1, string_now)
    #print(df)

    if df.empty:
        return "No data available"

    # Earliest data point (last in the sorted DataFrame)
    initial_dir = df['wind_dir'].iloc[-13]
    #print(f"hour_wind_initial {initial_dir}")
    # Most recent data point (first in the sorted DataFrame)
    final_dir = df['wind_dir'].iloc[-1]
    #print(f"final_wind_dir {final_dir}")
    

    #print(f"Initial direction (earliest): {initial_dir}")
    #print(f"Final direction (most recent): {final_dir}")

    difference = (final_dir - initial_dir + 360) % 360
    if difference > 180:
        difference = 360 - difference  # Adjust to shortest path
        difference *= -1  # Make counterclockwise differences negative

    return difference

#hour_wind_diff = wind_direction_change_1hour()
#print(f"hour_wind_diff {hour_wind_diff}")

def wind_direction_change_3hour():
    now = datetime.now()
    now3 = now - timedelta(hours=3, minutes=30)

    string_now = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")
    string_now3 = dt.datetime.strftime(now3, "%Y-%m-%d %H:%M")

    # Unpack the DataFrame and other data correctly
    df, date_time_index_series_str, wind_spd_series = data_frame_set(string_now3, string_now)
    #print(df)


    if df.empty:
        return "No data available"

    # Earliest data point (last in the sorted DataFrame)
    initial_dir = df['wind_dir'].iloc[-37]
    #print(f"three_hour_wind_initial {initial_dir}")
    # Most recent data point (first in the sorted DataFrame)
    final_dir = df['wind_dir'].iloc[-1]
    #print(f"final_wind_dir {final_dir}")

    #print(f"Initial direction (earliest): {initial_dir}")
    #print(f"Final direction (most recent): {final_dir}")

    difference = (final_dir - initial_dir + 360) % 360
    if difference > 180:
        difference = 360 - difference  # Adjust to shortest path
        difference *= -1  # Make counterclockwise differences negative

    return difference

#three_hour_wind_diff = wind_direction_change_3hour()
#print(f"three_hour_wind_diff {three_hour_wind_diff}")

def wind_direction_change_6hour():
    now = datetime.now()
    now6 = now - timedelta(hours=6, minutes=30)

    string_now = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")
    string_now6 = dt.datetime.strftime(now6, "%Y-%m-%d %H:%M")

    # Unpack the DataFrame and other data correctly
    df, date_time_index_series_str, wind_spd_series = data_frame_set(string_now6, string_now)
    #print(df)


    if df.empty:
        return "No data available"

    # Earliest data point (last in the sorted DataFrame)
    initial_dir = df['wind_dir'].iloc[-73]
    #print(f"six_hour_wind_initial {initial_dir}")
    # Most recent data point (first in the sorted DataFrame)
    final_dir = df['wind_dir'].iloc[-1]
    #print(f"final_wind_dir {final_dir}")

    difference = (final_dir - initial_dir + 360) % 360
    if difference > 180:
        difference = 360 - difference  # Adjust to shortest path
        difference *= -1  # Make counterclockwise differences negative

    return difference

#six_hour_wind_diff = wind_direction_change_6hour()
#print(f"six_hour_wind_diff {six_hour_wind_diff}")







