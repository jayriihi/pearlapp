# Small geometry, bearing wording and chart teal

Only the three requested visual refinements were made. Review at `/wind-map`.

## Conservative geography filtering

The display now skips 140 of the 324 land polygons; 184 remain visible. A polygon
is omitted only if it is smaller than 500 m² and is outside every preservation
exception. Area is measured in UTM 20N during the offline build, not calculated
in the browser or estimated from pixel size.

Preservation exceptions:

- Any polygon containing Pearl's verified station coordinate.
- Any polygon containing a named OSM island/islet node or an interior reference
  point from a named island/islet area.
- Every polygon intersecting the broad Great/Little Sound and Pearl preservation
  envelope: west −64.88, south 32.258, east −64.795, north 32.332. This rectangle
  is an editorial preservation zone, not a claimed boundary of Great Sound.

This intentionally retains some tiny features in the protected island group and
some named small features elsewhere. It avoids turning a size-only rule into a
claim that every small polygon is a reef. Larger offshore rocks may remain.

All original polygon coordinates are retained in `land.geojson`; each feature
now has area/protection/render metadata. Leaflet skips only `render=false`
features at all zoom levels. No shoreline was reshaped, merged or filled. Roads,
runways, reference-place coordinates and Pearl's position are unchanged.

Rendered close-ups of Horseshoe Bay and Great Sound were inspected. The offshore
speckling is substantially reduced near Horseshoe Bay; the Pearl/Great Sound
island group remains intact. The full derived database and its attribution
remain available through the existing map-data download.

## Wording and exact colour

The on-map bearing legend is now **From 45° NE**, with no reciprocal/illustrative
second line. The existing test badge still identifies this as non-live data.
Particle travel calculations remain reciprocal: the 45° FROM wind travels SW.

The actual chart wind-series colour is `#00e1d1`: `wind_tide_dir.html` defines
`--aqua` near line 17, reads it into `AQUA` near line 864, and uses it as the
`wind speeds` dataset's `borderColor` and `pointBackgroundColor` near line 935.
`wind.js` now uses that exact hex value for both trails and heads. It is kept as
a documented local constant to preserve dashboard isolation.

No particle thickness, length, count, speed, opacity or lifecycle behavior was
changed. The subtle dark under-stroke remains for contrast against pale land.

## Review images and checks

Updated WebKit captures (geography © OpenStreetMap contributors):

- [Portrait overview](wind-map-polish/portrait.jpg)
- [Landscape overview](wind-map-polish/landscape.jpg)
- [Horseshoe Bay close-up](wind-map-polish/horseshoe.jpg)
- [Great Sound/Pearl close-up](wind-map-polish/great-sound.jpg)

Geometry/protection checks, six animation tests and five Flask tests pass.
Original land coordinates were compared against the initial Stage 2 build;
roads/runways were compared byte for byte. Browser review checks cover the
simplified legend, active animation, reciprocal bearing, viewport sizing,
pan/zoom, orientation, reduced motion, retry and navigation.

Changed: `app/static/wind-map/map.js`, `wind.js`, `data/land.geojson`,
`data/metadata.json`, `data/README.txt`; `tools/bermuda-map/build.py`, `validate.py`,
`review_browser.py`, `README.md`; `docs/wind-animation.md`.
Added this report and its four review images. No additional feature work or
dashboard connection was undertaken.
