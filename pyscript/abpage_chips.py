#!/usr/bin/env python3
"""Chips for an A/B listening page, computed from the STAGED WAV PAIR ALONE.

    python pyscript/abpage.py chips -o build/listen/chips.json
    python pyscript/abpage.py build --chips build/listen/chips.json

No renderer, no emulator, no siddump. The two WAVs already sit in
`build/listen`; every number here is a pure function of those bytes, which is
what makes the rail affordable on a ~100-song corpus and what lets it be
recomputed after a rebuild without re-staging anything.

WHAT THIS IS NOT
----------------
It is not a score, and no chip here may be read as pass/fail. That is not
conservatism, it is the calibration result: `docs/AUDIO_LISTENING_CALIBRATION.md`
records a build that was 99.8% register-exact scoring **64.7%** onset match
against an original-vs-itself floor of **85-91%**. Onset match has ordinal
sensitivity and NO absolute gate, so any threshold that flags a bad build
condemns a good one too. The floor is per-tune and measuring it REQUIRES
re-rendering (`measure_repeatability_floor` renders nine phase-perturbed
copies), which this module is forbidden to do -- so the onset chip is opt-in
and ships labelled as ordinal-only with no floor attached.

WHICH FEATURE IS INFORMATIVE IS DEFECT-DEPENDENT, which is why several are
emitted rather than one composite. From the calibration corpus: A-weighted
level is the strongest discriminator (1.5-1.6x) on the two timing/percussive
defects and scores 0.011 -- noise -- on a vibrato-width pitch defect, where
chroma instead fires at 0.072 and the others correctly stay null. A single
blended number would have averaged the one informative feature away. Every
chip therefore carries a `blind` note saying what it cannot see.

THE SCORER IS NOT NEW. Everything routes through `sidm2.audio_listen` and
`sidm2.audio_tightness`; nothing here reimplements a comparison.
`sidm2/fidelity_common.py`'s docstring records FIVE independently-broken copies
of one weighted-accuracy scheme in this repo, one of which scored two identical
captures at 50%. A sixth is not wanted. Those modules are read-only from here:
`fidelity_common` alone has 51 non-test dependents, including every
`bin/build_*_native_song.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from sidm2.audio_listen import (AudioFeatures, chroma_shift_description,
                                dominant_pitch_classes, extract_features)
from sidm2.audio_tightness import load_wav_mono

# A side whose frames are this nearly all below the silence floor carries no
# evidence, and a delta against it is not agreement.
SILENT_FRAC = 0.99


class ChipRefusal(RuntimeError):
    """The pair cannot be compared at all (rate mismatch, unreadable WAV)."""


def _fmt(v: float, unit: str, places: int = 1) -> str:
    # rstrip: a unitless chip ("noisiness") would otherwise carry a trailing
    # space into the JSON and onto the page.
    return (("%+." + str(places) + "f %s") % (v, unit)).rstrip()


def _both_silent(a: AudioFeatures, b: AudioFeatures) -> bool:
    """Both sides carry no audible signal.

    This is the guard the repo keeps relearning. A DELTA between two silent
    renders is 0.0, and 0.0 renders as perfect agreement -- the same shape as
    the vacuous-100 bug `fidelity_common.exercised()` exists to catch, where a
    tune that never filters scored a confident 100% because siddump
    force-displays every register on its first row. A chip must say "both
    silent", never "0.0 dB".
    """
    return a.silence_frac >= SILENT_FRAC and b.silence_frac >= SILENT_FRAC


def chips_for_pair(orig_wav: Path, ours_wav: Path, *,
                   with_onset: bool = False) -> tuple[dict, dict]:
    """(chips, blind) for one staged pair. Never renders anything.

    `chips` is {label: value-string} for the page rail; `blind` is
    {label: what this chip cannot see}, carried alongside so the page can say
    it rather than leaving a reader to assume a number means more than it does.
    """
    x_a, sr_a = load_wav_mono(orig_wav)
    x_b, sr_b = load_wav_mono(ours_wav)
    if sr_a != sr_b:
        raise ChipRefusal(
            "sample-rate mismatch: %s is %d Hz, %s is %d Hz -- these were not "
            "staged by one renderer, and every number below would be wrong"
            % (orig_wav.name, sr_a, ours_wav.name, sr_b))

    fa = extract_features(x_a, sr_a)
    fb = extract_features(x_b, sr_b)

    # A 'linear' and a 'mel' AudioFeatures are NOT comparable -- the same audio
    # yields different centroid/rolloff/flatness under each, so a delta between
    # them looks like a real difference and is not one. audio_listen's own
    # format_feature_report() refuses such a pair; refuse it here too rather
    # than quietly producing the number it declines to print.
    if fa.band_scale != fb.band_scale:
        raise ChipRefusal(
            "band-scale mismatch: %r vs %r -- centroid/rolloff/flatness are "
            "not comparable across band geometries" % (fa.band_scale, fb.band_scale))

    chips: dict[str, str] = {}
    blind: dict[str, str] = {}

    if _both_silent(fa, fb):
        chips["signal"] = "both silent"
        blind["signal"] = ("neither render produced audible signal, so every "
                           "other comparison would be a delta between two "
                           "silences and would read as perfect agreement")
        return chips, blind

    # One side silent and the other not is the loudest thing a rail can say.
    if fa.silence_frac >= SILENT_FRAC or fb.silence_frac >= SILENT_FRAC:
        which = "original" if fa.silence_frac >= SILENT_FRAC else "ours"
        chips["signal"] = "%s is silent" % which
        blind["signal"] = ("one side has no audible signal; the deltas below "
                           "are against a silence and are not fidelity")

    chips["level"] = _fmt(fb.rms_db_mean - fa.rms_db_mean, "dB")
    blind["level"] = ("raw dBFS: deaf to WHERE the level differs, and weights "
                      "sub-audible low frequencies the ear does not")

    chips["level dBA"] = _fmt(fb.rms_dba_mean - fa.rms_dba_mean, "dBA")
    blind["level dBA"] = ("A-weighted, the strongest discriminator measured on "
                          "timing/percussive defects (1.5-1.6x) and MEASURED "
                          "NOISE (0.011) on a pitch defect -- a null here does "
                          "not clear a tuning error; read chroma for that")

    chips["brightness"] = _fmt(fb.centroid_hz_mean - fa.centroid_hz_mean, "Hz", 0)
    blind["brightness"] = ("spectral centroid: moves for a filter change, a "
                           "waveform change or a lost voice alike, and cannot "
                           "say which")

    chips["rolloff"] = _fmt(fb.rolloff85_hz_mean - fa.rolloff85_hz_mean, "Hz", 0)
    blind["rolloff"] = "where 85% of the energy sits; a companion to brightness, not independent of it"

    chips["noisiness"] = _fmt(fb.flatness_mean - fa.flatness_mean, "", 3)
    blind["noisiness"] = ("spectral flatness, 0 tonal .. 1 noise-like: catches a "
                          "wrong noise waveform, blind to pitch")

    # Chroma. All-zero means NO pitched energy was found -- "no evidence", not
    # "every pitch class equally present" -- and audio_listen's own
    # chroma_shift_description() refuses to describe a shift from it. Honour
    # that refusal instead of emitting a distance computed from a zero vector.
    if not np.any(fa.chroma) or not np.any(fb.chroma):
        chips["pitch"] = "no pitched energy"
        blind["pitch"] = ("chroma found no energy in its band on at least one "
                          "side -- this is absence of evidence, not agreement")
    else:
        chips["pitch"] = "%.3f" % float(np.abs(fb.chroma - fa.chroma).sum() / 2.0)
        blind["pitch"] = ("chroma L1/2 distance, 0 identical .. 1 disjoint: the "
                          "feature that fires (0.072) on a vibrato-width defect "
                          "A-weighting scores as noise; octave- and "
                          "timbre-blind by construction. ours: %s"
                          % dominant_pitch_classes(fb.chroma))

    if with_onset:
        # Deliberately opt-in and deliberately unbounded by any gate. See the
        # module docstring: the floor this number needs is per-tune and costs
        # nine re-renders, which this module may not do.
        from sidm2.audio_tightness import analyze_tightness_files
        rep = analyze_tightness_files(orig_wav, ours_wav)
        total = len(rep.matched) + len(rep.missing)
        if not total:
            chips["onset"] = "no onsets"
            blind["onset"] = "the detector found nothing to match on the original"
        else:
            chips["onset"] = "%.1f%% (n=%d)" % (100.0 * len(rep.matched) / total, total)
            # Single '%', NOT '%%': this string is never passed through a
            # %-format, so a doubled sign would reach the page literally. The
            # offset note below IS %-formatted and correctly doubles its own.
            blind["onset"] = (
                "ORDINAL ONLY, NO GATE, NO FLOOR. A 99.8%-register-exact build "
                "measured 64.7% here against an 85-91% original-vs-itself "
                "floor, so this number is meaningful only against a baseline of "
                "the SAME tune -- never as pass/fail. The floor needs nine "
                "re-renders and is not computed here.")
            chips["offset"] = _fmt(rep.median_offset_ms, "ms", 1)
            blind["offset"] = (
                "median whole-render shift, separated from per-note looseness "
                "on purpose: a uniformly late render is rhythmically perfect "
                "but would otherwise read as ~100%% loose. Median inter-onset "
                "interval is %.0f ms -- a shift near that is not measurable "
                "here." % rep.median_ioi_ms)

    return chips, blind
