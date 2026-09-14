# Fixed-direction wind animation review

The subsequent [visual refinement](wind-map-polish.md) adds the conservative
small-polygon display filter and switches the animation to the exact dashboard
teal. The current bearing legend is simply **From 45° NE**.

Implemented only the approved title/footer refinements and the isolated Canvas
animation. No LIVE observations, Explore controls or dashboard Dir-card links.

## View and verify

The existing local development server serves
<http://127.0.0.1:5001/wind-map>. To restart from the repository root:

```sh
conda activate pearl311
FLASK_DEBUG=0 python run.py
```

In Chrome, reload the map. On iOS Safari use the same local map URL already used
for the geography review, or `http://<Mac-LAN-IP>:5001/wind-map` on the same Wi-Fi.

1. Confirm **Bermuda live wind map**, the compact station footer and visible OSM
   attribution. **Test wind · not live** must remain clearly visible.
2. Watch a bright particle head: it should move down and left, southwest. The
   temporary legend explicitly says **From 45° NE**. This is a
   test direction, not a retrieved Pearl observation.
3. Pan the map, zoom in/out, tap Pearl, and use **Show Bermuda**. Wind covers both
   land and water; labels and the station sit above it. The overlay must stay
   aligned with the viewport, and controls must remain usable.
4. Rotate the phone. The canvas should resize to the map and maintain the same
   NE-to-SW direction. Brief clearing/reseeding during zoom is intentional.
5. Switch tabs/apps or lock the phone for several seconds, then return. Motion
   should resume without a large catch-up jump. Repeat in the Home Screen app.
6. With the OS/browser's Reduce Motion preference enabled, expect still direction
   arrows and no continuous animation. Changing the preference while open is
   supported.

Review stills (geography © OpenStreetMap contributors):
[portrait](wind-animation-review/portrait.jpg),
[landscape](wind-animation-review/landscape.jpg),
[desktop](wind-animation-review/desktop.jpg).
Use the running page to judge motion; screenshots show appearance only.

## Implementation and performance choices

`TEST_WIND_FROM_DEGREES = 45` in `map.js` is the single temporary bearing input.
`wind.js` exposes a small independent `PearlWindOverlay` class. It receives the
Leaflet map and a bearing, and creates one transparent canvas in its own pane
above land/roads and below reference labels and the Pearl marker. All particle
positions are ordinary JS objects, with no per-particle DOM, external library,
texture download, worker, API request or new package dependency.

For a FROM bearing θ, the unit travel vector in north-up screen coordinates is
`(-sin θ, cos θ)`. Canvas y increases downward, so FROM north travels south;
FROM east travels west. The entire field uses the same vector and the same
illustrative 28 CSS-pixels/second speed. Nothing samples land, terrain or local
wind speed. Occasional small arrowheads reinforce the direction.

One requestAnimationFrame chain updates motion using elapsed time, with at most
approximately 60 canvas draws per second even on higher-refresh displays. This
follows the browser's [timestamp-based animation guidance](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame).
Particle count follows viewport area, between 32 and 220; sustained frame gaps
over 40 ms reduce the count. Density is capped at 1.5 device pixels per CSS pixel
and approximately three million backing pixels in very large windows. There is
no continuous quality increase/decrease cycle.

Trails are short line segments redrawn onto a cleared transparent canvas, rather
than an accumulating image buffer. This avoids residual ghost trails and opaque
water-colour fills over the geography. Subtle dark outlines keep the aqua trails
legible on pale land. Tail lengths and lifetimes vary only for appearance;
direction and travel speed remain uniform.

Pan movement cancels the Leaflet pane's translation through its public coordinate
conversion, keeping this uniform field aligned with the visible map. Movement
boundaries and bearing changes reseed particles. Animated zoom temporarily pauses
and clears wind, then resumes with fresh trails to avoid stretching or smearing.

[Visibility events](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API)
and pagehide/pageshow explicitly stop/restart scheduling. Elapsed time resets on
resume and is capped after throttling. Reduced motion draws a sparse static arrow
field. Event listeners and the scheduled callback are removed on map disposal.
Canvas setup failure leaves the geography and exit controls usable with an
animation-unavailable message.

The footer is 36 CSS px at the tested 390×844 phone size, 49 px at 320×568 where
its content wraps, 40 px in 844×390 landscape and 41 px at 1440×900. Device safe-area
insets are additional. OSM attribution and the database download remain present.

## Validation and practical limits

- Six Node tests pass: cardinal/reciprocal/wrap bearings, equal displacement with
  simulated 60/120 Hz clocks, one RAF chain, visibility/page lifecycle pause and
  resume, reduced-motion changes, zoom/resize/disposal and slow-frame adaptation.
- Five existing Flask tests pass. JavaScript syntax and whitespace checks pass.
- Chrome and WebKit browser reviews pass at 390×844, 320×568, 844×390 and 1440×900.
  Checks include changing Canvas pixels, one canvas only, 45°/225° diagnostics,
  pixel-density cap, map/canvas alignment after pan, zoom, orientation, station
  popup, overview/return navigation, loading/retry and unchanged reduced-motion
  frames. No external requests or JavaScript page errors were observed.
- The automated lifecycle tests exercise application behavior with controlled
  events and clocks. Actual iPhone backgrounding, thermals, battery usage,
  Safari/Home Screen lifecycle and perceived frame rate still require device
  review. Desktop WebKit is not an iPhone performance benchmark.

Tradeoffs are deliberate: animation is screen-space and uniformly illustrative,
briefly disappears during animated zoom, and may reduce particle density on slow
devices. It does not claim real wind at each place. The test badge/legend must
remain until the next separately approved stage provides real observation and
freshness handling.

## Exact file changes for this stage

Modified:

```text
app/templates/wind_map.html
app/static/wind-map/map.css
app/static/wind-map/map.js
tests/test_wind_map.py
tools/bermuda-map/review_browser.py
tools/bermuda-map/README.md
docs/wind-map.md
```

Added:

```text
app/static/wind-map/wind.js
tests/wind_animation.test.cjs
docs/wind-animation.md
docs/wind-animation-review/portrait.jpg
docs/wind-animation-review/landscape.jpg
docs/wind-animation-review/desktop.jpg
```

Geography assets, Pearl position, reference-place selection, Flask route/blueprint,
production dependencies, `views.py`, dashboard templates and all Dir cards are
unchanged in this stage. Nothing was deployed. Stop here for owner review before
LIVE data and Explore implementation.
