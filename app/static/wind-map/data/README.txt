Pearl / Bermuda local geography

Data: OpenStreetMap contributors, extracted by Geofabrik.
See LICENSE.txt for ODbL-1.0 attribution and licence information.
See metadata.json for the exact source date, URL, SHA-256 and file checksums.

land.geojson: coastlines assembled as land polygons, with mapped water areas
removed. All islands retained; one-metre topology-preserving simplification.
Display only: polygons below 500 square metres have render=false unless they
intersect the Great/Little Sound preservation envelope, contain a named OSM
island/islet reference, or contain Pearl. Original geometry remains intact in
this database. area_m2 and protected properties document the selection;
metadata.json records the envelope and counts. This is a cartographic clutter
filter, not a geological classification of reefs versus islands.
roads.geojson: primary, secondary, tertiary and unclassified roads, grouped
by display class. Residential/service roads deliberately omitted.
context.geojson: runway lines.
labels.geojson: Great Sound plus seven selected watersports/beach reference
locations: Somerset Long Bay, Spanish Point (waterfront park), Horseshoe Bay,
Elbow Beach, Shelly Bay, Stone Crusher Corner and Clearwater Beach. Exact OSM
source features and original source names accompany each anchor. Beach/park
anchors are interior points of their mapped areas; Great Sound and Stone Crusher
Corner use their original OSM nodes. No other place or road labels are displayed.

All GeoJSON coordinates are WGS84 [longitude, latitude]. Place labels are
derived from OSM geometry; their selection, priorities and zoom thresholds
are editorial cartography. Not a nautical chart or navigation dataset.

Preparation: tools/bermuda-map/build.py in the Pearl repository.
The Flask application serves these files unchanged; it performs no GIS work.
