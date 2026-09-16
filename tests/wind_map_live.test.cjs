// No packages: node --test tests/wind_map_live.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

const source = readFileSync('app/static/wind-map/live.js', 'utf8');

function emitter(extra = {}) {
  const events = new Map();
  return {
    ...extra,
    addEventListener(name, fn) {
      if (!events.has(name)) events.set(name, []);
      events.get(name).push(fn);
    },
    emit(name, event = {}) {
      for (const fn of events.get(name) || []) fn(event);
    },
  };
}

function node(extra = {}) {
  return emitter({
    textContent: '', hidden: false, dataset: {}, value: '0',
    style: { setProperty() {} },
    setAttribute() {}, hasPointerCapture: () => false,
    ...extra,
  });
}

function harness(gtag) {
  const elements = {
    'wind-mode-toggle': node(),
    'explore-controls': node({ hidden: true }),
    'direction-dial': node(),
    'direction-range': node(),
    'wind-state': node(),
    'wind-reading': node(),
    'wind-age': node(),
  };
  const intro = node();
  const page = node();
  const document = emitter({
    hidden: true,
    getElementById: id => elements[id],
    querySelector: selector => selector === '.map-intro' ? intro : page,
    dispatchEvent() {},
  });
  const window = emitter({ gtag });
  const context = {
    window, document,
    performance: { now: () => 0 },
    Date, Event: class {}, AbortController,
    setTimeout: () => 1, clearTimeout() {},
    setInterval: () => 1, clearInterval() {},
  };
  vm.runInNewContext(source, context);
  const controller = new window.PearlWindController({ pollSeconds: 60, staleSeconds: 360 });
  return { controller, elements };
}

test('LIVE and EXPLORE transitions emit only the two intended GA4 events', () => {
  const calls = [];
  const h = harness((...args) => calls.push(args));
  h.controller.enterExplore();
  h.controller.enterExplore();
  h.controller.enterLive();
  h.controller.enterLive();
  assert.deepEqual(calls, [
    ['event', 'wind_map_explore_open'],
    ['event', 'wind_map_live_return'],
  ]);
});

test('missing or failing analytics cannot break wind-map mode changes', () => {
  const missing = harness(undefined);
  missing.controller.enterExplore();
  assert.equal(missing.controller.mode, 'explore');
  assert.equal(missing.elements['explore-controls'].hidden, false);
  missing.controller.enterLive();
  assert.equal(missing.controller.mode, 'live');

  const blocked = harness(() => { throw new Error('blocked'); });
  blocked.controller.enterExplore();
  assert.equal(blocked.controller.mode, 'explore');
  blocked.controller.enterLive();
  assert.equal(blocked.controller.mode, 'live');
});
