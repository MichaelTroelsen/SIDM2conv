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
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np


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


def band_energies(x: np.ndarray, sr: int, hop_s: float = 0.01, win_s: float = 0.04,
                   nb: int = 40, fmin: float = 30, fmax: float = 8000) -> np.ndarray:
    """Frame-hopped generalization of listen_compare.py's logmel(): linear
    (not log) per-band energy per hop, shape (n_frames, nb)."""
    hop = max(1, int(round(hop_s * sr)))
    win = max(2, int(round(win_s * sr)))
    n_frames = max(0, (len(x) - win) // hop + 1)
    if n_frames == 0:
        return np.zeros((0, nb))

    window = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    edges = np.linspace(fmin, fmax, nb + 1)
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


def _logmel(seg: np.ndarray, sr: int, nb: int = 24, fmin: float = 200, fmax: float = 5000) -> np.ndarray:
    if len(seg) == 0:
        return np.zeros(nb)
    window = np.hanning(len(seg)) if len(seg) > 1 else np.ones(len(seg))
    mag = np.abs(np.fft.rfft(seg * window))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / sr)
    edges = np.linspace(fmin, fmax, nb + 1)
    energies = np.array([
        mag[(freqs >= edges[i]) & (freqs < edges[i + 1])].sum()
        for i in range(nb)
    ])
    total = energies.sum() + 1e-9
    return np.log(energies / total + 1e-6)


def logmel_distance(seg_a: np.ndarray, seg_b: np.ndarray, sr: int, nb: int = 24,
                     fmin: float = 200, fmax: float = 5000) -> float:
    """Generalized listen_compare.py::logmel() distance between two segments."""
    la = _logmel(seg_a, sr, nb, fmin, fmax)
    lb = _logmel(seg_b, sr, nb, fmin, fmax)
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
                       onset_tolerance_ms: float = 150, loose_threshold_ms: float = 40,
                       **detector_kwargs) -> TightnessReport:
    """Pure top-level entry point: two mono float arrays at the same sample
    rate in, a TightnessReport out."""
    orig_times = detect_onsets(orig, sr, **detector_kwargs)
    driver_times = detect_onsets(driver, sr, **detector_kwargs)

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
                  **detector_kwargs)
    return TightnessReport(
        orig_onsets=[Onset(t=t) for t in orig_times],
        driver_onsets=[Onset(t=t) for t in driver_times],
        matched=matched,
        missing=missing,
        extra=extra,
        params=params,
        median_offset_ms=median_offset_ms,
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
