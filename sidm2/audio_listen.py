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
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np

from sidm2.audio_tightness import band_energies

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


_SILENT_FEATURES_DB = -120.0


def _frame_rms(x: np.ndarray, hop: int, win: int) -> np.ndarray:
    n = max(0, (len(x) - win) // hop + 1)
    out = np.zeros(n)
    for i in range(n):
        seg = x[i * hop: i * hop + win]
        if seg.size:
            out[i] = np.sqrt(np.mean(seg.astype(np.float64) ** 2))
    return out


def extract_features(x: np.ndarray, sr: int, hop_ms: float = 10, win_ms: float = 40,
                      nb: int = 40, fmin: float = 30, fmax: float = 8000) -> AudioFeatures:
    """Whole-file feature summary. NOT onset-aligned -- a global average, so it
    complements audio_tightness's per-note numbers rather than replacing them.
    """
    hop = max(1, int(round(hop_ms / 1000 * sr)))
    win = max(2, int(round(win_ms / 1000 * sr)))

    rms = _frame_rms(x, hop, win)
    rms_db = 20 * np.log10(np.clip(rms, 1e-9, None)) if rms.size else np.array([])

    bands = band_energies(x, sr, hop_s=hop_ms / 1000, win_s=win_ms / 1000,
                           nb=nb, fmin=fmin, fmax=fmax)
    if bands.shape[0] == 0:
        return AudioFeatures(
            duration_s=len(x) / sr if sr else 0.0,
            rms_db_mean=float(rms_db.mean()) if rms_db.size else _SILENT_FEATURES_DB,
            rms_db_max=float(rms_db.max()) if rms_db.size else _SILENT_FEATURES_DB,
            silence_frac=1.0,
            centroid_hz_mean=0.0, centroid_hz_std=0.0,
            rolloff85_hz_mean=0.0, zcr_mean=0.0, flatness_mean=0.0,
        )

    edges = np.linspace(fmin, fmax, nb + 1)
    centers = (edges[:-1] + edges[1:]) / 2

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
    )


def format_feature_report(orig: AudioFeatures, driver: AudioFeatures,
                           orig_label: str = 'original', driver_label: str = 'driver') -> str:
    """Text summary for Claude: side-by-side whole-file features plus deltas.

    Deliberately labeled and hedged rather than scored pass/fail -- unlike the
    onset report, there is no established threshold for "different enough to
    matter" on these features, so this is context for a human/Claude read, not
    a verdict.
    """
    lines = []
    lines.append("AUDIO FEATURE SUMMARY (whole-file average, not onset-aligned)")
    lines.append("=" * 70)
    lines.append(f"{'':22s} {orig_label[:20]:>20s} {driver_label[:20]:>20s} {'delta':>10s}")

    def row(label, a, b, unit='', fmt='{:.1f}'):
        d = b - a
        lines.append(f"{label:22s} {fmt.format(a) + unit:>20s} {fmt.format(b) + unit:>20s} "
                      f"{('+' if d >= 0 else '') + fmt.format(d) + unit:>10s}")

    row('duration', orig.duration_s, driver.duration_s, 's')
    row('RMS level (mean)', orig.rms_db_mean, driver.rms_db_mean, ' dBFS')
    row('RMS level (peak)', orig.rms_db_max, driver.rms_db_max, ' dBFS')
    row('silence fraction', orig.silence_frac * 100, driver.silence_frac * 100, '%')
    row('spectral centroid', orig.centroid_hz_mean, driver.centroid_hz_mean, ' Hz')
    row('centroid spread', orig.centroid_hz_std, driver.centroid_hz_std, ' Hz')
    row('rolloff (85%)', orig.rolloff85_hz_mean, driver.rolloff85_hz_mean, ' Hz')
    row('zero-crossing rate', orig.zcr_mean * 100, driver.zcr_mean * 100, '%')
    row('spectral flatness', orig.flatness_mean, driver.flatness_mean, '', fmt='{:.3f}')

    lines.append("")
    lines.append("  centroid/rolloff higher on one side = that render is brighter (more")
    lines.append("  high-frequency energy) -- often a filter cutoff or waveform difference.")
    lines.append("  flatness closer to 1.0 = more noise-like (e.g. an unfiltered noise")
    lines.append("  waveform or digi channel); closer to 0.0 = more tonal.")
    lines.append("  These are global averages and can hide a localized problem -- if they")
    lines.append("  don't explain a discrepancy the onset report flagged, render a")
    lines.append("  spectrogram (--spectrogram) and inspect it directly.")
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
