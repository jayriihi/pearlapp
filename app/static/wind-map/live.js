/* LIVE/EXPLORE state and controls. Geography and particle styling stay separate. */
(() => {
  'use strict';
  const COMPASS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const normalize = degrees => ((degrees % 360) + 360) % 360;
  const compass = degrees => COMPASS[Math.round(normalize(degrees) / 22.5) % 16];
  const whole = degrees => Math.round(normalize(degrees)) % 360;
  const setText = (node, text) => { if (node.textContent !== text) node.textContent = text; };

  class PearlWindController {
    static normalize = normalize;
    static compass = compass;
    static whole = whole;
    static pointerBearing(x, y) { return normalize(Math.atan2(x, -y) * 180 / Math.PI); }

    constructor(config) {
      this.config = config;
      this.mode = 'live';
      this.status = 'loading';
      this.checking = true;
      this.lastObservation = null;
      this.exploreBearing = 0;
      this.serverEpoch = 0;
      this.receivedAt = 0;
      this.receivedWall = 0;
      this.pollTimer = null;
      this.ageTimer = null;
      this.inflight = null;
      this.requestId = 0;
      this.pageHidden = false;
      this.wind = null;
      this.pointerId = null;
      this.toggle = document.getElementById('wind-mode-toggle');
      this.controls = document.getElementById('explore-controls');
      this.dial = document.getElementById('direction-dial');
      this.slider = document.getElementById('direction-range');
      this.stateText = document.getElementById('wind-state');
      this.reading = document.getElementById('wind-reading');
      this.ageText = document.getElementById('wind-age');
      this.intro = document.querySelector('.map-intro');
      this.toggle.addEventListener('click', () => this.mode === 'live' ? this.enterExplore() : this.enterLive());
      this.slider.addEventListener('input', () => this.selectBearing(Number(this.slider.value)));
      for (const control of [this.dial, this.slider]) control.addEventListener('keydown', event => this.keyDirection(event));
      this.dial.addEventListener('pointerdown', event => {
        if (this.mode !== 'explore' || this.pointerId !== null || event.button !== 0) return;
        event.preventDefault();
        this.pointerId = event.pointerId;
        this.dial.setPointerCapture(event.pointerId);
        this.dial.focus({ preventScroll: true });
        this.dragDirection(event);
      });
      this.dial.addEventListener('pointermove', event => {
        if (event.pointerId === this.pointerId) this.dragDirection(event);
      });
      for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
        this.dial.addEventListener(name, event => { if (event.pointerId === this.pointerId) this.pointerId = null; });
      }
      window.addEventListener('resize', () => {
        if (this.pointerId !== null && this.dial.hasPointerCapture(this.pointerId)) this.dial.releasePointerCapture(this.pointerId);
        this.pointerId = null;
      });
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) this.pauseRequests();
        else if (!this.pageHidden && this.mode === 'live') this.resumeLive();
      });
      window.addEventListener('pagehide', () => { this.pageHidden = true; this.pauseRequests(); });
      window.addEventListener('pageshow', event => {
        const wasHidden = this.pageHidden;
        this.pageHidden = false;
        // A restored navigation is a new map entry and opens LIVE; ordinary
        // background/foreground does not reset an ongoing Explore session.
        if (event.persisted) this.enterLive();
        else if (wasHidden && this.mode === 'live') this.resumeLive();
      });
      this.render();
      this.startUpdates();
    }

    attachWind(wind) { this.wind = wind; wind.setEnabled(false); this.render(); }

    now() {
      // Use server time, not the phone's clock. Wall elapsed additionally covers
      // platforms whose performance clock pauses during system sleep.
      return this.serverEpoch + Math.max(0, performance.now() - this.receivedAt, Date.now() - this.receivedWall);
    }

    observationAge() {
      return this.lastObservation ? (this.now() - Date.parse(this.lastObservation.observed_at)) / 1000 : null;
    }

    ageLabel(age) {
      if (age < 60) return 'just now';
      if (age < 3600) return `${Math.floor(age / 60)} min ago`;
      return `${Math.floor(age / 3600)} hr ago`;
    }

    enterExplore() {
      this.mode = 'explore';
      this.exploreBearing = this.lastObservation?.direction_deg ?? 0;
      this.pauseRequests();
      this.render();
    }

    enterLive() {
      this.mode = 'live';
      this.resumeLive();
    }

    resumeLive() {
      this.pauseRequests();
      this.checking = true;
      this.render();
      this.startUpdates();
    }

    selectBearing(degrees) {
      if (this.mode !== 'explore' || !Number.isFinite(degrees)) return;
      this.exploreBearing = normalize(degrees);
      this.render();
    }

    dragDirection(event) {
      const rect = this.dial.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      if (Math.hypot(x, y) < 12) return; // No undefined jumps at the centre.
      this.selectBearing(PearlWindController.pointerBearing(x, y));
    }

    keyDirection(event) {
      if (this.mode !== 'explore') return;
      const steps = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 15, PageDown: -15 };
      let value;
      if (event.key in steps) value = this.exploreBearing + steps[event.key];
      else if (event.key === 'Home') value = 0;
      else if (event.key === 'End') value = 359;
      else return;
      event.preventDefault();
      event.stopPropagation();
      this.selectBearing(value);
    }

    render() {
      const explore = this.mode === 'explore';
      const age = this.observationAge();
      let status = this.checking ? 'loading' : this.status;
      if (!explore && status === 'live' && (age === null || age < -120)) status = 'unavailable';
      if (!explore && status === 'live' && age >= this.config.staleSeconds) status = 'stale';
      const bearing = explore ? this.exploreBearing : this.lastObservation?.direction_deg;
      setText(this.toggle, explore ? 'Back to Live' : 'Explore');
      this.toggle.setAttribute('aria-expanded', String(explore));
      const controlsChanged = this.controls.hidden === explore;
      this.controls.hidden = !explore;
      this.intro.dataset.status = explore ? 'explore' : status;
      document.querySelector('.map-page').dataset.windMode = this.mode;
      if (explore) {
        setText(this.stateText, 'EXPLORE');
        setText(this.reading, `${whole(bearing)}° · ${compass(bearing)}`);
        setText(this.ageText, 'Hypothetical wind direction');
        this.dial.style.setProperty('--bearing', `${bearing}deg`);
        this.dial.setAttribute('aria-valuenow', String(whole(bearing)));
        const spoken = `${whole(bearing)} degrees, ${compass(bearing)}, wind from`;
        this.dial.setAttribute('aria-valuetext', spoken);
        this.slider.setAttribute('aria-valuetext', spoken);
        this.slider.value = String(bearing);
      } else {
        setText(this.stateText, { live: 'PEARL LIVE', stale: 'PEARL STALE', unavailable: 'PEARL UNAVAILABLE', loading: 'PEARL · CONNECTING' }[status]);
        const observation = this.lastObservation;
        const speed = observation ? observation.speed_kts.toFixed(1).replace(/\.0$/, '') : '';
        setText(this.reading, observation ? `From ${whole(bearing)}° ${compass(bearing)} · ${speed} kt` : status === 'loading' ? 'Loading observation…' : 'Observation unavailable');
        setText(this.ageText, status === 'loading' ? 'Checking latest Pearl measurement…' : observation
          ? `Observed ${this.ageLabel(Math.max(0, age))}${status === 'stale' ? ' · stale' : status === 'unavailable' ? ' · update unavailable' : ''}`
          : 'Explore any hypothetical direction.');
      }
      if (this.wind) {
        const enabled = explore || status === 'live';
        if (enabled && bearing !== this.wind.bearing) this.wind.setBearing(bearing, { reseed: !explore });
        this.wind.setEnabled(enabled);
      }
      if (controlsChanged) document.dispatchEvent(new Event('windmaplayout'));
    }

    pauseRequests() {
      clearTimeout(this.pollTimer);
      clearInterval(this.ageTimer);
      this.pollTimer = this.ageTimer = null;
      this.requestId++;
      this.inflight?.abort();
      this.inflight = null;
    }

    startUpdates() {
      if (this.mode !== 'live' || document.hidden || this.pageHidden) return;
      if (this.ageTimer === null) this.ageTimer = setInterval(() => this.render(), 1000);
      this.poll();
    }

    async poll() {
      if (this.inflight || this.mode !== 'live' || document.hidden || this.pageHidden) return;
      clearTimeout(this.pollTimer);
      const requestId = ++this.requestId;
      const controller = new AbortController();
      this.inflight = controller;
      const began = performance.now();
      const timeout = setTimeout(() => controller.abort(), 25000);
      try {
        const response = await fetch(this.config.observationUrl, { cache: 'no-store', signal: controller.signal });
        const data = await response.json();
        if (requestId !== this.requestId) return;
        if (!['live', 'stale', 'unavailable'].includes(data.status) || !Number.isFinite(Date.parse(data.server_time))) throw new Error('Invalid observation response');
        if (!response.ok && data.status !== 'unavailable') throw new Error('Observation request failed');
        const observation = data.observation;
        if (data.status !== 'unavailable') {
          if (!observation || observation.station !== 'pearl' || !Number.isFinite(observation.direction_deg) || observation.direction_deg < 0 || observation.direction_deg >= 360
              || !Number.isFinite(observation.speed_kts) || observation.speed_kts < 0 || !Number.isFinite(Date.parse(observation.observed_at))
              || Date.parse(observation.observed_at) > Date.parse(data.server_time) + 120000) throw new Error('Invalid Pearl measurement');
          this.lastObservation = observation;
        }
        // Include request duration conservatively; never give network transit
        // time to an old observation as extra freshness.
        this.serverEpoch = Date.parse(data.server_time) + performance.now() - began;
        this.receivedAt = performance.now();
        this.receivedWall = Date.now();
        this.status = data.status;
      } catch (_) {
        if (requestId !== this.requestId) return;
        this.status = 'unavailable';
      } finally {
        clearTimeout(timeout);
        if (requestId === this.requestId) {
          this.inflight = null;
          this.checking = false;
          this.render();
          if (this.mode === 'live' && !document.hidden && !this.pageHidden) this.pollTimer = setTimeout(() => this.poll(), this.config.pollSeconds * 1000);
        }
      }
    }
  }
  window.PearlWindController = PearlWindController;
})();
