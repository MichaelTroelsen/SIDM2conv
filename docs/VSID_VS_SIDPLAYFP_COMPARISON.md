# VSID vs sidplayfp Renderer Comparison

**Date**: 2026-08-09 | **Tool**: `pyscript/audio_tightness_tool.py` (WAV2WAV mode) + `sidm2/audio_listen.py`

Both renderers, run on the SAME original `.sid`, then diffed against each other. This
isolates renderer-vs-renderer differences from any driver/conversion question. 6 songs,
3 SID engines (Hubbard, Tel/MoN, native Laxity), run TWICE at different render lengths:
an initial pass at 20 s each (Stinsen truncated early on the VSID side, see Finding 4),
and a follow-up pass at **60 s** each (Finding 2 revisited below) -- the longer window
was requested specifically to check whether Finding 2's offset held up with more
material, and it does not.

## Method

- `_render_vsid()` / `_render_sidplayfp()` (`pyscript/audio_tightness_tool.py`) rendered
  each `.sid` once per tool, `-limitcycles`/`--seconds 20` on both.
- Onset alignment (`sidm2.audio_tightness.analyze_tightness`) needs matching sample
  rates; VSID outputs 48 kHz, sidplayfp outputs 44.1 kHz (see Finding 1), so the VSID
  side was linearly resampled to 44.1 kHz before alignment. Resampling does not
  introduce a time shift by itself.
- Whole-file features (`sidm2.audio_listen.extract_features`) and the spectrograms were
  computed on the UNRESAMPLED originals at their native rate.
- Full artifacts (WAVs, per-song text reports, spectrogram PNGs, `results.json`) are in
  the scratch dir this run used and were not committed; re-run the script below to
  regenerate.

## Finding 1: different sample rates (structural, not a fidelity question)

VSID renders at **48000 Hz**; sidplayfp renders at **44100 Hz**, on every song. Any tool
that diffs a VSID WAV against a sidplayfp WAV directly (not through this project's
onset/feature tooling, which resamples) will see a sample-rate mismatch, not a musical
one. `audio_tightness_tool.py`'s own onset path already refuses a raw cross-renderer
WAV2WAV comparison for exactly this reason (`ValueError: Sample rate mismatch`) --
consistent with the tool's existing rule that both sides of a comparison must come from
ONE renderer (`choose_renderer()`'s docstring).

## Finding 2: a consistent -10 ms onset offset, every song

| Song | Match rate | Offset (sidplayfp − VSID) | Jitter p50 / p95 |
|---|---:|---:|---:|
| Hubbard_Commando | 90.1% (146/162) | **-10.0 ms** | 0.0 / 47.5 ms |
| Hubbard_I_Ball | 92.7% (202/218) | **-10.0 ms** | 0.0 / 20.0 ms |
| Hubbard_Sanxion | 92.1% (198/215) | **-10.0 ms** | 0.0 / 20.0 ms |
| Tel_Cybernoid_II | 85.7% (132/154) | **-10.0 ms** | 0.0 / 40.0 ms |
| Tel_Hawkeye | 93.8% (181/193) | **-10.0 ms** | 0.0 / 10.0 ms |
| Stinsen | 85.9% (85/99)¹ | **-10.0 ms** | 0.0 / 30.0 ms |

¹ Stinsen's VSID render is truncated (see Finding 4) -- its numbers are the least
trustworthy of the six.

**Every one of the six songs reports EXACTLY -10.0 ms**, no scatter at all. That is not
six independent measurements agreeing by chance; it is a single systematic constant,
almost certainly startup/init-latency, not per-note jitter -- 10 ms is exactly half a
PAL frame (20 ms/frame @ 50 Hz). This project has prior, independent evidence pointing
the same direction: commit `21917ba` ("sidplayfp rendered with a RANDOM power-on delay;
add guarded per-voice sweep") already found sidplayfp's power-on delay is not fixed.
This run's constant -10 ms is consistent with that delay landing at the SAME point
across these six particular runs, not with the two engines being frame-locked in
general -- **do not read this -10 ms as a universal constant** without re-running to
check it varies with sidplayfp's delay parameter.

Post-offset jitter is otherwise tight: p50 is 0.0 ms on every song (i.e. most onsets land
within the onset detector's own ~10 ms hop resolution once the constant is removed).
p95 ranges 10-47.5 ms -- a handful of onsets per song diverge further, consistent with
emulation-core differences on complex frames (filter/digi) rather than a timing defect.

### Finding 2, revisited at 60 s: the -10 ms offset does NOT replicate

Re-ran all 6 songs at **60 s** instead of 20 s (same method, same files, `analyze_tightness`
on VSID-resampled-to-44.1kHz vs sidplayfp, `power_on_delay=0` on the sidplayfp side both
times). Result:

| Song | Onsets (orig/driver) | Match rate | Offset | Jitter p50 / p95 |
|---|---:|---:|---:|---:|
| Hubbard_Commando | 500 / 482 | 90.2% (451) | **0.0 ms** | 10.0 / 40.0 ms |
| Hubbard_I_Ball | 620 / 661 | 93.5% (580) | **0.0 ms** | 0.0 / 20.0 ms |
| Hubbard_Sanxion | 547 / 568 | 94.5% (517) | **0.0 ms** | 10.0 / 30.0 ms |
| Tel_Cybernoid_II | 490 / 495 | 89.0% (436) | **0.0 ms** | 0.0 / 30.0 ms |
| Tel_Hawkeye | 541 / 546 | 91.9% (497) | **0.0 ms** | 10.0 / 30.0 ms |
| Stinsen | 543 / 542 | 90.8% (493) | **0.0 ms** | 10.0 / 30.0 ms |

Every song now reads **exactly 0.0 ms**, not -10.0 ms -- the same "no scatter at all"
pattern as the 20 s run, just at a different constant. Match rates hold in the same
85-95% band as the 20 s pass (more onsets per song -- 490-620 vs 99-218 at 20 s -- give a
more stable estimate, and it lands in the same place). Stinsen also renders its full
60.00 s on the VSID side this time (see Finding 4 below for the 20 s truncation this
contradicts).

**Read this as a correction, not a second independent finding.** A "-10.0 ms, zero
scatter" result and a "0.0 ms, zero scatter" result from the same six songs, same method,
different render length, cannot both be a real fixed renderer-latency constant --
`median_offset_ms` is computed from onset times that are themselves quantized to the
onset detector's 10 ms hop (`hop_ms=10` default), so both "-10.0" and "0.0" are the two
adjacent bins either side of whatever the true sub-hop-resolution offset actually is. The
originally reported explanation ("almost certainly startup/init latency... 10 ms is
exactly half a PAL frame") is **not supported once the 60 s data is in** -- the true
constant is too small for this detector's 10 ms hop to resolve, and which of the two
neighbouring bins it rounds into depends on something sensitive to render length (most
likely the linear resampling step from 48 kHz to 44.1 kHz shifting phase by a length-
dependent sub-sample amount, since that resampling is the one part of the method whose
output changes shape with duration). **Net effect on the practical conclusion**: VSID and
sidplayfp start in sync to within this detector's resolution (~10 ms, likely much
tighter) -- there is no evidence of a real, several-frame startup mismatch between the
two renderers. Anyone citing this doc for a hard offset number should use "sub-10ms,
unresolved" rather than either single-pass figure.

## Finding 3: level and brightness are close but not identical (20 s pass)

| Song | RMS Δ (sidplayfp − VSID) | Centroid Δ | Rolloff Δ | Flatness Δ |
|---|---:|---:|---:|---:|
| Hubbard_Commando | +0.22 dB | +18.8 Hz | +30.2 Hz | +0.0040 |
| Hubbard_I_Ball | **+2.76 dB** | +76.6 Hz | +34.7 Hz | +0.0043 |
| Hubbard_Sanxion | +0.76 dB | +14.1 Hz | +13.7 Hz | +0.0021 |
| Tel_Cybernoid_II | -0.05 dB | -42.0 Hz | -102.7 Hz | -0.0103 |
| Tel_Hawkeye | -0.08 dB | -4.5 Hz | -17.0 Hz | -0.0007 |
| Stinsen¹ | **+3.47 dB** | -73.9 Hz | -230.3 Hz | -0.0296 |

Commando, Sanxion, and Hawkeye are close on every axis (well under 1 dB, centroid within
~1-2%). **I_Ball is the outlier of the reliable five**: sidplayfp is 2.76 dB louder and
its silence fraction is 0% vs VSID's 3.21% -- VSID's render has brief quiet stretches
sidplayfp's does not. I_Ball is already flagged elsewhere in this project
(`sidm2/audio_tightness.py`'s digi-bleed measurements) as having the worst voice-mute
bleed in the 12-tune corpus (`.587`), so a digi/filter-path difference between the two
emulation cores landing here is plausible, not confirmed -- this run did not isolate
which SID register or voice drives it.

### Finding 3, revisited at 60 s

| Song | RMS Δ (sidplayfp − VSID) | Centroid Δ | Rolloff Δ | Flatness Δ | VSID silence % | sidplayfp silence % |
|---|---:|---:|---:|---:|---:|---:|
| Hubbard_Commando | +0.12 dB | +17.4 Hz | +28.2 Hz | +0.0043 | 0.00% | 0.00% |
| Hubbard_I_Ball | **+1.44 dB** | +44.1 Hz | +21.9 Hz | +0.0024 | 1.27% | 0.00% |
| Hubbard_Sanxion | +0.68 dB | +2.4 Hz | -1.3 Hz | +0.0005 | 0.00% | 0.00% |
| Tel_Cybernoid_II | -0.11 dB | -32.1 Hz | -75.1 Hz | -0.0080 | 0.00% | 0.00% |
| Tel_Hawkeye | -0.19 dB | -18.3 Hz | -53.2 Hz | -0.0037 | 0.00% | 0.00% |
| Stinsen | +1.27 dB | -21.6 Hz | -87.0 Hz | -0.0098 | 0.05% | 0.00% |

I_Ball is still the largest gap of the reliable five (+1.44 dB at 60 s vs +2.76 dB at 20
s -- same direction, smaller magnitude with more material, and its VSID-side silence
fraction is again nonzero where sidplayfp's is 0%, corroborating rather than contradicting
the 20 s finding). Stinsen now renders its FULL 60 s on both sides (no truncation, unlike
the 20 s pass), and reads +1.27 dB -- a real, if smaller, level gap now that the
truncation confound is removed. Commando/Sanxion/Cybernoid_II/Hawkeye stay under ~0.7 dB
at both durations. Net: the level/brightness picture from the 20 s pass holds up at 60 s;
only Finding 2's offset needed correcting.

## Finding 4: Stinsen's VSID render came back short

Requested 20 s; the VSID WAV is **12.67 s** (sidplayfp's is the full 20.0 s). This
surfaced as part of a 6-song batch run under `_render_vsid()`'s own 110 s
(`max(60, seconds*4+30)`) subprocess timeout -- the function falls through to "return
whatever file exists" on a `TimeoutExpired`, so a slow/stalled VSID run produces a
truncated WAV rather than an error. This may be a resource-contention artifact of
rendering 6 songs back-to-back in one batch rather than a Stinsen-specific defect. **This
is now supported, not just hypothesized**: the 60 s follow-up run (Finding 2/3 revisited,
above) re-rendered Stinsen back-to-back with the same 5 other songs in the same kind of
batch, and it came back full-length (60.00 s) both sides that time. A resource-contention
theory predicts exactly this kind of non-reproduction (timing-sensitive, not
deterministic); a genuine Stinsen-specific VSID defect would be expected to reproduce at
both durations. Treat the 20 s Stinsen numbers in this section and Finding 2 as
unreliable and prefer the 60 s tables above for Stinsen.

## Finding 5: parameter surfaces -- what this project passes, what's common, what's different

Checked against each tool's own `--help` output (`tools\sidplayfp\sidplayfp.exe -h`;
`C:\winvice\bin\vsid.exe -help`, which dumps VICE's full general-emulator option list --
filtered to the SID/sound-relevant subset below) and this project's two wrapper code
paths: `sidm2/vsid_wrapper.py` + `pyscript/audio_tightness_tool.py::_render_vsid()` for
VSID, `sidm2/sidplayfp_wrapper.py` for sidplayfp.

### What this project actually passes today

| Concern | VSID invocation | sidplayfp invocation |
|---|---|---|
| Duration | `-limitcycles <exact cycle count>` (`_render_vsid`, this tool's own path) or a wall-clock subprocess timeout (`VSIDIntegration.export_to_wav`, used elsewhere) | `-t<seconds>` -- native, exact, no timeout race |
| Sample rate | **not passed** -- falls back to VICE's own default | `-f44100` -- **always explicit** |
| Bit depth | not passed -- VICE default | `-p16` (or `-p32`) -- explicit |
| Stereo/mono | not passed -- VICE default | `-s` / `-m` -- explicit, driven by a `stereo` param |
| Subtune/track | `-tune <n>` | `-o<n>` |
| Output file | `-sounddev wav -soundarg <path>` | `-w<path>` (native WAV writer) |
| Voice mute | **not available** -- VSID's option list has no per-voice mute at all | `-u<num>` per voice (this tool's `--voice` flag depends on this) |
| Power-on delay | **not exposed** -- no equivalent option exists in VSID's CLI | `--delay=<cycles>`, this project pins it to `0` (`power_on_delay` param, see `sidplayfp_wrapper.py`'s docstring -- sidplayfp's own default is *random*) |

**This asymmetry is the direct, mechanical cause of Finding 1.** Nothing about VICE
forces 48 kHz -- `-soundrate <value>` exists and is documented in `vsid -help`. This
project's `_render_vsid()` and `VSIDIntegration.export_to_wav()` simply never call it,
so VSID renders at whatever its own internal default happens to be (measured 48000 Hz
today), while the sidplayfp wrapper always pins `-f44100` explicitly. The sample-rate
mismatch is a **wrapper-code choice**, not a renderer capability gap -- VSID could be
pinned to 44100 Hz with one added arg.

### Capability each tool has that the other lacks entirely

| VSID-only (no sidplayfp equivalent) | sidplayfp-only (no VSID equivalent) |
|---|---|
| Multi-SID addressing (`-sidextra`, `-sid2address`..`-sid8address`) -- irrelevant here, every file in this project is single-SID | Per-voice mute `-u<num>` (this tool's entire `--voice`/`--voice all` isolation feature depends on this) |
| `-sidenginemodel`/`-sidmodel` (6581/8580/8580+digiboost as one setting) | Sample-channel mute `-g<num>` (separate from voice mute) |
| `--digiboost`, `-residfilterbias`, `-resid8580*` (separate 8580 gain/passband/bias controls) | `--fcurve`/`--frange` (continuous 0.0-1.0 filter curve/range tuning in ReSIDfp) |
| Full general-VICE surface (window geometry, monitor, breakpoints, etc.) -- noise for audio export, not a SID-emulation difference | `-nf` (disable filter emulation entirely), `-cw<w|a|s>` (combined-waveform strength) |
| | Controllable `--delay=<cycles>` power-on delay (VSID has no equivalent knob -- see Finding 2's "not exposed" row above; any VSID-side startup variance is currently un-tunable from its CLI) |

### Capability both tools have, expressed differently

| Concern | VSID | sidplayfp |
|---|---|---|
| SID emulation core | reSID only (`-sidengine 1`) | reSID **or** reSIDfp (`--resid` / `--residfp`, default reSIDfp) |
| Filter emulation on/off | `-sidfilters` / `+sidfilters` | `-nf` |
| PAL/NTSC clock | `-pal` / `-ntsc` / `-ntscold` / `-paln` | `-vp` / `-vn` (per `-v[p|n][f]`) |
| SID chip model | `-sidmodel <0|1|2>` | `-m<o|n>[f]` |

## Assessment

- **Finding 1's sample-rate gap is fixable in one line, not a fundamental engine
  difference.** If this project ever wants a direct (non-resampled) WAV2WAV diff between
  the two renderers, add `-soundrate 44100` to `_render_vsid()`'s arg list (and the
  equivalent to `VSIDIntegration.export_to_wav()` if that path matters too). Until then,
  any cross-renderer comparison tool must keep resampling or refusing the pair, exactly
  as `audio_tightness_tool.py`'s WAV2WAV path already does.
- **Finding 2's -10 ms offset has no cheap fix on the VSID side**, because VSID exposes
  no power-on-delay control at all -- there is nothing to pin to match sidplayfp's
  `--delay=0`. That asymmetry alone is reason enough to keep `choose_renderer()`'s
  existing rule (one renderer for BOTH sides of any comparison): even if the sample rate
  were unified, VSID's startup timing is not independently controllable the way
  sidplayfp's is, so a VSID-vs-sidplayfp diff can never fully separate "renderer timing
  difference" from "emulation difference" the way a same-renderer diff can.
  [[choose_renderer's docstring already states this design rule -- this run and this
  parameter audit are both direct evidence for it, not a new conclusion.]]
- **The two tools are not capability-equivalent**, which is *why* this project uses both
  rather than picking one permanently: sidplayfp is the only one with per-voice
  isolation (`-u<num>`), which `--voice`/`--voice all` depend on entirely; VSID's default
  preference for whole-mix renders rests on it being the long-standing default this
  project's existing fidelity corpus was validated against (per `choose_renderer()`'s
  docstring), not on any audio-quality argument surfaced by this comparison.
- Neither tool's default invocation in this project pins the SID engine/model
  explicitly (VSID: `-sidenginemodel`/`-sidmodel` unset; sidplayfp: `--residfp` is only
  the tool's own default, not passed explicitly) -- both rely on tool-internal defaults
  for that axis too, a second unpinned parameter beyond sample rate. Not measured
  separately in this run; flagging it as the same class of gap as Finding 1, not a new
  finding.

## Interpretation

- VSID and sidplayfp agree closely on WHAT plays (85-95% onset match across both the
  20 s and 60 s passes, tight post-alignment jitter) and are close on level/timbre for
  4 of 6 songs at both durations.
- They agree closely on WHEN it starts: the "10 ms offset" from the 20 s pass **did not
  replicate** at 60 s (see "Finding 2, revisited at 60 s") -- both renderers are in sync
  to within this detector's ~10 ms resolution, not several PAL frames apart as first
  read.
- Where they DO genuinely diverge -- I_Ball's level gap, corroborated in the same
  direction at both 20 s and 60 s -- is exactly the class of difference
  `choose_renderer()` already exists to prevent contaminating a fidelity comparison:
  "mixing two SID emulations would fold two different SID emulations into the onset
  deltas." This run is direct evidence for that existing design rule, not just a
  restatement of it.
- The sample-rate difference (Finding 1) means any NEW tooling comparing these two
  renderers' raw output must resample or reject the pair, same as the existing tool
  does.
- **Methodological note for future re-runs**: this doc's own Finding 2 correction is the
  reason to always sanity-check a "suspiciously clean, zero-scatter" result against a
  second render length before treating it as a real renderer constant, particularly for
  any number derived from a fixed-hop-resolution detector.

## Assessment: is sidplayfp usable in the wider pipeline?

The question this section answers: today sidplayfp is used in exactly one place in this
codebase (`pyscript/audio_tightness_tool.py`, as the fallback renderer and the forced
renderer when `--voice` is given). Everywhere else that exports audio uses VSID only,
hardcoded:

| Call site | Wrapper used | What it produces |
|---|---|---|
| `pyscript/sf2_playback.py` (SF2 editor playback preview) | `VSIDIntegration.export_to_wav()` directly -- no sidplayfp fallback | one full-mix WAV |
| `scripts/sid_to_sf2.py`'s `--export-audio` flag | `AudioExportIntegration.export_to_wav()` (VSID-preferred, sidplayfp fallback already wired) | one full-mix WAV |
| `sidm2/conversion_pipeline.py`'s `config.export_audio` | `AudioExportIntegration.export_to_wav()` (same) | one full-mix WAV |

**None of these three produce anything but a single mixed-down WAV.** Per-voice
isolation exists nowhere outside `audio_tightness_tool.py --voice`, and that tool is a
diagnostic script a person runs by hand on two specific files -- it is not reachable from
the normal conversion pipeline (`sid-to-sf2.bat`, the cockpit GUI, the SF2 editor's
playback preview).

**Yes, sidplayfp can be used more broadly, and per-voice muting is the concrete win.**
Two of the three call sites (`sid_to_sf2.py`, `conversion_pipeline.py`) already route
through `AudioExportIntegration`, which already falls back to
`SidplayfpIntegration.export_to_wav(mute_voices=...)` -- the mute-voices parameter is
fully implemented and tested (it's what `--voice` in `audio_tightness_tool.py` calls).
The gap is purely that nothing above `AudioExportIntegration` ever asks for it: neither
`--export-audio`'s CLI flag nor `config.export_audio` exposes a way to request per-voice
stems, so the capability sits unused one layer down. Concretely, this would need:

1. A new opt-in flag (e.g. `sid-to-sf2.bat input.sid output.sf2 --export-audio --export-audio-voices`,
   or a `config.export_audio_voices` bool) that, alongside the existing full-mix export,
   calls `SidplayfpIntegration.export_to_wav()` three more times with
   `mute_voices="23"/"13"/"12"` (reusing `audio_tightness_tool.py`'s existing `MUTE_MAP`
   constant rather than re-deriving the digit strings) and writes
   `<name>_voice1.wav`/`_voice2.wav`/`_voice3.wav` next to the mix.
2. This forces sidplayfp specifically for that step (VSID cannot do it at all -- Finding
   5 confirmed VSID's CLI has no per-voice mute option), independent of whichever
   renderer produced the full mix -- there is no conflict, since the mix and the stems
   are three separate deliverables, not a single comparison, so `choose_renderer()`'s
   "one renderer for both sides" rule (which governs *diffing* two renders) does not
   apply here.
3. **Carry over two things this comparison already surfaced**: pin `power_on_delay=0`
   on the stem renders (sidplayfp's own default is random -- see the parameter table
   above) so re-generating a stem later is reproducible, and be aware the stems will be
   44.1 kHz sidplayfp output sitting next to a 48 kHz VSID full mix unless the full mix
   is also switched to sidplayfp or VSID is pinned to `-soundrate 44100` (Finding 1) --
   not a blocker for casual listening, but worth fixing before any tool diffs the stems
   against the mix.
4. Digi-bleed caution carries over too: `sidm2/audio_tightness.py`'s own measurements
   (module docstring) found muting all three voices is NOT silence on every tune (I_Ball
   worst case, 58.7% shared residual) -- a per-voice stem export should say so in its
   output (or reuse `analyze_voice_bleed`) rather than presenting an isolated stem as a
   clean single-voice recording unconditionally.

**Recommendation**: keep VSID as the default full-mix renderer (matches the existing
validated fidelity corpus, per `choose_renderer()`'s docstring -- nothing in this
comparison found a reason to change that default). Add sidplayfp-based per-voice stem
export as a new, separate, opt-in output alongside it, not a replacement -- the two
renderers serve different jobs (whole-song reference vs per-channel isolation) and this
project already has the isolation logic built and tested, just not wired above
`audio_tightness_tool.py`.

## Reproduction

```
py -3 pyscript/audio_tightness_tool.py --renderer vsid      original.sid /dev/null  # (illustrative; see script below for the actual batch)
```

The 20 s comparison used a small ad-hoc script (render both renderers per song via
`_render_vsid`/`_render_sidplayfp`, then `sidm2.audio_tightness.analyze_tightness` +
`sidm2.audio_listen.extract_features`/`render_comparison_spectrogram` directly) rather
than `audio_tightness_tool.py`'s CLI, because the CLI's WAV2WAV path refuses a
sample-rate mismatch outright (Finding 1) instead of resampling. That script was not
committed. The 60 s follow-up used the same method (`analyze_tightness` +
`extract_features`, VSID resampled 48kHz->44.1kHz via linear interpolation) in
`vsid_vs_sidplayfp_60s.py`, also not committed (scratch dir). Re-create either from the
functions named above and the 6 files under
`SID/Hubbard_Rob/{Commando,I_Ball,Sanxion}.sid`, `SID/Tel_Jeroen/{Cybernoid_II,Hawkeye}.sid`,
`SID/Stinsens_Last_Night_of_89.sid` to regenerate.
