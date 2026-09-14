from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

import pandas as pd

from app import app
from app import wind_map_observation as source

NOW = datetime(2026, 9, 13, 22, 45, tzinfo=timezone.utc)


def frame(direction=35.4, speed=18.2, timestamp='2026-09-13 19:43:00'):
    return pd.DataFrame({'wind_spd': [speed], 'wind_max': [20], 'wind_dir': [direction]},
                        index=pd.to_datetime([timestamp]))


def observation(age=120, direction=35.4):
    return {'station': 'pearl', 'direction_deg': direction, 'speed_kts': 18.2,
            'observed_at': source.iso(NOW - timedelta(seconds=age))}


class ObservationTests(unittest.TestCase):
    def read(self, data):
        with patch.object(source.wind, 'fetch_sheet_window_df', return_value=data) as fetch, patch.object(source, 'utc_now', return_value=NOW):
            result = source.read_latest_pearl()
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.kwargs['sheet_name'], 'Pearl')
        return result

    def test_same_authoritative_frame_and_latest_row_with_bermuda_time(self):
        data = pd.concat([frame(), frame(270, 9, '2026-09-13 19:38')])
        result = self.read(data)
        self.assertEqual(result, observation())

    def test_north_normalization_and_zero_speed(self):
        result = self.read(frame(360, 0))
        self.assertEqual(result['direction_deg'], 0)
        self.assertEqual(result['speed_kts'], 0)

    def test_invalid_latest_does_not_fall_back_to_older_valid_row(self):
        for direction, speed in [(float('nan'), 12), (361, 12), (-1, 12), (35, -1), (35, float('inf'))]:
            with self.subTest(direction=direction, speed=speed):
                data = pd.concat([frame(35, 12, '2026-09-13 19:38'), frame(direction, speed)])
                with self.assertRaises(source.wind.NoWindDataError): self.read(data)

    def test_future_empty_and_flatlined_data_are_unavailable(self):
        for data in [frame(timestamp='2026-09-13 19:50'), frame().iloc[0:0],
                     pd.concat([frame(timestamp=f'2026-09-13 19:{minute:02}') for minute in [18, 23, 28, 33, 38, 43]])]:
            with self.assertRaises(source.wind.NoWindDataError): self.read(data)

    def test_winter_timezone_and_ambiguous_dst(self):
        result = self.read(frame(timestamp='2026-01-13 09:00'))
        self.assertEqual(result['observed_at'], '2026-01-13T13:00:00Z')
        with patch.object(source.wind, 'fetch_sheet_window_df', return_value=frame(timestamp='2026-11-01 01:30')):
            with self.assertRaises(Exception): source.read_latest_pearl()

    def test_cached_success_expires_by_observation_time_not_retrieval_time(self):
        cache = source.ObservationCache()
        with patch.object(source, 'read_latest_pearl', return_value=observation(age=350)) as read, patch.object(source.time, 'monotonic', return_value=10), patch.object(source, 'utc_now', return_value=NOW):
            self.assertEqual(cache.get()['status'], 'live')
            with patch.object(source, 'utc_now', return_value=NOW + timedelta(seconds=10)):
                self.assertEqual(cache.get()['status'], 'stale')
            self.assertEqual(read.call_count, 1)

    def test_cache_refresh_and_failure_ttl(self):
        cache = source.ObservationCache()
        with patch.object(source, 'read_latest_pearl', side_effect=[observation(), observation(0, 90), RuntimeError('upstream')]) as read, patch.object(source, 'utc_now', return_value=NOW), patch.object(source.time, 'monotonic', return_value=1) as clock:
            self.assertEqual(cache.get()['observation']['direction_deg'], 35.4)
            clock.return_value = 30
            cache.get()
            self.assertEqual(read.call_count, 1)
            clock.return_value = 62
            self.assertEqual(cache.get()['observation']['direction_deg'], 90)
            clock.return_value = 123
            self.assertEqual(cache.get()['status'], 'unavailable')
            clock.return_value = 140
            self.assertEqual(cache.get()['status'], 'unavailable')
            self.assertEqual(read.call_count, 3)

    def test_public_map_endpoint_no_store_and_protected_partner_endpoint_unchanged(self):
        payload = {'status': 'live', 'observation': observation(), 'server_time': source.iso(NOW),
                   'stale_after_seconds': 360, 'poll_interval_seconds': 60}
        with app.test_client() as client, patch('app.wind_map.observations.get', return_value=payload):
            result = client.get('/wind-map/observation')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json, payload)
            self.assertEqual(result.headers['Cache-Control'], 'no-store')
            self.assertEqual(client.get('/api/pearl/latest').status_code, 403)
            payload.update(status='unavailable', observation=None)
            result = client.get('/wind-map/observation')
            self.assertEqual(result.status_code, 503)
            self.assertEqual(result.headers['Retry-After'], '60')


if __name__ == '__main__':
    unittest.main()
