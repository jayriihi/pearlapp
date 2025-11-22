-----------------------------
daylight_savings_update_procedure
------------------------------



To update the time for wind in the main page and for sessions -

Open the Google virtual machine and use nano to open crescent_scraper.py.
Scroll to the near the bottom where the timedelta is set for the gsheet 
The timedelta sgould be -180 for DLS time and -240 for non DLS time
this is the difference between UTC and local BDA time 

To update time in the historic 1hr, 3hr and 8hr graphs -

Navigate to the wind_data_functions.py file in the crescent-app folder in python anywhere
make the adjustments to the time in the plots as noted in the comments for each chart

This updates the time for the tide -

Navigate to the tide_now.py file in the crescent-app folder in python anywhere

Change the timedelta according to the notes in the comments

Next to change the time in the tide chart go to the graph_temp_info_tide_chart.html file
scroll down to this code and make the change neccessary           

// Subtract 4 hours for Bermuda's time zone, 3 for daylight savings time
          hours -= 4;



