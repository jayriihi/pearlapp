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
    
    # crescent gsheet 
    # specify gsheet id and sheet name for URL
    gsheetid = "1FIqEkMQv1468IU5gm_CrF1Vr6Ir1NF6PTiFDgcoGFo8"
    sheet_name = "Sheet1"
    gsheet_url = "https://docs.google.com/spreadsheets/d/{}/gviz/tq?tqx=out:csv&sheet={}".format(gsheetid, sheet_name)
    #print(gsheet_url)
    #pearl gsheet for compare purposes
     #specify gsheet id and sheet name for URL
    



    #Read gsheet into dataframe, rename columns and drop unused
    df = pd.read_csv(gsheet_url, skiprows = 2 )
    df.set_index ('Date/Time', inplace = True)
    df.rename(columns= {'Date/Time' :'date_time','Unnamed: 1' : 'wind_spd' , 'Unnamed: 2' : 'wind_max','Unnamed: 3' : 'wind_dir','Unnamed: 6' : 'date_code', 'Unnamed: 7' : 'time_code'}, inplace = True)
    df.drop({'Unnamed: 4','Unnamed: 5'}, axis=1, inplace =True)
    
    #make datetime the index of the df
    df.index = pd.to_datetime(df.index)
    #create sesh var = to df for the session period
    sesh = df.sort_index().loc[string_start_time:string_end_time]
    #print(sesh)
    #get series from sesh for graphs
    date_time_index_series = list(sesh.index)
    date_time_index_series_str = [t.strftime("%H:%M") for t in date_time_index_series]

    wind_spd_series = list (sesh["wind_spd"])

    #print(date_time_index_series_str, wind_spd_series)
    return sesh, date_time_index_series_str, wind_spd_series


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
    sesh, date_time_index_series_str, wind_spd_series = data_frame_set(string_start_time, string_end_time)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
    #print(date_time_of_wind_speed,avg_wind_speeds_for_sesh)
    #date_time_index_series_str, wind_spd_series = get_sesh_series_for_graphs(sesh)
    #print(date_time_index_series, wind_spd_series)
    return string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str,avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series

    #print(get_sesh_wind('2024-05-11T13:10','2:0'))


def pearl_1hr_quik():
    #get beginning and ending times the past hour and format to str
    now = datetime.now()
    now1 = now-timedelta(hours=1)

    string_now1 = dt.datetime.strftime(now1,"%Y-%m-%d %H:%M")
    string_now = dt.datetime.strftime(now,"%Y-%m-%d %H:%M")

    sesh, date_time_index_series_str, wind_spd_series = data_frame_set(string_now1, string_now)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
    #print(date_time_of_wind_speed,avg_wind_speeds_for_sesh)
    #date_time_index_series_str, wind_spd_series = get_sesh_series_for_graphs(sesh)
    #print(date_time_index_series, wind_spd_series)
    print(avg_wind_spd)
    return avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series
    #print(get_sesh_wind('2024-05-18T13:10','2,0'))  
#pearl_1hr_quik()

def pearl_3hr_quik():
    now = datetime.now()
    now3 = now-timedelta(hours=3)

    string_now3 = dt.datetime.strftime(now3,"%Y-%m-%d %H:%M")
    string_now = dt.datetime.strftime(now,"%Y-%m-%d %H:%M")

    sesh, date_time_index_series_str, wind_spd_series = data_frame_set(string_now3, string_now)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
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

    sesh, date_time_index_series_str, wind_spd_series = data_frame_set(string_now8, string_now)
    #date_time_of_wind_speed, avg_wind_speeds_for_sesh = get_df_series_for_graphs(sesh)
    avg_wind_spd, wind_max, wind_min,avg_wind_dir = get_wind_speed_data(sesh)
    #print(date_time_of_wind_speed,avg_wind_speeds_for_sesh)
    #date_time_index_series_str, wind_spd_series = get_sesh_series_for_graphs(sesh)
    #print(date_time_index_series, wind_spd_series)
    print(get_sesh_wind('2024-05-11T13:10','2:0'))
    return avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series
    
#pearl_1hr_quik()
