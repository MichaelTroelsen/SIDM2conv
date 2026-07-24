#!/usr/bin/env python3
"""Text formatter for sidm2.audio_tightness's TightnessReport.

Pure string formatting -- no I/O. Fixed structure (header, SUMMARY, WORST
OFFENDERS, MISSING/EXTRA), designed to be read directly by Claude as well
as a human.
"""

from typing import Any, Dict

import numpy as np

from sidm2.audio_tightness import (
    TightnessReport,
    count_alignment_crossings,
    offset_and_jitter,
)


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

        thr = report.params.get('loose_threshold_ms', 40)
        # Recomputed, not read off the report -- see offset_and_jitter's docstring.
        offset, jitters = offset_and_jitter(report.matched)
        abs_jitters = [abs(j) for j in jitters]
        loose_jitter = [j for j in jitters if abs(j) > thr]
        # A PAL frame is 20 ms -- the engine's own timing quantum, so
        # expressing the offset in frames is what makes it actionable
        # (e.g. "3 frames" points straight at a startup-pipeline difference).
        offset_frames = offset / 20.0

        lines.append("")
        lines.append("RAW onset delta -- includes any whole-render time shift:")
        lines.append("  " + _stat_line("delta (ms)", deltas))
        lines.append(f"  max |delta_ms|: {max(abs_deltas):.1f}")
        lines.append(f"  Loose (|delta| > {thr:g}ms): {len(loose)} / {n_matched} "
                      f"({100.0 * len(loose) / n_matched:.1f}%)")

        lines.append("")
        lines.append(f"SYSTEMATIC OFFSET (median delta): {offset:+.1f} ms "
                      f"({offset_frames:+.2f} PAL frames)")
        lines.append("  A uniform shift of the whole render (playback start point,")
        lines.append("  driver startup pipeline, ...) -- NOT per-note looseness.")

        lines.append("")
        lines.append("JITTER -- offset removed; THIS is the tightness measure:")
        lines.append("  " + _stat_line("jitter (ms)", jitters))
        lines.append(f"  max |jitter_ms|: {max(abs_jitters):.1f}")
        lines.append(f"  Loose (|jitter| > {thr:g}ms): {len(loose_jitter)} / {n_matched} "
                      f"({100.0 * len(loose_jitter) / n_matched:.1f}%)")

        lines.append("")
        lines.append(_stat_line("Attack rise delta (ms)", rises))
        lines.append(_stat_line("Spectral distance", specs, signed=False))

        lines.append("")
        lines.append("HOW TO READ THIS:")
        lines.append("  large offset + small jitter -> render is shifted but rhythmically tight")
        lines.append("  small offset + large jitter -> genuinely loose timing (the 'not tight' case)")
        lines.append("  both large                  -> shifted AND loose; fix the offset first,")
        lines.append("                                  it can mis-pair onsets and inflate jitter")
        # The single most important sanity check in this report. A tolerance
        # at or above the inter-onset interval lets greedy matching pair a
        # note with its NEIGHBOUR; that pairing preserves time order, so the
        # crossed-pair check below cannot see it, and it manufactures a fake
        # systematic offset out of nothing.
        _ioi = report.median_ioi_ms or report.params.get('median_ioi_ms', 0.0)
        _tol_now = report.params.get('onset_tolerance_ms', 0.0)
        if _ioi > 0:
            lines.append("")
            lines.append(f"Median inter-onset interval (original): {_ioi:.1f} ms")
            lines.append(f"Alignment tolerance: {_tol_now:.1f} ms "
                          f"({report.params.get('tolerance_source', 'explicit')})")
            if _tol_now >= _ioi:
                lines.append("  *** TOLERANCE EXCEEDS THE NOTE SPACING ***")
                lines.append("  Onsets can be paired with their NEIGHBOURS, which fabricates")
                lines.append("  a systematic offset and inflates jitter. Every timing number")
                lines.append(f"  below is unreliable. Re-run with --onset-tolerance-ms "
                              f"{_ioi * 0.5:.0f} or less.")
            elif _tol_now > _ioi * 0.5:
                lines.append(f"  NOTE: tolerance is above half the note spacing "
                              f"({_ioi * 0.5:.0f} ms); neighbour-pairing is possible.")

        n_cross = count_alignment_crossings(report.matched)
        if n_cross:
            lines.append("")
            lines.append(f"  WARNING: {n_cross} matched pair(s) run BACKWARDS in time "
                          f"relative to the previous pair.")
            lines.append("  Music cannot reorder itself, so these are greedy-alignment")
            lines.append("  mispairings (usually around a missing/extra onset). Jitter is")
            lines.append("  contaminated by them -- treat the numbers above as an upper")
            lines.append("  bound on looseness, and check the HTML timeline's crossed")
            lines.append("  connector lines to see where.")

        _tol = report.params.get('onset_tolerance_ms', 150)
        n_pinned = sum(1 for d in abs_deltas if abs(d - _tol) < 1e-6)
        if n_pinned:
            # Deltas sitting exactly on the tolerance ceiling are suspicious:
            # greedy alignment may have paired an onset with the wrong
            # neighbour rather than reporting it missing.
            lines.append("")
            lines.append(f"  WARNING: {n_pinned} matched onset(s) sit exactly at the "
                          f"{_tol:g}ms tolerance ceiling --")
            lines.append("  those pairings may be greedy-alignment artifacts rather than real")
            lines.append("  matches. Re-run with a smaller --onset-tolerance-ms to check.")
    else:
        lines.append("")
        lines.append("No matched onsets -- nothing to summarize.")

    lines.append("")
    lines.append("-" * 80)
    lines.append("WORST OFFENDERS (top 20 by |jitter_ms|, i.e. offset removed)")
    lines.append("-" * 80)
    # Ranked by jitter, not raw delta: with a large systematic offset every
    # row would otherwise look equally bad and the genuinely mistimed notes
    # would be indistinguishable from the uniformly-shifted ones.
    _off, _jit = offset_and_jitter(report.matched)
    _thr = report.params.get('loose_threshold_ms', 40)
    worst = sorted(zip(report.matched, _jit), key=lambda p: abs(p[1]), reverse=True)[:20]
    if worst:
        lines.append(f"{'orig_t':>8}  {'driver_t':>8}  {'delta_ms':>9}  {'jitter_ms':>9}  "
                      f"{'rise_dms':>9}  {'spec_dist':>9}  loose")
        for m, j in worst:
            spec = f"{m.spectral_dist:.3f}" if m.spectral_dist == m.spectral_dist else "n/a"
            lines.append(
                f"{m.orig_t:8.3f}  {m.driver_t:8.3f}  {m.delta_ms:+9.1f}  {j:+9.1f}  "
                f"{m.rise_delta_ms:+9.1f}  {spec:>9}  {'YES' if abs(j) > _thr else ''}"
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
