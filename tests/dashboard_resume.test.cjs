const { test } = require('node:test');
const assert = require('node:assert/strict');
const { startObservationRefresh } = require('../app/static/pearl-dashboard.js');
const FIVE = 300000;
const NOW = Date.parse('2026-11-18T11:02:00Z');
function storage() {
  const data = new Map();
  return { getItem: key => data.has(key) ? data.get(key) : null,
    setItem: (key, value) => data.set(key, value) };
}
function harness(options = {}) {
  let now = options.now ?? NOW, refreshes = 0;
  const queue = [];
  function emitter(extra) {
    const handlers = new Map();
    return { ...extra, addEventListener(name, fn) {
      if (!handlers.has(name)) handlers.set(name, []);
      handlers.get(name).push(fn);
    }, emit(name, event = {}) { for (const fn of handlers.get(name) || []) fn(event); } };
  }
  const document = emitter({ visibilityState: options.visibility || 'visible' });
  const window = emitter({ Date: { now: () => now },
    navigator: { onLine: options.online ?? true }, sessionStorage: options.storage || storage(),
    setTimeout(fn, delay) { assert.equal(delay, 0); queue.push(fn); },
    refreshPearlPage() { refreshes++; window.pearlRefreshPending = true; } });
  startObservationRefresh(window, document,
    Object.hasOwn(options, 'observation') ? options.observation : now - 40 * 60000,
    options.station || 'pearl');
  return { window, document, get refreshes() { return refreshes; },
    advance(ms) { now += ms; }, flush() { while (queue.length) queue.shift()(); },
    visibility(state) { document.visibilityState = state; document.emit('visibilitychange'); } };
}

test('initial load checks observation age: below, exactly at, and beyond five minutes', () => {
  for (const [age, expected] of [[FIVE - 1, 0], [FIVE, 1], [40 * 60000, 1]]) {
    const h = harness({ observation: NOW - age });
    h.window.emit('pageshow', { persisted: false }); h.flush();
    assert.equal(h.refreshes, expected);
  }
});
test('focus-only return works without a captured departure; short absences use observation age', () => {
  const h = harness({ observation: NOW }); h.flush(); h.advance(FIVE);
  h.window.emit('focus'); h.flush(); assert.equal(h.refreshes, 1);
  const short = harness({ observation: NOW - FIVE + 1000 }); short.flush();
  short.visibility('hidden'); short.advance(2000); short.visibility('visible'); short.flush();
  assert.equal(short.refreshes, 1);
});
test('pageshow restores both persisted and non-persisted old pages', () => {
  for (const persisted of [true, false]) {
    const h = harness({ observation: NOW }); h.flush(); h.advance(FIVE);
    h.window.emit('pageshow', { persisted }); h.flush(); assert.equal(h.refreshes, 1);
  }
});
test('overlapping and repeated lifecycle events produce one reload', () => {
  const h = harness();
  for (let i = 0; i < 3; i++) {
    h.window.emit('pageshow'); h.window.emit('focus'); h.visibility('visible');
  }
  h.flush(); h.advance(FIVE); h.window.emit('focus'); h.flush();
  assert.equal(h.refreshes, 1);
});
test('focus before visible settles correctly; hidden pages do not reload', () => {
  const h = harness({ visibility: 'hidden' }); h.flush();
  h.window.emit('focus'); h.flush(); assert.equal(h.refreshes, 0);
  h.window.emit('focus'); h.document.visibilityState = 'visible'; h.flush();
  assert.equal(h.refreshes, 1);
});
test('unchanged auto-reloaded pages cannot loop, but later foreground events can retry', () => {
  const shared = storage();
  const first = harness({ storage: shared }); first.flush(); assert.equal(first.refreshes, 1);
  const next = harness({ storage: shared, now: NOW + 1000 });
  next.window.emit('pageshow'); next.window.emit('focus'); next.flush();
  assert.equal(next.refreshes, 0);
  next.advance(FIVE - 1); next.window.emit('focus'); next.flush(); assert.equal(next.refreshes, 0);
  next.advance(1); next.window.emit('focus'); next.flush(); assert.equal(next.refreshes, 1);
});
test('even a slow reload does not immediately refresh again', () => {
  const shared = storage(); const first = harness({ storage: shared }); first.flush();
  const slow = harness({ storage: shared, now: NOW + FIVE + 1000 });
  slow.window.emit('pageshow'); slow.window.emit('focus'); slow.flush();
  assert.equal(slow.refreshes, 0);
});
test('cooldowns are station scoped and survive manual navigation', () => {
  const shared = storage(); const first = harness({ storage: shared }); first.flush();
  const same = harness({ storage: shared }); same.flush(); assert.equal(same.refreshes, 0);
  const other = harness({ storage: shared, station: 'nmb' }); other.flush(); assert.equal(other.refreshes, 1);
});
test('offline skips reload; online checks again using the same guards', () => {
  const h = harness({ online: false }); h.flush(); assert.equal(h.refreshes, 0);
  h.window.navigator.onLine = true; h.window.emit('online'); h.flush();
  assert.equal(h.refreshes, 1);
});
test('missing or invalid timestamps get one bounded recovery attempt; future values do not loop', () => {
  for (const observation of [null, undefined, NaN, 'bad']) {
    const shared = storage(); const h = harness({ observation, storage: shared }); h.flush();
    assert.equal(h.refreshes, 1);
    const next = harness({ observation, storage: shared }); next.flush(); assert.equal(next.refreshes, 0);
  }
  const future = harness({ observation: NOW + FIVE }); future.flush(); assert.equal(future.refreshes, 0);
});
test('blocked, full, corrupt or silently failing storage fails safely without a reload', () => {
  const cases = [
    { getItem() { throw Error('blocked'); } },
    { getItem() { return null; }, setItem() { throw Error('quota'); } },
    { getItem() { return '{broken'; } },
    { getItem() { return '{}'; } },
    { getItem() { return null; }, setItem() {} },
  ];
  for (const shared of cases) {
    const h = harness({ storage: shared }); h.flush(); h.window.emit('focus'); h.flush();
    assert.equal(h.refreshes, 0); h.window.refreshPearlPage(); assert.equal(h.refreshes, 1);
  }
});
test('manual refresh bypasses cooldown and overlapping automatic checks', () => {
  const shared = storage(); const first = harness({ storage: shared }); first.flush();
  const h = harness({ storage: shared }); h.flush(); h.window.refreshPearlPage();
  assert.equal(h.refreshes, 1);
  const pending = harness(); pending.window.refreshPearlPage(); pending.flush();
  assert.equal(pending.refreshes, 1);
});
test('continuously visible pages have no recurring timers or unsolicited reloads', () => {
  const h = harness({ observation: NOW }); h.flush(); h.advance(10 * FIVE); h.flush();
  assert.equal(h.refreshes, 0);
});

test('actual manual helper survives blocked storage and retains zoom and scroll normalization', () => {
  const fs = require('node:fs'), vm = require('node:vm');
  const source = fs.readFileSync('app/templates/base.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  const events = [], scrolls = [], timers = [];
  let reloads = 0;
  const viewport = { dataset: {}, getAttribute: () => 'width=device-width, initial-scale=1',
    setAttribute(_, value) { this.content = value; } };
  const context = { sessionStorage: { getItem() { throw Error('blocked'); }, setItem() { throw Error('blocked'); } },
    history: { scrollRestoration: 'auto' }, document: { querySelector: () => viewport },
    window: { addEventListener: (...args) => events.push(args), scrollTo: (...args) => scrolls.push(args),
      setTimeout: fn => timers.push(fn), location: { reload: () => reloads++ } } };
  vm.runInNewContext(source, context);
  context.window.refreshPearlPage(); context.window.refreshPearlPage();
  assert.equal(timers.length, 1); assert.ok(viewport.content.endsWith('maximum-scale=1'));
  assert.deepEqual(scrolls, [[0, 0]]); timers[0](); assert.equal(reloads, 1);
});

test('UTC epoch freshness crosses Bermuda midnight without parsing wall-clock strings', () => {
  const midnight = Date.parse('2026-11-18T04:02:00Z');
  const h = harness({ now: midnight, observation: Date.parse('2026-11-18T03:58:00Z') });
  h.flush(); assert.equal(h.refreshes, 0);
  h.advance(60000); h.window.emit('focus'); h.flush(); assert.equal(h.refreshes, 1);
});


test('retained page rereads another page’s cooldown and retries only after it expires', () => {
  const shared = storage();
  const retained = harness({ storage: shared, observation: NOW - 240000 });
  retained.flush(); retained.visibility('hidden');
  const newer = harness({ storage: shared, now: NOW + 60000 });
  newer.flush(); assert.equal(newer.refreshes, 1);
  retained.advance(60000); retained.visibility('visible');
  retained.window.emit('pageshow', { persisted: true }); retained.window.emit('focus');
  retained.flush(); assert.equal(retained.refreshes, 0);
  retained.advance(FIVE - 1); retained.window.emit('focus'); retained.flush();
  assert.equal(retained.refreshes, 0);
  retained.advance(1); retained.window.emit('focus'); retained.flush();
  assert.equal(retained.refreshes, 1);
});

test('retained page validates records and storage failures introduced after initialization', () => {
  for (const invalid of ['{broken', '{}', '{"attemptedAt":0,"retryAfter":"bad"}']) {
    const shared = storage();
    const h = harness({ storage: shared, observation: NOW }); h.flush();
    shared.setItem('pearl_auto_refresh:pearl', invalid);
    h.advance(FIVE); h.window.emit('focus'); h.flush(); assert.equal(h.refreshes, 0);
    h.window.refreshPearlPage(); assert.equal(h.refreshes, 1);
  }
  const shared = storage(); const h = harness({ storage: shared, observation: NOW }); h.flush();
  shared.getItem = () => { throw Error('storage became unavailable'); };
  h.advance(FIVE); h.window.emit('focus'); h.flush(); assert.equal(h.refreshes, 0);
});
