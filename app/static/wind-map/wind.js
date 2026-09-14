/* Uniform, illustrative wind. No observations or spatial wind-speed model. */
(() => {
  'use strict';
  const SPEED_PX_PER_SECOND = 28; // Display speed, deliberately unrelated to knots.
  const MAX_DPR = 1.5;
  const MIN_PARTICLES = 32, MAX_PARTICLES = 220;
  // Exact wind-series AQUA from wind_tide_dir.html (--aqua), kept local so this
  // isolated prototype does not require dashboard CSS or template changes.
  const WIND_SERIES_COLOR = '#00e1d1';

  class PearlWindOverlay {
    static directionVector(fromDegrees) {
      if (!Number.isFinite(fromDegrees)) throw new TypeError('Wind bearing must be finite');
      const radians = fromDegrees * Math.PI / 180;
      // Bearing is FROM true north. Canvas y increases downward, so a northerly
      // moves down; an easterly moves left. NE (45°) flows SW (225°).
      return { x: -Math.sin(radians), y: Math.cos(radians) };
    }

    constructor(map, fromDegrees) {
      this.map = map;
      this.canvas = document.createElement('canvas');
      this.canvas.className = 'wind-canvas';
      this.canvas.setAttribute('aria-hidden', 'true');
      this.context = this.canvas.getContext('2d');
      if (!this.context) throw new Error('Canvas is unavailable');
      const pane = map.getPane('windParticles') || map.createPane('windParticles');
      pane.style.zIndex = 450; // Above land/roads, below the station and labels.
      pane.style.pointerEvents = 'none';
      pane.append(this.canvas);
      this.motion = window.matchMedia('(prefers-reduced-motion: reduce)');
      this.frame = null;
      this.previous = null;
      this.zooming = false;
      this.suspended = false;
      this.destroyed = false;
      this.enabled = true;
      this.slowFrames = 0;
      this.quality = 1;
      this.particles = [];
      this.tick = this.tick.bind(this);
      this.onVisibility = () => this.refresh();
      this.onPageHide = () => { this.suspended = true; this.refresh(); };
      this.onPageShow = () => { this.suspended = false; this.resize(); this.refresh(); };
      this.onMotion = () => { this.reset(); this.refresh(); };
      this.onResize = () => this.resize();
      this.onMovementBoundary = () => this.reset();
      this.onMove = () => this.position();
      this.onZoomStart = () => { this.zooming = true; this.refresh(); };
      this.onZoomEnd = () => { this.zooming = false; this.reset(); this.refresh(); };
      this.onRemove = () => this.destroy();
      document.addEventListener('visibilitychange', this.onVisibility);
      window.addEventListener('pagehide', this.onPageHide);
      window.addEventListener('pageshow', this.onPageShow);
      this.motion.addEventListener('change', this.onMotion);
      map.on('resize', this.onResize);
      map.on('movestart moveend', this.onMovementBoundary);
      map.on('move', this.onMove);
      map.on('zoomstart', this.onZoomStart);
      map.on('zoomend', this.onZoomEnd);
      map.on('unload', this.onRemove);
      this.setBearing(fromDegrees);
      this.resize();
    }

    setBearing(fromDegrees, { reseed = true } = {}) {
      this.vector = PearlWindOverlay.directionVector(fromDegrees);
      this.bearing = ((fromDegrees % 360) + 360) % 360;
      this.canvas.dataset.from = this.bearing;
      this.canvas.dataset.toward = (this.bearing + 180) % 360;
      // Every draw clears the canvas, so dial changes can rotate existing trails
      // without respawning particles on every pointer event (which would flicker).
      if (reseed) this.reset();
      else if (this.motion.matches && this.enabled && !document.hidden && !this.suspended && !this.zooming) this.draw(0, true);
    }

    setEnabled(enabled) {
      if (this.enabled === enabled) return;
      this.enabled = enabled;
      if (enabled) this.reset();
      this.refresh();
    }

    resize() {
      if (this.destroyed) return;
      const { x, y } = this.map.getSize();
      this.width = x;
      this.height = y;
      // Also cap total backing pixels for large desktop windows.
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR, Math.sqrt(3_000_000 / Math.max(1, x * y)));
      this.canvas.width = Math.max(1, Math.round(x * dpr));
      this.canvas.height = Math.max(1, Math.round(y * dpr));
      this.canvas.style.width = `${x}px`;
      this.canvas.style.height = `${y}px`;
      this.context.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.canvas.dataset.pixelRatio = dpr;
      this.position();
      this.reset();
      this.refresh();
    }

    position() {
      // The uniform field is screen-space, with north always up. Cancel the
      // map pane's pan offset using Leaflet's public coordinate conversion.
      const origin = this.map.containerPointToLayerPoint([0, 0]);
      this.canvas.style.transform = `translate(${origin.x}px, ${origin.y}px)`;
    }

    seed(particle, initial = false) {
      particle.x = Math.random() * this.width;
      particle.y = Math.random() * this.height;
      particle.life = 5 + Math.random() * 5;
      particle.age = initial ? Math.random() * particle.life : 0;
      particle.length = 18 + Math.random() * 20;
      return particle;
    }

    reset() {
      if (!this.width || !this.height || this.destroyed) return;
      const count = this.motion.matches ? MIN_PARTICLES : Math.max(MIN_PARTICLES,
        Math.round(Math.min(MAX_PARTICLES, this.width * this.height / 3300) * this.quality));
      this.particles = Array.from({ length: count }, () => this.seed({}, true));
      this.canvas.dataset.particles = count;
      this.previous = null;
      this.slowFrames = 0;
      this.context.clearRect(0, 0, this.width, this.height);
      if (this.motion.matches && this.enabled && !document.hidden && !this.suspended && !this.zooming) this.draw(0, true);
    }

    refresh() {
      if (this.frame !== null) cancelAnimationFrame(this.frame);
      this.frame = null;
      this.previous = null;
      if (this.destroyed) return;
      const paused = !this.enabled || document.hidden || this.suspended || this.zooming || !this.width || !this.height;
      this.canvas.dataset.motion = paused ? 'paused' : this.motion.matches ? 'reduced' : 'running';
      if (paused) {
        this.context.clearRect(0, 0, this.width, this.height);
      } else if (this.motion.matches) {
        this.draw(0, true);
      } else {
        this.frame = requestAnimationFrame(this.tick);
      }
    }

    tick(timestamp) {
      this.frame = null;
      if (this.destroyed || !this.enabled || document.hidden || this.suspended || this.zooming || this.motion.matches) {
        this.refresh();
        return;
      }
      const elapsed = this.previous === null ? 1000 / 60 : timestamp - this.previous;
      // At most ~60 draws/sec on ProMotion/high-refresh screens, one RAF chain.
      if (elapsed >= 1000 / 60 - 1) {
        this.previous = timestamp;
        this.slowFrames = elapsed > 40 ? this.slowFrames + 1 : Math.max(0, this.slowFrames - 1);
        if (this.slowFrames >= 30 && this.particles.length > MIN_PARTICLES) {
          this.quality *= .8;
          this.reset();
        }
        // No catch-up jump after throttling/backgrounding.
        this.draw(Math.min(elapsed / 1000, .05), false);
      }
      this.frame = requestAnimationFrame(this.tick);
    }

    draw(dt, still) {
      const ctx = this.context, { x: dx, y: dy } = this.vector;
      ctx.clearRect(0, 0, this.width, this.height);
      ctx.lineCap = 'round';
      for (let i = 0; i < this.particles.length; i++) {
        const p = this.particles[i];
        if (!still) {
          p.x += dx * SPEED_PX_PER_SECOND * dt;
          p.y += dy * SPEED_PX_PER_SECOND * dt;
          p.age += dt;
          if (p.age >= p.life || p.x < -40 || p.x > this.width + 40 || p.y < -40 || p.y > this.height + 40) this.seed(p);
        }
        const fade = still ? .65 : Math.min(1, p.age / .8, (p.life - p.age) / .8);
        const length = still ? 20 : p.length;
        ctx.beginPath();
        ctx.moveTo(p.x - dx * length, p.y - dy * length);
        ctx.lineTo(p.x, p.y);
        // A faint outline keeps the same aqua trails readable over pale land,
        // without per-particle shadows, gradients or land-dependent sampling.
        ctx.globalAlpha = .25 * fade;
        ctx.strokeStyle = '#183e49';
        ctx.lineWidth = 2.5;
        ctx.stroke();
        ctx.globalAlpha = .34 * fade;
        ctx.strokeStyle = WIND_SERIES_COLOR;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.globalAlpha = .62 * fade;
        ctx.strokeStyle = WIND_SERIES_COLOR;
        ctx.beginPath();
        ctx.moveTo(p.x - dx * 3, p.y - dy * 3);
        ctx.lineTo(p.x, p.y);
        // Occasional tiny arrowheads make the travel direction unambiguous.
        if (still || i % 4 === 0) {
          ctx.moveTo(p.x - dx * 4 - dy * 2.5, p.y - dy * 4 + dx * 2.5);
          ctx.lineTo(p.x, p.y);
          ctx.lineTo(p.x - dx * 4 + dy * 2.5, p.y - dy * 4 - dx * 2.5);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    destroy() {
      if (this.destroyed) return;
      this.destroyed = true;
      if (this.frame !== null) cancelAnimationFrame(this.frame);
      this.frame = null;
      document.removeEventListener('visibilitychange', this.onVisibility);
      window.removeEventListener('pagehide', this.onPageHide);
      window.removeEventListener('pageshow', this.onPageShow);
      this.motion.removeEventListener('change', this.onMotion);
      this.map.off('resize', this.onResize);
      this.map.off('movestart moveend', this.onMovementBoundary);
      this.map.off('move', this.onMove);
      this.map.off('zoomstart', this.onZoomStart);
      this.map.off('zoomend', this.onZoomEnd);
      this.map.off('unload', this.onRemove);
      this.canvas.remove();
    }
  }

  window.PearlWindOverlay = PearlWindOverlay;
})();
