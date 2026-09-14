// No packages: node --test tests/wind_animation.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const source = readFileSync('app/static/wind-map/wind.js', 'utf8');

function emitter(extra = {}) {
  const events = new Map();
  const target = {
    ...extra,
    on(names, fn) { for (const name of names.split(' ')) { if (!events.has(name)) events.set(name, new Set()); events.get(name).add(fn); } },
    off(names, fn) { for (const name of names.split(' ')) events.get(name)?.delete(fn); },
    emit(name) { for (const fn of events.get(name) || []) fn(); },
  };
  target.addEventListener = target.on;
  target.removeEventListener = target.off;
  return target;
}

function harness(reduced = false, width = 390, height = 690) {
  const frames = new Map();
  let id = 0, strokes = 0;
  const ctx = { setTransform() {}, clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() { strokes++; } };
  const canvas = { dataset: {}, style: {}, setAttribute() {}, getContext: () => ctx, remove() {} };
  const document = emitter({ hidden: false, createElement: () => canvas });
  const motion = emitter({ matches: reduced });
  const window = emitter({ devicePixelRatio: 3, matchMedia: () => motion });
  const pane = { style: {}, append() {} };
  const map = emitter({ size: { x: width, y: height }, getSize() { return this.size; },
    getPane: () => pane, containerPointToLayerPoint: () => ({ x: 0, y: 0 }) });
  vm.runInNewContext(source, { window, document, requestAnimationFrame: fn => { frames.set(++id, fn); return id; },
    cancelAnimationFrame: key => frames.delete(key) });
  const wind = new window.PearlWindOverlay(map, 45);
  return { wind, canvas, map, motion, window, document, frames, get strokes() { return strokes; },
    frame(timestamp) { const pending = [...frames.entries()]; for (const [key, fn] of pending) { frames.delete(key); fn(timestamp); } } };
}

function close(actual, expected) { assert.ok(Math.abs(actual - expected) < 1e-7, `${actual} != ${expected}`); }

test('meteorological FROM bearings travel to the reciprocal, including north wrap', () => {
  const h = harness();
  for (const [from, x, y] of [[0, 0, 1], [90, -1, 0], [180, 0, -1], [270, 1, 0],
                             [360, 0, 1], [45, -Math.SQRT1_2, Math.SQRT1_2]]) {
    const vector = h.wind.constructor.directionVector(from);
    close(vector.x, x); close(vector.y, y);
  }
  assert.throws(() => h.wind.setBearing(NaN));
  h.wind.setBearing(-1);
  assert.equal(h.canvas.dataset.from, 359);
  assert.equal(h.canvas.dataset.toward, 179);
});

test('60 Hz and 120 Hz clocks produce the same illustrative speed and one RAF chain', () => {
  function run(hz) {
    const h = harness(false, 1000, 1000);
    h.wind.particles = [{ x: 500, y: 100, age: 2, life: 10, length: 25 }];
    for (let i = 1; i <= hz; i++) { h.frame(i * 1000 / hz); assert.equal(h.frames.size, 1); }
    return h.wind.particles[0];
  }
  const normal = run(60), promotion = run(120);
  close(normal.x, promotion.x); close(normal.y, promotion.y);
  close(500 - normal.x, 28 * Math.SQRT1_2);
  close(normal.y - 100, 28 * Math.SQRT1_2);
});

test('hidden/pagehide cancels work; visible/pageshow resumes without a catch-up jump', () => {
  const h = harness();
  h.frame(16);
  h.document.hidden = true; h.document.emit('visibilitychange');
  assert.equal(h.frames.size, 0); assert.equal(h.canvas.dataset.motion, 'paused');
  h.document.hidden = false; h.document.emit('visibilitychange'); h.document.emit('visibilitychange');
  assert.equal(h.frames.size, 1);
  h.wind.particles = [{ x: 150, y: 150, age: 2, life: 10, length: 25 }];
  h.frame(60000);
  assert.ok(Math.abs(h.wind.particles[0].x - 150) < 1);
  h.window.emit('pagehide'); assert.equal(h.frames.size, 0);
  h.window.emit('pageshow'); assert.equal(h.frames.size, 1);
});

test('reduced motion has static arrows with no animation loop, including setting changes', () => {
  const h = harness(true);
  assert.equal(h.frames.size, 0); assert.ok(h.strokes > 0);
  assert.equal(h.canvas.dataset.motion, 'reduced');
  h.motion.matches = false; h.motion.emit('change'); assert.equal(h.frames.size, 1);
  h.motion.matches = true; h.motion.emit('change'); assert.equal(h.frames.size, 0);
});

test('zoom pauses/reseeds, resize caps density, and destroy removes event-driven restarts', () => {
  const h = harness();
  const initialCount = h.wind.particles.length;
  h.map.emit('zoomstart'); assert.equal(h.frames.size, 0);
  h.map.emit('zoomend'); assert.equal(h.frames.size, 1);
  h.map.size = { x: 4000, y: 2200 }; h.map.emit('resize');
  assert.ok(h.wind.particles.length > initialCount && h.wind.particles.length <= 220);
  assert.ok(h.canvas.dataset.pixelRatio <= 1.5);
  assert.ok(h.canvas.width * h.canvas.height < 3_010_000);
  const oldParticles = h.wind.particles;
  h.wind.setBearing(180); assert.notEqual(h.wind.particles, oldParticles);
  h.wind.destroy(); assert.equal(h.frames.size, 0);
  h.window.emit('pageshow'); h.map.emit('zoomend'); assert.equal(h.frames.size, 0);
});

test('sustained slow rendering reduces particle count without changing bearing or speed', () => {
  const h = harness(false, 1200, 800);
  const initialCount = h.wind.particles.length;
  for (let i = 0; i < 40; i++) h.frame(i * 50);
  assert.ok(h.wind.particles.length < initialCount);
  assert.equal(h.canvas.dataset.from, 45);
  assert.equal(h.frames.size, 1);
});

test('unavailable LIVE disables animation; continuous Explore rotates without respawning', () => {
  const h = harness();
  h.wind.setEnabled(false);
  assert.equal(h.frames.size, 0);
  h.document.emit('visibilitychange');
  assert.equal(h.frames.size, 0);
  h.wind.setEnabled(true);
  assert.equal(h.frames.size, 1);
  const particles = h.wind.particles;
  h.wind.setBearing(359.5, { reseed: false });
  h.wind.setBearing(.5, { reseed: false });
  assert.equal(h.wind.particles, particles);
  close(h.wind.vector.x, -Math.sin(.5 * Math.PI / 180));
  assert.equal(h.frames.size, 1);
});
