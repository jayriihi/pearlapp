(function(root) {
  'use strict';
  const FIVE_MINUTES = 5 * 60 * 1000;

  function startObservationRefresh(window, document, observationMs, stationKey) {
    const storageKey = 'pearl_auto_refresh:' + stationKey;
    let pending = false;
    let scheduled = false;
    let storage;
    let record = null;
    let storageAvailable = true;

    function readRecord() {
      const encoded = storage.getItem(storageKey);
      if (encoded === null) return null;
      const current = JSON.parse(encoded);
      if (!current || !Number.isFinite(current.attemptedAt) ||
          !Number.isFinite(current.retryAfter)) throw new Error('Invalid refresh record');
      return current;
    }

    // Persist before reloading: an unchanged response must not reload itself.
    function save(next) {
      try {
        const encoded = JSON.stringify(next);
        storage.setItem(storageKey, encoded);
        if (storage.getItem(storageKey) !== encoded) throw new Error('Storage unavailable');
        record = next;
        return true;
      } catch (_) {
        storageAvailable = false;
        return false;
      }
    }

    try {
      storage = window.sessionStorage;
      record = readRecord();
      if (record !== null) {
        if (record.awaitingResult) {
          // Also cover a slow reload or a cached response with the same observation.
          save({ attemptedAt: record.attemptedAt,
                 retryAfter: Math.max(record.retryAfter, window.Date.now() + FIVE_MINUTES),
                 awaitingResult: false });
        }
      }
    } catch (_) {
      // Manual refresh remains available when storage is blocked or corrupt.
      storageAvailable = false;
    }

    function check() {
      scheduled = false;
      if (pending || window.pearlRefreshPending || !storageAvailable ||
          document.visibilityState !== 'visible' || window.navigator.onLine === false) return;
      const now = window.Date.now();
      if (Number.isFinite(observationMs) && now - observationMs < FIVE_MINUTES) return;
      // A retained document may predate an attempt made by another page.
      try {
        record = readRecord();
      } catch (_) {
        storageAvailable = false;
        return;
      }
      if (record && now < record.retryAfter) return;
      if (!save({ attemptedAt: now, retryAfter: now + FIVE_MINUTES, awaitingResult: true })) return;
      pending = true;
      window.refreshPearlPage();
    }

    function scheduleCheck() {
      if (scheduled || pending) return;
      scheduled = true;
      // One deferred check lets iOS settle visibility and coalesces event bursts.
      window.setTimeout(check, 0);
    }
    document.addEventListener('visibilitychange', function() {
      if (document.visibilityState === 'visible') scheduleCheck();
    });
    window.addEventListener('pageshow', scheduleCheck);
    window.addEventListener('focus', scheduleCheck);
    window.addEventListener('online', scheduleCheck);
    scheduleCheck();
  }

  function selectWindTickIndices(labels, width, measureText, maxTicks) {
    if (!labels.length) return [];
    const last = labels.length - 1;
    if (!last) return [0];
    const labelWidth = Math.max(...labels.map(label => measureText(String(label))));
    // Reserve room for the right-aligned endpoint and its centered neighbour.
    const gap = 1.5 * labelWidth + 12;
    const step = Math.max(1, Math.ceil(gap * last / Math.max(1, width)),
                          Math.ceil(last / Math.max(1, maxTicks - 1)));
    const indices = [];
    for (let index = last; index >= 0; index -= step) indices.push(index);
    return indices.reverse();
  }

  const api = { startObservationRefresh, selectWindTickIndices };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PearlDashboard = api;
})(typeof window === 'undefined' ? globalThis : window);
