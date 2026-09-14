# Stage 2: isolated Bermuda basemap preview

**Animation update:** the later [fixed-direction wind animation report](wind-animation.md)
describes the current test animation, updated title and compact footer. The
Stage 2 report below records the original geography-only milestone.

**Cartography update:** the subsequent [label and Pearl-marker refinement](wind-map-labels.md)
supersedes this initial review's broad label selection and asset-size figures.
The original Stage 2 captures below are retained for comparison; updated renders
are linked from the refinement report. Page structure and geography are unchanged.

Review date: 2026-09-13. Open `/wind-map` directly. The dashboard has no link to
this preview. This stage delivers the geography and page foundation for review;
it does not display live measurements, simulate wind or provide Explore controls.

## Run and view

Use the existing Pearl Python environment; no new production packages are needed:

```sh
conda activate pearl311
FLASK_DEBUG=0 python run.py
```

Open <http://127.0.0.1:5001/wind-map>. On this workstation the equivalent Python
executable is `/Users/jayriihiluoma/miniconda3/envs/pearl311/bin/python`.
If the development server is already running on port 5001, use that instance.
On an iPhone on the same Wi-Fi, use `http://<Mac-LAN-IP>:5001/wind-map`, subject
to the Mac firewall. The existing `maintenance.on` switch still applies.

Pan, pinch/zoom, tap Pearl for verified coordinates, and use **Show Bermuda** to
restore the overview. **Back to Pearl** targets `/winds/1` and sets the existing
dashboard scroll-reset flag. Normal dashboard loading still needs its existing
weather services; map loading does not.

Review captures from WebKit (map data © OpenStreetMap contributors):

- [Portrait](wind-map-review/portrait.jpg)
- [Landscape](wind-map-review/landscape.jpg)
- [Pearl Island close-up](wind-map-review/pearl-detail.jpg)
- [Flatts Inlet close-up](wind-map-review/flatts-detail.jpg)
- [Castle Harbour close-up](wind-map-review/castle-detail.jpg)

## What is implemented

- Separate Flask blueprint and standalone template, local Leaflet 1.9.4 and local
  GeoJSON. No dashboard/base-template assets or Chart.js are loaded by this page.
- North-up Bermuda, navy water, muted land, subtle roads/runways and labels that
  appear with zoom. A collision check limits displayed labels to 32 and preserves
  space around the station and map controls. Overview labels take priority.
- A keyboard-accessible station marker at exactly `32.29175333333333,
  -64.83724166666667`. The owner verified the position from installation-photo
  GPS EXIF and WindSonic alignment to true north. No declination correction.
- Portrait and compact landscape layouts, dynamic viewport height, safe-area
  padding, reduced-motion map transitions and resize handling that preserves
  map centre/zoom. No continuously running render loop in this stage.
- Loading timeout, recoverable asset-load error, attribution and a downloadable
  ZIP containing the entire derived geographic database and its notices.

## Geography findings and licensing

The committed data comes from the Geofabrik Bermuda OpenStreetMap extract dated
2026-09-12. The dated download's SHA-256 was verified against the actual build
source. `metadata.json` records its URL, timestamp, checksum and derived-file
checksums. Preparation is reproducible with the scripts described in
[the preparation guide](../tools/bermuda-map/README.md).

There are 366 source coastline ways forming 318 closed, correctly oriented
coastline rings. Subtracting mapped inland water yields 324 land polygons; all
324 survive one-metre topology-preserving simplification. Area change is
0.001297%. Pearl's coordinate lies in both the source's named Pearl Island
outline and the final small island polygon. No coastline gaps were repaired or
land invented to make the source work.

Rendered reviews covered the whole island chain, the Great/Little Sounds,
Harrington Sound, Hamilton, Dockyard, St. George's, Pearl Island and nearby
islands, Flatts Inlet and Castle Harbour/causeway/runway context. Flatts' open
water corridor and the small Castle Harbour islands remain visible on zoom.
These are cartographic checks against the source, not a hydrographic survey.

Map data is under ODbL 1.0; attribution remains visible and `/wind-map/geography`
offers the complete derived database with source information and licence links.
Pearl's independently supplied station facts are stored separately. Leaflet's
BSD-2-Clause licence is included beside its pinned JS/CSS. No recurring map
subscription, tile service or API key is involved. Normal application hosting
and bandwidth still apply.

The four geographic layers total 614,555 bytes uncompressed (about 600 KiB).
Their estimated gzip total is 151,354 bytes (about 148 KiB); Flask's development
server serves the uncompressed files. Enabling static compression at the normal
web server is a later deployment option, not part of this change.

## Verification and limits

- Five Flask unit tests pass: page isolation from weather services, geography
  archive integrity, static assets, existing partner-API access protection and
  the existing maintenance hook.
- Offline geometry checks pass: checksums, valid geometry, retained islands,
  Pearl on its own island, five major water areas, five settlements and Flatts
  Inlet. A second build from the separately downloaded dated source reproduced
  all four layers and metadata byte for byte. JavaScript syntax check passes.
- Automated Chrome and WebKit checks pass at 390×844, 320×568, 844×390 and
  1440×900, at device scale factor 2. No external requests or JavaScript page
  errors were observed during normal map loading. Checked zoom controls,
  station popup, orientation/map-centre preservation, overview reset, return
  target/scroll flag, failed geography load/retry and reduced-motion loading.
- The return destination was intercepted in browser tests to avoid invoking
  production weather sources. Existing dashboard chart rendering was not
  exercised or changed.
- Actual iPhone touch/pinch behaviour, older iOS versions, Home Screen resume,
  notch/safe-area behaviour and performance on physical hardware still require
  review. Desktop WebKit is useful evidence, not a substitute for those checks.

The map is intentionally sparse: no buildings, residential/service roads,
bathymetry or terrain. Small islands cannot all be legible at whole-Bermuda
scale; zoom reveals them. Pearl's touch marker covers much of its tiny island
even at high zoom. Some overview labels are omitted when space is tight.
Local hosting removes third-party map requests but does not add offline support.
Future OSM refreshes require a deliberate rebuild and visual review; unexpected
coastline topology causes the build to fail for inspection.

## Exact file changes

Only one pre-existing file changed: `app/__init__.py`, adding blueprint import
and registration. `views.py`, `wind_tide_dir.html`, `base.html`, all Dir cards,
`run.py` and production `requirements.txt` are unchanged.

Added files:

```text
app/wind_map.py
app/wind_map_config.py
app/templates/wind_map.html
app/static/wind-map/map.js
app/static/wind-map/map.css
app/static/wind-map/data/land.geojson
app/static/wind-map/data/roads.geojson
app/static/wind-map/data/context.geojson
app/static/wind-map/data/labels.geojson
app/static/wind-map/data/metadata.json
app/static/wind-map/data/LICENSE.txt
app/static/wind-map/data/README.txt
app/static/vendor/leaflet/leaflet.js
app/static/vendor/leaflet/leaflet.css
app/static/vendor/leaflet/LICENSE
tests/test_wind_map.py
tools/bermuda-map/build.py
tools/bermuda-map/validate.py
tools/bermuda-map/review_browser.py
tools/bermuda-map/requirements.txt
tools/bermuda-map/README.md
docs/wind-map.md
docs/wind-map-review/portrait.jpg
docs/wind-map-review/landscape.jpg
docs/wind-map-review/pearl-detail.jpg
docs/wind-map-review/flatts-detail.jpg
docs/wind-map-review/castle-detail.jpg
```

GIS and browser-review tools were installed only in a temporary directory for
this work. They are not Flask runtime dependencies. Nothing was deployed.

## Next stage, after review approval

Keep working behind `/wind-map`. Add the isolated public Pearl observation
endpoint with timestamp validation, freshness/availability states and tests.
Always open in LIVE using the latest published measurement. Stale or unavailable
data must never retain a LIVE presentation; stop or clearly alter animation.
EXPLORE must remain usable when the observation service is unavailable.

Add the single Canvas wind overlay and lightweight requestAnimationFrame loop,
with uniform illustrative speed, adaptive particle count, capped pixel density,
pause when hidden, and a static reduced-motion alternative. The bearing is where
wind is FROM, so particles travel toward `(bearing + 180) % 360`, with cardinal
and wraparound direction tests. Keep the actual Pearl speed numeric only.

Implement the portrait circular dial and landscape horizontal slider with one
shared floating-point bearing, immediate continuous response without snapping,
whole-degree display and nearest 16-point label. Preserve bearing on orientation
changes. Label EXPLORE as hypothetical; Back to Live refreshes Pearl's measurement
without changing the map position. Include observation age and the explanation:
“Pearl’s direction shown uniformly across Bermuda. Local conditions vary.”

Review the complete isolated experience on physical iPhones/Home Screen before
a separately approved final dashboard connection. That final connection would
only make Pearl's Dir cards on 1/3/8-hour dashboards links, retaining their
existing degree readings. Back to Pearl will continue to target `/winds/1`.
