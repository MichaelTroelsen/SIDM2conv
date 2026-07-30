"""Tests for Driver 11 part planning (`sidm2.d11_windowing`).

The property under test is the one that was violated in production: a song too
big for the 128-entry sequence pointer table must be SPLIT, never silently
truncated -- and a song that already fits must be untouched, so the fix cannot
churn the 300+ files that were fine.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.d11_windowing import (  # noqa: E402
    MAX_SEQUENCES, pack_entry_window, pack_rows_window, plan_entry_windows,
    plan_row_windows)
from sidm2.galway_to_driver11 import D11Row, SF2_GATE_OFF  # noqa: E402


def _rows(n, seed=0):
    """n rows whose content does not repeat, so segment_track cannot dedup it.

    A short repeating motif (say note = i % 24) collapses to a handful of unique
    sequences however long the song is -- dedup is that effective -- so a naive
    generator produces a grid that always fits one module and quietly tests
    nothing. Scramble the note so successive chunks genuinely differ.
    """
    return [D11Row(note=(0x30 + (((i + seed) * 2654435761) >> 16) % 60
                         if i % 2 else SF2_GATE_OFF))
            for i in range(n)]


# --------------------------------------------------------------------------
# Row-grid windows (SDI's shape)
# --------------------------------------------------------------------------

def test_short_song_is_one_window_spanning_everything():
    grid = [_rows(40), _rows(40, 1), _rows(40, 2)]
    assert plan_row_windows(grid) == [(0, 40)]


def test_every_window_fits_the_cap():
    grid = [_rows(6000), _rows(6000, 7), _rows(6000, 13)]
    windows = plan_row_windows(grid)
    assert len(windows) > 1, "this grid must not fit one module"
    for lo, hi in windows:
        seqs, _ = pack_rows_window(grid, lo, hi)
        assert len(seqs) <= MAX_SEQUENCES, f"window {lo}-{hi} overflows"


def test_windows_are_contiguous_and_cover_the_whole_song():
    """The split must lose nothing -- that is the entire point."""
    grid = [_rows(6000), _rows(6000, 7), _rows(6000, 13)]
    windows = plan_row_windows(grid)
    assert windows[0][0] == 0
    assert windows[-1][1] == 6000
    for (_, prev_hi), (next_lo, _) in zip(windows, windows[1:]):
        assert prev_hi == next_lo, "windows must not overlap or leave a gap"


def test_all_voices_are_cut_at_the_same_row():
    """Voices share the row grid, so one (lo, hi) cuts all three together --
    this is what keeps them in sync; a per-voice cut would desync the song."""
    grid = [_rows(3000), _rows(3000, 5), _rows(3000, 9)]
    for lo, hi in plan_row_windows(grid):
        _seqs, ols = pack_rows_window(grid, lo, hi)
        assert all(ols[v] for v in range(3)), "each voice needs its own entries"


def test_dedup_is_counted_so_repetitive_songs_are_not_over_split():
    """Sequences are deduplicated across voices; a planner counting before
    dedup would split songs that comfortably fit."""
    one = _rows(2000)
    grid = [list(one), list(one), list(one)]      # three identical voices
    seqs, ols = pack_rows_window(grid, 0, 2000)
    assert len(seqs) < sum(len(o) for o in ols), "identical voices must dedup"


def test_empty_grid_does_not_hang_or_raise():
    assert plan_row_windows([[], [], []]) == [(0, 0)]


def test_dedup_false_counts_the_way_the_segmenting_emitter_does():
    """`dedup` must match how the emitter will be called.

    `emit_driver11_sf2(song)` (no explicit sequences) packs `song.tracks` in its
    own segmenting branch, which does NOT deduplicate -- it appends every packed
    sequence. Planning with dedup=True there underestimates, so the planner says
    "fits" and the emitter then truncates. That is exactly how Galway's
    Short_Circuit kept losing 29 sequences after the first fix attempt.
    """
    one = _rows(2000)
    grid = [list(one), list(one), list(one)]      # three identical voices
    deduped, _ = pack_rows_window(grid, 0, 2000, dedup=True)
    raw, raw_ols = pack_rows_window(grid, 0, 2000, dedup=False)
    assert len(raw) > len(deduped), "dedup=False must not collapse duplicates"
    assert len(raw) == sum(len(o) for o in raw_ols), \
        "undeduped count must equal one sequence per orderlist entry"


def test_dedup_false_plans_more_parts_than_dedup_true():
    grid = [_rows(9000), _rows(9000, 3), _rows(9000, 11)]
    assert len(plan_row_windows(grid, dedup=False)) >= \
        len(plan_row_windows(grid, dedup=True))


# --------------------------------------------------------------------------
# Orderlist-entry windows (Sound Monitor's shape)
# --------------------------------------------------------------------------

def test_entry_windows_fit_and_cover():
    seqs = [bytes([0x30 + (i % 60), 0x7F]) for i in range(300)]
    ols = [list(range(0, 100)), list(range(100, 200)), list(range(200, 300))]
    windows = plan_entry_windows(seqs, ols)
    assert len(windows) > 1
    assert windows[0][0] == 0 and windows[-1][1] == 100
    for lo, hi in windows:
        part_seqs, _ = pack_entry_window(seqs, ols, lo, hi)
        assert len(part_seqs) <= MAX_SEQUENCES


def test_entry_window_renumbers_sequences_densely():
    """A part must carry only the sequences it uses, indexed from 0 -- an
    index left pointing at the parent song's numbering would read the wrong
    sequence (or past the table)."""
    seqs = [bytes([i, 0x7F]) for i in range(10)]
    ols = [[5, 6], [7, 8], [9, 5]]
    part_seqs, part_ols = pack_entry_window(seqs, ols, 0, 2)
    assert len(part_seqs) == 5                      # 5,6,7,8,9
    for v in range(3):
        for idx in part_ols[v]:
            assert 0 <= idx < len(part_seqs)
    # the repeat of sequence 5 in voice 3 maps to the same new index
    assert part_ols[0][0] == part_ols[2][1]


def test_entry_windows_preserve_playing_order():
    seqs = [bytes([i & 0x7F, 0x7F]) for i in range(200)]
    ols = [list(range(200)), list(range(200)), list(range(200))]
    rebuilt = []
    for lo, hi in plan_entry_windows(seqs, ols):
        part_seqs, part_ols = pack_entry_window(seqs, ols, lo, hi)
        rebuilt.extend(part_seqs[i] for i in part_ols[0])
    assert rebuilt == [seqs[i] for i in ols[0]], "order must survive the split"
