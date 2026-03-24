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


-----------------------------
maintenance_mode
------------------------------

Turn ON:
touch maintenance.on

Turn OFF:
rm maintenance.on

Bypass (when maintenance is ON):
- Set MAINT_BYPASS_KEY in your environment
- Visit any page with ?bypass=<SECRET>
  Example: /?bypass=your-secret-here
- If MAINT_BYPASS_KEY is unset or empty, bypass is disabled.

Git commands to pull to python anywhere from repo

git fetch
git checkout main
git pull

-----------------------------
production_deployment
------------------------------

Local environment variables needed before production-like testing:

- APP_ENV=development
- SECRET_KEY
- OPENWEATHER_API_KEY
- MAINT_BYPASS_KEY (optional)
- SESSION_COOKIE_SECURE=1 for HTTPS deployments

Local run command:

FLASK_DEBUG=1 python3 run.py

PythonAnywhere notes:

- The app object to import is: from app import app as application
- This repo includes /Users/jayriihiluoma/Documents/pearlapp/wsgi.py as a helper import target.
- The live PythonAnywhere WSGI file is the separate file configured in the Web tab under /var/www/.

PythonAnywhere checklist:

1. Create a virtualenv with the Python version used by your web app.
2. Install dependencies from requirements.txt.
3. Set environment variables in the PythonAnywhere WSGI file:
   APP_ENV=staging
   SECRET_KEY
   OPENWEATHER_API_KEY
   MAINT_BYPASS_KEY (optional)
   SESSION_COOKIE_SECURE=1
4. Add the repo path to sys.path in the PythonAnywhere WSGI file.
5. Import the Flask app as application.
6. Reload the web app from the PythonAnywhere Web tab.
