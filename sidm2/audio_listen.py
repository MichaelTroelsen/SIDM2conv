"""Audio "listening" aids: whole-file feature summaries and spectrogram images.

sidm2/audio_tightness.py answers "do onsets line up" -- a narrow, note-timing
question. This module answers the broader "what does this sound like":
level, spectral center of mass, noisiness, silence -- as text Claude can read
directly, plus a spectrogram image for the cases the text alone doesn't
explain (a filter sweep, a timbre difference with no clear onset defect).

Pure numpy + Pillow, no matplotlib/librosa/scipy -- matching audio_tightness's
zero-heavy-dep style and this project's already-installed set. Reuses
band_energies() rather than re-deriving an STFT.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Union

import numpy as np

if TYPE_CHECKING:  # annotation-only: PIL is imported lazily inside the renderers
    from PIL import Image

from sidm2.audio_tightness import band_centers, band_energies

# Frames quieter than this are treated as silence for silence_frac.
SILENCE_DBFS = -50.0

# dB floor/ceiling for spectrogram color mapping -- a fixed range (rather than
# per-image min/max) so two spectrograms rendered from the same reference are
# visually comparable instead of each auto-stretching its own contrast.
SPEC_DB_FLOOR = -80.0
SPEC_DB_CEIL = 0.0

# Diverging diff range: a driver panel this many dB above/below the original
# saturates the diff colormap. Wide enough that onset transients (tens of dB)
# don't blow out a sustained-tone comparison.
DIFF_DB_RANGE = 24.0

# ---------------------------------------------------------------------------
# Chroma (pitch-class) analysis
# ---------------------------------------------------------------------------
#
# centroid/rolloff say a render got BRIGHTER; they never say the pitch content
# moved. A 12-bin pitch-class histogram does, so the report can distinguish
# "same notes, different timbre" from "different notes".
#
# This deliberately does NOT reuse band_energies(): that function groups FFT
# bins into `nb` wide bands BEFORE anything else, and two adjacent semitones
# routinely land in one band. Pitch class needs per-bin frequency resolution,
# so chroma runs its own STFT.
PITCH_CLASS_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')

# C0. Pitch class 0 is C, so semitone distance from this reference, rounded and
# taken mod 12, indexes PITCH_CLASS_NAMES directly (A4=440 -> 57 -> 57%12=9='A').
_C0_HZ = 16.351597831287414

# Chroma needs a LONGER window than the rest of this module. The 40 ms default
# elsewhere is tuned for onset TIMING; at 40 ms an FFT bin is 25 Hz wide, while
# the gap between adjacent semitones down at A1 (55 Hz) is only ~3.3 Hz -- every
# bass note would land in whichever pitch class the bin edge happened to favour.
# 200 ms gives 5 Hz bins, which resolves the SID bass register (measured: a
# 55 Hz tone lands on 'A' with a clear margin; at 40 ms it does not).
CHROMA_WIN_S = 0.2
CHROMA_HOP_S = 0.1

# C1..C7. The plan for this feature suggested a 65.4 Hz (C2) floor, but SID bass
# routinely runs below that -- A1 is 55 Hz -- so a C2 floor would discard the
# very register the long window exists to resolve. C1 covers it.
CHROMA_FMIN_HZ = 32.703195662574764   # C1
CHROMA_FMAX_HZ = 2093.004522404789    # C7

# Below this fraction of total chroma energy, a pitch class' change is noise
# rather than a shift worth naming in the report.
CHROMA_MIN_SHIFT = 0.02

# ---------------------------------------------------------------------------
# A-weighting (perceptual loudness)
# ---------------------------------------------------------------------------
#
# rms_db_* are raw dBFS, where 2 dB at 8 kHz counts exactly as much as 2 dB at
# 200 Hz although the ear is far less sensitive to the first. A-weighting
# (IEC 61672) is the standard first-order correction and is closed-form -- no
# lookup table. Verified against the published third-octave table
# (31.5/63/125/250/500/1k/2k/4k/8k Hz) to within 0.13 dB.
#
# ADDITIVE, never a replacement: raw dBFS stays the right number for an exact
# level check (confirming a driver's master-volume nibble, say), while dBA is
# the better number for "would a listener call this quieter".

_SILENT_FEATURES_DB = -120.0

# The correction must NOT be read off band_energies()' bands, for the same
# reason chroma_vector() runs its own STFT: at the default 40 linear bands they
# are 199 Hz wide, and the A curve falls fastest exactly where SID bass sits.
# Measured band-centre error over 30-8000 Hz, 40 linear bands:
#      55 Hz   true -28.6 dB, via band centre -15.7 dB  ->  +12.8 dB WRONG
#      60 Hz   true -27.1 dB, via band centre -15.7 dB  ->  +11.3 dB WRONG
#     220 Hz   true  -9.9 dB, via band centre -15.7 dB  ->   -5.8 dB WRONG
#    1000 Hz   true   0.0 dB, via band centre  -0.3 dB  ->   -0.3 dB ok
# A 12.8 dB error on a bass note is not a rounding difference, it is a
# confident wrong answer. So weighting is applied per FFT BIN, full resolution,
# and is therefore independent of nb/band_scale (pinned as a test).
#
# What the shipped implementation actually achieves, measured on pure tones as
# (dBA - dBFS) against the true curve:
#    1000 Hz  0.00 dB error      440 Hz  0.00 dB      220 Hz  0.02 dB
#     110 Hz  0.18 dB error       60 Hz  1.08 dB       55 Hz  1.36 dB
# Exact above ~220 Hz. The residual at the very bottom is FFT bin width -- at
# a 40 ms window bins are 25 Hz apart, so a 55 Hz tone's energy straddles
# several bins and the A curve is convex across them, biasing the energy
# weighted average slightly high. It is bounded, ~10x better than the banded
# alternative, and pinned as a test so it cannot silently grow.


@dataclass
class AudioFeatures:
    duration_s: float
    rms_db_mean: float
    rms_db_max: float
    silence_frac: float       # fraction of frames below SILENCE_DBFS
    centroid_hz_mean: float   # spectral "center of mass" -- brightness
    centroid_hz_std: float
    rolloff85_hz_mean: float  # freq below which 85% of energy sits
    zcr_mean: float           # zero-crossing rate, 0..1 -- noisiness/pitch proxy
    flatness_mean: float      # geometric/arithmetic mean of band energy, 0 (tonal) .. 1 (noise-like)
    # 12-bin pitch-class histogram, index 0 = C, summing to 1.0. All-zeros means
    # NO pitched energy was found in [CHROMA_FMIN_HZ, CHROMA_FMAX_HZ] -- that is
    # "no evidence", not "every pitch class equally present", and
    # chroma_shift_description() refuses to describe a shift from it.
    chroma: np.ndarray = field(default_factory=lambda: np.zeros(12))
    # Which band geometry produced centroid/rolloff/flatness. Recorded because
    # a 'linear' and a 'mel' AudioFeatures are NOT comparable -- the same audio
    # yields different numbers under each -- and a delta between them would look
    # like a real difference. format_feature_report() refuses such a pair.
    band_scale: str = 'linear'
    # A-weighted (IEC 61672) counterparts of rms_db_mean/rms_db_max, in dBA.
    # Additive -- the raw dBFS fields above stay authoritative for an exact
    # level check. Defaulted so the no-spectrum early return stays valid.
    rms_dba_mean: float = _SILENT_FEATURES_DB
    rms_dba_max: float = _SILENT_FEATURES_DB


def _frame_rms(x: np.ndarray, hop: int, win: int) -> np.ndarray:
    n = max(0, (len(x) - win) // hop + 1)
    out = np.zeros(n)
    for i in range(n):
        seg = x[i * hop: i * hop + win]
        if seg.size:
            out[i] = np.sqrt(np.mean(seg.astype(np.float64) ** 2))
    return out


def chroma_vector(x: np.ndarray, sr: int, hop_s: float = CHROMA_HOP_S,
                   win_s: float = CHROMA_WIN_S, fmin: float = CHROMA_FMIN_HZ,
                   fmax: float = CHROMA_FMAX_HZ) -> np.ndarray:
    """Energy-weighted 12-bin pitch-class histogram, normalized to sum 1.0.

    Returns all zeros when no energy falls in [fmin, fmax] -- an empty result
    that a caller can tell apart from a flat one, on the same "no evidence is
    not a zero" rule as sidm2.fidelity_common.score_pct.

    CAVEAT, and it is not small: chroma folds every FFT bin onto a pitch class,
    so a harmonically rich waveform contributes its HARMONICS too, not just its
    fundamental. A 55 Hz sawtooth puts energy on A (110, 220 Hz), but also on E
    (165 Hz) and C# (275 Hz). SID's saw/pulse voices are harmonically rich by
    construction, so read this as "where the pitch energy sits", not "which
    notes are being played". It answers 'did the pitch content move', which is
    a comparison between two renders -- not 'what note is this'.
    """
    win = max(2, int(round(win_s * sr)))
    hop = max(1, int(round(hop_s * sr)))
    hist = np.zeros(12)
    if len(x) < win:
        return hist

    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    in_band = (freqs >= fmin) & (freqs <= fmax) & (freqs > 0)
    if not in_band.any():
        return hist

    # Precomputed once: the bin -> pitch-class map depends only on the window
    # geometry, not on the audio.
    pc = np.full(freqs.shape, -1, dtype=np.int64)
    pc[in_band] = np.rint(12 * np.log2(freqs[in_band] / _C0_HZ)).astype(np.int64) % 12
    valid = pc >= 0
    pc_valid = pc[valid]

    window = np.hanning(win)
    n_frames = (len(x) - win) // hop + 1
    for i in range(n_frames):
        seg = x[i * hop: i * hop + win] * window
        mag2 = np.abs(np.fft.rfft(seg)) ** 2
        hist += np.bincount(pc_valid, weights=mag2[valid], minlength=12)

    total = hist.sum()
    return hist / total if total > 0 else hist


def chroma_shift_description(orig: np.ndarray, driver: np.ndarray,
                              top_n: int = 2,
                              min_delta: float = CHROMA_MIN_SHIFT) -> str:
    """One-line account of how pitch-class energy moved between two renders.

    e.g. "energy shifted toward C# (+0.08), away from G (-0.06)". Says so
    plainly when either side has no pitched energy, rather than reporting a
    shift computed from an empty histogram.
    """
    orig = np.asarray(orig, dtype=np.float64).ravel()
    driver = np.asarray(driver, dtype=np.float64).ravel()
    if orig.size != 12 or driver.size != 12:
        return "chroma unavailable (expected 12 bins per side)"
    if orig.sum() <= 0 and driver.sum() <= 0:
        return "no pitched energy detected on either side"
    if orig.sum() <= 0:
        return "no pitched energy in the original -- cannot describe a shift"
    if driver.sum() <= 0:
        return "no pitched energy in the driver render -- cannot describe a shift"

    delta = driver - orig
    order = np.argsort(delta)
    gains = [i for i in order[::-1] if delta[i] >= min_delta][:top_n]
    losses = [i for i in order if delta[i] <= -min_delta][:top_n]

    if not gains and not losses:
        return (f"pitch-class distribution essentially unchanged "
                f"(largest shift {np.abs(delta).max():.3f})")

    parts = []
    if gains:
        parts.append("toward " + ", ".join(
            f"{PITCH_CLASS_NAMES[i]} ({delta[i]:+.3f})" for i in gains))
    if losses:
        parts.append("away from " + ", ".join(
            f"{PITCH_CLASS_NAMES[i]} ({delta[i]:+.3f})" for i in losses))
    return "energy shifted " + ", ".join(parts)


def dominant_pitch_classes(chroma: np.ndarray, top_n: int = 3) -> str:
    """The strongest pitch classes, as "A 0.31, E 0.22, C# 0.14"."""
    chroma = np.asarray(chroma, dtype=np.float64).ravel()
    if chroma.size != 12 or chroma.sum() <= 0:
        return "n/a"
    idx = np.argsort(chroma)[::-1][:top_n]
    return ", ".join(f"{PITCH_CLASS_NAMES[i]} {chroma[i]:.2f}" for i in idx)


def a_weight_db(f):
    """IEC 61672 A-weighting, in dB, at frequency f (Hz). Accepts an array.

    -inf at DC, which is a real zero of the response rather than missing data.
    """
    f = np.asarray(f, dtype=np.float64)
    f2 = f ** 2
    with np.errstate(divide='ignore', invalid='ignore'):
        ra = (12194.0 ** 2 * f2 ** 2) / (
            (f2 + 20.6 ** 2)
            * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2))
            * (f2 + 12194.0 ** 2))
        db = 20 * np.log10(ra) + 2.0     # +2.0 normalizes A(1 kHz) to 0 dB
    return np.where(f > 0, db, -np.inf)


def a_weighting_correction_db(x: np.ndarray, sr: int, hop_s: float = 0.01,
                               win_s: float = 0.04) -> np.ndarray:
    """Per-frame dB offset turning a raw dBFS level into an A-weighted dBA.

    One value per analysis frame, on the SAME frame grid _frame_rms() uses, so
    the two are simply added. A frame with no energy gets 0.0 rather than a
    fabricated correction -- it has no spectrum to weight, and no evidence must
    not become a number (score_pct's rule, sidm2/fidelity_common.py).

    Weighting is per FFT bin in the POWER domain: an amplitude gain of A dB is
    a power factor of 10**(A/10), and the offset returned is
    10*log10(sum(g*P) / sum(P)). For a pure tone that collapses exactly to the
    A curve at the tone's own frequency, which is what keeps the result
    comparable with rms_db_*.
    """
    win = max(2, int(round(win_s * sr)))
    hop = max(1, int(round(hop_s * sr)))
    n_frames = max(0, (len(x) - win) // hop + 1)
    if n_frames == 0:
        return np.zeros(0)

    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    gain = np.zeros(freqs.shape)
    pos = freqs > 0
    gain[pos] = 10.0 ** (a_weight_db(freqs[pos]) / 10.0)

    window = np.hanning(win)
    out = np.zeros(n_frames)
    for i in range(n_frames):
        seg = x[i * hop: i * hop + win] * window
        power = np.abs(np.fft.rfft(seg)) ** 2
        total = power.sum()
        if total > 0:
            out[i] = 10 * np.log10(max(float((power * gain).sum()), 1e-30) / total)
    return out


def extract_features(x: np.ndarray, sr: int, hop_ms: float = 10, win_ms: float = 40,
                      nb: int = 40, fmin: float = 30, fmax: float = 8000,
                      band_scale: str = 'linear') -> AudioFeatures:
    """Whole-file feature summary. NOT onset-aligned -- a global average, so it
    complements audio_tightness's per-note numbers rather than replacing them.

    band_scale='mel' spaces the analysis bands by pitch rather than by Hz, so
    centroid/rolloff/flatness track what a listener notices instead of dividing
    the spectrum evenly in Hz (which spends half its bins above 4 kHz, where
    SID material rarely sits). It is OPT-IN: the linear default is what every
    existing number in this project was computed under, and the two are NOT
    comparable -- see AudioFeatures.band_scale and format_feature_report's guard.
    """
    hop = max(1, int(round(hop_ms / 1000 * sr)))
    win = max(2, int(round(win_ms / 1000 * sr)))

    rms = _frame_rms(x, hop, win)
    rms_db = 20 * np.log10(np.clip(rms, 1e-9, None)) if rms.size else np.array([])

    bands = band_energies(x, sr, hop_s=hop_ms / 1000, win_s=win_ms / 1000,
                           nb=nb, fmin=fmin, fmax=fmax, scale=band_scale)
    if bands.shape[0] == 0:
        return AudioFeatures(
            duration_s=len(x) / sr if sr else 0.0,
            rms_db_mean=float(rms_db.mean()) if rms_db.size else _SILENT_FEATURES_DB,
            rms_db_max=float(rms_db.max()) if rms_db.size else _SILENT_FEATURES_DB,
            silence_frac=1.0,
            centroid_hz_mean=0.0, centroid_hz_std=0.0,
            rolloff85_hz_mean=0.0, zcr_mean=0.0, flatness_mean=0.0,
            band_scale=band_scale,
        )

    # From band_centers(), NOT a local np.linspace: the centres MUST match the
    # geometry band_energies() actually binned with, or the centroid weights
    # energies by frequencies they were never measured at.
    centers = band_centers(nb, fmin, fmax, band_scale)

    energy = bands.sum(axis=1)
    nz = energy > 0
    centroid = np.zeros(len(energy))
    centroid[nz] = (bands[nz] @ centers) / energy[nz]

    cumsum = np.cumsum(bands, axis=1)
    total = cumsum[:, -1]
    rolloff = np.zeros(len(energy))
    for i in np.nonzero(nz)[0]:
        idx = int(np.searchsorted(cumsum[i], 0.85 * total[i]))
        rolloff[i] = centers[min(idx, len(centers) - 1)]

    gmean = np.exp(np.mean(np.log(bands + 1e-12), axis=1))
    amean = bands.mean(axis=1) + 1e-12
    flatness = gmean / amean

    zcr = float(np.mean(np.abs(np.diff(np.sign(x))) > 0)) if len(x) > 1 else 0.0

    # A CORRECTION on the true time-domain dBFS, not a second independent level
    # estimate -- so dBA and dBFS share one scale and their difference is
    # exactly "how much of this level the ear discounts".
    a_corr = a_weighting_correction_db(x, sr, hop_ms / 1000, win_ms / 1000)
    n_dba = min(len(rms_db), len(a_corr))
    rms_dba = (rms_db[:n_dba] + a_corr[:n_dba]) if n_dba else np.array([])

    return AudioFeatures(
        duration_s=len(x) / sr if sr else 0.0,
        rms_db_mean=float(np.mean(rms_db)) if rms_db.size else _SILENT_FEATURES_DB,
        rms_db_max=float(np.max(rms_db)) if rms_db.size else _SILENT_FEATURES_DB,
        silence_frac=float(np.mean(rms_db < SILENCE_DBFS)) if rms_db.size else 1.0,
        centroid_hz_mean=float(np.mean(centroid[nz])) if nz.any() else 0.0,
        centroid_hz_std=float(np.std(centroid[nz])) if nz.any() else 0.0,
        rolloff85_hz_mean=float(np.mean(rolloff[nz])) if nz.any() else 0.0,
        zcr_mean=zcr,
        flatness_mean=float(np.mean(flatness[nz])) if nz.any() else 0.0,
        rms_dba_mean=float(np.mean(rms_dba)) if rms_dba.size else _SILENT_FEATURES_DB,
        rms_dba_max=float(np.max(rms_dba)) if rms_dba.size else _SILENT_FEATURES_DB,
        # Its OWN window, not win_ms: 40 ms cannot resolve semitones in SID's
        # bass register (see CHROMA_WIN_S).
        chroma=chroma_vector(x, sr),
        band_scale=band_scale,
    )


def format_feature_report(orig: AudioFeatures, driver: AudioFeatures,
                           orig_label: str = 'original', driver_label: str = 'driver') -> str:
    """Text summary for Claude: side-by-side whole-file features plus deltas.

    Deliberately labeled and hedged rather than scored pass/fail -- unlike the
    onset report, there is no established threshold for "different enough to
    matter" on these features, so this is context for a human/Claude read, not
    a verdict.
    """
    # Refuse rather than subtract. centroid/rolloff/flatness are functions of
    # the band geometry, so the same audio analysed under 'linear' and 'mel'
    # gives different numbers; differencing them would render a pure
    # measurement-settings artifact as a finding about the driver.
    if orig.band_scale != driver.band_scale:
        return (
            "AUDIO FEATURE SUMMARY: REFUSED\n" + "=" * 70 + "\n"
            f"  The two sides were analysed under different band scales "
            f"({orig_label}={orig.band_scale!r}, {driver_label}={driver.band_scale!r}).\n"
            "  Spectral features depend on band geometry, so a delta between them\n"
            "  would measure the settings, not the audio. Re-extract both sides with\n"
            "  the same band_scale."
        )

    lines = []
    scale_note = '' if orig.band_scale == 'linear' else f", {orig.band_scale}-spaced bands"
    lines.append(f"AUDIO FEATURE SUMMARY (whole-file average, not onset-aligned{scale_note})")
    lines.append("=" * 70)
    lines.append(f"{'':22s} {orig_label[:20]:>20s} {driver_label[:20]:>20s} {'delta':>10s}")

    def row(label, a, b, unit='', fmt='{:.1f}'):
        d = b - a
        lines.append(f"{label:22s} {fmt.format(a) + unit:>20s} {fmt.format(b) + unit:>20s} "
                      f"{('+' if d >= 0 else '') + fmt.format(d) + unit:>10s}")

    row('duration', orig.duration_s, driver.duration_s, 's')
    row('RMS level (mean)', orig.rms_db_mean, driver.rms_db_mean, ' dBFS')
    row('RMS level (peak)', orig.rms_db_max, driver.rms_db_max, ' dBFS')
    row('RMS level (A-wtd)', orig.rms_dba_mean, driver.rms_dba_mean, ' dBA')
    row('silence fraction', orig.silence_frac * 100, driver.silence_frac * 100, '%')
    row('spectral centroid', orig.centroid_hz_mean, driver.centroid_hz_mean, ' Hz')
    row('centroid spread', orig.centroid_hz_std, driver.centroid_hz_std, ' Hz')
    row('rolloff (85%)', orig.rolloff85_hz_mean, driver.rolloff85_hz_mean, ' Hz')
    row('zero-crossing rate', orig.zcr_mean * 100, driver.zcr_mean * 100, '%')
    row('spectral flatness', orig.flatness_mean, driver.flatness_mean, '', fmt='{:.3f}')

    lines.append("")
    # top_n=2 here, not the function default of 3: three classes overflow the
    # 20-char column and break the table alignment.
    lines.append(f"{'dominant pitch':22s} "
                  f"{dominant_pitch_classes(orig.chroma, top_n=2):>20s} "
                  f"{dominant_pitch_classes(driver.chroma, top_n=2):>20s}")
    lines.append(f"  pitch content: {chroma_shift_description(orig.chroma, driver.chroma)}")

    lines.append("")
    lines.append("  centroid/rolloff higher on one side = that render is brighter (more")
    lines.append("  high-frequency energy) -- often a filter cutoff or waveform difference.")
    lines.append("  flatness closer to 1.0 = more noise-like (e.g. an unfiltered noise")
    lines.append("  waveform or digi channel); closer to 0.0 = more tonal.")
    lines.append("  dBA is the dBFS level with IEC 61672 A-weighting applied -- the same")
    lines.append("  level as the ear would judge it, discounting bass heavily (~-27 dB at")
    lines.append("  60 Hz) and boosting 2-4 kHz slightly. Two renders equal in dBFS but")
    lines.append("  far apart in dBA differ in where their energy sits, not how much")
    lines.append("  there is. dBFS stays the number for an exact level check.")
    lines.append("  pitch content answers what centroid cannot: whether the NOTES moved,")
    lines.append("  not just the brightness. It folds in harmonics as well as fundamentals")
    lines.append("  (a SID saw/pulse voice is harmonically rich), so read it as a")
    lines.append("  between-render comparison, not as note transcription.")
    lines.append("  These are global averages and can hide a localized problem -- if they")
    lines.append("  don't explain a discrepancy the onset report flagged, render a")
    lines.append("  spectrogram (--spectrogram) and inspect it directly.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Windowed (section-aware) features
# ---------------------------------------------------------------------------
#
# extract_features() returns ONE AudioFeatures for a whole render. A driver that
# is right for 90% of a song and badly wrong across one 2-second bridge shows up
# there as a small average delta that is easy to miss -- the defect is diluted by
# every correct second around it. Slicing the render into sections and comparing
# them individually is what makes a localized problem visible.
WINDOW_S = 5.0

# A trailing remainder shorter than this fraction of a full window is dropped.
# Its statistics come from proportionally fewer analysis frames, so it would win
# the worst-window search on sample-count noise rather than on content.
MIN_WINDOW_FRACTION = 0.5

# Outlier threshold, in robust-sigma units, for calling a window out. Below it
# nothing is named: windows all sitting within a few sigma of each other means
# there is no localized problem to find, and naming a "worst" one anyway
# manufactures a finding out of ordinary variation.
WINDOW_OUTLIER_SIGMA = 3.0

# Used when the baseline is PERFECTLY FLAT (every window's delta identical), so
# no sigma can be formed at all. Deviation is then judged against the metric's
# own magnitude, which is dimensionless and so still comparable across the
# dB/Hz/ratio columns.
#
# The obvious alternative -- fall back to std -- is not merely weaker, it is
# actively broken, and this was measured rather than reasoned about. For ONE
# outlier among n identical values, std-based z has a hard ceiling of
# n/sqrt(n-1): 2.5 at n=5, which is BELOW WINDOW_OUTLIER_SIGMA. A section that
# collapsed into noise (+3035 Hz centroid, +0.888 flatness -- about as obvious
# as a defect gets) scored exactly 2.5 and was reported as "no section stands
# out". A confident false negative on the clearest possible case is the worst
# failure this module could have, so the std fallback is gone.
WINDOW_RELATIVE_DEVIATION = 0.25

# With fewer windows than this the spread estimate is itself too unstable to
# rank against, so the table still prints but the verdict is withheld -- the
# same "not enough evidence to claim anything" rule the rest of this codebase
# follows (see fidelity_common.score_pct, audio_tightness_tool's repeat floor).
MIN_WINDOWS_FOR_OUTLIER = 4

# (attribute, label, unit, format) for the metrics the outlier search ranks.
# chroma is deliberately absent: it is a 12-vector, not a scalar, so it has no
# single delta to normalize -- chroma_shift_description() reports it instead.
_WINDOW_METRICS = (
    ('rms_db_mean', 'RMS level', ' dB', '{:+.1f}'),
    ('centroid_hz_mean', 'centroid', ' Hz', '{:+.0f}'),
    ('rolloff85_hz_mean', 'rolloff', ' Hz', '{:+.0f}'),
    ('flatness_mean', 'flatness', '', '{:+.3f}'),
    ('silence_frac', 'silence', '', '{:+.3f}'),
)

Window = Tuple[float, AudioFeatures]


@dataclass
class WindowOutlier:
    """The single most locally-deviant window.

    `score` is normalized so that >= 1.0 means "clears the flagging bar",
    whichever branch produced it -- that is what makes a sigma-judged metric and
    a flat-baseline-judged one rankable against each other. `detail` carries the
    human-readable basis, since the two branches are not the same quantity and
    printing one number as if they were would be a small lie.
    """
    index: int
    start_s: float
    metric: str          # human label from _WINDOW_METRICS
    delta: float         # driver - orig, in that metric's own unit
    score: float         # >= 1.0 => flagged
    basis: str           # 'sigma' | 'flat-baseline'
    detail: str          # e.g. "4.2 sigma" / "9.1x the baseline level"

    @property
    def is_outlier(self) -> bool:
        return self.score >= 1.0


def extract_features_windowed(x: np.ndarray, sr: int, window_s: float = WINDOW_S,
                               hop_s: Optional[float] = None,
                               **kwargs) -> List[Window]:
    """[(window_start_s, AudioFeatures), ...] -- extract_features() per section.

    hop_s=None gives non-overlapping windows (hop == window). A signal shorter
    than one window yields a single window covering all of it, rather than an
    empty list, so a short render still reports something.

    Deliberately a thin wrapper: extract_features() is unchanged and does all
    the work, so a windowed number and a whole-file number are always the same
    computation over different spans, never two implementations that could drift.
    """
    if hop_s is None:
        hop_s = window_s
    if len(x) == 0:
        return []

    win = max(1, int(round(window_s * sr)))
    hop = max(1, int(round(hop_s * sr)))
    if len(x) < win:
        return [(0.0, extract_features(x, sr, **kwargs))]

    min_len = max(1, int(win * MIN_WINDOW_FRACTION))
    out: List[Window] = []
    start = 0
    while start < len(x):
        seg = x[start:start + win]
        if len(seg) < min_len:
            break
        out.append((start / sr, extract_features(seg, sr, **kwargs)))
        start += hop
    return out


def _robust_spread(values: np.ndarray) -> float:
    """MAD scaled to normal-consistent sigma. 0.0 when the series is flat.

    MAD rather than std so the one genuinely bad window cannot inflate the very
    scale it is being judged against. It has a known breakdown -- any series
    where more than half the values are identical, e.g. [0,0,0,0,10], gives
    exactly 0 -- and that case is handled by the caller's flat-baseline branch,
    NOT by falling back to std. See WINDOW_RELATIVE_DEVIATION for why the std
    fallback was removed.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.size == 0:
        return 0.0
    return float(np.median(np.abs(v - np.median(v)))) * 1.4826


def _metric_scale(orig_vals: np.ndarray, driver_vals: np.ndarray) -> float:
    """Typical magnitude of a metric, for the flat-baseline relative test.

    Median of |value| on each side, whichever is larger -- median so one bad
    window does not set the yardstick, larger-of-two so a metric that is ~0 on
    the original but large on the driver is measured against the side that has
    something to measure.
    """
    o = float(np.median(np.abs(np.asarray(orig_vals, dtype=np.float64))))
    d = float(np.median(np.abs(np.asarray(driver_vals, dtype=np.float64))))
    return max(o, d)


def worst_window(orig_windows: Sequence[Window],
                  driver_windows: Sequence[Window]) -> Optional[WindowOutlier]:
    """The most locally-deviant window across all tracked metrics, or None.

    TWO decisions carry this function.

    First, metrics live in different units -- dB, Hz, dimensionless ratios -- so
    a raw |delta| cannot be compared across them (a 100 Hz centroid shift and a
    0.1 flatness shift are not the same size). Each metric's deltas are
    normalized by their OWN robust spread, making "how unusual is this window
    for this metric" the common currency.

    Second, the MEDIAN delta is subtracted before ranking. A render that is
    uniformly 2 dB loud is 2 dB loud in every window; that is a whole-file
    offset, which format_feature_report() already shows. Subtracting it leaves
    only what differs BETWEEN sections, which is the one thing windowing adds.
    This mirrors TightnessReport.median_offset_ms in sidm2/audio_tightness.py,
    which splits a systematic shift from per-note jitter for the same reason.

    Returns None when nothing deviates (every metric flat across windows) or
    when there is no overlap to compare.
    """
    n = min(len(orig_windows), len(driver_windows))
    if n == 0:
        return None

    best: Optional[WindowOutlier] = None
    for attr, label, _unit, _fmt in _WINDOW_METRICS:
        orig_vals = np.array([getattr(orig_windows[i][1], attr) for i in range(n)], dtype=np.float64)
        driver_vals = np.array([getattr(driver_windows[i][1], attr) for i in range(n)], dtype=np.float64)
        deltas = driver_vals - orig_vals
        dev = np.abs(deltas - np.median(deltas))
        if not dev.any():
            continue          # uniform across windows: an offset, not a localized defect

        spread = _robust_spread(deltas)
        if spread > 0:
            scores = (dev / spread) / WINDOW_OUTLIER_SIGMA
            basis = 'sigma'
        else:
            # Flat baseline: no observed variation to form a sigma from, so
            # judge the deviation against the metric's own magnitude instead.
            scale = _metric_scale(orig_vals, driver_vals)
            rel = dev / scale if scale > 0 else np.where(dev > 0, np.inf, 0.0)
            scores = rel / WINDOW_RELATIVE_DEVIATION
            basis = 'flat-baseline'

        i = int(np.argmax(scores))
        if best is not None and scores[i] <= best.score:
            continue
        if basis == 'sigma':
            detail = f"{dev[i] / spread:.1f} sigma"
        else:
            scale = _metric_scale(orig_vals, driver_vals)
            detail = (f"{dev[i] / scale:.1f}x the baseline level, and every other "
                      f"window is identical"
                      if scale > 0 else
                      "nonzero where every other window is exactly zero")
        best = WindowOutlier(index=i, start_s=float(orig_windows[i][0]),
                             metric=label, delta=float(deltas[i]),
                             score=float(scores[i]), basis=basis, detail=detail)
    return best


def format_windowed_diff_report(orig_windows: Sequence[Window],
                                 driver_windows: Sequence[Window],
                                 orig_label: str = 'original',
                                 driver_label: str = 'driver') -> str:
    """Per-section deltas, worst window called out first.

    The call-out leads because the table exists to be skimmed, not read: dumping
    every window's full feature set would recreate the "too much to scan"
    problem that windowing is meant to solve.
    """
    lines = []
    lines.append("WINDOWED FEATURE DIFF (per section -- finds LOCALIZED problems a "
                 "whole-file mean hides)")
    lines.append("=" * 78)

    n = min(len(orig_windows), len(driver_windows))
    if n == 0:
        lines.append("  No comparable windows (one side produced no audio).")
        return "\n".join(lines)
    if len(orig_windows) != len(driver_windows):
        lines.append(f"  NOTE: window counts differ ({orig_label} {len(orig_windows)}, "
                      f"{driver_label} {len(driver_windows)}) -- the renders are not the "
                      f"same length. Comparing the first {n}.")

    outlier = worst_window(orig_windows, driver_windows)
    flagged = bool(outlier and outlier.is_outlier and n >= MIN_WINDOWS_FOR_OUTLIER)
    if outlier is None:
        lines.append("  Every tracked metric is uniform across windows -- no section deviates")
        lines.append("  from the rest. A whole-render offset, if any, is in the table below")
        lines.append("  and in the whole-file report; it is not a localized defect.")
    elif n < MIN_WINDOWS_FOR_OUTLIER:
        lines.append(f"  Worst: window {outlier.index} (t={outlier.start_s:.1f}s), "
                      f"{outlier.metric} {outlier.delta:+.3g} ({outlier.detail})")
        lines.append(f"  NOT called an outlier: only {n} window(s), and ranking needs "
                      f"{MIN_WINDOWS_FOR_OUTLIER}+ to estimate a spread worth comparing to.")
    elif flagged:
        lines.append(f"  >> WORST WINDOW: {outlier.start_s:.1f}s "
                      f"(window {outlier.index}) -- {outlier.metric} "
                      f"{outlier.delta:+.3g}, {outlier.detail}")
    else:
        lines.append(f"  No section stands out (largest deviation: {outlier.metric} "
                      f"{outlier.delta:+.3g}, {outlier.detail}) -- the difference between "
                      f"these renders is spread evenly, not localized.")

    lines.append("")
    header = f"  {'start':>7s}"
    for _attr, label, _unit, _fmt in _WINDOW_METRICS:
        header += f" {label:>11s}"
    lines.append(header)

    for i in range(n):
        o, d = orig_windows[i][1], driver_windows[i][1]
        marker = '>' if (flagged and outlier.index == i) else ' '
        row = f"{marker} {orig_windows[i][0]:6.1f}s"
        for attr, _label, _unit, fmt in _WINDOW_METRICS:
            row += f" {fmt.format(getattr(d, attr) - getattr(o, attr)):>11s}"
        lines.append(row)

    lines.append("")
    lines.append("  Values are driver MINUS original, per section. The worst-window search")
    lines.append("  removes each metric's MEDIAN delta first, so a uniform whole-render")
    lines.append("  offset does not read as a localized defect -- only variation BETWEEN")
    lines.append("  sections does. A window is judged against the spread of the others")
    lines.append("  ('N sigma'), or, when the other windows are all identical and no spread")
    lines.append("  exists, against the metric's own magnitude ('Nx the baseline level').")
    lines.append("  Either way the score is dimensionless, which is what makes the dB, Hz")
    lines.append("  and ratio columns rankable against each other at all.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Spectrogram image rendering
# ---------------------------------------------------------------------------

# A compact inferno-like colormap (black -> purple -> red -> orange -> pale
# yellow), hand-picked control points, linearly interpolated. Avoids a
# matplotlib dependency; visually similar to matplotlib's 'inferno' at the
# resolution these images are viewed at.
_INFERNO_STOPS = np.array([
    [0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99],
    [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 255, 164],
], dtype=np.float64)

# Diverging blue-white-red for the diff panel: driver quieter than original at
# a frequency reads blue, louder reads red, agreement reads white.
_DIFF_STOPS = np.array([
    [33, 102, 172], [146, 197, 222], [247, 247, 247],
    [244, 165, 130], [178, 24, 43],
], dtype=np.float64)


def _colormap(v: np.ndarray, stops: np.ndarray) -> np.ndarray:
    """v in [0,1], any shape -> same shape + (3,) uint8 via linear interp over stops."""
    n = len(stops) - 1
    pos = np.clip(v, 0, 1) * n
    idx = np.clip(pos.astype(int), 0, n - 1)
    frac = (pos - idx)[..., None]
    c0 = stops[idx]
    c1 = stops[idx + 1]
    rgb = c0 + (c1 - c0) * frac
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _db_bands(x: np.ndarray, sr: int, hop_ms: float, win_ms: float, nb: int,
              fmin: float, fmax: float) -> np.ndarray:
    bands = band_energies(x, sr, hop_s=hop_ms / 1000, win_s=win_ms / 1000,
                           nb=nb, fmin=fmin, fmax=fmax)
    return 10 * np.log10(np.clip(bands, 1e-12, None))


def _panel_image(db: np.ndarray, db_floor: float, db_ceil: float) -> "Image.Image":
    from PIL import Image
    norm = (db - db_floor) / (db_ceil - db_floor)
    rgb = _colormap(norm, _INFERNO_STOPS)
    # (n_frames, n_bands, 3) -> rows=freq (low at bottom), cols=time
    img = np.ascontiguousarray(np.transpose(rgb, (1, 0, 2))[::-1])
    return Image.fromarray(img, mode='RGB')


def _diff_panel_image(diff_db: np.ndarray, db_range: float) -> "Image.Image":
    from PIL import Image
    norm = (diff_db + db_range) / (2 * db_range)
    rgb = _colormap(norm, _DIFF_STOPS)
    img = np.ascontiguousarray(np.transpose(rgb, (1, 0, 2))[::-1])
    return Image.fromarray(img, mode='RGB')


def render_comparison_spectrogram(
        orig_x: np.ndarray, orig_sr: int, driver_x: np.ndarray, driver_sr: int,
        out_path: Union[str, Path], hop_ms: float = 10, win_ms: float = 40,
        nb: int = 96, fmin: float = 30, fmax: float = 8000,
        orig_label: str = 'original', driver_label: str = 'driver',
        max_width: int = 1400, band_px: int = 4) -> Path:
    """Render a 3-panel PNG: original spectrogram / driver spectrogram / dB
    diff, stacked vertically with labels. For visual inspection (by Claude,
    via the Read tool) when the text feature report and onset report don't
    explain a discrepancy -- see format_feature_report's closing note.

    Both sides are leveled against the SAME reference (the louder side's
    peak), so panel brightness is comparable across panels -- an
    independently-normalized pair would each stretch to full contrast and
    hide a genuine level difference.
    """
    from PIL import Image, ImageDraw

    db_o = _db_bands(orig_x, orig_sr, hop_ms, win_ms, nb, fmin, fmax)
    db_d = _db_bands(driver_x, driver_sr, hop_ms, win_ms, nb, fmin, fmax)
    ref = max(db_o.max(initial=SPEC_DB_FLOOR), db_d.max(initial=SPEC_DB_FLOOR))
    db_o = db_o - ref
    db_d = db_d - ref

    n = min(len(db_o), len(db_d))
    diff = db_o[:n] - db_d[:n]

    img_o = _panel_image(db_o, SPEC_DB_FLOOR, SPEC_DB_CEIL)
    img_d = _panel_image(db_d, SPEC_DB_FLOOR, SPEC_DB_CEIL)
    img_diff = _diff_panel_image(diff, DIFF_DB_RANGE)

    panel_h = nb * band_px
    label_h = 20
    panels = [(f"{orig_label}  (0 dB = louder side's peak)", img_o),
              (driver_label, img_d),
              (f"diff (orig - driver, +-{DIFF_DB_RANGE:g} dB)", img_diff)]

    widths = [im.width for _, im in panels]
    target_w = min(max_width, max(widths)) if widths else max_width
    target_w = max(target_w, 1)

    total_h = (panel_h + label_h) * len(panels)
    canvas = Image.new('RGB', (target_w, total_h), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)

    y = 0
    for label, im in panels:
        resized = im.resize((target_w, panel_h), Image.NEAREST)
        canvas.paste(resized, (0, y + label_h))
        draw.text((4, y + 2), label, fill=(230, 230, 230))
        y += panel_h + label_h

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path
