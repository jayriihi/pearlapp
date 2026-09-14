"""Build the small, local basemap from a complete Geofabrik Bermuda extract.

No network calls. Coastline gaps, reversed rings and invalid selected geometry
fail the build instead of being silently repaired. See README.md.
"""
import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import osmium
from pyproj import Transformer
from shapely import line_merge
from shapely.geometry import LineString, LinearRing, MultiLineString, Point, Polygon, box, mapping
from shapely.ops import polygonize_full, transform, unary_union
from shapely.wkb import loads

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Transformer.from_crs(4326, 32620, always_xy=True).transform
UNPROJECT = Transformer.from_crs(32620, 4326, always_xy=True).transform
PEARL = Point(-64.83724166666667, 32.29175333333333)
# Cartographic display policy only: preserve all source geometry in the database.
MIN_DISPLAY_AREA_M2 = 500
# Deliberately broad preservation envelope around Great/Little Sound and Pearl.
# This is not a claimed geographic boundary of the sounds.
PRESERVE_SOUND_BOUNDS = (-64.88, 32.258, -64.795, 32.332)
# Exact OSM features, not name matching: beach polygons rather than similarly
# named bays/hotels; Spanish Point's waterfront park rather than its village.
# Source decisions are documented in docs/wind-map-labels.md.
REFERENCE_PLACES = {
    "node/1930879167": "Great Sound",
    "way/915919000": "Somerset Long Bay",
    "way/184584796": "Spanish Point",
    "way/116591351": "Horseshoe Bay",
    "way/173928971": "Elbow Beach",
    "way/166120993": "Shelly Bay",
    "node/8541258182": "Stone Crusher Corner",
    "way/155080043": "Clearwater Beach",
}
ROAD_CLASSES = {"primary": "main", "primary_link": "main", "secondary": "main",
                "secondary_link": "main", "tertiary": "secondary", "unclassified": "local"}


def feature(geometry, **properties):
    return {"type": "Feature", "properties": properties, "geometry": mapping(geometry)}


def compact(geometry, metres):
    result = transform(UNPROJECT, transform(PROJECT, geometry).simplify(metres, preserve_topology=True))
    if result.is_empty or not result.is_valid:
        raise ValueError("Invalid simplified geometry")
    return result


class Extract(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.coast = []
        self.roads = defaultdict(list)
        self.water = []
        self.context = []
        self.labels = {}
        self.pearl_outline = None
        self.named_island_points = []
        self.factory = osmium.geom.WKBFactory()

    def label(self, tags, geometry, source):
        name = REFERENCE_PLACES.get(source)
        if not name:
            return
        # Interior points anchor the actual mapped beach/park, not its car park.
        point = geometry if geometry.geom_type == "Point" else geometry.representative_point()
        candidate = feature(point, name=name, source_name=tags.get("name"), kind="water" if name == "Great Sound" else "reference",
                            priority=list(REFERENCE_PLACES).index(source), min_zoom=10, osm_source=source)
        self.labels.setdefault(name, candidate)

    def node(self, node):
        tags = dict(node.tags)
        if tags.get("name"):
            self.label(tags, Point(node.location.lon, node.location.lat), f"node/{node.id}")
            if tags.get("place") in {"island", "islet"}:
                self.named_island_points.append(Point(node.location.lon, node.location.lat))

    def way(self, way):
        tags = dict(way.tags)
        road = ROAD_CLASSES.get(tags.get("highway"))
        coast = tags.get("natural") == "coastline"
        runway = tags.get("aeroway") == "runway"
        if not (road or coast or runway):
            return
        line = LineString([(n.lon, n.lat) for n in way.nodes])
        if coast:
            self.coast.append(line)
            if tags.get("name") == "Pearl Island":
                self.pearl_outline = Polygon(line)
        if road:
            self.roads[road].append(compact(line, 3))
        if runway:
            self.context.append(feature(compact(line, 2), kind="runway", osm_source=f"way/{way.id}"))

    def area(self, area):
        tags = dict(area.tags)
        water = tags.get("natural") == "water"
        source = f"{'way' if area.from_way() else 'relation'}/{area.orig_id()}"
        named = source in REFERENCE_PLACES
        named_island = bool(tags.get("name")) and tags.get("place") in {"island", "islet"}
        if not (water or named or named_island):
            return
        geometry = loads(self.factory.create_multipolygon(area), hex=True)
        if not geometry.is_valid:
            raise ValueError(f"Invalid selected area: {area.id}")
        if water:
            self.water.append(geometry)
        if named:
            self.label(tags, geometry, source)
        if named_island:
            self.named_island_points.extend(g.representative_point() for g in geometry.geoms)


def write_json(path, data):
    raw = (json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    path.write_bytes(raw)
    return {"bytes": len(raw), "gzip_bytes": len(gzip.compress(raw, mtime=0)),
            "sha256": hashlib.sha256(raw).hexdigest()}


def build(source, output, source_url, expected_sha256=None):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("Source checksum does not match pinned extract")
    data = Extract()
    data.apply_file(str(source), locations=True)
    _, cuts, dangles, invalid = polygonize_full(data.coast)
    if any(not g.is_empty for g in (cuts, dangles, invalid)):
        raise ValueError("Coastline is incomplete or invalid; inspect the source before rebuilding")
    merged = line_merge(MultiLineString(data.coast), directed=True)
    rings = list(merged.geoms) if merged.geom_type == "MultiLineString" else [merged]
    # Bermuda's complete sea-facing rings are all CCW (land to the left).
    # Refuse unexpected topology instead of guessing which side is land.
    if any(not r.is_ring or not LinearRing(r.coords).is_ccw for r in rings):
        raise ValueError("Unexpected open/reversed coastline; manual review required")
    raw_land = unary_union([Polygon(r) for r in rings]).difference(unary_union(data.water))
    if not raw_land.is_valid:
        raise ValueError("Invalid assembled land")
    land = compact(raw_land, 1)  # one metre, retains tiny islands and narrow channels
    if not data.pearl_outline or not data.pearl_outline.covers(PEARL) or not land.covers(PEARL):
        raise ValueError("Verified Pearl mast must fall inside the source and rendered Pearl outline")
    land_parts = list(land.geoms) if land.geom_type == "MultiPolygon" else [land]
    source_parts = list(raw_land.geoms) if raw_land.geom_type == "MultiPolygon" else [raw_land]
    if len(land_parts) != len(source_parts):
        raise ValueError("Simplification lost an island")
    if set(data.labels) != set(REFERENCE_PLACES.values()):
        raise ValueError("A reference place is missing from the source; review its OSM feature")
    preservation_area = box(*PRESERVE_SOUND_BOUNDS)
    land_features = []
    for g in land_parts:
        area_m2 = transform(PROJECT, g).area
        protected = (g.covers(PEARL) or preservation_area.intersects(g)
                     or any(g.covers(point) for point in data.named_island_points))
        land_features.append(feature(g, area_m2=round(area_m2, 2),
                                     protected=protected, render=protected or area_m2 >= MIN_DISPLAY_AREA_M2))
    layers = {
        "land.geojson": land_features,
        "roads.geojson": [feature(MultiLineString(lines), kind=kind)
                          for kind, lines in sorted(data.roads.items())],
        "context.geojson": data.context,
        "labels.geojson": sorted(data.labels.values(), key=lambda f: (f["properties"]["priority"], f["properties"]["name"])),
    }
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, features in layers.items():
        files[name] = write_json(output / name, {"type": "FeatureCollection", "features": features})
        files[name]["features"] = len(features)
    with osmium.io.Reader(str(source)) as reader:
        timestamp = reader.header().get("osmosis_replication_timestamp")
    metadata = {
        "source": "OpenStreetMap contributors / Geofabrik Bermuda extract", "source_url": source_url,
        "source_timestamp": timestamp, "source_sha256": digest,
        "license": "ODbL-1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "coordinates": "WGS84 longitude, latitude (EPSG:4326)", "bounds": list(land.bounds),
        "build": "pyosmium 4.3.1, Shapely 2.1.2, pyproj 3.7.2; tools/bermuda-map/build.py",
        "display_filter": {"minimum_area_m2": MIN_DISPLAY_AREA_M2,
            "preserve_sound_bounds": list(PRESERVE_SOUND_BOUNDS),
            "preserve_named_islands_and_pearl": True,
            "rendered_polygons": sum(f["properties"]["render"] for f in land_features),
            "hidden_small_polygons": sum(not f["properties"]["render"] for f in land_features)},
        "validation": {"source_coastline_ways": len(data.coast), "closed_ccw_rings": len(rings),
            "coastline_cuts": 0, "coastline_dangles": 0, "invalid_rings": 0,
            "land_polygons_before": len(source_parts), "land_polygons_after": len(land_parts),
            "pearl_inside_named_source_island_and_rendered_land": True,
            "simplification_metres": 1,
            "land_area_change_percent": round(100 * abs(transform(PROJECT,land).area / transform(PROJECT,raw_land).area - 1), 6)},
        "files": files,
    }
    write_json(output / "metadata.json", metadata)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "app/static/wind-map/data")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    build(args.source, args.output, args.source_url, args.expected_sha256)
