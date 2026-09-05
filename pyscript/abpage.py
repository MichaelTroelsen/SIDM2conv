#!/usr/bin/env python3
"""Gapless A/B listening pages for an original SID against a SIDM2 conversion.

    python pyscript/abpage.py stage orig.sid conv.sf2 --driver-init 0x1000 \
                                    --driver-play 0x1003 --voices
    python pyscript/abpage.py build                 # one page per staged pair
    python pyscript/abpage.py serve                 # ...and host them
    python pyscript/abpage.py build --embed NAME    # self-contained, WAVs inlined

A page plays **both renders at once and swaps which one is audible**, so the
switch is gapless and position-matched. That is the whole reason for the tool:
two files in a media player cannot be compared that way, and a comparison that
loses its place between clicks is a comparison of two memories.

Every accuracy percentage in CLAUDE.md's Known Limitations table is a claim
about whether a build SOUNDS right. Until this tool there was no rig for a
human to check one of those claims by ear -- only an assistant reading a
static spectrogram (`sidm2/audio_listen.py`) or a person opening two WAVs in a
media player by hand, which is the exact comparison-of-two-memories this page
exists to replace.

Ported from h2g's `python/abpage.py` (a separate repo, SID -> GoatTracker).
The transport, sync, envelope and spectrogram machinery is h2g's, near
verbatim; what is NOT h2g's is the staging (it goes through this repo's own
`pyscript/audio_tightness_tool.py`, so both sides come from ONE renderer --
see `choose_renderer`'s docstring for why mixing two is a measurement error)
and the report-quoting layer, which reads an explicit `--chips` JSON rather
than scraping a Markdown table. h2g's own module warns that a Markdown-table
scraper degrades SILENTLY into reading nothing; a report this page cannot
parse must show a gap, never an empty rail that looks like a clean result.

Two output modes, and the difference matters:

* **Local** (default) references `<name>.original.wav` beside the page, so a
  page is ~25 KB and carries a tune of any length. Serve it -- the envelope
  overlay and the automatic sync read the two WAVs with `fetch()`, which no
  browser allows over `file://`. Audio playback works either way.
* **`--embed`** inlines both renders as data URIs, for publishing somewhere
  the WAVs cannot follow. That costs 4/3 of the audio: at 44.1 kHz mono a
  minute a side is about 14 MB, which is the practical ceiling.

stdlib only (the FFT included) -- deliberately, so a listening page can be
built on a machine where numpy is not installed. The staging half imports
numpy transitively through `audio_tightness_tool`; `build` and `serve` do not.
"""
from __future__ import annotations

import argparse
import base64
import cmath
import json
import math
import os
import re
import shutil
import struct
import sys
import wave
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTEN = ROOT / "build" / "listen"

# The infix on our side of the pair. h2g used ".h2g."; everything downstream
# (globbing, the voice map, prune) derives from this one constant rather than
# repeating the literal.
OURS = "sidm2"

# The label the page prints for our side.
OURS_LABEL = "SIDM2 conversion"


def listen_dir() -> Path:
    """`build/listen`, resolved against the CURRENT value of ROOT on every call.

    Never against a module-level constant computed at import time: the tests
    redirect this module at a temporary directory with
    `monkeypatch.setattr(A, "ROOT", tmp_path)`, and a constant would ignore
    that and read the real staging area. That is not hypothetical -- h2g's
    own `_doc()` carries the same note because two of its tests began
    asserting against the live corpus instead of their own fixture, and
    passed or failed on whatever the last build happened to produce.
    """
    return ROOT / "build" / "listen"


def orig_wav(name: str) -> Path:
    return listen_dir() / ("%s.original.wav" % name)


def ours_wav(name: str) -> Path:
    return listen_dir() / ("%s.%s.wav" % (name, OURS))


# ---------------------------------------------------------------------------
# staging -- goes through this repo's own renderer plumbing, never a new one
# ---------------------------------------------------------------------------

def _stage_args(seconds, subtune, driver_init, driver_play, voice, verbose):
    """The argparse-shaped namespace `audio_tightness_tool` expects.

    That module's `resolve_input`/`resolve_to_sid`/`_render_muted` all read
    their settings off an `args` object rather than parameters. Building one
    here is what lets this tool reuse them unmodified -- which is the point:
    the SF2 -> SID -> WAV path (including the "init/play could not be
    auto-detected" refusal that stops a Driver 11 default guess being applied
    to a native-driver SF2) is already written and already tested there.
    """
    return argparse.Namespace(
        seconds=seconds, subtune=subtune, voice=voice, verbose=verbose,
        driver_init=driver_init, driver_play=driver_play)


def stage(orig: Path, conv: Path, name: str, seconds: int, subtune,
          driver_init, driver_play, want_voices: bool, requested_renderer: str,
          verbose: int, allow_renderer_change: bool = False) -> int:
    """Render both sides into `build/listen` under the page's naming scheme."""
    import tempfile

    sys.path.insert(0, str(ROOT))
    from pyscript import audio_tightness_tool as att
    from sidm2.audio_export_wrapper import AudioExportIntegration
    from sidm2.vsid_wrapper import VSIDIntegration

    out = listen_dir()
    out.mkdir(parents=True, exist_ok=True)

    # ONE renderer for both sides. Comparing a VSID render against a
    # sidplayfp render folds two different SID emulations into everything the
    # page draws -- see choose_renderer's own docstring.
    try:
        renderer, why = att.choose_renderer(
            requested_renderer, 1 if want_voices else None,
            VSIDIntegration._check_tool_available(),
            AudioExportIntegration._check_tool_available())
    except att.RenderError as exc:
        print("[ERROR] %s" % exc)
        return 2
    print("renderer: %s (%s)" % (renderer, why))

    # REFUSE A SILENT RENDERER CHANGE. Staging with --voices forces sidplayfp
    # (the only renderer with a voice mute); staging the same tune again
    # without it picks vsid, overwrites the main pair, and leaves the six
    # sidplayfp stems on disk. The page then compares a vsid main pair against
    # sidplayfp stems, and applies a sync offset derived from one to the other
    # -- which choose_renderer's own docstring calls "exactly the measurement
    # error this tool exists to avoid". It is silent, it looks fine, and it
    # happened for real in this repo's own session log.
    #
    # Refuse rather than warn: a warning scrolls past, and the result is a
    # wrong number nobody knows is wrong. Refuse rather than auto-delete: the
    # stems are minutes of rendering, and destroying them on the user's behalf
    # is a bigger surprise than stopping.
    prev = sources_for(name)
    if prev and prev.get("renderer") and prev["renderer"] != renderer:
        stale = [p.name for p in sorted(listen_dir().glob("%s.v[123].*.wav" % name))]
        if stale:
            print(
                "[ERROR] %s was staged with %s and %d solo stem(s) from it are "
                "still on disk, but this run would use %s.\n"
                "        Mixing renderers across a comparison is a measurement "
                "error, not a cosmetic one: the per-voice strips would compare "
                "%s stems against a %s pair.\n"
                "        Either re-stage with the same renderer "
                "(--renderer %s), or add --voices so every file is re-rendered "
                "together, or pass --allow-renderer-change to delete the stale "
                "stems and continue."
                % (name, prev["renderer"], len(stale), renderer,
                   prev["renderer"], renderer, prev["renderer"]))
            if not allow_renderer_change:
                return 2
            for s in stale:
                (listen_dir() / s).unlink()
            print("        --allow-renderer-change: deleted %d stale stem(s)"
                  % len(stale))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        args = _stage_args(seconds, subtune, driver_init, driver_play,
                           None, verbose)
        pairs = (("original", orig, orig_wav(name)),
                 (OURS, conv, ours_wav(name)))
        for role, src, dest in pairs:
            wav = att.resolve_input(Path(src), role, args, tmp, renderer)
            if wav is None:
                return 2                      # resolve_input already printed
            shutil.copyfile(str(wav), str(dest))
            print("  %s  <- %s" % (dest.name, src))

        if want_voices:
            # sidplayfp is the only renderer with a voice-mute flag, which
            # choose_renderer already enforced above. CLAUDE.md's standing
            # caveat applies and is repeated on the page: muting is NOT clean
            # isolation on every tune.
            for role, src, _dest in pairs:
                sid = att.resolve_to_sid(Path(src), role, args, tmp)
                if sid is None:
                    return 2
                for v in (1, 2, 3):
                    dest = listen_dir() / ("%s.v%d.%s.wav" % (name, v, role))
                    att._render_muted(sid, tmp / ("%s.v%d.wav" % (role, v)),
                                      att.MUTE_MAP[v], args)
                    shutil.copyfile(str(tmp / ("%s.v%d.wav" % (role, v))),
                                    str(dest))
                    print("  %s" % dest.name)
    # Provenance sidecar. The staged WAVs do not say what they came from, and
    # anything that reasons about the MUSIC rather than the audio -- the
    # instrument map, the pattern view -- needs the .sid/.sf2, not the render.
    # Written last, so it exists only when the staging above actually
    # succeeded: a sidecar pointing at sources whose render failed would send
    # the next tool off to trace a pair the page does not contain.
    (listen_dir() / ("%s.sources.json" % name)).write_text(json.dumps({
        "original": str(Path(orig).resolve()),
        "converted": str(Path(conv).resolve()),
        "seconds": seconds, "subtune": subtune,
        "driver_init": driver_init, "driver_play": driver_play,
        "renderer": renderer, "voices": bool(want_voices),
    }, indent=1), encoding="utf-8")
    print("staged %r in %s" % (name, listen_dir()))
    return 0


def sources_for(name: str) -> dict | None:
    """What `stage` recorded for this tune, or None if it predates the sidecar."""
    p = listen_dir() / ("%s.sources.json" % name)
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


# ---------------------------------------------------------------------------
# the report-quoting layer -- explicit inputs, never a scraped table
# ---------------------------------------------------------------------------

def chips_rows(path: Path | None) -> dict[str, dict[str, str]]:
    """`{tune: {label: value}}` from a JSON file, or {} when none was given.

    JSON and not a scraped Markdown table, on purpose: a table scraper that
    stops matching returns zero rows and the page renders a confident empty
    rail, which reads exactly like "nothing to report". A JSON file that does
    not parse is an error with a line number.

    Accepts both shapes `abpage_chips` can write: the flat
    `{tune: {label: value}}`, and the annotated
    `{tune: {"chips": {...}, "blind": {...}}}` -- the second carries, per chip,
    what that chip cannot see. `blind_rows()` reads the same file for the
    second half.
    """
    if path is None or not Path(path).exists():
        return {}
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as exc:
        print("[ERROR] --chips %s does not parse: %s" % (path, exc))
        return {}
    if not isinstance(doc, dict):
        print("[ERROR] --chips %s: expected an object keyed by tune name" % path)
        return {}
    out = {}
    for k, v in doc.items():
        if not isinstance(v, dict):
            continue
        inner = v.get("chips") if isinstance(v.get("chips"), dict) else v
        out[k] = {str(a): str(b) for a, b in inner.items()}
    return out


def blind_rows(path: Path | None) -> dict[str, dict[str, str]]:
    """`{tune: {label: what-this-chip-cannot-see}}`, or {} when absent.

    Kept beside the values rather than folded into them because the whole
    calibration finding is that WHICH feature is informative depends on the
    defect: A-weighted level is the strongest discriminator on a timing defect
    and pure noise on a pitch defect, where chroma fires instead. A rail of
    bare numbers invites reading a null as "clean" when it may only mean "this
    feature is blind to this defect".
    """
    if path is None or not Path(path).exists():
        return {}
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError:
        return {}
    if not isinstance(doc, dict):
        return {}
    out = {}
    for k, v in doc.items():
        if isinstance(v, dict) and isinstance(v.get("blind"), dict):
            out[k] = {str(a): str(b) for a, b in v["blind"].items()}
    return out


def listening_notes(path: Path | None) -> dict[str, list[str]]:
    """The `- bullet` lines under each `## <tune>` heading of a notes file."""
    if path is None or not Path(path).exists():
        return {}
    notes: dict[str, list[str]] = {}
    name = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        head = re.match(r"^## (.+?)(?: [-—].*)?$", line)
        if head:
            name = head.group(1).strip()
            notes.setdefault(name, [])
            continue
        if name and line.startswith("- "):
            notes[name].append(line[2:].strip())
    return notes


def md(text: str) -> str:
    """The little Markdown a notes file carries: **bold**, `code`, *em*."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    return text.replace("--", "&mdash;")


# ---------------------------------------------------------------------------
# spectrogram: both sides' FFT, precomputed at build time
# ---------------------------------------------------------------------------
#
# A per-sample FFT in the browser over two two-minute WAVs cannot draw in
# under a second -- so the heavy pass runs exactly once, here, in Python, and
# the page ships two small fixed-size byte grids (bins x cols) that cost the
# same to paint regardless of how long the tune runs. Log-spaced frequency
# bins, because an octave low down and an octave up high are the same size to
# the ear and should be the same width on screen.
SPEC_COLS = 480          # ~250ms/column over a 120s tune
SPEC_BINS = 64
SPEC_WINDOW = 2048       # power of two; ~46ms per analysis frame at 44.1kHz
SPEC_FMIN = 40.0
SPEC_FMAX = 12000.0
SPEC_FLOOR_DB = -60.0

_TWIDDLE_CACHE: dict[int, list[complex]] = {}
_HANN_CACHE: dict[int, list[float]] = {}


def _twiddles(n: int) -> list[complex]:
    t = _TWIDDLE_CACHE.get(n)
    if t is None:
        t = [cmath.exp(-2j * math.pi * k / n) for k in range(n // 2)]
        _TWIDDLE_CACHE[n] = t
    return t


def _hann(n: int) -> list[float]:
    w = _HANN_CACHE.get(n)
    if w is None:
        w = [0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]
        _HANN_CACHE[n] = w
    return w


def _fft(a: list[complex]) -> list[complex]:
    """Iterative radix-2 Cooley-Tukey. `len(a)` must be a power of two.

    Kept stdlib rather than swapped for numpy: `build` and `serve` then work
    on a machine that has not installed this repo's requirements, which is
    the case for anyone who only wants to LISTEN to an artifact somebody else
    built. Twiddles are cached across the ~1000 calls a page costs.
    """
    n = len(a)
    a = a[:]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        half = length // 2
        tw = _twiddles(length)
        for start in range(0, n, length):
            for k in range(half):
                u = a[start + k]
                v = a[start + k + half] * tw[k]
                a[start + k] = u + v
                a[start + k + half] = u - v
        length <<= 1
    return a


def _read_wav_mono(path: Path) -> tuple[list[float], int] | None:
    """16-bit PCM samples as floats in [-1, 1], averaged to mono if needed.

    Returns None for anything that is not a readable 16-bit WAV -- including
    the truncated placeholder bytes a test fixture writes in place of real
    audio -- so a page build never crashes on bad or missing input.
    """
    try:
        with wave.open(str(path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError, OSError):
        return None
    if sampwidth != 2 or framerate <= 0:
        return None
    usable = len(raw) - (len(raw) % 2)
    if usable <= 0:
        return None
    try:
        ints = struct.unpack("<%dh" % (usable // 2), raw[:usable])
    except struct.error:
        return None
    if n_channels <= 1:
        samples = [s / 32768.0 for s in ints]
    else:
        samples = [
            sum(ints[i:i + n_channels]) / n_channels / 32768.0
            for i in range(0, len(ints) - n_channels + 1, n_channels)
        ]
    if not samples:
        return None
    return samples, framerate


def _log_bin_lookup(framerate: int, window: int, fmin: float, fmax: float,
                    bins: int) -> list[int]:
    """For each rFFT bin `0..window//2`, the log-spaced bin (`0..bins-1`) its
    frequency falls in, or -1 outside `[fmin, min(fmax, nyquist))`."""
    hi = min(fmax, framerate / 2)
    if hi <= fmin:
        return [-1] * (window // 2 + 1)
    ratio = hi / fmin
    out = []
    for k in range(window // 2 + 1):
        f = k * framerate / window
        if f < fmin or f >= hi:
            out.append(-1)
            continue
        b = int(math.log(f / fmin) / math.log(ratio) * bins)
        out.append(min(bins - 1, max(0, b)))
    return out


def _spectrogram_grid(samples: list[float], framerate: int, cols: int,
                      bins: int, window: int = SPEC_WINDOW,
                      fmin: float = SPEC_FMIN,
                      fmax: float = SPEC_FMAX) -> list[list[float]] | None:
    """`bins` x `cols` grid of average power, one column per time slice.

    Each column's analysis frame is Hann-windowed and centred on that
    column's nominal position (clipped to stay in bounds); the frame is much
    shorter than a column's time span on a full-length tune, so this is a
    sampled overview rather than a full overlap-add STFT -- the tradeoff that
    keeps the whole build a fixed, small cost.
    """
    n = len(samples)
    if n < window:
        return None
    lookup = _log_bin_lookup(framerate, window, fmin, fmax, bins)
    hann = _hann(window)
    hop = n / cols
    grid = [[0.0] * cols for _ in range(bins)]
    for c in range(cols):
        centre = int((c + 0.5) * hop)
        start = max(0, min(n - window, centre - window // 2))
        frame = samples[start:start + window]
        windowed = [complex(frame[i] * hann[i], 0.0) for i in range(window)]
        spec = _fft(windowed)
        sums = [0.0] * bins
        counts = [0] * bins
        for k, b in enumerate(lookup):
            if b < 0:
                continue
            re_, im_ = spec[k].real, spec[k].imag
            sums[b] += re_ * re_ + im_ * im_
            counts[b] += 1
        col = [sums[b] / counts[b] if counts[b] else 0.0 for b in range(bins)]
        for b in range(bins):
            grid[b][c] = col[b]
    return grid


def _grids_to_bytes(grid_a: list[list[float]],
                    grid_b: list[list[float]]) -> tuple[bytes, bytes]:
    """Both grids to 0-255 dB-scaled bytes against ONE shared peak, so a
    quieter render draws visibly dimmer rather than being re-normalised up to
    match -- the loudness difference is part of what this overlay shows."""
    peak = 1e-12
    for g in (grid_a, grid_b):
        for row in g:
            m = max(row) if row else 0.0
            if m > peak:
                peak = m

    def to_bytes(g: list[list[float]]) -> bytes:
        out = bytearray()
        for row in g:
            for v in row:
                db = SPEC_FLOOR_DB if v <= 0 else max(
                    SPEC_FLOOR_DB, 10.0 * math.log10(v / peak))
                level = (db - SPEC_FLOOR_DB) / -SPEC_FLOOR_DB
                out.append(int(round(level * 255)))
        return bytes(out)

    return to_bytes(grid_a), to_bytes(grid_b)


def spectrogram_payload(name: str) -> dict | None:
    """Both sides' log-frequency magnitude grid, base64-encoded, or None if
    either WAV is missing or unreadable."""
    a = _read_wav_mono(orig_wav(name))
    b = _read_wav_mono(ours_wav(name))
    if a is None or b is None:
        return None
    grid_a = _spectrogram_grid(a[0], a[1], SPEC_COLS, SPEC_BINS)
    grid_b = _spectrogram_grid(b[0], b[1], SPEC_COLS, SPEC_BINS)
    if grid_a is None or grid_b is None:
        return None
    bytes_a, bytes_b = _grids_to_bytes(grid_a, grid_b)
    return {
        "cols": SPEC_COLS, "bins": SPEC_BINS,
        "fmin": SPEC_FMIN, "fmax": SPEC_FMAX,
        "a": base64.b64encode(bytes_a).decode("ascii"),
        "b": base64.b64encode(bytes_b).decode("ascii"),
    }


def spectrogram_card(spec: dict | None) -> str:
    """The frequency-overlay card, or "" when no spectrogram was built."""
    if not spec:
        return ""
    return (
        '<div class="card wave">\n  <h2>Both sides, by frequency</h2>\n'
        '  <canvas id="spectro"></canvas>\n'
        '  <div class="legend">\n'
        '    <span class="swatch orig"><i></i>original</span>\n'
        '    <span class="swatch ours"><i></i>%s</span>\n'
        '    <span>brighter = louder at that frequency &middot; click to seek both</span>\n'
        '  </div>\n'
        '  <p class="caveat">Precomputed once at build time (log-spaced '
        '%d&ndash;%d&nbsp;Hz, %d time slices), so drawing it costs the same '
        'however long the tune runs. Colour is the two renders overlaid, not '
        'a difference &mdash; a wrong-pitch note shows as a bar lining up on '
        'one colour and not the other, and a quieter render draws visibly '
        'dimmer rather than being normalised up to match.</p>\n</div>\n'
        % (OURS_LABEL, spec["fmin"], spec["fmax"], spec["cols"]))


CSS = """
:root {
  --ground:#EEF1F4; --panel:#FFFFFF; --sunk:#E4E9ED;
  --ink:#0F171D; --muted:#5D6B77; --line:#D6DDE3;
  --a:#A8471C; --b:#17697F; --live:#2F7D52;
  --mono: ui-monospace, "Cascadia Mono", "SF Mono", Consolas, monospace;
  --sans: ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0E1418; --panel:#161E24; --sunk:#111A20;
    --ink:#E6EDF2; --muted:#8A9AA6; --line:#253039;
    --a:#E08A5C; --b:#5FBBD4; --live:#63C48D;
  }
}
:root[data-theme="dark"] {
  --ground:#0E1418; --panel:#161E24; --sunk:#111A20;
  --ink:#E6EDF2; --muted:#8A9AA6; --line:#253039;
  --a:#E08A5C; --b:#5FBBD4; --live:#63C48D;
}
* { box-sizing:border-box; }
body {
  margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--sans); line-height:1.55;
  padding:clamp(16px,4vw,44px) clamp(14px,4vw,32px);
}
.wrap { max-width:62rem; margin:0 auto; display:flex; flex-direction:column; gap:22px; }
header { display:flex; flex-direction:column; gap:10px; }
.eyebrow { font-family:var(--mono); font-size:11.5px; letter-spacing:.13em;
  text-transform:uppercase; color:var(--muted); }
.eyebrow a { color:var(--muted); }
h1 { margin:0; font-size:clamp(28px,5vw,44px); letter-spacing:-.02em; text-wrap:balance; }
h1 small { display:block; font-size:15px; font-weight:400; color:var(--muted);
  letter-spacing:0; margin-top:6px; }
.rail { display:flex; flex-wrap:wrap; gap:7px; }
.chip { font-family:var(--mono); font-size:12px; padding:5px 9px;
  border:1px solid var(--line); border-radius:3px; background:var(--panel);
  display:flex; gap:7px; align-items:baseline; }
.chip b { font-weight:600; font-variant-numeric:tabular-nums; }
.chip span { color:var(--muted); }
/* A chip with a known blind spot carries its caveat in `title`. The dotted
   underline is what makes that discoverable -- an un-marked tooltip is one
   nobody hovers, and the whole point is that a null reading must not be taken
   for "clean" when the feature is simply blind to this defect. */
.chip.hasblind { cursor:help; }
.chip.hasblind span { border-bottom:1px dotted var(--muted); }
/* The instrument-map verdict leads the card, because on this corpus about a
   third of files cannot be keyed at all and the verdict IS the result. */
.verdictline { margin:0 0 12px; font-family:var(--mono); font-size:13px; }
.verdictline b { color:var(--b); }
/* Three row states. An agreeing row stays quiet so the eye lands on the
   disagreements; a row NEITHER side sounds is greyed, because it is no
   evidence rather than agreement and must not read as either. */
tr.differs td { color:var(--a); }
tr.differs td:first-child { font-weight:600; }
tr.noevidence td { opacity:.45; font-style:italic; }
.card .caveat { margin:12px 0 0; font-size:.86rem; color:var(--muted); }
.trk { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.trkcol { border:1px solid var(--line); border-radius:6px; overflow:hidden;
  background:var(--sunk); }
.seqlab { float:right; font-weight:400; color:var(--muted); font-size:11px; }
.trkcol h3 { margin:0; padding:6px 10px; font-family:var(--mono); font-size:12px;
  letter-spacing:.06em; background:var(--panel);
  border-bottom:1px solid var(--line); }
.trkbody { height:420px; overflow:hidden; position:relative;
  font-family:var(--mono); font-size:12.5px; line-height:1.45; }
/* The rows sit in here and this is what MOVES -- a translate, never scrollTop.
   will-change lifts it onto its own layer so a 50 Hz update does not repaint
   the whole card. */
.trkinner { position:relative; will-change:transform; }
.trkhead { display:flex; gap:8px; padding:4px 10px; white-space:pre;
  font-size:11px; letter-spacing:.06em; color:var(--muted); opacity:.75;
  border-bottom:1px solid var(--line); }
.trkrow { display:flex; gap:8px; padding:0 10px; white-space:pre;
  color:var(--ink); cursor:pointer; }
.trkrow:hover { background:color-mix(in srgb, var(--ink) 6%, transparent); }
/* A tie advances no time, so several rows can share one frame. Dimmed, or the
   highlight resting on the row above reads as a bug rather than as the tie. */
.trkrow.tie { color:var(--muted); opacity:.6; }
.trkrow.cur { background:color-mix(in srgb, var(--live) 22%, transparent); }
.trkhead .ix, .trkrow .ix { display:inline-block; width:2.6em; color:var(--muted); opacity:.65; }
.trkhead .n, .trkrow .n { display:inline-block; width:3em; }
.trkhead .instr, .trkrow .instr { display:inline-block; width:2.6em; color:var(--b); }
.trkhead .cmd, .trkrow .cmd { display:inline-block; width:2.6em; color:var(--muted); }
.trkbody.empty { padding:14px 12px; font-size:.84rem; color:var(--muted); height:auto; }
.trkbody.empty p { margin:0; }
.trknote { margin:12px 0 0; font-size:.86rem; color:var(--muted); }
.trkstat { font-family:var(--mono); font-size:11.5px; color:var(--muted);
  margin:0 0 10px; letter-spacing:.04em; }
@media (max-width:640px) { .trk { grid-template-columns:1fr; } }
.rig { background:var(--panel); border:1px solid var(--line); border-radius:5px;
  padding:clamp(16px,3vw,26px); display:flex; flex-direction:column; gap:20px; }
.sources { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.src { appearance:none; cursor:pointer; text-align:left; font-family:var(--mono);
  background:var(--sunk); color:var(--ink); border:1.5px solid var(--line);
  border-radius:4px; padding:14px 16px; display:flex; flex-direction:column; gap:3px;
  transition:border-color .12s, background .12s; }
.src:hover { border-color:var(--muted); }
.src:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
.src .key { font-size:11px; letter-spacing:.12em; color:var(--muted); text-transform:uppercase; }
.src .name { font-size:17px; font-weight:600; }
/* When this WAV was rendered. A stale pair is indistinguishable from a fresh
   one by ear until something sounds wrong, and then the first suspicion falls
   on the converter rather than on the file's age. Kept quiet: provenance, not
   a control. */
.src .rendered { font-family:var(--mono); font-size:10.5px; color:var(--muted);
  letter-spacing:.04em; opacity:.8; }
.blind .src .rendered { visibility:hidden; }
.src[data-side="a"][aria-pressed="true"] { border-color:var(--a);
  background:color-mix(in srgb, var(--a) 11%, var(--panel)); }
.src[data-side="b"][aria-pressed="true"] { border-color:var(--b);
  background:color-mix(in srgb, var(--b) 11%, var(--panel)); }
.src[data-side="a"][aria-pressed="true"] .name { color:var(--a); }
.src[data-side="b"][aria-pressed="true"] .name { color:var(--b); }
.blind .src .name { color:var(--ink) !important; }
.transport { display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.play { appearance:none; cursor:pointer; width:52px; height:52px; flex:none;
  border-radius:50%; border:1.5px solid var(--ink); background:transparent;
  color:var(--ink); font-size:17px; display:grid; place-items:center; }
.play:focus-visible { outline:2px solid var(--ink); outline-offset:3px; }
.scrub { flex:1 1 240px; display:flex; flex-direction:column; gap:6px; }
input[type="range"] { width:100%; accent-color:var(--ink); }
.time { font-family:var(--mono); font-size:12px; color:var(--muted);
  font-variant-numeric:tabular-nums; display:flex; justify-content:space-between; }
.loop { display:flex; gap:14px; align-items:center; flex-wrap:wrap;
  font-family:var(--mono); font-size:12.5px; color:var(--muted); }
.mode { display:flex; gap:14px; align-items:center; flex-wrap:wrap;
  border-top:1px solid var(--line); padding-top:16px; }
.toggle { display:flex; align-items:center; gap:8px; font-family:var(--mono);
  font-size:12.5px; cursor:pointer; color:var(--ink); }
.ghost { appearance:none; cursor:pointer; font-family:var(--mono); font-size:12.5px;
  background:transparent; color:var(--ink); border:1px solid var(--line);
  border-radius:3px; padding:6px 11px; }
.ghost:hover { border-color:var(--muted); }
.ghost:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
.tally { font-family:var(--mono); font-size:12.5px; color:var(--muted);
  margin-left:auto; font-variant-numeric:tabular-nums; }
.verdict { font-family:var(--mono); font-size:12.5px; min-height:1.2em; }
.verdict.right { color:var(--live); }
.verdict.wrong { color:var(--a); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:5px;
  padding:18px 20px; }
.card h2 { margin:0 0 12px; font-size:12px; font-family:var(--mono); letter-spacing:.13em;
  text-transform:uppercase; color:var(--muted); font-weight:600; }
.card ul { margin:0; padding-left:1.1em; display:flex; flex-direction:column;
  gap:9px; font-size:14.5px; }
footer { color:var(--muted); font-size:12.5px; font-family:var(--mono);
  display:flex; flex-direction:column; gap:8px; }
footer a { color:var(--ink); }
kbd { font-family:var(--mono); font-size:11.5px; border:1px solid var(--line);
  border-bottom-width:2px; border-radius:3px; padding:1px 5px; }
table { width:100%; border-collapse:collapse; font-family:var(--mono); font-size:13px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line);
  font-variant-numeric:tabular-nums; }
th { color:var(--muted); font-weight:600; font-size:11.5px; letter-spacing:.1em;
  text-transform:uppercase; }
td a { color:var(--ink); font-weight:600; }
.scroll { overflow-x:auto; }
.sync { display:flex; gap:12px; align-items:center; flex-wrap:wrap;
  border-top:1px solid var(--line); padding-top:16px;
  font-family:var(--mono); font-size:12.5px; color:var(--muted); }
.sync input[type="range"] { flex:1 1 220px; }
.sync b { color:var(--ink); font-variant-numeric:tabular-nums; min-width:5.5em;
  display:inline-block; text-align:right; }
.sync .ghost { font-family:var(--mono); font-size:12px; }
.voices { display:flex; gap:8px; align-items:center; flex-wrap:wrap;
  border-top:1px solid var(--line); padding-top:16px; }
.voices .lbl { font-family:var(--mono); font-size:12px; color:var(--muted);
  letter-spacing:.1em; text-transform:uppercase; }
.voices button {
  appearance:none; cursor:pointer; font-family:var(--mono); font-size:13px;
  padding:6px 12px; border-radius:4px; border:1.5px solid var(--line);
  background:var(--sunk); color:var(--ink); }
.voices button[aria-pressed="true"] { border-color:var(--ink); font-weight:600; }
.voices .note { font-family:var(--mono); font-size:12px; color:var(--muted); }
.wave { position:relative; }
.wave canvas {
  display:block; width:100%; height:auto; border-radius:10px;
  background:var(--sunk); border:1px solid var(--line); cursor:crosshair;
}
.wave .legend {
  display:flex; flex-wrap:wrap; gap:14px; align-items:center;
  margin:10px 0 0; font-size:.82rem; color:var(--muted);
}
.voicewave .vwrap { display:flex; flex-direction:column; gap:10px; }
.voicewave .vw { border:1px solid var(--line); border-radius:6px;
  background:var(--sunk); overflow:hidden; }
.voicewave .vwhead { display:flex; justify-content:space-between;
  align-items:baseline; padding:5px 10px; font-family:var(--mono);
  font-size:11.5px; color:var(--muted); border-bottom:1px solid var(--line); }
.voicewave .vwhead b { color:var(--ink); letter-spacing:.06em; }
/* 84 of bands + 22 of |difference| strip, matching the canvas set in JS. */
.voicewave canvas { display:block; width:100%; height:106px; cursor:pointer; }
.voicewave button.vwtoggle { appearance:none; background:none; border:0;
  padding:0; font:inherit; color:inherit; cursor:pointer; display:inline-flex;
  align-items:center; gap:7px; }
.voicewave button.vwtoggle:focus-visible { outline:2px solid var(--ink);
  outline-offset:3px; border-radius:3px; }
/* A caret that turns, so the collapsed state reads as collapsed rather than
   as a voice that failed to render. */
.voicewave .cx { width:0; height:0; border-left:5px solid currentColor;
  border-top:4px solid transparent; border-bottom:4px solid transparent;
  transform:rotate(90deg); transition:transform .12s; opacity:.65; }
.voicewave button.vwtoggle[aria-pressed="false"] .cx { transform:rotate(0deg); }
.voicewave button.vwtoggle[aria-pressed="false"] b { color:var(--muted); }
.voicewave .vw.off canvas { display:none; }
.voicewave .vw.off { background:transparent; }
.wave .swatch { display:inline-flex; align-items:center; gap:6px; }
/* The two bands sit on top of each other at 62% alpha, so where they agree
   they are one colour and neither is readable on its own. Hiding a key is
   how you read the other -- and hiding BOTH but the difference strip is how
   you see where they part company with nothing else on the canvas. */
button.swatch { appearance:none; background:none; border:0; padding:0;
  font:inherit; color:inherit; cursor:pointer; }
button.swatch:focus-visible { outline:2px solid var(--ink); outline-offset:3px;
  border-radius:3px; }
button.swatch[aria-pressed="false"] { opacity:.42; text-decoration:line-through; }
button.swatch[aria-pressed="false"] i { background:transparent !important;
  box-shadow:inset 0 0 0 1.5px var(--muted); }
.wave .swatch i { width:11px; height:11px; border-radius:3px; display:inline-block; }
.wave .swatch.orig i { background:var(--a); }
.wave .swatch.ours i { background:var(--b); }
.wave .swatch.diff i { background:var(--ink); opacity:.45; }
.wave .stat { margin-left:auto; font-family:var(--mono); color:var(--ink); }
.wave .caveat { margin:12px 0 0; font-size:.86rem; color:var(--muted); }
.wave .msg {
  padding:26px 16px; text-align:center; color:var(--muted); font-size:.9rem;
  border:1px dashed var(--line); border-radius:10px; background:var(--sunk);
}
@media (prefers-reduced-motion:reduce) { * { transition:none !important; } }
@media (max-width:520px) { .sources { grid-template-columns:1fr; } }
"""

SCRIPT = r"""
(function () {
  var au = document.getElementById("au"), bu = document.getElementById("bu");
  var play = document.getElementById("play"), seek = document.getElementById("seek");
  var now = document.getElementById("now"), dur = document.getElementById("dur");
  var blind = document.getElementById("blind"), rig = document.getElementById("rig");
  var looping = document.getElementById("looping");
  var gA = document.getElementById("guessA"), gB = document.getElementById("guessB");
  var verdict = document.getElementById("verdict"), tally = document.getElementById("tally");
  var nameA = document.getElementById("nameA"), nameB = document.getElementById("nameB");
  var srcs = Array.prototype.slice.call(document.querySelectorAll(".src"));
  var syncr = document.getElementById("syncr"), syncv = document.getElementById("syncv");
  var syncauto = document.getElementById("syncauto"), synczero = document.getElementById("synczero");
  var syncwhy = document.getElementById("syncwhy");
  var OURS = window.__abOursLabel || "conversion";
  var side = "a", swapped = false, right = 0, total = 0;

  // Seconds to ADD to A's position to get B's. The two renders need not start
  // together: a converted build can reach its first note a few frames after
  // the original, which is comfortably audible as a flam when the sources are
  // swapped -- and the whole point of this rig is that switching does not lose
  // your place. Positive means B's content is late and B must be run ahead.
  var sync = 0, autoSync = null;
  function bAt(t) {
    var d = bu.duration;
    var v = t + sync;
    if (v < 0) v = 0;
    if (d && isFinite(d) && v > d) v = d;
    return v;
  }
  function setSync(ms, why) {
    sync = ms / 1000;
    syncr.value = String(Math.round(ms));
    syncv.textContent = (ms > 0 ? "+" : "") + Math.round(ms) + " ms";
    if (why) syncwhy.innerHTML = why;
    if (!au.paused || au.currentTime) bu.currentTime = bAt(au.currentTime);
    if (window.__abRedraw) window.__abRedraw();
    if (window.__abSpectroRedraw) window.__abSpectroRedraw();
    if (window.__abVoiceRedraw) window.__abVoiceRedraw();
  }
  syncr.addEventListener("input", function () {
    setSync(Number(syncr.value), "&mdash; set by hand");
  });
  synczero.addEventListener("click", function () {
    setSync(0, "&mdash; no offset: the two renders as staged");
  });
  syncauto.addEventListener("click", function () {
    if (autoSync === null) {
      syncwhy.innerHTML = "&mdash; auto needs the envelopes, which need http (see below)";
      return;
    }
    setSync(autoSync, "&mdash; auto: our render's first note is "
            + Math.round(autoSync) + " ms (" + (autoSync / 20).toFixed(1)
            + " frames) later than the original's");
  });

  au.volume = 1; bu.volume = 0;

  function apply() {
    var leftEl = swapped ? bu : au, rightEl = swapped ? au : bu;
    leftEl.volume = side === "a" ? 1 : 0;
    rightEl.volume = side === "b" ? 1 : 0;
    srcs.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.side === side));
    });
  }
  function pick(s) { side = s; apply(); }
  srcs.forEach(function (b) {
    b.addEventListener("click", function () { pick(b.dataset.side); });
  });

  function fmt(t) {
    if (!isFinite(t)) return "0:00";
    var m = Math.floor(t / 60), s = Math.floor(t % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function toggle() {
    if (au.paused) {
      bu.currentTime = bAt(au.currentTime);
      au.play(); bu.play();
      play.innerHTML = "&#10074;&#10074;"; play.setAttribute("aria-label", "Pause");
    } else {
      au.pause(); bu.pause();
      play.innerHTML = "&#9654;"; play.setAttribute("aria-label", "Play");
    }
  }
  play.addEventListener("click", toggle);
  looping.addEventListener("change", function () {
    au.loop = looping.checked; bu.loop = looping.checked;
  });

  au.addEventListener("loadedmetadata", function () { dur.textContent = fmt(au.duration); });
  au.addEventListener("timeupdate", function () {
    now.textContent = fmt(au.currentTime);
    if (au.duration) seek.value = String(Math.round(au.currentTime / au.duration * 1000));
    if (Math.abs(bu.currentTime - bAt(au.currentTime)) > 0.06) bu.currentTime = bAt(au.currentTime);
  });
  au.addEventListener("ended", function () {
    if (!au.loop) { play.innerHTML = "&#9654;"; play.setAttribute("aria-label", "Play"); }
  });
  seek.addEventListener("input", function () {
    var t = (Number(seek.value) / 1000) * (au.duration || 60);
    au.currentTime = t; bu.currentTime = bAt(t); now.textContent = fmt(t);
  });

  function setNames() {
    if (blind.checked) {
      nameA.textContent = "X"; nameB.textContent = "Y";
      rig.classList.add("blind"); gA.hidden = false; gB.hidden = false;
    } else {
      nameA.textContent = swapped ? OURS : "Original .sid";
      nameB.textContent = swapped ? "Original .sid" : OURS;
      rig.classList.remove("blind"); gA.hidden = true; gB.hidden = true;
      verdict.textContent = "";
    }
  }
  blind.addEventListener("change", function () {
    swapped = blind.checked ? Math.random() < 0.5 : false;
    verdict.textContent = ""; apply(); setNames();
  });

  function guess(saidLeft) {
    var correct = saidLeft ? !swapped : swapped;
    total++; if (correct) right++;
    verdict.textContent = correct ? "Correct — that was the original."
                                  : "No — that was the conversion.";
    verdict.className = "verdict " + (correct ? "right" : "wrong");
    tally.textContent = right + " / " + total + " identified";
    swapped = Math.random() < 0.5; apply();
    nameA.textContent = "X"; nameB.textContent = "Y";
  }
  gA.addEventListener("click", function () { guess(true); });
  gB.addEventListener("click", function () { guess(false); });

  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "INPUT" && e.target.type !== "range") return;
    if (e.code === "Space") { e.preventDefault(); toggle(); }
    else if (e.key === "1" || e.key === "ArrowLeft") { e.preventDefault(); pick("a"); }
    else if (e.key === "2" || e.key === "ArrowRight") { e.preventDefault(); pick("b"); }
    else if (e.key === "l" || e.key === "L") {
      looping.checked = !looping.checked; au.loop = bu.loop = looping.checked;
    }
  });

  // ---- amplitude overlay -------------------------------------------------
  // Both sides' peak envelopes on one canvas. It shows dropped notes, wrong
  // note lengths and tempo drift (the two traces shear apart); it cannot show
  // pitch, timbre or filter, which is why the caveat is printed beside it
  // rather than left for the reader to infer.
  var cv = document.getElementById("wave");
  if (cv) (function () {
    var msg = document.getElementById("wavemsg");
    var stat = document.getElementById("wavestat");
    var COLS = 1400, H = 200, DIFF = 46, PAD = 6;
    var off = document.createElement("canvas");
    off.width = COLS; off.height = H + DIFF;
    cv.width = COLS; cv.height = H + DIFF;
    var ctx = cv.getContext("2d"), oc = off.getContext("2d");
    var envA = null, envB = null;

    function css(n) {
      return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    }
    function envelope(buf) {
      var ch = buf.getChannelData(0), n = ch.length;
      var out = new Float32Array(COLS), per = n / COLS;
      for (var i = 0; i < COLS; i++) {
        var s = Math.floor(i * per), e = Math.min(n, Math.floor((i + 1) * per));
        var pk = 0;
        for (var j = s; j < e; j++) { var v = ch[j] < 0 ? -ch[j] : ch[j]; if (v > pk) pk = v; }
        out[i] = pk;
      }
      return out;
    }
    function band(g, env, colour, alpha) {
      var mid = H / 2, half = mid - PAD;
      g.beginPath();
      for (var i = 0; i < COLS; i++) g.lineTo(i, mid - env[i] * half);
      for (var k = COLS - 1; k >= 0; k--) g.lineTo(k, mid + env[k] * half);
      g.closePath();
      g.globalAlpha = alpha; g.fillStyle = colour; g.fill(); g.globalAlpha = 1;
    }
    // B is drawn where it is *heard*, i.e. shifted by the sync offset, so the
    // picture never contradicts the ears.
    function shiftCols() {
      var d = au.duration;
      if (!d || !isFinite(d)) return 0;
      return Math.round(sync / d * COLS);
    }
    function shifted(env, by) {
      if (!by) return env;
      var out = new Float32Array(COLS);
      for (var i = 0; i < COLS; i++) {
        var j = i + by;
        out[i] = (j >= 0 && j < COLS) ? env[j] : 0;
      }
      return out;
    }
    function paint() {
      var line = css("--line"), ink = css("--ink");
      var envBs = shifted(envB, shiftCols());
      oc.clearRect(0, 0, COLS, H + DIFF);
      oc.strokeStyle = line; oc.lineWidth = 1;
      oc.beginPath(); oc.moveTo(0, H / 2 + 0.5); oc.lineTo(COLS, H / 2 + 0.5); oc.stroke();
      oc.beginPath(); oc.moveTo(0, H + 0.5); oc.lineTo(COLS, H + 0.5); oc.stroke();
      if (show.a) band(oc, envA, css("--a"), 0.62);
      if (show.b) band(oc, envBs, css("--b"), 0.62);
      // difference strip: |peak difference| per column, same time axis.
      // The sum accumulates whether or not the strip is drawn -- the mean is a
      // property of the two renders, not of what is currently on screen, and
      // recomputing it from the visible traces would make hiding a key look
      // like it changed the measurement.
      var sum = 0;
      oc.globalAlpha = 0.45; oc.fillStyle = ink;
      for (var i = 0; i < COLS; i++) {
        var d = Math.abs(envA[i] - envBs[i]); sum += d;
        if (show.d) oc.fillRect(i, H + DIFF - d * (DIFF - 4), 1, d * (DIFF - 4));
      }
      oc.globalAlpha = 1;
      if (stat) stat.textContent = "mean |Δ| " + (100 * sum / COLS).toFixed(1) + "%";
      frame();
    }

    // Which traces are drawn. Hiding one does not recompute anything.
    var show = { a: true, b: true, d: true };
    Array.prototype.forEach.call(
      cv.parentNode.querySelectorAll("button.swatch[data-trace]"),
      function (b) {
        b.addEventListener("click", function () {
          var k = b.dataset.trace;
          show[k] = !show[k];
          b.setAttribute("aria-pressed", String(show[k]));
          if (envA) paint();
        });
      });
    window.__abRedraw = function () { if (envA) paint(); };

    // --- automatic sync ---------------------------------------------------
    // Measured as the difference between the two FIRST ONSETS rather than by
    // cross-correlating the whole file. Correlation is the wrong instrument
    // here: over a minute the two sides can drift and can play different
    // numbers of notes, so the correlation comes out flat and its top lags sit
    // within a few percent of each other. A start offset is a property of the
    // start, and the first onset is where it lives.
    var ONSET_FRAC = 0.05, ONSET_LOOK = 20;
    function firstOnset(b) {
      var ch = b.getChannelData(0), rate = b.sampleRate;
      var n = Math.min(ch.length, Math.round(ONSET_LOOK * rate)), pk = 0;
      for (var i = 0; i < n; i++) { var v = ch[i] < 0 ? -ch[i] : ch[i]; if (v > pk) pk = v; }
      if (!pk) return null;
      var thr = pk * ONSET_FRAC;
      for (var j = 0; j < n; j++) { var w = ch[j] < 0 ? -ch[j] : ch[j]; if (w >= thr) return j / rate; }
      return null;
    }
    function startupLagMs(bufA, bufB) {
      var fa = firstOnset(bufA), fb = firstOnset(bufB);
      if (fa === null || fb === null) return null;
      var ms = (fb - fa) * 1000;
      if (ms < -500 || ms > 500) return null;   // not a startup lag
      return ms;
    }

    function frame() {
      ctx.clearRect(0, 0, COLS, H + DIFF);
      ctx.drawImage(off, 0, 0);
      var d = au.duration;
      if (d && isFinite(d)) {
        var x = Math.round(au.currentTime / d * COLS) + 0.5;
        ctx.strokeStyle = css("--live"); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H + DIFF); ctx.stroke();
      }
    }
    au.addEventListener("timeupdate", function () { if (envA) frame(); });
    seek.addEventListener("input", function () { if (envA) frame(); });

    cv.addEventListener("click", function (e) {
      var d = au.duration;
      if (!d || !isFinite(d)) return;
      var r = cv.getBoundingClientRect();
      var t = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * d;
      au.currentTime = t; bu.currentTime = bAt(t);
      now.textContent = fmt(t);
      seek.value = String(Math.round(t / d * 1000));
      frame();
    });

    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { if (msg) msg.textContent = "This browser has no Web Audio."; return; }
    var ac = new AC();
    function load(src) {
      return fetch(src).then(function (r) { return r.arrayBuffer(); })
        .then(function (ab) { return ac.decodeAudioData(ab); });
    }
    function loadPair(keepSync) {
    return Promise.all([load(au.src), load(bu.src)]).then(function (bufs) {
      envA = envelope(bufs[0]); envB = envelope(bufs[1]);
      if (msg) msg.hidden = true;
      cv.hidden = false;
      // A solo render's first onset is that voice's, not the song's, so the
      // startup lag is measured once from the full pair and carried across
      // voice switches rather than re-derived from a voice that may not play
      // at the start at all.
      var lag = keepSync ? null : startupLagMs(bufs[0], bufs[1]);
      if (lag !== null) {
        autoSync = lag;
        setSync(autoSync, "&mdash; auto: our render's first note is "
                + Math.round(lag) + " ms (" + (lag / 20).toFixed(1)
                + " frames) later than the original's; drag to taste");
      } else {
        syncwhy.innerHTML = "&mdash; no first onset found; drag to align by ear";
      }
      paint();
    }).catch(function () {
      // file:// blocks fetch of a sibling .wav in most browsers; the audio
      // elements themselves still play, so this is a missing picture and not
      // a broken page.
      cv.hidden = true;
      if (msg) msg.innerHTML =
        "The drawing and the automatic sync read both WAVs, which a browser "
        + "refuses over file://. Run <code>ab-listen.bat serve</code> and "
        + "open the printed http:// address; playback and the sync slider "
        + "work here either way.";
    });
    }
    window.__abReload = loadPair;
    loadPair(false);
  })();

  // ---- per-voice amplitude -------------------------------------------------
  // Three overlays on one time axis, so "which voice is wrong" is a glance
  // rather than three rounds of soloing.
  var vwrap = document.getElementById("vwrap");
  if (vwrap && window.__abVoices) (function () {
    var vmsg = document.getElementById("vwmsg");
    var COLS = 1400, H = 84, DIFF = 22, PAD = 3;
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { if (vmsg) vmsg.textContent = "This browser has no Web Audio."; return; }
    var ac = new AC(), strips = [];

    function env(buf) {
      var ch = buf.getChannelData(0), n = ch.length;
      var out = new Float32Array(COLS), per = n / COLS;
      for (var i = 0; i < COLS; i++) {
        var s = Math.floor(i * per), e = Math.min(n, Math.floor((i + 1) * per)), pk = 0;
        for (var j = s; j < e; j++) { var v = ch[j] < 0 ? -ch[j] : ch[j]; if (v > pk) pk = v; }
        out[i] = pk;
      }
      return out;
    }
    function grab(src) {
      return fetch(src).then(function (r) { return r.arrayBuffer(); })
        .then(function (ab) { return ac.decodeAudioData(ab); });
    }
    function cssv(n) {
      return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    }
    // The SAME shift the combined picture uses, derived from the full pair --
    // a voice silent at the start has no first onset of its own, and measuring
    // one per strip would slide the quiet voices against the loud ones for no
    // musical reason.
    function shiftCols() {
      var d = au.duration;
      if (!d || !isFinite(d)) return 0;
      return Math.round(sync / d * COLS);
    }
    function paintStrip(s) {
      var g = s.ctx, by = shiftCols(), mid = H / 2, half = mid - PAD;
      g.clearRect(0, 0, COLS, H + DIFF);
      g.strokeStyle = cssv("--line"); g.lineWidth = 1;
      g.beginPath(); g.moveTo(0, mid + 0.5); g.lineTo(COLS, mid + 0.5); g.stroke();
      g.beginPath(); g.moveTo(0, H + 0.5); g.lineTo(COLS, H + 0.5); g.stroke();
      function band(e, colour, doShift) {
        g.beginPath();
        for (var i = 0; i < COLS; i++) {
          var j = doShift ? i + by : i, v = (j >= 0 && j < COLS) ? e[j] : 0;
          g.lineTo(i, mid - v * half);
        }
        for (var k = COLS - 1; k >= 0; k--) {
          var m = doShift ? k + by : k, w = (m >= 0 && m < COLS) ? e[m] : 0;
          g.lineTo(k, mid + w * half);
        }
        g.closePath(); g.globalAlpha = 0.62; g.fillStyle = colour; g.fill();
        g.globalAlpha = 1;
      }
      if (vshow.a) band(s.a, cssv("--a"), false);
      if (vshow.b) band(s.b, cssv("--b"), true);
      // |difference| per column, same time axis and same shift as the bands
      // above it: on a voice where the renders agree it is a flat line, so a
      // spike is the moment to go and listen to.
      if (vshow.d) {
        g.globalAlpha = 0.45; g.fillStyle = cssv("--ink");
        for (var i = 0; i < COLS; i++) {
          var j = i + by;
          var dv = Math.abs(s.a[i] - ((j >= 0 && j < COLS) ? s.b[j] : 0));
          g.fillRect(i, H + DIFF - dv * (DIFF - 3), 1, dv * (DIFF - 3));
        }
        g.globalAlpha = 1;
      }
      var d = au.duration;
      if (d && isFinite(d)) {
        var x = Math.round(au.currentTime / d * COLS) + 0.5;
        g.strokeStyle = cssv("--live"); g.lineWidth = 2;
        g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H + DIFF); g.stroke();
      }
    }
    function paintAll() { strips.forEach(paintStrip); }
    window.__abVoiceRedraw = paintAll;

    var vshow = { a: true, b: true, d: true };
    Array.prototype.forEach.call(
      document.querySelectorAll(".voicewave button.swatch[data-vtrace]"),
      function (b) {
        b.addEventListener("click", function () {
          var k = b.dataset.vtrace;
          vshow[k] = !vshow[k];
          b.setAttribute("aria-pressed", String(vshow[k]));
          paintAll();
        });
      });

    var jobs = [1, 2, 3].map(function (v) {
      var pair = window.__abVoices["v" + v];
      return Promise.all([grab(pair[0]), grab(pair[1])]).then(function (bufs) {
        var c = document.getElementById("vwcv" + v);
        c.width = COLS; c.height = H + DIFF;
        var a = env(bufs[0]), b = env(bufs[1]), by = shiftCols(), sum = 0;
        for (var i = 0; i < COLS; i++) {
          var j = i + by;
          sum += Math.abs(a[i] - ((j >= 0 && j < COLS) ? b[j] : 0));
        }
        var st = document.getElementById("vwstat" + v);
        if (st) st.textContent = "mean |Δ| " + (100 * sum / COLS).toFixed(1) + "%";
        c.addEventListener("click", function (e) {
          var d = au.duration;
          if (!d || !isFinite(d)) return;
          var r = c.getBoundingClientRect();
          var t = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * d;
          au.currentTime = t; bu.currentTime = bAt(t);
          now.textContent = fmt(t);
          seek.value = String(Math.round(t / d * 1000));
        });
        strips.push({ ctx: c.getContext("2d"), a: a, b: b });
      });
    });
    // Collapse a voice. The strip keeps its mean |difference| visible while
    // collapsed -- that number is what ranks the voices, so hiding it with the
    // picture would defeat the point of collapsing the other two.
    Array.prototype.forEach.call(
      vwrap.querySelectorAll("button.vwtoggle"), function (b) {
        b.addEventListener("click", function () {
          var box = b.closest(".vw");
          var on = b.getAttribute("aria-pressed") !== "false";
          b.setAttribute("aria-pressed", String(!on));
          box.classList.toggle("off", on);
          if (!on) paintAll();      // re-shown: it was not painted while off
        });
      });

    Promise.all(jobs).then(function () {
      if (vmsg) vmsg.hidden = true;
      vwrap.hidden = false;
      paintAll();
    }).catch(function () {
      vwrap.hidden = true;
      if (vmsg) vmsg.innerHTML =
        "The per-voice drawing reads the six solo WAVs, which a browser "
        + "refuses over file://. Run <code>ab-listen.bat serve</code>.";
    });
    au.addEventListener("timeupdate", paintAll);
    seek.addEventListener("input", paintAll);
  })();

  // ---- spectrogram overlay ------------------------------------------------
  // Precomputed once at build time (see spectrogram_payload) -- a per-sample
  // FFT here, over two two-minute WAVs, could not draw in under a second.
  var scv = document.getElementById("spectro");
  if (scv && window.__abSpectrogram) (function () {
    var spec = window.__abSpectrogram, COLS = spec.cols, BINS = spec.bins;
    var W = 900, H = 220;
    scv.width = W; scv.height = H;
    var ctx = scv.getContext("2d");
    var off = document.createElement("canvas");
    off.width = COLS; off.height = BINS;
    var octx = off.getContext("2d");

    function decode(b64) {
      var bin = atob(b64), out = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return out;
    }
    var gridA = decode(spec.a), gridB = decode(spec.b);

    function css(n) {
      return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    }
    function hexToRgb(hex) {
      hex = hex.trim().replace("#", "");
      if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join("");
      var n = parseInt(hex, 16);
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    function shiftCols() {
      var d = au.duration;
      if (!d || !isFinite(d)) return 0;
      return Math.round(sync / d * COLS);
    }
    function paint() {
      var rgbA = hexToRgb(css("--a")), rgbB = hexToRgb(css("--b"));
      var img = octx.createImageData(COLS, BINS);
      var by = shiftCols();
      for (var b = 0; b < BINS; b++) {
        var row = BINS - 1 - b;                 // bin 0 (lowest freq) at the bottom
        for (var c = 0; c < COLS; c++) {
          var cc = c - by;
          var va = gridA[b * COLS + c] / 255;
          var vb = (cc >= 0 && cc < COLS) ? gridB[b * COLS + cc] / 255 : 0;
          var idx = (row * COLS + c) * 4;
          img.data[idx] = Math.min(255, rgbA[0] * va + rgbB[0] * vb);
          img.data[idx + 1] = Math.min(255, rgbA[1] * va + rgbB[1] * vb);
          img.data[idx + 2] = Math.min(255, rgbA[2] * va + rgbB[2] * vb);
          img.data[idx + 3] = 255;
        }
      }
      octx.putImageData(img, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, W, H);
      ctx.drawImage(off, 0, 0, COLS, BINS, 0, 0, W, H);
      var d = au.duration;
      if (d && isFinite(d)) {
        var x = Math.round(au.currentTime / d * W) + 0.5;
        ctx.strokeStyle = css("--live"); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      }
    }
    scv.addEventListener("click", function (e) {
      var d = au.duration;
      if (!d || !isFinite(d)) return;
      var r = scv.getBoundingClientRect();
      var t = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * d;
      au.currentTime = t; bu.currentTime = bAt(t);
      now.textContent = fmt(t);
      seek.value = String(Math.round(t / d * 1000));
      paint();
    });
    au.addEventListener("timeupdate", paint);
    au.addEventListener("loadedmetadata", paint);
    seek.addEventListener("input", paint);
    window.__abSpectroRedraw = paint;
    paint();
  })();

  // ---- voice selector ----------------------------------------------------
  // Each button swaps BOTH sources to the same voice, so the comparison stays
  // like-for-like. Position and play state are preserved across the swap, and
  // the sync offset is left alone -- it is a property of the two players'
  // startup, not of which voice is audible.
  var vrow = document.getElementById("voices");
  if (vrow && window.__abVoices) {
    var vbtns = Array.prototype.slice.call(vrow.querySelectorAll("button"));
    var vnote = document.getElementById("voicenote");
    var setVoice = function (key) {
      var pair = window.__abVoices[key];
      if (!pair) return;
      var t = au.currentTime, playing = !au.paused;
      au.src = pair[0]; bu.src = pair[1];
      au.load(); bu.load();
      au.currentTime = t; bu.currentTime = bAt(t);
      if (playing) { au.play(); bu.play(); }
      vbtns.forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.voice === key));
      });
      if (vnote) {
        vnote.textContent = key === "all"
          ? "all three voices, as staged"
          : "voice " + key.slice(1) + " alone on both sides";
      }
      if (window.__abReload) window.__abReload(true);
    };
    vbtns.forEach(function (b) {
      b.addEventListener("click", function () { setVoice(b.dataset.voice); });
    });
  }

  // ---- pattern scroll ----------------------------------------------------
  // Follows OUR render's clock (bu), because the rows are our conversion's.
  // The frame of a row came from the tempo written in the file, so a drift
  // here against the audio is the row rate being wrong -- left visible on
  // purpose, and said so in the caption.
  if (window.__abRows) (function () {
    var cols = [0, 1, 2].map(function (v) { return document.getElementById("trk" + v); });
    var inner = [0, 1, 2].map(function (v) { return document.getElementById("trkin" + v); });
    // Bail only if NO column exists. A REFUSED voice renders without a trkN
    // element, and requiring all three here meant one refused voice silently
    // killed the scroll for the other two -- the whole view sat at row 000 with
    // no highlight, which reads as "the feature does not work" rather than as
    // "one voice was refused". Every loop below guards its own column instead.
    if (!cols.some(function (c) { return !!c; })) return;
    var cur = [null, null, null];

    function rowAt(frames, f) {
      var lo = 0, hi = frames.length - 1, best = 0;
      while (lo <= hi) {
        var mid = (lo + hi) >> 1;
        if (frames[mid] <= f) { best = mid; lo = mid + 1; } else hi = mid - 1;
      }
      return best;
    }
    function updateRow(v, i) {
      if (i === cur[v]) return;
      var box = cols[v], inn = inner[v] || box;
      if (!box) return;
      cur[v] = i;
      var prev = box.querySelector(".trkrow.cur");
      if (prev) prev.classList.remove("cur");
      var el = inn.children[i];
      if (el) el.classList.add("cur");
    }
    // A single scrollTop per note reads as a series of leaps (timeupdate fires
    // ~4x/sec), and CSS smooth scrolling made it worse: each leap restarted the
    // browser's own animation mid-flight. Instead a rAF loop interpolates
    // between the current row's offset and the next by how far the play
    // position sits between their start frames -- one continuous motion.
    // The next row that starts at a LATER frame than row i -- not simply i+1.
    // A tie advances no time, so runs of rows share one frame, and
    // frames[i+1] - frames[i] is then 0. Interpolating over that span divides
    // by zero (guarded to frac=0), which pins the scroll until the frame ticks
    // over and then jumps -- exactly the judder this fixes. Angular's voice 1
    // alternates note/tie, so HALF its steps had a zero span.
    function nextDistinct(frames, i) {
      for (var j = i + 1; j < frames.length; j++) {
        if (frames[j] > frames[i]) return j;
      }
      return -1;
    }
    var stat = document.getElementById("trkstat");
    function scrollTick() {
      var f = (bu.currentTime || au.currentTime) * 50;
      var seen = [];
      for (var v = 0; v < 3; v++) {
        var box = cols[v];
        if (!box) continue;                      // a refused voice has no column
        var frames = window.__abRows[v];
        if (!frames || !frames.length) continue;
        var inn = inner[v] || box;
        var i = rowAt(frames, Math.floor(f));
        updateRow(v, i);
        var el = inn.children[i];
        if (!el) continue;
        var top = el.offsetTop;
        var j = nextDistinct(frames, i);
        if (j >= 0) {
          var jEl = inn.children[j];
          // Fractional position uses the UNFLOORED f, so the glide is
          // continuous between frames rather than stepping 50 times a second.
          var span = frames[j] - frames[i];
          if (jEl && span > 0) {
            var frac = Math.min(1, Math.max(0, (f - frames[i]) / span));
            top += (jEl.offsetTop - el.offsetTop) * frac;
          }
        }
        var shift = top - box.clientHeight / 2 + el.offsetHeight / 2;
        if (shift < 0) shift = 0;
        if (inner[v]) inn.style.transform = "translateY(" + (-shift) + "px)";
        else box.scrollTop = shift;          // fallback if the wrapper is absent
        seen.push(v + 1 + ":" + i);
      }
      // A live read-out of what the scroll thinks it is doing. It is here
      // because two rounds were spent theorising about why the pattern did not
      // move, with no way to see from the page whether the loop was even
      // running. Now it says so, and it stays: knowing the current row per
      // voice is useful on its own.
      if (stat) {
        stat.textContent = "scroll: frame " + Math.floor(f)
          + "  row " + (seen.join("  ") || "-")
          + (rafId !== null ? "  (following)" : "  (paused)");
      }
    }
    var rafId = null;
    function frameLoop() { scrollTick(); rafId = requestAnimationFrame(frameLoop); }
    au.addEventListener("play", function () {
      if (rafId === null) rafId = requestAnimationFrame(frameLoop);
    });
    function stopScroll() {
      if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
      scrollTick();
    }
    au.addEventListener("pause", stopScroll);
    au.addEventListener("ended", stopScroll);
    seek.addEventListener("input", scrollTick);
    scrollTick();

    // Click a row to jump both sides there and pause, so a row that looks wrong
    // can be heard on its own. Guarded on readyState: setting currentTime before
    // the browser has metadata can block on a large WAV while it works out
    // whether the position is seekable at all.
    cols.forEach(function (box) {
      if (!box) return;                          // a refused voice has no column
      box.addEventListener("click", function (e) {
        var row = e.target.closest(".trkrow");
        if (!row || !box.contains(row)) return;
        if (au.readyState < 1 || bu.readyState < 1) return;
        var i = Number(row.dataset.i), v = cols.indexOf(box);
        var frames = window.__abRows[v];
        if (!frames || !(i in frames)) return;
        var t = frames[i] / 50;
        au.pause(); bu.pause();
        play.innerHTML = "&#9654;"; play.setAttribute("aria-label", "Play");
        au.currentTime = t; bu.currentTime = bAt(t);
        now.textContent = fmt(t);
        if (au.duration) seek.value = String(Math.round(t / au.duration * 1000));
        scrollTick();
      });
    });
  })();

  apply(); setNames();
})();
"""


def wav_rendered(path: Path) -> str:
    """"rendered 2026-08-23 14:07" for a staged WAV, or "" if it is absent.

    Local time, not UTC: the reader comparing this against "did I just
    re-stage?" is looking at their own clock.

    This exists because a stale render is SILENT. A pair left from an earlier
    converter state plays perfectly and sounds subtly wrong, and the first
    suspicion falls on the converter rather than on the file's age. h2g
    records that costing it one wrong diagnosis; this repo's own docs record
    the same shape of error twice (31 of 33 HardTrack builds predating a fix
    while the table quoted the fixed builder). A timestamp on the face of the
    page turns "why does this sound off" into "this was staged before the fix".
    """
    try:
        ts = path.stat().st_mtime
    except OSError:
        return ""
    return "rendered " + datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def wav_uri(path: Path) -> str:
    return "data:audio/wav;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


LAUNCHER_CMD = r"""@echo off
REM Listen.cmd -- double-click to serve the A/B listening pages and open them.
REM Written by pyscript/abpage.py; edits here are overwritten on the next build.
REM The envelope overlay and the automatic sync read both WAVs with fetch(),
REM which no browser allows over file:// -- so this serves rather than opening
REM the file directly. Close the window to stop the server.
start "" "http://127.0.0.1:%(port)d/index.html"
pushd "%(repo)s"
py -3 pyscript\abpage.py serve --port %(port)d --no-build
popd
if errorlevel 1 pause
"""


def write_launcher(port: int = 8730) -> Path:
    """Drop a double-clickable Listen.cmd beside the staged pairs."""
    cmd = listen_dir() / "Listen.cmd"
    # ASCII, CRLF: a .cmd is read by the legacy command processor, which does
    # not want a UTF-8 BOM and is happier with DOS line endings. `newline=""`
    # and NOT a manual "\n" -> "\r\n" replace: text mode translates on write,
    # so a string that already carries \r\n is written as \r\r\n -- a real
    # corruption, and invisible to read_text(), which translates it back.
    with open(cmd, "w", encoding="ascii", newline="\r\n") as fh:
        fh.write(LAUNCHER_CMD % {"repo": str(ROOT), "port": port})
    return cmd


def voicewave_card(voice_map: dict) -> str:
    """Three stacked amplitude overlays, one per voice, drawn at once.

    The question actually asked of these pages is "WHICH voice is wrong", and
    that is a comparison ACROSS voices, not within one. Three strips on one
    time axis answer it by looking; switching back and forth does not.

    Empty unless `stage --voices` produced the six solo renders.
    """
    if not voice_map or not all("v%d" % v in voice_map for v in (1, 2, 3)):
        return ""
    strips = "".join(
        '<div class="vw" data-voice="%d">'
        '<div class="vwhead">'
        '<button type="button" class="vwtoggle" data-strip="%d" '
        'aria-pressed="true" aria-label="Show or hide voice %d">'
        '<span class="cx"></span><b>Voice %d</b></button>'
        '<span class="stat" id="vwstat%d"></span></div>'
        '<canvas id="vwcv%d"></canvas></div>' % (v, v, v, v, v, v)
        for v in (1, 2, 3))
    return (
        '<div class="card wave voicewave">\n  <h2>Each voice, drawn</h2>\n'
        '  <div class="msg" id="vwmsg">Reading the six solo renders&hellip;</div>\n'
        '  <div class="vwrap" id="vwrap" hidden>%s</div>\n'
        '  <div class="legend">\n'
        '    <button type="button" class="swatch orig" data-vtrace="a" '
        'aria-pressed="true"><i></i>original</button>\n'
        '    <button type="button" class="swatch ours" data-vtrace="b" '
        'aria-pressed="true"><i></i>%s</button>\n'
        '    <button type="button" class="swatch diff" data-vtrace="d" '
        'aria-pressed="true"><i></i>|difference|, lower strip</button>\n'
        '    <span>click a key to hide it in all three &middot; click a voice '
        'name to collapse it &middot; same time axis and the same sync offset '
        'as the pair above &middot; click a strip to seek</span>\n'
        '  </div>\n'
        '  <p class="caveat">The voice whose <code>mean&nbsp;|&Delta;|</code> '
        'is worst is the one to solo with the buttons at the top, and the '
        '<b>lower strip under each voice</b> says <i>where</i> to listen. '
        'Same caveat as the combined picture: this is amplitude, so it shows '
        'dropped notes, note lengths and silence, and says nothing about '
        'pitch or timbre. A voice the original never plays draws a flat line '
        'on both sides and scores 0%%, which is agreement, not absence of '
        'evidence. <b>And note what voice isolation is here:</b> these stems '
        'are renders with the other two voices MUTED, which is not clean '
        'isolation on every tune &mdash; a tune whose voices interact through '
        'the shared filter or through ring/sync will not decompose this way, '
        'and the strips are then three views of a mix, not three voices.</p>\n'
        '</div>\n' % (strips, OURS_LABEL))


def _laxity_real_sequences(p) -> bool:
    """Opt a Laxity SF2 into the reader that decodes its REAL sequences.

    WHY FROM THE CONSUMER SIDE. sf2_viewer_core still runs
    `_parse_packed_sequences_laxity_sf2()` first, and it SUCCEEDS WITH GARBAGE,
    so the correct reader below it never runs. Flipping that dispatch inside the
    parser is a separate task (`laxity-dispatch-flip-needs-abpage-row-schedule`)
    because it changes what `self.sequences` means for six importing modules;
    asking for the right decode here changes it for this consumer only.

    WHAT THE WRONG DECODE LOOKS LIKE, so this is not taken on faith: the
    dispatched reader hands us three "sequences" of 197/174/139 rows on
    SF2/Angular.sf2. Those are the three ORDERLISTS read with the SEQUENCE
    grammar -- proved on the bytes in 34ed351 / docs/players/LAXITY.md. An
    orderlist is `transpose, sequence numbers..., $FF` and is 14 bytes here, but
    `_extract_sequence_at_address` terminates on $7F, so it runs past the $FF and
    keeps eating the file. All three then exceed the file's own
    default_sequence_length of 75 and every column is refused.

    IDEMPOTENT ON PURPOSE: once the parser's own dispatch is flipped it will have
    populated `laxity_orderlists` itself and this becomes a no-op, not a second
    decode.
    """
    if getattr(p, "laxity_orderlists", None):
        return True                          # the parser already did it
    if not getattr(p, "is_laxity_driver", False):
        return False
    fn = getattr(p, "_parse_laxity_real_sequences", None)
    if fn is None:
        return False                         # older parser -- leave it alone
    try:
        return bool(fn())
    except Exception:                                     # noqa: BLE001
        return False


def _track_orderlists(p) -> list:
    """Per-voice orderlists as `[{"sequence": n}, ...]`, whichever reader ran.

    A Laxity orderlist is a TRANSPOSE BYTE followed by sequence numbers, so entry
    0 is dropped -- it is not a sequence index, and walking it as one is what put
    another sequence's notes under a voice's heading before. The $FF terminator is
    already stripped by the parser's reader.

    Falls back to `orderlist_unpacked` for every non-Laxity file, which is the
    only shape Driver 11 and the rest have ever had.
    """
    ols = getattr(p, "laxity_orderlists", None) or []
    if ols:
        return [[{"sequence": int(n)} for n in (ol or [])[1:]] for ol in ols]
    return list(p.orderlist_unpacked or [])


def row_schedule(sf2_path: Path, max_rows: int | None = None) -> dict | None:
    """Per-track rows with the frame each one starts on, read from the SF2.

    max_rows DEFAULT IS NOW None -- NO CAP -- after two rounds of raising a
    constant only to have the corpus outgrow it
    (abpage-row-schedule-cap-still-truncates-four-files-at-2048). The prior
    round raised 512 -> 2048 and was STILL wrong: swept over all 411 readable
    .sf2 in SF2/ and out/ (`(ROOT/"SF2").glob("*.sf2")` + `(ROOT/"out").glob(
    "*.sf2")`, TOP-LEVEL ONLY -- an rglob over the same roots picks up 8,753
    files from nested build/pipeline output dirs and is NOT the corpus this
    module or its tests mean), out/hawkeye_subtune_0.sf2 sat at EXACTLY 2048
    on voice 0 -- clipped by the constant, same defect one threshold higher.
    Re-run with max_rows=100000 (i.e. effectively uncapped) over the same 411
    files: NOT ONE track hits that ceiling, hawkeye's true voice-0 length is
    2495 rows, and the corpus-wide largest __abRows payload (this module's
    own `rows_json` shape -- frame numbers only, not full row dicts) is
    UNCHANGED at 22,732 bytes (Sanxion.sf2) -- identical to the figure at the
    2048 cap, because Sanxion was already under 2048 per track and hawkeye's
    extra 447 rows of frame integers don't move the corpus max. Cost was
    never the argument for a ceiling; a ceiling only ever produced a new
    threshold to outgrow. So the cap is now OPT-IN: pass an explicit
    max_rows (tests do, to exercise `cut = True` below) and you get one;
    production's one caller does not, and gets the whole walk. A genuinely
    runaway decode is still caught upstream by the seqlen/pointer/over-read
    guard a few lines down -- that guard doesn't measure row COUNT at all,
    it refuses a sequence body that over-ran its own table, so it is
    unaffected by max_rows being None (see
    test_the_guard_STILL_refuses_a_genuinely_unbounded_body, which pins
    SF2/_test_commando.sf2's 11k+/13k+-entry bodies still refused).

    Earlier history, for the record -- max_rows DEFAULT WAS 512, WHICH
    TRUNCATED TWO OF ANGULAR'S THREE VOICES
    (abpage-row-schedule-truncates-two-voices-at-512-rows). Angular's own
    orderlists walk to 564/744/481 rows per voice -- voice 1 alone needed 744,
    232 past the old cap -- so tracks reported [512, 512, 481] with
    truncated == [0, 1] even though the page honestly said so. Raised rather
    than left in place or turned into a caller-set parameter, because the
    measured cost of doing the WHOLE walk is trivial: serialising
    row_schedule's own tracks into window.__abRows (the exact `rows_json`
    expression this module already uses to build the page) is 9,651 bytes at
    the old 512 cap and 11,639 bytes for Angular's full 1,789-row walk -- a
    1,988-byte (20.6%) increase, on a page whose CSS/script/HTML already run
    to tens of KB. A genuinely runaway decode (SF2/_test_commando.sf2, 11k+
    entries) is still caught upstream by the seqlen/overread guard above, not by
    this cap (see test_the_guard_STILL_refuses_a_genuinely_unbounded_body).

    2048 IS NOT COMFORTABLE HEADROOM, and saying so is the point of this
    paragraph. It was first justified as ">2.7x over Angular's longest voice
    (744)" -- true, and measured against ONE FILE. Swept over all 411 readable
    .sf2 in SF2/ and out/, the corpus does not agree: Chain_Reaction 1664,
    Unboxed_Ending_8580 1408, Cybernoid_II 1216, Cycles 1049. FOUR files are
    still truncated at 2048, and out/hawkeye_subtune_0.sf2 sits at EXACTLY 2048
    on voice 0 -- i.e. it is clipped by this constant, the same defect this
    change fixed for Angular, one threshold higher. The largest payload in that
    whole sweep is 22,732 bytes (Sanxion.sf2), so cost is NOT what argues for a
    ceiling here. Raising it again is cheap and is filed as
    abpage-row-schedule-cap-still-truncates-four-files-at-2048; it was left at
    2048 rather than raised blind because the three OTHER truncated files report
    tracks [0, 0, 0] with truncated [0, 1, 2] -- zero rows emitted yet flagged
    truncated, which is a different bug and would not be fixed by a bigger
    number (abpage-row-schedule-flags-empty-tracks-as-truncated).

    THE SCHEDULE COMES FROM THE FILE, NEVER FROM THE AUDIO. It would be easy
    to fit rows to the onsets our render actually produced and get a picture
    that always lines up -- and worthless, because a row rate that is WRONG is
    exactly what this view exists to show. Drift against the audio stays
    visible on purpose.

    The arithmetic, from docs/reference/SF2_FORMAT_SPEC.md and the parser:
      * the tempo table "defines song speed as FRAMES PER ROW", driver at 50 Hz
        (spec, Tempo Table); `music_data_info.default_tempo` is that value;
      * `SequenceEntry.duration` is "how many ticks this entry lasts"
        (sf2_viewer_core), so a row occupies `duration * tempo` frames;
      * a `duration == 0` entry is a TIE/continuation -- it advances no time.
        Angular: 64 entries in sequence 0, of which 37 are duration 0. Treating
        those as one row each would stretch the song by more than 2x.
    Cross-check on Angular: sum(duration) = 29 over sequence 0, x tempo 31 =
    899 frames = 18.0 s, against a 20 s render of a song that then loops. That
    is a sanity check on the ORDER OF MAGNITUDE, not a calibration -- nothing
    here is tuned to make it match.

    Returns None when the file cannot be parsed at all.
    """
    sys.path.insert(0, str(ROOT / "pyscript"))
    import logging
    # The parser narrates to stderr, so silence it -- but for the PARSE ONLY,
    # and restore on every path including the early returns. logging.disable()
    # is PROCESS-WIDE: leaking it here silences the host program's logging too.
    # It did exactly that, and the damage was invisible from inside this module
    # -- 27 unrelated tests in three other files started asserting against an
    # empty log, and they only failed in a FULL suite run, never in isolation.
    _prev_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        try:
            from sf2_viewer_core import SF2Parser
        except ImportError:
            return None
        try:
            p = SF2Parser(str(sf2_path))       # a PATH, never bytes
            if not p.parse():
                return None
        except Exception:                                 # noqa: BLE001
            return None
    finally:
        logging.disable(_prev_disable)

    mdi = p.music_data_info
    tempo = int(getattr(mdi, "default_tempo", 0) or 0)
    if tempo <= 0:
        return None
    _laxity_real_sequences(p)
    seqs = p.sequences or {}
    fmts = getattr(p, "sequence_formats", {}) or {}
    seqlen = int(getattr(mdi, "default_sequence_length", 0) or 0)
    # WAS THIS DECODE BOUNDED BY THE FILE'S OWN POINTER TABLE? That decides
    # whether the length guard below means anything at all.
    #
    # default_sequence_length is a DEFAULT, NOT A MAXIMUM -- SF2_FORMAT_SPEC.md,
    # "Contiguous Sequence Stacking": "Sequences in each track can have different
    # lengths - they stack like Tetris blocks." It is the length a NEW sequence
    # gets in the editor. So `len(rows) > seqlen` is not an over-read; it is
    # ordinary music, and refusing on it DROPPED WHOLE VOICES:
    #     Cycles.sf2   dsl 13 -> tracks [78, 0, 0]      105 refusals
    #     Unboxed.sf2  dsl 38 -> tracks [0, 512, 512]    22 refusals
    #     Angular.sf2  dsl 75 -> tracks [512, 512, 481]   0 -- the LUCKY case,
    #         its dsl merely happens to exceed its longest sequence, which is the
    #         only reason the guard ever looked correct.
    #
    # When laxity_seq_table is set, every body was cut at the NEXT POINTER
    # (sf2_viewer_core's `stop = ptrs[idx+1]`), so its length is structural and
    # needs no second opinion. When it is NOT set -- 25 of 47 Laxity SF2s, whose
    # table refuses to locate -- the fallback readers scan to the grammar's own
    # $7F with nothing bounding them, and that genuinely runs away:
    # _test_commando.sf2 yields bodies of 11,335 and 13,361 entries. The guard is
    # the only thing standing between that and the page, so it stays for exactly
    # that case. Pinned by test_the_length_guard_applies_only_to_UNBOUNDED_decodes.
    pointer_bounded = bool(getattr(p, "laxity_seq_table", None))
    tracks, degenerate, truncated, overread, fallback = [], [], [], [], []
    # AN ORDERLIST ENTRY POINTING AT A SEQUENCE THE READER NEVER
    # PRODUCED was, until now, the one way a track could come out empty
    # with NO reason recorded anywhere. `degenerate`, `truncated` and
    # `overread` were all reported; this was not, so the page fell
    # through to "this voice has no rows in the orderlist" -- which is
    # FALSE for exactly these files. Measured 2026-09-04 across the 12
    # staged songs: every one of the seven blank pages has a populated
    # orderlist (lens like [3,4,3] and [7,7,4]), and the ids it names
    # are simply absent from `p.sequences` -- 8 of 10 on
    # 2_Young_2_Die_native_part01, 17 of 18 on 5_Title_Tunes_song0_part01,
    # 2 of 3 on Beginning. The orderlist and the sequence table
    # disagree, which is a LOCATE failure and not an empty song.
    missing = []
    for tno, entries in enumerate(_track_orderlists(p)[:3]):
        rows, frame, cut = [], 0, False
        for ent in entries or []:
            sidx = ent.get("sequence")
            if sidx not in seqs:
                # Recorded, not skipped silently -- see `missing` above.
                missing.append((tno, sidx))
                continue
            rowsrc = seqs.get(sidx, [])
            # NOT DE-INTERLEAVED. The parser flags some sequences
            # `interleaved` and sf2_viewer_gui's comment describes such a
            # layout, so this code used to slice `rowsrc[tno::3]`. GROUND
            # TRUTH SAYS OTHERWISE: SF2/Angular.sf2 opened in SID Factory II
            # (Ctrl+P follow, F1) renders Track 3 as
            #   A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4 G-4 A-4 +++
            # which is sequence 2 read FLAT, all eleven notes, while its
            # de-interleaved lane matches nothing. One sequence per track.
            # De-interleaving was my own error on top of a correct reading.
            # AN OVER-READ SEQUENCE IS NOT THIS TRACK'S MUSIC. The file
            # declares its own sequence length (music_data_info.
            # default_sequence_length, 75 on Angular); a sequence decoding to
            # more rows than that is the decoder running past the real end.
            # Angular's sequence 1 yields 222 rows of nonsense that way --
            # notes like B-16, an octave that does not exist -- and unlike the
            # earlier all-ties case it DOES advance time, so the zero-advance
            # guard below never sees it. Refuse on the file's own number rather
            # than on a note-plausibility heuristic.
            if seqlen and not pointer_bounded and len(rowsrc) > seqlen:
                # This track's own sequence is unreadable -- Angular's sequence
                # 1 begins `note=$CB cmd=$FF` and then runs to zeros, i.e. the
                # parser located something that is not a sequence at all. But an
                # INTERLEAVED sequence already carries all three voices, so if
                # any valid one exists this track's music is in its lane. Take
                # it, and record the substitution so the column can say where
                # its rows came from rather than quietly showing another
                # sequence's notes -- which is the exact mistake that produced
                # the stacked-voices column in the first place.
                overread.append((tno, sidx, len(rowsrc)))
                rowsrc = []
            for e in rowsrc:
                if max_rows is not None and len(rows) >= max_rows:
                    cut = True
                    break
                note = int(getattr(e, "note", 0) or 0)
                if note == 0x7F:            # END terminates the sequence
                    break
                dur = int(getattr(e, "duration", 0) or 0)
                # Formatting comes from SequenceEntry's OWN methods, which are
                # documented as "SID Factory II editor format" -- note_name(),
                # instrument_display(), command_display(). Rolling my own
                # printed raw hex where the editor prints `--` and an
                # instrument INDEX (0xAB is instrument 0B, not AB), which is
                # why the column did not look like the editor.
                rows.append({
                    "f": frame, "seq": sidx, "dur": dur, "note": note,
                    "n": e.note_name() if hasattr(e, "note_name") else str(note),
                    "i": (e.instrument_display()
                          if hasattr(e, "instrument_display") else "--"),
                    "c": (e.command_display()
                          if hasattr(e, "command_display") else "--"),
                    "tie": dur == 0,
                })
                frame += dur * tempo
            if cut:
                break
        # A TRACK THAT ADVANCES NO TIME IS NOT A TRACK. Measured on
        # SF2/Angular.sf2: sequence 1 decodes to 667 entries of which 663 have
        # duration 0, against a file whose own default_sequence_length is 75 --
        # the decoder runs past the real end of that sequence and yields
        # hundreds of junk rows. Drawn, that is a column of plausible-looking
        # nonsense pinned at frame 0 forever; the whole point of this view is
        # to show a WRONG row rate, so a column that cannot be trusted must be
        # refused rather than rendered. The test is derived, not tuned: rows
        # exist but total advance is zero.
        if rows and rows[-1]["f"] == 0:
            degenerate.append(tno)
            rows = []
            # DEGENERATE WINS OVER TRUNCATED, and the two were being reported
            # together. `cut` says a cap stopped the walk; the block above then
            # throws the rows away for an unrelated reason. Reporting both left
            # three files claiming they had been cut short while emitting
            # nothing -- measured at max_rows=2048: BMX_Kidz, Human_Race and
            # Lakers_vs_Celtics each gave tracks [0, 0, 0] with
            # truncated == [0, 1, 2] AND degenerate == [0, 1, 2].
            #
            # "Emitted nothing, and was cut short" is a contradiction, and it
            # points at the wrong remedy: truncated invites a bigger cap, and a
            # bigger cap cannot help here. Uncapped, these same three still give
            # [0, 0, 0] -- the rows are refused because they advance no time,
            # which is exactly what `degenerate` already says. So a track that
            # was emptied here is degenerate, full stop.
            cut = False
        if cut:
            truncated.append(tno)
        tracks.append(rows)
    while len(tracks) < 3:
        tracks.append([])
    return {"tempo": tempo, "tracks": tracks,
            # WHERE the sequences came from, verbatim from the parser. The
            # packed heuristic's locate is measurably misaligned (seven rows
            # off on Angular, the one file with editor ground truth), so a
            # column drawn from it must be LABELLED, not presented as the
            # file's music. None on parsers that predate the field.
            "provenance": getattr(p, "sequence_provenance", None),
            "frames": max((t[-1]["f"] if t else 0) for t in tracks),
            "sequences": len(seqs), "degenerate": degenerate,
            "truncated": truncated,
            "overread": [{"track": t, "seq": sq, "rows": n}
                         for t, sq, n in overread],
            "missing_sequences": [{"track": t, "seq": sq}
                                  for t, sq in missing],
            "fallback": fallback,
            "default_sequence_length": seqlen}


def patterns_payload(name: str) -> dict | None:
    p = listen_dir() / ("%s.patterns.json" % name)
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def _note_name(n: int) -> str:
    """SF2 note byte to a name.

    126 is `$7E` = GATE_ON in this repo's own constant table (CLAUDE.md), not a
    pitch and not a tie -- it was labelled `===` here until the de-interleaving
    fix made it obvious the column was full of them.
    """
    if n == 126:
        return "GATE"
    if n <= 0:
        return "..."
    names = ("C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-")
    return "%s%d" % (names[n % 12], n // 12)


def patterns_card(pat: dict | None) -> str:
    """Three per-voice row columns that scroll with playback."""
    if not pat:
        return ""
    if not any(pat.get("tracks") or []):
        # EVERY VOICE REFUSED. Returning "" here showed the reader
        # NOTHING -- no card, no reason -- on SEVEN of the twelve songs
        # staged 2026-09-04, which is the worst of both worlds: the page
        # looked as though pattern data had never been asked for, when in
        # fact every voice had been refused and the reason was recorded.
        # Fall through instead and let the per-voice branches below say
        # why each one was refused.
        #
        # Silence is still correct when there is genuinely nothing to
        # report -- an all-empty payload with no recorded reason -- which
        # is what test_patterns_card_absent_without_a_payload pins.
        if not (pat.get("degenerate") or pat.get("overread")
                or pat.get("missing_sequences") or pat.get("truncated")):
            return ""
    cols = ""
    for tno, rows in enumerate(pat["tracks"][:3]):
        if not rows:
            over = [o for o in (pat.get("overread") or []) if o.get("track") == tno]
            miss = [m for m in (pat.get("missing_sequences") or [])
                    if m.get("track") == tno]
            if over:
                why = ("its sequence (%s) decodes to %d rows against a declared "
                       "sequence length of %s &mdash; the decoder ran past the "
                       "real end, and what follows is not this voice's music"
                       % (over[0].get("seq"), over[0].get("rows"),
                          pat.get("default_sequence_length") or "?"))
            elif tno in (pat.get("degenerate") or []):
                why = ("its sequence decodes to rows that advance no time at "
                       "all, so they cannot be this voice's")
            elif miss:
                why = ("its orderlist names sequence(s) %s, which the reader "
                       "never produced &mdash; the orderlist and the sequence "
                       "table disagree, so the music was not located rather "
                       "than absent"
                       % ", ".join(str(m.get("seq")) for m in miss[:6]))
            else:
                why = "this voice has no rows in the orderlist"
            cols += ('<div class="trkcol"><h3>Voice %d</h3>'
                     '<div class="trkbody empty"><p>No pattern shown: %s. '
                     'Refused rather than drawn &mdash; a column of rows pinned '
                     'at frame 0 would look like a real part.</p></div></div>'
                     % (tno + 1, why))
            continue

        # Which sequence these rows actually came from. Printed because a
        # column that silently shows ANOTHER sequence's notes is exactly the
        # mistake that produced the stacked-voices bug -- if a substitution
        # happens, it should be visible on the face of the column.
        fb = [x for x in (pat.get("fallback") or []) if x.get("track") == tno]
        used = sorted({r.get("seq") for r in rows if r.get("seq") is not None})
        label = ("seq " + "+".join(str(x) for x in used)) if used else ""
        if fb:
            label += " &middot; own seq unreadable"

        body = ""
        for i, r in enumerate(rows):
            cls = "trkrow" + (" tie" if r.get("tie") else "")
            body += ('<div class="%s" data-i="%d"><span class="ix">%03d</span>'
                     '<span class="n">%s</span><span class="instr">%s</span>'
                     '<span class="cmd">%s</span></div>'
                     % (cls, i, i, r.get("n") or _note_name(r.get("note", 0)),
                        r.get("i", "--"), r.get("c", "--")))
        # The rows live in an inner element that is MOVED WITH A TRANSFORM,
        # not scrolled. scrollTop on an overflow:hidden box is the obvious
        # way and it cost two rounds of "it does not scroll" that I could not
        # reproduce; translateY has no dependence on scroll-container
        # behaviour, composites on the GPU, and is what a tracker does anyway.
        cols += ('<div class="trkcol">'
                 '<h3>Voice %d<span class="seqlab">%s</span></h3>'
                 '<div class="trkhead"><span class="ix">row</span>'
                 '<span class="n">note</span><span class="instr">ins</span>'
                 '<span class="cmd">cmd</span></div>'
                 '<div class="trkbody" id="trk%d">'
                 '<div class="trkinner" id="trkin%d">%s</div></div></div>'
                 % (tno + 1, label, tno, tno, body))
    prov = pat.get("provenance") or {}
    if prov and not prov.get("structural"):
        # THE LABEL THIS BANNER EXISTS FOR. Some Laxity SF2s decode via the
        # file's own pointer table (structural lengths); the rest fall to a
        # heuristic locate that is SEVEN ROWS OFF on Angular, the one file
        # with editor ground truth. Refusing would blank those files' pattern
        # view entirely; drawing them unlabelled presents a misaligned decode
        # as the file's music. So: emit, and say what it is.
        provbanner = ('  <div class="trkstat">heuristic decode '
                      '(&#8220;%s&#8221;), unverified &mdash; the sequence '
                      'table did not locate, so these rows come from a scan '
                      'whose alignment is not established. On the one file '
                      'with editor ground truth the same scan lands seven '
                      'rows off.</div>\n'
                      % prov.get("reader", "?"))
    else:
        provbanner = ""
    return (
        '<div class="card">\n  <h2>The pattern, as our conversion wrote it</h2>\n'
        + provbanner +
        '  <div class="trkstat" id="trkstat">scroll: waiting for playback</div>\n'
        '  <div class="trk">%s</div>\n'
        '  <p class="trknote">Rows are placed by the tempo written IN THE FILE '
        '(%d frames per row at 50&nbsp;Hz), never fitted to the audio &mdash; so '
        'if the highlight drifts against what you hear, <b>that drift is the '
        'row rate being wrong</b>, and it is the only thing this view shows that '
        'the envelopes cannot. It follows OUR render\'s clock, because these are '
        'our conversion\'s rows. A <code>===</code> row is a tie: it advances no '
        'time, which is why the highlight rests on the row above it. A '
        '<code>+++</code> row is gate-on/sustain ($7E) and <code>---</code> is '
        "gate-off, in SID Factory II's own notation. Click any "
        'row to jump both sides there and pause.%s</p>\n</div>\n'
        % (cols, pat.get("tempo", 0), _pattern_caveats(pat)))


def _pattern_caveats(pat: dict) -> str:
    out = ""
    deg = pat.get("degenerate") or []
    if deg:
        out += (" <b>Voice %s refused</b>: the decoder produced rows advancing "
                "no time at all (on the file this was first measured against, "
                "one sequence yielded 667 entries of which 663 had zero "
                "duration, against a declared sequence length of %s). That is a "
                "limit of the SF2 sequence decoder, not evidence about the "
                "conversion."
                % (", ".join(str(d + 1) for d in deg),
                   pat.get("default_sequence_length") or "?"))
    miss = pat.get("missing_sequences") or []
    if miss:
        out += (" <b>%d orderlist entr%s</b> name a sequence the reader never "
                "produced (voice%s %s). The orderlist and the sequence table "
                "disagree: the music was not LOCATED, which is a limit of the "
                "SF2 reader on this driver layout and is not evidence about the "
                "conversion."
                % (len(miss), "y" if len(miss) == 1 else "ies",
                   "" if len({m["track"] for m in miss}) == 1 else "s",
                   ", ".join(str(t + 1) for t in
                             sorted({m["track"] for m in miss}))))
    trunc = pat.get("truncated") or []
    if trunc:
        out += (" Voice %s was truncated at the row cap, so the tail is not "
                "shown." % ", ".join(str(t + 1) for t in trunc))
    return out


def instrmap_payload(name: str) -> dict | None:
    """`<name>.instrmap.json` as written by the `instrmap` subcommand, or None."""
    p = listen_dir() / ("%s.instrmap.json" % name)
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def instrmap_card(im: dict | None) -> str:
    """WHICH instrument differs, or the verdict explaining why there is no table.

    The verdict comes first and is always shown, because on this corpus a
    third of files cannot be keyed at all: `instrument_map_sweep` grades 27
    files as 16 reliable / 6 insufficient-data / 2 no-trace / 2 degenerate /
    1 unusable. A card that quietly showed nothing for those would be
    indistinguishable from a card for a song with no problems.

    WHETHER A TABLE IS SHOWN IS NOT DECIDED HERE. `instrument_map.Verdict`
    owns that rule (its `usable` property) and the report tool only computes
    rows when it says so -- so an empty `map` IS the refusal, and this reads it
    rather than re-deriving it. Worth knowing before "fixing" that:
    `degenerate` is deliberately usable -- one ADSR over every note is a
    perfectly stable key that separates nothing, and the module's own docstring
    says the caller should SAY so rather than refuse. Hard-coding a
    "degenerate means no table" rule here would contradict the module.
    """
    if not im:
        return ""
    key = im.get("key") or {}
    verdict = str(key.get("verdict") or "unknown")
    why = str(key.get("why") or "")
    rows = im.get("map") or []
    orphans = im.get("orphans") or []

    head = ('<div class="card">\n  <h2>Which instrument</h2>\n'
            '  <p class="verdictline"><b>%s</b> &mdash; %s</p>\n'
            % (verdict, why))

    if not rows:
        # The refusal, stated as a result. Wording follows the report tool's
        # own: "That is the result, not a failure to produce one."
        return head + (
            '  <p class="caveat">No mapping table is emitted for this tune. '
            'That is the result, not a failure to produce one &mdash; the ADSR '
            'key does not identify instruments here, so any table would be '
            'naming records that do not exist. See <code>'
            'sidm2/instrument_map.py</code> for the files each verdict was '
            'calibrated against.</p>\n</div>\n')

    # THREE row states, not two. The report tool's own vocabulary is `ok`,
    # `unused both sides`, and a description of the difference -- and the
    # middle one is NEITHER agreement NOR a defect: it is a record that neither
    # side ever sounds, so there is no evidence about it in either direction.
    # On the first real file measured here that was 18 of 27 rows. Folding it
    # in with the differences painted two thirds of the table as broken; folding
    # it in with `ok` would have been the vacuous-agreement bug instead.
    def _state(v: str) -> str:
        if v == "ok":
            return "agree"
        if "unused" in v:
            return "noevidence"
        return "differs"

    body, counts = "", {"agree": 0, "noevidence": 0, "differs": 0}
    for r in rows:
        recs = ", ".join(str(x) for x in (r.get("records") or []))
        v = str(r.get("verdict") or "")
        st = _state(v)
        counts[st] += 1
        body += ('<tr class="%s"><td>%s</td><td>%s</td><td>%s (%s)</td>'
                 "<td>%s (%s)</td><td>%s</td></tr>"
                 % (st, recs, r.get("adsr", "?"),
                    r.get("orig_wave", "?"), r.get("orig_notes", 0),
                    r.get("ours_wave", "?"), r.get("ours_notes", 0), v))

    extra = ('  <p class="caveat"><b>%d record(s) differ</b>, %d agree, and %d '
             'are sounded by NEITHER side. That last group is <i>no evidence</i> '
             '&mdash; not agreement and not a defect &mdash; and is greyed '
             'rather than counted either way.</p>\n'
             % (counts["differs"], counts["agree"], counts["noevidence"]))
    if verdict == "suspect":
        extra += ('  <p class="caveat">Key graded <b>suspect</b>: usable, but '
                  'treat any instrument seen once or twice as unconfirmed.</p>\n')
    if verdict == "degenerate":
        extra += ('  <p class="caveat">Key graded <b>degenerate</b>: a single '
                  'ADSR covers every note, so the key is perfectly stable and '
                  'carries no information. The table below separates nothing '
                  '&mdash; this file\'s instruments, if it has several, differ '
                  'somewhere ADSR does not reach.</p>\n')
    if orphans:
        extra += ('  <p class="caveat">%d envelope(s) sound that NEITHER side\'s '
                  'table declares: %s. A blind spot in the key, not necessarily '
                  'a conversion gap.</p>\n'
                  % (len(orphans),
                     ", ".join("%s x%s" % (o.get("adsr"), o.get("notes"))
                               for o in orphans[:6])))
    lv = im.get("layout_verdict")
    if lv:
        extra += ('  <p class="caveat">Instrument table located by <b>search</b>, '
                  'never a constant (layout: %s). Reading a documented address '
                  'blind has matched 0 of 10 sounded envelopes on a file whose '
                  'table was elsewhere.</p>\n' % lv)

    return head + (
        '  <div class="scroll"><table>\n'
        '    <thead><tr><th>records</th><th>adsr</th><th>original</th>'
        '<th>ours</th><th></th></tr></thead>\n'
        '    <tbody>%s</tbody>\n  </table></div>\n%s</div>\n' % (body, extra))


def page(name: str, chips_row: dict, notes: list[str], version: str,
         embed: bool, index_link: bool, blind_row: dict | None = None) -> str:
    pretty = name.replace("_", " ")
    blind_row = blind_row or {}
    # `title` rather than a footnote: the blindness belongs ON the number, so a
    # reader cannot take a null for "clean" without meeting the caveat. A chip
    # with a known blind spot is also marked, so the caveat is discoverable
    # without hovering every chip to find which ones have one.
    chips = "".join(
        '<div class="chip%s"%s><span>%s</span><b>%s</b></div>'
        % (" hasblind" if blind_row.get(k) else "",
           ' title="%s"' % blind_row[k].replace('"', "&quot;") if blind_row.get(k) else "",
           k, v)
        for k, v in (chips_row or {}).items() if v and v != "-")
    if not chips:
        # An honest gap, never an empty rail: a page with no numbers must not
        # look like a page whose numbers were all fine.
        chips = ('<div class="chip"><span>no measured row</span>'
                 '<b>not in --chips</b></div>')

    bullets = "".join("<li>%s</li>" % md(n) for n in notes) or (
        "<li>No notes were written for this tune. Anything heard here is "
        "something no check in the repo can see &mdash; which is the reason "
        "this pass exists.</li>")

    a_rendered = wav_rendered(orig_wav(name))
    b_rendered = wav_rendered(ours_wav(name))

    if embed:
        a_src = wav_uri(orig_wav(name))
        b_src = wav_uri(ours_wav(name))
        provenance = ("Both renders are inlined in this page. Same renderer, "
                      "same settings, same duration on both sides.")
    else:
        a_src = "%s.original.wav" % name
        b_src = "%s.%s.wav" % (name, OURS)
        provenance = ("Plays <code>%s</code> and <code>%s</code> from this "
                      "directory. If the browser refuses <code>file://</code> "
                      "media, serve the directory instead." % (a_src, b_src))

    # Per-voice pairs, if `stage --voices` produced them. Never under --embed:
    # six more multi-megabyte data URIs is not a page.
    voice_map, voice_row = {}, ""
    if not embed:
        have = all((listen_dir() / ("%s.v%d.%s.wav" % (name, v, side))).exists()
                   for v in (1, 2, 3) for side in ("original", OURS))
        if have:
            voice_map = {"all": [a_src, b_src]}
            for v in (1, 2, 3):
                voice_map["v%d" % v] = ["%s.v%d.original.wav" % (name, v),
                                        "%s.v%d.%s.wav" % (name, v, OURS)]
            buttons = '<button data-voice="all" aria-pressed="true">All</button>'
            buttons += "".join(
                '<button data-voice="v%d" aria-pressed="false">Voice %d</button>'
                % (v, v) for v in (1, 2, 3))
            voice_row = (
                '<div class="voices" id="voices">'
                '<span class="lbl">Solo</span>%s'
                '<span class="note" id="voicenote">all three voices, as '
                'staged</span></div>' % buttons)

    spec = spectrogram_payload(name)
    pat = patterns_payload(name)
    back = ('<a href="index.html">&larr; all tunes</a> &middot; ' if index_link else "")

    return """<meta charset="utf-8">
<title>%(pretty)s A/B</title>
<style>%(css)s</style>
<div class="wrap">
<header>
  <div class="eyebrow">%(back)sSIDM2 listening pass &middot; %(version)s &middot; built %(built)s</div>
  <h1>%(pretty)s<small>original <code>.sid</code> against the %(ours)s, switched in place</small></h1>
  <div class="rail">%(chips)s</div>
</header>

<div class="rig" id="rig">
  <div class="sources">
    <button class="src" data-side="a" aria-pressed="true">
      <span class="key">Source A &middot; press <kbd>1</kbd></span>
      <span class="name" id="nameA">Original .sid</span>
      <span class="rendered">%(a_rendered)s</span>
    </button>
    <button class="src" data-side="b" aria-pressed="false">
      <span class="key">Source B &middot; press <kbd>2</kbd></span>
      <span class="name" id="nameB">%(ours)s</span>
      <span class="rendered">%(b_rendered)s</span>
    </button>
  </div>
  <div class="transport">
    <button class="play" id="play" aria-label="Play">&#9654;</button>
    <div class="scrub">
      <input type="range" id="seek" min="0" max="1000" value="0" step="1" aria-label="Position">
      <div class="time"><span id="now">0:00</span><span id="dur">&ndash;:&ndash;&ndash;</span></div>
    </div>
  </div>
  <div class="loop">
    <label class="toggle"><input type="checkbox" id="looping"> Loop</label>
    <span>&middot; a passage you cannot decide on is worth hearing four times, not once</span>
  </div>
  <div class="sync">
    <span>Sync</span>
    <input type="range" id="syncr" min="-500" max="500" value="0" step="1"
           aria-label="Sync offset in milliseconds">
    <b id="syncv">0 ms</b>
    <button class="ghost" id="syncauto">auto</button>
    <button class="ghost" id="synczero">0</button>
    <span id="syncwhy">&mdash; a converted build can reach its first note a few frames after the original</span>
  </div>
  <div class="mode">
    <label class="toggle"><input type="checkbox" id="blind"> Blind &mdash; hide which is which</label>
    <button class="ghost" id="guessA" hidden>Left is the original</button>
    <button class="ghost" id="guessB" hidden>Right is the original</button>
    <span class="verdict" id="verdict"></span>
    <span class="tally" id="tally"></span>
  </div>
  %(voice_row)s
</div>

<div class="card wave">
  <h2>Both sides, drawn</h2>
  <div class="msg" id="wavemsg">Reading both renders&hellip;</div>
  <canvas id="wave" hidden></canvas>
  <div class="legend">
    <button type="button" class="swatch orig" data-trace="a" aria-pressed="true"><i></i>original</button>
    <button type="button" class="swatch ours" data-trace="b" aria-pressed="true"><i></i>%(ours)s</button>
    <button type="button" class="swatch diff" data-trace="d" aria-pressed="true"><i></i>|difference|, lower strip</button>
    <span>click a key to hide it &middot; click the picture to seek both</span>
    <span class="stat" id="wavestat"></span>
  </div>
  <p class="caveat"><b>This is amplitude, and amplitude is not fidelity.</b>
  It shows dropped or extra notes, note lengths, missing drums, silence, and
  tempo drift &mdash; the two traces shear apart as the clocks part company.
  It cannot show <b>pitch</b>, <b>timbre</b> or <b>filter</b>: two completely
  different notes of the same loudness draw the same shape. The
  <code>mean&nbsp;|&Delta;|</code> beside the legend is the average gap
  between the two envelopes, not a score &mdash; read it only as "how far
  apart these pictures are".</p>
</div>

%(voicewave)s
%(spectrogram)s
%(patterns)s
%(instrmap)s
<div class="card">
  <h2>What to listen for</h2>
  <ul>%(bullets)s</ul>
</div>
<footer>
  <div><kbd>Space</kbd> play &middot; <kbd>1</kbd>/<kbd>2</kbd> or <kbd>&larr;</kbd>/<kbd>&rarr;</kbd> switch source &middot; <kbd>L</kbd> loop &middot; both tracks run in sync, so switching never loses your place.</div>
  <div>%(provenance)s</div>
  <div>Numbers in the rail above are quoted from the file passed to <code>--chips</code>; this page measures nothing of its own except the two <code>mean&nbsp;|&Delta;|</code> figures, which are labelled as pictures rather than scores.</div>
</footer>
</div>
<audio id="au" preload="auto" src="%(a_src)s"></audio>
<audio id="bu" preload="auto" src="%(b_src)s"></audio>
<script>window.__abVoices = %(voice_map)s;
window.__abOursLabel = %(ours_json)s;
window.__abRows = %(rows_json)s;
window.__abSpectrogram = %(spectrogram_json)s;</script>
<script>%(script)s</script>
""" % dict(pretty=pretty, css=CSS, back=back, version=version, chips=chips,
           bullets=bullets, provenance=provenance, a_src=a_src, b_src=b_src,
           a_rendered=a_rendered, b_rendered=b_rendered, ours=OURS_LABEL,
           ours_json=json.dumps(OURS_LABEL),
           # When THIS page was generated. The provenance stamp on each WAV
           # says when the audio was rendered; this says when the markup and
           # the script came out, which is the question you are asking when a
           # fix appears not to have landed.
           built=datetime.now().strftime("%H:%M:%S"),
           voice_row=voice_row, voice_map=json.dumps(voice_map),
           voicewave=voicewave_card(voice_map),
           instrmap=instrmap_card(instrmap_payload(name)),
           patterns=patterns_card(pat),
           rows_json=json.dumps([[r["f"] for r in t] for t in
                                 (pat["tracks"][:3] if pat else [[], [], []])]),
           spectrogram=spectrogram_card(spec),
           spectrogram_json=json.dumps(spec) if spec else "null",
           script=SCRIPT)


def index(names: list[str], rows: dict, version: str) -> str:
    # The columns are whatever --chips actually carried, in first-seen order,
    # rather than a hard-coded list that silently prints em-dashes when the
    # report changes shape.
    cols: list[str] = []
    for n in names:
        for k in (rows.get(n) or {}):
            if k not in cols:
                cols.append(k)
    cols = cols[:5]
    head = "".join("<th>%s</th>" % c for c in cols)
    body = ""
    for n in names:
        r = rows.get(n, {})
        cells = "".join("<td>%s</td>" % (r.get(c) or "&mdash;") for c in cols)
        body += ('<tr><td><a href="%s.html">%s</a></td>%s</tr>'
                 % (n, n.replace("_", " "), cells))
    return """<meta charset="utf-8">
<title>SIDM2 Listening Pass</title>
<style>%(css)s</style>
<div class="wrap">
<header>
  <div class="eyebrow">SIDM2 &middot; %(version)s &middot; %(count)d tune(s)</div>
  <h1>Listening pass<small>Each page plays the original and the conversion together and swaps which one you hear, so a switch never loses your place.</small></h1>
</header>
<div class="card">
  <h2>Staged tunes</h2>
  <div class="scroll"><table>
    <thead><tr><th>tune</th>%(head)s</tr></thead>
    <tbody>%(body)s</tbody>
  </table></div>
</div>
<footer>
  <div>Any columns above are quoted verbatim from the <code>--chips</code> file. They compare what is PLAYED, never how it sounds &mdash; which is what these pages are for.</div>
</footer>
</div>
""" % dict(css=CSS, version=version, count=len(names), head=head, body=body)


def staged_names() -> list[str]:
    """Tune names with a staged pair, excluding the per-voice solo renders.

    The `.v1`/`.v2`/`.v3` stems are the SAME tune with two voices muted, not
    tunes of their own -- globbing them in would give three extra "songs" per
    staged file, each with no row and a page nobody wants.
    """
    d = listen_dir()
    if not d.exists():
        return []
    return sorted(p.name[: -len(".original.wav")]
                  for p in d.glob("*.original.wav")
                  if not re.search(r"\.v[123]$", p.name[: -len(".original.wav")]))


def prune_stale_pages(names: list[str]) -> list[Path]:
    """Delete pages this build no longer produces, and return what it deleted.

    A page outlives the staged pair it was built from -- staging never deletes
    its own output -- so a pair removed from `build/listen` would otherwise
    leave a page behind, still reachable by URL and still linked from a stale
    index a reader had open. Nothing else here carries a `.html` suffix, so
    "every `.html` whose page-name is not in `names`" removes exactly the
    pages a rebuild stopped producing: never a staged WAV, and never
    `index.html`, which the caller rewrites unconditionally right after.
    """
    keep = set(names)
    removed: list[Path] = []
    d = listen_dir()
    if not d.exists():
        return removed
    for f in sorted(d.glob("*.html")):
        if f.name == "index.html":
            continue
        stem = f.stem                                  # strips one ".html"
        if stem.endswith(".embed"):
            stem = stem[: -len(".embed")]
        if stem not in keep:
            f.unlink()
            removed.append(f)
    return removed


# ---------------------------------------------------------------------------
# serving
# ---------------------------------------------------------------------------

import http.server as _http_server


class _RangeHandler(_http_server.SimpleHTTPRequestHandler):
    """A static handler that honours HTTP Range. The stock one does not.

    `SimpleHTTPRequestHandler` ignores `Range` entirely: it answers every
    request with `200 OK` and the WHOLE file, and advertises no
    `Accept-Ranges`. For HTML that is merely wasteful. For a multi-megabyte
    WAV driving an `<audio>` element it is a bug with an audible symptom --
    the media pipeline asks for a byte range to seek or to refill, is handed
    the file from byte 0 again, and replays the opening seconds. h2g chased
    that twice and misdiagnosed it both times as a stale render, because the
    WAV on disk measured clean each time; the file was never the problem. It
    is also why an automated browser's `readyState` can sit at 0 forever.

    Two changes and no more: advertise and implement single-range requests,
    and speak HTTP/1.1 so a keep-alive connection is available. Multi-range
    (`bytes=0-99,200-299`) is not implemented -- no browser uses it for media
    -- and is answered as a normal 200 rather than wrongly.
    """

    protocol_version = "HTTP/1.1"

    def send_head(self):
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m or (not m.group(1) and not m.group(2)):
            return super().send_head()          # unsatisfiable shape: 200
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        try:
            size = os.fstat(f.fileno()).st_size
            first, last = m.group(1), m.group(2)
            if first:
                start = int(first)
                end = int(last) if last else size - 1
            else:                                # "bytes=-N": the final N bytes
                start = max(0, size - int(last))
                end = size - 1
            end = min(end, size - 1)
            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                f.close()
                return None
            self.send_response(206)
            self.send_header("Content-type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range",
                             "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Last-Modified", self.date_time_string(
                os.fstat(f.fileno()).st_mtime))
            self.end_headers()
            f.seek(start)
            # copyfile() would send to EOF; hand back only the slice asked for.
            return _Slice(f, end - start + 1)
        except Exception:
            f.close()
            raise

    def send_response(self, code, message=None):
        # Advertise range support on every response EXCEPT the 206, which sets
        # the header itself -- a flag rather than scanning the header buffer,
        # which is a list of bytes and cannot be searched for a str.
        super().send_response(code, message)
        if code != 206:
            self.send_header("Accept-Ranges", "bytes")
        # NEVER CACHE. This server exists to look at pages that are being
        # rebuilt underneath it, and the stock handler sends Last-Modified with
        # no Cache-Control -- so a plain reload serves the browser's copy and
        # a fix that shipped correctly appears not to have shipped at all.
        # That cost two rounds of "it still does not work" on a page whose
        # script was already fixed on disk.
        self.send_header("Cache-Control", "no-store, must-revalidate")

    def log_message(self, fmt, *args):        # keep the console readable
        pass


class _Slice:
    """A read-only file view of exactly `remaining` bytes, for copyfile()."""

    def __init__(self, fh, remaining):
        self._fh, self._left = fh, remaining

    def read(self, n=-1):
        if self._left <= 0:
            return b""
        if n is None or n < 0 or n > self._left:
            n = self._left
        chunk = self._fh.read(n)
        self._left -= len(chunk)
        return chunk

    def close(self):
        self._fh.close()


def _port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Is something already listening there?

    WHY A PROBE, RATHER THAN LETTING bind() FAIL. `http.server.HTTPServer` sets
    `allow_reuse_address = True`, and on Windows SO_REUSEADDR lets a second
    process bind an address that is ALREADY IN USE. Measured 2026-09-04 against
    a live server on 8791: the second bind SUCCEEDED. Two servers then hold the
    port, which one answers any given connection is undefined, and a reader can
    be served a `build/listen` snapshot belonging to a process they have
    forgotten about -- silently, because both answer 200.

    That makes `serve`'s `except OSError` branch effectively DEAD on Windows for
    the in-use case. It is kept, because it still catches a privileged port, a
    bad interface, and the POSIX in-use error.

    THE REUSE FLAG IS DELIBERATELY NOT TURNED OFF. On POSIX it is what lets this
    server restart immediately after a crash instead of waiting out TIME_WAIT,
    which is the case it is most often restarted in. Refusing early costs
    nothing there and fixes the Windows shadow.

    A connect probe races a process starting between the probe and the bind.
    That race is not worth closing for a loopback dev server: it replaces a
    silent wrong answer with a rare and obvious one.
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.35)
        return probe.connect_ex((host, port)) == 0


def serve(port: int) -> int:
    """Serve build/listen on 127.0.0.1 until interrupted.

    A page opened as a file:// URL plays fine but cannot DRAW: the overlay and
    the automatic sync both read the two WAVs with fetch(), which browsers
    refuse on file://. Rather than leave that as a message telling the reader
    to go and find a web server, the tool is the web server. Loopback only --
    nothing here is meant to leave the machine.
    """
    import functools
    import http.server

    if _port_in_use(port):
        # Refused BEFORE binding: on Windows the bind would otherwise succeed
        # and shadow the running server rather than failing.
        print("127.0.0.1:%d is already serving -- refusing to start a second "
              "server on that port." % port)
        print("Almost always an earlier `abpage serve` still running in the "
              "background; stop that process, or use a different port:")
        print("    py -3 pyscript/abpage.py serve --port %d" % (port + 1))
        return 2

    handler = functools.partial(_RangeHandler, directory=str(listen_dir()))
    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        print("cannot bind 127.0.0.1:%d -- %s" % (port, exc))
        return 2
    print("http://127.0.0.1:%d/index.html   (ctrl-c to stop)" % port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
        print("stopped")
    finally:
        httpd.server_close()
    return 0


# ---------------------------------------------------------------------------


def _version() -> str:
    try:
        sys.path.insert(0, str(ROOT))
        from sidm2 import __version__
        return "v%s" % __version__
    except Exception:                                    # noqa: BLE001
        return "unversioned"


def chips(out_path, with_onset: bool, verbose: int) -> int:
    """Write a --chips JSON for every staged pair. Renders NOTHING.

    Separate from `build` on purpose: the numbers are a pure function of the
    staged WAVs, so they survive a rebuild and can be regenerated without
    re-staging -- and keeping the computation out of `build` keeps `build`
    dependency-free (stdlib only), which is what lets someone who only wants to
    LISTEN build the pages without this repo's requirements installed.
    """
    # ROOT on the path FIRST: run as a script (`py -3 pyscript/abpage.py`),
    # sys.path[0] is pyscript/, not the repo root, so `pyscript.abpage_chips`
    # is not importable. The test suite hid this because it inserts ROOT at
    # import time -- caught only by running the tool, which is the same lesson
    # this repo's fidelity docstring already records twice.
    sys.path.insert(0, str(ROOT))
    from pyscript.abpage_chips import ChipRefusal, chips_for_pair

    names = staged_names()
    if not names:
        print("no staged pairs in %s -- run `abpage.py stage ...` first"
              % listen_dir())
        return 2
    doc, refused = {}, []
    for n in names:
        try:
            c, b = chips_for_pair(orig_wav(n), ours_wav(n), with_onset=with_onset)
        except ChipRefusal as exc:
            # Named, never silent: a tune missing from the rail must be
            # distinguishable from a tune whose numbers were all fine.
            refused.append((n, str(exc)))
            continue
        doc[n] = {"chips": c, "blind": b}
        if verbose:
            print("  %-28s %s" % (n, "  ".join("%s=%s" % kv for kv in c.items())))
    out = Path(out_path) if out_path else listen_dir() / "chips.json"
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print("%d tune(s) -> %s" % (len(doc), out))
    for n, why in refused:
        print("  REFUSED %s: %s" % (n, why))
    if not with_onset:
        print("onset/offset omitted (--onset to include; it is ordinal-only "
              "with no gate and no floor -- see abpage_chips.py)")
    return 0


def instrmap(only: str | None, seconds: int, verbose: int) -> int:
    """Run the instrument map for staged tunes into `<name>.instrmap.json`.

    OPT-IN and never part of `build`: this traces TWO emulations per song
    (the original and ours), which is minutes across a corpus where a page
    rebuild is seconds. h2g's equivalent is opt-in for exactly this reason.

    Delegates wholly to `pyscript/instrument_map_report.py --json` -- the same
    tool `instrument-map.bat` runs. Nothing about instrument identification is
    re-derived here, and the `--json` path is used rather than its Markdown so
    there is no table to scrape: a scraper that stops matching returns nothing
    and renders as "no problems found".
    """
    import subprocess

    names = [n for n in staged_names() if only in (None, n)]
    if not names:
        print("no staged pairs in %s" % listen_dir())
        return 2
    ok = skipped = 0
    for n in names:
        src = sources_for(n)
        if not src or not src.get("converted"):
            # Staged before the sidecar existed. Named, not silent: the card is
            # simply absent otherwise, which reads as "nothing to report".
            print("  SKIP %s: no %s.sources.json -- re-stage it to record which "
                  ".sid/.sf2 it came from" % (n, n))
            skipped += 1
            continue
        cmd = [sys.executable, str(ROOT / "pyscript" / "instrument_map_report.py"),
               src["original"], src["converted"], "--json",
               "-t", str(seconds or src.get("seconds") or 20)]
        if src.get("driver_init") is not None:
            cmd += ["--init", hex(src["driver_init"])]
        if src.get("driver_play") is not None:
            cmd += ["--play", hex(src["driver_play"])]
        # encoding='utf-8' explicitly: text=True alone decodes with the LOCALE
        # codec, which on Windows mangles the em-dashes the report tool writes
        # into its verdict prose -- and that prose is rendered verbatim on the
        # page, so the mojibake ships.
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(ROOT))
        if r.returncode != 0:
            print("  FAILED %s: %s" % (n, (r.stderr or r.stdout).strip()[:200]))
            continue
        try:
            doc = json.loads(r.stdout)
        except ValueError:
            print("  FAILED %s: the report did not emit JSON" % n)
            continue
        (listen_dir() / ("%s.instrmap.json" % n)).write_text(
            json.dumps(doc, indent=1), encoding="utf-8")
        ok += 1
        if verbose:
            k = doc.get("key") or {}
            print("  %-26s %-18s %d row(s)"
                  % (n, k.get("verdict"), len(doc.get("map") or [])))
    print("%d instrument map(s) -> %s%s"
          % (ok, listen_dir(), ("; %d skipped" % skipped) if skipped else ""))
    print("re-run `abpage.py build` to put them on the pages")
    return 0


def patterns(only: str | None, verbose: int) -> int:
    """Read each staged tune's converted .sf2 into `<name>.patterns.json`.

    Cheap -- a file parse, no emulation -- so unlike `instrmap` this could
    reasonably be folded into `build` later. It is kept separate for now so
    `build` stays stdlib-only and dependency-free.
    """
    names = [n for n in staged_names() if only in (None, n)]
    if not names:
        print("no staged pairs in %s" % listen_dir())
        return 2
    ok = skipped = 0
    for n in names:
        src = sources_for(n)
        if not src or not src.get("converted"):
            print("  SKIP %s: no %s.sources.json -- re-stage it" % (n, n))
            skipped += 1
            continue
        conv = Path(src["converted"])
        if conv.suffix.lower() != ".sf2":
            # A .sid conversion has no sequence tables to read. Named, because
            # a missing card otherwise reads as "this tune has no pattern".
            print("  SKIP %s: converted side is %s, not an .sf2" % (n, conv.suffix))
            skipped += 1
            continue
        sched = row_schedule(conv)
        if sched is None:
            print("  FAILED %s: %s could not be parsed for sequences" % (n, conv.name))
            continue
        (listen_dir() / ("%s.patterns.json" % n)).write_text(
            json.dumps(sched, indent=1), encoding="utf-8")
        ok += 1
        if verbose:
            print("  %-26s tempo=%-3d rows=%s frames=%d"
                  % (n, sched["tempo"], [len(t) for t in sched["tracks"]],
                     sched["frames"]))
    print("%d pattern(s) -> %s%s"
          % (ok, listen_dir(), ("; %d skipped" % skipped) if skipped else ""))
    print("re-run `abpage.py build` to put them on the pages")
    return 0


def build(chips_file, notes_file, embed_name, output) -> int:
    names = staged_names()
    if not names:
        print("no staged pairs in %s -- run `abpage.py stage ...` first"
              % listen_dir())
        return 2
    rows, notes = chips_rows(chips_file), listening_notes(notes_file)
    blind = blind_rows(chips_file)
    version = _version()

    if embed_name:
        if embed_name not in names:
            print("%s is not staged; have: %s" % (embed_name, ", ".join(names)))
            return 2
        html = page(embed_name, rows.get(embed_name, {}),
                    notes.get(embed_name, []), version,
                    embed=True, index_link=False,
                    blind_row=blind.get(embed_name, {}))
        out = (Path(output) if output
               else listen_dir() / ("%s.embed.html" % embed_name))
        out.write_text(html, encoding="utf-8")
        print("%s  %.2f MB" % (out, len(html) / 1e6))
        return 0

    for n in names:
        html = page(n, rows.get(n, {}), notes.get(n, []), version,
                    embed=False, index_link=True, blind_row=blind.get(n, {}))
        (listen_dir() / ("%s.html" % n)).write_text(html, encoding="utf-8")
    pruned = prune_stale_pages(names)
    (listen_dir() / "index.html").write_text(index(names, rows, version),
                                             encoding="utf-8")
    cmd = write_launcher()
    print("%d page(s) + index -> %s" % (len(names), listen_dir()))
    if pruned:
        print("pruned %d stale page(s): %s"
              % (len(pruned), ", ".join(p.name for p in pruned)))
    missing = [n for n in names if n not in rows]
    if missing:
        # Named rather than silent: a page whose rail says "not in --chips"
        # looks the same as one whose tune had nothing to report.
        print("no --chips row for: %s" % ", ".join(missing))
    print("%s -- double-click to serve and open" % cmd)
    print("file:// hides the overlay -- `abpage.py serve` to draw it")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="abpage",
        description="Gapless A/B listening pages for SIDM2 conversions.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stage", help="render an original/conversion pair")
    s.add_argument("original", type=Path, help=".sid/.sf2/.wav")
    s.add_argument("converted", type=Path, help=".sid/.sf2/.wav")
    s.add_argument("--name", default=None,
                   help="page name (default: the original's stem)")
    s.add_argument("-t", "--seconds", type=int, default=60)
    s.add_argument("--subtune", type=int, default=None)
    s.add_argument("--driver-init", type=lambda x: int(x, 0), default=None)
    s.add_argument("--driver-play", type=lambda x: int(x, 0), default=None)
    s.add_argument("--voices", action="store_true",
                   help="also render the three solo stems per side (forces "
                        "sidplayfp, the only renderer with a voice mute). NOT "
                        "clean isolation on every tune -- the page says so.")
    s.add_argument("--renderer", choices=("auto", "vsid", "sidplayfp"),
                   default="auto")
    s.add_argument("--allow-renderer-change", action="store_true",
                   help="proceed when this run would use a different renderer "
                        "than the one that produced the solo stems already on "
                        "disk, DELETING those stale stems. Without it such a "
                        "run is refused: mixing renderers across a comparison "
                        "is a measurement error, not a cosmetic one.")
    s.add_argument("-v", "--verbose", action="count", default=0)

    b = sub.add_parser("build", help="build a page per staged pair")
    b.add_argument("--chips", type=Path, default=None,
                   help="JSON {tune: {label: value}} quoted in the page's rail")
    b.add_argument("--notes", type=Path, default=None,
                   help="Markdown with '## <tune>' headings and '- ' bullets")
    b.add_argument("--embed", metavar="TUNE", default=None,
                   help="one self-contained page with the audio inlined "
                        "(~14 MB per minute per side -- the practical ceiling)")
    b.add_argument("-o", "--output", default=None, help="--embed only")

    c = sub.add_parser("chips", help="measure the staged pairs into a --chips JSON")
    c.add_argument("-o", "--output", default=None,
                   help="where to write (default: build/listen/chips.json)")
    c.add_argument("--onset", action="store_true",
                   help="also emit onset match and median offset. OPT-IN because "
                        "onset match is ORDINAL ONLY with no absolute gate: a "
                        "99.8%% register-exact build measured 64.7%% against an "
                        "85-91%% original-vs-itself floor. Meaningful against a "
                        "baseline of the same tune, never as pass/fail.")
    c.add_argument("-v", "--verbose", action="count", default=0)

    m = sub.add_parser("instrmap",
                       help="run the instrument map for staged tunes (OPT-IN: "
                            "two emulations per song)")
    m.add_argument("--only", default=None, metavar="TUNE")
    m.add_argument("-t", "--seconds", type=int, default=0,
                   help="trace length (default: whatever the tune was staged at)")
    m.add_argument("-v", "--verbose", action="count", default=0)

    q = sub.add_parser("patterns",
                       help="read each staged tune's .sf2 rows into a patterns JSON")
    q.add_argument("--only", default=None, metavar="TUNE")
    q.add_argument("-v", "--verbose", action="count", default=0)

    v = sub.add_parser("serve", help="serve build/listen over http")
    v.add_argument("--port", type=int, default=8730)
    v.add_argument("--no-build", action="store_true",
                   help="serve what is already staged; skip rebuilding first")
    v.add_argument("--chips", type=Path, default=None)
    v.add_argument("--notes", type=Path, default=None)

    args = ap.parse_args(argv)

    if args.cmd == "stage":
        name = args.name or args.original.stem
        return stage(args.original, args.converted, name, args.seconds,
                     args.subtune, args.driver_init, args.driver_play,
                     args.voices, args.renderer, args.verbose,
                     args.allow_renderer_change)
    if args.cmd == "chips":
        return chips(args.output, args.onset, args.verbose)
    if args.cmd == "instrmap":
        return instrmap(args.only, args.seconds, args.verbose)
    if args.cmd == "patterns":
        return patterns(args.only, args.verbose)
    if args.cmd == "build":
        return build(args.chips, args.notes, args.embed, args.output)
    if args.cmd == "serve":
        if not args.no_build:
            rc = build(args.chips, args.notes, None, None)
            if rc:
                return rc
        elif not list(listen_dir().glob("*.html")):
            print("no pages in %s -- run `abpage.py build` first" % listen_dir())
            return 2
        return serve(args.port)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
