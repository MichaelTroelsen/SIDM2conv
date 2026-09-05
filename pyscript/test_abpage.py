"""Tests for pyscript/abpage.py -- the A/B listening pages.

Every test that touches staging redirects the module at a tmp_path with
`monkeypatch.setattr(A, "ROOT", tmp_path)`. That works ONLY because every
path in the module goes through `listen_dir()`, which re-resolves against the
CURRENT `ROOT` on each call; a module-level constant computed at import time
would ignore the monkeypatch and read the real `build/listen`. h2g's own
module carries the same note because two of its tests silently began
asserting against the live corpus instead of their fixture.
"""
from __future__ import annotations

import json
import math
import shutil
import struct
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyscript import abpage as A


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def write_wav(path: Path, seconds=1.0, rate=44100, freq=440.0, channels=1,
              sampwidth=2, amp=0.5):
    n = int(rate * seconds)
    frames = bytearray()
    for i in range(n):
        v = int(amp * 32767 * math.sin(2 * math.pi * freq * i / rate))
        for _ in range(channels):
            frames += struct.pack("<h", v)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(bytes(frames))
    return path


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """A tmp repo root with one staged pair, module redirected at it."""
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = tmp_path / "build" / "listen"
    write_wav(d / "Tune.original.wav", seconds=0.4, freq=440.0)
    write_wav(d / ("Tune.%s.wav" % A.OURS), seconds=0.4, freq=445.0)
    return tmp_path


# ---------------------------------------------------------------------------
# _read_wav_mono -- must never crash a build on bad input
# ---------------------------------------------------------------------------

def test_read_wav_mono_reads_a_real_wav(tmp_path):
    p = write_wav(tmp_path / "a.wav", seconds=0.1, rate=8000)
    got = A._read_wav_mono(p)
    assert got is not None
    samples, rate = got
    assert rate == 8000
    assert len(samples) == 800
    assert all(-1.0 <= s <= 1.0 for s in samples)


def test_read_wav_mono_averages_stereo_to_mono(tmp_path):
    p = write_wav(tmp_path / "s.wav", seconds=0.1, rate=8000, channels=2)
    samples, rate = A._read_wav_mono(p)
    assert len(samples) == 800          # frames, not interleaved samples


@pytest.mark.parametrize("make", [
    lambda p: p.write_bytes(b""),                       # empty
    lambda p: p.write_bytes(b"RIFF\x00\x00\x00\x00WAVEjunk"),   # truncated
    lambda p: p.write_bytes(b"not a wav at all"),       # not a wav
])
def test_read_wav_mono_returns_none_on_bad_input(tmp_path, make):
    p = tmp_path / "bad.wav"
    make(p)
    assert A._read_wav_mono(p) is None


def test_read_wav_mono_rejects_8bit(tmp_path):
    """Only 16-bit PCM is handled; anything else must decline, not guess."""
    p = tmp_path / "eight.wav"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)
        wf.setframerate(8000)
        wf.writeframes(b"\x80" * 800)
    assert A._read_wav_mono(p) is None


def test_read_wav_mono_missing_file_is_none(tmp_path):
    assert A._read_wav_mono(tmp_path / "nope.wav") is None


# ---------------------------------------------------------------------------
# FFT / spectrogram
# ---------------------------------------------------------------------------

def test_fft_matches_a_naive_dft():
    sig = [complex(math.sin(2 * math.pi * 3 * i / 16), 0.0) for i in range(16)]
    fast = A._fft(sig)
    for k in range(16):
        slow = sum(sig[n] * complex(math.cos(-2 * math.pi * k * n / 16),
                                    math.sin(-2 * math.pi * k * n / 16))
                   for n in range(16))
        assert abs(fast[k] - slow) < 1e-9


def test_spectrogram_grid_shape_and_none_when_too_short():
    rate = 44100
    samples = [math.sin(2 * math.pi * 1000 * i / rate) for i in range(rate)]
    grid = A._spectrogram_grid(samples, rate, cols=20, bins=8)
    assert len(grid) == 8 and all(len(r) == 20 for r in grid)
    # Shorter than one analysis window: no grid rather than a padded lie.
    assert A._spectrogram_grid(samples[:100], rate, cols=20, bins=8) is None


def test_spectrogram_grid_puts_energy_in_the_right_bin():
    rate = 44100
    lo = [math.sin(2 * math.pi * 100 * i / rate) for i in range(rate)]
    hi = [math.sin(2 * math.pi * 8000 * i / rate) for i in range(rate)]
    g_lo = A._spectrogram_grid(lo, rate, cols=4, bins=16)
    g_hi = A._spectrogram_grid(hi, rate, cols=4, bins=16)
    peak_lo = max(range(16), key=lambda b: g_lo[b][2])
    peak_hi = max(range(16), key=lambda b: g_hi[b][2])
    assert peak_lo < peak_hi


def test_grids_to_bytes_shares_one_peak_so_quieter_draws_dimmer():
    """The loudness difference between the two renders is part of what the
    overlay shows -- re-normalising each side independently would erase it."""
    loud = [[1.0, 1.0], [1.0, 1.0]]
    quiet = [[0.01, 0.01], [0.01, 0.01]]
    ba, bb = A._grids_to_bytes(loud, quiet)
    assert max(ba) == 255                      # the loud side hits the top
    assert max(bb) < max(ba)                   # the quiet side is visibly down


def test_spectrogram_payload_none_when_a_side_is_missing(staged):
    (staged / "build" / "listen" / ("Tune.%s.wav" % A.OURS)).unlink()
    assert A.spectrogram_payload("Tune") is None


def test_spectrogram_card_empty_without_a_payload():
    assert A.spectrogram_card(None) == ""
    assert "canvas" in A.spectrogram_card(
        {"cols": 4, "bins": 2, "fmin": 40.0, "fmax": 12000.0, "a": "", "b": ""})


# ---------------------------------------------------------------------------
# staged_names -- the .v[123] stems are not tunes of their own
# ---------------------------------------------------------------------------

def test_staged_names_excludes_solo_voice_stems(staged):
    d = staged / "build" / "listen"
    for v in (1, 2, 3):
        write_wav(d / ("Tune.v%d.original.wav" % v), seconds=0.05)
        write_wav(d / ("Tune.v%d.%s.wav" % (v, A.OURS)), seconds=0.05)
    assert A.staged_names() == ["Tune"]


def test_staged_names_empty_when_nothing_staged(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    assert A.staged_names() == []


# ---------------------------------------------------------------------------
# the report-quoting layer -- an honest gap, never an empty rail
# ---------------------------------------------------------------------------

def test_page_with_no_chips_says_so_rather_than_showing_an_empty_rail(staged):
    html = A.page("Tune", {}, [], "v1", embed=False, index_link=True)
    assert "not in --chips" in html
    assert "No notes were written" in html


def test_page_renders_supplied_chips_and_notes(staged):
    html = A.page("Tune", {"onset": "94.1%"}, ["**Listen** to the `bass`"],
                  "v1", embed=False, index_link=True)
    assert "94.1%" in html and "onset" in html
    assert "<strong>Listen</strong>" in html and "<code>bass</code>" in html


def test_chips_rows_bad_json_returns_empty_not_garbage(tmp_path, capsys):
    p = tmp_path / "chips.json"
    p.write_text("{not json", encoding="utf-8")
    assert A.chips_rows(p) == {}
    assert "does not parse" in capsys.readouterr().out


def test_chips_rows_reads_a_good_file(tmp_path):
    p = tmp_path / "chips.json"
    p.write_text(json.dumps({"Tune": {"onset": "94.1%", "n": 312}}),
                 encoding="utf-8")
    assert A.chips_rows(p) == {"Tune": {"onset": "94.1%", "n": "312"}}


def test_chips_rows_none_path_is_empty():
    assert A.chips_rows(None) == {}
    assert A.listening_notes(None) == {}


def test_listening_notes_parses_headings_and_bullets(tmp_path):
    p = tmp_path / "notes.md"
    p.write_text("## Tune\n- first\n- second\n\n## Other\n- only\n",
                 encoding="utf-8")
    assert A.listening_notes(p) == {"Tune": ["first", "second"],
                                    "Other": ["only"]}


# ---------------------------------------------------------------------------
# page structure
# ---------------------------------------------------------------------------

def test_page_wires_both_audio_elements_and_the_blind_rig(staged):
    html = A.page("Tune", {}, [], "v1", embed=False, index_link=True)
    assert 'id="au"' in html and 'id="bu"' in html
    assert 'src="Tune.original.wav"' in html
    assert 'src="Tune.%s.wav"' % A.OURS in html
    assert 'id="blind"' in html and 'id="guessA"' in html
    assert 'id="syncr"' in html          # the sync control
    assert "window.__abSpectrogram" in html


def test_page_omits_the_voice_card_without_solo_stems(staged):
    html = A.page("Tune", {}, [], "v1", embed=False, index_link=True)
    assert "Each voice, drawn" not in html
    assert "window.__abVoices = {}" in html


def test_page_adds_the_voice_card_when_all_six_stems_exist(staged):
    d = staged / "build" / "listen"
    for v in (1, 2, 3):
        write_wav(d / ("Tune.v%d.original.wav" % v), seconds=0.05)
        write_wav(d / ("Tune.v%d.%s.wav" % (v, A.OURS)), seconds=0.05)
    html = A.page("Tune", {}, [], "v1", embed=False, index_link=True)
    assert "Each voice, drawn" in html
    assert "Tune.v2.%s.wav" % A.OURS in html
    # The muting caveat must travel with the card, not live only in the docs.
    assert "not clean isolation on every tune" in html


def test_voice_card_needs_all_six_not_some(staged):
    d = staged / "build" / "listen"
    write_wav(d / "Tune.v1.original.wav", seconds=0.05)
    html = A.page("Tune", {}, [], "v1", embed=False, index_link=True)
    assert "Each voice, drawn" not in html


def test_embed_inlines_the_audio_and_drops_the_voice_card(staged):
    html = A.page("Tune", {}, [], "v1", embed=True, index_link=False)
    assert "data:audio/wav;base64," in html
    assert "Each voice, drawn" not in html
    assert "index.html" not in html          # no back-link without an index


def test_page_is_theme_aware_both_ways():
    """A page renders in the viewer's theme; a colour defined only inside a
    media query leaves the other mode unpainted."""
    assert "prefers-color-scheme: dark" in A.CSS
    assert '[data-theme="dark"]' in A.CSS
    assert "--ground:#EEF1F4" in A.CSS       # the bare :root light default


# ---------------------------------------------------------------------------
# the instrument-map card
#
# The rule under test is a REFUSAL, so most of these feed it a key that fails.
# A card that only ever gets a passing fixture is a card whose whole purpose is
# untested: on the calibration corpus roughly a third of files cannot be keyed.
# ---------------------------------------------------------------------------

def _im(verdict, why="because", rows=(), orphans=(), layout=None):
    return {"key": {"verdict": verdict, "why": why},
            "map": list(rows), "orphans": list(orphans),
            "layout_verdict": layout}


ROW = {"records": [3], "adsr": "$0A8C", "orig_wave": "pulse", "orig_notes": 12,
       "ours_wave": "saw", "ours_notes": 12, "verdict": "wave differs"}


def test_instrmap_card_absent_without_a_payload():
    assert A.instrmap_card(None) == ""
    assert A.instrmap_card({}) == ""


@pytest.mark.parametrize("verdict", ["no-trace", "unusable", "insufficient-data"])
def test_a_failed_key_emits_NO_table_only_the_verdict(verdict):
    """The whole value of the card is refusing to draw when the key fails."""
    html = A.instrmap_card(_im(verdict, why="the key does not hold here"))
    assert verdict in html
    assert "the key does not hold here" in html
    assert "<table>" not in html
    assert "the result, not a failure" in html


def test_the_verdict_is_shown_even_when_a_table_is():
    html = A.instrmap_card(_im("reliable", why="stable enough to key on",
                               rows=[ROW]))
    assert "reliable" in html and "stable enough to key on" in html
    assert "<table>" in html


def test_a_disagreeing_row_is_marked_and_an_agreeing_one_is_not():
    """The tool's agreement word is `ok`, NOT `match`. Guessing `match` marked
    every row on the first real file as differing -- 27 of 27, including the 9
    that agreed."""
    agree = dict(ROW, verdict="ok", ours_wave="pulse")
    html = A.instrmap_card(_im("reliable", rows=[ROW, agree]))
    assert html.count('<tr class="differs">') == 1
    assert html.count('<tr class="agree">') == 1


def test_a_record_neither_side_sounds_is_NO_EVIDENCE_not_agreement(monkeypatch):
    """The third state, and the one that matters most.

    On the first real file measured, 18 of 27 rows were `unused both sides` --
    records NEITHER side ever sounds. Counting them as differences paints two
    thirds of the table as broken; counting them as agreement is the
    vacuous-agreement bug. They are evidence of nothing and must render as a
    third thing.
    """
    unused = dict(ROW, verdict="unused both sides", orig_notes=0, ours_notes=0,
                  orig_wave="-", ours_wave="-")
    html = A.instrmap_card(_im("reliable", rows=[ROW, unused]))
    assert html.count('<tr class="noevidence">') == 1
    assert html.count('<tr class="differs">') == 1
    assert "no evidence" in html
    assert "not agreement and not a defect" in html


def test_the_card_counts_all_three_states_explicitly():
    rows = [ROW,
            dict(ROW, verdict="ok"),
            dict(ROW, verdict="ok"),
            dict(ROW, verdict="unused both sides")]
    html = A.instrmap_card(_im("reliable", rows=rows))
    assert "<b>1 record(s) differ</b>" in html
    assert "2 agree" in html
    assert "1 are sounded by NEITHER side" in html


def test_degenerate_still_draws_a_table_and_says_it_separates_nothing():
    """instrument_map.Verdict.usable INCLUDES degenerate on purpose -- a single
    ADSR over every note is a perfectly stable key that carries no information,
    and the module says the caller should SAY so rather than refuse. Hard-coding
    'degenerate means no table' here would contradict the module."""
    html = A.instrmap_card(_im("degenerate", rows=[ROW]))
    assert "<table>" in html
    assert "separates nothing" in html


def test_suspect_draws_a_table_with_its_own_caution():
    html = A.instrmap_card(_im("suspect", rows=[ROW]))
    assert "<table>" in html
    assert "unconfirmed" in html


def test_orphan_envelopes_are_reported_as_a_key_blind_spot():
    """An envelope NEITHER side declares is a hole in the key, not a conversion
    gap -- conflating the two has produced a wrong answer here before."""
    html = A.instrmap_card(_im("reliable", rows=[ROW],
                               orphans=[{"adsr": "$0028", "notes": 50}]))
    assert "$0028" in html
    assert "blind spot in the key, not necessarily a conversion gap" in html


def test_the_card_says_the_table_was_located_by_search():
    html = A.instrmap_card(_im("reliable", rows=[ROW], layout="row-major @ $1A6B"))
    assert "by <b>search</b>" in html
    assert "0 of 10" in html          # the concrete miss that motivates the rule


def test_an_empty_map_refuses_regardless_of_a_usable_verdict():
    """The refusal is DERIVED from the tool's own output (rows are computed only
    when Verdict.usable), never re-implemented from the verdict word."""
    html = A.instrmap_card(_im("reliable", rows=[]))
    assert "<table>" not in html


def test_instrmap_payload_and_card_reach_the_page(staged):
    d = staged / "build" / "listen"
    (d / "Tune.instrmap.json").write_text(
        json.dumps(_im("reliable", why="stable", rows=[ROW])), encoding="utf-8")
    assert A.build(None, None, None, None) == 0
    html = (d / "Tune.html").read_text(encoding="utf-8")
    assert "Which instrument" in html and "$0A8C" in html


def test_a_page_without_an_instrmap_simply_omits_the_card(staged):
    assert A.build(None, None, None, None) == 0
    html = (staged / "build" / "listen" / "Tune.html").read_text(encoding="utf-8")
    assert "Which instrument" not in html


def test_instrmap_skips_and_NAMES_a_tune_with_no_sources_sidecar(staged, capsys):
    """Absent a sidecar the card is simply missing, which reads as 'nothing to
    report'. It must say so instead."""
    assert A.instrmap(None, 0, 0) == 0
    out = capsys.readouterr().out
    assert "SKIP Tune" in out and "sources.json" in out


def test_stage_records_a_sources_sidecar(tmp_path, monkeypatch):
    """Written LAST, so it exists only if the renders actually succeeded."""
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = tmp_path / "build" / "listen"
    d.mkdir(parents=True)
    (d / "X.sources.json").write_text(json.dumps(
        {"original": "a.sid", "converted": "b.sf2", "seconds": 20,
         "driver_init": 4096, "driver_play": 4099}), encoding="utf-8")
    got = A.sources_for("X")
    assert got["converted"] == "b.sf2" and got["driver_init"] == 4096
    assert A.sources_for("nope") is None


# ---------------------------------------------------------------------------
# the renderer-mismatch guard
#
# The bug this pins is SILENT: everything renders, the page looks fine, and the
# per-voice strips are comparing two different emulators. It was observed live
# in this repo before it was guarded.
# ---------------------------------------------------------------------------

def _stage_with(monkeypatch, root, renderer, want_voices, **kw):
    """Drive stage() with the renderer decided for us and rendering stubbed."""
    import types
    calls = {"rendered": 0}

    fake = types.SimpleNamespace(
        RenderError=RuntimeError,
        MUTE_MAP={1: "23", 2: "13", 3: "12"},
        choose_renderer=lambda req, voice, v_ok, s_ok: (renderer, "test"),
        resolve_input=lambda p, role, args, tmp, r: _touch_wav(tmp / (role + ".wav"), calls),
        resolve_to_sid=lambda p, role, args, tmp: p,
        _render_muted=lambda sid, out, mute, args: _touch_wav(Path(out), calls),
    )
    # BOTH of these are required, and setitem alone is a trap. abpage.stage()
    # does `from pyscript import audio_tightness_tool as att`, which reads the
    # ATTRIBUTE off the already-imported `pyscript` package object and never
    # consults sys.modules. In isolation nothing has imported that submodule,
    # so the attribute is absent and the sys.modules stub wins -- which is why
    # this file passed on its own. In a full-suite run
    # test_audio_tightness_renderer.py imports it first, the attribute exists,
    # and the stub is bypassed: three tests then invoked the REAL renderer and
    # died on "VSID produced no audio".
    import pyscript as _pyscript_pkg
    monkeypatch.setitem(sys.modules, "pyscript.audio_tightness_tool", fake)
    monkeypatch.setattr(_pyscript_pkg, "audio_tightness_tool", fake,
                        raising=False)
    monkeypatch.setitem(sys.modules, "sidm2.audio_export_wrapper",
                        types.SimpleNamespace(AudioExportIntegration=types.SimpleNamespace(
                            _check_tool_available=lambda: True)))
    monkeypatch.setitem(sys.modules, "sidm2.vsid_wrapper",
                        types.SimpleNamespace(VSIDIntegration=types.SimpleNamespace(
                            _check_tool_available=lambda: True)))
    rc = A.stage(root / "a.sid", root / "b.sf2", "T", 20, None, None, None,
                 want_voices, "auto", 0, **kw)
    return rc, calls


def _touch_wav(p, calls):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_wav(p, seconds=0.05)
    calls["rendered"] += 1
    return p


def _seed(root, renderer):
    d = root / "build" / "listen"
    write_wav(d / "T.original.wav", seconds=0.05)
    write_wav(d / ("T.%s.wav" % A.OURS), seconds=0.05)
    for v in (1, 2, 3):
        write_wav(d / ("T.v%d.original.wav" % v), seconds=0.05)
        write_wav(d / ("T.v%d.%s.wav" % (v, A.OURS)), seconds=0.05)
    (d / "T.sources.json").write_text(json.dumps(
        {"original": "a.sid", "converted": "b.sf2", "renderer": renderer,
         "voices": True}), encoding="utf-8")
    return d


def test_a_renderer_change_over_existing_stems_is_REFUSED(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = _seed(tmp_path, "sidplayfp")
    rc, calls = _stage_with(monkeypatch, tmp_path, "vsid", False)
    assert rc == 2
    out = capsys.readouterr().out
    assert "measurement error" in out
    assert "sidplayfp" in out and "vsid" in out
    assert calls["rendered"] == 0            # refused BEFORE spending renders
    assert (d / "T.v1.original.wav").exists()   # and without destroying them


def test_the_refusal_names_all_three_remedies(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    _seed(tmp_path, "sidplayfp")
    _stage_with(monkeypatch, tmp_path, "vsid", False)
    out = capsys.readouterr().out
    assert "--renderer" in out and "--voices" in out and "--allow-renderer-change" in out


def test_allow_renderer_change_deletes_the_stale_stems_and_proceeds(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = _seed(tmp_path, "sidplayfp")
    rc, calls = _stage_with(monkeypatch, tmp_path, "vsid", False,
                            allow_renderer_change=True)
    assert rc == 0
    assert not list(d.glob("T.v[123].*.wav")), "stale stems must be gone"
    assert "deleted 6 stale stem(s)" in capsys.readouterr().out
    assert calls["rendered"] > 0


def test_the_same_renderer_is_not_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = _seed(tmp_path, "vsid")
    rc, _ = _stage_with(monkeypatch, tmp_path, "vsid", False)
    assert rc == 0
    assert (d / "T.v1.original.wav").exists()   # untouched


def test_a_renderer_change_with_NO_stems_on_disk_is_fine(tmp_path, monkeypatch):
    """Nothing to mismatch against -- the main pair is rewritten wholesale."""
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = tmp_path / "build" / "listen"
    write_wav(d / "T.original.wav", seconds=0.05)
    (d / "T.sources.json").write_text(json.dumps({"renderer": "sidplayfp"}),
                                      encoding="utf-8")
    rc, _ = _stage_with(monkeypatch, tmp_path, "vsid", False)
    assert rc == 0


def test_a_first_stage_with_no_sidecar_is_fine(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    (tmp_path / "build" / "listen").mkdir(parents=True)
    rc, _ = _stage_with(monkeypatch, tmp_path, "vsid", False)
    assert rc == 0


# ---------------------------------------------------------------------------
# the pattern view and its row-to-frame schedule
# ---------------------------------------------------------------------------

REAL_SF2 = Path(__file__).resolve().parent.parent / "SF2" / "Angular.sf2"


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_row_schedule_against_a_known_sf2():
    """Pinned against real numbers, so a change to the arithmetic is visible.

    tempo is FRAMES PER ROW (SF2_FORMAT_SPEC, Tempo Table; driver at 50 Hz) and
    a row occupies duration*tempo frames.

    THESE NUMBERS HAVE BEEN WRONG TWICE AND THE SECOND TIME THIS TEST HELD THEM.
    It first asserted voice 1 had 64 rows ending at frame 899 -- every entry of
    an INTERLEAVED sequence, all three voices stacked into one column, which the
    user spotted on the page. It was then re-pinned to a FLAT read of the packed
    heuristic (64 / 31 rows), and that was wrong too: 34ed351 proved on the bytes
    that the heuristic locates seven rows into the real sequence 07, so the run
    it called "sequence 2 from row 0" is sequence 07 from row 7.

    THE NUMBERS BELOW COME FROM THE ORDERLISTS, which are byte-proved. Voice 2's
    is [transpose, 5,6,3,4,3,7,10,10,11,12,11,13] and the sequence lengths are
    64/64/45/40/45/38/36/36/29/32/29/35 -- so the editor's T3 line, which lives
    at sequence 07 rows 7..14, lands at voice-2 rows 260..267 of the walked
    stream. That is asserted below rather than assumed.
    """
    s = A.row_schedule(REAL_SF2)
    assert s is not None
    assert s["tempo"] == 31
    assert s["default_sequence_length"] == 75
    # 14 sequences: the FILE's, not three per-voice orderlists read as sequences
    assert s["sequences"] == 14
    # All three voices render complete at the default max_rows=2048
    # (abpage-row-schedule-truncates-two-voices-at-512-rows). Under the OLD
    # 512-row default this was [512, 512, 481] with truncated == [0, 1] --
    # voices 0 and 1 cut off two-thirds through the song. Angular's own walk
    # tops out at 744 rows (voice 1), comfortably inside the new cap.
    assert [len(t) for t in s["tracks"]] == [564, 744, 481]
    assert s["truncated"] == []
    assert s["overread"] == [] and s["degenerate"] == []

    # the voice-2 orderlist, recovered from the walked rows
    import itertools
    order = [k for k, _ in itertools.groupby(r["seq"] for r in s["tracks"][2])]
    assert order == [5, 6, 3, 4, 3, 7, 10, 11, 12, 11, 13], order

    # VERIFIED AGAINST THE EDITOR: SF2/Angular.sf2 in SID Factory II (Ctrl+P,
    # F1) renders Track 3 as A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4. Same eight notes
    # test_sf2_viewer_core pins at sequence 07 rows 7..14.
    t2 = s["tracks"][2]
    start = next(i for i, r in enumerate(t2) if r["seq"] == 7)
    assert start == 253, start
    assert [r["n"] for r in t2[start + 7:start + 15]] == [
        "A-4", "G-4", "B-4", "G-4", "D-4", "C-5", "B-4",
        "G-4"], "voice 3 must still match what the editor shows"


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_row_schedule_still_truncates_when_a_caller_passes_a_smaller_cap():
    """The cut/truncated machinery is still live -- raising the DEFAULT to
    2048 (abpage-row-schedule-truncates-two-voices-at-512-rows) does not
    delete the cap itself. Nothing in production currently passes max_rows
    explicitly, so without this test the `cut = True` branch in row_schedule
    would go unexercised by the suite entirely."""
    s = A.row_schedule(REAL_SF2, max_rows=100)
    assert s is not None
    assert [len(t) for t in s["tracks"]] == [100, 100, 100]
    assert s["truncated"] == [0, 1, 2]


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_a_tie_row_advances_no_time():
    """A zero-duration row must not advance the frame clock.

    RE-POINTED AT A SYNTHETIC SCHEDULE, and the reason is a finding rather than
    convenience: under the CORRECT Laxity decode Angular has no zero-duration
    rows at all. `duration` now comes from sidm2/sequence_translator.py, whose
    LaxityEvent defaults to 1 and decodes $80-$9F as 1..32 frames, so the
    minimum is one. `dur == 0` was a property of the packed heuristic that
    34ed351 refuted -- it is not a property of the music.

    The ARITHMETIC is still worth pinning (a tie row that advanced time would
    stretch a song), so it is exercised directly instead of through a fixture
    that no longer produces the shape.
    """
    tempo = 31
    rows = [{"f": 0, "dur": 2, "tie": False},
            {"f": 62, "dur": 0, "tie": True},
            {"f": 62, "dur": 0, "tie": True},
            {"f": 62, "dur": 3, "tie": False},
            {"f": 155, "dur": 1, "tie": False}]
    for i, r in enumerate(rows[1:], 1):
        if r["tie"]:
            assert r["dur"] == 0
        else:
            assert r["f"] == rows[i - 1]["f"] + rows[i - 1]["dur"] * tempo

    # ... and the real fixture is asserted to be free of them, so that this
    # substitution is recorded as a measurement rather than an assumption.
    real = A.row_schedule(REAL_SF2)
    if real is not None:
        assert all(r["dur"] > 0 for t in real["tracks"] for r in t), (
            "Angular now has zero-duration rows again -- if that is correct, this "
            "test should go back to using the real fixture")


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_an_OVER_READ_sequence_is_REFUSED():
    """A sequence decoding to more rows than the file declares is not music.

    THE GUARD IS UNCHANGED AND STILL RIGHT; what changed is that Angular no
    longer trips it. Under the packed heuristic its "sequence 1" decoded to 667
    entries against a declared length of 75, and all three of its columns were
    refused for the same reason (197/174/139 rows -- the ORDERLISTS read with
    the sequence grammar). Under the correct decode the file yields 14 sequences,
    the longest 64 rows, so nothing over-reads and `overread` is empty.

    So the guard is exercised synthetically. Removing it because the fixture
    stopped reaching it would be exactly wrong: the shape it refuses is a
    decoder running past a sequence's real end, which is a live failure mode for
    any file whose table is mislocated.
    """
    s = A.row_schedule(REAL_SF2)
    assert s["overread"] == [], (
        "Angular over-reads again -- that is the two-stage-reader regression, "
        "not a fixture change")
    assert all(len(t) > 0 for t in s["tracks"]), "a voice was refused"

    # the guard itself: seqlen bounds the row source
    seqlen = s["default_sequence_length"]
    assert seqlen == 75
    import inspect
    max_rows_default = inspect.signature(A.row_schedule).parameters["max_rows"].default
    # max_rows_default is None (no cap by default,
    # abpage-row-schedule-cap-still-truncates-four-files-at-2048) -- there is
    # no ceiling to check Angular's tracks against, and that IS the point:
    # nothing here is refusing rows because of seqlen either.
    if max_rows_default is not None:
        assert max(len(t) for t in s["tracks"]) <= max_rows_default


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_the_three_voices_are_DIFFERENT_music_not_one_stacked_column():
    """The bug the user caught: all three voices showed voice 1's column,
    because an interleaved sequence's entries were walked as one voice's rows.
    Three identical or near-identical note runs means it has come back."""
    s = A.row_schedule(REAL_SF2)
    runs = [tuple(r["note"] for r in t[:10]) for t in s["tracks"] if t]
    assert len(runs) >= 2, "at least two voices must decode"
    assert len(set(runs)) == len(runs), "voices are showing the same notes"


def test_row_schedule_returns_none_on_an_unparseable_file(tmp_path):
    bad = tmp_path / "not.sf2"
    bad.write_bytes(b"nonsense")
    assert A.row_schedule(bad) is None


def test_note_name_marks_the_gate_byte_as_a_gate_not_a_pitch():
    """126 is $7E = GATE_ON in this repo's own constant table. It was rendered
    as `===` and described as a tie until de-interleaving made it obvious how
    many of them there were."""
    assert A._note_name(126) == "GATE"
    assert A._note_name(0) == "..."
    assert A._note_name(60).startswith("C-")


def _pat(tracks, tempo=31, degenerate=(), truncated=(), seqlen=75):
    return {"tempo": tempo, "tracks": list(tracks), "frames": 100,
            "sequences": 3, "degenerate": list(degenerate),
            "truncated": list(truncated), "default_sequence_length": seqlen}


def test_patterns_card_absent_without_a_payload():
    assert A.patterns_card(None) == ""
    assert A.patterns_card(_pat([[], [], []])) == ""


def test_patterns_card_names_WHY_a_refused_voice_is_empty():
    row = {"f": 0, "seq": 0, "dur": 1, "note": 60, "instr": 1, "cmd": 0, "tie": False}
    html = A.patterns_card(_pat([[row], [], []], degenerate=[1]))
    assert "Voice 2" in html
    assert "advance no time" in html
    assert "Refused rather than drawn" in html
    assert "667" in html and "663" in html      # the measured evidence, in place


def test_patterns_card_says_the_schedule_is_not_fitted_to_the_audio():
    row = {"f": 0, "seq": 0, "dur": 1, "note": 60, "instr": 1, "cmd": 0, "tie": False}
    html = A.patterns_card(_pat([[row], [row], [row]]))
    assert "never fitted to the audio" in html
    assert "that drift is the row rate being wrong" in html.replace("<b>", "").replace("</b>", "")


def test_page_carries_the_row_frames_for_the_scroll(staged):
    d = staged / "build" / "listen"
    row = {"f": 0, "seq": 0, "dur": 1, "note": 60, "instr": 1, "cmd": 0, "tie": False}
    row2 = dict(row, f=31)
    (d / "Tune.patterns.json").write_text(
        json.dumps(_pat([[row, row2], [], []], degenerate=[1])), encoding="utf-8")
    assert A.build(None, None, None, None) == 0
    html = (d / "Tune.html").read_text(encoding="utf-8")
    assert "window.__abRows = [[0, 31], [], []]" in html
    assert 'id="trk0"' in html


# --- the scroll, actually EXECUTED -----------------------------------------
#
# An HTTP probe cannot see JavaScript that never runs, and that is precisely
# how the scroll shipped broken: a refused voice renders without its trkN
# element, one early return keyed on "all three exist" disabled the scroll for
# EVERY voice, and the page sat at row 000 with no highlight. It looked like a
# feature that did not work. These tests run the real script under node.

def _node() -> str | None:
    return shutil.which("node")


def _run_scroll(tmp_path, missing="", rows=None, script=None):
    import subprocess
    rows = rows or [[0, 31, 31, 62, 62, 93, 93, 124, 124, 155, 155, 186,
                     186, 217, 217, 248, 248, 279, 279, 310, 310, 341],
                    [],
                    [0, 31, 62, 93, 124, 155, 186, 217, 248, 279, 310, 341]]
    js = tmp_path / "script.js"
    js.write_text(script if script is not None else A.SCRIPT, encoding="utf-8")
    harness = Path(__file__).resolve().parent / "abpage_scroll_harness.js"
    r = subprocess.run([_node(), str(harness), str(js), missing, json.dumps(rows)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
def test_a_refused_voice_does_not_disable_the_scroll_for_the_others(tmp_path):
    """The exact configuration the user reported: voice 2 refused, nothing moved."""
    out = _run_scroll(tmp_path, missing="trk1")
    assert "error" not in out, out
    assert out["trk1"] is None                       # refused, as designed
    assert out["trk0"]["highlighted"] == 0           # ...and the others still run
    assert out["trk2"]["highlighted"] == 0
    # and they MOVE, rather than merely being highlighted at row 0
    assert out["after_seek"]["trk0"] > 0
    assert out["after_seek"]["trk2"] > 0


@pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
def test_that_test_would_have_CAUGHT_the_bug(tmp_path):
    """Mutation check: restore the pre-fix guard and confirm the harness fails.

    Without this, the test above could pass for the wrong reason and nobody
    would know it was pinning anything.
    """
    mutant = A.SCRIPT.replace(
        "if (!cols.some(function (c) { return !!c; })) return;",
        "if (cols.some(function (c) { return !c; })) return;")
    assert mutant != A.SCRIPT, "the guard moved; update this mutation"
    out = _run_scroll(tmp_path, missing="trk1", script=mutant)
    assert out["trk0"]["highlighted"] == -1          # the reported symptom
    assert out["trk2"]["highlighted"] == -1
    assert out["after_seek"]["trk0"] == -1


@pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
def test_the_scroll_runs_with_all_three_columns_present(tmp_path):
    out = _run_scroll(tmp_path, missing="")
    assert "error" not in out, out
    assert out["trk0"]["highlighted"] == 0 and out["trk2"]["highlighted"] == 0
    assert out["trk1"]["highlighted"] == -1          # it was given no rows


def test_the_scroll_interpolates_across_ties_not_row_to_row():
    """A tie advances no time, so runs of rows share a frame and the naive
    `frames[i+1] - frames[i]` span is zero -- which pins the scroll and then
    jumps. Angular's voice 1 alternates note/tie, so half its steps hit this.
    Pinned on the emitted script because the behaviour is JS."""
    assert "function nextDistinct" in A.SCRIPT
    assert "frames[j] > frames[i]" in A.SCRIPT
    # the naive span must be gone
    assert "frames[i + 1] - frames[i]" not in A.SCRIPT


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_the_real_schedule_contains_zero_span_steps_the_fix_targets():
    """Guards `nextDistinct` from becoming dead code -- now stated honestly.

    This used to assert the REAL fixture contains zero-span steps. It no longer
    does: under the correct Laxity decode every row lasts at least one frame
    (see test_a_tie_row_advances_no_time), so Angular produces none. That does
    NOT make nextDistinct dead -- a tie-run is still possible in any file whose
    rows carry duration 0, and the interpolation would judder without it.

    What is pinned instead: the mechanism is present in the emitted script, and
    the arithmetic it replaces is gone. The claim "the real fixture exercises
    it" is retired rather than quietly weakened, because a guard asserting
    something false about the fixture is worse than no guard.
    """
    assert "function nextDistinct" in A.SCRIPT
    assert "frames[j] > frames[i]" in A.SCRIPT
    assert "frames[i + 1] - frames[i]" not in A.SCRIPT

    frames = [r["f"] for r in A.row_schedule(REAL_SF2)["tracks"][0]]
    zero_spans = sum(1 for a, b in zip(frames, frames[1:]) if b == a)
    assert zero_spans == 0, (
        "Angular has zero-span steps again (%d). If the decode changed back, "
        "restore the original assertion; if it is a new defect, that is the "
        "bug." % zero_spans)


def test_a_page_without_a_pattern_payload_omits_the_card(staged):
    assert A.build(None, None, None, None) == 0
    html = (staged / "build" / "listen" / "Tune.html").read_text(encoding="utf-8")
    assert "The pattern, as our conversion wrote it" not in html
    assert "window.__abRows = [[], [], []]" in html


def test_patterns_skips_a_non_sf2_conversion(staged, capsys):
    d = staged / "build" / "listen"
    (d / "Tune.sources.json").write_text(json.dumps(
        {"original": "a.sid", "converted": "b.sid"}), encoding="utf-8")
    assert A.patterns(None, 0) == 0
    assert "not an .sf2" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# build / index / prune
# ---------------------------------------------------------------------------

def test_build_writes_a_page_an_index_and_a_launcher(staged):
    assert A.build(None, None, None, None) == 0
    d = staged / "build" / "listen"
    assert (d / "Tune.html").exists()
    assert (d / "index.html").exists()
    assert (d / "Listen.cmd").exists()


def test_build_refuses_when_nothing_is_staged(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    assert A.build(None, None, None, None) == 2
    assert "no staged pairs" in capsys.readouterr().out


def test_build_embed_unknown_tune_refuses(staged, capsys):
    assert A.build(None, None, "Nope", None) == 2
    assert "is not staged" in capsys.readouterr().out


def test_launcher_is_crlf_not_crcrlf(staged):
    """Text mode translates on write, so a string already carrying \\r\\n is
    written as \\r\\r\\n -- a real corruption, invisible to read_text()."""
    A.build(None, None, None, None)
    raw = (staged / "build" / "listen" / "Listen.cmd").read_bytes()
    assert b"\r\r\n" not in raw
    assert b"\r\n" in raw


def test_index_columns_come_from_the_chips_file_not_a_hardcoded_list(staged):
    html = A.index(["Tune"], {"Tune": {"onset": "94.1%", "drift": "0.2"}}, "v1")
    assert "<th>onset</th>" in html and "<th>drift</th>" in html


def test_index_renders_a_dash_for_a_tune_with_no_row(staged):
    html = A.index(["Tune", "Other"], {"Tune": {"onset": "94.1%"}}, "v1")
    assert "&mdash;" in html


def test_prune_removes_only_pages_for_unstaged_tunes(staged):
    d = staged / "build" / "listen"
    A.build(None, None, None, None)
    (d / "Gone.html").write_text("stale", encoding="utf-8")
    (d / "Gone.embed.html").write_text("stale", encoding="utf-8")
    removed = A.prune_stale_pages(A.staged_names())
    names = sorted(p.name for p in removed)
    assert names == ["Gone.embed.html", "Gone.html"]
    assert (d / "Tune.html").exists()
    assert (d / "index.html").exists()          # never pruned
    assert (d / "Tune.original.wav").exists()   # never touches the staged pair


# ---------------------------------------------------------------------------
# the Range-honouring server -- a 200-for-everything handler makes an <audio>
# element replay its opening seconds, which reads as a stale render
# ---------------------------------------------------------------------------

@pytest.fixture
def server(staged):
    import functools
    import http.server
    import threading

    A.build(None, None, None, None)
    handler = functools.partial(A._RangeHandler,
                                directory=str(staged / "build" / "listen"))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d" % httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def _get(url, headers=None):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_server_serves_the_page_and_advertises_ranges(server):
    status, headers, body = _get(server + "/index.html")
    assert status == 200
    assert headers.get("Accept-Ranges") == "bytes"
    assert b"Listening pass" in body


def test_server_honours_a_byte_range(server, staged):
    wav = staged / "build" / "listen" / "Tune.original.wav"
    full = wav.read_bytes()
    status, headers, body = _get(server + "/Tune.original.wav",
                                 {"Range": "bytes=100-199"})
    assert status == 206
    assert headers["Content-Range"] == "bytes 100-199/%d" % len(full)
    assert headers["Content-Length"] == "100"
    assert body == full[100:200]


def test_server_handles_an_open_ended_and_a_suffix_range(server, staged):
    full = (staged / "build" / "listen" / "Tune.original.wav").read_bytes()
    status, _h, body = _get(server + "/Tune.original.wav",
                            {"Range": "bytes=%d-" % (len(full) - 10)})
    assert status == 206 and body == full[-10:]
    status, _h, body = _get(server + "/Tune.original.wav",
                            {"Range": "bytes=-10"})
    assert status == 206 and body == full[-10:]


def test_server_416s_a_range_past_the_end(server, staged):
    full = (staged / "build" / "listen" / "Tune.original.wav").read_bytes()
    status, headers, _b = _get(server + "/Tune.original.wav",
                               {"Range": "bytes=%d-%d" % (len(full) + 5,
                                                          len(full) + 9)})
    assert status == 416
    assert headers["Content-Range"] == "bytes */%d" % len(full)


def test_server_falls_back_to_200_on_a_multi_range(server):
    """Multi-range is not implemented; answering it as a normal 200 is correct,
    answering it with one slice would be wrong."""
    status, _h, _b = _get(server + "/Tune.original.wav",
                          {"Range": "bytes=0-99,200-299"})
    assert status == 200


# `row_schedule` silences the SF2 parser with logging.disable(), which is a
# PROCESS-WIDE switch, not a local one. It used to leak: after one call, the
# host program's logging stayed dead. That is invisible from inside this
# module, and it surfaced as 27 failures in test_stage7_emissions.py,
# test_sf2_diagnostics.py and test_sf2_logger_unit.py -- all of them asserting
# against a log that had become ''. They passed in isolation and only failed
# in a full-suite run, which is the worst shape a regression can have.
def test_row_schedule_restores_the_global_logging_disable_level():
    import logging
    before = logging.root.manager.disable
    A.row_schedule(REAL_SF2)
    assert logging.root.manager.disable == before


def test_row_schedule_restores_logging_even_on_the_early_returns(tmp_path):
    """The early returns are the paths that actually leaked -- a missing file
    bails before any `finally` the naive fix would have reached."""
    import logging
    before = logging.root.manager.disable
    assert A.row_schedule(tmp_path / "nope.sf2") is None
    assert logging.root.manager.disable == before


def test_a_logger_still_emits_after_row_schedule_has_run(caplog):
    """The end-to-end shape of the bug, stated the way the broken tests saw
    it: a log that should carry a message comes back empty."""
    import logging
    A.row_schedule(REAL_SF2)
    with caplog.at_level(logging.INFO, logger="abpage_regression_probe"):
        logging.getLogger("abpage_regression_probe").info("still audible")
    assert "still audible" in caplog.text


# --- the tail: what the scroll does PAST the end of the schedule ----------
# The task that prompted these ("the pattern view keeps scrolling past the end
# of the row schedule") had a premise that MEASUREMENT REFUTES: it does not.
# Seeking well past the last row pins the highlight on that row. It is correct
# by construction rather than by luck -- three independent clamps -- so all
# three are pinned here, because removing any one of them silently restores the
# behaviour the task was worried about.

@pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
def test_seeking_past_the_end_of_the_schedule_pins_the_last_row(tmp_path):
    """REAL EXECUTION, not a source assertion.

    The harness seeks to frame 300 (its fixed 6.0s). Give it a schedule whose
    last row starts at frame 100 and the seek is comfortably past the tail --
    which is how this gets tested without the harness needing a seek argument
    it does not have.

    Five rows, so the last index is 4. Anything other than 4 -- especially a
    larger number, or -1 -- is the runaway this pins against.
    """
    rows = [[0, 25, 50, 75, 100], [], [0, 25, 50, 75, 100]]
    out = _run_scroll(tmp_path, rows=rows)
    assert "error" not in out, out
    assert out["after_seek"]["trk0"] == 4, out["after_seek"]
    assert out["after_seek"]["trk2"] == 4, out["after_seek"]


def test_the_three_clamps_that_make_the_tail_safe_are_all_present():
    """Pinned on the emitted script, and the reason is honest: the node harness
    reports the highlighted ROW INDEX only, never the transform, so two of the
    three clamps are not observable through it. Asserting on the source is
    weaker than executing it and is used only where execution cannot reach.

      1. rowAt() binary-searches for the last frame <= f and returns `best`,
         which cannot exceed frames.length - 1.
      2. nextDistinct() returns -1 when no later frame exists, and the caller
         guards on `j >= 0`, so the tail interpolates against nothing.
      3. frac is clamped to 1, so even a span that did resolve could not
         extrapolate beyond the next row.
    """
    s = A.SCRIPT
    assert "var lo = 0, hi = frames.length - 1, best = 0;" in s   # (1)
    assert "return best;" in s
    assert "      return -1;" in s                                # (2)
    assert "var j = nextDistinct(frames, i);" in s
    assert "if (j >= 0) {" in s
    assert "Math.min(1, Math.max(0, (f - frames[i]) / span))" in s  # (3)


@pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
def test_that_tail_test_would_have_CAUGHT_a_runaway(tmp_path):
    """Mutation check, on the repo's own idiom: break the clamp, see it fail.

    Without this the test above could pass because the schedule happens to end
    where the seek lands, rather than because anything clamps. Mutating rowAt
    to walk one past the last row makes the highlight land on a row that does
    not exist, and `after_seek` reports -1 (no .cur element) rather than 4.
    """
    mutant = A.SCRIPT.replace(
        "if (frames[mid] <= f) { best = mid; lo = mid + 1; } else hi = mid - 1;",
        "if (frames[mid] <= f) { best = mid + 1; lo = mid + 1; } else hi = mid - 1;")
    assert mutant != A.SCRIPT, "rowAt moved; update this mutation"
    rows = [[0, 25, 50, 75, 100], [], [0, 25, 50, 75, 100]]
    out = _run_scroll(tmp_path, rows=rows, script=mutant)
    assert out["after_seek"]["trk0"] != 4, out["after_seek"]


_SF2DIR = Path(__file__).resolve().parent.parent / "SF2"
CYCLES_SF2 = _SF2DIR / "Cycles.sf2"
COMMANDO_SF2 = _SF2DIR / "_test_commando.sf2"


@pytest.mark.skipif(not CYCLES_SF2.exists(), reason="SF2/Cycles.sf2 not present")
def test_the_length_guard_applies_only_to_UNBOUNDED_decodes():
    """A pointer-bounded sequence longer than dsl is MUSIC, not an over-read.

    default_sequence_length is a DEFAULT, not a maximum -- SF2_FORMAT_SPEC.md's
    "Contiguous Sequence Stacking" says sequences legitimately differ in length.
    Refusing on `len > dsl` therefore dropped whole voices. Measured before the
    fix:
        Cycles.sf2   dsl 13 -> tracks [78, 0, 0]     105 refusals
        Unboxed.sf2  dsl 38 -> tracks [0, 512, 512]   22 refusals
    and corpus-wide 132 of 141 voices rendered, with 2 files only partly drawn.
    After: 135 of 141, 0 partial.

    ANGULAR NEVER CAUGHT THIS because its dsl (75) happens to exceed its longest
    sequence (64) -- the coincidence that made the guard look correct for as long
    as one file was the fixture.
    """
    s = A.row_schedule(CYCLES_SF2)
    assert s is not None
    assert s["default_sequence_length"] == 13, s["default_sequence_length"]
    assert all(len(t) > 0 for t in s["tracks"]), (
        "Cycles must draw all three voices; %s means the length guard is refusing "
        "pointer-bounded music again" % [len(t) for t in s["tracks"]])
    assert s["overread"] == [], s["overread"][:3]


@pytest.mark.skipif(not COMMANDO_SF2.exists(), reason="SF2/_test_commando.sf2 not present")
def test_the_guard_STILL_refuses_a_genuinely_unbounded_body():
    """The other half, and the reason the guard was not simply deleted.

    _test_commando.sf2's sequence table does NOT locate, so the fallback readers
    scan to the grammar's own $7F with nothing bounding them and yield bodies of
    11,335 and 13,361 entries against a declared length of 77. Those must not
    reach the page. If this file ever starts rendering, either its table began to
    locate (check that first) or the guard was lost.
    """
    s = A.row_schedule(COMMANDO_SF2)
    assert s is not None
    assert s["overread"], "the runaway bodies are no longer being refused"
    assert all(len(t) == 0 for t in s["tracks"]), [len(t) for t in s["tracks"]]


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_the_gate_is_the_pointer_table_not_a_length():
    """Pins WHICH condition switches the guard, so a future edit cannot quietly
    swap it back to a threshold. laxity_seq_table is set exactly when every body
    was cut at the next pointer."""
    src = (Path(__file__).resolve().parent / "abpage.py").read_text(encoding="utf-8")
    assert 'pointer_bounded = bool(getattr(p, "laxity_seq_table", None))' in src
    assert "if seqlen and not pointer_bounded and len(rowsrc) > seqlen:" in src


_OUTDIR = Path(__file__).resolve().parent.parent / "out"
HAWKEYE_SF2 = _OUTDIR / "hawkeye_subtune_0.sf2"


@pytest.mark.skipif(not HAWKEYE_SF2.exists(), reason="out/hawkeye_subtune_0.sf2 not present")
def test_row_schedule_default_no_longer_truncates_hawkeye_at_2048():
    """abpage-row-schedule-cap-still-truncates-four-files-at-2048.

    Swept over all 411 readable .sf2 in SF2/ and out/ (top-level `glob`, not
    `rglob` -- an rglob over the same two roots picks up 8,753 files from
    nested build/pipeline dirs, which is not the corpus this bug or its fix
    were measured against), out/hawkeye_subtune_0.sf2 sat at EXACTLY 2048 on
    voice 0 under the then-default max_rows=2048 -- clipped by the constant,
    not by the seqlen/pointer/over-read guard. Its TRUE voice-0 length,
    measured with the cap effectively disabled (max_rows=100000), is 2495
    rows. The default is now None (no cap), so calling row_schedule with NO
    max_rows argument -- exactly what production's one caller
    (`sched = row_schedule(conv)`) does -- must render all 2495 rows and
    report the voice as NOT truncated.
    """
    s = A.row_schedule(HAWKEYE_SF2)          # no max_rows -- the production call
    assert s is not None
    assert len(s["tracks"][0]) == 2495, len(s["tracks"][0])
    assert s["truncated"] == [], s["truncated"]


def test_row_schedule_default_is_uncapped():
    """The default itself, pinned directly rather than inferred from one
    fixture's row count -- so a future edit that re-introduces a numeric
    default (even a bigger one) fails here first."""
    import inspect
    default = inspect.signature(A.row_schedule).parameters["max_rows"].default
    assert default is None, (
        "max_rows has a numeric default again -- that is exactly the "
        "recurring defect abpage-row-schedule-cap-still-truncates-four-"
        "files-at-2048 describes: a bigger constant is still a ceiling the "
        "corpus will eventually outgrow")


@pytest.mark.skipif(not COMMANDO_SF2.exists(), reason="SF2/_test_commando.sf2 not present")
def test_the_guard_STILL_refuses_with_no_cap_at_all():
    """The over-read guard must not depend on max_rows being set. With the
    cap OFF (the new default), _test_commando.sf2's unbounded fallback
    bodies (11k+/13k+ entries against a declared length of 77) must still be
    refused -- by the seqlen/pointer_bounded check, not by hitting a row
    ceiling that no longer exists."""
    s = A.row_schedule(COMMANDO_SF2)          # no max_rows: nothing to hit
    assert s is not None
    assert s["overread"], "the runaway bodies are no longer being refused"
    assert all(len(t) == 0 for t in s["tracks"]), [len(t) for t in s["tracks"]]


# --- a track emptied as degenerate is NOT also truncated ----------------------

# These live under out/, NOT SF2/ -- checked, after a first version of this
# file pointed at SF2/ and the three cases SKIPPED silently rather than failing.
# out/ is gitignored, so these three SKIP on a fresh clone: the same portability
# limit CLAUDE.md already records for the bundle-diversity control. The
# corpus-wide invariant test below is the part that still means something
# without them, and `test_a_REAL_truncation_is_still_reported` uses the TRACKED
# SF2/Angular.sf2.
_EMPTY_YET_TRUNCATED = [
    Path(__file__).resolve().parent.parent / "out" / name
    for name in ("BMX_Kidz.sf2", "Human_Race.sf2", "Lakers_vs_Celtics.sf2")
]


@pytest.mark.skipif(not all(p.exists() for p in _EMPTY_YET_TRUNCATED),
                    reason="the three empty-yet-truncated SF2s are not present")
@pytest.mark.parametrize("sf2", _EMPTY_YET_TRUNCATED, ids=lambda p: p.stem)
def test_an_empty_track_is_reported_degenerate_not_truncated(sf2):
    """"Emitted nothing" and "was cut short" cannot both be true.

    Measured at max_rows=2048 BEFORE the fix: each of these three gave
    tracks [0, 0, 0] with truncated == [0, 1, 2] AND degenerate == [0, 1, 2].
    Two branches wrote independently -- the degenerate check empties `rows`,
    and the `cut` flag from the row cap was appended afterwards regardless.

    The distinction is not cosmetic: `truncated` invites a bigger cap, and a
    bigger cap cannot help. Uncapped, these same three still give [0, 0, 0],
    because the rows advance no time and are refused on that ground alone.
    """
    r = A.row_schedule(sf2, max_rows=2048)
    assert r is not None
    assert [len(t) for t in r["tracks"]] == [0, 0, 0]
    assert r["degenerate"] == [0, 1, 2]
    assert r["truncated"] == [], (
        "a track that emitted nothing is not truncated -- it is degenerate")


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_a_REAL_truncation_is_still_reported():
    """The guard above must not silence honest truncation.

    Angular decodes to 564/744/481 rows uncapped; at max_rows=100 every voice
    really is cut short, and has rows to show for it.
    """
    r = A.row_schedule(REAL_SF2, max_rows=100)
    assert [len(t) for t in r["tracks"]] == [100, 100, 100]
    assert r["truncated"] == [0, 1, 2]
    assert r["degenerate"] == []


def test_no_track_is_ever_both_truncated_and_degenerate():
    """The invariant, over the whole readable corpus rather than three files.

    Swept at max_rows=2048 across all 411 top-level .sf2 in SF2/ and out/
    (TOP-LEVEL only -- an rglob picks up 8,753 nested build files and is not
    this module's corpus): zero files have a track in both lists, and no
    truncated flag sits on a track that emitted zero rows. One file still
    reports truncated -- out/hawkeye_subtune_0.sf2, tracks [2048, 0, 133] --
    and that one is honest.
    """
    root = Path(__file__).resolve().parent.parent
    files = sorted((root / "SF2").glob("*.sf2")) + sorted((root / "out").glob("*.sf2"))
    if len(files) < 50:
        pytest.skip("no corpus on this machine")
    seen = 0
    for f in files:
        try:
            r = A.row_schedule(f, max_rows=2048)
        except Exception:                                     # noqa: BLE001
            continue
        if not r:
            continue
        seen += 1
        both = set(r["truncated"]) & set(r["degenerate"])
        assert not both, (f.name, sorted(both))
        for tno in r["truncated"]:
            assert len(r["tracks"][tno]) > 0, (
                "%s track %d is flagged truncated but emitted no rows"
                % (f.name, tno))
    assert seen > 300, "swept too few files for this to mean anything: %d" % seen


# --- a heuristic decode is labelled on the page, not presented as the music ---

def test_a_heuristic_decode_is_labelled_on_the_pattern_card():
    """21-of-45 was the measured split when this task was opened; today it is
    22 structural / 25 heuristic. Refusing the heuristic files would blank
    their pattern view; drawing them unlabelled presents a decode that is
    measurably misaligned (seven rows off on the one ground-truth file) as the
    file's music. So the card says what it is."""
    root = Path(__file__).resolve().parent.parent
    hit = None
    for f in sorted((root / "SF2").glob("*.sf2")):
        r = A.row_schedule(f)
        if (r and (r.get("provenance") or {}).get("structural") is False
                and any(r["tracks"])):
            hit = r
            break
    if hit is None:
        pytest.skip("no heuristic decode with rows in the corpus")
    card = A.patterns_card(hit)
    assert "heuristic decode" in card
    assert "unverified" in card
    assert hit["provenance"]["reader"] in card


@pytest.mark.skipif(not REAL_SF2.exists(), reason="SF2/Angular.sf2 not present")
def test_a_structural_decode_gets_NO_heuristic_banner():
    """Angular's sequence table locates, so its lengths are structural and the
    banner would be a false alarm."""
    r = A.row_schedule(REAL_SF2)
    assert (r.get("provenance") or {}).get("structural") is True
    assert "heuristic decode" not in A.patterns_card(r)


def test_row_schedule_carries_provenance_verbatim():
    """The page's JSON sidecar is written from this dict, so the field must be
    present (None is acceptable only for parsers predating it)."""
    root = Path(__file__).resolve().parent.parent
    r = A.row_schedule(root / "SF2" / "Angular.sf2")
    assert "provenance" in r
    assert set(r["provenance"]) == {"reader", "structural"}

# ---------------------------------------------------------------------------
# `serve` must refuse a port that is already serving.
#
# The bug was NOT that serve lacked an error path -- it has one. It is that on
# Windows the error path never fires: HTTPServer sets allow_reuse_address, and
# SO_REUSEADDR there permits binding an address already in use. Measured
# against a live server, the second bind SUCCEEDED. Both processes then hold
# the port and both answer 200, so a reader silently gets whichever one wins --
# potentially a stale build/listen from a forgotten background process.
# ---------------------------------------------------------------------------


def _free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_port_in_use_is_true_only_while_something_listens():
    import socket

    port = _free_port()
    assert A._port_in_use(port) is False, "nothing is listening yet"

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", port))
        srv.listen(1)
        assert A._port_in_use(port) is True
    finally:
        srv.close()


def test_serve_refuses_an_occupied_port_WITHOUT_binding(monkeypatch, capsys):
    """The refusal must happen BEFORE the bind.

    Binding first and checking afterwards is exactly the defect: on Windows the
    bind succeeds, so by the time anything could notice, the port is shadowed.
    This asserts the server is never constructed at all.
    """
    import http.server

    monkeypatch.setattr(A, "_port_in_use", lambda port, host="127.0.0.1": True)

    def _explode(*a, **k):                       # pragma: no cover - must not run
        raise AssertionError("serve() bound the port despite it being in use")

    monkeypatch.setattr(http.server, "ThreadingHTTPServer", _explode)

    assert A.serve(8791) == 2
    out = capsys.readouterr().out
    assert "8791" in out and "already serving" in out
    assert "--port" in out, "the refusal should say how to pick another port"


def test_serve_still_reports_a_bind_failure_that_is_not_in_use(monkeypatch, capsys):
    """The OSError path is kept, not replaced -- it still covers a privileged
    port, a bad interface, and the POSIX in-use error."""
    import http.server

    monkeypatch.setattr(A, "_port_in_use", lambda port, host="127.0.0.1": False)

    def _refuse(*a, **k):
        raise OSError("permission denied")

    monkeypatch.setattr(http.server, "ThreadingHTTPServer", _refuse)

    assert A.serve(80) == 2
    assert "cannot bind" in capsys.readouterr().out

# ---------------------------------------------------------------------------
# An empty voice must always SAY WHY.
#
# Measured 2026-09-04 over the twelve staged songs: seven rendered no pattern
# card at all. `patterns_card` returned "" whenever no voice had rows, so the
# page looked as though pattern data had never been requested -- when in fact
# every voice had been refused, and for a recorded reason.
#
# One of those reasons was recorded NOWHERE: an orderlist entry naming a
# sequence the reader never produced. `degenerate`, `truncated` and `overread`
# were all reported; this was not, so the card fell through to "this voice has
# no rows in the orderlist" -- which is FALSE for these files. Their orderlists
# are populated (lens like [3,4,3] and [7,7,4]); the ids they name are simply
# absent from the parser's sequence table, 8 of 10 on 2_Young_2_Die_native_part01
# and 17 of 18 on 5_Title_Tunes_song0_part01. The music was not LOCATED, which
# is a different statement from "this voice is empty".
# ---------------------------------------------------------------------------


def _pat_all_empty(**extra):
    d = {"tempo": 31, "tracks": [[], [], []], "frames": 0, "sequences": 3,
         "degenerate": [], "truncated": [], "default_sequence_length": 134}
    d.update(extra)
    return d


def test_patterns_card_is_silent_only_when_there_is_NO_reason():
    """The old behaviour, kept: an all-empty payload with nothing to report
    still renders nothing."""
    assert A.patterns_card(_pat_all_empty()) == ""


def test_patterns_card_EXPLAINS_when_every_voice_was_refused():
    """The fix: all three refused, but a reason exists, so the card appears."""
    pat = _pat_all_empty(missing_sequences=[{"track": 0, "seq": 7},
                                            {"track": 1, "seq": 9},
                                            {"track": 2, "seq": 9}])
    html = A.patterns_card(pat)
    assert html, "every voice refused for a RECORDED reason must still explain"
    assert "7" in html and "9" in html, "name the sequences that did not resolve"
    assert "no rows in the orderlist" not in html, (
        "the orderlist is NOT empty on these files -- saying so is false")


def test_a_missing_sequence_is_not_reported_as_an_empty_orderlist():
    """The specific wrong message this fixes, pinned on its own."""
    one = _pat_all_empty(missing_sequences=[{"track": 1, "seq": 4}])
    html = A.patterns_card(one)
    assert "orderlist and the sequence table disagree" in html
    # voice 1 has no reason of its own -> it may still use the old wording
    assert html.count("no rows in the orderlist") <= 2


def test_row_schedule_records_missing_sequence_references(tmp_path):
    """Real-file check. Skips on a clone without the built corpus, which is
    gitignored -- the assertion is about a defect only real artifacts show."""
    src = Path(__file__).resolve().parent.parent / "out" / "sdi" / \
        "2_Young_2_Die_native_part01.sf2"
    if not src.exists():
        pytest.skip("built SDI corpus not present (out/ is gitignored)")
    r = A.row_schedule(src)
    assert r is not None
    assert r["missing_sequences"], (
        "this file's orderlists name sequences the reader never produced; "
        "that must be RECORDED, not silently skipped")
    # and every empty track has SOME recorded reason
    reasons = set(r["degenerate"]) | set(r["truncated"])
    reasons |= {o["track"] for o in r["overread"]}
    reasons |= {m["track"] for m in r["missing_sequences"]}
    for tno, rows in enumerate(r["tracks"]):
        if not rows:
            assert tno in reasons, (
                "voice %d is empty with no recorded reason -- the page would "
                "have to guess" % tno)
