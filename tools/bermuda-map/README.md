# Preparing the local Bermuda basemap

These tools are for occasional offline data preparation and review. The Flask
application serves committed assets and does not import GIS or browser packages.

## Source and reproducible build

Source: [Geofabrik Bermuda extract](https://download.geofabrik.de/europe/united-kingdom/bermuda.html),
derived from OpenStreetMap. The committed extract snapshot is
`2026-09-12T20:21:58Z`. Its dated download was independently retrieved and verified
to have the same SHA-256 as the build input:

```text
c7bf9b9867bce712972b8e676fd2db62c314c7d4449c2c1cc0c6169a1cffe46f
```

Use a separate development environment (Python 3.11 was used), not the running
Flask environment. Example commands from the repository root:

```sh
python3 -m venv /tmp/pearl-map-build
/tmp/pearl-map-build/bin/pip install -r tools/bermuda-map/requirements.txt
curl -fL https://download.geofabrik.de/europe/united-kingdom/bermuda-260912.osm.pbf -o /tmp/bermuda.osm.pbf
/tmp/pearl-map-build/bin/python tools/bermuda-map/build.py /tmp/bermuda.osm.pbf \
  --source-url https://download.geofabrik.de/europe/united-kingdom/bermuda-260912.osm.pbf \
  --expected-sha256 c7bf9b9867bce712972b8e676fd2db62c314c7d4449c2c1cc0c6169a1cffe46f
/tmp/pearl-map-build/bin/python tools/bermuda-map/validate.py
```

The source PBF is about 2 MB and is not checked in. Geofabrik may eventually
remove older dated downloads; archive the pinned PBF separately if long-term
byte-for-byte regeneration is required. For a new snapshot, record its actual
dated URL/checksum and inspect the result before replacing the committed files.
Use `--output /tmp/bermuda-candidate` to generate a candidate without replacing
the served data. `validate.py` checks the committed directory.

The builder uses pyosmium to read complete coastline/road/area geometry, Shapely
to assemble directed closed coastline rings and subtract mapped inland water,
and pyproj for metre-based simplification in UTM zone 20N. It does not use a
world tile stack, tile server, GIS work during requests or manually sketched
coastlines. Closed CCW sea-facing rings are an explicit property of this extract;
unexpected gaps, reversed rings or invalid geometry stop the build rather than
being guessed or repaired. One-metre land simplification preserves topology;
road simplification uses three metres. All shipped coordinates are WGS84.

Source metadata, geometry counts, validation results and SHA-256 file hashes are
written to `app/static/wind-map/data/metadata.json`. Estimated gzip sizes are
measurements only; the builder does not write compressed assets or configure
HTTP compression. LICENSE.txt and README.txt are maintained separately and
must accompany all four layers and metadata in the downloadable archive.

The label selection is now the eight exact OSM features in `REFERENCE_PLACES`.
See [label provenance and cartography review](../../docs/wind-map-labels.md).
The build fails if a selected feature disappears; it does not fall back to a
similarly named neighbourhood, hotel or bay. Land, roads and runways retain
their original Stage 2 geometry. Geometry checks for the former settlement and
water labels now use their original coordinates independently of displayed text.

The land layer also carries a conservative display filter: `render=false` for
polygons smaller than 500 m², except Pearl, named OSM islands/islets and all
polygons intersecting the Great/Little Sound preservation envelope. The full
geometry is retained in the database. The renderer skips flagged features at
every zoom level. The builder measures area in UTM 20N, records policy/counts in
metadata, and the validator checks that the protected group and Pearl remain
displayed. See [the refinement report](../../docs/wind-map-polish.md).

## Licence and vendor assets

The derived geographic database is offered under
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), with visible
[OpenStreetMap attribution](https://www.openstreetmap.org/copyright) and a
complete ZIP available at `/wind-map/geography`. Keep both the notices and the
download when deploying or editing the geography. Independently supplied Pearl
station information is kept outside the OSM database in `app/wind_map_config.py`.

Leaflet 1.9.4 is vendored unmodified from:

- `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`
- `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css`
- `https://unpkg.com/leaflet@1.9.4/LICENSE`

Leaflet uses BSD-2-Clause. Default marker and layers-control images are not used;
the station uses a CSS div icon. No CDN request occurs at page load. Vendor
upgrades should be deliberate and followed by mobile regression checks.

## Local verification

In the existing application environment:

```sh
python -m unittest discover -s tests -v
node --test tests/wind_animation.test.cjs
node --check app/static/wind-map/map.js
node --check app/static/wind-map/wind.js
FLASK_DEBUG=0 python run.py
```

In a separate review environment, optionally install `playwright==1.62.0` and
its WebKit browser. `review_browser.py` uses an installed Google Chrome for its
default engine. The script connects to an already running local server:

```sh
python tools/bermuda-map/review_browser.py --engine chrome
python tools/bermuda-map/review_browser.py --engine webkit
```

Options include `--url` and `--output`. Default captures go to
`/private/tmp/pearl-map-review`. The review script injects a test-only Leaflet hook
into its browser response to capture precise close-up locations; no debugging
global is exposed by the application's JS. The return destination is intercepted
to avoid triggering remote weather calls. It checks loading, viewport sizes,
marker coordinates, zoom, orientation, navigation, reduced motion and retry.

Inspect the images as well as assertions: Pearl and nearby islands, Flatts' open
channel, Castle Harbour/causeway/runways, labels and low-clutter overview framing.
Browser emulation does not establish physical iPhone/Home Screen performance.

The browser review now also checks the fixed-direction Canvas overlay: a single
canvas, changing frames, the 45° FROM / 225° TO convention, pixel-density cap,
alignment after map panning and static reduced-motion frames. See the current
[wind animation review](../../docs/wind-animation.md) for lifecycle tests,
implementation details and the physical-device checklist.
