#!/usr/bin/env python3
"""
Audio Tightness Tool - Compare onset timing + attack shape between two renders

Register-write-exact trace comparison (trace_comparison_tool.py,
accuracy_heatmap_tool.py) can miss audio-domain "tightness" problems that a
human ear catches immediately -- see docs/guides/AUDIO_TIGHTNESS_GUIDE.md for
the motivating case (docs/players/BLACKBIRD.md's B13 entry). This tool
renders both sides to WAV, detects onsets via spectral flux, aligns them, and
reports timing/attack-shape divergence as text (for Claude) and HTML (for a
human).

Usage:
    python audio_tightness_tool.py original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
    python audio_tightness_tool.py original.sid converted.sid --voice 1
    python audio_tightness_tool.py a.wav b.wav --no-html

Version: 1.0.0
"""

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sf2_to_sid import SF2File, convert_sf2_to_sid
from sidm2.audio_export_wrapper import AudioExportIntegration
from sidm2.audio_tightness import (analyze_tightness_files, analyze_voice_bleed,
                                   load_wav_mono, offset_and_jitter,
                                   BLEED_REFUSE_FRAC, BLEED_WARN_FRAC)
from sidm2.fidelity_common import fmt_pct, per_voice_register_agreement
from sidm2.vsid_wrapper import VSIDIntegration
from pyscript.audio_tightness_report import format_text_report
from pyscript.audio_tightness_html_exporter import AudioTightnessHTMLExporter

MUTE_MAP = {1: "23", 2: "13", 3: "12"}
MUTE_ALL = "123"

# Exit code for "the analysis ran, but the per-voice half was withheld because
# voice isolation is not valid on this tune" (see the digi-bleed guard in
# sidm2/audio_tightness.py). Distinct from 1 (the tool failed) because the mix
# row IS still valid and still printed -- a script sweeping a corpus needs to
# tell "no per-voice numbers exist" apart from "the run broke".
EXIT_BLEED_REFUSED = 3

# PAL cycles/second -- same constant bin/listen_compare.py uses to turn a
# wall-clock duration into an exact VSID -limitcycles value.
PAL_CYCLES_PER_SEC = 985248


class RenderError(RuntimeError):
    """A render failed in a way the user needs to act on (not a bug)."""


def choose_renderer(requested, voice, vsid_available, sidplayfp_available):
    """Pick ONE renderer for BOTH sides of the comparison.

    Both renders must come from the same tool -- comparing a VSID render
    against a sidplayfp render would fold two different SID emulations into
    the onset deltas, which is exactly the measurement error this tool
    exists to avoid.

    sidplayfp is the only renderer with a voice-mute flag (-u<num>), so
    --voice forces it. Otherwise VSID is preferred as the long-standing
    default; sidplayfp is the actively maintained replacement for SID2WAV
    (a 1997 build that used to hang indefinitely on some newer tunes -- e.g.
    lft's Glyptodont, which it parsed correctly and then never rendered a
    single sample of, the exact case that motivated this function).

    Returns (renderer, reason). Raises RenderError if the request is
    impossible to satisfy.
    """
    if requested == 'vsid' and voice:
        raise RenderError(
            "--renderer vsid cannot be combined with --voice: VSID has no "
            "voice-mute equivalent. Use --renderer sidplayfp, or drop --voice."
        )

    if requested == 'vsid':
        if not vsid_available:
            raise RenderError(
                "--renderer vsid requested but vsid.exe was not found "
                "(looked in C:\\winvice\\bin, tools/vice/bin, tools/vice, PATH). "
                "Install VICE with: python pyscript/install_vice.py"
            )
        return 'vsid', 'explicitly requested'

    if requested == 'sidplayfp':
        if not sidplayfp_available:
            raise RenderError(
                "--renderer sidplayfp requested but tools/sidplayfp/sidplayfp.exe was not found."
            )
        return 'sidplayfp', 'explicitly requested'

    # auto
    if voice:
        if not sidplayfp_available:
            raise RenderError(
                "--voice requires sidplayfp (the only renderer with a voice-mute "
                "flag), but tools/sidplayfp/sidplayfp.exe was not found."
            )
        return 'sidplayfp', 'required by --voice (only renderer with -u voice mute)'

    if vsid_available:
        return 'vsid', 'preferred (default renderer)'
    if sidplayfp_available:
        return 'sidplayfp', 'VSID not found, falling back'
    raise RenderError(
        "No renderer available: neither vsid.exe nor tools/sidplayfp/sidplayfp.exe was found. "
        "Install VICE with: python pyscript/install_vice.py"
    )


def setup_logging(verbose: int):
    """Setup logging based on verbosity level"""
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format='[%(levelname)s] %(message)s')


def _hex_or_int(s: str) -> int:
    return int(s, 0)


def _voice_arg(s: str):
    """--voice {1,2,3,all}. 'all' sweeps every voice in one run."""
    if s.lower() == 'all':
        return 'all'
    if s in ('1', '2', '3'):
        return int(s)
    raise argparse.ArgumentTypeError(
        f"invalid voice {s!r}: expected 1, 2, 3, or 'all'")


def _render_vsid(sid_path, out_wav, seconds, subtune, verbose):
    """Render via VSID with an exact -limitcycles bound.

    Deliberately NOT routed through VSIDIntegration.export_to_wav(), which
    runs vsid unbounded and kills it on a subprocess timeout -- that makes the
    output length depend on wall-clock speed rather than the requested
    duration, so two renders can differ in length. -limitcycles makes vsid
    stop itself at an exact cycle count, the same technique
    bin/listen_compare.py already uses.

    vsid exits non-zero on normal termination (a documented quirk -- see
    CLAUDE.md), so success is judged by the output file, never the exit code.
    """
    vsid_exe = VSIDIntegration._find_vsid()
    if vsid_exe is None:
        raise RenderError("vsid.exe not found")

    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    if out_wav.exists():
        out_wav.unlink()

    limit = int(seconds * PAL_CYCLES_PER_SEC)
    args = [str(vsid_exe), '-console', '-sounddev', 'wav',
            '-soundarg', str(out_wav), '-limitcycles', str(limit)]
    if subtune is not None:
        args += ['-tune', str(subtune)]
    args.append(str(sid_path))

    if verbose > 1:
        print(f"  Command: {' '.join(args)}")

    # Generous ceiling: vsid renders faster than real time here, but this is
    # a hard stop so a wedged emulator can't hang the tool forever.
    timeout_s = max(60, seconds * 4 + 30)
    try:
        subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        pass  # fall through to the file check below

    if not out_wav.exists() or out_wav.stat().st_size == 0:
        raise RenderError(
            f"VSID produced no audio for {sid_path} (timeout {timeout_s:.0f}s). "
            f"Try --renderer sidplayfp."
        )
    return out_wav


def _render_sidplayfp(sid_path, out_wav, seconds, subtune, voice, verbose):
    """Render via sidplayfp, the only renderer with a voice-mute flag."""
    mute_voices = MUTE_MAP.get(voice) if voice else None
    result = AudioExportIntegration.export_to_wav(
        sid_file=Path(sid_path), output_file=Path(out_wav),
        duration=int(seconds), verbose=verbose,
        force_sidplayfp=True, mute_voices=mute_voices, subtune=subtune,
    )
    if not result or not result.get('success'):
        err = result.get('error') if result else 'no rendering tool available'
        hint = ""
        if 'timeout' in str(err).lower():
            if voice:
                hint = (
                    "\n  --voice forces sidplayfp (it is the only renderer with a "
                    "voice-mute flag), so this file cannot be voice-isolated. "
                    "Drop --voice to render it with VSID instead."
                )
            else:
                hint = "\n  Retry with --renderer vsid."
        raise RenderError(f"Failed to render {sid_path} to WAV: {err}{hint}")
    return out_wav


def _render(sid_path, out_wav, seconds, subtune, voice, renderer, verbose):
    """Dispatch to the renderer chosen once, up front, for BOTH sides."""
    if renderer == 'vsid':
        return _render_vsid(sid_path, out_wav, seconds, subtune, verbose)
    return _render_sidplayfp(sid_path, out_wav, seconds, subtune, voice, verbose)


def resolve_input(path: Path, role: str, args, tmp_dir: Path, renderer: str):
    """Resolve a .sid/.sf2/.wav CLI arg to a WAV file, rendering as needed.
    Returns None (after printing [ERROR]) on failure."""
    ext = path.suffix.lower()

    if ext == '.wav':
        return path

    if ext == '.sf2':
        data = path.read_bytes()
        sf2 = SF2File(data)
        if sf2.address_source == 'default_guess' and args.driver_init is None and args.driver_play is None:
            print(
                f"[ERROR] {path}: init/play addresses could not be auto-detected "
                f"(SF2 has no Block 2 header and doesn't match the Laxity heuristics, "
                f"so this fell back to the Driver 11 default guess -- WRONG for any "
                f"bin/-only native driver). Pass --driver-init/--driver-play with the "
                f"driver's real addresses."
            )
            return None

        tmp_sid = tmp_dir / f"{role}.sid"
        if not convert_sf2_to_sid(str(path), str(tmp_sid),
                                   init_override=args.driver_init, play_override=args.driver_play):
            print(f"[ERROR] Failed to convert {path} to SID")
            return None
        out_wav = tmp_dir / f"{role}.wav"
        return _render(tmp_sid, out_wav, args.seconds, args.subtune, args.voice,
                       renderer, args.verbose)

    if ext == '.sid':
        out_wav = tmp_dir / f"{role}.wav"
        return _render(path, out_wav, args.seconds, args.subtune, args.voice,
                       renderer, args.verbose)

    print(f"[ERROR] Unsupported file extension for {path}: {ext!r} (expected .sid, .sf2, or .wav)")
    return None


def _downsample_envelope(x: np.ndarray, sr: int, hop_s: float):
    """Peak-normalized RMS envelope at hop_s resolution, for the HTML waveform view."""
    hop = max(1, int(round(hop_s * sr)))
    win = hop
    n = max(0, (len(x) - win) // hop + 1)
    env = np.zeros(n)
    for i in range(n):
        seg = x[i * hop: i * hop + win]
        if seg.size:
            env[i] = np.sqrt(np.mean(seg.astype(np.float64) ** 2))
    peak = env.max() if env.size else 0.0
    if peak > 0:
        env = env / peak
    return env.tolist()


def resolve_to_sid(path: Path, role: str, args, tmp_dir: Path):
    """Resolve a .sid/.sf2 CLI arg to a playable .sid, without rendering.

    The single-voice path renders once and is done; the sweep renders the SAME
    file five times with different mutes, and also hands the .sid to siddump for
    the register half of the cross-tab. So "make it playable" has to be
    separable from "render it". Returns None (after printing [ERROR]) on
    failure, including for a .wav input -- a WAV cannot be re-rendered with
    different voices muted, so --voice all is impossible from one.
    """
    ext = path.suffix.lower()
    if ext == '.sid':
        return path
    if ext == '.wav':
        print(f"[ERROR] {path}: --voice all needs a .sid or .sf2 for {role}, not a "
              f"pre-rendered .wav -- voice isolation requires re-rendering with the "
              f"other two voices muted.")
        return None
    if ext == '.sf2':
        data = path.read_bytes()
        sf2 = SF2File(data)
        if sf2.address_source == 'default_guess' and args.driver_init is None and args.driver_play is None:
            print(
                f"[ERROR] {path}: init/play addresses could not be auto-detected "
                f"(SF2 has no Block 2 header and doesn't match the Laxity heuristics, "
                f"so this fell back to the Driver 11 default guess -- WRONG for any "
                f"bin/-only native driver). Pass --driver-init/--driver-play with the "
                f"driver's real addresses."
            )
            return None
        tmp_sid = tmp_dir / f"{role}.sid"
        if not convert_sf2_to_sid(str(path), str(tmp_sid),
                                   init_override=args.driver_init, play_override=args.driver_play):
            print(f"[ERROR] Failed to convert {path} to SID")
            return None
        return tmp_sid
    print(f"[ERROR] Unsupported file extension for {path}: {ext!r} (expected .sid or .sf2)")
    return None


def _render_muted(sid_path, out_wav, mute, args):
    """One sidplayfp render with an explicit mute set.

    Goes straight to AudioExportIntegration rather than through
    _render_sidplayfp's `voice` parameter because the guard render mutes ALL
    THREE voices, which MUTE_MAP cannot express.
    """
    out_wav = Path(out_wav)
    if out_wav.exists():
        out_wav.unlink()
    result = AudioExportIntegration.export_to_wav(
        sid_file=Path(sid_path), output_file=out_wav, duration=int(args.seconds),
        verbose=args.verbose, force_sidplayfp=True, mute_voices=mute,
        subtune=args.subtune)
    if not result or not result.get('success'):
        err = result.get('error') if result else 'no rendering tool available'
        raise RenderError(f"Failed to render {sid_path} (mute={mute!r}): {err}")
    return out_wav


def sweep_renders(sid_path, role, args, tmp_dir):
    """The five renders one side of a voice sweep needs.

    mix + the all-muted guard + one render per isolated voice. The guard render
    is NOT optional and is not derivable from the other four: it is the only way
    to see the signal that survives muting every voice -- the signal that would
    otherwise appear identically in all three "isolated" slices and make them
    agree with each other for reasons that have nothing to do with the driver.
    See sidm2/audio_tightness.py's module comment for the measurements.
    """
    out = {}
    for label, mute in (('mix', None), ('muted', MUTE_ALL),
                        (1, MUTE_MAP[1]), (2, MUTE_MAP[2]), (3, MUTE_MAP[3])):
        wav = _render_muted(sid_path, tmp_dir / f"{role}_{label}.wav", mute, args)
        out[label] = load_wav_mono(wav)[0]
        out[(label, 'path')] = wav
    return out


def row_stats(report, loose_threshold_ms):
    """Collapse a TightnessReport to the scalars the sweep table shows."""
    n_orig = len(report.orig_onsets)
    n_matched = len(report.matched)
    offset, jitters = offset_and_jitter(report.matched)
    abs_jit = sorted(abs(j) for j in jitters)
    p50 = abs_jit[len(abs_jit) // 2] if abs_jit else None
    loose = sum(1 for j in jitters if abs(j) > loose_threshold_ms)
    return {
        'orig_onsets': n_orig,
        'driver_onsets': len(report.driver_onsets),
        'matched': n_matched,
        'missing': len(report.missing),
        'extra': len(report.extra),
        # None, not 100.0 and not 0.0, when the original produced no onsets at
        # all: a render with nothing to match is not a perfect match. Same rule
        # as sidm2.fidelity_common.score_pct, for the same reason.
        'match_rate': (n_matched / n_orig) if n_orig else None,
        'offset_ms': offset if n_matched else None,
        'jitter_p50_ms': p50,
        'loose_pct': (100.0 * loose / len(jitters)) if jitters else None,
    }


def format_bleed(label, bleed):
    def frac(f):
        return ' n/a ' if f is None else f"{100.0 * f:4.1f}%"
    parts = "  ".join(f"v{vb.voice} {frac(vb.shared_frac)}" for vb in bleed.voices)
    corr = "  ".join(f"r({k})={v:+.2f}" for k, v in sorted(bleed.pair_corr.items()))
    ratio = (bleed.muted_rms / bleed.mix_rms) if bleed.mix_rms else float('nan')
    return (f"  {label:9s} residual/mix {ratio:.3f}   shared: {parts}   "
            f"[{bleed.verdict}]\n  {'':9s} inter-voice {corr}")


def diagnose(reg_row, stats, reg_match_pct, audio_match_rate, loose_threshold_ms):
    """The register x audio partition. Returns (verdict, explanation)."""
    freq = reg_row.get('freq') if reg_row else None
    if freq is None:
        return 'n/a', 'registers not exercised on this voice -- cannot partition'
    if stats['match_rate'] is None:
        return 'n/a', 'no onsets detected in the original for this voice'
    reg_ok = freq >= reg_match_pct
    audio_ok = (stats['match_rate'] >= audio_match_rate
                and (stats['jitter_p50_ms'] is None
                     or stats['jitter_p50_ms'] <= loose_threshold_ms))
    if reg_ok and audio_ok:
        return 'ok', 'registers and audio both agree'
    if reg_ok:
        return 'SYNTHESIS', 'registers match, audio diverges -- envelope/pulse/filter timing'
    if not audio_ok:
        return 'SEQUENCER', 'registers and audio both diverge -- note data / sequencer'
    return 'METRIC', 'audio matches, registers do not -- suspect a metric artifact (phase-offset sweep)'


def run_voice_sweep(orig_sid, driver_sid, args, tmp_dir):
    """Sweep all three voices in one run, guarded, cross-tabbed against registers.

    Returns an exit code. Prints its own report -- format_text_report is
    per-comparison and there are four comparisons here.
    """
    print("\nRendering voice sweep (5 renders per side)...")
    o = sweep_renders(orig_sid, 'orig', args, tmp_dir)
    d = sweep_renders(driver_sid, 'driver', args, tmp_dir)

    bleed_o = analyze_voice_bleed(o['mix'], o['muted'], {v: o[v] for v in (1, 2, 3)})
    bleed_d = analyze_voice_bleed(d['mix'], d['muted'], {v: d[v] for v in (1, 2, 3)})

    print("\n" + "=" * 88)
    print("VOICE ISOLATION GUARD  (does muting the other two actually isolate a voice?)")
    print("=" * 88)
    print(f"  warn at {100 * BLEED_WARN_FRAC:.0f}% shared energy, refuse at "
          f"{100 * BLEED_REFUSE_FRAC:.0f}% -- measured thresholds, see "
          f"sidm2/audio_tightness.py")
    print(format_bleed('original', bleed_o))
    print(format_bleed('driver', bleed_d))

    blocked = (bleed_o.blocking or bleed_d.blocking) and not args.allow_digi_bleed
    if bleed_o.blocking or bleed_d.blocking:
        print("\n  [REFUSED] Muting two voices does not isolate the third on this tune:")
        print("            a signal that survives muting ALL THREE dominates each")
        print("            \"isolated\" render, so all three would look alike for")
        print("            reasons that have nothing to do with the driver.")
        if args.allow_digi_bleed:
            print("            --allow-digi-bleed given: reporting anyway, TREAT THE")
            print("            PER-VOICE ROWS AS UNSOUND.")
        else:
            print("            Reporting the mix row only. Re-run with")
            print("            --allow-digi-bleed to see them anyway.")
    elif 'warn' in (bleed_o.verdict, bleed_d.verdict):
        print("\n  [WARN] A meaningful part of each isolated render is shared signal.")
        print("         Per-voice deltas below are usable but partly correlated")
        print("         across voices.")

    rows = ['mix'] if blocked else ['mix', 1, 2, 3]
    stats = {}
    for label in rows:
        report = analyze_tightness_files(
            o[(label, 'path')], d[(label, 'path')],
            onset_tolerance_ms=args.onset_tolerance_ms,
            loose_threshold_ms=args.loose_threshold_ms,
            hop_ms=args.hop_ms, window_ms=args.window_ms, bands=args.bands,
            freq_lo=args.freq_lo, freq_hi=args.freq_hi)
        stats[label] = row_stats(report, args.loose_threshold_ms)

    def _pct(x):
        return 'n/a' if x is None else f"{x:.1f}%"

    def _ms(x, signed=True):
        return 'n/a' if x is None else (f"{x:+.1f}ms" if signed else f"{x:.1f}ms")

    print("\n" + "=" * 88)
    print("PER-VOICE ONSET TIGHTNESS")
    print("=" * 88)
    print(f"  {'side':8s} {'onsets':>7s} {'matched':>8s} {'missing':>8s} {'extra':>6s} "
          f"{'offset':>9s} {'jitter50':>9s} {'loose':>7s}")
    for label in rows:
        st = stats[label]
        name = 'mix' if label == 'mix' else f"voice {label}"
        print(f"  {name:8s} {st['orig_onsets']:7d} {st['matched']:8d} {st['missing']:8d} "
              f"{st['extra']:6d} {_ms(st['offset_ms']):>9s} "
              f"{_ms(st['jitter_p50_ms'], signed=False):>9s} {_pct(st['loose_pct']):>7s}")

    if blocked:
        return EXIT_BLEED_REFUSED

    sub_args = [f"-a{args.subtune}"] if args.subtune is not None else []
    try:
        reg_rows, reg_meta = per_voice_register_agreement(
            str(orig_sid), str(driver_sid), args.seconds,
            orig_args=sub_args, drv_args=sub_args)
    except Exception as e:
        print(f"\n[WARN] Register half of the cross-tab unavailable: {e}")
        return 0

    print("\n" + "=" * 88)
    print(f"REGISTERS x AUDIO  ({reg_meta['frames']} frames, engine delay "
          f"{reg_meta['delay']:+d})")
    print("=" * 88)
    print(f"  {'voice':6s} {'freq':>6s} {'wf':>6s} {'pul':>6s} {'audio':>7s}  diagnosis")
    for v in (1, 2, 3):
        rr = reg_rows.get(v - 1, {})
        st = stats[v]
        verdict, why = diagnose(rr, st, args.reg_match_pct, args.audio_match_rate,
                                 args.loose_threshold_ms)
        audio = 'n/a' if st['match_rate'] is None else f"{100 * st['match_rate']:.0f}%"
        print(f"  {v:<6d} {fmt_pct(rr.get('freq')):>6s} {fmt_pct(rr.get('wf')):>6s} "
              f"{fmt_pct(rr.get('pul')):>6s} {audio:>7s}  {verdict}: {why}")
    print("\n  freq is compared as a SEMITONE (vibrato landing on the same note is not a")
    print("  note error). 'n/a' is never a 0 and never a 100 -- it means not measured.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Compare audio-domain 'tightness' (onset timing + attack shape) "
                     "between an original SID and a converted driver render",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
  %(prog)s original.sid converted.sid --voice 1
  %(prog)s a.wav b.wav --no-html

Output:
  Text report (stdout, or --text-output FILE): onset match/missing/extra
  counts, onset-delta and attack-rise-time statistics, worst-offenders table.
  Designed to be read directly by Claude.
  HTML report (unless --no-html): waveform view with colored onset markers
  and a sortable onset table, for human review.

Renderers:
  ONE renderer is chosen for BOTH sides (mixing two SID emulations would
  contaminate the onset deltas). Default --renderer auto prefers VSID.
  --voice forces sidplayfp (https://github.com/libsidplayfp/sidplayfp), since
  it is the only renderer with a voice-mute flag.

Voice isolation:
  --voice {1,2,3} mutes the OTHER two SID voices (sidplayfp's -u<num>) on BOTH
  renders, so a single channel can be compared cleanly.
  --voice all sweeps all three in one run (5 renders per side) and prints:
    (a) an ISOLATION GUARD -- an extra render with ALL THREE voices muted. On
        many tunes that is not silence, and the signal that survives appears
        identically in all three "isolated" renders, making them agree for
        reasons unrelated to the driver. Measured shared-energy fractions run
        from 0.2%% (Commando) to 68%% (I_Ball); the guard warns at 5%% and REFUSES
        to print per-voice rows at 50%% (exit code 3), which --allow-digi-bleed
        overrides.
    (b) a REGISTERS x AUDIO cross-tab, the partition neither half can make
        alone: registers match + audio diverges = driver synthesis; both
        diverge = note data / sequencer; audio matches + registers do not = a
        metric artifact.

Exit codes:
  0 ok   1 error   3 per-voice rows withheld by the isolation guard

Native drivers (bin/-only, e.g. Blackbird):
  --driver-init/--driver-play are REQUIRED when the .sf2's init/play
  addresses can't be auto-detected -- the tool refuses to guess, since the
  Driver-11 default guess is wrong for these (see docs/guides/AUDIO_TIGHTNESS_GUIDE.md).
        '''
    )

    parser.add_argument('orig', help="Original .sid/.wav file")
    parser.add_argument('driver', help="Driver-rendered .sf2/.sid/.wav file to compare against")

    parser.add_argument('--seconds', type=float, default=30,
                         help="Render duration in seconds (default: 30)")
    parser.add_argument('--subtune', type=int, default=None,
                         help="Subtune/song number (sidplayfp -o<num>)")
    parser.add_argument('--voice', type=_voice_arg, default=None, metavar='{1,2,3,all}',
                         help="Isolate one SID voice by muting the other two on BOTH renders "
                              "(forces --renderer sidplayfp). 'all' sweeps all three in one "
                              "run and cross-tabs them against per-voice register agreement")
    parser.add_argument('--allow-digi-bleed', action='store_true',
                         help="Report per-voice rows even when the isolation guard refuses "
                              "them (see --voice all). The numbers are unsound; this exists "
                              "to inspect them, not to trust them")
    parser.add_argument('--reg-match-pct', type=float, default=95.0,
                         help="Per-voice freq agreement at or above which the REGISTERS are "
                              "called matching in the cross-tab (default: 95)")
    parser.add_argument('--audio-match-rate', type=float, default=0.9,
                         help="Onset match fraction at or above which the AUDIO is called "
                              "matching in the cross-tab (default: 0.9)")
    parser.add_argument('--renderer', choices=['auto', 'vsid', 'sidplayfp'], default='auto',
                         help="Renderer for BOTH sides (default: auto -- prefers VSID)")
    parser.add_argument('--driver-init', type=_hex_or_int, default=None,
                         help="Override the driver SF2's init address (e.g. 0x1000)")
    parser.add_argument('--driver-play', type=_hex_or_int, default=None,
                         help="Override the driver SF2's play address (e.g. 0x1003)")

    parser.add_argument('--onset-tolerance-ms', type=float, default=None,
                         help="Max |delta| to still count as a matched onset. "
                              "Default: auto, derived as half the original's median "
                              "inter-onset interval. A fixed value wider than the note "
                              "spacing lets onsets pair with their neighbours and "
                              "fabricates a systematic offset -- override with care.")
    parser.add_argument('--loose-threshold-ms', type=float, default=40,
                         help="|delta| above which a matched onset is flagged loose (default: 40)")
    parser.add_argument('--hop-ms', type=float, default=10, help="Onset detector hop size (default: 10)")
    parser.add_argument('--window-ms', type=float, default=40, help="Onset detector window size (default: 40)")
    parser.add_argument('--bands', type=int, default=40, help="Onset detector band count (default: 40)")
    parser.add_argument('--freq-lo', type=float, default=30, help="Onset detector band low edge Hz (default: 30)")
    parser.add_argument('--freq-hi', type=float, default=8000, help="Onset detector band high edge Hz (default: 8000)")

    parser.add_argument('-o', '--output', default=None,
                         help="Output HTML path (default: audio_tightness_<timestamp>.html)")
    parser.add_argument('--text-output', default=None, help="Also write the text report to this path")
    parser.add_argument('--no-html', action='store_true', help="Skip HTML generation")
    parser.add_argument('--keep-temp', action='store_true', help="Keep temporary rendered .sid/.wav files")

    parser.add_argument('-v', '--verbose', action='count', default=0, help="Increase verbosity (-v, -vv)")

    args = parser.parse_args()
    setup_logging(args.verbose)

    orig_path = Path(args.orig)
    driver_path = Path(args.driver)

    if not orig_path.exists():
        print(f"[ERROR] File not found: {args.orig}")
        return 1
    if not driver_path.exists():
        print(f"[ERROR] File not found: {args.driver}")
        return 1

    # Resolve the renderer ONCE, before any rendering, so both sides are
    # guaranteed to come from the same tool.
    needs_render = orig_path.suffix.lower() != '.wav' or driver_path.suffix.lower() != '.wav'
    renderer = None
    if needs_render:
        try:
            renderer, reason = choose_renderer(
                args.renderer, args.voice,
                vsid_available=VSIDIntegration._check_tool_available(),
                sidplayfp_available=AudioExportIntegration._check_tool_available(),
            )
        except RenderError as e:
            print(f"[ERROR] {e}")
            return 1
        print(f"\nRenderer: {renderer} ({reason})")

    tmp_dir = Path(tempfile.mkdtemp(prefix="audio_tightness_"))
    try:
        if args.voice == 'all':
            orig_sid = resolve_to_sid(orig_path, 'orig', args, tmp_dir)
            driver_sid = resolve_to_sid(driver_path, 'driver', args, tmp_dir)
            if orig_sid is None or driver_sid is None:
                return 1
            try:
                return run_voice_sweep(orig_sid, driver_sid, args, tmp_dir)
            except RenderError as e:
                print(f"[ERROR] {e}")
                return 1

        print(f"\nResolving original: {args.orig}")
        try:
            orig_wav = resolve_input(orig_path, 'orig', args, tmp_dir, renderer)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return 1
        if orig_wav is None:
            return 1
        print(f"  [OK] {orig_wav}")

        print(f"\nResolving driver: {args.driver}")
        try:
            driver_wav = resolve_input(driver_path, 'driver', args, tmp_dir, renderer)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return 1
        if driver_wav is None:
            return 1
        print(f"  [OK] {driver_wav}")

        print("\nAnalyzing tightness...")
        try:
            report = analyze_tightness_files(
                orig_wav, driver_wav,
                onset_tolerance_ms=args.onset_tolerance_ms,
                loose_threshold_ms=args.loose_threshold_ms,
                hop_ms=args.hop_ms, window_ms=args.window_ms, bands=args.bands,
                freq_lo=args.freq_lo, freq_hi=args.freq_hi,
            )
        except Exception as e:
            print(f"[ERROR] Analysis failed: {e}")
            if args.verbose >= 2:
                import traceback
                traceback.print_exc()
            return 1

        meta = dict(
            orig_path=args.orig, driver_path=args.driver, duration=args.seconds,
            voice=args.voice, mute_voices=MUTE_MAP.get(args.voice) if args.voice else None,
            renderer=renderer or 'n/a (both inputs were .wav)',
        )

        text_report = format_text_report(report, meta)
        print("\n" + text_report)

        if args.text_output:
            Path(args.text_output).write_text(text_report, encoding='utf-8')
            print(f"\n[OK] Text report written: {args.text_output}")

        if not args.no_html:
            if args.output:
                output_path = args.output
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"audio_tightness_{timestamp}.html"

            print(f"\nGenerating HTML report: {output_path}")
            try:
                orig_audio, orig_sr = load_wav_mono(orig_wav)
                driver_audio, driver_sr = load_wav_mono(driver_wav)
                env_hop_s = 0.02
                orig_env = _downsample_envelope(orig_audio, orig_sr, env_hop_s)
                driver_env = _downsample_envelope(driver_audio, driver_sr, env_hop_s)

                exporter = AudioTightnessHTMLExporter(
                    report, meta, orig_env=orig_env, driver_env=driver_env, env_hop_s=env_hop_s
                )
                if exporter.export(output_path):
                    file_size = Path(output_path).stat().st_size
                    print(f"[OK] HTML report generated: {output_path}")
                    print(f"     Size: {file_size:,} bytes")
                else:
                    print("[ERROR] Failed to generate HTML report")
                    return 1
            except Exception as e:
                print(f"[ERROR] Failed to export HTML: {e}")
                if args.verbose >= 2:
                    import traceback
                    traceback.print_exc()
                return 1

        return 0
    finally:
        if args.keep_temp:
            print(f"\n[INFO] Temp render files kept: {tmp_dir}")
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
