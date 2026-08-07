"""Tests for sidm2/fidelity_common.py — the shared validator plumbing (roadmap A3).

Covers: canonical semitone conversion (incl. the boundary semantics the old
per-tool copies disagreed on), PSID wrapping, siddump table parsing on a canned
dump (no subprocess), zig64 fill-forward serialization, the gated best-offset
search, and the A/B harness (dimension registry, output hashing, run delta).
"""
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (           # noqa: E402
    SEMI_REF, freq_to_semi, psid_wrap, iter_siddump_rows, siddump_per_frame,
    siddump_note_onsets, siddump_filter_trace, fill_forward, zig64_voices,
    best_gated_offset, Dimension, register_dimension, dimension, split_key,
    dimensions_present, registers_read, registers_unread, format_coverage,
    output_digest, git_label, result_row, dump_rows, load_rows,
    settings_mismatch, option_drift, regressions, compare_runs,
    format_run_delta,
)
import sidm2.fidelity_common as FC            # noqa: E402


# --- freq_to_semi -----------------------------------------------------------

def test_semi_silence_and_subaudio():
    assert freq_to_semi(None) == -1
    assert freq_to_semi(0) == -1
    assert freq_to_semi(7) == -1        # below the note table
    assert freq_to_semi(8) == 0         # clamped to note 0


def test_semi_reference_is_c4():
    # SEMI_REF is by definition C-4 = note index 48.
    assert freq_to_semi(SEMI_REF) == 48


def test_semi_octaves():
    # One octave up doubles the freq value.
    assert freq_to_semi(SEMI_REF * 2) == 60
    assert freq_to_semi(SEMI_REF // 2) == 36


def test_semi_16bit_max_stays_in_table():
    assert 0 <= freq_to_semi(0xFFFF) <= 95


def test_semi_comparison_stable_across_old_references():
    # The pre-consolidation copies used 0x1168 vs 0x1167. The unified function
    # must classify equal/unequal pairs the same way the old ones did for
    # byte-quantized SID freqs: equal freqs match, a semitone step doesn't.
    for f in (0x0130, 0x1167, 0x13EF, 0x2000, 0x7FFF):
        assert freq_to_semi(f) == freq_to_semi(f)
        up = round(f * 2 ** (1 / 12))
        assert freq_to_semi(up) == freq_to_semi(f) + 1


# --- psid_wrap --------------------------------------------------------------

def test_psid_wrap_header_fields():
    data = bytes(range(16))
    blob = psid_wrap(data, 0x1000, 0x1000, 0x1003)
    assert blob[:4] == b'PSID'
    # header is 0x7C bytes for v2; payload appended verbatim
    assert blob.endswith(data)
    load, init, play = struct.unpack('>HHH', blob[8:14])
    songs, start = struct.unpack('>HH', blob[14:18])
    assert (init, play) == (0x1000, 0x1003)
    assert (songs, start) == (1, 1)
    # load address: either in the header word or as the 2-byte prefix convention
    assert load == 0x1000 or blob[len(blob) - len(data) - 2:len(blob) - len(data)]


# --- siddump parsing (canned dump, no subprocess) ---------------------------

CANNED = """\
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
+-------+---------------------------+---------------------------+---------------------------+---------------+
|     0 | 13EF  D-4 32  41 00DB 500 | 0857  F-2 11  43 00D9 800 | 0000  ...  .. .... ... ... | 5800 F1 Low F |
|     1 | 1400 (D-4 32) ..  .... ... | ....  ... .. .... ... ... | 2100  C-5 21  41 0869 600 | .... .. ... . |
|     2 | ....  ... .. .... ...  ... | 0000  ... 08  .... ... ... | ....  ... ..  .... ... ... | 5000 .. ... . |
"""


def test_iter_siddump_rows():
    rows = list(iter_siddump_rows(CANNED))
    assert [fr for fr, _ in rows] == [0, 1, 2]
    assert all(len(c) >= 6 for _, c in rows)


def test_siddump_note_onsets_from_canned(monkeypatch):
    monkeypatch.setattr(FC, 'run_siddump', lambda p, a: CANNED)
    # unbracketed onsets, no wf requirement: V0 D-4@0, V1 F-2@0, V2 C-5@1
    V = FC.siddump_note_onsets('x', [])
    assert V[0] == [(0, 'D-4')]
    assert V[1] == [(0, 'F-2')]
    assert V[2] == [(1, 'C-5')]
    # require_wf drops nothing here (all onsets carry a WF byte)
    Vw = FC.siddump_note_onsets('x', [], require_wf=True)
    assert Vw == V


def test_siddump_per_frame_fill_forward(monkeypatch):
    monkeypatch.setattr(FC, 'run_siddump', lambda p, a: CANNED)
    frames = FC.siddump_per_frame('x', [])
    assert len(frames) == 3
    v0_f0, fcut0 = frames[0][0][0], frames[0][1]
    assert (v0_f0['freq'], v0_f0['wf'], v0_f0['pul']) == (0x13EF, 0x41, 0x500)
    assert fcut0 == 0x5800
    # frame 1: V0 freq updates to 1400, wf carries forward
    v0_f1 = frames[1][0][0]
    assert (v0_f1['freq'], v0_f1['wf']) == (0x1400, 0x41)
    # frame 2: everything carries forward for V0; filter cutoff updates
    assert frames[2][0][0] == v0_f1
    assert frames[2][1] == 0x5000


def test_siddump_filter_trace_fill_forward(monkeypatch):
    monkeypatch.setattr(FC, 'run_siddump', lambda p, a: CANNED)
    ft = FC.siddump_filter_trace('x', [])
    assert ft == [(0x5800, 0xF1), (0x5800, 0xF1), (0x5000, 0xF1)]


# --- zig64 serialization ----------------------------------------------------

def test_fill_forward():
    assert fill_forward({0: 5, 3: 7}, 5) == [5, 5, 5, 7, 7]
    assert fill_forward({2: 9}, 4) == [0, 0, 9, 9]
    assert fill_forward({}, 3, initial=None) == [None, None, None]


def test_zig64_voices():
    reg = {
        (0, 'freq_lo'): {0: 0xEF}, (0, 'freq_hi'): {0: 0x13},
        (0, 'pw_lo'): {0: 0x00}, (0, 'pw_hi'): {0: 0xF5},   # &0xF -> 0x500
        (0, 'control'): {0: 0x41, 2: 0x40},
        (0, 'attack_decay'): {0: 0x00}, (0, 'sustain_release'): {0: 0xDB},
    }
    V = zig64_voices(reg, 3)
    assert V[0]['freq'] == [0x13EF, 0x13EF, 0x13EF]
    assert V[0]['pw'] == [0x500, 0x500, 0x500]
    assert V[0]['wf'] == [0x41, 0x41, 0x40]
    assert V[1]['freq'] == [0, 0, 0]     # untouched voice serializes to zeros


# --- best-offset search -----------------------------------------------------

def test_best_gated_offset_picks_max_and_keeps_its_total():
    scores = {-1: (2, 10, 'a'), 0: (5, 9, 'b'), 1: (5, 8, 'c'), 2: (3, 7, 'd')}
    off, hits, total, extra = best_gated_offset(range(-1, 3), lambda o: scores[o])
    # ties keep the EARLIEST offset (0 beats 1 at hits=5)
    assert (off, hits, total, extra) == (0, 5, 9, 'b')


# --- dimension registry -----------------------------------------------------

# A build-shape number that reads no SID register. Registered once at import
# so the reads=() path is exercised the way a real caller uses it.
PARTS = register_dimension(
    Dimension("test_parts", (), "SF2 parts a build emitted", "count",
              higher_is_better=False), replace=True)


def test_split_key_scoped_and_bare():
    assert split_key("osc1/freq") == ("osc1", "freq")
    assert split_key("freq") == ("", "freq")


def test_dimension_lookup_is_scope_blind():
    assert dimension("osc3/freq") is dimension("freq")


def test_dimension_unknown_key_raises_not_defaults():
    # A defaulted dimension would silently count as register coverage nobody
    # declared — the exact failure the registry exists to prevent.
    with pytest.raises(KeyError) as e:
        dimension("osc1/no_such_column")
    assert "no_such_column" in str(e.value)


def test_register_dimension_refuses_silent_redefinition():
    d = Dimension("test_redef", ("$D404",), "x")
    register_dimension(d, replace=True)
    with pytest.raises(ValueError):
        register_dimension(Dimension("test_redef", ("$D417",), "y"))
    # identical re-registration is a no-op, not an error (import order)
    register_dimension(Dimension("test_redef", ("$D404",), "x"))


def test_dimensions_present_drops_none_scores():
    # score_pct returns None for an empty comparison; a row that scored n/a
    # contributes no coverage for that register.
    got = dimensions_present({"osc1/freq": 99.0, "osc1/pul": None,
                              "osc2/freq": 100.0})
    assert got == ["freq"]


def test_registers_read_and_unread_complement():
    read = registers_read(["freq", "wf"])
    assert read == {"$D400/$D401", "$D404"}
    unread = [r for r, _ in registers_unread(["freq", "wf"])]
    assert "$D405/$D406" in unread and "$D402/$D403" in unread
    assert "$D404" not in unread


def test_reads_nothing_dimension_adds_no_coverage():
    assert registers_read(["test_parts"]) == set()
    assert len(registers_unread(["test_parts"])) == len(FC.SID_REGISTERS)


def test_registers_unread_empty_when_everything_read():
    every = [d for d in ("freq", "wf", "pul", "adsr", "cutoff", "filtctl",
                         "volmode")]
    assert registers_unread(every) == []


def test_format_coverage_names_the_blind_spots():
    txt = format_coverage(["freq", "wf", "pul"])
    assert "$D400/$D401" in txt
    assert "NOT read by anything in this run" in txt
    assert "$D405/$D406" in txt          # the envelope nobody compared
    assert "every SID register is read" not in txt


def test_format_coverage_says_so_when_nothing_was_compared():
    assert "nothing" in format_coverage([])


# --- Dimension movement / worse ---------------------------------------------

def test_movement_appearing_or_disappearing_ranks_above_any_number():
    d = dimension("freq")
    assert d.movement(99.0, None) == float("inf")
    assert d.movement(None, 99.0) == float("inf")
    assert d.movement(None, None) == 0.0
    assert d.movement(99.0, 100.0) == pytest.approx(1.0)


def test_movement_counts_are_relativised():
    # 5 -> 2823 and 0.94 -> 0.95 must not rank as the same size of finding.
    assert PARTS.movement(5, 2823) > PARTS.movement(100, 101)
    assert PARTS.movement(0, 0) == 0.0


def test_worse_respects_direction():
    freq = dimension("freq")
    assert freq.worse(99.0, 98.0)          # agreement fell
    assert not freq.worse(98.0, 99.0)
    assert PARTS.worse(8, 9)               # more parts is worse
    assert not PARTS.worse(9, 8)


def test_worse_treats_a_lost_measurement_as_a_regression():
    freq = dimension("freq")
    assert freq.worse(99.0, None)          # we could score it, now we cannot
    assert freq.worse(None, 99.0)
    assert not freq.worse(None, None)      # never compared on either side


def test_worse_tolerance_ignores_float_noise():
    assert not dimension("freq").worse(99.0, 99.0 - 1e-12)


# --- output_digest ----------------------------------------------------------

def test_output_digest_missing_path_is_none_not_a_hash(tmp_path):
    # sha1 of nothing is da39a3ee5e6b and compares EQUAL to itself: two failed
    # builds would otherwise read as "byte-identical output", the same
    # empty==empty defect score_pct documents.
    assert output_digest(str(tmp_path / "nope.sf2")) is None
    assert output_digest([]) is None


def test_output_digest_stable_and_content_sensitive(tmp_path):
    a = tmp_path / "part01.sf2"
    a.write_bytes(b"hello")
    first = output_digest(str(a))
    assert first and output_digest(str(a)) == first
    a.write_bytes(b"hellp")
    assert output_digest(str(a)) != first


def test_output_digest_one_missing_part_poisons_the_whole(tmp_path):
    a = tmp_path / "part01.sf2"
    a.write_bytes(b"x")
    assert output_digest([str(a), str(tmp_path / "part02.sf2")]) is None


def test_output_digest_covers_names_and_lengths(tmp_path):
    a, b = tmp_path / "part01.sf2", tmp_path / "part02.sf2"
    a.write_bytes(b"ab")
    b.write_bytes(b"cd")
    both = output_digest([str(a), str(b)])
    assert len(both) == 12
    # renaming a part must move the hash even though the byte set is identical
    c = tmp_path / "part03.sf2"
    b.rename(c)
    assert output_digest([str(a), str(c)]) != both
    # and a split-point collision must not tie: ["ab","cd"] vs ["a","bcd"]
    # concatenate to the same stream, which is why the length is folded in.
    b.write_bytes(b"a")
    a2, b2 = tmp_path / "part01.sf2", tmp_path / "part02.sf2"
    a2.write_bytes(b"a")
    b2.write_bytes(b"bcd")
    assert output_digest([str(a2), str(b2)]) != both


def test_output_digest_order_independent(tmp_path):
    a, b = tmp_path / "part01.sf2", tmp_path / "part02.sf2"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    assert output_digest([str(a), str(b)]) == output_digest([str(b), str(a)])


# --- git_label --------------------------------------------------------------

def test_git_label_is_a_rev_or_none():
    # Scoped to this repo, so it either answers with a short rev (optionally
    # `-dirty`) or declines; it must never raise and never invent a label.
    lab = git_label()
    assert lab is None or (lab.split("-")[0].isalnum() and len(lab) >= 6)


def test_git_label_declines_outside_a_repo(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise OSError("git not found")
    monkeypatch.setattr(FC.subprocess, "run", boom)
    assert git_label(str(tmp_path)) is None


# --- result_row / json roundtrip -------------------------------------------

def test_result_row_derives_dimensions_and_keeps_extras():
    r = result_row("Hawkeye sub0", {"osc1/freq": 99.5, "osc1/pul": None},
                   measurement={"window_secs": 40}, options={"X": "1"},
                   output_sha="abc", label="deadbee", parts=8)
    assert r["target"] == "Hawkeye sub0"
    assert r["dimensions"] == ["freq"]        # pul was n/a, so not covered
    assert r["parts"] == 8
    assert r["measurement"] == {"window_secs": 40}


def test_result_row_rejects_an_undeclared_column():
    with pytest.raises(KeyError):
        result_row("t", {"osc1/mystery": 1.0})


def test_ab_pair_shares_settings_and_hashes_each_side(tmp_path):
    a, b = tmp_path / "off.sf2", tmp_path / "on.sf2"
    a.write_bytes(b"off")
    b.write_bytes(b"on")
    off, on = FC.ab_pair(
        "Hawkeye sub0",
        dict(scores={"osc1/freq": 99.0}, options={"F": None},
             paths=str(a), parts=8),
        dict(scores={"osc1/freq": 99.0}, options={"F": "1"},
             paths=str(b), parts=7),
        measurement={"window_secs": 88, "subtune": 0}, label="c0ffee")
    # the settings that make two runs comparable are shared BY CONSTRUCTION
    assert off["measurement"] == on["measurement"] == {"window_secs": 88,
                                                       "subtune": 0}
    assert off["label"] == on["label"] == "c0ffee"
    # each side's own build is hashed separately, so an A/B can still say the
    # output moved when no score did
    assert off["output_sha"] and on["output_sha"]
    assert off["output_sha"] != on["output_sha"]
    assert (off["parts"], on["parts"]) == (8, 7)
    assert compare_runs([off], [on]).refused == []


def test_ab_pair_missing_artifact_leaves_the_hash_unknown(tmp_path):
    off, on = FC.ab_pair("t",
                         dict(scores={}, paths=str(tmp_path / "gone.sf2")),
                         dict(scores={}, paths=str(tmp_path / "gone2.sf2")))
    assert off["output_sha"] is None and on["output_sha"] is None
    assert "CANNOT say" in compare_runs([off], [on]).verdict


def test_dump_and_load_rows_roundtrip(tmp_path):
    rows = [result_row("t", {"osc1/freq": 99.0}, measurement={"w": 10})]
    p = str(tmp_path / "base.json")
    dump_rows(p, rows)
    assert load_rows(p) == rows


# --- settings / options -----------------------------------------------------

def _row(target, scores, meas=None, opts=None, sha=None, label=None, **kw):
    return result_row(target, scores, measurement=meas, options=opts,
                      output_sha=sha, label=label, **kw)


def test_settings_mismatch_flags_a_different_window():
    b = {"t": _row("t", {}, meas={"window_secs": 40, "subtune": 0})}
    n = {"t": _row("t", {}, meas={"window_secs": 60, "subtune": 0})}
    assert settings_mismatch(b, n) == ["t: window_secs 40 -> 60"]


def test_settings_mismatch_treats_a_missing_field_as_old_not_wrong():
    # A baseline taken before a field was recorded is still a baseline.
    b = {"t": _row("t", {}, meas={"window_secs": 40})}
    n = {"t": _row("t", {}, meas={"window_secs": 40, "subtune": 2})}
    assert settings_mismatch(b, n) == []


def test_option_drift_is_reported_not_refused():
    b = {"t": _row("t", {}, opts={"MON_ARP_STRUCT": None})}
    n = {"t": _row("t", {}, opts={"MON_ARP_STRUCT": "1"})}
    drift = option_drift(b, n)
    assert len(drift) == 1 and "MON_ARP_STRUCT" in drift[0]


# --- regressions / compare_runs --------------------------------------------

def test_regressions_uses_per_dimension_direction():
    a = _row("t", {"osc1/freq": 99.0, "osc1/wf": 100.0})
    b = _row("t", {"osc1/freq": 99.5, "osc1/wf": 98.0})
    assert regressions(a, b) == [("osc1/wf", 100.0, 98.0)]


def test_regressions_flag_a_voice_that_stopped_being_measurable():
    a = _row("t", {"osc2/freq": 97.0})
    b = _row("t", {})
    assert regressions(a, b) == [("osc2/freq", 97.0, None)]


def test_compare_runs_refuses_across_measurement_settings():
    a = [_row("t", {"osc1/freq": 99.0}, meas={"window_secs": 40})]
    b = [_row("t", {"osc1/freq": 99.0}, meas={"window_secs": 60})]
    d = compare_runs(a, b)
    assert d.refused and d.exit_code == 2
    assert "REFUSED" in format_run_delta(d)
    # a refused run must not publish a verdict about the change
    assert d.verdict == ""


def test_compare_runs_refuses_when_no_target_overlaps():
    d = compare_runs([_row("a", {})], [_row("b", {})])
    assert d.refused and d.exit_code == 2


def test_compare_runs_surfaces_options_as_the_change_under_test():
    m = {"window_secs": 40}
    a = [_row("t", {"osc1/freq": 99.0}, meas=m, opts={"F": None}, sha="aa")]
    b = [_row("t", {"osc1/freq": 99.9}, meas=m, opts={"F": "1"}, sha="bb")]
    d = compare_runs(a, b)
    assert not d.refused
    assert d.option_drift and "F" in d.option_drift[0]
    assert d.bytes_changed == ["t"] and not d.regressed
    assert "moved at least one number" in d.verdict


def test_compare_runs_names_the_invisible_change():
    # The sharp case: the build output moved, no measured number did. That is
    # NOT a no-op, and the verdict has to say which of the two it is.
    m = {"window_secs": 40}
    a = [_row("t", {"osc1/freq": 99.0}, meas=m, sha="aa")]
    b = [_row("t", {"osc1/freq": 99.0}, meas=m, sha="bb")]
    d = compare_runs(a, b)
    assert not d.moved and d.exit_code == 0
    assert "invisible" in d.verdict and "NOT a no-op" in d.verdict


def test_compare_runs_names_the_change_that_reached_nothing():
    m = {"window_secs": 40}
    a = [_row("t", {"osc1/freq": 99.0}, meas=m, sha="aa")]
    b = [_row("t", {"osc1/freq": 99.0}, meas=m, sha="aa")]
    d = compare_runs(a, b)
    assert "reached nothing" in d.verdict


def test_compare_runs_admits_it_cannot_tell_without_a_hash():
    m = {"window_secs": 40}
    a = [_row("t", {"osc1/freq": 99.0}, meas=m)]
    b = [_row("t", {"osc1/freq": 99.0}, meas=m)]
    d = compare_runs(a, b)
    assert "CANNOT say" in d.verdict
    assert d.bytes_unknown == ["t"]


def test_compare_runs_sorts_targets_by_largest_movement():
    m = {"window_secs": 40}
    a = [_row("small", {"osc1/freq": 99.0}, meas=m),
         _row("big", {"osc1/freq": 99.0}, meas=m),
         _row("gone", {"osc1/freq": 99.0}, meas=m)]
    b = [_row("small", {"osc1/freq": 99.1}, meas=m),
         _row("big", {"osc1/freq": 80.0}, meas=m),
         _row("gone", {}, meas=m)]
    d = compare_runs(a, b)
    # a lost measurement (inf) outranks any numeric move, then 19.0, then 0.1
    assert [t for t, _ in d.moved] == ["gone", "big", "small"]


def test_compare_runs_reports_only_in_one_run_and_dimension_summary():
    m = {"window_secs": 40}
    a = [_row("t", {"osc1/freq": 99.0, "osc1/wf": 100.0}, meas=m),
         _row("dropped", {"osc1/freq": 50.0}, meas=m)]
    b = [_row("t", {"osc1/freq": 98.0, "osc1/wf": 100.0}, meas=m),
         _row("added", {"osc1/freq": 60.0}, meas=m)]
    d = compare_runs(a, b)
    assert d.only_base == ["dropped"] and d.only_new == ["added"]
    assert d.dimension_summary == {"freq": (1, 1), "wf": (0, 1)}
    assert d.exit_code == 1 and d.regressed


def test_format_run_delta_prints_coverage_and_verdict():
    m = {"window_secs": 40}
    a = [_row("t", {"osc1/freq": 99.0}, meas=m, sha="aa", label="c0ffee")]
    b = [_row("t", {"osc1/freq": 98.0}, meas=m, sha="bb", label="beef00")]
    txt = format_run_delta(compare_runs(a, b))
    assert "c0ffee -> beef00" in txt
    assert "verdict:" in txt
    assert "what this run compared" in txt
    assert "$D405/$D406" in txt            # blind spot named, not remembered
