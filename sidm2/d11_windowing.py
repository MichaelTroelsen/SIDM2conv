"""Split a Driver 11 song across several modules when it will not fit one.

Driver 11's sequence pointer table holds exactly 128 entries. A Stage A builder
that hands `emit_driver11_sf2` more than that gets them TRUNCATED -- and every
orderlist entry referencing a dropped sequence removed with them, so a voice
loses arbitrary chunks of its structure while the file still parses, loads and
plays. Measured 2026-07-30: 13 of 343 SDI Stage A files and 2 Sound Monitor ones
were shipping like that (worst: `Psycho`, 101 of 229 sequences gone).

The fix is the one the native builders and `mattgray_to_sf2` already use: emit
several shorter parts instead of one truncated module. This module holds the
part-planning so every Stage A builder can share it rather than each inventing
its own.

TWO SHAPES, because Stage A builders pack differently:

* **Row-grid** (`plan_row_windows`) -- the builder has a per-voice row grid and
  packs it with `segment_track`. Cutting at a row index is automatically aligned
  across voices because all three share the grid. This is SDI's shape.
* **Aligned orderlist** (`plan_entry_windows`) -- the builder emits one sequence
  per musical bar, walking the same bar chain for every voice, so orderlist
  entry *k* is bar *k* in all three voices and cutting at an entry index is
  aligned. This is Sound Monitor's shape.

Both plan windows the same way -- grow while it fits, then binary-search the
edge -- and both COUNT WHAT A WINDOW NEEDS rather than reading a count back out
of an emitted file. That direction matters: the emitter truncates, so an emitted
module can never report more sequences than the cap however much it lost. (The
Matt Gray probe made exactly this mistake, comparing a count taken over
`range(128)` against 128 -- a test that could never fail.)
"""

from .galway_driver11_emitter import _MAX_SEQUENCES, segment_track

__all__ = ["pack_rows_window", "plan_row_windows",
           "pack_entry_window", "plan_entry_windows", "MAX_SEQUENCES"]

MAX_SEQUENCES = _MAX_SEQUENCES


def pack_rows_window(all_rows, lo, hi, dedup=True):
    """(sequences, orderlists) for rows [lo, hi) of a 3-voice row grid.

    `dedup` MUST match how the emitter will be called, or the plan is wrong:

    * ``True``  -- the caller will pass these `sequences`/`orderlists` to
      `emit_driver11_sf2`, which uses them as given. Identical sequences share a
      slot, which is what makes many songs fit at all.
    * ``False`` -- the caller will pass a bare `song` and let the emitter's own
      segmenting branch pack `song.tracks`. **That branch does not dedup**: it
      appends every packed sequence. Counting post-dedup there UNDERESTIMATES,
      so the planner reports "fits" for a song the emitter then truncates --
      exactly what happened to Galway's `Short_Circuit` (157 sequences
      undeduped, under the cap once deduped, 29 dropped).
    """
    sequences, orderlists, seq_index = [], [[], [], []], {}
    for v in range(3):
        rows = all_rows[v][lo:hi] if v < len(all_rows) else []
        for pk in segment_track(rows):
            idx = seq_index.get(pk) if dedup else None
            if idx is None:
                idx = len(sequences)
                if dedup:
                    seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)
    return sequences, orderlists


def plan_row_windows(all_rows, cap=None, dedup=True):
    """[(lo, hi), ...] row windows whose packed sequences each fit `cap`.

    Returns a single full-span window when the whole song fits, so a song that
    never needed splitting is emitted byte-identically to before. See
    `pack_rows_window` for why `dedup` must match the emitter call you intend.
    """
    cap = MAX_SEQUENCES if cap is None else cap
    total = max((len(r) for r in all_rows), default=0)
    if total == 0:
        return [(0, 0)]

    def fits(lo, hi):
        return len(pack_rows_window(all_rows, lo, hi, dedup)[0]) <= cap

    return _plan(total, fits)


def pack_entry_window(sequences, orderlists, lo, hi):
    """(sequences, orderlists) for orderlist entries [lo, hi).

    Only valid when entry *k* means the same musical position in every voice
    (see the module docstring). Sequences are renumbered densely so the part
    indexes from 0 and carries only what it uses.
    """
    out_seqs, out_ols, remap = [], [[], [], []], {}
    for v in range(3):
        entries = orderlists[v][lo:hi] if v < len(orderlists) else []
        for idx in entries:
            new = remap.get(idx)
            if new is None:
                new = len(out_seqs)
                remap[idx] = new
                out_seqs.append(sequences[idx])
            out_ols[v].append(new)
    return out_seqs, out_ols


def plan_entry_windows(sequences, orderlists, cap=None):
    """[(lo, hi), ...] orderlist-entry windows that each fit `cap`."""
    cap = MAX_SEQUENCES if cap is None else cap
    total = max((len(o) for o in orderlists), default=0)
    if total == 0:
        return [(0, 0)]

    def fits(lo, hi):
        return len(pack_entry_window(sequences, orderlists, lo, hi)[0]) <= cap

    return _plan(total, fits)


def _plan(total, fits):
    """Walk [0, total) into the longest windows for which `fits` holds.

    Grow by doubling while it fits, then binary-search the boundary -- the same
    shape as `mattgray_to_sf2`'s capacity probe, so the two behave alike.
    """
    windows, lo = [], 0
    while lo < total:
        if fits(lo, total):                       # the rest fits: done
            windows.append((lo, total))
            break
        hi, step = lo + 1, 1
        if not fits(lo, hi):
            # A single unit does not fit. Cannot be split further; emit it and
            # let the emitter's own warning report the loss rather than looping.
            windows.append((lo, hi))
            lo = hi
            continue
        while hi < total and fits(lo, min(total, hi + step)):
            hi = min(total, hi + step)
            step *= 2
        good, bad = hi, min(total, hi + max(1, step // 2))
        while bad > good + 1:
            mid = (good + bad) // 2
            if fits(lo, mid):
                good = mid
            else:
                bad = mid
        windows.append((lo, good))
        lo = good
    return windows or [(0, total)]
