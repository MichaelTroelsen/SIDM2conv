"""The passband check's own logic, on synthetic frames -- no siddump, no builds.

The defect this guards was invisible for as long as it existed because the
document quoted the BUILDER and nothing measured the ARTIFACT: 21 of 33 shipped
HardTrack builds rendered low-pass where their originals select low+band,
band+high, or modulate between modes up to 87 times, while `HARDTRACK.md` said
`$D418` was 100.00% byte-exact -- which was true of `build_hardtrack_native_song.py`
and false of every file it had not been re-run over.

Two failure shapes have to stay distinguishable, because a plain equality test
against a static side scores them the same:

  A. both sides constant, different constants  (LP vs LP+BP -- a permanent
     timbre offset on every frame)
  B. original modulates, ours is constant      (agreement can still look high
     if the original spends most frames on the mode we happen to hold)

`Hopscotch` was shape B at 87.2% agreement. A 99%-threshold catches it; a
"do the sets of modes used overlap?" test would not.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import passband_check as pb  # noqa: E402


def frames(vals):
    """siddump_frames_full-shaped: (voices, filter) per frame. Index 0 is the
    force-displayed row the module must drop."""
    return [({}, {"volmode": v}) for v in vals]


def test_frame_zero_is_dropped():
    """siddump force-displays every register on frame 0 whether the playroutine
    wrote it or not -- counting it would invent a mode change at the start."""
    assert pb.mode_sequence(frames([0x6F, 0x1F, 0x1F])) == [0x10, 0x10]


def test_only_the_passband_bits_are_compared():
    """Low nibble is master VOLUME. A volume difference is audible as level, not
    timbre; pooling them lets one mask the other."""
    assert pb.mode_sequence(frames([0x00, 0x1F, 0x10, 0x1A])) == [0x10] * 3


def test_absent_register_is_not_agreement():
    """`score_pct`'s rule: an unmeasured comparison is None, never 100.0."""
    assert pb.mode_sequence(frames([0x1F, None, None])) == []
    pct, n, _oc, _dc, _off, _aud = pb.compare([], [0x10])
    assert pct is None and n == 0
    pct, _n, _oc, _dc, _off, _aud = pb.compare([0x10], [])
    assert pct is None


def test_shape_A_constant_but_different():
    """Altered_States_Tune_1 as shipped: original LP+BP, ours LP, every frame."""
    pct, n, oc, dc, _off, _aud = pb.compare([0x30] * 100, [0x10] * 100)
    assert pct == 0.0 and n == 100
    assert oc == 0 and dc == 0, "neither side modulates -- the tell is the value"


def test_shape_B_original_modulates_ours_is_static():
    """Hopscotch as shipped: the original leaves LP for BP+HP on some frames and
    ours never does. Agreement stays HIGH because the original spends most of
    its time on the mode we hold -- the change counts are what expose it."""
    orig = [0x10] * 80 + [0x60] * 13 + [0x10] * 7   # leaves LP and comes back
    pct, _n, oc, dc, _off, _aud = pb.compare(orig, [0x10] * 100)
    assert pct == 87.0, "87 of 100 frames still match -- high, and still broken"
    assert oc == 2 and dc == 0, "one departure and one return = 2 changes"


def test_a_correct_build_agrees():
    orig = [0x10] * 50 + [0x60] * 50
    pct, n, oc, dc, off, _aud = pb.compare(orig, list(orig))
    assert pct == 100.0 and n == 100 and oc == dc == 1 and off == 0


def test_describe_names_every_mode_present():
    names, changes = pb.describe([0x10, 0x30, 0x60, 0x10])
    assert names == ["LP", "LP+BP", "BP+HP"]
    assert changes == 3


def test_overlap_is_the_shorter_side():
    """Parts differ in length between the two sides; scoring past the end of one
    would compare against nothing."""
    pct, n, _oc, _dc, _off, _aud = pb.compare([0x10] * 10, [0x10] * 4)
    assert n == 4 and pct == 100.0


def test_a_boot_offset_is_fitted_not_assumed():
    """The native driver boots a few frames late. Comparing frame i to frame i
    made a KNOWN constant delay read as a passband defect on every tune that
    MODULATES -- and only on those, since a static mode is immune to shifting,
    which is why the flaw survived the check's first run against real builds."""
    orig = [0x10] * 40 + [0x60] * 20 + [0x10] * 40
    late = [0x10] * 3 + orig[:-3]           # same programme, 3 frames late
    pct, _n, oc, dc, off, _aud = pb.compare(orig, late)
    assert pct == 100.0, "a pure delay is not a wrong passband"
    assert off == 3 and oc == dc == 2


def test_the_fitted_offset_is_reported():
    """A large offset is itself a finding -- right band, arriving late -- and a
    different defect from selecting the wrong band. It must not be absorbed."""
    orig = [0x10] * 50 + [0x60] * 50
    _pct, _n, _oc, _dc, off, _aud = pb.compare(orig, [0x10] * 6 + orig[:-6])
    assert off == 6


def test_a_tie_keeps_the_unshifted_reading():
    """Two constants that agree nowhere agree nowhere at every offset. Picking
    a shifted one would quietly shrink n."""
    pct, n, _oc, _dc, off, _aud = pb.compare([0x30] * 100, [0x10] * 100)
    assert pct == 0.0 and n == 100 and off == 0


def test_the_fit_cannot_manufacture_agreement():
    """Guard against the obvious abuse: a wide enough search will align almost
    anything. Two unrelated programmes must not reach agreement by shifting."""
    orig = [0x10] * 25 + [0x60] * 25 + [0x10] * 25 + [0x60] * 25
    ours = [0x40] * 100
    pct, _n, _oc, _dc, _off, _aud = pb.compare(orig, ours)
    assert pct == 0.0


def test_a_modulating_original_does_not_condemn_a_100pct_build():
    """`Alf_TV_Theme`, `Dragon_Sword` and `Slimbo4` were reported broken at
    100.0% agreement. The original's only "mode change" is its initial
    off -> LP+BP transition; our build starts already on LP+BP and matches every
    frame that exists. Modulation-count is a LABEL for a failure, never a
    trigger for one -- a genuinely static build against a modulating original
    cannot reach the gate anyway (`Hopscotch` sat at 87.2%)."""
    orig = [0x00] + [0x30] * 99
    ours = [0x30] * 100
    pct, _n, oc, dc, _off, _aud = pb.compare(orig, ours)
    assert oc == 1 and dc == 0, "the shape that used to trigger the false flag"
    assert pct >= 99.0, "yet it agrees on all but the one power-on frame"


def test_routing_fraction_reads_the_low_nibble_of_D417():
    """`$D417` low nibble = which VOICES feed the filter. The high nibble is
    resonance and must not be mistaken for routing."""
    fr = [({}, {"filtctl": 0xF0})] + [({}, {"filtctl": 0xF0})] * 9
    assert pb.routed_fraction(fr) == 0.0, "resonance alone routes nothing"
    fr = [({}, {"filtctl": 0x00})] + [({}, {"filtctl": 0x01})] * 4 + [({}, {"filtctl": 0x00})] * 4
    assert pb.routed_fraction(fr) == 0.5
    assert pb.routed_fraction([({}, {"filtctl": None})] * 4) is None


def test_an_unrouted_filter_makes_the_passband_inaudible():
    """`Eagles`, `In_the_Mood`, `Roadblaster`: cutoff 0, `$D417` $00, `$D418`
    mode 001/011 against our 000 on every frame. The register claim is true and
    the severity is nil -- with nothing fed into the filter the passband bits
    select among three silent outputs. The check called these failures three
    separate times before this was noticed."""
    fr = [({}, {"filtctl": 0x00})] * 10
    assert pb.routed_fraction(fr) == 0.0
    # The mode comparison itself still reports the difference honestly.
    pct, _n, _oc, _dc, _off, _aud = pb.compare([0x10] * 9, [0x00] * 9)
    assert pct == 0.0, "the difference is still measured, just not counted"


def test_every_player_whose_builder_was_fixed_is_checkable():
    """The defect is not per-player, it is per-ARTIFACT-SET, and it has now
    appeared three times: HardTrack 21 of 33 wrong, DMC 26 of 57, MoN 8 of 19.
    Each time a session fixed the builder and left the output, and each time the
    player doc quoted the builder. A player whose builder got `passband_trace`
    but has no entry here cannot be checked at all."""
    for player in ("hardtrack", "dmc", "mon"):
        assert player in pb.PLAYERS
        cfg = pb.PLAYERS[player]
        assert cfg["suffix"].endswith((".sf2", ".sid"))
        assert cfg["origs"], "an empty origs glob silently finds no originals"


def test_a_dead_reference_trace_is_refused_not_compared():
    """Adding Blackbird produced, in order: "16/16 pass", then "16 files where
    the original never routes a voice", then a measurement that our builds route
    the filter on 56-100% of frames where the original routes 0% -- which reads
    as a real audible defect and is not one. `SID/LFT/*.sid` produce NO trace
    under siddump: no frequency, no waveform, and `$D418` = 0 (volume zero) for
    every frame. Three labels deep before anyone asked whether the reference was
    playing.

    This repo already had the rule: the `zig64-gate-false-pass` fix was "assert
    evidence exists before comparing", after a gate certified unverified SF2s by
    comparing empty against empty."""
    dead = [({vi: {"freq": 0, "wf": 0, "pul": 0} for vi in range(3)},
             {"volmode": 0x00, "filtctl": 0x00, "cutoff": 0})] * 50
    assert pb.has_evidence(dead) is False

    live = list(dead)
    live[10] = ({0: {"freq": 0x1234, "wf": 0x41, "pul": 0},
                 1: {"freq": 0, "wf": 0, "pul": 0},
                 2: {"freq": 0, "wf": 0, "pul": 0}},
                {"volmode": 0x1F, "filtctl": 0x00, "cutoff": 0})
    assert pb.has_evidence(live) is True, "one sounded voice is enough"


def test_a_silent_tune_and_an_undriveable_file_look_identical():
    """Which is exactly why the gate is on evidence rather than on the filter
    registers: a full-length series of zeroes is byte-identical to 'this tune
    never filters' and to 'siddump could not drive this file'."""
    zeros = [({vi: {"freq": 0, "wf": 0, "pul": 0} for vi in range(3)},
              {"volmode": 0x00, "filtctl": 0x00, "cutoff": 0})] * 30
    assert pb.mode_sequence(zeros) == [0x00] * 29, "reads as a valid 'off'"
    assert pb.routed_fraction(zeros) == 0.0, "reads as a valid 'routes nothing'"
    assert pb.has_evidence(zeros) is False, "only this distinguishes them"


def test_a_multipart_failure_is_unconfirmed_without_an_asserted_window():
    """The window flaw, third occurrence in one session and second tool. The
    check compared part 1 against a fixed 28 s for every file; HardTrack part 1s
    are 6-12 s and DMC's `Domino_Dancing` is 12 s. Past its end our part LOOPS,
    so the comparison ran our restarted part against the original's continuing
    music and counted the difference as a defect:

        Something_to_Eat   68.7% -> 100.0% at its real 10 s   (31 changes vs 31)
        Illmatic_end       71.1% -> 100.0% at 6 s             (8 vs 8)
        Domino_Dancing     99.0% -> 100.0% at 12 s            (1 vs 1)

    Over-running can only MANUFACTURE disagreement, never hide it, so passes
    need no such caveat -- a file that matched across a too-long window matched
    everywhere it was compared. Only failures are downgraded."""
    orig = [0x10] * 500                       # the original keeps going
    ours = ([0x10] * 250) + ([0x60] * 250)    # our part loops and diverges
    pct, _n, _oc, _dc, _off, _aud = pb.compare(orig, ours)
    assert pct < 99.0, "the raw comparison sees a mismatch"
    # ...which is exactly the shape that must not be published as a defect
    # without knowing where part 1 ended.


def test_blackbird_uses_the_simulator_as_its_reference():
    """siddump cannot drive an LFT rip, which left the one player whose docs
    describe a per-frame `$D418` rewrite unmeasurable -- and produced three
    confident wrong readings before `has_evidence` stopped them.
    `bin/blackbird_everyframe_sim.py` is the reference BLACKBIRD.md validates
    against and models `$D418` directly (`self.w(24, self.filttable(y))`).
    Against it, all 16 builds score 100.0%."""
    assert pb.PLAYERS["blackbird"]["ref"] == "sim"
    assert os.path.exists(os.path.join(
        pb.ROOT, "bin", "blackbird_everyframe_sim.py"))


def test_the_simulator_reference_has_siddumps_shape():
    """Returned in `siddump_frames_full`'s shape on purpose, so
    `mode_sequence`, `routed_fraction` and `has_evidence` all work unchanged. A
    second comparison path is how the two sides of a metric drift apart."""
    orig = os.path.join(pb.ROOT, "SID", "LFT", "Fargo.sid")
    if not os.path.exists(orig):
        return
    fr = pb.sim_reference(orig, 1)
    assert len(fr) == 50
    voices, glob_ = fr[0]
    assert set(voices) == {0, 1, 2}
    assert {"freq", "wf", "pul"} <= set(voices[0])
    assert {"cutoff", "filtctl", "volmode"} <= set(glob_)
    assert pb.has_evidence(fr) is True, "the simulator drives it where siddump cannot"


def test_routing_is_scored_on_the_MISMATCHING_frames():
    """`Altered_States_Tune_2` was the last HardTrack residual, reported at
    93.4% "routed 80%" -- which reads as a defect you can hear. All 47 of its
    mismatched frames are frames where the ORIGINAL routes nothing: it holds
    `$D417 = 0` for the first 50 frames while selecting LP, our build reads
    `off` across exactly that stretch, and from the moment a voice is actually
    fed to the filter the two agree.

    A GLOBAL routed fraction cannot see that -- it answers "does this tune use
    the filter at all" when the question is "does it use the filter WHERE WE
    DISAGREE". The unrouted-severity rule already existed; it ran over the wrong
    frames, which is why it caught three all-unrouted DMC files and missed this
    one."""
    orig = [0x10] * 100
    ours = [0x00] * 40 + [0x10] * 60        # wrong for the first 40 frames
    routed = [0] * 40 + [1] * 60            # ...which are exactly the unrouted ones
    pct, _n, _oc, _dc, _off, audible = pb.compare(orig, ours, routed_seq=routed)
    assert pct < 99.0, "the raw agreement is genuinely poor"
    assert audible == 0, "and none of it can be heard"


def test_a_mismatch_on_a_ROUTED_frame_still_counts():
    """The guard must not swallow a real defect: same shape, but the original
    feeds the filter throughout.

    The wrong stretch sits in the MIDDLE on purpose. Put it at the start and the
    offset fitter legitimately absorbs up to 8 frames of it (a leading defect is
    indistinguishable from a late boot), which is the tool working -- but it
    makes the count depend on the search range rather than on the defect."""
    orig = [0x10] * 100
    ours = [0x10] * 40 + [0x00] * 20 + [0x10] * 40
    pct, _n, _oc, _dc, _off, audible = pb.compare(orig, ours, routed_seq=[1] * 100)
    assert pct < 99.0
    assert audible == 20, "every mismatching frame is routed, so every one counts"


def test_audible_is_None_when_routing_was_not_supplied():
    """Absent, not zero -- a caller with no routing data must not be told the
    mismatches are inaudible."""
    _pct, _n, _oc, _dc, _off, audible = pb.compare([0x10] * 10, [0x00] * 10)
    assert audible is None


# --- the variant-V reference -----------------------------------------------
#
# `Filthy_Hit_VE-4x` read 0.0% over 1,387 audible frames against siddump, and it
# was not a build defect. The V wrapper declares `play=$0000` and installs its
# own IRQ at `v_mult` calls per frame; siddump calls the player ONCE per frame,
# so on a tune that alternates its passband WITHIN the frame the two sample
# different instants. Measured on that file over 400 frames:
#
#     py65 mult=1 : off x6,  BP x384, LP x10     <- reproduces siddump
#     py65 mult=4 : off x1,  BP x96,  LP x303    <- the tune's real rate
#     siddump     : off x25, BP x375
#
# Driving the module at its real rate is the only reference that can adjudicate
# a V build, and it is the same trace the builder captures from. These tests pin
# the wiring, not the numbers -- the numbers need a build.


def test_sdi_declares_a_per_file_reference():
    """`sdi_v` must be per FILE. Making it per player would swap the reference
    for all 281 SDI builds to fix 5, and the other five variants are driven
    perfectly well by siddump."""
    assert pb.PLAYERS["sdi"].get("ref") == "sdi_v"
    assert hasattr(pb, "sdi_v_reference")


def test_the_v_reference_declines_a_non_v_file():
    """It returns None for anything that is not variant V, so the caller falls
    back to siddump. A reference that answered for every SDI file would be a
    silent corpus-wide change dressed as a four-file fix."""
    import inspect
    src = inspect.getsource(pb.sdi_v_reference)
    assert 'variant' in src and 'return None' in src


def test_the_v_reference_reconstructs_the_passband_in_d418_position():
    """`v_traces` records $D418's mode bits already shifted DOWN, and
    `mode_sequence` masks `& 0x70`. Handing the shifted-down value through
    unshifted would read every BP as `off` and score a confident 0%."""
    import inspect
    src = inspect.getsource(pb.sdi_v_reference)
    assert '<< 4' in src, "the passband must be put back in bits 4-6"


def test_a_v_style_within_frame_alternation_is_not_scored_as_agreement():
    """The shape the two references disagree about: a tune whose passband
    alternates frame to frame against one that holds a single mode. Whichever is
    right, they are not the same sequence and must not read as one."""
    alternating = [0x20 if i % 2 else 0x10 for i in range(100)]
    static = [0x20] * 100
    pct, _n, oc, dc, _off, _aud = pb.compare(alternating, static,
                                             routed_seq=[1] * 100)
    assert pct is not None and pct < 60.0
    assert oc > dc == 0, "the original modulates and ours does not"


# --- the part-1 span sidecar -----------------------------------------------
#
# The span was always known and always thrown away: every native builder labels
# each part `part N/M (A-Bs)` and PRINTS it. Nothing wrote it down, so this check
# had to report 41 multi-part builds UNCONFIRMED and ask a human for 41 numbers
# the build had already computed. `emit_one` now drops a `.span` beside each
# artifact and `part_span` reads it.


def test_the_window_may_only_narrow():
    """A recorded span narrows; it must NEVER widen past --seconds.

    Over-run is the error the whole guard exists for -- past a part's end our
    build LOOPS against the original's continuing music -- and it produced five
    retracted readings in three tools in one session. Narrowing can only remove
    manufactured disagreement; widening can only create it."""
    assert pb.window_for(12, 28) == (12, True)      # narrower span wins
    assert pb.window_for(60, 28) == (28, False)     # longer span is IGNORED
    assert pb.window_for(28, 28) == (28, False)     # equal is not "derived"


def test_no_span_means_the_global_window():
    """Absent is not zero. An artifact built before the sidecar existed must
    fall back and stay UNCONFIRMED, not silently adopt a default."""
    assert pb.window_for(None, 28) == (28, False)
    assert pb.window_for(0, 28) == (28, False)


def test_part_span_reads_the_sidecar(tmp_path):
    b = tmp_path / "Song_part01.sf2"
    b.write_bytes(b"")
    (tmp_path / "Song_part01.sf2.span").write_text("0 6\n")
    assert pb.part_span(str(b)) == 6


def test_part_span_refuses_a_degenerate_or_missing_sidecar(tmp_path):
    """A zero-length or unparsable span is NO span. Returning 0 would read as
    'compare nothing' and score a confident, empty agreement."""
    b = tmp_path / "Song_part01.sf2"
    b.write_bytes(b"")
    assert pb.part_span(str(b)) is None          # no sidecar at all
    (tmp_path / "Song_part01.sf2.span").write_text("6 6\n")
    assert pb.part_span(str(b)) is None          # t1 == t0
    (tmp_path / "Song_part01.sf2.span").write_text("garbage\n")
    assert pb.part_span(str(b)) is None


def test_the_emitter_writes_a_span_only_for_a_windowed_label(tmp_path):
    """Single-window builders label their output `<base> 0-28s` with no `part
    N/M`, and they must produce NO sidecar -- a span nobody established is worse
    than none, because the reader would believe it."""
    sys.path.insert(0, os.path.join(ROOT, "bin"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bmns", os.path.join(ROOT, "bin", "build_mon_native_song.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bmns"] = mod
    spec.loader.exec_module(mod)

    out = str(tmp_path / "x.sf2")
    mod._write_span(out, "part 1/2 (0-6s) SDI Stage B")
    assert open(out + ".span").read().split() == ["0", "6"]

    out2 = str(tmp_path / "y.sf2")
    mod._write_span(out2, "Commando 0-28s")
    assert not os.path.exists(out2 + ".span")


def test_the_span_regex_matches_every_builders_label():
    """One regex has to cover SDI, HardTrack, DMC, FC, MattGray, MoN and Myth,
    whose labels differ after the window."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bmns2", os.path.join(ROOT, "bin", "build_mon_native_song.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bmns2"] = mod
    spec.loader.exec_module(mod)
    for label, want in (
            ("part 1/2 (0-6s) SDI Stage B", ("0", "6")),
            ("part 3/6 (58-80s, 2900-4000f)", ("58", "80")),
            ("part 1/4 (0-28s)", ("0", "28")),
    ):
        m = mod._SPAN_RE.search(label)
        assert m and (m.group(3), m.group(4)) == want, label


def test_a_shift_that_repairs_nothing_cannot_win_the_offset_fit():
    """The fit maximises the match COUNT, not the rate.

    Reproduces DMC Soap_Theme exactly: the original holds one constant mode for
    the whole window, ours sits on `off` for a 19-frame startup transient and
    then matches forever. `_agree_at` trims the TAIL, so every positive offset
    removes matching frames from `n` while repairing an equal number at the
    head -- `ok` is algebraically FLAT and the rate climbs for free. Fitting on
    the rate returned max(OFFSETS) and inflated 98.537% to 99.148%, which
    carried the file over the --min 99.0 gate.
    """
    N = 1299
    TRANSIENT = 19
    orig = [0x30] * N                                   # LP+BP from INIT, never changes
    ours = [0x00] * TRANSIENT + [0x30] * (N - TRANSIENT)

    # the degeneracy itself: no offset >= 0 gains a single extra match
    counts = {off: pb._agree_at(orig, ours, off)[0] for off in pb.OFFSETS if off >= 0}
    assert len(set(counts.values())) == 1, counts

    pct, n, oc, dc, off, _aud = pb.compare(orig, ours)
    assert off == 0, "a shift buying zero extra matches must not win, got off=%d" % off
    assert n == N
    assert abs(pct - 100.0 * (N - TRANSIENT) / N) < 1e-9, pct
    assert (oc, dc) == (0, 1)


def test_a_real_boot_delay_is_still_found():
    """The count-maximiser must not throw out the case the fit exists for.

    Ours is the original delayed by 3 frames. Shifting repairs far more frames
    than the trim costs, so `ok` genuinely rises and +3 wins outright.
    """
    LAG = 3
    orig = ([0x10] * 40 + [0x50] * 40) * 8
    ours = [0x10] * LAG + orig[:-LAG]

    assert pb._agree_at(orig, ours, LAG)[0] > pb._agree_at(orig, ours, 0)[0]
    pct, n, _oc, _dc, off, _aud = pb.compare(orig, ours)
    assert off == LAG, "a real lag must still be fitted, got off=%d" % off
    assert pct == 100.0
