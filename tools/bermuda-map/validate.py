"""Validate shipped geometry with the offline preparation requirements."""
import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, shape, box
from shapely.ops import unary_union

DATA = Path(__file__).resolve().parents[2] / 'app/static/wind-map/data'


def validate():
    metadata = json.loads((DATA / 'metadata.json').read_text())
    collections = {}
    for name, facts in metadata['files'].items():
        raw = (DATA / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == facts['sha256'], name
        collection = json.loads(raw)
        assert len(collection['features']) == facts['features'], name
        for feature in collection['features']:
            geometry = shape(feature['geometry'])
            assert not geometry.is_empty and geometry.is_valid, (name, feature['properties'])
        collections[name] = collection
    land = unary_union([shape(f['geometry']) for f in collections['land.geojson']['features']])
    pearl = Point(-64.83724166666667, 32.29175333333333)
    assert land.covers(pearl)
    islands = [g for g in land.geoms if g.covers(pearl)]
    assert len(islands) == 1
    assert islands[0].area < .00001, 'Pearl incorrectly joined to a main island'
    policy = metadata['display_filter']
    rendered = [f for f in collections['land.geojson']['features'] if f['properties']['render']]
    assert len(rendered) == policy['rendered_polygons']
    assert unary_union([shape(f['geometry']) for f in rendered]).covers(pearl)
    preserve_sound = box(*policy['preserve_sound_bounds'])
    for f in collections['land.geojson']['features']:
        if f['properties']['protected'] or preserve_sound.intersects(shape(f['geometry'])):
            assert f['properties']['render'], 'Protected island removed from display'
        if not f['properties']['render']:
            assert f['properties']['area_m2'] < policy['minimum_area_m2']
    # Original source reference points remain geometry checks even though these
    # town/water labels are no longer part of the displayed label collection.
    water_points = [(-64.8576111, 32.2814669), (-64.847899, 32.2609911),
                    (-64.7175491441161, 32.3332999), (-64.68686959124443, 32.3477207),
                    (-64.7901825, 32.2871891)]
    town_points = [(-64.7853167, 32.2942679), (-64.8339593, 32.3276283),
                   (-64.676717, 32.3810447), (-64.8699524, 32.2962083),
                   (-64.7385344, 32.3211651)]
    for coordinates in water_points:
        assert not land.covers(Point(coordinates)), f'Water incorrectly filled: {coordinates}'
    for coordinates in town_points:
        assert land.covers(Point(coordinates)), f'Settlement missing land: {coordinates}'
    # Open water through the central neck of Flatts Inlet, sourced from the
    # coastline's open corridor and visually checked in the browser detail view.
    assert not land.covers(Point(-64.7375, 32.3230)), 'Flatts Inlet filled'
    assert metadata['validation']['land_polygons_before'] == metadata['validation']['land_polygons_after']
    assert sum(f['gzip_bytes'] for f in metadata['files'].values()) < 500_000
    print('PASS: file checksums, valid geometry, Pearl on its own island, five open water areas,')
    print('      five land settlements, Flatts Inlet, island retention and size budget.')
    print(f"      Display: {len(rendered)} polygons; Pearl and protected island group retained.")


if __name__ == '__main__':
    validate()
