const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const dashboard = require('../app/static/pearl-dashboard.js');
const template = readFileSync('app/templates/wind_tide_dir.html', 'utf8');
const source = template.match(/<script>\s*(\/\/ palette[\s\S]*?)<\/script>/)[1];
function chart(hours, count, suppliedLabels) {
  const labels = suppliedLabels || Array.from({ length: count }, (_, i) => `${String(Math.floor(i / 12)).padStart(2, '0')}:${String(i % 12 * 5).padStart(2, '0')}`);
  let config;
  function Chart(_, options) { config = options; }
  Chart.helpers = { toFont: () => ({ string: '12px Arial' }) }; Chart.defaults = { font: {} };
  const script = source.replace(/{{ H }}/g, hours).replace(/{{ \(H >= 3\) \| tojson }}/g, String(hours >= 3))
    .replace(/{{ labels \| default\(\[\]\) \| tojson }}/g, JSON.stringify(labels))
    .replace(/{{ values \| default\(\[\]\) \| tojson }}/g, JSON.stringify(labels.map(() => 10)));
  vm.runInNewContext(script, { Chart, PearlDashboard: dashboard, windAvailable: true, DPR: 1,
    document: { documentElement: {}, getElementById: () => ({ style: {} }) },
    getComputedStyle: () => ({ getPropertyValue: () => '#fff' }) });
  return { config, labels };
}
test('real chart configuration labels the final observation for every range and point count', () => {
  for (const hours of [1, 3, 8]) for (const count of [0, 1, 2, 12, 13, 14, 37, 38, 97, 98]) {
    const { config, labels } = chart(hours, count);
    const x = config.options.scales.x;
    assert.equal(x.type, 'category'); assert.equal(x.ticks.autoSkip, false);
    for (const width of [160, 240, 320, 375, 430, 800]) {
      const available = Math.max(0, width - 80);
      const scale = { width, chart: { width, ctx: { save() {}, restore() {}, measureText: text => ({ width: text.length * 7 }) } },
        options: { ticks: { font: {} } }, ticks: [] };
      x.afterBuildTicks(scale);
      const indices = Array.from(scale.ticks, tick => tick.value);
      if (!count) { assert.deepEqual(indices, []); continue; }
      assert.equal(indices.at(-1), count - 1);
      assert.equal(x.ticks.callback.call({ getLabelForValue: value => labels[value] }, count - 1), labels.at(-1));
      if (hours === 1) {
        const expected = Array.from({ length: count }, (_, i) => i)
          .filter(i => (count - 1 - i) % 2 === 0);
        assert.deepEqual(indices, expected);
        assert.equal(x.ticks.minRotation, 50);
        assert.equal(x.ticks.maxRotation, 50);
        continue;
      }
      assert.equal(x.ticks.minRotation, 0);
      assert.equal(x.ticks.maxRotation, 0);
      assert.ok(indices.length <= 12);
      for (let i = 1; i < indices.length; i++) {
        const pixelGap = (indices[i] - indices[i - 1]) / (count - 1) * available;
        assert.ok(pixelGap >= 1.5 * 35 + 12, `${hours}h/${count}/${width}: overlapping ticks`);
      }
    }
  }
});
test('resize and orientation changes recalculate density while preserving the endpoint', () => {
  const labels = Array(98).fill('20:06');
  const narrow = dashboard.selectWindTickIndices(labels, 160, () => 35, 12);
  const wide = dashboard.selectWindTickIndices(labels, 900, () => 35, 12);
  assert.ok(wide.length > narrow.length);
  assert.equal(wide.at(-1), 97); assert.equal(narrow.at(-1), 97);
});


test('one-hour ticks retain real irregular timestamps and count backward from the latest reading', () => {
  const labels = ['11:01', '11:06', '11:16', '11:21', '11:26', '11:31'];
  const { config } = chart(1, labels.length, labels);
  const x = config.options.scales.x;
  const scale = { ticks: [] };
  x.afterBuildTicks(scale);
  assert.deepEqual(Array.from(scale.ticks, tick => tick.value), [1, 3, 5]);
  const displayed = Array.from(scale.ticks, tick =>
    x.ticks.callback.call({ getLabelForValue: index => labels[index] }, tick.value));
  assert.deepEqual(displayed, ['11:06', '11:21', '11:31']);
});
