"""Dashboard retrieval checks; all HTTP and tide data are mocked."""
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests

from app import app, views
from app.modules import wind_data_functionsc as wind

NOW = wind.bda_tz.localize(pd.Timestamp('2026-11-17 12:00').to_pydatetime())
TIDE = dict.fromkeys(('flow_state_beg', 'prev_peak_time_disp', 'prev_peak_state_disp',
                      'next_peak_time_disp', 'next_peak_state_disp', 'tide_error_msg'))
TIDE['tide_ok'] = False


def frame(end='2026-11-17 12:00', flat=False):
    times = pd.date_range(end=end, periods=120, freq='5min')
    return pd.DataFrame({
        'Date/Time': times,
        'wind_spd': [10 if flat else 5 + i % 17 for i in range(120)],
        'wind_max': [25 + i % 9 for i in range(120)],
        'wind_dir': [90 if flat else (350 + i * 7) % 360 for i in range(120)],
    }).iloc[::-1].reset_index(drop=True)


def response(data, source='gviz'):
    # Match the actual Pearl CSV formats, including slash-separated timestamps.
    header = ('"Pearl data Past hour - Avg Date/Time","speed","Max max","dir"\n'
              if source == 'gviz' else
              '"Pearl data","","",""\n"Past hour - Avg","","Max",""\n'
              '"Date/Time","speed","max","dir"\n')
    return Mock(text=header + data.to_csv(
        index=False, header=False, date_format='%Y/%m/%d %H:%M',
    ))


class DashboardWindTests(unittest.TestCase):
    def setUp(self):
        self.now = patch.object(wind, 'get_timezone_now', return_value=NOW)
        self.now.start()
        self.addCleanup(self.now.stop)

    def route(self, hours, station='pearl', responses=None, error=None):
        with patch.object(wind.requests, 'get', side_effect=error or responses) as http, \
                patch.object(views, 'get_tide_snapshot', return_value=TIDE.copy()), \
                patch.object(views.tide_now, 'fetch_tide_predictions', return_value=([], [])), \
                patch.object(views, 'render_template', wraps=views.render_template) as render, \
                patch.object(views, 'log') as log:
            result = app.test_client().get(f'/winds/{hours}?station={station}')
        self.assertEqual(result.status_code, 200)
        self.assertIn('wind', result.get_data(as_text=True).lower())
        logs = '\n'.join(str(call.args[0]) for call in log.call_args_list)
        self.assertNotIn('[winds timing]', logs)
        return render.call_args.kwargs, http

    def assert_ranges(self, http, rows):
        for call in http.call_args_list:
            query = parse_qs(urlparse(call.args[0]).query)
            self.assertEqual(query['range'], [f'A1:D{rows}'])
            self.assertIn('cb', query)
            self.assertEqual(call.kwargs['headers']['Cache-Control'], 'no-cache')
            self.assertEqual(call.kwargs['headers']['Pragma'], 'no-cache')

    def test_all_windows_and_stations_share_one_download_and_preserve_calculations(self):
        data = frame()
        for hours in (1, 3, 8):
            for station, config in wind.STATIONS.items():
                with self.subTest(hours=hours, station=station):
                    context, http = self.route(hours, station, [response(data)])
                    self.assertEqual(http.call_count, 1)
                    self.assert_ranges(http, 123)
                    self.assertEqual(parse_qs(urlparse(http.call_args.args[0]).query)['sheet'], [config['sheet']])
                    self.assertEqual(context['station_key'], station)
                    self.assertTrue(context['wind_available'])
                    chronological = data.sort_values('Date/Time').set_index('Date/Time')
                    start = pd.Timestamp(NOW.replace(tzinfo=None)) - pd.Timedelta(hours=hours, minutes=5)
                    selected = chronological.loc[start:]
                    self.assertEqual(context['values'], selected.wind_spd.tolist())
                    self.assertEqual(context['labels'], selected.index.strftime('%H:%M').tolist())
                    self.assertEqual(context['past_hour_avg_wind_spd'], round(selected.wind_spd.mean(), 1))
                    self.assertEqual(context['past_hour_avg_wind_max'], selected.wind_max.max())
                    self.assertEqual(context['past_hour_avg_wind_min'], selected.wind_spd.min())
                    self.assertEqual(context['avg_wind_dir'], int(round(wind.get_avg_wind_dir(selected.wind_dir))))
                    self.assertEqual(context['cur_wind_spd'], selected.wind_spd.iloc[-1])
                    self.assertEqual(context['cur_wind_dir'], selected.wind_dir.iloc[-1])
                    history = chronological.loc[pd.Timestamp('2026-11-17 08:55'):]
                    self.assertEqual(context['wd_dirs'], history.wind_dir.tolist())
                    self.assertEqual(len(context['wd_labels']), 38)
                    self.assertTrue(all(label.endswith('Z') for label in context['wd_labels']))

    def test_freshness_fallback_uses_same_small_range(self):
        context, http = self.route(1, responses=[response(frame('2026-11-17 11:40')), response(frame(), 'export')])
        self.assertEqual(http.call_count, 2)
        self.assertIn('/export?', http.call_args.args[0])
        self.assert_ranges(http, 123)
        self.assertTrue(context['wind_available'])
        self.assertEqual(context['values'][-1], frame().wind_spd.iloc[0])

    def test_http_failure_uses_existing_export_fallback(self):
        context, http = self.route(3, responses=[requests.ConnectionError('gviz down'), response(frame(), 'export')])
        self.assertEqual(http.call_count, 2)
        self.assertTrue(context['wind_available'])
        self.assert_ranges(http, 123)

    def test_flatlined_and_out_of_window_data_are_unavailable(self):
        for data in (frame(flat=True), frame('2026-11-15 12:00')):
            with self.subTest(latest=data['Date/Time'].max()):
                context, http = self.route(1, responses=[response(data), response(data, 'export')])
                self.assertFalse(context['wind_available'])
                self.assertEqual(context['wd_dirs'], [])
                self.assert_ranges(http, 123)

    def test_failed_download_does_not_retry_for_direction_history(self):
        context, http = self.route(8, error=requests.ConnectionError('offline'))
        self.assertEqual(http.call_count, 2)  # Existing gviz/export fallback only.
        self.assertFalse(context['wind_available'])
        self.assertEqual(context['wind_error'], 'Unexpected error retrieving wind data')
        self.assertEqual(context['wd_labels'], [])
        self.assertEqual(context['wd_dirs'], [])

    def test_session_history_keeps_8064_rows_and_historical_lookup(self):
        data = frame('2026-11-14 12:00')
        with patch.object(wind.requests, 'get', side_effect=[response(data), response(data, 'export')]) as http:
            result = wind.get_sesh_wind('2026-11-14T11:00', '1:00', station_key='pearl')
        self.assert_ranges(http, 8064)
        self.assertEqual(wind.SESSION_NUM_ROWS, 8064)
        self.assertEqual(result[-1], data.sort_values('Date/Time').tail(14).wind_spd.tolist())

    def test_pearl_gviz_retains_all_120_readings_including_newest_two(self):
        data = frame()
        with patch.object(wind.requests, 'get', return_value=response(data)) as http:
            parsed = wind.fetch_sheet_csv('Pearl', num_rows=wind.DASHBOARD_NUM_ROWS)
        self.assertEqual(http.call_count, 1)
        self.assert_ranges(http, 123)
        self.assertEqual(parse_qs(urlparse(http.call_args.args[0]).query)['headers'], ['3'])
        self.assertEqual(len(parsed), 120)
        self.assertEqual(pd.to_datetime(parsed['Date/Time']).tolist(), data['Date/Time'].tolist())
        for column in ('wind_spd', 'wind_max', 'wind_dir'):
            self.assertEqual(parsed[column].tolist(), data[column].tolist())

    def test_pearl_export_preserves_all_readings_after_gviz_failure(self):
        data = frame()
        with patch.object(wind.requests, 'get', side_effect=[
            requests.ConnectionError('gviz down'), response(data, 'export'),
        ]) as http:
            parsed = wind.fetch_sheet_csv('Pearl', num_rows=wind.DASHBOARD_NUM_ROWS)
        self.assertEqual(http.call_count, 2)
        self.assert_ranges(http, 123)
        self.assertEqual(len(parsed), 120)
        self.assertEqual(pd.to_datetime(parsed['Date/Time']).tolist(), data['Date/Time'].tolist())
        self.assertEqual(parsed.wind_spd.tolist(), data.wind_spd.tolist())

    def test_pearl_fallback_keeps_gviz_when_export_is_older(self):
        gviz_data = frame('2026-11-17 11:50')
        with patch.object(wind.requests, 'get', side_effect=[
            response(gviz_data), response(frame('2026-11-17 11:40'), 'export'),
        ]) as http:
            parsed = wind.fetch_sheet_csv('Pearl', num_rows=123)
        self.assertEqual(http.call_count, 2)
        self.assertEqual(pd.to_datetime(parsed['Date/Time']).max(), gviz_data['Date/Time'].max())

    def test_shared_frame_is_not_mutated_and_legacy_callers_still_work(self):
        data = frame()
        original = data.copy(deep=True)
        with patch.object(wind, 'fetch_sheet_csv', side_effect=AssertionError('duplicate download')):
            wind.get_wind_data(1, sheet_df=data)
            wind.wind_dir_3hours(sheet_df=data)
        pd.testing.assert_frame_equal(data, original)
        with patch.object(wind.requests, 'get', return_value=response(data)) as http:
            wind.pearl_8hr_quik()
        self.assertEqual(http.call_count, 1)
        self.assert_ranges(http, 123)


if __name__ == '__main__':
    unittest.main()
