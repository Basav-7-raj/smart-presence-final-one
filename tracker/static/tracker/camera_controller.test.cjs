'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const CameraController = require('./camera_controller.js');

function harness(options = {}) {
  const timers = new Map();
  let timerId = 0;
  const diagnostics = [];
  const errors = [];
  const results = [];
  const states = [];
  const tracks = [];
  let getUserMediaCalls = 0;
  let fetchCalls = 0;
  let fetchImpl = options.fetch || (async () => ({
    ok: true, status: 200,
    json: async () => ({ status: 'success', face_count: 0, results: [] })
  }));
  const mediaListeners = new Map();
  const mediaDevices = {
    getUserMedia: async () => {
      getUserMediaCalls += 1;
      if (options.getUserMedia) return options.getUserMedia(tracks);
      const trackListeners = new Map();
      const track = {
        readyState: 'live',
        stopped: false,
        addEventListener(name, callback) { trackListeners.set(name, callback); },
        getSettings() { return { deviceId: 'mock-camera' }; },
        stop() { this.stopped = true; this.readyState = 'ended'; }
      };
      track.fire = (name) => { const callback = trackListeners.get(name); if (callback) callback(); };
      tracks.push(track);
      return { getTracks: () => [track], getVideoTracks: () => [track] };
    },
    addEventListener(name, callback) { mediaListeners.set(name, callback); },
    removeEventListener(name) { mediaListeners.delete(name); },
    async enumerateDevices() { return [{ kind: 'videoinput', deviceId: 'mock-camera' }]; },
    fire(name) { const callback = mediaListeners.get(name); if (callback) callback(); }
  };
  const videoListeners = new Map();
  const video = {
    readyState: 4, videoWidth: 640, videoHeight: 480, srcObject: null,
    addEventListener(name, callback) { videoListeners.set(name, callback); },
    removeEventListener(name) { videoListeners.delete(name); },
    async play() {
      if (options.play) await options.play();
      this.videoWidth = 640; this.videoHeight = 480;
    },
    pause() {},
    fire(name) { const callback = videoListeners.get(name); if (callback) callback(); }
  };
  const canvas = {
    width: 0, height: 0,
    getContext() { return { drawImage() {} }; },
    toBlob(callback) { callback({ mockFrame: true }); }
  };
  const controller = new CameraController({
    mediaDevices, video, canvas,
    fetch: async (...args) => { fetchCalls += 1; return fetchImpl(...args); },
    getCsrfToken: () => options.csrf === undefined ? 'test-csrf' : options.csrf,
    isSecureContext: () => options.secure !== false,
    setTimeout: (callback, delay) => {
      const id = ++timerId; timers.set(id, { callback, delay }); return id;
    },
    clearTimeout: (id) => timers.delete(id),
    onState: (state, message) => states.push({ state, message }),
    onResults: (body) => results.push(body),
    onRecognitionError: (message) => errors.push(message),
    onDiagnostic: (code, message) => diagnostics.push({ code, message })
  });
  async function flush() {
    for (let i = 0; i < 8; i += 1) await Promise.resolve();
  }
  async function runTimer() {
    const entry = timers.entries().next().value;
    if (!entry) return false;
    timers.delete(entry[0]);
    entry[1].callback();
    await flush();
    return true;
  }
  return {
    controller, timers, diagnostics, errors, results, states, tracks, video, mediaDevices,
    getUserMediaCalls: () => getUserMediaCalls,
    fetchCalls: () => fetchCalls,
    flush, runTimer
  };
}

test('camera starts only on explicit start and repeated start calls do not acquire duplicate streams', async () => {
  const h = harness();
  assert.equal(h.controller.state, 'IDLE');
  assert.equal(h.getUserMediaCalls(), 0);
  await h.controller.start();
  await h.flush();
  await h.controller.start();
  await h.flush();
  assert.equal(h.getUserMediaCalls(), 1);
  assert.equal(h.controller.state, 'RUNNING');
  assert.ok(h.timers.size <= 1);
  h.controller.dispose();
});

test('three start/stop cycles stop every stream and keep at most one scan timer', async () => {
  const h = harness();
  for (let cycle = 0; cycle < 3; cycle += 1) {
    await h.controller.start();
    await h.flush();
    assert.equal(h.controller.state, 'RUNNING');
    assert.ok(h.timers.size <= 1);
    h.controller.stop();
    assert.equal(h.controller.state, 'IDLE');
    assert.equal(h.tracks[cycle].stopped, true);
    assert.equal(h.timers.size, 0);
  }
  assert.equal(h.getUserMediaCalls(), 3);
  assert.ok(h.fetchCalls() <= 3);
  h.controller.dispose();
});

test('playback failure releases the stream acquired before video.play rejects', async () => {
  const h = harness({ play: async () => { throw new Error('mock playback failure'); } });
  await h.controller.start();
  assert.equal(h.controller.state, 'ERROR');
  assert.equal(h.tracks[0].stopped, true);
  assert.equal(h.video.srcObject, null);
  h.controller.dispose();
});

for (const status of [403, 404, 500]) {
  test('recognition HTTP ' + status + ' is surfaced instead of being treated as success', async () => {
    const h = harness({ fetch: async () => ({
      ok: false, status,
      json: async () => status === 500 ? { status: 'error', message: 'Model unavailable.' } : { status: 'error' }
    }) });
    await h.controller.start();
    await h.flush();
    assert.match(h.errors.join(' '), new RegExp(String(status) + '|CSRF|forbidden|Model unavailable', 'i'));
    assert.equal(h.results.length, 0);
    assert.ok(h.timers.size <= 1);
    h.controller.dispose();
  });
}

test('denied camera permission transitions to ERROR with a helpful message', async () => {
  const h = harness({
    getUserMedia: async () => {
      const error = new Error('permission denied');
      error.name = 'NotAllowedError';
      throw error;
    }
  });
  await h.controller.start();
  assert.equal(h.controller.state, 'ERROR');
  assert.match(h.states[h.states.length - 1].message, /permission was denied/i);
  assert.equal(h.tracks.length, 0);
  h.controller.dispose();
});

test('stopping while permission is pending releases a late-arriving stream', async () => {
  let resolveMedia;
  const h = harness({ getUserMedia: () => new Promise((resolve) => { resolveMedia = resolve; }) });
  const starting = h.controller.start();
  h.controller.stop();
  const track = {
    readyState: 'live', stopped: false,
    addEventListener() {},
    stop() { this.stopped = true; this.readyState = 'ended'; }
  };
  resolveMedia({ getTracks: () => [track], getVideoTracks: () => [track] });
  await starting;
  assert.equal(h.controller.state, 'IDLE');
  assert.equal(track.stopped, true);
  assert.equal(h.fetchCalls(), 0);
  h.controller.dispose();
});

test('stopping while recognition is pending prevents later frame submissions', async () => {
  let resolveFetch;
  const h = harness({ fetch: () => new Promise((resolve) => { resolveFetch = resolve; }) });
  await h.controller.start();
  await h.flush();
  assert.equal(h.fetchCalls(), 1);
  h.controller.stop();
  resolveFetch({ ok: true, status: 200, json: async () => ({ status: 'success', face_count: 0, results: [] }) });
  await h.flush();
  assert.equal(h.fetchCalls(), 1);
  assert.equal(h.timers.size, 0);
  h.controller.dispose();
});

test('a missing CSRF token produces a visible request error and sends no frame', async () => {
  const h = harness({ csrf: '' });
  await h.controller.start();
  await h.flush();
  assert.match(h.errors.join(' '), /CSRF/i);
  assert.equal(h.fetchCalls(), 0);
  h.controller.dispose();
});

test('camera track ending transitions to ERROR and stops remaining resources', async () => {
  const h = harness();
  await h.controller.start();
  await h.flush();
  h.tracks[0].fire('ended');
  assert.equal(h.controller.state, 'ERROR');
  assert.equal(h.tracks[0].stopped, true);
  assert.equal(h.timers.size, 0);
  h.controller.dispose();
});
