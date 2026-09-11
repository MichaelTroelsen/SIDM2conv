"""
SidWiz-class per-voice oscilloscope video renderer.

Renders one oscilloscope-style video per voice (using ffmpeg's `showwaves`
filter) from the per-voice isolated WAV stems that
sidm2.sidplayfp_wrapper.SidplayfpIntegration / sidm2.audio_export_wrapper
already produce via sidplayfp's -u<voice> mute flags (see
scripts/sid_to_sf2.py --audio-export-voices). This module does NOT
re-implement voice isolation -- it renders video from the stems those
existing tools generate.

FFMPEG RESOLUTION -- copied strategy, not shared code
------------------------------------------------------
sidm2/conversion_pipeline.py's `_tool_path()` resolves bundled tools by
trying, in order: sys._MEIPASS (frozen build), the repo root derived from
the resolving module's OWN file location (so it doesn't care what the
process cwd is), then finally cwd. Its docstring records why this matters:
a naive `os.path.join(os.getcwd(), 'tools', name)` is only right when the
process happens to be launched from the repo root, and gets it wrong
SILENTLY elsewhere -- player-id.exe not found there means player type
'Unknown' means a fallback to Driver 11, the documented 1-8% accuracy path
for a native Laxity file, and the process still exits 0.

`find_ffmpeg()` below applies the same resolution order to
tools/ffmpeg/bin/ffmpeg(.exe), which is a DIFFERENT layout than
`_tool_path()` handles (that helper looks directly under tools/<name>, not
tools/<name>/bin/<name>), so it is copied and adapted here rather than
imported. tools/ffmpeg/ is listed in .gitignore and the binary itself is
untracked, so a fresh clone has no ffmpeg at all -- unlike `_tool_path`,
which returns a best-guess path even when nothing exists (leaving the
caller to fail however it likes), `find_ffmpeg()` REFUSES LOUDLY: it raises
FileNotFoundError naming every path it looked in, rather than returning a
path that doesn't exist and letting a later subprocess call fail in a way
that could be caught and silently downgraded into "render nothing, exit 0".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sidm2.audio_export_wrapper import AudioExportIntegration  # noqa: E402

__version__ = "1.0.0"

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "out" / "oscilloscope"
DEFAULT_DURATION = 30
DEFAULT_SIZE = "1280x480"
DEFAULT_MODE = "line"  # ffmpeg showwaves mode: point/line/p2p/cline


def _ffmpeg_binary_name() -> str:
    return "ffmpeg.exe" if os.name == "nt" else "ffmpeg"


def _ffmpeg_candidates(repo_root: Path) -> List[Path]:
    """Same three-tier order as conversion_pipeline._tool_path, adapted to
    ffmpeg's tools/ffmpeg/bin/<name> layout instead of tools/<name>."""
    name = _ffmpeg_binary_name()
    candidates: List[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "tools" / "ffmpeg" / "bin" / name)
    candidates.append(repo_root / "tools" / "ffmpeg" / "bin" / name)
    candidates.append(Path.cwd() / "tools" / "ffmpeg" / "bin" / name)
    return candidates


def find_ffmpeg(repo_root: Optional[Path] = None) -> Path:
    """Resolve the bundled ffmpeg binary, refusing loudly if it is absent.

    `repo_root` defaults to this file's own repo (two levels up from
    pyscript/), computed from __file__ so it is correct regardless of cwd.
    Tests pass an explicit `repo_root` pointing at an empty directory to
    exercise the "absent binary" path without touching the real tools/.

    Raises FileNotFoundError (never returns a non-existent path, and never
    falls back to PATH) when nothing is found -- ffmpeg is not expected to
    be a system install here; tools/ffmpeg/ is gitignored precisely because
    it must be present as this repo's own bundled 183MB build, and a
    missing render must be a hard failure, not a quietly empty video.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    candidates = _ffmpeg_candidates(repo_root)
    for c in candidates:
        if c.exists():
            return c
    listed = "\n".join(f"  {c}" for c in candidates)
    raise FileNotFoundError(
        "ffmpeg not found. tools/ffmpeg/ is gitignored and untracked, so a "
        "fresh clone must populate it with a real ffmpeg build "
        "(tools/ffmpeg/bin/ffmpeg(.exe)) before an oscilloscope video can be "
        f"rendered. Looked in:\n{listed}"
    )


def render_oscilloscope(
    wav_path: Path,
    out_path: Path,
    ffmpeg_bin: Path,
    size: str = DEFAULT_SIZE,
    mode: str = DEFAULT_MODE,
    color: str = "0x00ff41",
) -> Path:
    """Render one SidWiz-style oscilloscope video from a mono/stereo WAV.

    Uses ffmpeg's `showwaves` filter (waveform-over-time, the classic
    oscilloscope look), muxed against the source audio so the render is
    both watchable and listenable. Raises subprocess.CalledProcessError on
    an ffmpeg failure rather than leaving a partial/empty file silently
    treated as success -- CalledProcessError carries stderr for diagnosis.
    """
    wav_path = Path(wav_path)
    out_path = Path(out_path)
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV stem not found: {wav_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    filter_complex = (
        f"[0:a]showwaves=s={size}:mode={mode}:colors={color}[v]"
    )
    args = [
        str(ffmpeg_bin),
        "-y",
        "-i", str(wav_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(out_path),
    ]
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        raise subprocess.CalledProcessError(
            result.returncode, args, output=result.stdout, stderr=result.stderr
        )
    return out_path


def render_voice_oscilloscopes(
    sid_file: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    duration: int = DEFAULT_DURATION,
    subtune: Optional[int] = None,
    size: str = DEFAULT_SIZE,
    mode: str = DEFAULT_MODE,
    verbose: int = 1,
    ffmpeg_bin: Optional[Path] = None,
) -> Dict[int, Path]:
    """Generate the 3 per-voice isolated WAV stems (via the existing
    sidplayfp -u<voice> isolation in sidm2.audio_export_wrapper /
    sidm2.sidplayfp_wrapper -- NOT reimplemented here) and render one
    oscilloscope video per voice under out_dir.

    Returns {voice_number: rendered_video_path} for voices that succeeded.
    Raises FileNotFoundError immediately (before any stem is even
    generated) if ffmpeg is not resolvable -- never falls through to a
    silent no-op render.
    """
    sid_file = Path(sid_file)
    out_dir = Path(out_dir)
    ffmpeg_bin = Path(ffmpeg_bin) if ffmpeg_bin is not None else find_ffmpeg()
    if not ffmpeg_bin.exists():
        raise FileNotFoundError(f"ffmpeg binary does not exist: {ffmpeg_bin}")

    out_dir.mkdir(parents=True, exist_ok=True)
    wav_stem_base = out_dir / f"{sid_file.stem}.wav"

    stem_results = AudioExportIntegration.export_voice_stems(
        sid_file=sid_file,
        output_wav=wav_stem_base,
        duration=duration,
        subtune=subtune,
        verbose=verbose,
    )
    if stem_results is None:
        raise RuntimeError(
            "sidplayfp not available -- cannot generate voice stems "
            "(see sidm2/sidplayfp_wrapper.py _find_sidplayfp)"
        )

    rendered: Dict[int, Path] = {}
    for voice, result in stem_results.items():
        if not result.get("success"):
            if verbose > 0:
                print(f"[sid_oscilloscope] voice {voice} stem failed, skipping render: {result.get('error')}")
            continue
        wav_path = out_dir / f"{sid_file.stem}_voice{voice}.wav"
        video_path = out_dir / f"{sid_file.stem}_voice{voice}_oscilloscope.mp4"
        render_oscilloscope(wav_path, video_path, ffmpeg_bin, size=size, mode=mode)
        rendered[voice] = video_path
        if verbose > 0:
            print(f"[sid_oscilloscope] voice {voice}: {video_path}")

    return rendered


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sid_file", help="Path to input .sid file")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION)
    parser.add_argument("--subtune", type=int, default=None)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["point", "line", "p2p", "cline"])
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        rendered = render_voice_oscilloscopes(
            sid_file=Path(args.sid_file),
            out_dir=Path(args.out_dir),
            duration=args.duration,
            subtune=args.subtune,
            size=args.size,
            mode=args.mode,
            verbose=0 if args.quiet else 1,
        )
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as e:
        print(f"[sid_oscilloscope] FAILED: {e}", file=sys.stderr)
        return 1

    if not rendered:
        print("[sid_oscilloscope] FAILED: no voice renders succeeded", file=sys.stderr)
        return 1

    print(f"[sid_oscilloscope] {len(rendered)}/3 voices rendered to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
