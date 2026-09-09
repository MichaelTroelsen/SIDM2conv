# h2g's `fidelity.py` — applicability to SIDM2

**Source**: `C:\Users\mit\claude\h2g` (separate repo — SID → GoatTracker converter,
mostly Hubbard-family players). Its fidelity tool: `python/fidelity.py` (5,784
lines), docs at `h2g/docs/FIDELITY.md`, `SIDM2-FIDELITY-TESTER.md`,
`SNG2SID-FIDELITY.md`, `FIDELITY-TOOL-IMPROVEMENTS.md`.

**Relationship already exists**: h2g's own docs (`SIDM2-FIDELITY-TESTER.md`)
record that h2g already *wraps* two SIDM2 tools unmodified —
`scripts/validate_sid_accuracy.py` (`--register`) and
`pyscript/audio_tightness_tool.py` (`--audio`) — via `SIDM2_ROOT` (defaults to
`C:\Users\mit\claude\c64server\SIDM2`, still valid on this machine). This
analysis is the reverse direction: what `fidelity.py` has that SIDM2's own
fidelity stack (`sidm2/fidelity_common.py`, `pyscript/instrument_map.py`,
`sidm2/audio_listen.py`) does not, and whether it's worth pulling in.

## 1. What `fidelity.py` measures that SIDM2 doesn't

SIDM2's own tooling is register-frame-exact (`validate_sid_accuracy.py`) or
audio-onset-timing (`audio_tightness.bat`). h2g's tool adds a layer in between
that SIDM2 has no equivalent for: **note-sequence identity, tempo-independent**.

| Dimension | What it answers | SIDM2 equivalent? |
|---|---|---|
| `melody` / `seq` | difflib ratio over the attack-note sequence (siddump's *bare* notes only — true gate-rising-edge attacks) | None. SIDM2's frame comparisons require tempo match; this doesn't. |
| `retrig` | our attacks / original's attacks | None — closest is `instrument_map.py`'s onset keying, but that requires ADSR-key reliability first |
| `pitch` (Jaccard) | right notes, ignoring order/count | None |
| `slides` / `bend` | frames where pitch moved *without* a retrigger, and how far (ratio) — separates a stepped/glide difference a note-count can't see | None. SIDM2's `shape_agreement` in `fidelity_common.py` does the analogous phase-invariant trick for a **swept register** (pulse/cutoff), not for pitch/vibrato |
| `vib` | vibrato rate, ours/original's (step function on short notes) | None |
| `drift` | Theil-Sen fit of lead/lag in frames-per-1000 over matched onsets — separates "wrong tempo" from "right tempo, offset start" | None — SIDM2's `audio_tightness.bat` aligns onsets but doesn't report an accumulating drift rate |
| `nrun` / `hold` / `tail` / `onset` | per-*instrument* noise-run length, note duration, release shape, opening waveform | Partially covered by `instrument_map.py`, but that's gated on ADSR-key reliability per player family and SIDM2 doesn't have a `hold`/`tail` breakdown |
| `pspan` | how wide a band the duty cycle covers, ratio (companion to `pul`'s move-count) | Close to `shape_agreement`'s travel+count pairing, not identical |

The single most transferable idea, independent of any specific metric: **the
`DIMENSIONS` registry + `--baseline` mechanism.** Each dimension declares which
SID registers it's computed from; a report states, in plain language, which
registers *no* dimension reads (`"Registers no dimension above reads"` — the
change-invisible-here list). `--baseline old.json` hashes the converter's
output per row and turns a flat diff into "no dimension this report measures
can see this change" vs. "this change reaches nothing." h2g's own doc says
this caught two real cases where a shipped fix landed in a register nothing
then measured and would otherwise have read as a silent no-op.

This is exactly the failure mode `sidm2/fidelity_common.py`'s docstring
already names as recurring in *this* project — "five separate copies of the
same weighted-accuracy scheme existed, each independently broken," a metric
that scored two identical captures at 50%, `$D418` unscored by anything until
2026-08-07 across several players. A `DIMENSIONS`-style registry with an
explicit "unreachable registers" printout, sitting on top of
`fidelity_common.py`, would make that class of gap visible by construction
instead of by a bug report every time.

## 2. Why it isn't a drop-in for SIDM2's actual comparison

h2g's `fidelity.py` is built for **cross-tempo** comparison: a native player's
row and Goattracker's row are not the same length, so *every* frame differs by
construction, and the whole point of `melody`/`seq`/`drift` is tolerating that.
SIDM2's native-driver ports (Laxity, Blackbird, DMC, SDI, etc.) are the
opposite case — the whole point of a native driver is **matching the original
player's own row timing**, and SIDM2's `fidelity_common.py` guards
(`score_pct`, `exercised`, `underpowered`) are built assuming frame alignment
holds. Importing h2g's tempo-tolerant metrics wholesale would be solving a
problem SIDM2's native-driver work doesn't have.

Where SIDM2 *does* have h2g's problem: **Stage A conversions** (SF2-editor
based, not native-driver) — Driver 11, NP20, Galway's SF2II staging — convert
into a fixed-tempo editor format the same way h2g converts into GoatTracker's
row grid. Those are the candidates for a tempo-tolerant note-sequence score;
the native-driver corpus (the majority of the accuracy table in `CLAUDE.md`)
is not.

## 3. Concrete recommendation

Don't port `fidelity.py` itself (it's h2g-specific: GoatTracker pattern/order
list internals, `gt2reloc`, `goatwriter.py` wavetable semantics — none of
which exist in SIDM2). Two things are worth taking:

1. **The `DIMENSIONS`-registry + unreachable-registers pattern** — SIDM2
   already gestures at this (`fidelity_common.py`'s "dimension registry so a
   report can generate — not hand-maintain — the list of registers nothing it
   measured reads" is described as already shipped for the shared harness).
   Confirm it's applied consistently across the per-player scorers, since
   h2g's version is more mature (explicit `--baseline old.json` diffing) and
   the exact bug class it guards against ($D418 unscored for months) has hit
   this project multiple times per `CLAUDE.md`'s Known Limitations table.
2. **Tempo-tolerant note-sequence scoring, scoped to Stage A / SF2-editor
   conversions only** — a `melody`/`seq`/`retrig`-style siddump-attack
   comparator (stdlib-only, no dependency on SIDM2's own tooling) would give
   those drivers a cheap first-pass signal ("right notes, right order") before
   spending an `audio-tightness.bat` or `validate-accuracy.bat` run. Not
   needed for native-driver work, where frame alignment is the goal, not an
   obstacle.

Everything else in h2g's tool — `--vice` (312-sample/frame emulator trace for
sub-frame register writes), `--equal-calls` (re-samples at the original's
call rate instead of siddump's fixed 1/frame) — targets h2g's specific
row-multiplier packing (`gt2reloc -S<n>`) problem and has no SIDM2 analogue to
port to; note it only as a technique (sub-frame VICE tracing) if a future
SIDM2 defect turns out to be invisible at 1 sample/frame the way `--vice`
found for h2g.

## 4. `abpage.py` — the A/B listening page (h2g has this, SIDM2 does not)

Separate tool from `fidelity.py`: `h2g/python/abpage.py` (~2,700 lines, stdlib
only — no numpy, matches h2g's "no third-party runtime deps" rule) builds one
self-contained HTML page per tune. **SIDM2 has nothing like it** — grepped for
any blind-test/gapless-swap rig across `sidm2/audio_listen.py` and
`fidelity_common.py`; the closest thing SIDM2 ships is `audio_listen.py`'s
static 3-panel spectrogram PNG, which is read once, not interacted with.

**What the page does**: both renders (`<name>.original.wav` /
`<name>.h2g.wav`) load into two `<audio>` elements and play in lock-step at
all times; a source button just flips which one has `volume=1` — so the
switch is sample-accurate and position-matched, unlike opening two files in a
media player. On top of that transport:

- **Blind mode** — labels become "X"/"Y", sides randomize per guess, and a
  tally scores whether the listener correctly identifies the original.
- **Sync offset control** — corrects for `startup_lag` (h2g's packed player
  reaching its first note 3-8 frames after the original, per `FIDELITY.md`),
  either auto-detected from the first onset in both WAVs or dragged by hand;
  every other visualization on the page reads this offset before drawing.
- **Amplitude-envelope overlay** — both renders' peak envelopes on one canvas
  plus a `|difference|` strip, with per-trace show/hide toggles; explicitly
  captioned that it shows dropped notes/wrong note-length/tempo drift but
  *not* pitch, timbre, or filter.
- **Per-voice envelope strips** — same overlay, split three ways, so "which
  voice diverges" is a glance instead of three rounds of re-soloing.
- **Precomputed dual-spectrogram** (log-frequency, shared peak so a quieter
  render draws visibly dimmer rather than being renormalized) — the FFT runs
  once at Python build time so the page cost is constant regardless of tune
  length.
- **Quotes generated reports rather than re-deriving numbers**: the per-tune
  chips (`melody`, `seq`, `retrig`, `wave`, `gate`, `hold`, `onset`, `bend`,
  `vib`, `drift`) are pulled from `FIDELITY.md`, prose from `LISTENING.md`
  — so the page cannot disagree with the report it's summarizing, and a tune
  the report didn't measure shows an honest gap instead of an empty rail.
- Two build modes: local (page references sibling WAVs, ~25 KB, needs
  `--serve` for `fetch()`-based sync/spectrogram since `file://` blocks it)
  and `--embed` (both WAVs inlined as data URIs, for publishing standalone —
  costs ~14 MB/minute of mono audio, the practical ceiling h2g's own docstring
  names).

**Applicability to SIDM2**: high, and more directly portable than
`fidelity.py` itself — this tool doesn't touch GoatTracker internals at all,
it only reads two WAVs and (optionally) a Markdown fidelity table. SIDM2
already produces both halves of its input on every player: paired
original/converted WAVs via `sidm2.vsid_wrapper`/`sidm2.sidplayfp_wrapper`
(the `--export-audio` / `--audio-export-voices` flags in `sid-to-sf2.bat`),
and a fidelity report to quote chips from (`FIDELITY.md`'s equivalent would
be `audio-tightness.bat`'s onset-timing output or `fidelity_common.py`'s
`result_row`/`ab_pair` tables). The gap it would close: every fidelity number
in SIDM2's Known Limitations table is a claim about *whether a build sounds
right*, verified today only by an assistant reading a spectrogram PNG or a
human running the WAV through a media player by hand — there is no rig for a
human to blind-test a claim like "Blackbird B1-B25 mean 99.96%" against their
own ears with position-matched, gapless switching.

**Recommendation**: worth porting as a genuinely new SIDM2 tool (e.g.
`abpage.py` under `pyscript/`), not as part of the h2g-analysis integration
in §3 above — it's an independent capability (human-in-the-loop listening
verification), not a fidelity-metric gap. Scope: strip h2g-specific pieces
(the `FIDELITY.md`/`SURVEY.md`/`presets.json`/`instrmap.json` table readers,
which are h2g's own report formats) and re-point the report-quoting layer at
SIDM2's own outputs — `audio_tightness.bat`'s per-voice numbers and
`instrument-map.bat`'s per-instrument table are the natural sources. The
transport/sync/envelope/spectrogram machinery (the bulk of the file, lines
~200-1150+ of stdlib JS+Python) needs no SIDM2-specific change to reuse.

Port plan (settled 2026-08-23): `docs/plans/ABPAGE_PORT_PLAN.md`, queued as
`port-h2g-abpage-listening-rig` in `.claude/tasks/whattask.json`.

## 5. `instrmap.py` — convergent with SIDM2's own tool; nothing to port

`h2g/python/instrmap.py` (901 lines) is the same idea as SIDM2's
`sidm2/instrument_map.py`, arrived at independently: key note onsets on
`$D405/$D406` (a verbatim per-instrument ADSR copy), decide the instrument
once per note on the frame *after* the attack (the attack frame can still
hold hard-restart transition bytes), letter-label unmatched ADSR values
rather than dropping them. h2g adds pulse-width bucketing (`PULSE_BUCKET =
0x100`) and a fixed 8-frame per-onset profile for drum/noise-sweep
classification; SIDM2's version is the more rigorous overall — it gates on
`key_reliability()` before trusting the ADSR key at all (h2g assumes it,
justified for its one player family; SIDM2 measured that assumption failing
on 6+ of 27 calibration files), and locates the instrument table by search
where h2g can call its own converter's `_detect_tables`. Verdict: do not
port; do not re-investigate. If h2g's 8-frame onset profile idea is ever
wanted, it is a ~30-line addition to `instrument_map.py`, not a port.

## 6. The flagship staging estimate, re-measured (2026-09-03)

The staging decision quoted **~5 h and ~8 GB** for 100 songs at 60 s with
voices, extrapolated linearly from ONE measured Angular run at ~7.5 s per 20 s
render. Both halves are now measured. The size half survives; the time half
does not.

### Time — the estimate is ~6.5x pessimistic, with one caveat that matters

Rendering through the same path `ab-listen stage` uses
(`AudioExportIntegration.export_to_wav`, `force_sidplayfp=True`), into a
scratch directory, on this machine:

| render length | n | mean | min | max |
|---|---|---|---|---|
| 20 s | 3 | **1.15 s** | 1.04 | 1.22 |
| 30 s | 3 | **1.58 s** | 1.35 | 1.73 |

(Angular, 5_Title_Tunes, Bahbar — three player families.) That is **1.15 s per
20 s render, not 7.5 s**. Fitting the two points gives ≈ 0.29 s fixed +
0.043 s per rendered second, so a 60 s render ≈ **2.9 s**. A song staged
`--voices` needs 8 renders (original and sidm2, each × full/v1/v2/v3), so
≈ **23 s/song**, and 100 songs ≈ **38 minutes** rather than ~5 hours.

**THE CAVEAT, and do not drop it:** I measured the BARE RENDER. If the
original 7.5 s was the whole `stage` step — render plus page build, pattern
decode, spectrogram — then 1.15 s is not the comparable number and the missing
~6.3 s is non-render work this measurement does not cover. The honest reading
is that the RENDER is not the bottleneck the estimate assumed it was, and that
whatever the remaining cost is, it is not rendering.

### Size — ~8 GB is right for the decided configuration, and nothing on disk matches it

`build/listen` holds **11 songs**, and they are NOT the configuration the
estimate covers:

| | length | channels | voices | bytes/song |
|---|---|---|---|---|
| `Angular` (the file the estimate came from) | 20 s | stereo | **yes**, 8 wavs | **28.2 MB** |
| the other 10, staged since | 30 s | **mono** | **no**, 2 wavs | **5.3 MB** |

Scaling Angular — the right configuration — to 60 s gives 84.7 MB/song and
**8.5 GB per 100 songs**, so the ~8 GB figure is CONFIRMED at n=1 with the
correct shape. But scaling what is actually on disk (mono, no voices) gives
10.6 MB/song and **1.06 GB per 100** — 8x less.

The trap that follows: `build/listen` totals only 60 MB for 11 songs, and
reading that against "8 GB for 100" invites the conclusion that the estimate
was wildly pessimistic. It is not. The corpus on disk is a different, cheaper
configuration than the one the decision authorised, on two axes at once
(mono vs stereo, no voices vs voices).
