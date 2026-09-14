/* Local geography; LIVE/EXPLORE state is managed separately in live.js. */
(() => {
  'use strict';
  const config = JSON.parse(document.getElementById('map-config').textContent);
  const message = document.getElementById('map-message');
  const messageText = document.getElementById('map-message-text');
  const retry = document.getElementById('retry-map');
  const fitButton = document.getElementById('show-bermuda');
  const zoomIn = document.getElementById('zoom-in');
  const zoomOut = document.getElementById('zoom-out');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let map, extent, labels = [], ready = false, loading = false;
  let layoutFrame = null, resizeFrame = null;
  const stationPosition = [config.station.latitude, config.station.longitude];
  const live = new window.PearlWindController(config);
  document.addEventListener('windmaplayout', scheduleLayout);

  document.getElementById('back-to-pearl').addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button) return;
    // Reuse the destination page's existing pageshow scroll-reset contract.
    try { sessionStorage.setItem('pearl_scroll_to_top_after_refresh', '1'); } catch (_) { /* ordinary navigation still works */ }
  });

  function fail() {
    messageText.textContent = 'Bermuda could not be loaded. Check your connection and try again.';
    message.hidden = false;
    retry.hidden = false;
  }

  async function readJSON(name) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(config.dataUrl + name, { signal: controller.signal });
      if (!response.ok) throw new Error(`Map asset ${name}: ${response.status}`);
      return await response.json();
    } finally { clearTimeout(timer); }
  }

  function fitBermuda() {
    if (!ready) return;
    const short = map.getSize().y < 340;
    map.fitBounds(extent, { paddingTopLeft: [26, short ? 15 : 65], paddingBottomRight: [26, short ? 50 : 75], animate: false });
  }

  function makeMap() {
    map = L.map('bermuda-map', {
      zoomControl: false, attributionControl: false,
      minZoom: 9, maxZoom: 16, zoomSnap: .1, zoomDelta: .75,
      maxBounds: [[32.20, -64.96], [32.44, -64.58]], maxBoundsViscosity: 1,
      zoomAnimation: !reducedMotion.matches, fadeAnimation: !reducedMotion.matches,
    }).setView([32.316, -64.766], 11);
    map.createPane('geographicLabels').style.zIndex = 650;
    map.getPane('geographicLabels').style.pointerEvents = 'none';
    fitButton.addEventListener('click', fitBermuda);
    zoomIn.addEventListener('click', () => map.zoomIn(.75, { animate: !reducedMotion.matches }));
    zoomOut.addEventListener('click', () => map.zoomOut(.75, { animate: !reducedMotion.matches }));
    map.on('moveend zoomend', scheduleLayout);
    // Avoid detached labels during Leaflet's animated zoom; pan remains anchored.
    map.on('zoomstart', () => { map.getPane('geographicLabels').style.visibility = 'hidden'; });
    map.on('zoomend', () => { map.getPane('geographicLabels').style.visibility = ''; });
    const stage = document.querySelector('.map-stage');
    const resize = () => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => {
        map.invalidateSize({ pan: true, animate: false, debounceMoveend: true });
        scheduleLayout();
      });
    };
    new ResizeObserver(resize).observe(stage);
    window.addEventListener('pageshow', resize);
    window.visualViewport?.addEventListener('resize', resize);
  }

  function addStation() {
    const icon = L.divIcon({ className: 'pearl-icon', iconSize: [44, 44], iconAnchor: [22, 22],
      html: '<span class="pearl-target" aria-hidden="true"></span><span class="pearl-caption" aria-hidden="true">PEARL</span>' });
    const marker = L.marker(stationPosition, { icon, title: 'Pearl Island wind station — view location',
      alt: 'Pearl Island wind station', keyboard: true, zIndexOffset: 1000 }).addTo(map);
    const popup = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = 'Pearl Island station';
    popup.append(title, document.createElement('br'),
      `${config.station.latitude.toFixed(7)}° N`, document.createElement('br'),
      `${Math.abs(config.station.longitude).toFixed(7)}° W`, document.createElement('br'),
      'Wind direction referenced to true north.');
    marker.bindPopup(popup, { maxWidth: 240, autoPanPadding: [30, 40] });
    marker.getElement().setAttribute('aria-label', 'Pearl Island wind station — view verified coordinates');
    marker.getElement().dataset.station = 'pearl';
  }

  function addLabels(features) {
    labels = features.map(feature => {
      const anchor = L.DomUtil.create('div', 'geo-label-anchor', map.getPane('geographicLabels'));
      const text = L.DomUtil.create('span', 'geo-label', anchor);
      const properties = feature.properties;
      text.classList.add(properties.kind);
      text.textContent = properties.name;
      anchor.setAttribute('aria-hidden', 'true');
      return { anchor, text, properties, position: L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]) };
    });
  }

  function intersects(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  function scheduleLayout() {
    if (layoutFrame !== null) return;
    layoutFrame = requestAnimationFrame(() => { layoutFrame = null; layoutLabels(); });
  }

  function layoutLabels() {
    if (!ready) return;
    const size = map.getSize(), zoom = map.getZoom();
    const station = map.latLngToContainerPoint(stationPosition);
    const occupied = [
      { left: station.x - 48, right: station.x + 8, top: station.y - 10, bottom: station.y + 10 },
    ];
    const mapRect = map.getContainer().getBoundingClientRect();
    for (const selector of ['.map-actions', '.north', '.map-intro', '.explore-controls']) {
      const node = document.querySelector(selector);
      if (node.hidden) continue;
      const rect = node.getBoundingClientRect();
      occupied.push({ left: rect.left - mapRect.left - 5, right: rect.right - mapRect.left + 5,
        top: rect.top - mapRect.top - 5, bottom: rect.bottom - mapRect.top + 5 });
    }
    let count = 0;
    for (const item of labels) {
      item.anchor.style.visibility = 'hidden';
      if (zoom < item.properties.min_zoom || count >= 32) continue;
      const point = map.latLngToContainerPoint(item.position);
      const width = item.text.offsetWidth, height = item.text.offsetHeight;
      // Keep coastal names inside the viewport with only a small text offset.
      // This does not change the geographic anchor or move off-screen places in.
      const shiftX = Math.max(16 + width / 2, Math.min(size.x - 16 - width / 2, point.x)) - point.x;
      if (Math.abs(shiftX) > 24) continue;
      // Small text-placement alternatives keep coastal names apart.
      // Anchors stay geographic; no geographic feature is moved or invented.
      let placement = null;
      for (const offset of [0, -14, 14, -28, 28]) {
        for (const offsetX of [shiftX, shiftX + 24, shiftX - 24]) {
          if (Math.abs(offsetX) > 28) continue;
          const rect = { left: point.x + offsetX - width / 2 - 4, right: point.x + offsetX + width / 2 + 4,
            top: point.y + offset - height / 2 - 3, bottom: point.y + offset + height / 2 + 3 };
          if (rect.left < 12 || rect.right > size.x - 12 || rect.top < 12 || rect.bottom > size.y - 12) continue;
          if (occupied.some(other => intersects(rect, other))) continue;
          placement = { rect, offset, offsetX };
          break;
        }
        if (placement) break;
      }
      if (!placement) continue;
      L.DomUtil.setPosition(item.anchor, map.latLngToLayerPoint(item.position).add([placement.offsetX, placement.offset]));
      item.anchor.style.visibility = '';
      occupied.push(placement.rect);
      count++;
    }
    const metres = map.distance(map.containerPointToLatLng([0, size.y / 2]), map.containerPointToLatLng([80, size.y / 2]));
    const candidates = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000];
    const rounded = candidates.filter(value => value <= metres).pop() || 10;
    const scale = document.getElementById('map-scale');
    scale.textContent = rounded >= 1000 ? `${rounded / 1000} km` : `${rounded} m`;
    scale.style.width = `${80 * rounded / metres}px`;
    zoomIn.disabled = zoom >= map.getMaxZoom();
    zoomOut.disabled = zoom <= map.getMinZoom();
    document.getElementById('bermuda-map').dataset.visibleLabels = count;
  }

  async function load() {
    if (loading || ready) return;
    loading = true;
    retry.hidden = true;
    messageText.textContent = 'Loading Bermuda…';
    try {
      if (!window.L) throw new Error('Leaflet is unavailable');
      const [land, roads, context, places, metadata] = await Promise.all([
        'land.geojson', 'roads.geojson', 'context.geojson', 'labels.geojson', 'metadata.json'
      ].map(readJSON));
      for (const collection of [land, roads, context, places]) {
        if (collection.type !== 'FeatureCollection' || !Array.isArray(collection.features)) throw new Error('Invalid geography');
      }
      if (!map) makeMap();
      L.geoJSON(land, { interactive: false, filter: feature => feature.properties.render !== false,
        style: { color: '#9dafad', weight: .8, opacity: 1,
        fillColor: '#b9c9c4', fillOpacity: 1, smoothFactor: 0 } }).addTo(map);
      const roadLayer = L.geoJSON(roads, { interactive: false, style: feature => ({ color: '#829a99',
        weight: feature.properties.kind === 'main' ? .8 : .5,
        opacity: feature.properties.kind === 'local' ? 0 : .45 }) }).addTo(map);
      const roadDetail = () => roadLayer.eachLayer(layer => {
        const kind = layer.feature.properties.kind;
        layer.setStyle({ opacity: kind === 'local' ? (map.getZoom() >= 14 ? .28 : 0) : .45,
          weight: kind === 'main' ? (map.getZoom() >= 13 ? 1.3 : .8) : .6 });
      });
      map.on('zoomend', roadDetail);
      L.geoJSON(context, { interactive: false, style: { color: '#81989a', weight: 3, opacity: .8 } }).addTo(map);
      addLabels(places.features);
      addStation();
      const [west, south, east, north] = metadata.bounds;
      extent = L.latLngBounds([south, west], [north, east]);
      ready = true;
      message.hidden = true;
      fitButton.disabled = false;
      fitBermuda();
      roadDetail();
      scheduleLayout();
      // Animation failure must not break geography, map controls or navigation.
      try {
        const wind = new window.PearlWindOverlay(map, 0);
        live.attachWind(wind);
      } catch (error) {
        document.getElementById('wind-age').textContent = 'Wind animation unavailable';
        console.error('Pearl wind:', error);
      }
      document.getElementById('bermuda-map').dataset.ready = 'true';
    } catch (error) {
      console.error('Bermuda map:', error);
      fail();
    } finally { loading = false; }
  }

  retry.addEventListener('click', load);
  load();
})();
