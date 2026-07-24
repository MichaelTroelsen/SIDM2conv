# Audio Tightness Tool - User Guide

**Version**: 1.0.0
**Tool**: `audio-tightness.bat` / `pyscript/audio_tightness_tool.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Understanding the Report / HTML Output](#understanding-the-report--html-output)
4. [Key Metrics Explained](#key-metrics-explained)
5. [Use Cases](#use-cases)
6. [Interpreting Results](#interpreting-results)
7. [Troubleshooting](#troubleshooting)
8. [Tips & Tricks](#tips--tricks)

---

## Overview

SIDM2's fidelity measurement is almost entirely register-write-exact trace
comparison (`trace-compare.bat`, `accuracy-heatmap.bat`) — % match on SID
registers, frame-by-frame. This catches most bugs, but it can hide a real
gap: during the Blackbird native-driver work, B13 (see
`docs/players/BLACKBIRD.md`, lines 46/2997-2998) shipped a verified,
register-exact-match improvement for Glyptodont (97.6% overall — freq 99.5%,
waveform 95.5%, pulse 99.7%, adsr 96.2%, filter 95.2%), but the user,
listening to the actual rendered SF2 in the real SID Factory II editor,
still reported "something with the perc or drums." The register percentage
never dipped in a way that flagged this — the problem hid inside categories
(waveform/filter, ~95%) that looked "pretty good" in aggregate.

The **Audio Tightness Tool** measures the audio domain directly: do
note/drum onsets land at the same time, with the same attack shape, as the
original? It renders both sides to WAV, detects onsets via spectral flux,
aligns them, and reports timing/attack-shape divergence — as text (for
Claude to read directly) and HTML (for a human).

### What It Does

1. **Renders** the original and the driver output to WAV (via SID2WAV —
   see "Why SID2WAV, not VSID" below)
2. **Detects onsets** in both renders (numpy spectral-flux + adaptive
   peak-picking, no external audio library)
3. **Aligns** onsets between the two renders (greedy nearest-neighbor
   within a tolerance window)
4. **Measures** onset-timing delta, attack-rise-time delta, and spectral
   distance per matched onset
5. **Reports** a text summary + worst-offenders table, and an HTML
   waveform view with colored onset markers

### When to Use It

- A register-exact (or near-exact) conversion still "sounds off" to a human
  listener, and you need a number to reason about instead of a vague
  impression
- Investigating drum/percussion tightness specifically (the category most
  sensitive to onset timing and attack shape)
- Comparing one SID voice in isolation (`--voice 1/2/3`) to narrow down
  which channel a "not tight" complaint is actually about
- As a complement to, **not a replacement for**, `trace-compare.bat` /
  `accuracy-heatmap.bat` — those catch register-level bugs; this catches
  what register-level metrics can miss

### Why SID2WAV, not VSID

`sidm2/audio_export_wrapper.py` normally prefers VSID (the VICE emulator)
over SID2WAV for accuracy. This tool always forces SID2WAV
(`force_sid2wav=True`), because per-voice isolation (`--voice`) and subtune
selection (`--subtune`) need SID2WAV-only flags — confirmed directly against
`tools/SID2WAV.EXE`'s own `-h` output:

```
-m<num>    mute voices out of 1,2,3,4 (default: none)
-o<num>    set song number (default: preset)
```

VICE's `vsid` wrapper (`sidm2/vsid_wrapper.py`) has no equivalent. Both
sides of a comparison always render through the same tool, so the
comparison stays apples-to-apples even when voice isolation isn't used.

---

## Quick Start

### Basic Comparison

```bash
audio-tightness.bat original.sid converted.sid
```

**Output**: text report on stdout + `audio_tightness_<timestamp>.html`.

### Comparing Against a Native-Driver SF2

Native `bin/`-only drivers (Blackbird, Galway, Romuzak, etc.) each hardcode
their own init/play addresses, which `scripts/sf2_to_sid.py` **cannot**
auto-detect (see "Native Drivers" below) — pass them explicitly:

```bash
audio-tightness.bat original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
```

### Isolating One Voice

```bash
audio-tightness.bat original.sid converted.sid --voice 1
```

`--voice N` mutes the *other two* SID voices (via SID2WAV's `-m<num>`) on
**both** renders, so voice N can be compared cleanly.

### Common Options

```bash
--seconds 30                  # Render duration (default: 30)
--subtune 2                   # Subtune/song number (SID2WAV -o<num>)
--voice {1,2,3}                # Isolate one SID voice
--driver-init 0xHHHH           # Override the driver SF2's init address
--driver-play 0xHHHH           # Override the driver SF2's play address
--onset-tolerance-ms 150       # Max |delta| to still count as matched (default: 150)
--loose-threshold-ms 40        # |delta| above which a matched onset is "loose" (default: 40)
--output report.html           # Output HTML path
--text-output report.txt       # Also write the text report to a file
--no-html                      # Skip HTML generation (quick check)
--keep-temp                    # Keep the temporary rendered .sid/.wav files
-v, -vv                        # Verbose logging
```

Both `orig` and `driver` accept `.sid`, `.sf2`, or `.wav` directly — `.wav`
is used as-is, `.sid` is rendered, `.sf2` is converted to `.sid` first (via
`scripts/sf2_to_sid.py::convert_sf2_to_sid`) and then rendered.

---

## Understanding the Report / HTML Output

### Text Report

Fixed sections, in order:
- **Header** — file paths, render params, detector/alignment params
- **SUMMARY** — onset counts (orig/driver/matched/missing/extra), onset-delta
  mean/median/max, loose-onset count/%, attack-rise-time delta stats,
  spectral-distance stats
- **WORST OFFENDERS** — top 20 matched onsets by `|delta_ms|`
- **MISSING / EXTRA ONSETS** — onsets present only in the original, or only
  in the driver render

### HTML Report

- **Overview** — the same summary as the text report, as a table
- **Waveform** — a downsampled RMS envelope of both renders on a shared
  time axis, with colored onset markers (green = matched, yellow = matched
  but loose, red = missing, purple = extra) and hover tooltips
- **Onset Table** — every matched/missing/extra onset, sortable by column,
  with a search box

---

## Key Metrics Explained

| Metric | Meaning |
|---|---|
| **Matched** | Orig onsets found in the driver render within `--onset-tolerance-ms` |
| **Missing** | Orig onsets with no driver onset in the tolerance window |
| **Extra** | Driver onsets with no orig onset in the tolerance window |
| **Onset delta (ms)** | `driver_t - orig_t` for a matched pair; positive = driver plays late |
| **Loose** | A matched onset whose `|delta_ms|` exceeds `--loose-threshold-ms` |
| **Attack rise delta (ms)** | Difference in 10%→90%-of-peak RMS-envelope rise time between the two onsets — a sharper/softer attack than the original |
| **Spectral distance** | Log-mel distance (24 bands, 200-5000Hz) between the two onsets' first 80ms — a proxy for timbre/waveform difference at the attack |

---

## Use Cases

- **"Register match is 97%+ but it still sounds off"** — run this tool
  against the full mix first; if loose-onset % or attack-rise delta is
  elevated, that's a concrete, actionable number instead of "sounds close."
- **Narrowing down which voice** — run with `--voice 1`, `--voice 2`,
  `--voice 3` and compare loose-onset % per voice. Treat the result as a
  hypothesis, not a given — a "drums sound off" complaint doesn't
  necessarily map cleanly onto a single SID voice.
- **Regression-checking a fix** — run before/after a driver change on the
  same file/voice and compare loose-onset % and mean `|delta_ms|`.

---

## Interpreting Results

- **0% loose, low mean |delta_ms|, low spectral distance**: the register
  match is likely also an audio-tight match — the "not tight" complaint (if
  any) is probably elsewhere (sustain/release shape, filter sweep, etc. —
  outside this tool's scope).
- **High loose %, but missing/extra both ~0%**: onsets exist in the right
  place but are individually mistimed — a systematic per-note delay or
  jitter, not a missing/extra-note bug.
- **Nonzero missing or extra**: either a genuine dropped/added note (check
  against the register trace with `trace-compare.bat` to confirm) or the
  onset detector's threshold missed a quiet onset — try tuning
  `--onset-tolerance-ms` / detector params (see below) before concluding a
  note is really missing.
- **Elevated attack-rise delta with low onset-delta**: onsets land on time,
  but the attack itself is shaped differently (e.g. a filter-cutoff sweep
  or ADSR envelope difference) — this is exactly the class of gap register
  percentages can hide inside a "pretty good" aggregate score.

The onset-tolerance/loose-threshold defaults (150ms / 40ms) and the
detector tuning (`--hop-ms`/`--window-ms`/`--bands`/`--freq-lo`/`--freq-hi`)
are **provisional** — revisit them once real acceptance runs (see
`docs/players/BLACKBIRD.md`'s dated entries) give real data points.

---

## Troubleshooting

**`[ERROR] ...init/play addresses could not be auto-detected...`**
The `.sf2` has no Block 2 header and doesn't match the Laxity heuristics, so
`scripts/sf2_to_sid.py` would otherwise silently guess Driver 11's
`$1000/$1006` — wrong for `bin/`-only native drivers (e.g. Blackbird is
`$1000/$1003`). Pass `--driver-init`/`--driver-play` with the driver's real
addresses (check the driver's own build script, e.g.
`bin/build_blackbird_driver_full.py`'s `DRV_INIT`/`DRV_PLAY`).

**`Failed to render ... to WAV: no rendering tool available`**
`tools/SID2WAV.EXE` isn't present. Install it or run
`python pyscript/install_vice.py` (note: VSID alone won't help here — voice
isolation and subtune selection require SID2WAV specifically).

**`Sample rate mismatch`**
The two renders came out at different sample rates — shouldn't normally
happen (both go through the same SID2WAV render path), but can occur if one
side was pre-rendered externally as a `.wav`. Re-render both, or convert
the mismatched `.wav` to match.

**Detected onset count looks wrong (too many/too few)**
Tune `--onset-tolerance-ms`, or the underlying detector params
(`--hop-ms`/`--window-ms`/`--bands`/`--freq-lo`/`--freq-hi`) — these are
provisional defaults, not tuned against a large corpus yet.

---

## Tips & Tricks

- Use `--no-html --text-output -` (or just omit `--text-output` and read
  stdout) for a fast Claude-in-the-loop check without generating a browser
  report every time.
- `--keep-temp` is useful when iterating on detector params against the
  same pair — reuse the kept `.wav` files directly as `orig`/`driver`
  arguments instead of re-rendering.
- Cross-link: `docs/guides/TRACE_COMPARISON_GUIDE.md` /
  `docs/guides/ACCURACY_HEATMAP_GUIDE.md` for the register-level complement
  to this tool; `docs/guides/WAVEFORM_ANALYSIS_GUIDE.md` for the older,
  human-visual waveform tool (not onset-aware).
