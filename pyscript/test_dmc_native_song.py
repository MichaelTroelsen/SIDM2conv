"""The DMC native shim's contract with the shared builder.

`build_native_song` places event k at tick `sum(dur[:k])` — the timeline is
implied by the durations, and nothing else records where a voice starts. DMC's
shim emits durations as onset-to-onset GAPS, so a voice whose first onset is at
frame N is placed N frames early for the entire song unless a leading rest
restores the origin.

That bug shipped: `Billie_Jean`'s first onsets are `[2, 0, 962]` and all three
voices began at tick 0. Voice 1 (first onset 0) scored 100.0 and set the global
boot-offset fit, so the other two read as broken content — voice 0 at
63.3/50.1/81.2 where its notes were exact. Voice 2's 962-frame shift measured as
the same −2 as voice 0, because that voice's phrase is periodic at 96 frames and
962 = 10×96 + 2; no per-frame column and no delta histogram can see a shift of a
whole number of phrase-lengths. Only the absolute onset list can.

HardTrack met the same contract first and pinned it in
`test_hardtrack_native.py::test_event_timeline_is_contiguous_from_tick_zero`.
The contract belongs to the shared builder, so the pin should have travelled;
this file is it travelling. See `PATTERNS.md` F11.

No siddump, no assembler, no build — the shim is constructed directly from the
parsed module with a synthetic onset list.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORP = os.path.join(ROOT, "SID", "JohannesBjerregaard")

pytestmark = pytest.mark.skipif(not os.path.isdir(CORP),
                                reason="Bjerregaard corpus absent")


@pytest.fixture(scope="module")
def B():
    """Import the builder as a module. It reads `sys.argv` at import time for the
    SID path, which pytest's argv would poison — so hand it a real one."""
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "bin"))
    saved = sys.argv
    sys.argv = ["build_dmc_native_song.py",
                os.path.join(CORP, "Balloon.sid"), "10"]
    try:
        spec = importlib.util.spec_from_file_location(
            "build_dmc_native_song",
            os.path.join(ROOT, "bin", "build_dmc_native_song.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.argv = saved


@pytest.fixture(scope="module")
def module():
    from sidm2.dmc_parser import load_sid, DMCModule
    d, la, _h = load_sid(os.path.join(CORP, "Balloon.sid"))
    return DMCModule(d, la)


def shim(B, module, onsets, **env):
    """A shim over a synthetic onset list. `DMC_GRID=0` keeps fpt at 1 so a tick
    IS a frame and the assertions read as frames; the grid path is exercised
    separately below."""
    old = {k: os.environ.get(k) for k in ("DMC_GRID", "DMC_LEAD_REST")}
    os.environ["DMC_GRID"] = "0"
    os.environ.update({k: v for k, v in env.items()})
    try:
        return B.DMCShim(module, 0, budget_ticks=4000, onsets=onsets,
                         frames=None, legato_set=frozenset())
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def start_frames(sh):
    """Absolute frame each voice's first NOTE lands on, the way
    `build_native_song` computes it: `tick_to_frame(sum of the durations ahead
    of it) + onset_delay`. The delay term is 0 at fpt=1 and non-zero in grid
    mode, where the whole timeline is offset by the onsets' shared residue."""
    out = []
    for v in range(3):
        tk = 0
        for e in sh.voices[v]:
            if not getattr(e, "rest", False):
                break
            tk += e.dur
        out.append(sh.tick_to_frame(tk) + sh.onset_delay)
    return out


def test_a_late_entering_voice_starts_where_its_first_onset_is(B, module):
    """THE DEFECT, in the shape it shipped: Billie_Jean's `[2, 0, 962]`."""
    sh = shim(B, module, [[2, 14, 26], [0, 194, 206], [962, 998, 1058]])
    assert start_frames(sh) == [2, 0, 962]


def test_the_old_behaviour_played_every_late_voice_from_frame_zero(B, module):
    """Same input with the A/B switch — so the regression is pinned from both
    sides rather than only described."""
    sh = shim(B, module, [[2, 14, 26], [0, 194, 206], [962, 998, 1058]],
              DMC_LEAD_REST="0")
    assert start_frames(sh) == [0, 0, 0]


def test_a_voice_that_starts_at_frame_zero_gets_no_leading_rest(B, module):
    """The rest must be conditional: an unconditional one would push every voice
    that IS at the origin one event later."""
    sh = shim(B, module, [[0, 10], [0, 10], [0, 10]])
    for v in range(3):
        assert not getattr(sh.voices[v][0], "rest", False)
    assert start_frames(sh) == [0, 0, 0]


def test_the_rest_does_not_disturb_the_gaps_after_it(B, module):
    """The durations following the rest are still onset-to-onset gaps — the fix
    adds an origin, it does not re-time anything."""
    sh = shim(B, module, [[5, 15, 40], [0, 10], [0, 10]])
    notes = [e for e in sh.voices[0] if not getattr(e, "rest", False)]
    assert [e.dur for e in notes[:2]] == [10, 25]


def test_it_holds_in_STEP_GRID_mode_too(B, module):
    """When every gate onset shares one residue mod `fpt*mult` the shim runs on
    that grid instead of per-frame, and the durations become grid ticks. The
    origin still has to be recorded -- in ticks now, with the shared residue
    carried in `onset_delay`."""
    ofpt = module.lay.tempo_reload + 1
    ons = [[ofpt * k + 1 for k in (8, 12, 16)],
           [ofpt * k + 1 for k in (0, 4, 8)],
           [ofpt * k + 1 for k in (40, 44, 48)]]
    old = os.environ.pop("DMC_GRID", None)
    try:
        sh = B.DMCShim(module, 0, budget_ticks=4000, onsets=ons, frames=None,
                       legato_set=frozenset())
    finally:
        if old is not None:
            os.environ["DMC_GRID"] = old
    assert sh.frames_per_tick > 1, "this input should have selected the grid"
    assert start_frames(sh) == [ons[0][0], ons[1][0], ons[2][0]]


def test_every_voice_is_contiguous_from_tick_zero(B, module):
    """The shared builder's actual contract (HardTrack's wording): durations
    must tile the timeline with no gap and no overlap, for every voice."""
    sh = shim(B, module, [[2, 14, 26], [0, 194, 206], [962, 998, 1058]])
    for v in range(3):
        assert sh.voices[v], f"voice {v} has no events"
        for e in sh.voices[v]:
            assert e.dur >= 1


# --- the $40-$43 SCALED-marker collision, decided per SONG -------------------
# These pin the IDENTITY the scan relies on, not any particular song: for k >= 2
# a note's FM delta is freq[k]-freq[k-1] with the base cancelled, so scanning
# consecutive frames covers every within-note delta under ANY segmentation.

def _bmns():
    import importlib.util
    sys.path.insert(0, ROOT)
    spec = importlib.util.spec_from_file_location(
        "bmns_fm", os.path.join(ROOT, "bin", "build_mon_native_song.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bmns_fm"] = mod
    spec.loader.exec_module(mod)
    return mod


class _M:
    """Minimum surface _fm_would_collide touches."""
    def __init__(self, notes=()):
        self.voices = [list(notes), [], []]
    def tick_to_frame(self, t):
        return t
    def note_freq(self, n):
        return 0x1000


class _Ev:
    def __init__(self, note=48, dur=8, rest=False):
        self.note, self.dur, self.rest = note, dur, rest


def _frames(v0):
    return [({0: {"freq": f}, 1: {"freq": None}, 2: {"freq": None}},)
            for f in v0]


def test_a_delta_inside_the_marker_range_is_detected():
    """A jump of +$41C1 is DMC Balloon's two-octave arp, the documented case."""
    B = _bmns()
    assert B._fm_would_collide(_M(), _frames([0x1000, 0x1000 + 0x41C1])) is True


def test_a_song_whose_deltas_stay_clear_does_not_collide():
    B = _bmns()
    assert B._fm_would_collide(_M(), _frames([0x1000, 0x1010, 0x1020])) is False


def test_the_base_cancels_so_segmentation_cannot_hide_a_collision():
    """The scan never sees the note boundaries, and must not need to: the same
    frame series collides identically however it is cut into notes."""
    B = _bmns()
    series = _frames([0x1000, 0x1000 + 0x4200, 0x1000])
    for cut in ([], [_Ev(dur=1)], [_Ev(dur=1), _Ev(dur=1), _Ev(dur=1)]):
        assert B._fm_would_collide(_M(cut), series) is True, cut


def test_a_siddump_gap_holds_rather_than_faking_a_delta():
    """`fm_program_for` HOLDS the last value across a None, so the delta is 0 --
    a naive None-to-int subtraction would invent a huge one."""
    B = _bmns()
    assert B._fm_would_collide(_M(), _frames([0x1000, None, 0x1010])) is False


# --- the build lock's Windows failure mode ----------------------------------

def test_the_build_lock_retries_a_pending_delete_not_just_an_existing_file():
    """On Windows a lock file whose last handle closed but which is still
    PENDING DELETION answers O_CREAT|O_EXCL with ERROR_ACCESS_DENIED, not
    "exists". Catching only FileExistsError let that escape and kill one song's
    build in a -j16 sweep, and the sweep carried on with a quietly smaller
    denominator (207 voices instead of 210) which read as "AUTO builds one more
    song". An 8-process stress showed 78 escapes before the fix and 0 after.
    """
    B = _bmns()
    os.environ["MON_BUILD_LOCK"] = "1"
    real_open, calls = os.open, {"n": 0}

    def flaky(path, *a, **kw):
        if path == B._BUILD_LOCK:
            calls["n"] += 1
            if calls["n"] == 1:                  # first attempt: pending delete
                raise PermissionError(13, "Permission denied", path)
        return real_open(path, *a, **kw)

    os.open = flaky
    try:
        with B._build_lock(timeout=5):
            pass                                  # must not raise
    finally:
        os.open = real_open
        os.environ.pop("MON_BUILD_LOCK", None)
        try:
            os.remove(B._BUILD_LOCK)
        except OSError:
            pass
    assert calls["n"] >= 2, "the PermissionError should have been retried"
