from flask import Flask, redirect, url_for, render_template, request, session
import tide_now
import wind_data_functionsc

from app import app

@app.route("/")
@app.route("/home")
def home():
    avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series = wind_data_functionsc.pearl_1hr_quik()

    flow_state_beg, prev_peak_time, prev_peak_state, next_peak_time, next_peak_state = tide_now.get_tide_data_for_session()

    return render_template ("graph_temp.html", labels = date_time_index_series_str, values = wind_spd_series, past_hour_avg_wind_spd = avg_wind_spd, past_hour_avg_wind_min = wind_min, past_hour_avg_wind_max = wind_max, avg_wind_dir = avg_wind_dir, flow_state_beg = flow_state_beg , prev_peak_time = prev_peak_time, prev_peak_state = prev_peak_state, next_peak_time = next_peak_time, next_peak_state = next_peak_state)
    #return render_template("graph_1hr.html")

@app.route("/graph_1hr")
def graph_1hr():
    avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series = wind_data_functionsc.pearl_1hr_quik()

    return render_template ("graph_temp.html", labels = date_time_index_series_str, values = wind_spd_series, past_hour_avg_wind_spd = avg_wind_spd, past_hour_avg_wind_min = wind_min, past_hour_avg_wind_max = wind_max, avg_wind_dir = avg_wind_dir)

@app.route("/graph_3hr")
def graph_3hr():
    avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series = wind_data_functionsc.pearl_3hr_quik()

    return render_template ("graph_temp.html", labels = date_time_index_series_str, values = wind_spd_series, past_hour_avg_wind_spd = avg_wind_spd, past_hour_avg_wind_min = wind_min, past_hour_avg_wind_max = wind_max, avg_wind_dir = avg_wind_dir )


@app.route("/graph_8hr")
def graph_8hr():
    avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series = wind_data_functionsc.pearl_8hr_quik()

    return render_template ("graph_temp.html", labels = date_time_index_series_str, values = wind_spd_series, past_hour_avg_wind_spd = avg_wind_spd, past_hour_avg_wind_min = wind_min, past_hour_avg_wind_max = wind_max, avg_wind_dir = avg_wind_dir )
    #return render_template("graph_1hr.html")


@app.route("/windput", methods = ["POST" , "GET"])
# takes the post intputs fromer user on windput page makes them into session variables
def windput():
    if request.method == "POST":
        #getting form data and saving as session variables
        req = request.form
        #print(req)
        sessiondatetime = request.form["sessiondatetime"]
        #print(sessiondatetime)
        #sessiondatetime_str = datetime.strftime(sessiondatetime)
        #print(sessiondatetime)
        session['sessiondatetime'] = sessiondatetime

        duration = request.form["duration"]
        session['duration'] = duration
        #print(session['duration'])
               
        return wind()
        #return render_template("windput.html",form = form)

    else:
        return_val = render_template("windput.html") 
        return return_val


@app.route("/wind")
def wind():

    #print(session['timestart'])
    #avg_wind_spd, wind_max, wind_min,sesh_start_date_str,sesh_start_time_str,h,m,avg_wind_dir = get_sesh_wind(session['sessiondatetime'],  session['duration'])

    string_start_time, string_end_time, h, m, sesh_start_date_str, sesh_start_time_str,avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series = wind_data_functionsc.get_sesh_wind(session['sessiondatetime'],  session['duration'])
    

    #wind = get_sesh_wind(datetime.date(2022,5,3), datetime.time(12,00), timedelta(hours=+1, minutes=+0))
    #return render_template('wind.html', value_avg = avg_wind_spd, value_max = wind_max, value_min = wind_min,value_date = sesh_start_date_str, value_time = sesh_start_time_str, value_hours = h, value_minutes = m, value_avg_n_wind_dir = avg_wind_dir)
    return render_template('wind.html', value_avg = avg_wind_spd, value_max = wind_max, value_min = wind_min,value_date = sesh_start_date_str, value_time = sesh_start_time_str, value_hours = h, value_minutes = m, value_avg_n_wind_dir = avg_wind_dir, labels = date_time_index_series_str , values = wind_spd_series)

    #value_avg = wind[6], value_max = wind[7], value_min = wind[8],value_date = wind[4], value_time = wind[5], value_hours = wind[2], value_minutes = wind[3], value_avg_n_wind_dir = wind[9])


@app.route("/graph_temp")
def graph_temp():
    avg_wind_spd, wind_max, wind_min,avg_wind_dir, date_time_index_series_str, wind_spd_series = wind_data_functionsc.pearl_1hr_quik()

    return render_template ("graph_temp.html", labels = date_time_index_series_str, values = wind_spd_series, past_hour_avg_wind_spd = avg_wind_spd, past_hour_avg_wind_min = wind_min, past_hour_avg_wind_max = wind_max, avg_wind_dir = avg_wind_dir )
    #return render_template("graph_1hr.html")


@app.errorhandler(500)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('500.html'), 500
