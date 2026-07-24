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
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sf2_to_sid import SF2File, convert_sf2_to_sid
from sidm2.audio_export_wrapper import AudioExportIntegration
from sidm2.audio_tightness import analyze_tightness_files, load_wav_mono
from pyscript.audio_tightness_report import format_text_report
from pyscript.audio_tightness_html_exporter import AudioTightnessHTMLExporter

MUTE_MAP = {1: "23", 2: "13", 3: "12"}


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


def _render(sid_path, out_wav, seconds, subtune, voice, verbose):
    """Render a .sid to .wav via SID2WAV (always -- mute/subtune have no VSID
    equivalent, and both sides must use the same tool for an apples-to-apples
    comparison)."""
    mute_voices = MUTE_MAP.get(voice) if voice else None
    result = AudioExportIntegration.export_to_wav(
        sid_file=Path(sid_path), output_file=Path(out_wav),
        duration=int(seconds), verbose=verbose,
        force_sid2wav=True, mute_voices=mute_voices, subtune=subtune,
    )
    if not result or not result.get('success'):
        err = result.get('error') if result else 'no rendering tool available'
        raise RuntimeError(f"Failed to render {sid_path} to WAV: {err}")
    return out_wav


def resolve_input(path: Path, role: str, args, tmp_dir: Path):
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
        return _render(tmp_sid, out_wav, args.seconds, args.subtune, args.voice, args.verbose)

    if ext == '.sid':
        out_wav = tmp_dir / f"{role}.wav"
        return _render(path, out_wav, args.seconds, args.subtune, args.voice, args.verbose)

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

Voice isolation:
  --voice {1,2,3} mutes the OTHER two SID voices (SID2WAV's -m<num>) on BOTH
  renders, so a single channel can be compared cleanly. Renders always use
  SID2WAV (not VSID), since VSID has no mute/subtune equivalent.

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
                         help="Subtune/song number (SID2WAV -o<num>)")
    parser.add_argument('--voice', type=int, choices=[1, 2, 3], default=None,
                         help="Isolate one SID voice by muting the other two on BOTH renders")
    parser.add_argument('--driver-init', type=_hex_or_int, default=None,
                         help="Override the driver SF2's init address (e.g. 0x1000)")
    parser.add_argument('--driver-play', type=_hex_or_int, default=None,
                         help="Override the driver SF2's play address (e.g. 0x1003)")

    parser.add_argument('--onset-tolerance-ms', type=float, default=150,
                         help="Max |delta| to still count as a matched onset (default: 150)")
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

    tmp_dir = Path(tempfile.mkdtemp(prefix="audio_tightness_"))
    try:
        print(f"\nResolving original: {args.orig}")
        try:
            orig_wav = resolve_input(orig_path, 'orig', args, tmp_dir)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return 1
        if orig_wav is None:
            return 1
        print(f"  [OK] {orig_wav}")

        print(f"\nResolving driver: {args.driver}")
        try:
            driver_wav = resolve_input(driver_path, 'driver', args, tmp_dir)
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
