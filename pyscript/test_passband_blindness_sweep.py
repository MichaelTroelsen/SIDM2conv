"""The blindness sweep's criterion, pinned so a re-run means the same thing.

Three prior passband measurements in this repo could not be reproduced because
their scripts were scratch one-offs. This one is tracked, so its CRITERION has
to be tracked too -- otherwise "0 blind events over 728 files" is a number
whose definition drifted out from under it.

What each test exists to stop, in one line each:
  * the windowed criterion silently reverting to the naive adjacent-delta one;
  * FILT_FAST drifting apart from the builder's copy;
  * frame 0's pre-init artefact being counted as a passband change;
  * the Byte_Bite refutation (66e3877) being un-refuted by accident.
"""
import json
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

import passband_blindness_sweep as S            # noqa: E402

BUILDER = os.path.join(_ROOT, "bin", "build_mon_native_song.py")
BYTE_BITE = os.path.join(_ROOT, "SID", "Fun_Fun", "Byte_Bite.sid")


def test_filt_fast_still_agrees_with_the_builder():
    """Read as TEXT, never imported -- and that is the point being pinned.

    Importing bin/build_mon_native_song.py pulls in 11 modules (the graph names
    build_romuzak_driver_full, build_romuzak_native_song, hardtrack_to_sf2,
    mon_to_sf2, the Galway emitters), and the ROMUZAK path writes
    drivers_src/romuzak/layout.inc and out/romuzak_driver.prg -- PATTERNS.md F12
    shared state. A read-only measurement must not touch those, so the constant
    is duplicated and this test is what keeps the duplicate honest.
    """
    src = open(BUILDER, encoding="utf-8").read()
    m = re.search(r"^FILT_FAST\s*=\s*(0x[0-9A-Fa-f]+|\d+)", src, re.M)
    assert m, "FILT_FAST is no longer a module-level constant in the builder"
    assert int(m.group(1), 0) == S.FILT_FAST, (
        "the builder's FILT_FAST moved to %s; passband_blindness_sweep.py still "
        "says %s, so any sweep run since is measuring a different threshold"
        % (m.group(1), hex(S.FILT_FAST)))


def test_a_passband_change_beside_a_cutoff_jump_is_NOT_blind():
    """The window is +/-8 on BOTH sides, not just at the frame itself.

    A filter attack landing one frame either side of the passband write would
    read as blind under the naive adjacent-delta criterion, while the detector
    would in fact have caught it. That is the false-positive shape.
    """
    n = 40
    cut = [100] * n
    pb = [1] * n
    pb[20:] = [2] * (n - 20)                      # passband change at frame 20
    for off in (-8, -1, 0, 1, 8):
        c = list(cut)
        f = 20 + off
        c[f:] = [100 + S.FILT_FAST] * (n - f)     # one jump AT the threshold
        assert S.blind_events(c, pb) == [], "offset %d must not count as blind" % off


def test_a_passband_change_with_no_cutoff_movement_IS_blind():
    n = 40
    cut = [100] * n
    pb = [1] * 20 + [2] * 20
    assert S.blind_events(cut, pb) == [20]


def test_a_cutoff_jump_just_outside_the_window_does_not_clear_it():
    """Pins the window EDGE. 9 frames away is outside; 8 is inside."""
    n = 60
    pb = [1] * 30 + [2] * 30
    c = [100] * n
    c[39:] = [100 + S.FILT_FAST] * (n - 39)       # 9 frames after the change
    assert S.blind_events(c, pb) == [30]


def test_frame_zero_is_never_reported():
    """siddump force-displays $D418 on row 0 with the pre-init bus state, so the
    0 -> real transition is an artefact of the DUMP, not of the tune. Counting it
    would score a blind event in every file on disk."""
    cut = [0] * 10
    pb = [0] + [1] * 9                            # "change" at frame 1
    assert S.blind_events(cut, pb) == []
    # ... while a genuine change later in the same series still counts
    pb2 = [0] + [1] * 4 + [2] * 5
    assert S.blind_events(cut, pb2) == [5]


def test_a_sub_threshold_cutoff_move_does_not_clear_a_blind_event():
    n = 40
    pb = [1] * 20 + [2] * 20
    c = [100 + (i % 2) * (S.FILT_FAST - 1) for i in range(n)]
    assert 20 in S.blind_events(c, pb)


@pytest.mark.skipif(not os.path.isfile(BYTE_BITE), reason="Byte_Bite.sid absent")
def test_byte_bite_separates_the_two_questions_that_look_like_one():
    """THE MEASUREMENT THAT MADE THIS SCRIPT SEPARATE ITS TWO COLUMNS.

    I expected the windowed criterion to score Byte_Bite ZERO, because 66e3877
    refuted it as evidence. It scores 324. Both readings are correct and they
    answer DIFFERENT questions:

      per-EVENT  is THIS passband change invisible to detect_filter_drives?
                 Byte_Bite: yes, 324 times. Its cutoff sweep is in the opening;
                 the every-6-frames passband pulses happen later, where cutoff
                 is static, so no jump falls within +/-8 of them.
      per-FILE   is this file's FILTER invisible to detect_filter_drives?
                 Byte_Bite: NO -- its cutoff moves by >= FILT_FAST elsewhere,
                 so the detector does fire on this file and does build it a
                 filter program.

    66e3877 used the per-FILE test and was right to refute on it. The criterion
    this task specifies is the per-EVENT one, and it does NOT reproduce that
    refutation -- which is exactly why `main()` reports `hits` and `unswept`
    apart instead of pooling them. Pooling is how the last count came out wrong,
    and averaging these two would be the same mistake in a new place.
    """
    rec = S.sweep_file(("fc", BYTE_BITE, 20))
    assert rec["error"] is None, rec["error"]
    assert rec["frames"] > 0
    # per-FILE: the refutation stands, and this is the column that carries it
    assert rec["max_abs_dcutoff"] >= S.FILT_FAST, (
        "Byte_Bite's cutoff must move by at least FILT_FAST somewhere -- that is "
        "the whole reason 66e3877 refuted it as evidence of blindness")
    # per-EVENT: it genuinely has blind passband changes, and hiding that would
    # be fitting the criterion to a conclusion reached by a different test
    assert rec["n_blind"] > 0, (
        "Byte_Bite's passband pulses ARE individually invisible to the cutoff "
        "criterion; a zero here means the windowed test silently reverted")


def test_jsonl_sidecar_is_flushed_per_row_not_buffered_to_close(tmp_path, monkeypatch):
    """Pins the mechanism, not just the end state: a test that only opens the
    finished file after main() returns would pass against the OLD
    collect-then-json.dumps-once behaviour just as well, because both leave a
    complete file behind. This test instead asserts, from INSIDE the fsync call
    that main()'s per-row write triggers, that the sidecar on disk already holds
    exactly as many rows as have been reported so far -- i.e. the data reached
    disk before the sweep moved on to the next file, not only once it finished.
    """
    real_fsync = os.fsync
    seen_counts = []

    def spying_fsync(fd):
        # The write+flush the parent just did must already be on disk here --
        # os.fsync is called once per row, immediately after that row's write.
        with open(jsonl_path, encoding="utf-8") as fh:
            seen_counts.append(sum(1 for _ in fh))
        real_fsync(fd)

    monkeypatch.setattr(S.os, "fsync", spying_fsync)

    out_json = tmp_path / "out.json"
    jsonl_path = str(out_json) + ".jsonl"
    rc = S.main(["--corpus", "fc", "--limit", "3", "--secs", "5",
                 "--jobs", "1", "--json", str(out_json)])
    assert rc == 0
    assert os.path.isfile(jsonl_path), "no incremental sidecar was written"
    assert len(seen_counts) == 3, "expected one fsync per row, got %r" % seen_counts
    # The Nth fsync must see exactly N rows already on disk -- proof each row
    # landed before the next file was even dispatched, not batched at the end.
    assert seen_counts == [1, 2, 3], (
        "sidecar rows were not visible on disk at the time of their own fsync "
        "(%r) -- writes are being buffered rather than flushed incrementally"
        % seen_counts)
    with open(jsonl_path, encoding="utf-8") as fh:
        final_lines = fh.readlines()
    assert len(final_lines) == 3
    for line in final_lines:
        rec = json.loads(line)
        assert rec["corpus"] == "fc"


def test_a_file_that_cannot_be_dumped_is_an_error_not_a_zero():
    """'no blind events' and 'no trace' must never look the same -- an exception
    swallowed into a zero would answer the corpus question wrongly."""
    rec = S.sweep_file(("x", os.path.join(_ROOT, "does_not_exist.sid"), 5))
    assert rec["error"], "a missing file must report an error"
    assert rec["n_blind"] == 0
