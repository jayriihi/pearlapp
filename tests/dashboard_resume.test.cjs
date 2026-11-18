// Run with node --test tests/dashboard_resume.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

const template = readFileSync('app/templates/wind_tide_dir.html', 'utf8');
const source = template.match(/<script>\s*(\(function\(\) \{\s*const refreshAfterMs[\s\S]*?)<\/script>/)[1];

function harness(initialVisibility = 'visible') {
  let now = 1000;
  let refreshes = 0;
  function emitter(extra = {}) {
    const handlers = new Map();
    return { ...extra,
      addEventListener(name, callback) {
        if (!handlers.has(name)) handlers.set(name, []);
        handlers.get(name).push(callback);
      },
      emit(name, event = {}) {
        for (const callback of handlers.get(name) || []) callback(event);
      },
    };
  }
  const document = emitter({ visibilityState: initialVisibility });
  const window = emitter({ refreshPearlPage: () => refreshes++ });
  // No timer APIs supplied: the script must be entirely event-driven.
  vm.runInNewContext(source, { document, window, Date: { now: () => now } });
  return {
    window, document,
    advance(ms) { now += ms; },
    visibility(state) { document.visibilityState = state; document.emit('visibilitychange'); },
    get refreshes() { return refreshes; },
  };
}

test('short and exactly 60-second absences do not refresh; longer absences do', () => {
  for (const [duration, expected] of [[10000, 0], [60000, 0], [60001, 1]]) {
    const h = harness();
    h.window.emit('pageshow', { persisted: false });
    h.visibility('hidden');
    h.advance(duration);
    h.visibility('visible');
    assert.equal(h.refreshes, expected);
  }
});

test('subsequent pagehide and hidden events preserve the first hidden time', () => {
  const h = harness();
  h.visibility('hidden');
  h.advance(40000);
  h.window.emit('pagehide');
  h.visibility('hidden');
  h.advance(21000);
  h.visibility('visible');
  assert.equal(h.refreshes, 1);
});

test('every pageshow checks a recorded absence, including non-persisted restoration', () => {
  for (const persisted of [false, true]) {
    const h = harness();
    h.window.emit('pagehide');
    h.advance(61000);
    h.window.emit('pageshow', { persisted });
    assert.equal(h.refreshes, 1);
  }
});

test('focus checks a recorded absence and waits until the page is visible', () => {
  const h = harness();
  h.visibility('hidden');
  h.advance(61000);
  h.window.emit('focus');
  assert.equal(h.refreshes, 0);
  h.document.visibilityState = 'visible';
  h.window.emit('focus');
  assert.equal(h.refreshes, 1);
});

test('missing hidden timestamps use initialization age on actual resume signals', () => {
  for (const signal of ['visibility', 'persisted-pageshow', 'later-pageshow']) {
    for (const [duration, expected] of [[10000, 0], [61000, 1]]) {
      const h = harness();
      h.window.emit('pageshow', { persisted: false });
      h.advance(duration);
      if (signal === 'visibility') h.visibility('visible');
      else h.window.emit('pageshow', { persisted: signal === 'persisted-pageshow' });
      assert.equal(h.refreshes, expected, `${signal}, ${duration}`);
    }
  }
  const h = harness('hidden');
  h.advance(61000);
  h.document.visibilityState = 'visible';
  h.window.emit('focus');
  assert.equal(h.refreshes, 1);
});

test('multiple resume events trigger only one refresh', () => {
  const h = harness();
  h.window.emit('pageshow', { persisted: false });
  h.visibility('hidden');
  h.advance(61000);
  h.visibility('visible');
  h.window.emit('pageshow', { persisted: true });
  h.window.emit('focus');
  h.visibility('visible');
  assert.equal(h.refreshes, 1);
});

test('short absence on an old page stays short across repeated resume events', () => {
  const h = harness();
  h.window.emit('pageshow', { persisted: false });
  h.advance(300000);
  h.visibility('hidden');
  h.advance(10000);
  h.visibility('visible');
  h.window.emit('pageshow', { persisted: true });
  h.window.emit('focus');
  assert.equal(h.refreshes, 0);
  h.visibility('hidden');
  h.advance(61000);
  h.visibility('visible');
  assert.equal(h.refreshes, 1);
});

test('continuously visible pages do not refresh on elapsed time or focus alone', () => {
  const h = harness();
  h.advance(300000);
  h.window.emit('pageshow', { persisted: false }); // Delayed initial load.
  h.window.emit('focus');
  h.advance(300000);
  h.window.emit('focus');
  assert.equal(h.refreshes, 0);
});
