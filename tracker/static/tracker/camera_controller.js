(function (root, factory) {
  const CameraController = factory();
  if (typeof module === 'object' && module.exports) module.exports = CameraController;
  if (root) root.SmartPresenceCameraController = CameraController;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const STATES = Object.freeze({
    IDLE: 'IDLE', STARTING: 'STARTING', RUNNING: 'RUNNING',
    STOPPING: 'STOPPING', ERROR: 'ERROR'
  });

  function cameraErrorMessage(error) {
    const name = error && error.name ? error.name : '';
    if (name === 'NotAllowedError' || name === 'SecurityError') {
      return 'Camera permission was denied. Allow camera access in the browser site settings.';
    }
    if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      return 'No camera was found. Connect or enable a webcam, then retry.';
    }
    if (name === 'NotReadableError' || name === 'TrackStartError') {
      return 'The camera is busy or unavailable. Close apps using it and retry.';
    }
    if (name === 'OverconstrainedError') {
      return 'The camera cannot satisfy the requested video settings. Try another device.';
    }
    if (name === 'AbortError') return 'Camera startup was interrupted. Try again.';
    return (name ? name + ': ' : '') + ((error && error.message) || 'Unexpected camera error.');
  }

  class CameraController {
    constructor(options) {
      const opts = options || {};
      if (!opts.mediaDevices || typeof opts.mediaDevices.getUserMedia !== 'function') {
        throw new TypeError('mediaDevices.getUserMedia is required.');
      }
      if (!opts.video || !opts.canvas || typeof opts.fetch !== 'function') {
        throw new TypeError('video, canvas and fetch are required.');
      }
      this.mediaDevices = opts.mediaDevices;
      this.video = opts.video;
      this.canvas = opts.canvas;
      this.context = this.canvas.getContext('2d');
      this.fetch = opts.fetch;
      this.getCsrfToken = opts.getCsrfToken || function () { return ''; };
      this.onState = opts.onState || function () {};
      this.onResults = opts.onResults || function () {};
      this.onRecognitionError = opts.onRecognitionError || function () {};
      this.onDiagnostic = opts.onDiagnostic || function () {};
      this.isSecureContext = opts.isSecureContext || function () { return true; };
      this.schedule = opts.setTimeout || setTimeout;
      this.cancel = opts.clearTimeout || clearTimeout;
      this.interval = opts.interval || 850;
      this.retryInterval = opts.retryInterval || 2500;
      this.state = STATES.IDLE;
      this.stream = null;
      this.timer = null;
      this.generation = 0;
      this.inflightVersion = null;
      this.requestAbort = null;
      this.disposed = false;
      this.clientId = opts.clientId || ('client-' + Math.random().toString(36).slice(2));
      this._onDeviceChange = this._onDeviceChange.bind(this);
      this._onVideoError = this._onVideoError.bind(this);
      this._onPageHide = this.dispose.bind(this);

      if (this.video.addEventListener) this.video.addEventListener('error', this._onVideoError);
      if (this.mediaDevices.addEventListener) {
        this.mediaDevices.addEventListener('devicechange', this._onDeviceChange);
      }
    }

    _setState(next, message) {
      this.state = next;
      this.onState(next, message || ('Camera · ' + next));
    }

    _isCurrent(version) {
      return !this.disposed && version === this.generation;
    }

    _clearTimer() {
      if (this.timer !== null) {
        this.cancel(this.timer);
        this.timer = null;
      }
    }

    _stopTracks() {
      const oldStream = this.stream;
      this.stream = null;
      if (oldStream) {
        oldStream.getTracks().forEach((track) => {
          try { track.stop(); }
          catch (error) { this.onDiagnostic('TRACK_STOP', error && error.name); }
        });
      }
      try { this.video.pause(); } catch (error) {
        this.onDiagnostic('VIDEO_PAUSE', error && error.name);
      }
      this.video.srcObject = null;
    }

    _abortRecognition() {
      if (this.requestAbort) {
        try { this.requestAbort.abort(); } catch (error) {
          this.onDiagnostic('REQUEST_ABORT', error && error.name);
        }
      }
      this.requestAbort = null;
    }

    _releaseLateStream(acquired) {
      acquired.getTracks().forEach((track) => {
        try { track.stop(); } catch (error) {
          this.onDiagnostic('TRACK_STOP', error && error.name);
        }
      });
    }

    _fail(error, version) {
      if (!this._isCurrent(version)) return;
      this._clearTimer();
      this._abortRecognition();
      this._stopTracks();
      this.inflightVersion = null;
      const message = cameraErrorMessage(error);
      this._setState(STATES.ERROR, 'Camera error · ' + message);
      this.onDiagnostic('CAMERA', message);
    }

    async start() {
      if (this.disposed || [STATES.STARTING, STATES.RUNNING, STATES.STOPPING].includes(this.state)) return;
      this.generation += 1;
      const version = this.generation;
      this._clearTimer();
      this._abortRecognition();
      this.inflightVersion = null;
      this._setState(STATES.STARTING, 'Requesting camera access…');
      try {
        if (!this.isSecureContext()) {
          throw new Error('Camera access requires HTTPS or localhost. Open the secure forwarded URL.');
        }
        const acquired = await this.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false
        });
        // Permission prompts can outlive a Stop click. A late stream must never leak.
        if (!this._isCurrent(version) || this.state !== STATES.STARTING) {
          this._releaseLateStream(acquired);
          return;
        }
        this.stream = acquired;
        this.stream.getVideoTracks().forEach((track) => {
          if (track.addEventListener) {
            track.addEventListener('ended', () => this._onTrackEnded(version), { once: true });
          } else {
            track.onended = () => this._onTrackEnded(version);
          }
        });
        this.video.srcObject = this.stream;
        await this.video.play();
        if (!this._isCurrent(version) || this.state !== STATES.STARTING) {
          this._stopTracks();
          return;
        }
        if (!this.video.videoWidth || !this.video.videoHeight) {
          throw new Error('Camera opened but video frames are unavailable.');
        }
        this._setState(STATES.RUNNING, 'Camera running · recognition is starting.');
        void this._scan(version);
      } catch (error) {
        this._fail(error, version);
      }
    }

    stop() {
      if (this.disposed || this.state === STATES.IDLE || this.state === STATES.STOPPING) return;
      this.generation += 1;
      this._clearTimer();
      this._setState(STATES.STOPPING, 'Stopping camera…');
      this._abortRecognition();
      this._stopTracks();
      this.inflightVersion = null;
      this._setState(STATES.IDLE, 'Camera · Idle · Click Start Camera to begin.');
    }

    async _captureBlob() {
      return new Promise((resolve) => {
        this.canvas.toBlob(resolve, 'image/jpeg', 0.78);
      });
    }

    _scheduleNext(version, delay) {
      if (!this._isCurrent(version) || this.state !== STATES.RUNNING) return;
      this._clearTimer();
      this.timer = this.schedule(() => {
        this.timer = null;
        void this._scan(version);
      }, delay);
    }

    async _scan(version) {
      if (!this._isCurrent(version) || this.state !== STATES.RUNNING) return;
      if (this.inflightVersion === version) return;
      if (!this.context) {
        this._fail(new Error('Canvas is unavailable in this browser.'), version);
        return;
      }
      if (this.video.readyState < 2 || !this.video.videoWidth || !this.video.videoHeight) {
        this._scheduleNext(version, 300);
        return;
      }

      this.inflightVersion = version;
      let retry = false;
      try {
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        const blob = await this._captureBlob();
        if (!this._isCurrent(version) || this.state !== STATES.RUNNING) return;
        if (!blob) throw new Error('Browser could not encode a camera frame.');

        const csrfToken = this.getCsrfToken();
        if (!csrfToken) throw new Error('CSRF token is unavailable. Reload the page and retry.');
        const abortController = typeof AbortController !== 'undefined' ? new AbortController() : null;
        this.requestAbort = abortController;
        const response = await this.fetch('/recognize/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'image/jpeg',
            'X-Client-ID': this.clientId,
            'X-CSRFToken': csrfToken
          },
          body: blob,
          ...(abortController ? { signal: abortController.signal } : {})
        });
        if (!this._isCurrent(version) || this.state !== STATES.RUNNING) return;

        let body;
        try {
          body = await response.json();
        } catch (error) {
          if (!response.ok && response.status === 403) {
            throw new Error('Request forbidden (403). CSRF validation or session failed; reload the page and verify trusted HTTPS proxy settings.');
          }
          if (!response.ok && response.status === 404) {
            throw new Error('Recognition endpoint not found (404). Check the server route.');
          }
          if (!response.ok && response.status >= 500) {
            throw new Error('Recognition server error (' + response.status + '). Check server diagnostics and model files.');
          }
          throw new Error('/recognize/ returned invalid JSON (HTTP ' + response.status + ').');
        }
        if (!response.ok) {
          let message = body && body.message;
          if (response.status === 403) message = message || 'Request forbidden (403). Check the session and CSRF token.';
          else if (response.status === 404) message = message || 'Recognition endpoint not found (404).';
          else if (response.status >= 500) message = message || 'Recognition server error (' + response.status + ').';
          else message = message || 'Recognition request failed (HTTP ' + response.status + ').';
          throw new Error(message);
        }
        if (!body || body.status !== 'success' || !Array.isArray(body.results)) {
          throw new Error((body && body.message) || 'Recognition returned an unexpected response.');
        }
        this.onResults(body);
      } catch (error) {
        if (this._isCurrent(version) && this.state === STATES.RUNNING) {
          retry = true;
          const message = error && error.message ? error.message : 'Recognition request failed.';
          this.onRecognitionError(message);
          this.onDiagnostic(message.includes('CSRF') || message.includes('(403)') ? 'CSRF_OR_FORBIDDEN' : 'RECOGNITION', message);
        }
      } finally {
        if (this.inflightVersion === version) this.inflightVersion = null;
        if (this.requestAbort && this.inflightVersion === null) this.requestAbort = null;
        this._scheduleNext(version, retry ? this.retryInterval : this.interval);
      }
    }

    _onTrackEnded(version) {
      if (!this._isCurrent(version) || this.state !== STATES.RUNNING) return;
      this._fail(new Error('Camera disconnected or its video track ended. Reconnect the camera and restart.'), version);
    }

    async _onDeviceChange() {
      if (this.state !== STATES.RUNNING || !this.stream) return;
      const track = this.stream.getVideoTracks()[0];
      if (!track || track.readyState === 'ended') {
        this._fail(new Error('Active camera disconnected. Reconnect the camera and restart.'), this.generation);
        return;
      }
      if (!this.mediaDevices.enumerateDevices || !track.getSettings) return;
      try {
        const devices = await this.mediaDevices.enumerateDevices();
        if (this.state !== STATES.RUNNING || !this.stream) return;
        const deviceId = track.getSettings().deviceId;
        if (deviceId && !devices.some((device) =>
          device.kind === 'videoinput' && device.deviceId === deviceId)) {
          this._fail(new Error('The active camera is no longer available. Reconnect it and restart.'), this.generation);
        }
      } catch (error) {
        this.onDiagnostic('DEVICE_CHANGE', error && error.name);
      }
    }

    _onVideoError() {
      if (this.state === STATES.RUNNING || this.state === STATES.STARTING) {
        this._fail(new Error('The browser video element reported a playback error.'), this.generation);
      }
    }

    dispose() {
      if (this.disposed) return;
      this.disposed = true;
      this.generation += 1;
      this._clearTimer();
      this._abortRecognition();
      this._stopTracks();
      this.inflightVersion = null;
      if (this.video.removeEventListener) this.video.removeEventListener('error', this._onVideoError);
      if (this.mediaDevices.removeEventListener) {
        this.mediaDevices.removeEventListener('devicechange', this._onDeviceChange);
      }
      this.state = STATES.IDLE;
    }
  }

  CameraController.STATES = STATES;
  CameraController.cameraErrorMessage = cameraErrorMessage;
  return CameraController;
}));
