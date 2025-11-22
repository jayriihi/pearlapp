from wind_data_functionsc import data_frame_set, fetch_pred_cres_data
from datetime import datetime, timedelta
import datetime as dt

def test_data_frame_set():
    # Define test inputs for start and end times
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)

    string_start_time = dt.datetime.strftime(one_hour_ago, "%Y-%m-%d %H:%M")
    string_end_time = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")

    # Call the data_frame_set function
    try:
        result = data_frame_set(string_start_time, string_end_time)
        print(f"data_frame_set returned: {result}")
    except Exception as e:
        print(f"Error while testing data_frame_set: {e}")

def test_fetch_pred_cres_data():
    # Define test inputs for start and end times
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)

    string_start_time = dt.datetime.strftime(one_hour_ago, "%Y-%m-%d %H:%M")
    string_end_time = dt.datetime.strftime(now, "%Y-%m-%d %H:%M")

    # Call the fetch_pred_cres_data function
    try:
        result = fetch_pred_cres_data(string_start_time, string_end_time)
        print(f"fetch_pred_cres_data returned: {result}")
    except Exception as e:
        print(f"Error while testing data_frame_set: {e}")


if __name__ == "__main__":
    #test_data_frame_set()
    test_fetch_pred_cres_data()

