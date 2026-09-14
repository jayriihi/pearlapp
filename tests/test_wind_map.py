"""Run with python -m unittest discover -s tests -v. No external services."""
import hashlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from app import app
from app.wind_map_config import PEARL_STATION

DATA = Path(app.static_folder) / "wind-map/data"


class WindMapTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_preview_is_independent_of_weather_services(self):
        with patch('requests.get', side_effect=AssertionError('Unexpected external request')):
            response = self.client.get('/wind-map')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Bermuda live wind map', html)
        self.assertIn('PEARL · CONNECTING', html)
        self.assertIn('id="direction-dial"', html)
        self.assertIn('id="direction-range"', html)
        self.assertIn('href="/winds/1"', html)
        self.assertNotIn('chart.js', html)
        self.assertNotIn('bootstrap', html)
        self.assertNotIn('Pearl LIVE', html)
        self.assertIn(str(PEARL_STATION['latitude']), html)
        self.assertIn(str(PEARL_STATION['longitude']), html)
        self.assertEqual(PEARL_STATION['bearing_reference'], 'true north')
        self.assertEqual(PEARL_STATION['magnetic_correction_deg'], 0)

    def test_geography_download_is_complete_and_attributed(self):
        response = self.client.get('/wind-map/geography')
        self.assertEqual(response.status_code, 200)
        with ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(set(archive.namelist()), {
                'land.geojson', 'roads.geojson', 'context.geojson', 'labels.geojson',
                'metadata.json', 'LICENSE.txt', 'README.txt'})
            self.assertIn(b'OpenStreetMap contributors', archive.read('LICENSE.txt'))
            metadata = json.loads(archive.read('metadata.json'))
            for name, facts in metadata['files'].items():
                raw = archive.read(name)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), facts['sha256'])
                self.assertEqual(len(json.loads(raw)['features']), facts['features'])

    def test_static_geography_and_vendor_assets_exist(self):
        for filename in ('land.geojson', 'roads.geojson', 'labels.geojson', 'context.geojson', 'metadata.json'):
            response = self.client.get('/static/wind-map/data/' + filename)
            self.assertEqual(response.status_code, 200, filename)
            json.loads(response.data)
            response.close()
        for filename in ('leaflet.js', 'leaflet.css', 'LICENSE'):
            response = self.client.get('/static/vendor/leaflet/' + filename)
            self.assertEqual(response.status_code, 200, filename)
            response.close()

    def test_existing_partner_api_still_requires_credentials(self):
        self.assertEqual(self.client.get('/api/pearl/latest').status_code, 403)

    def test_existing_maintenance_hook_covers_map(self):
        with patch('app.os.path.exists', return_value=True):
            self.assertEqual(self.client.get('/wind-map').status_code, 503)


if __name__ == '__main__':
    unittest.main()
