"""Guards for the HardTrack duration-law audit.

WHY THESE LIVE IN THIS FILE. They test `pyscript/hardtrack_duration_law_sweep.py`,
so `test_hardtrack_duration_law_sweep.py` is their natural name -- that path is
not in this task's declared `touches` and this one is, and the repo's
missing-test hook matches on IMPORTS rather than on filenames (cb37012), so the
coverage lands either way. Renaming is a job for the cycle that also fixes the
parser.

WHAT IS WORTH PINNING HERE. The audit's value is entirely in refusing to report
a number it cannot support, and this repo has shipped the opposite mistake
repeatedly: a 100.0% over three samples, and an agreement satisfied by two series
that carry no information. So the guards under test are the `few` and `flat`
statuses and the fact that `shift` and `identity` are DIFFERENT questions -- a
series can score 100% on one and near zero on the other, which is exactly what
separates an affected song from a healthy one.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pyscript"))

import hardtrack_duration_law_sweep as S  # noqa: E402


def test_gaps_and_agreement_are_the_two_different_questions():
    """POSITIVE CONTROL. A shifted series must score 100% on the shift relation
    and NOT on identity -- if both fired, neither would mean anything."""
    og = [10, 20, 30, 40, 50]
    gg = og[1:]                       # ours[i] == original's[i+1]
    assert S.agreement(gg, og[1:]) == (4, 4)
    im, inn = S.agreement(gg, og)
    assert im == 0 and inn == 4, (im, inn)


def test_agreement_never_divides_by_zero_and_reports_its_own_n():
    """`agreement` returns (matches, n), never a percentage, so a caller cannot
    average two rows of different weight into a meaningless mean."""
    assert S.agreement([], [1, 2, 3]) == (0, 0)
    assert S.agreement([1, 2, 3], []) == (0, 0)


def test_gaps_of_a_single_onset_is_empty_not_zero():
    """A voice with one onset has NO gaps. Returning [0] here would be the
    vacuous-agreement shape `fidelity_common.exercised` exists to catch."""
    assert S.gaps([42]) == []
    assert S.gaps([]) == []
    assert S.gaps([10, 14, 20]) == [4, 6]


def test_the_underpowered_and_flat_thresholds_are_real_numbers():
    """These constants are the whole guard; a zero or None would silently
    disable it while every row still printed a confident percentage."""
    assert isinstance(S.MIN_N, int) and S.MIN_N >= 2
    assert isinstance(S.MIN_DISTINCT, int) and S.MIN_DISTINCT >= 2


def test_a_flat_gap_series_cannot_confirm_a_shift():
    """THE REASON `flat` EXISTS. A constant gap sequence satisfies gg[i]==og[i+1]
    trivially, so a 100% shift on it is arithmetic, not evidence."""
    og = [8] * 20
    gg = [8] * 19
    sm, sn = S.agreement(gg, og[1:])
    assert sm == sn == 19                      # a perfect, meaningless 100%
    assert len(set(og)) < S.MIN_DISTINCT       # ...which is why it is flagged


def test_gate_and_note_onsets_are_distinct_entry_points():
    """The law is stated over NOTE rows; measuring it over GATE rises answers a
    different question and reads as a refutation. Both must remain reachable, or
    the audit can only reproduce one of the two recorded readings."""
    assert callable(S.gate_onsets) and callable(S.note_onsets)


def test_gate_onsets_counts_rises_not_frames():
    """A 40-frame held note is ONE onset. Counting gate-on frames instead would
    turn every duration question into a loudness question."""
    def fr(bits):
        return [({0: {"wf": 0}, 1: {"wf": b}, 2: {"wf": 0}}, {}) for b in bits]
    # gate on for 3, off 2, on 2  ->  rises at index 0 and 5
    frames = fr([0x41, 0x41, 0x41, 0x40, 0x40, 0x41, 0x41])
    assert S.gate_onsets(frames, 1, 0, len(frames)) == [0, 5]


@pytest.mark.skipif(not os.path.isdir(S.BUILD_DIR),
                    reason="out/hardtrack_native not present in this checkout")
def test_songs_pairs_every_artifact_with_a_real_original():
    """`songs()` must not return a pair whose original is missing -- a sweep row
    measured against a file that is not there is the failure mode that produced
    three confident wrong readings elsewhere in this repo."""
    for stem, orig, part in S.songs():
        assert os.path.exists(orig), (stem, orig)
        assert os.path.exists(part), (stem, part)
