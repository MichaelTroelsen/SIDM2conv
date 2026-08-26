// Execute abpage.py's SCRIPT against a stub DOM and report what the pattern
// scroll actually did. Written for pyscript/test_abpage.py, which pipes the
// script in on argv[2].
//
// This exists because an HTTP probe cannot see JavaScript that never runs. A
// refused voice renders without its trkN element, and a single early return
// keyed on "all three columns exist" silently disabled the scroll for EVERY
// voice -- the page sat at row 000 with no highlight, which reads as a broken
// feature rather than as one refused voice. Pattern-matching the source would
// not have caught it; running it does.
const fs = require('fs');
const store = {};

const script = fs.readFileSync(process.argv[2], 'utf8');
const MISSING = (process.argv[3] || '').split(',').filter(Boolean); // e.g. "trk1"

// MIRROR THE REAL DOM, do not hand every element children it does not have.
// Twice now this harness passed a page that was broken, because a permissive
// stub answered questions the real DOM answers differently: first by skipping
// the canvas blocks, then by giving the scroll box 40 row children when the
// real one has exactly ONE (the trkinner wrapper) and the rows hang off that.
// A fixture looser than reality tests nothing.
const ROWCOUNT = { trkin0: 64, trkin1: 0, trkin2: 31 };

function el(id) {
  const kids = [];
  const n = id in ROWCOUNT ? ROWCOUNT[id] : (/^trk\d$/.test(id) ? 0 : 40);
  for (let i = 0; i < n; i++) {
    kids.push({
      offsetTop: i * 20, offsetHeight: 20, dataset: { i: String(i) },
      classList: {
        _s: new Set(),
        add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
        toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); },
        contains(c) { return this._s.has(c); },
      },
    });
  }
  const self = {
    id, children: kids, scrollTop: 0, clientHeight: 420, value: '0',
    textContent: '', innerHTML: '', hidden: false, checked: false,
    readyState: 4, duration: 20, currentTime: 0, paused: true, volume: 1,
    dataset: {}, style: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener(t, fn) { (this._h ||= {})[t] = fn; },
    setAttribute() {}, getAttribute() { return null; },
    querySelector(sel) {
      if (sel === '.trkrow.cur') {
        const m = /^trk(\d)$/.exec(id);
        const rows = m ? (store['trkin' + m[1]] || {}).children || [] : kids;
        return rows.find(k => k.classList.contains('cur')) || null;
      }
      return null;
    },
    querySelectorAll() { return []; },
    getBoundingClientRect() { return { left: 0, width: 100 }; },
    getContext() { return ctx2d(); },
    parentNode: { querySelectorAll() { return []; } },
    contains() { return true; }, closest() { return null; },
    play() {}, pause() {}, load() {},
    insertAdjacentHTML() {},
  };
  // A trkbody's ONLY child is its trkinner, exactly as the page emits it.
  const m = /^trk(\d)$/.exec(id);
  if (m) self.children = [store['trkin' + m[1]] ||= el('trkin' + m[1])];
  return self;
}

// The canvas-backed blocks run BEFORE the scroll block in the script, and the
// whole thing is one IIFE -- so a synchronous throw in any of them kills the
// scroll while leaving the A/B controls working, because those bound earlier.
// Skipping them here is exactly how this harness missed a real bug once. They
// are stubbed rather than skipped: pass "skipcanvas" as argv[5] to go back to
// skipping, for isolating the scroll on its own.
const SKIP_CANVAS = (process.argv[5] || '') === 'skipcanvas';
const NOT_UNDER_TEST = SKIP_CANVAS ? ['wave', 'spectro', 'vwrap', 'voices'] : [];

function ctx2d() {
  const noop = () => {};
  return {
    clearRect: noop, fillRect: noop, beginPath: noop, moveTo: noop,
    lineTo: noop, closePath: noop, fill: noop, stroke: noop, drawImage: noop,
    putImageData: noop, save: noop, restore: noop, scale: noop, translate: noop,
    createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }),
    globalAlpha: 1, fillStyle: '', strokeStyle: '', lineWidth: 1,
    imageSmoothingEnabled: false,
  };
}

const document = {
  getElementById(id) {
    if (MISSING.includes(id) || NOT_UNDER_TEST.includes(id)) return null;
    return (store[id] ||= el(id));
  },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  documentElement: {},
  createElement() { return { getContext: () => ctx2d(), width: 0, height: 0 }; },
};
function AudioContext() {
  this.decodeAudioData = () => Promise.reject(new Error('no audio in harness'));
}
const window = {
  __abRows: JSON.parse(process.argv[4] || '[[],[],[]]'),
  AudioContext: AudioContext,
  __abVoices: JSON.parse(process.argv[6] || 'null'),
  __abSpectrogram: JSON.parse(process.argv[7] || 'null'),
  __abOursLabel: 'SIDM2 conversion',
};
const getComputedStyle = () => ({ getPropertyValue: () => '#000' });
// A REAL rAF, bounded. The previous version returned an id and never invoked
// the callback, so the whole PLAY path -- the one that actually drives the
// scroll during playback -- was never executed by this harness. The seek path
// was, which is why it reported success on a page that did not scroll.
let rafQueue = [];
const requestAnimationFrame = (fn) => { rafQueue.push(fn); return rafQueue.length; };
const cancelAnimationFrame = () => { rafQueue = []; };
const fetch = () => Promise.reject(new Error('no fetch in the harness'));
const atob = s => s;

try {
  new Function('document', 'window', 'getComputedStyle', 'requestAnimationFrame',
               'cancelAnimationFrame', 'fetch', 'atob', 'Audio', 'console',
               script)
    (document, window, getComputedStyle, requestAnimationFrame,
     cancelAnimationFrame, fetch, atob, function () {}, console);
} catch (e) {
  console.log(JSON.stringify({ error: String(e && e.message || e) }));
  process.exit(0);
}

// After load the script calls scrollTick() once, so a highlight should already
// exist on every column that HAS rows -- even when a sibling was refused.
const out = {};
for (const id of ['trk0', 'trk1', 'trk2']) {
  const box = store[id];
  if (!box) { out[id] = null; continue; }
  const rows = (store['trkin' + id.slice(-1)] || {}).children || [];
  const cur = rows.findIndex(k => k.classList.contains('cur'));
  out[id] = { highlighted: cur, scrollTop: box.scrollTop };
}

// Advance our render's clock and re-run via the seek handler, to prove the
// highlight MOVES rather than merely existing at row 0.
const bu = store['bu'], seek = store['seek'];
if (bu && seek && seek._h && seek._h.input) {
  bu.currentTime = 6.0;                    // frame 300 at 50 Hz
  seek._h.input();
  out.after_seek = {};
  for (const id of ['trk0', 'trk2']) {
    const box = store[id];
    if (!box) { out.after_seek[id] = null; continue; }
    out.after_seek[id] = ((store['trkin' + id.slice(-1)] || {}).children || [])
      .findIndex(k => k.classList.contains('cur'));
  }
}
// THE PLAY PATH, which is what actually scrolls during playback. Fire the
// element's own "play" handler, then pump rAF while advancing our render's
// clock, and record where each column ended up.
const au = store['au'];
out.play_path = { started: false, samples: [] };
if (au && au._h && au._h.play && bu) {
  au.paused = false;
  au._h.play();                                  // starts the rAF loop
  out.play_path.started = rafQueue.length > 0;
  for (let step = 0; step < 6; step++) {
    bu.currentTime = step * 2.0;                 // 0s, 2s, 4s ... = frame 0,100,200
    const pending = rafQueue;
    rafQueue = [];
    pending.forEach(fn => fn());                 // one animation frame
    out.play_path.samples.push({
      t: bu.currentTime,
      trk0: ((store['trkin0'] || {}).children || []).findIndex(k => k.classList.contains('cur')),
      trk2: ((store['trkin2'] || {}).children || []).findIndex(k => k.classList.contains('cur')),
      scroll0: store['trk0'] ? store['trk0'].scrollTop : null,
      transform0: store['trkin0'] ? store['trkin0'].style.transform : null,
    });
  }
}
console.log(JSON.stringify(out));
