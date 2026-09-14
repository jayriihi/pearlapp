# Cartography refinement

This change only refines map labels and the Pearl marker. Page layout,
navigation, coastline, roads, runways, navy water and pale land are unchanged.
No wind animation, controls, observation endpoint or dashboard connection was
added.

## Appearance

- Pearl's visible dot is 7 px instead of 12 px; the former broad double halo is
  replaced by a faint 2 px halo. Its label is 10 px, medium weight and muted aqua
  instead of 12 px bold bright aqua. The invisible 44 px touch target and
  verified-coordinate popup remain intact.
- Only Great Sound and the seven requested reference places are in the label
  collection. Former town, water, island and road labels cannot reappear on zoom.
- Reference text follows Great Sound's subdued blue-grey italic styling, at
  12 px on larger screens and 11 px on phones, normal weight and without pins.
- Labels wrap and use small screen-space placement alternatives to avoid
  collisions and clipping. Their underlying geographic anchors are unchanged by
  this placement. Panning and zooming continue to anchor them geographically.

## Position verification and naming decisions

Every anchor comes from an exact feature in the previously verified
2026-09-12 Geofabrik/OSM extract. The builder records both original source names
and OSM IDs. Area anchors are interior points of actual beach/park polygons,
not manually estimated coordinates or hotel/parking locations. Coordinates below
are rounded for readability; the GeoJSON retains source-derived precision.

| Display label | Latitude | Longitude | Source feature |
| --- | ---: | ---: | --- |
| Great Sound | 32.281467 | -64.857611 | [OSM node 1930879167](https://www.openstreetmap.org/node/1930879167) |
| Somerset Long Bay | 32.304321 | -64.871562 | [Somerset Long Bay Beach, way 915919000](https://www.openstreetmap.org/way/915919000) |
| Spanish Point | 32.306569 | -64.814373 | [Spanish Point Park, way 184584796](https://www.openstreetmap.org/way/184584796) |
| Horseshoe Bay | 32.252186 | -64.821680 | [Horseshoe Bay Beach, way 116591351](https://www.openstreetmap.org/way/116591351) |
| Elbow Beach | 32.272598 | -64.777125 | [Elbow Beach, way 173928971](https://www.openstreetmap.org/way/173928971) |
| Shelly Bay | 32.332921 | -64.739145 | [Shelly Bay Beach, way 166120993](https://www.openstreetmap.org/way/166120993) |
| Stone Crusher Corner | 32.364190 | -64.706356 | [OSM cape node 8541258182](https://www.openstreetmap.org/node/8541258182) |
| Clearwater Beach | 32.355786 | -64.659994 | [Clearwater Beach, way 155080043](https://www.openstreetmap.org/way/155080043) |

Spanish Point was the substantive naming ambiguity: OSM also has a broader
neighbourhood/peninsula node about 400 m east. This refinement uses the waterfront
park by the boat club, which suits the stated watersports purpose. The local
[Spanish Point Park listing](https://www.bermudayp.com/poi/view/444/spanish-point-park)
also places it at the end of Spanish Point Road beside the boat club. This choice
was raised with the owner for clarification; the waterfront is the working
interpretation unless they request the broader neighbourhood.

Stone Crusher Corner is an explicit named OSM cape, not an inferred location.
The [Bermuda government's Kindley Field Park notice](https://www.gov.bm/articles/section-kindley-field-park-closed-public)
independently identifies the locality along Kindley Field Road. The label marks
that locality, not a surveyed boat-ramp entrance.

The other beach names have matching mapped beach areas. Somerset Long Bay was
distinguished from both Warwick Long Bay and Long Bay at Cooper's Island;
Clearwater Beach was distinguished from Clearwater Middle School. Horseshoe Bay
and Shelly Bay use their beach polygons rather than offshore bay-label nodes.
The tourism authority's [beach geography descriptions](https://www.gotobermuda.com/plan/inspiration/article/bermudas-favourite-beach-walks)
provide supporting parish/coastal context for Horseshoe Bay, Elbow Beach and
Shelly Bay. All displayed wording follows the owner's requested names.

## Review

Updated WebKit renders (geography © OpenStreetMap contributors):

- [Phone portrait](wind-map-refinement/portrait.jpg)
- [Small phone](wind-map-refinement/small-phone.jpg)
- [Phone landscape](wind-map-refinement/landscape.jpg)
- [Desktop](wind-map-refinement/desktop.jpg)

The original land, road and runway GeoJSON files were compared byte for byte
against the Stage 2 build and are unchanged. Label data is now eight features
instead of 402, with refreshed checksums in metadata. The geometry checks, five
Flask tests, JavaScript syntax check and WebKit browser checks passed. All eight
reference labels are visible in the 390×844 portrait, 844×390 landscape and
1440×900 desktop overview. At the smallest 320×568 viewport, Spanish Point and
Clearwater Beach are collision-suppressed in the overview; panning/zooming gives
their labels space. No labels are placed beyond the map edges or over controls.
Physical iPhone review remains useful.

Changed files for this refinement: `app/static/wind-map/map.css`, `map.js`,
`data/labels.geojson`, `data/metadata.json`, `data/README.txt`;
`tools/bermuda-map/build.py`, `validate.py`, `README.md`; `docs/wind-map.md`.
Added this report and four updated screenshots under `docs/wind-map-refinement/`.
