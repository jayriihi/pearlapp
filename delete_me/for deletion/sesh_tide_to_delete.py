
import requests
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
      
    string_start_time = dt.datetime.strftime(sesh_start_datetime,"%H:%M")
    #print(string_start_time)
    string_end_time = dt.datetime.strftime(sesh_end_time,"%H:%M")

    sesh_date = datetime.date(sesh_start_datetime)
    #print(string_end_time)

    return string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str, sesh_start_datetime, sesh_duration, sesh_end_time , sesh_date





#get tide data for session
def get_tide_data_for_session(datetimelocal_str,duration_str):
    string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str, sesh_start_datetime, sesh_duration, sesh_end_time , sesh_date = format_date_time(datetimelocal_str,duration_str)

    #get next date for retrieving tide data for sesh day plus the next

    sesh_date = datetime.date(sesh_start_datetime)
    sesh_date_str = sesh_date.strftime('%Y%m%d')
    #print(sesh_date_str)
    next_date = sesh_date + timedelta(days=1)
    next_date_str = next_date.strftime('%Y%m%d')
    #print(next_date_str)

    # to get data from NOAA website using their API using input date
    noaa_api_url = (("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=NOS.COOPS.TAC.WL&begin_date={}&end_date={}&datum=MLLW&station=2695540&time_zone=lst_ldt&units=english&interval=hilo&format=json").format(sesh_date_str,next_date_str))
    #print(noaa_api_url)
    day_tide = requests.get(noaa_api_url)

    # to view json file
    day_table = day_tide.json()
    #create days table as list
    day_table_pred = day_table["predictions"]

    #create data frame from predictions list y
    df = pd.DataFrame(day_table_pred)
    #df

    #Rename columns
    df.rename(columns = {'t':'Datetime', 'v':'Ht','type':'Tide'}, inplace=True)
    #df

    #Convert Date series to Datetime format to be used in calulations
    df['Datetime']= pd.to_datetime(df['Datetime'])
    #df['Datetime']

    #Sets Datetime as the index of the dataframe and drps the column 
    df.set_index ("Datetime", inplace = True)
    #df

    #Convert the Datetime into the index of the dataframe
    # variable dt stnds for day tides
    dt =[df.to_dict(orient='index')]
    #dt

    #Get times of the tides as keys of dictionary
    tide_time_dict = dt[0]
    time = sesh_start_datetime

    

    '''def get_prev_time_and_state(time, tide_time_dict):
        filtered_dict = {k:v for (k, v) in tide_time_dict.items() if k < time}
        prev_peak_time = max(filtered_dict.keys())
        prev_peak_state = filtered_dict[prev_peak_time]
        return prev_peak_time, prev_peak_state

    def get_next_time_and_state(time, tide_time_dict):
        filtered_dict = {k:v for (k, v) in tide_time_dict.items() if k >= time}
        next_peak_time = min(filtered_dict.keys())
        next_peak_state = filtered_dict[next_peak_time]
        return next_peak_time, next_peak_state

    def get_interval_qtr(low_input, high_input):
        return (high_input - low_input) / 4

    def is_my_time_slack(time, tide_time_dict):
        prev_peak_time, prev_peak_state = get_prev_time_and_state(time, tide_time_dict)
        next_peak_time, next_peak_state = get_next_time_and_state(time, tide_time_dict)
        interval_qtr = get_interval_qtr(prev_peak_time, next_peak_time)
        
        if (time > prev_peak_time + interval_qtr) and (time < next_peak_time - interval_qtr):
            return False
        else:
            return True

    def what_is_flow_direction(prev_peak_state):
        prev_peak_state = get_prev_time_and_state(time, tide_time_dict)
        if prev_peak_state == 'H':
            return 'Ebb'
        else:
            return 'Flood'
        
    def get_flow_state(time, tide_time_dict):
        if is_my_time_slack(time, tide_time_dict):
            return 'Slack'
        else:
            prev_peak_state = get_prev_time_and_state(time, tide_time_dict)
            return what_is_flow_direction(prev_peak_state)'''

    def get_prev_time_and_state(time, tide_time_dict):
        filtered_dict = {k:v for (k, v) in tide_time_dict.items() if k < time}
        prev_peak_time = max(filtered_dict.keys())
        prev_peak_state = filtered_dict[prev_peak_time]
        prev_peak_ht = (prev_peak_state['Ht'])
        prev_peak_ht = round(float(prev_peak_ht),1)
        prev_peak_state = (prev_peak_state['Tide'])
        #print(type(prev_peak_ht))
        return prev_peak_time, prev_peak_state, prev_peak_ht
    
    
    def get_next_time_and_state(time, tide_time_dict):
        filtered_dict = {k:v for (k, v) in tide_time_dict.items() if k >= time}
        next_peak_time = min(filtered_dict.keys())
        next_peak_state = filtered_dict[next_peak_time]
        next_peak_ht = (next_peak_state['Ht'])
        next_peak_ht = round(float(next_peak_ht),1)
        next_peak_state = (next_peak_state['Tide'])
        return next_peak_time, next_peak_state, next_peak_ht

    def get_interval_qtr(low_input, high_input):
        return (high_input - low_input) / 4

    def is_my_time_slack(time, tide_time_dict):
        prev_peak_time, prev_peak_state, prev_peak_ht = get_prev_time_and_state(time, tide_time_dict)
        next_peak_time, next_peak_state, next_peak_ht = get_next_time_and_state(time, tide_time_dict)
        interval_qtr = get_interval_qtr(prev_peak_time, next_peak_time)
        
        if (time > prev_peak_time + interval_qtr) and (time < next_peak_time - interval_qtr):
            return False
        else:
            return True

    def what_is_flow_direction(prev_peak_state):
        prev_peak_state = get_prev_time_and_state(time, tide_time_dict)
        prev_peak_state = prev_peak_state [1]
        if prev_peak_state == 'H':
            return 'Ebb'
        else:
            return 'Flood'
    
    def get_flow_state(time, tide_time_dict):
        if is_my_time_slack(time, tide_time_dict):
            return 'Slack'
        else:
            prev_peak_state = get_prev_time_and_state(time, tide_time_dict)
            return what_is_flow_direction(prev_peak_state)




    flow_state_beg = get_flow_state(sesh_start_datetime, tide_time_dict)
    flow_state_end = get_flow_state(sesh_end_time, tide_time_dict)
    prev_peak_time, prev_peak_state, prev_peak_ht = get_prev_time_and_state(time, tide_time_dict)
    next_peak_time, next_peak_state, next_peak_ht = get_next_time_and_state(time, tide_time_dict)

    print(sesh_start_datetime, flow_state_beg, sesh_end_time ,  flow_state_end )
    return(flow_state_beg, flow_state_end , prev_peak_time, prev_peak_state, next_peak_time, next_peak_state)

get_tide_data_for_session()
'''
def get_tide_for_now(now_time):
    now_time = datetime.now()
    string_now_time = dt.datetime.strftime(now_time,"%Y-%m-%d %H:%M")'''

     