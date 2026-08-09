# Calibrating the listening metrics against a human verdict

**Date**: 2026-08-09 | **Case**: Blackbird / Glyptodont, B13
**Manifest**: `pyscript/calibration_cases.json` | **Tests**: `pyscript/test_audio_listen_calibration.py`

Improvement #3 from `docs/AUDIO_LISTENING_IMPROVEMENT_PLANS.md`. Every threshold in
`sidm2/audio_listen.py` and `sidm2/audio_tightness.py` was chosen by reasoning, never
derived from a listening test. This is the first check of those metrics against evidence
outside themselves.

## The one case on record

`sidm2/audio_tightness.py` exists *because* of this case. A register-exact Blackbird
build of Glyptodont scored ~97.6% and a human listening in the real SID Factory II
editor still said **"something with the perc or drums."** No register category dipped in
a way that flagged it.

Reconstructing it needed git archaeology, because the defect was later fixed:

| Commit | Role |
|---|---|
| `d946701` | "Blackbird Stage B12+B13" -- **the build that was listened to** |
| `ef3263b` | B25, "fixes the real **drums sound off** cause" |
| `12c7da5` | E3e, the implicit-repeat root cause (note-ons 122 -> 157/162) |

Built at `d946701` in a throwaway git worktree, and at HEAD, giving a genuine A/B: same
tune, same builder, two code states, a recorded human verdict on one.

| Build | Register overall | Human verdict |
|---|---:|---|
| B13 (`d946701`) | 96.6% | "something with the perc or drums" |
| HEAD | 99.8% | 162/162 note-ons, no complaint |

(The reconstructed B13 build measures 96.6%, not the 97.6% the docs quote -- close, but
the doc's figure presumably came from a different measurement window. Noted rather than
papered over.)

## The measurement

Onset match against the original `Glyptodont.sid`, 60 s, sidplayfp, `--delay=0`, plus the
control that makes the numbers mean anything: **the original against a re-render of
ITSELF** at perturbed power-on delays.

| Comparison | Onset match |
|---|---:|
| Original vs itself, phase-perturbed -- **the floor** | **85.4 - 91.3%** |
| Original vs HEAD build (99.8% register, 162/162 note-ons) | **64.7%** |
| Original vs B13 build (the one that sounded wrong) | **56.9%** |

## What this says about the tooling

**It has ordinal sensitivity.** The known-bad build scores below the known-good one,
56.9 < 64.7, in the right direction without being told which was which. That is a real
result: the metric is not blind here.

**It has no usable absolute calibration, and this is the important half.** A build with
99.8% register accuracy and every note-on present scores 64.7% -- more than 20 points
*below* what the original scores against itself. So:

- Any threshold that flags the B13 build also flags the known-good build. The metric
  cannot answer "is this build acceptable"; it flags everything.
- The 20-point deficit is **systematic**, not a defect. It is the cost of comparing an
  original SID render against a native-driver SF2 render at all -- different playback
  engines produce different transients, and spectral-flux onset detection sees them as
  different events even where the registers agree.
- The bad/good gap (7.8 points) is only slightly larger than the floor's own spread
  (5.9 points), so a single A/B run cannot separate two builds with confidence.

**Did the tooling "catch" B13?** Honestly: not in the way the guide's framing implies. It
scores B13 below the good build, but it would have condemned the good build too. What it
provides is a *relative* signal for A/B regression work -- did this change move the
number, and which way -- not a verdict on whether a build sounds right.

## Consequences

1. **Do not use onset match as an absolute quality gate for native-driver builds.** Quote
   it against a baseline build or against the repeatability floor, never alone. This is
   the same rule `audio_tightness_tool.py` already applies per-voice via `--repeat-floor`;
   this case shows the whole-mix number needs it just as much.
2. **The floor must be measured per tune.** 85-91% here is not a constant; it depends on
   note density and material.
3. **Improvements #1 (mel-scale) and #2 (A-weighting) have a target now.** If either
   narrows the 20-point systematic deficit between a near-perfect build and the original,
   that is measurable progress against a real case rather than a plausible-sounding
   change. This manifest is how that gets checked.
4. **One case is not a calibration set.** The manifest is append-only by design and needs
   no new test code per case; the next time a human's verdict disagrees with a metric,
   it belongs in there.

## Regenerating

Audio is not committed. `pyscript/calibration_cases.json` records the commit and build
command for each side; `pyscript/test_audio_listen_calibration.py` validates the manifest
on every run and re-checks the ordinal claim from real audio when
`SIDM2_CALIBRATION_AUDIO=1` is set and the WAVs are present under `out/calibration/`.

The manifest's prose findings are themselves under test: `orders_correctly` and
`absolute_gate_usable` are re-derived from the recorded numbers, so a future re-measure
that changes the numbers without revisiting the conclusions fails loudly.
