#!/usr/bin/env python3
"""Text formatter for sidm2.audio_tightness's TightnessReport.

Pure string formatting -- no I/O. Fixed structure (header, SUMMARY, WORST
OFFENDERS, MISSING/EXTRA), designed to be read directly by Claude as well
as a human.
"""

from typing import Any, Dict

import numpy as np

from sidm2.audio_tightness import TightnessReport


def _stat_line(label: str, values, signed: bool = True) -> str:
    if not values:
        return f"{label}: n/a (no data)"
    arr = np.asarray(values, dtype=float)
    fmt = "{:+.1f}" if signed else "{:.1f}"
    return f"{label}: mean {fmt.format(np.mean(arr))}  median {fmt.format(np.median(arr))}"


def format_text_report(report: TightnessReport, meta: Dict[str, Any] = None) -> str:
    """Render a TightnessReport as a fixed-width text report."""
    meta = meta or {}
    lines = []

    lines.append("=" * 80)
    lines.append("AUDIO TIGHTNESS REPORT")
    lines.append("=" * 80)
    lines.append(f"Original: {meta.get('orig_path', '?')}")
    lines.append(f"Driver:   {meta.get('driver_path', '?')}")
    if meta.get('voice'):
        lines.append(f"Voice isolation: voice {meta['voice']} "
                      f"(muted: {meta.get('mute_voices', '?')})")
    if meta.get('duration') is not None:
        lines.append(f"Render duration: {meta['duration']}s")
    if meta.get('renderer'):
        lines.append(f"Renderer: {meta['renderer']}")

    lines.append("")
    lines.append("Detector/alignment params:")
    for key in sorted(report.params.keys()):
        lines.append(f"  {key}: {report.params[key]}")

    n_orig = len(report.orig_onsets)
    n_driver = len(report.driver_onsets)
    n_matched = len(report.matched)
    n_missing = len(report.missing)
    n_extra = len(report.extra)

    match_pct = 100.0 * n_matched / n_orig if n_orig else float('nan')
    missing_pct = 100.0 * n_missing / n_orig if n_orig else float('nan')
    extra_pct = 100.0 * n_extra / n_driver if n_driver else float('nan')

    lines.append("")
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Orig onsets:    {n_orig}")
    lines.append(f"Driver onsets:  {n_driver}")
    lines.append(f"Matched:        {n_matched} ({match_pct:.1f}% of orig)")
    lines.append(f"Missing:        {n_missing} ({missing_pct:.1f}% of orig)")
    lines.append(f"Extra:          {n_extra} ({extra_pct:.1f}% of driver)")

    if report.matched:
        deltas = [m.delta_ms for m in report.matched]
        abs_deltas = [abs(d) for d in deltas]
        loose = [m for m in report.matched if m.loose]
        rises = [m.rise_delta_ms for m in report.matched]
        specs = [m.spectral_dist for m in report.matched if m.spectral_dist == m.spectral_dist]

        lines.append("")
        lines.append(_stat_line("Onset delta (ms)", deltas))
        lines.append(f"  max |delta_ms|: {max(abs_deltas):.1f}")
        lines.append(f"Loose onsets:   {len(loose)} / {n_matched} "
                      f"({100.0 * len(loose) / n_matched:.1f}%)")
        lines.append(_stat_line("Attack rise delta (ms)", rises))
        lines.append(_stat_line("Spectral distance", specs, signed=False))
    else:
        lines.append("")
        lines.append("No matched onsets -- nothing to summarize.")

    lines.append("")
    lines.append("-" * 80)
    lines.append("WORST OFFENDERS (top 20 by |delta_ms|)")
    lines.append("-" * 80)
    worst = sorted(report.matched, key=lambda m: abs(m.delta_ms), reverse=True)[:20]
    if worst:
        lines.append(f"{'orig_t':>8}  {'driver_t':>8}  {'delta_ms':>9}  "
                      f"{'rise_dms':>9}  {'spec_dist':>9}  loose")
        for m in worst:
            spec = f"{m.spectral_dist:.3f}" if m.spectral_dist == m.spectral_dist else "n/a"
            lines.append(
                f"{m.orig_t:8.3f}  {m.driver_t:8.3f}  {m.delta_ms:+9.1f}  "
                f"{m.rise_delta_ms:+9.1f}  {spec:>9}  {'YES' if m.loose else ''}"
            )
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("-" * 80)
    lines.append(f"MISSING ONSETS (in original, not found in driver): {n_missing}")
    lines.append("-" * 80)
    lines.append(", ".join(f"{t:.3f}" for t in report.missing) if report.missing else "(none)")

    lines.append("")
    lines.append("-" * 80)
    lines.append(f"EXTRA ONSETS (in driver, not in original): {n_extra}")
    lines.append("-" * 80)
    lines.append(", ".join(f"{t:.3f}" for t in report.extra) if report.extra else "(none)")

    lines.append("=" * 80)
    return "\n".join(lines)
