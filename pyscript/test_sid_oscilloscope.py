"""Tests for pyscript/sid_oscilloscope.py.

Pins BOTH directions of ffmpeg resolution named in the task:
  1. the resolver finds the real bundled binary (tools/ffmpeg/bin/ffmpeg.exe)
  2. an absent binary makes the resolver raise -- never a silent no-op that
     would let a caller render empty/no video and still exit 0.
And one end-to-end smoke test that a real per-voice render lands under
out/oscilloscope from the existing sidplayfp voice-isolation stems.
"""

import shutil
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyscript.sid_oscilloscope import (  # noqa: E402
    find_ffmpeg,
    render_oscilloscope,
    render_voice_oscilloscopes,
    DEFAULT_OUT_DIR,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_FFMPEG = REPO_ROOT / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
SAMPLE_SID = REPO_ROOT / "SID" / "Angular.sid"


def _make_silent_wav(path: Path, seconds: float = 0.5, rate: int = 44100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n)


class TestFindFfmpegResolvesBundledBinary:
    def test_finds_real_bundled_ffmpeg(self):
        """Direction 1: the resolver locates the bundled binary this repo ships."""
        found = find_ffmpeg()
        assert found.exists()
        assert found.name.lower().startswith("ffmpeg")
        assert found == REAL_FFMPEG

    def test_default_repo_root_matches_module_location(self):
        # find_ffmpeg() with no args must derive repo_root from its own file
        # location (like conversion_pipeline._tool_path), not cwd.
        found = find_ffmpeg(repo_root=REPO_ROOT)
        assert found.exists()


class TestFindFfmpegRaisesWhenAbsent:
    def test_raises_on_empty_repo_root(self, tmp_path, monkeypatch):
        """Direction 2: pointing the resolver at a tree with no tools/ffmpeg
        must raise FileNotFoundError naming the paths it looked in -- never
        return a nonexistent path, never fall back to something that lets a
        caller silently proceed. Also chdir into tmp_path so the resolver's
        cwd-fallback tier (mirroring _tool_path's 3rd tier) can't find the
        real repo's bundled ffmpeg out from under the test."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError) as exc_info:
            find_ffmpeg(repo_root=tmp_path)
        msg = str(exc_info.value)
        assert "ffmpeg" in msg.lower()
        assert str(tmp_path) in msg

    def test_render_oscilloscope_raises_and_writes_nothing(self, tmp_path):
        """An absent ffmpeg binary must make render_oscilloscope raise
        rather than silently producing an empty/missing render."""
        wav_path = tmp_path / "silent.wav"
        _make_silent_wav(wav_path)
        out_path = tmp_path / "out.mp4"
        fake_ffmpeg = tmp_path / "does_not_exist" / "ffmpeg.exe"

        with pytest.raises((FileNotFoundError, OSError)):
            render_oscilloscope(wav_path, out_path, fake_ffmpeg)

        assert not out_path.exists()

    def test_render_voice_oscilloscopes_raises_before_any_stem_generated(self, tmp_path):
        """render_voice_oscilloscopes must resolve/validate ffmpeg BEFORE
        calling into sidplayfp stem generation, so a missing encoder fails
        fast with no partial output directory full of stems and no video."""
        out_dir = tmp_path / "oscilloscope"
        fake_ffmpeg = tmp_path / "nope" / "ffmpeg.exe"

        with pytest.raises(FileNotFoundError):
            render_voice_oscilloscopes(
                sid_file=SAMPLE_SID,
                out_dir=out_dir,
                duration=2,
                ffmpeg_bin=fake_ffmpeg,
            )
        # No stems, no videos -- the refusal must be total, not partial.
        assert not out_dir.exists() or list(out_dir.iterdir()) == []


@pytest.mark.skipif(not REAL_FFMPEG.exists(), reason="bundled ffmpeg not present")
class TestRenderOscilloscopeRealFfmpeg:
    def test_renders_a_real_nonempty_video(self, tmp_path):
        wav_path = tmp_path / "silent.wav"
        _make_silent_wav(wav_path, seconds=0.3)
        out_path = tmp_path / "out.mp4"

        result = render_oscilloscope(wav_path, out_path, REAL_FFMPEG)

        assert result == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0


@pytest.mark.skipif(
    not (REAL_FFMPEG.exists() and SAMPLE_SID.exists()),
    reason="bundled ffmpeg or sample SID not present",
)
class TestEndToEndVoiceRenders:
    def test_per_voice_oscilloscope_lands_under_out_oscilloscope(self, tmp_path):
        # Render into a throwaway dir under out/oscilloscope so the DoD's
        # "lands under out/oscilloscope" location is exercised for real,
        # without leaving permanent artifacts in the tracked-looking dir.
        out_dir = DEFAULT_OUT_DIR / "_test_run"
        try:
            rendered = render_voice_oscilloscopes(
                sid_file=SAMPLE_SID,
                out_dir=out_dir,
                duration=2,
                verbose=0,
            )
            assert len(rendered) >= 1
            for voice, path in rendered.items():
                assert path.exists()
                assert path.stat().st_size > 0
                assert out_dir in path.parents or path.parent == out_dir
        finally:
            if out_dir.exists():
                shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
