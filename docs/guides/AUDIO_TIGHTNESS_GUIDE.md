# Audio Tightness Tool - User Guide

**Version**: 1.0.0
**Tool**: `audio-tightness.bat` / `pyscript/audio_tightness_tool.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Sweeping all three voices](#sweeping-all-three-voices)
4. [Understanding the Report / HTML Output](#understanding-the-report--html-output)
5. [Key Metrics Explained](#key-metrics-explained)
6. [Use Cases](#use-cases)
7. [Interpreting Results](#interpreting-results)
8. [Troubleshooting](#troubleshooting)
9. [Tips & Tricks](#tips--tricks)

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

1. **Renders** the original and the driver output to WAV (via VSID or
   sidplayfp — see "Renderer selection" below)
2. **Detects onsets** in both renders (numpy spectral-flux + adaptive
   peak-picking, no external audio library)
3. **Aligns** onsets between the two renders (greedy nearest-neighbor
   within a tolerance window)
4. **Measures** onset-timing delta, attack-rise-time delta, and spectral
   distance per matched onset, splitting the timing delta into a
   **systematic offset** and per-note **jitter** (see below)
5. **Reports** a text summary + worst-offenders table, and an HTML report
   with an **alignment timeline**, a waveform view, and a sortable onset table

### Offset vs jitter — read this before trusting a "loose %" number

A raw onset delta mixes two completely different defects:

| | meaning | fix |
|---|---|---|
| **Systematic offset** (median delta) | the whole render is shifted — different playback start point, driver startup pipeline, etc. | rhythmically harmless; find the constant cause |
| **Jitter** (delta minus offset) | *this* note is early/late relative to the rest | the real "not tight" signal |

A render that is uniformly 50 ms late is rhythmically **perfect**, yet a
raw-delta report would flag ~100% of its onsets "loose". The tool therefore
reports both, ranks worst-offenders by **jitter**, and prints a `HOW TO READ
THIS` block. Offset is also shown in **PAL frames** (20 ms each), because the
engine's own timing quantum is what makes it actionable — "+2.50 frames"
points at a startup-pipeline difference in a way "+50 ms" does not.

### The alignment tolerance must stay below the note spacing

`--onset-tolerance-ms` defaults to **auto**: half the original's own median
inter-onset interval (clamped to 20–150 ms). This is not a stylistic default,
it is a correctness requirement. A greedy matcher with a window *wider than
the gap between consecutive notes* can pair an onset with its **neighbour** —
and because that mispairing preserves time order, the crossed-pair check
cannot detect it.

This produced a real false finding. Glyptodont (median IOI 90 ms) measured
against its Blackbird native build reported a **"+50 ms (+2.5 PAL frame)
systematic offset" and 60.7% loose onsets** under the old fixed 150 ms
default. Sweeping the tolerance down collapsed the offset monotonically to
**exactly 0.0 ms at ≤70 ms**. The true reading is offset **+0.00 frames**,
median jitter **0.0 ms**, **7.4%** loose — the timing was never the problem.

The report always prints the measured IOI alongside the tolerance in use, and
warns when the tolerance approaches (`> 0.5 × IOI`) or exceeds it. **If you
override `--onset-tolerance-ms`, keep it under half the IOI.**

Two further automatic warnings guard against over-reading the numbers:

- **Crossed pairs** — a matched pair whose driver onset runs *backwards*
  relative to its predecessor. Music does not reorder itself, so a crossing
  is a greedy-alignment **mispairing**, not a timing error. Any nonzero count
  means jitter is an upper bound only.
- **Tolerance-ceiling pinning** — onsets whose delta sits exactly at
  `--onset-tolerance-ms` are suspect pairings; re-run with a smaller
  tolerance to check.

### The alignment timeline

The HTML report's first view: original onsets on a top lane, driver onsets on
a bottom lane, one connector line per matched pair, coloured green→red by
`|jitter|`. Missing onsets are red ticks on the top lane, extra onsets purple
on the bottom.

- **Crossed connectors are drawn thick and red** — that is mispairing, visible
  at a glance, and the single most important thing this view shows.
- The **"Remove systematic offset"** checkbox (on by default) shifts the
  driver lane back by the median delta. Uncheck it to see the raw alignment.
- **Scroll to zoom, drag to pan, double-click to reset** — necessary, since a
  20-second render can carry ~200 onsets.
- Hover any tick for exact `orig_t` / `driver_t` / delta / jitter.

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

### Renderer selection

**One renderer serves both sides of a comparison.** Mixing a VSID render
with a sidplayfp render would fold two different SID emulations into the onset
deltas — exactly the measurement error this tool exists to avoid. The
renderer is resolved once, up front, before anything is rendered.

`--renderer auto` (the default) picks:

| Situation | Renderer | Why |
|---|---|---|
| `--voice` given | sidplayfp | Only renderer with a voice-mute flag (`-u<num>`) |
| otherwise, VSID available | VSID | The long-standing default |
| otherwise | sidplayfp | Fallback |

Override with `--renderer vsid` or `--renderer sidplayfp`. Combining
`--renderer vsid` with `--voice` is rejected rather than silently ignored —
an unmuted render presented as voice-isolated would be worse than an error.

**sidplayfp replaced SID2WAV.EXE (2026-08-07, commit `32a0e0c`).** The old
`tools/SID2WAV.EXE` was a 1997 build that hung outright on some newer tunes —
it parsed the PSID header, printed the metadata, then never emitted a single
sample (lft's `SID/LFT/Glyptodont.sid` was the confirmed case). The bundled
replacement is `tools/sidplayfp/sidplayfp.exe` (sidplayfp 2.16.2 /
libsidplayfp 2.16.1 / libresidfp 1.0.1).

**Per-voice isolation requires sidplayfp** — VSID has no mute equivalent:

```
-u<num>    mute voice <num> (e.g. -u1 -u2)
-g<num>    mute samples <num>
-o<num>    start track
--delay=<num>  simulate c64 power on delay (default: random)
```

**`--delay` is pinned to 0 by this repo, and that is not cosmetic.**
sidplayfp's own default is a *random* power-on delay, which shifts the entire
render by a random offset of up to ~8 ms — a random error of the same order as
the quantity this tool measures. Measured 2026-08-08 on Commando over 20 s,
three renders with identical arguments:

| `--delay` | onset counts | rms(difference)/rms between runs |
|---|---|---|
| sidplayfp default (random) | 152 / 159 / 156 | ~1.2 (the difference is as big as the signal) |
| `--delay=0` (this repo) | 156 / 156 / 156 | ~0.0003 |

Before the pin, **a file compared against itself scored 148/157 matched onsets
with 18 spurious extras**; after it, the same self-comparison comes back exact
(Commando 156/156 and Crazy_Comets 122/122, 0 missing, 0 extra, registers
100/100/100 on every voice). `sidm2/sidplayfp_wrapper.py` sets
`power_on_delay=0` by default; pass `power_on_delay=None` to restore
sidplayfp's random (more hardware-like, unreproducible) behaviour.

The residual `~0.0003` is libsidplayfp's own RAM/noise seeding and is **not
quite zero**: absolute onset counts can still move by one in a hundred between
runs (Hawkeye 196/195/195 over three renders, Crazy_Comets voice 3 at 112 then
113), and a self-comparison occasionally lands at 99% instead of 100% on one
voice. Treat differences of a single onset as noise; the ~8 ms *shift* the pin
removes is what was actually corrupting the measurement.

**VSID render precision:** the VSID path uses `-limitcycles` (an exact PAL
cycle count) rather than `sidm2/vsid_wrapper.py`'s unbounded-run-plus-
subprocess-timeout approach, so the render length is determined by the
requested duration rather than by wall-clock speed. This matches the
technique `bin/listen_compare.py` already uses. VSID exits non-zero on normal
termination (a documented quirk — see `CLAUDE.md`), so success is judged by
the output file, never the exit code.

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

`--voice N` mutes the *other two* SID voices (via sidplayfp's `-u<num>`) on
**both** renders, so voice N can be compared cleanly. This forces the
sidplayfp renderer, the only one with a mute flag.

**Muting two voices does not always isolate the third.** Use `--voice all`
(next section) to have that checked for you — it is not checked on the
single-voice path.

### Common Options

```bash
--seconds 30                  # Render duration (default: 30)
--subtune 2                   # Subtune/song number (sidplayfp -o<num>, VSID -tune)
--voice {1,2,3,all}            # Isolate one SID voice, or sweep all three
--allow-digi-bleed             # Print per-voice rows the guard refused (unsound)
--reg-match-pct 95             # Cross-tab: freq % at/above which registers "match"
--audio-match-rate 0.9         # Cross-tab: onset fraction at/above which audio "matches"
--renderer {auto,vsid,sidplayfp} # Renderer for BOTH sides (default: auto)
--driver-init 0xHHHH           # Override the driver SF2's init address
--driver-play 0xHHHH           # Override the driver SF2's play address
--onset-tolerance-ms 45        # Max |delta| to count as matched (default: auto = half the IOI)
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

## Sweeping all three voices

```bash
audio-tightness.bat original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003 \
    --voice all --seconds 12 --no-html
```

`--voice all` renders each side five times (mix, all-three-muted, and one
render per isolated voice) and prints three blocks. It answers a question the
mix comparison cannot: *which voice is the problem, and is it the note data or
the synthesis?*

`--voice all` needs `.sid`/`.sf2` inputs on both sides — a pre-rendered `.wav`
cannot be re-rendered with different voices muted. It prints no HTML (the HTML
exporter is per-comparison and there are four comparisons here).

### 1. The isolation guard

The extra all-muted render is the point. **On many tunes `-u1 -u2 -u3` is not
silence**, and whatever survives appears identically in all three "isolated"
renders — they then agree with each other for reasons that have nothing to do
with the driver, while looking reassuringly similar.

```
  original  residual/mix 0.584   shared: v1 67.8%  v2 53.6%  v3 59.4%   [refuse]
            inter-voice r(1-2)=+0.61  r(1-3)=+0.56  r(2-3)=+0.47
```

`shared` is the **energy fraction of each isolated render that is actually the
residual** — `(residual_rms / isolated_rms)²`. Measured across 12 tunes at
20 s, it runs from 0.2% (Commando, Crazy_Comets, Athena) through 4-5% (lft),
13-24% (Hawkeye, Cybernoid_II, Stinsen) to 54-68% (Sanxion, I_Ball, Arkanoid).

| verdict | condition | effect |
|---|---|---|
| `clean` | worst slice < 5% shared | per-voice rows printed normally |
| `warn` | 5-50% | printed, flagged as partly correlated across voices |
| `refuse` | ≥ 50% — the residual carries *more* energy than the voice | per-voice rows withheld, **exit code 3** |
| `no-signal` | nothing on either side | withheld — silence is not a clean isolation |

The 50% line is the one cut point that means something on its own terms
(at that point the slice is no longer mostly the voice you asked for) rather
than being read off a histogram. It matters that it is not read off the data:
**the fractions move with the measurement window** — Cybernoid_II's worst slice
reads 23.8% at 20 s and 34.5% at 12 s.

`--allow-digi-bleed` prints the rows anyway. They are unsound; the flag exists
to inspect them, not to trust them.

**The mechanism is mixed, and the obvious guess was wrong.** `$D418`
master-volume digi was the standing hypothesis and is **falsified** for the
worst offenders: Sanxion and I_Ball hold `$D418`'s volume nibble at a constant
15 for all 1000 frames of a 20 s siddump, exactly like clean Commando. What the
residual actually is varies per tune — Galway's Arkanoid is a *sample* channel
libsidplayfp mutes under its own separate flag (`-g1` drops it .114 → .004);
Hubbard's Sanxion is filter-path and emulation-dependent (`-nf` drops it
.032 → .004, `--resid` to .010, while `-g1` changes nothing). That is why the
guard thresholds are fractions rather than a test for one mechanism.

### 2. The per-voice tightness table

```
  side      onsets  matched  missing  extra    offset  jitter50   loose
  mix           91       69       22     25    +0.0ms    10.0ms   15.9%
  voice 1       97       82       15     34    +0.0ms    20.0ms   18.3%
  voice 2       70       51       19      8    +0.0ms     0.0ms    5.9%
  voice 3       99       79       20     14    +0.0ms     0.0ms    7.6%
```

Same statistics as the single-voice report, one row per slice. This is what
turns "the audio diverges" into "voice 1 is the problem".

### 3. The registers × audio cross-tab

```
Calibrating repeatability floor (9 extra renders per voice, delays [0, 2189, 4379,
6568, 8757, 10947, 13136, 15325, 17515] cycles -- the 0 is a plain replicate)...

  voice    freq     wf    pul   audio  repeat   floor  diagnosis
  1       100.0  100.0  100.0     85%    100%     73%  INCONCLUSIVE: registers
          match; audio 85% is inside the repeatability floor (73%, set by a
          phase-shifted re-render) -- this file scores no better against
          ITSELF, so the audio cannot separate a synthesis defect from metric
          noise and SID phase
  2       100.0  100.0  100.0     73%    100%     41%  INCONCLUSIVE: ...
  3       100.0  100.0    n/a     80%     95%     77%  INCONCLUSIVE: ...
```

The register half comes from `sidm2.fidelity_common.per_voice_register_agreement`
(siddump on both `.sid`s, a global engine-delay search, then `score_pct` +
`exercised` per dimension). `freq` is compared as a **semitone** — a vibrato
landing on the same note is not a note error, and the audio side cannot hear
the difference either. `n/a` means *not exercised*: neither side moved that
register, so it is never reported as 0 or 100.

`repeat` and `floor` are the **repeatability calibration**
(`--repeat-floor N`, default 9, `sidm2.audio_tightness.measure_repeatability_
floor` via `pyscript/audio_tightness_tool.py`): N extra renders of the
ORIGINAL per voice — one plain replicate at the reference render's own delay,
the rest at perturbed power-on delays — compared against that reference
through the same onset metric the driver row uses. `repeat` is the replicate
alone (pure metric noise); `floor` is the worst of all N (metric noise +
free-running SID phase), narrowed by the noise margin the replicate itself
revealed. **An audio score at or above `floor` is not evidence of anything.**
Voices whose registers match land in **INCONCLUSIVE** there rather than
SYNTHESIS — see PATTERNS.md **F5b** for why a bare `f(x, x)` check does not
rule this out.

Neither register+audio half, nor the floor, can make this partition alone:

| registers | audio vs floor | diagnosis |
|---|---|---|
| match | below floor | **SYNTHESIS** — the driver's envelope/pulse/filter timing |
| match | at/above floor | **INCONCLUSIVE** — the audio gap is inside this file's own repeatability noise; not evidence either way |
| match | floor not measured (`--repeat-floor 0`) | **SYNTHESIS**, but flagged uncalibrated — do not trust it |
| diverge | (either) | **SEQUENCER** — note data / order list |
| audio matches, registers don't | — | **METRIC** — suspect a measurement artifact, e.g. a phase-offset but musically correct pulse sweep scored frame-by-frame |

The thresholds are `--reg-match-pct` (default 95) and `--audio-match-rate`
(default 0.9). `--repeat-floor 0` disables the calibration and reverts to the
old unconditional SYNTHESIS-on-divergence behavior — the tool then says so in
the diagnosis text; don't quote a SYNTHESIS verdict produced that way.

The example above is real, and its story changed after this feature was
added. `Cybernoid_II` against its native MoN build was originally read as
register-exact on all three voices and still only 71-85% onset-matched —
"SYNTHESIS on every voice." That finding was **falsified 2026-08-08**: the
registers really are byte-identical except for one real, since-fixed defect (a
one-frame `$D418` filter-mode lag at startup), and the 71-85% audio band sits
entirely inside what this same file scores against re-renders of **itself** —
metric noise on a voice-isolated render (a full mix's onset detector doesn't
move at all under the same perturbation) plus free-running SID phase, neither
of which is a driver defect. All three voices now read INCONCLUSIVE. See
`docs/players/MON.md` and PATTERNS.md F5b for the full story — it is the
worked example for why the floor exists.

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

`--onset-tolerance-ms` is now derived from the material itself (see "The
alignment tolerance must stay below the note spacing"). The remaining
defaults — `--loose-threshold-ms 40` and the detector tuning
(`--hop-ms`/`--window-ms`/`--bands`/`--freq-lo`/`--freq-hi`) — are still
**provisional guesses**, not calibrated against a corpus; see
`docs/ROADMAP.md`'s E4.

---

## Troubleshooting

**`[ERROR] ...init/play addresses could not be auto-detected...`**
The `.sf2` has no Block 2 header and doesn't match the Laxity heuristics, so
`scripts/sf2_to_sid.py` would otherwise silently guess Driver 11's
`$1000/$1006` — wrong for `bin/`-only native drivers (e.g. Blackbird is
`$1000/$1003`). Pass `--driver-init`/`--driver-play` with the driver's real
addresses (check the driver's own build script, e.g.
`bin/build_blackbird_driver_full.py`'s `DRV_INIT`/`DRV_PLAY`).

**`No renderer available: neither vsid.exe nor tools/sidplayfp/sidplayfp.exe was found`**
Install VICE with `python pyscript/install_vice.py`, or restore
`tools/sidplayfp/`. Note that VSID alone cannot do voice isolation.

**`--renderer vsid cannot be combined with --voice`**
Working as intended: VSID has no voice-mute flag, and silently rendering an
unmuted mix while reporting it as voice-isolated would be worse than an
error. Use `--renderer sidplayfp`, or drop `--voice`.

**`[REFUSED] Muting two voices does not isolate the third on this tune` (exit 3)**
The isolation guard fired — see "Sweeping all three voices". The mix row is
still printed and still valid. `--allow-digi-bleed` shows the per-voice rows
anyway; they are unsound.

**`--voice all needs a .sid or .sf2 ..., not a pre-rendered .wav`**
Voice isolation re-renders with different voices muted, which a WAV cannot do.
Pass the source `.sid`/`.sf2`.

**Two runs of the same comparison give different numbers**
Should not happen since `--delay` was pinned (see "Renderer selection"). If it
does, check that nothing passes `power_on_delay=None` to the sidplayfp wrapper.

**`Sample rate mismatch`**
The two renders came out at different sample rates — shouldn't normally
happen (both sides always share one renderer), but can occur if one side was
pre-rendered externally as a `.wav`. Re-render both, or convert the
mismatched `.wav` to match.

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
