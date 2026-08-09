"""Audio-domain "tightness" measurement: onset timing + attack-shape comparison.

Register-write-exact trace comparison (trace_comparison_tool.py,
accuracy_heatmap_tool.py) is SIDM2's primary fidelity measure, but a
register match can still sound "not tight" to a human ear -- a verified,
97%+ register-exact Blackbird build (docs/players/BLACKBIRD.md's B13 entry)
still drew "something with the perc or drums" from a real listening pass,
with no dip in the register score to flag it. This module gives that
complaint a number: do note/drum onsets land at the same time, with the
same attack shape, as the original.

Pure array-in/array-out -- no subprocess, no file I/O except load_wav_mono
and analyze_tightness_files, so the rest is testable without VICE/SID2WAV
installed. Generalizes bin/listen_compare.py's get_audio()/logmel() (NOT
imported from there -- that file is Galway-digi-coupled) to onset detection
rather than continuous pitch tracking.
"""
import logging
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Onset:
    t: float


@dataclass
class OnsetMatch:
    orig_t: float
    driver_t: float
    delta_ms: float
    rise_delta_ms: float
    spectral_dist: float
    loose: bool
    # delta_ms with the run's systematic offset removed (see
    # TightnessReport.median_offset_ms). This is the "is this note itself
    # early/late relative to the rest of the performance" number.
    jitter_ms: float = 0.0
    # jitter_ms (not delta_ms) exceeding loose_threshold_ms.
    loose_jitter: bool = False


@dataclass
class TightnessReport:
    orig_onsets: List[Onset]
    driver_onsets: List[Onset]
    matched: List[OnsetMatch]
    missing: List[float]
    extra: List[float]
    params: Dict[str, Any] = field(default_factory=dict)
    # Median of every matched onset's delta_ms: a whole-render time shift
    # (different playback start point, driver startup pipeline, etc.), NOT
    # per-note looseness. Separating the two matters -- a render that is
    # uniformly 50 ms late is rhythmically perfect but would otherwise report
    # as ~100% "loose", which is a misleading verdict.
    median_offset_ms: float = 0.0
    # Median inter-onset interval of the ORIGINAL, in ms. The alignment
    # tolerance must stay well below this -- see safe_tolerance_ms.
    median_ioi_ms: float = 0.0


def load_wav_mono(path: Union[str, Path]) -> Tuple[np.ndarray, int]:
    """Load a WAV file as mono float32 in [-1, 1]. Generalized from
    bin/listen_compare.py's get_audio(), minus the render step."""
    with wave.open(str(path), 'rb') as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        sampwidth = w.getsampwidth()
        raw = w.readframes(w.getnframes())

    if sampwidth == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sampwidth} bytes ({path})")

    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def hz_to_mel(f):
    """Hz -> mel (O'Shaughnessy / HTK form). Closed-form, no dependency."""
    return 2595.0 * np.log10(1.0 + np.asarray(f, dtype=np.float64) / 700.0)


def mel_to_hz(m):
    """Inverse of hz_to_mel()."""
    return 700.0 * (10.0 ** (np.asarray(m, dtype=np.float64) / 2595.0) - 1.0)


# 'linear' is the default EVERYWHERE and must stay that way. detect_onsets()
# feeds band_energies() straight into the onset comparison that most of this
# project's published fidelity numbers rest on; changing the default would
# silently move every one of them with no corpus re-validation. 'mel' is opt-in
# per call site -- see extract_features(band_scale=...).
BAND_SCALES = ('linear', 'mel')


def band_edges(nb: int = 40, fmin: float = 30, fmax: float = 8000,
               scale: str = 'linear') -> np.ndarray:
    """The nb+1 band edges in Hz. SINGLE SOURCE OF TRUTH for band geometry.

    Both band_energies() and any consumer that needs the band CENTRES (e.g.
    sidm2.audio_listen.extract_features, which weights them to get a spectral
    centroid) must derive them from here. Those two used to compute
    `np.linspace(fmin, fmax, nb+1)` independently, which agreed only by
    coincidence -- with a scale parameter in play it would have become a real
    desync: energies binned one way, centre frequencies assigned another.

    'mel' spreads edges so bin width grows with frequency, matching the
    roughly-logarithmic resolution of hearing. Under 'linear' with the
    defaults, half the 40 bins sit above 4 kHz, a region SID material rarely
    occupies -- resolution spent where neither the ear nor the material is.
    """
    if scale not in BAND_SCALES:
        raise ValueError(f"unknown band scale {scale!r}: expected one of {BAND_SCALES}")
    if scale == 'mel':
        return mel_to_hz(np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), nb + 1))
    return np.linspace(fmin, fmax, nb + 1)


def band_centers(nb: int = 40, fmin: float = 30, fmax: float = 8000,
                 scale: str = 'linear') -> np.ndarray:
    """Midpoint of each band, in Hz. Derived from band_edges(), never re-derived."""
    edges = band_edges(nb, fmin, fmax, scale)
    return (edges[:-1] + edges[1:]) / 2


def undersampled_bands(sr: int, win_s: float, nb: int = 40, fmin: float = 30,
                        fmax: float = 8000, scale: str = 'linear') -> int:
    """How many bands are NARROWER than the FFT's own frequency resolution.

    Such a band can contain no FFT bin at all and then reads as exactly zero
    energy -- indistinguishable from real silence, and ruinous for flatness,
    which takes a geometric mean and so is dominated by its smallest entry.

    Only mel spacing can trigger this, because it deliberately narrows the low
    bands. MEASURED at sr=44100 with the default 40 ms window (25 Hz bins):
    nb=40 -> 0 undersampled (narrowest band 46.7 Hz), nb=64 -> 0 (28.8 Hz),
    nb=96 -> 11, nb=128 -> 29. So the mel default at nb=40 is safe with room to
    spare, and a caller raising nb (the spectrogram path uses 96) must either
    lengthen the window or stay on 'linear'.
    """
    win = max(2, int(round(win_s * sr)))
    fft_resolution = sr / win
    return int((np.diff(band_edges(nb, fmin, fmax, scale)) < fft_resolution).sum())


def band_energies(x: np.ndarray, sr: int, hop_s: float = 0.01, win_s: float = 0.04,
                   nb: int = 40, fmin: float = 30, fmax: float = 8000,
                   scale: str = 'linear') -> np.ndarray:
    """Frame-hopped generalization of listen_compare.py's logmel(): linear
    (not log) per-band energy per hop, shape (n_frames, nb).

    scale='mel' re-spaces the band edges (see band_edges); it does NOT change
    the default, which onset detection depends on.
    """
    hop = max(1, int(round(hop_s * sr)))
    win = max(2, int(round(win_s * sr)))
    n_frames = max(0, (len(x) - win) // hop + 1)
    if n_frames == 0:
        return np.zeros((0, nb))

    # Say so rather than returning zeros that look like silence. Not raised:
    # the result is still usable for anything that does not take a geometric
    # mean, and refusing outright would be a worse trade than a loud warning.
    n_under = undersampled_bands(sr, win_s, nb, fmin, fmax, scale)
    if n_under:
        logger.warning(
            "band_energies(scale=%r, nb=%d, win_s=%g) at sr=%d: %d band(s) are "
            "narrower than the %.1f Hz FFT resolution and will read as zero "
            "energy. Lengthen win_s or lower nb; flatness in particular is "
            "unusable in this configuration.",
            scale, nb, win_s, sr, n_under, sr / win)

    window = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    edges = band_edges(nb, fmin, fmax, scale)
    bin_idx = [np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0] for i in range(nb)]

    energies = np.zeros((n_frames, nb), dtype=np.float64)
    for i in range(n_frames):
        seg = x[i * hop: i * hop + win] * window
        mag = np.abs(np.fft.rfft(seg))
        for b, idx in enumerate(bin_idx):
            if idx.size:
                energies[i, b] = mag[idx].sum()
    return energies


def spectral_flux(bands: np.ndarray) -> np.ndarray:
    """Half-wave-rectified frame-to-frame band-energy delta, summed per frame."""
    if len(bands) == 0:
        return np.zeros(0)
    diff = np.diff(bands, axis=0, prepend=bands[:1])
    return np.clip(diff, 0, None).sum(axis=1)


def pick_onsets(flux: np.ndarray, hop_s: float, median_window_s: float = 0.5,
                 delta: float = 1.5, min_distance_s: float = 0.05) -> List[float]:
    """Local median+MAD adaptive-threshold peak picking (Dixon-style), with
    greedy min-distance suppression. Returns onset times in seconds.

    Two separate windows: median_window_s is the (larger) background-statistics
    window for the threshold; local-max detection uses a (smaller) window sized
    off min_distance_s -- using the same window for both would make a frame's
    "local max" status depend on unrelated onsets several onsets away.
    """
    n = len(flux)
    if n == 0:
        return []

    stat_win = max(1, int(round(median_window_s / hop_s)))
    min_dist = max(1, int(round(min_distance_s / hop_s)))
    peak_win = max(1, min_dist // 2)

    onsets = []
    last_idx = -min_dist - 1
    for i in range(n):
        stat_lo = max(0, i - stat_win)
        stat_hi = min(n, i + stat_win + 1)
        stat_local = flux[stat_lo:stat_hi]
        med = np.median(stat_local)
        mad = np.median(np.abs(stat_local - med)) + 1e-9
        threshold = med + delta * mad

        if flux[i] <= 0 or flux[i] < threshold:
            continue

        peak_lo = max(0, i - peak_win)
        peak_hi = min(n, i + peak_win + 1)
        if flux[i] != flux[peak_lo:peak_hi].max():
            continue

        if (i - last_idx) < min_dist:
            continue

        onsets.append(i * hop_s)
        last_idx = i
    return onsets


def detect_onsets(x: np.ndarray, sr: int, hop_ms: float = 10, window_ms: float = 40,
                   bands: int = 40, freq_lo: float = 30, freq_hi: float = 8000,
                   **peak_kwargs) -> List[float]:
    """Chain band_energies -> spectral_flux -> pick_onsets. Wider band range
    than listen_compare's 200-5000Hz (tuned for melodic pitch tracking);
    percussive transients are broadband."""
    hop_s = hop_ms / 1000.0
    win_s = window_ms / 1000.0
    bands_arr = band_energies(x, sr, hop_s=hop_s, win_s=win_s, nb=bands, fmin=freq_lo, fmax=freq_hi)
    flux = spectral_flux(bands_arr)
    return pick_onsets(flux, hop_s, **peak_kwargs)


def align_onsets(orig: List[float], driver: List[float],
                  tolerance_s: float) -> Tuple[List[Tuple[float, float]], List[float], List[float]]:
    """Greedy nearest-neighbor alignment in orig time order. NOT globally
    optimal for dense onset runs -- acceptable limitation for v1."""
    orig = sorted(orig)
    driver = sorted(driver)
    used = [False] * len(driver)
    pairs = []
    missing = []

    j_start = 0
    for ot in orig:
        while j_start < len(driver) and driver[j_start] < ot - tolerance_s:
            j_start += 1

        best_j, best_d = -1, None
        j = j_start
        while j < len(driver) and driver[j] <= ot + tolerance_s:
            if not used[j]:
                d = abs(driver[j] - ot)
                if best_d is None or d < best_d:
                    best_d, best_j = d, j
            j += 1

        if best_j >= 0:
            used[best_j] = True
            pairs.append((ot, driver[best_j]))
        else:
            missing.append(ot)

    extra = [driver[i] for i in range(len(driver)) if not used[i]]
    return pairs, missing, extra


def attack_rise_time_ms(x: np.ndarray, sr: int, onset_t: float, window_s: float = 0.08) -> float:
    """RMS envelope 10%->90%-of-local-peak rise time, in ms."""
    start = int(round(onset_t * sr))
    end = min(len(x), start + int(round(window_s * sr)))
    if end - start < 4:
        return 0.0

    seg = x[start:end]
    hop = max(1, int(round(0.001 * sr)))
    win = max(2, int(round(0.003 * sr)))
    n_frames = max(1, (len(seg) - win) // hop + 1)

    env = np.zeros(n_frames)
    for i in range(n_frames):
        chunk = seg[i * hop: i * hop + win]
        if chunk.size:
            env[i] = np.sqrt(np.mean(chunk.astype(np.float64) ** 2))

    peak = env.max()
    if peak <= 0:
        return 0.0

    lo_hits = np.where(env >= 0.1 * peak)[0]
    if lo_hits.size == 0:
        return 0.0
    lo_idx = lo_hits[0]

    hi_hits = np.where(env >= 0.9 * peak)[0]
    hi_hits = hi_hits[hi_hits >= lo_idx]
    if hi_hits.size == 0:
        return 0.0
    hi_idx = hi_hits[0]

    return float((hi_idx - lo_idx) * hop / sr * 1000.0)


def _logmel(seg: np.ndarray, sr: int, nb: int = 24, fmin: float = 200, fmax: float = 5000,
             scale: str = 'linear') -> np.ndarray:
    """NB the name is historical and inaccurate under the default: this is log
    energy in LINEARLY spaced bands unless scale='mel' is passed. Renaming it
    would churn call sites for no measurement gain; documenting it is enough."""
    if len(seg) == 0:
        return np.zeros(nb)
    window = np.hanning(len(seg)) if len(seg) > 1 else np.ones(len(seg))
    mag = np.abs(np.fft.rfft(seg * window))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / sr)
    edges = band_edges(nb, fmin, fmax, scale)
    energies = np.array([
        mag[(freqs >= edges[i]) & (freqs < edges[i + 1])].sum()
        for i in range(nb)
    ])
    total = energies.sum() + 1e-9
    return np.log(energies / total + 1e-6)


def logmel_distance(seg_a: np.ndarray, seg_b: np.ndarray, sr: int, nb: int = 24,
                     fmin: float = 200, fmax: float = 5000,
                     scale: str = 'linear') -> float:
    """Generalized listen_compare.py::logmel() distance between two segments.

    Default stays 'linear': this feeds OnsetMatch.spectral_dist, part of the
    onset-comparison output this project's fidelity numbers rest on.
    """
    la = _logmel(seg_a, sr, nb, fmin, fmax, scale)
    lb = _logmel(seg_b, sr, nb, fmin, fmax, scale)
    return float(np.abs(la - lb).mean())


def offset_and_jitter(matched: List[OnsetMatch]) -> Tuple[float, List[float]]:
    """(median_offset_ms, per-match jitter_ms) derived from delta_ms alone.

    Deliberately recomputed from delta_ms rather than read back off
    OnsetMatch.jitter_ms so that a TightnessReport assembled by hand (tests,
    or a caller reconstructing one from JSON) reports the same numbers as one
    produced by analyze_tightness, instead of silently falling back to the
    dataclass's 0.0 defaults.

    Median, not mean: a minority of badly-matched outliers (e.g. onsets
    pinned at the alignment tolerance ceiling) must not drag the offset.
    """
    if not matched:
        return 0.0, []
    offset = float(np.median([m.delta_ms for m in matched]))
    return offset, [m.delta_ms - offset for m in matched]


def median_ioi_ms(onset_times: List[float]) -> float:
    """Median inter-onset interval, in ms. 0.0 if fewer than 2 onsets."""
    if len(onset_times) < 2:
        return 0.0
    return float(np.median(np.diff(sorted(onset_times)))) * 1000.0


# An alignment window must stay well inside the gap between consecutive
# notes. At half the IOI, the nearest wrong partner is still outside the
# window; at or above the IOI, greedy matching can pair a note with its
# neighbour instead of itself -- and because such a pairing preserves time
# order, count_alignment_crossings() cannot detect it.
#
# This is not hypothetical. Glyptodont (IOI ~90ms) measured against its
# Blackbird native build reported a "+50ms (+2.5 PAL frame) systematic
# offset" at the original 150ms default. Sweeping the tolerance down
# collapsed that offset monotonically to EXACTLY 0.0 at <=70ms, with median
# |jitter| falling 50ms -> 10ms (the detector's own hop resolution). The
# offset was never real; it was neighbour-pairing.
TOLERANCE_IOI_FRACTION = 0.5
TOLERANCE_MIN_MS = 20.0
TOLERANCE_MAX_MS = 150.0


def safe_tolerance_ms(onset_times: List[float]) -> float:
    """Alignment tolerance derived from the material's own note density.

    Clamped to [TOLERANCE_MIN_MS, TOLERANCE_MAX_MS]: the floor keeps the
    window above the onset detector's own hop resolution (~10ms) so real
    matches are not rejected as noise; the ceiling keeps sparse material
    from getting an absurdly wide window.
    """
    ioi = median_ioi_ms(onset_times)
    if ioi <= 0:
        return TOLERANCE_MAX_MS
    return float(np.clip(ioi * TOLERANCE_IOI_FRACTION,
                         TOLERANCE_MIN_MS, TOLERANCE_MAX_MS))


def count_alignment_crossings(matched: List[OnsetMatch]) -> int:
    """Number of matched pairs whose driver onset goes BACKWARDS in time
    relative to the previous pair (ordered by orig_t).

    Music does not reorder itself: if onset A precedes onset B in the
    original, A's true partner precedes B's in the driver. So a decrease in
    driver_t across consecutive pairs cannot be real -- it means greedy
    nearest-neighbour alignment paired at least one onset with the wrong
    neighbour, typically around a missing or extra onset. Drawn as connector
    lines these pairs literally cross, which is why the timeline view makes
    the problem obvious at a glance.

    A nonzero count means jitter statistics are contaminated by pairing
    errors and should not be read as timing looseness.
    """
    if len(matched) < 2:
        return 0
    ordered = sorted(matched, key=lambda m: m.orig_t)
    return sum(1 for a, b in zip(ordered, ordered[1:]) if b.driver_t < a.driver_t)


def analyze_tightness(orig: np.ndarray, driver: np.ndarray, sr: int,
                       onset_tolerance_ms: Optional[float] = None,
                       loose_threshold_ms: float = 40,
                       **detector_kwargs) -> TightnessReport:
    """Pure top-level entry point: two mono float arrays at the same sample
    rate in, a TightnessReport out.

    onset_tolerance_ms=None (the default) derives the window from the
    original's own median inter-onset interval via safe_tolerance_ms(). A
    fixed default cannot be correct for all material: a window wider than
    the IOI lets greedy matching pair notes with their neighbours, which
    manufactures a fake systematic offset (see safe_tolerance_ms).
    """
    orig_times = detect_onsets(orig, sr, **detector_kwargs)
    driver_times = detect_onsets(driver, sr, **detector_kwargs)

    ioi_ms = median_ioi_ms(orig_times)
    if onset_tolerance_ms is None:
        onset_tolerance_ms = safe_tolerance_ms(orig_times)
        tolerance_source = 'auto (from median IOI)'
    else:
        tolerance_source = 'explicit'

    tolerance_s = onset_tolerance_ms / 1000.0
    pairs, missing, extra = align_onsets(orig_times, driver_times, tolerance_s)

    rise_window_s = 0.08
    matched = []
    for ot, dt in pairs:
        delta_ms = (dt - ot) * 1000.0
        orig_rise = attack_rise_time_ms(orig, sr, ot, window_s=rise_window_s)
        driver_rise = attack_rise_time_ms(driver, sr, dt, window_s=rise_window_s)

        oa = int(round(ot * sr))
        ob = int(round(dt * sr))
        win = int(round(rise_window_s * sr))
        seg_a = orig[oa:oa + win]
        seg_b = driver[ob:ob + win]
        spec_dist = logmel_distance(seg_a, seg_b, sr) if seg_a.size and seg_b.size else float('nan')

        matched.append(OnsetMatch(
            orig_t=ot,
            driver_t=dt,
            delta_ms=delta_ms,
            rise_delta_ms=driver_rise - orig_rise,
            spectral_dist=spec_dist,
            loose=abs(delta_ms) > loose_threshold_ms,
        ))

    # Split the raw deltas into a whole-render OFFSET (the median) and
    # per-note JITTER (the spread around it). A uniform shift and genuine
    # looseness are different defects with different causes, and reporting
    # only the raw delta conflates them -- a perfectly tight render that
    # merely starts 50 ms late would otherwise read as almost entirely
    # "loose". Median, not mean, so a minority of badly-matched outliers
    # can't drag the offset around.
    median_offset_ms, jitters = offset_and_jitter(matched)
    for m, j in zip(matched, jitters):
        m.jitter_ms = j
        m.loose_jitter = abs(j) > loose_threshold_ms

    params = dict(onset_tolerance_ms=onset_tolerance_ms, loose_threshold_ms=loose_threshold_ms,
                  tolerance_source=tolerance_source, median_ioi_ms=round(ioi_ms, 1),
                  **detector_kwargs)
    return TightnessReport(
        orig_onsets=[Onset(t=t) for t in orig_times],
        driver_onsets=[Onset(t=t) for t in driver_times],
        matched=matched,
        missing=missing,
        extra=extra,
        params=params,
        median_offset_ms=median_offset_ms,
        median_ioi_ms=ioi_ms,
    )


def analyze_tightness_files(orig_wav_path: Union[str, Path], driver_wav_path: Union[str, Path],
                             **kwargs) -> TightnessReport:
    """File-based wrapper for the CLI. Raises on sample-rate mismatch."""
    orig, sr_a = load_wav_mono(orig_wav_path)
    driver, sr_b = load_wav_mono(driver_wav_path)
    if sr_a != sr_b:
        raise ValueError(
            f"Sample rate mismatch: {orig_wav_path} is {sr_a} Hz, "
            f"{driver_wav_path} is {sr_b} Hz"
        )
    return analyze_tightness(orig, driver, sr_a, **kwargs)


# ---------------------------------------------------------------------------
# Voice isolation: the digi-bleed guard
# ---------------------------------------------------------------------------
#
# sidplayfp's -u<n> is the only voice-mute any renderer here has, so per-voice
# audio comparison is built on it. It is NOT a clean slice. Muting all three
# voices does not produce silence on every tune, and where it does not, all
# three "isolated" renders carry the same shared signal -- they then look
# reassuringly similar to each other while telling you nothing about the voice
# you asked about. That is the exact failure this guard exists to refuse.
#
# MEASURED, 2026-08-08, 12 tunes, 20 s renders (residual RMS / mix RMS):
#   Commando .024  Crazy_Comets .025  Athena .028  Stinsen .077
#   A_Computer_in_My_Backpack .091  A_Chipful_of_Love .102  Hawkeye .151
#   Cybernoid_II .190  Sanxion .353  Arkanoid .494  I_Ball .587
#   Arkanoid_alternative_drums .619
# It is a gradient, not two classes, so the guard has a warn band as well as a
# refusal.
#
# The MECHANISM is mixed, and the obvious guess was wrong. `$D418` master-volume
# digi was the standing hypothesis; it is FALSIFIED for the worst offenders --
# Sanxion and I_Ball hold $D418's volume nibble at a constant 15 for all 1000
# frames of a 20 s siddump, exactly like clean Commando. What the residual
# actually is varies by tune:
#   - Galway's Arkanoid: a SAMPLE channel libsidplayfp models separately and
#     mutes under its own flag -- `-u1 -u2 -u3 -g1` drops it .114 -> .004.
#   - Hubbard's Sanxion: filter-path, and emulation-dependent -- `-nf` drops it
#     .032 -> .004, `--resid` to .010, while `-g1` changes nothing.
#   - reSIDfp also has a small nonzero floor with everything muted (Commando
#     .0029, where `--resid` gives exactly 0).
# Hence the guard thresholds are FRACTIONS of the isolated render, never an
# absolute RMS: there is no single mechanism to test for, and the only thing
# that matters to the caller is whether the voice still dominates its own slice.

# Warn where the shared part stops being negligible (the clean tunes all sit
# under 0.5%, so 5% is an order of magnitude clear of them). REFUSE at the one
# cut point that means something on its own terms rather than being picked off a
# histogram: at 50% the residual carries MORE energy than the voice does, so the
# slice is no longer mostly the voice you asked for. The measured corpus happens
# to leave that line uncontested -- worst non-digi slice 38.4% (Cybernoid_II
# voice 3 over 12 s), lowest digi slice 53.6% (I_Ball voice 2) -- but the
# threshold is not derived FROM that gap, because the gap moves with the
# measurement window (Cybernoid_II's worst slice reads 23.8% at 20 s and 34.5%
# at 12 s: h2g's "window size is a measurement artifact", live in this metric).
BLEED_WARN_FRAC = 0.05
BLEED_REFUSE_FRAC = 0.50


def rms(x: np.ndarray) -> float:
    """Root-mean-square of a sample array. 0.0 for an empty array."""
    if x is None or len(x) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)))


def normalized_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Zero-lag Pearson correlation of two same-render-length signals.

    Both sides come from the same renderer with the same duration, so they are
    already sample-aligned; no lag search is wanted here (a lag search would
    hide exactly the shared-signal case this is used to detect). NaN when
    either side is constant -- an undefined correlation, not a zero one.
    """
    n = min(len(a), len(b))
    if n == 0:
        return float('nan')
    x = np.asarray(a[:n], dtype=np.float64)
    y = np.asarray(b[:n], dtype=np.float64)
    x = x - x.mean()
    y = y - y.mean()
    denom = np.sqrt(float((x * x).sum()) * float((y * y).sum()))
    return float((x * y).sum() / denom) if denom > 0 else float('nan')


@dataclass
class VoiceBleed:
    voice: int
    iso_rms: float
    # Energy fraction of this voice's "isolated" render that is actually the
    # shared residual, i.e. (residual_rms / iso_rms)**2 clipped to 1.0.
    # **None when there is no signal at all on either side** -- an empty
    # comparison, which must not read as 0% contamination (score_pct's rule,
    # applied to audio: see sidm2/fidelity_common.score_pct).
    shared_frac: Optional[float]


@dataclass
class BleedReport:
    mix_rms: float
    muted_rms: float
    voices: List[VoiceBleed]
    # {"1-2": r, "1-3": r, "2-3": r} -- corroboration, not the decision.
    # Near-zero on a clean tune (Commando .12/.03/.07), high when the three
    # slices share a signal (I_Ball .56/.50/.42, Arkanoid .65/.48/.50).
    # NOT used as the threshold: two voices playing in unison would correlate
    # legitimately, whereas the muted render isolates the shared part directly.
    pair_corr: Dict[str, float] = field(default_factory=dict)
    verdict: str = 'clean'          # 'clean' | 'warn' | 'refuse' | 'no-signal'
    max_shared_frac: Optional[float] = None

    @property
    def blocking(self) -> bool:
        """Should per-voice audio results be withheld?"""
        return self.verdict in ('refuse', 'no-signal')


def analyze_voice_bleed(mix: np.ndarray, muted: np.ndarray,
                         isolated: Dict[int, np.ndarray]) -> BleedReport:
    """Decide whether per-voice audio isolation is meaningful for this render.

    `muted` is the all-voices-muted render (`-u1 -u2 -u3`); `isolated[v]` is the
    render with the OTHER two voices muted. See the module comment above for the
    measurements the thresholds come from and for why the mechanism is not
    assumed.
    """
    muted_rms = rms(muted)
    voices = []
    for v in sorted(isolated):
        iso_rms = rms(isolated[v])
        if iso_rms <= 0.0:
            # A silent slice is either a silent voice in a silent render (no
            # evidence either way) or a silent voice drowning in residual
            # (total contamination). Distinguished by the residual itself.
            frac = None if muted_rms <= 0.0 else 1.0
        else:
            frac = min(1.0, (muted_rms / iso_rms) ** 2)
        voices.append(VoiceBleed(voice=v, iso_rms=iso_rms, shared_frac=frac))

    pair_corr = {}
    keys = sorted(isolated)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            pair_corr[f"{keys[i]}-{keys[j]}"] = normalized_correlation(
                isolated[keys[i]], isolated[keys[j]])

    fracs = [vb.shared_frac for vb in voices if vb.shared_frac is not None]
    if not fracs:
        verdict, worst = 'no-signal', None
    else:
        worst = max(fracs)
        if worst >= BLEED_REFUSE_FRAC:
            verdict = 'refuse'
        elif worst >= BLEED_WARN_FRAC:
            verdict = 'warn'
        else:
            verdict = 'clean'

    return BleedReport(mix_rms=rms(mix), muted_rms=muted_rms, voices=voices,
                       pair_corr=pair_corr, verdict=verdict, max_shared_frac=worst)
