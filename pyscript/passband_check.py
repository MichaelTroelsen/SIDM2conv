#!/usr/bin/env python3
"""Do the SHIPPED builds select the filter passband their originals do?

`docs/players/HARDTRACK.md` records `$D418` at **100.00% byte-exact**, and that
figure is true *about the builder*: `bin/build_hardtrack_native_song.py` passes
the 3-tuple whose third element is `BM.passband_trace(...)`, so a build made
today gets the passband right. What no check anywhere covered is whether the
SF2/SID files ON DISK were made by that builder. On 2026-08-12 they were not:
21 of 33 rendered low-pass where the original selects low+band, band+high, or
modulates between modes up to 87 times in 28 s. The builder had been fixed and
the artifacts predating the fix were never regenerated.

That gap -- correct code, stale output, and a document quoting the code -- is the
same shape as the tracked-`.inc` problem (`test_generated_inc_untracked.py`) and
deserves the same treatment: something that measures the artifact, not the
source. This script does that, and it is deliberately CHEAP (siddump only, no
audio render, no rebuild) so it can be run after any batch build.

WHY THE PASSBAND AND NOT THE WHOLE REGISTER: `$D418`'s low nibble is master
volume and its bits 4-6 are the low/band/high pass selects. A volume difference
is audible as level, a mode difference as timbre, and pooling them lets one mask
the other. This compares bits 4-6 only.

THREE THINGS SIDDUMP DOES THAT WOULD OTHERWISE FAKE A RESULT:
  - It FILL-FORWARDS: a side that never writes `$D418` shows its last value
    forever, so "static" here means "the register held that value", which is
    what the SID acts on -- not "the playroutine wrote it every frame".
  - It FORCE-DISPLAYS every register on frame 0 whatever the playroutine did,
    so frame 0 is dropped rather than counted as a write.
  - It CANNOT SEE bit 7 (voice-3-off); it prints only `(D418 >> 4) & 7`. That
    bit is outside this check and HARDTRACK.md says so too.

COMMIT `cffc51e` FIXED TWO BUILDERS, NOT ONE: `build_hardtrack_native_song.py`
and `build_dmc_native_song.py`. HardTrack's artifacts were regenerated on
2026-08-12; 968 of 984 `out/dmc/*.sf2` still predate the fix. So this takes a
`--player` rather than hard-coding one directory.

WHAT IT DOES NOT PROVE, for DMC especially: it reads **part 1 only**, against
the original's first `--seconds`. A song split into 77 parts has most of its
music outside that window, so a clean result here means "part 1's passband is
right", never "the song's is". A DIRTY result is still conclusive.

    py -3 pyscript/passband_check.py                     # hardtrack
    py -3 pyscript/passband_check.py --player dmc
    py -3 pyscript/passband_check.py --min 99            # gate at 99%

Exit 0 = every build agrees, 1 = at least one disagrees, 2 = nothing to check.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (  # noqa: E402
    siddump_frames_full, psid_wrap, part_span, window_for)
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Each player ships a different artifact: HardTrack writes a playable .sid
# beside its .sf2, DMC writes only .sf2 and must be PSID-wrapped before siddump
# will look at it. `origs` is a glob relative to SID/ -- '*' where the rip
# directory is not fixed.
PLAYERS = {
    "hardtrack": {"dir": ("out", "hardtrack_native"), "suffix": "_part01.sid",
                  "origs": "*"},
    "dmc": {"dir": ("out", "dmc"), "suffix": "_part01.sf2",
            "origs": "JohannesBjerregaard"},
    # MoN is where `passband_trace` was WRITTEN (464406a, 2026-08-08, "MoN
    # rebuilt every tune with a low-pass filter, whatever it selected") -- and
    # 131 of its 206 artifacts across 16 songs still predate that fix. The
    # builder being right is not the question this tool asks.
    "mon": {"dir": ("out", "mon"), "suffix": "_sub0_part01.sf2",
            "origs": "Tel_Jeroen"},
    # These three builders do NOT call `passband_trace` at all, so they emit
    # low-pass unconditionally. HARDTRACK.md's cross-builder audit called that
    # "right by luck" for FC and SDI because their originals select plain
    # low-pass -- a verdict reached from ONE file per player, which is the same
    # sampling that made "missing passband reads as darker" wrong. Entries exist
    # so the claim can be tested against a corpus instead of asserted.
    # `ref: "sdi_v"` is per FILE, not per player: only the `*_VE-4x` variant-V
    # rips need it. Their wrapper declares `play=$0000` and installs its own IRQ
    # at `v_mult` calls per frame, so siddump -- which calls the player ONCE per
    # frame -- samples a different instant of the same tune. On `Filthy_Hit` that
    # is not a rounding difference: siddump reads BP for 375 of 400 frames while
    # the tune at its real rate ends 303 of them on LP. Driving the module
    # through py65 at `v_mult`, which is what the builder captures from, is the
    # only reference that can adjudicate a V build.
    "sdi": {"dir": ("out", "sdi"), "suffix": "_native_part01.sf2",
            "origs": "Gallefoss_Glenn", "ref": "sdi_v"},
    "fc": {"dir": ("out", "fc"), "suffix": "_part01.sf2", "origs": "Fun_Fun"},
    # `ref: "sim"` -- siddump cannot drive an LFT rip, so the ORIGINAL side comes
    # from the simulator BLACKBIRD.md validates against. It writes `$D418` from
    # the tune's own filttable, which is exactly the register in question.
    "blackbird": {"dir": ("out", "blackbird"), "suffix": "_native_part01.sf2",
                  "origs": "LFT", "ref": "sim"},
}

MODE_NAMES = {0x00: "off", 0x10: "LP", 0x20: "BP", 0x30: "LP+BP",
              0x40: "HP", 0x50: "LP+HP", 0x60: "BP+HP", 0x70: "LP+BP+HP"}


def mode_sequence(frames):
    """Per-frame `$D418` passband (bits 4-6), frame 0 dropped.

    `frames` is `siddump_frames_full`'s output. Returns [] when the register
    never appears -- which is NOT the same as "the tune selects no filter", and
    the caller must not score an empty sequence as agreement.
    """
    return [f["volmode"] & 0x70 for _v, f in frames[1:]
            if f.get("volmode") is not None]


def sim_reference(orig_path, seconds):
    """Per-frame reference from the Blackbird simulator, in siddump's shape.

    Returned as `siddump_frames_full` output so `mode_sequence`,
    `routed_fraction` and `has_evidence` all work unchanged -- the alternative
    was a second comparison path, and two comparison paths is how the two sides
    of a metric drift apart.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bb_sim", os.path.join(ROOT, "bin", "blackbird_everyframe_sim.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bb_sim"] = mod          # @dataclass needs it importable
    spec.loader.exec_module(mod)
    _sim, frames, _recs = mod.run_sim(orig_path, seconds * 50)
    out = []
    for r in frames:
        voices = {}
        for vi in range(3):
            b = vi * 7
            voices[vi] = {"freq": r[b] | (r[b + 1] << 8), "wf": r[b + 4],
                          "pul": r[b + 2] | ((r[b + 3] & 0x0F) << 8),
                          "adsr": (r[b + 5] << 8) | r[b + 6]}
        out.append((voices, {"cutoff": r[22], "filtctl": r[23], "volmode": r[24]}))
    return out


def sdi_v_reference(orig_path, seconds):
    """Per-frame reference for a variant-V SDI rip, in siddump's shape.

    Returns None for any file that is not variant V, so the caller falls back to
    siddump -- the other five SDI variants are driven perfectly well by it and
    swapping their reference would change 276 rows to fix 4.

    The passband is reconstructed as `pb << 4`: `v_traces` records `$D418`'s
    mode bits already shifted down, and `mode_sequence` masks `& 0x70`, so the
    two line up exactly. `$D418`'s low nibble (master volume) is not part of
    this comparison and is left at 0 rather than invented.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sdi_build", os.path.join(ROOT, "bin", "build_sdi_native_song.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sdi_build"] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        # the builder runs main() on import when given no argv it understands;
        # everything needed is defined by then
        pass
    from sidm2.sdi_parser import SDIModule
    d, la, h = mod.load_sid(orig_path)
    m = SDIModule(d, la)
    if getattr(m.lay, "variant", None) != "V":
        return None
    mi, mp = mod._v_module_addrs(d, la, h.init_address)
    if mi is None:
        return None
    per, filt, pb, _onsets = mod.v_traces(
        d, la, mi, mp, m.lay.v_mult, seconds * 50)
    out = []
    for i, (st, cut) in enumerate(per):
        voices = {vi: {"freq": st[vi]["freq"], "wf": st[vi]["wf"],
                       "pul": st[vi]["pul"], "adsr": 0} for vi in range(3)}
        out.append((voices, {"cutoff": cut, "filtctl": filt[i][1],
                             "volmode": (pb[i] & 0x07) << 4}))
    return out


def has_evidence(frames):
    """Did this trace capture a playing tune at all?

    A file siddump cannot drive returns a full-length series of zeroes, which is
    byte-identical to "this tune never filters" and to "this tune is silent".
    Comparing against it produces confident nonsense in whichever direction the
    other side happens to differ. Requiring a sounded voice is the cheapest
    honest gate: a tune with no frequency and no waveform on any voice for the
    whole window was not playing.
    """
    for v, _g in frames[1:]:
        for vi in range(3):
            if v[vi].get("freq") or v[vi].get("wf"):
                return True
    return False


def routed_fraction(frames):
    """Fraction of frames where `$D417` feeds at least one voice to the filter.

    Returned separately from the passband rather than folded into it, because
    they answer different questions: the passband says WHICH filter output is
    summed, routing says whether anything is in the filter to be summed. A
    passband mismatch on a tune that routes nothing is inaudible by
    construction, and the check has no business calling that a failure.
    """
    vals = [g["filtctl"] for _v, g in frames[1:] if g.get("filtctl") is not None]
    if not vals:
        return None
    return sum(1 for v in vals if v & 0x0F) / len(vals)


def describe(modes):
    """(names present, number of mode CHANGES). The change count is what
    separates "both sides sit on one constant" from "the original modulates and
    we do not" -- two failures that score identically on a plain equality test
    against a static side."""
    names = [MODE_NAMES.get(m, f"${m:02X}") for m in sorted(set(modes))]
    changes = sum(1 for a, b in zip(modes, modes[1:]) if a != b)
    return names, changes


# The native driver boots a few frames after the original. Every other scorer
# in this repo fits this before comparing (`measure_parts` uses range(-4, 9));
# HARDTRACK.md states the render sits at -3. Not fitting it makes a constant
# boot delay read as a passband defect on any tune that MODULATES the mode --
# the static-mode files are immune, which is exactly why the flaw survived the
# first run of this check.
OFFSETS = range(-4, 9)


def _agree_at(orig_modes, our_modes, off):
    n = 0
    ok = 0
    for i in range(len(orig_modes)):
        j = i + off
        if not (0 <= j < len(our_modes)):
            continue
        n += 1
        ok += orig_modes[i] == our_modes[j]
    return ok, n


def compare(orig_modes, our_modes, offsets=OFFSETS, routed_seq=None):
    """Best-aligned frame-wise agreement, plus the two failure shapes.

    Returns (pct|None, n, orig_changes, our_changes, offset). `None` -- never
    100.0 and never 0.0 -- when either side has no `$D418` rows at all,
    following `fidelity_common.score_pct`: an unmeasured comparison is not a
    perfect one.

    The offset is fitted, not assumed, and REPORTED, because a large one is
    itself a finding: it means the passband is right but arrives late, which is
    a different defect from selecting the wrong band. That reading is only safe
    because the fit maximises the match COUNT -- an offset that gains no extra
    matches can never win, so a reported offset means frames were actually
    repaired by it. Reading the offset as a lag while fitting on the RATE was
    wrong for exactly this reason (fixed 2026-08-16; see the comment below).
    """
    if not orig_modes or not our_modes:
        return None, 0, 0, 0, 0, None
    # Maximise the raw MATCH COUNT, not the rate. Maximising the rate lets a
    # shift buy agreement for free: `_agree_at` trims the tail, so when the
    # disagreement sits anywhere else, a positive offset shrinks `n` without
    # repairing a single frame and the percentage climbs on its own. Measured
    # 2026-08-16 on two players at once -- DMC Soap_Theme's `ok` is FLAT at 1280
    # for every offset >= 0 while `n` falls 1299 -> 1291, so the rate climbed
    # 98.537 -> 99.148 and the winner was simply max(OFFSETS); SDI Arabia's
    # fitted +4 held `ok` at 879 and then LOST matches beyond it. Both bought
    # their offset with exactly zero extra matches.
    #
    # What it cost, measured after the fix rather than predicted before it: the
    # percentage, the reported offset, and the mismatch COUNT the audibility
    # annotation is computed over (Arabia read audible=3 at its fitted offset
    # against 7 at offset 0). It did NOT change any corpus verdict -- a build
    # passes on the AUDIBLE count, not on `agree`, so Soap_Theme passed at 99.1
    # and still passes at 98.5 with all 19 mismatches on unrouted frames.
    # HardTrack held 32/33 and DMC 53/74 across the fix. An earlier version of
    # this comment claimed the inflation carried Soap_Theme over the --min 99.0
    # gate and turned a fail into a pass; that was wrong, and running the corpus
    # is what corrected it.
    #
    # A real boot delay still scores: shifting by the true lag repairs more
    # frames than the trim costs, so `ok` genuinely rises and the count-
    # maximiser finds it. What it refuses is a shift that repairs nothing.
    # Ties go to the smallest shift, so a file that agrees nowhere reports
    # offset 0 rather than whichever offset happened to be tried first.
    cand = []
    for off in sorted(offsets, key=lambda o: (abs(o), o)):
        ok, n = _agree_at(orig_modes, our_modes, off)
        if n:
            cand.append((off, ok, n))
    if not cand:
        return None, 0, 0, 0, 0, None
    # A shift may not buy its rate by discarding the comparison: with offsets
    # bounded to a few frames against ~1400 this never binds, but it stops the
    # fit degenerating if either ever changes.
    widest = max(n for _o, _k, n in cand)
    cand = [c for c in cand if c[2] >= widest * 0.5]
    # ok, then "does this shift explain the overlap COMPLETELY", then the
    # smallest shift. The middle term is what keeps a real one-transition delay
    # fittable: a k-frame lag over T transitions repairs k*T frames and trims k,
    # so `ok` rises by k*(T-1) and ties at exactly T == 1. A shift that makes the
    # two sequences IDENTICAL over the overlap is the alignment; one that leaves
    # frames disagreeing (Soap_Theme 1280/1291, Arabia 879/895) is not, and loses
    # the tie to offset 0.
    best_off, best_ok, best_n = max(
        cand, key=lambda c: (c[1], c[1] == c[2], -abs(c[0])))
    _, oc = describe(orig_modes)
    _, dc = describe(our_modes)
    # Mismatches on frames where the ORIGINAL feeds no voice to the filter
    # cannot be heard: the passband selects among silent outputs there. Counted
    # at the winning offset, on the disagreeing frames only.
    audible = None
    if routed_seq is not None:
        audible = 0
        for i in range(len(orig_modes)):
            j = i + best_off
            if not (0 <= j < len(our_modes)):
                continue
            if orig_modes[i] != our_modes[j] and i < len(routed_seq) and routed_seq[i]:
                audible += 1
    return 100.0 * best_ok / best_n, best_n, oc, dc, best_off, audible


def find_original(base, origs):
    for cand in sorted(glob.glob(os.path.join(ROOT, "SID", origs, base + ".sid"))):
        return cand
    return None


def artifact_frames(path, args):
    """siddump an artifact, PSID-wrapping it first when it is a bare .sf2.

    The wrap is the same one the builders and sweeps use; writing it beside the
    source would litter `out/`, so it goes to a single scratch name that is
    overwritten per file and never read again.
    """
    if path.lower().endswith(".sid"):
        return siddump_frames_full(path, args)
    sf2 = open(path, "rb").read()
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    probe = os.path.join(os.path.dirname(path), "_passband_probe.sid")
    open(probe, "wb").write(psid_wrap(sf2[2:], sla, 0x1000, 0x1003))
    return siddump_frames_full(probe, args)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--player", choices=sorted(PLAYERS), default="hardtrack")
    ap.add_argument("--seconds", type=int, default=28,
                    help="comparison window. Passing it explicitly ASSERTS that "
                         "it fits part 1; without that a failure on a multi-part "
                         "build is reported UNCONFIRMED, because our part loops "
                         "inside a too-long window and manufactures mismatch")
    ap.add_argument("--files", nargs="*", metavar="NAME",
                    help="check only these songs (no suffix)")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="first N builds only -- a SAMPLE, and the summary says "
                         "so; a sampled count is not a corpus verdict")
    ap.add_argument("--min", type=float, default=99.0, metavar="PCT",
                    help="fail below this frame-wise mode agreement")
    a = ap.parse_args(argv)

    cfg = PLAYERS[a.player]
    build_dir = os.path.join(ROOT, *cfg["dir"])
    # `_`-prefixed names are scratch (A/B baselines, probes), never shipped.
    builds = sorted(b for b in glob.glob(os.path.join(build_dir, "*" + cfg["suffix"]))
                    if not os.path.basename(b).startswith("_"))
    if a.files:
        want = set(a.files)
        builds = [b for b in builds
                  if os.path.basename(b)[:-len(cfg["suffix"])] in want]
    sampled = bool(a.limit) and a.limit < len(builds)
    if a.limit:
        builds = builds[:a.limit]
    if not builds:
        print(f"no {a.player} builds in {build_dir} -- nothing to check")
        return 2

    print(f"{'file':<28s} {'original':<14s} {'ours':<14s} "
          f"{'oChg':>5s} {'dChg':>5s} {'off':>4s} {'agree':>7s} {'routed':>7s}")
    bad = []
    unexercised = []
    dead = []
    unconfirmed = []
    asserted_window = any(a_.startswith("--seconds") for a_ in (argv or sys.argv[1:]))
    for b in builds:
        base = os.path.basename(b)[:-len(cfg["suffix"])]
        # A recorded span beats the global window, and it beats it in ONE
        # direction: never widen past --seconds, because a longer window is the
        # over-run this whole guard exists for. An explicit --seconds still
        # wins, so an operator can always narrow further.
        span = None if asserted_window else part_span(b)
        secs, derived = window_for(span, a.seconds)
        args = ["-a0", f"-t{secs}"]
        orig = find_original(base, cfg["origs"])
        if not orig:
            print(f"{base:<28s} NO ORIGINAL FOUND -- cannot check")
            bad.append((base, "no original"))
            continue
        ref = cfg.get("ref")
        if ref == "sim":
            of = sim_reference(orig, secs)
        elif ref == "sdi_v":
            # per-file: None for the five non-V variants, which siddump drives
            of = sdi_v_reference(orig, secs) or siddump_frames_full(orig, args)
        else:
            of = siddump_frames_full(orig, args)
        if not has_evidence(of):
            # NOT a result about this build. Refuse loudly rather than compare
            # against silence -- see `has_evidence`.
            print(f"{base:<28s} NO REFERENCE TRACE -- siddump drove no voice "
                  f"on the ORIGINAL; nothing here can be compared")
            dead.append(base)
            continue
        om = mode_sequence(of)
        routed = routed_fraction(of)
        dm = mode_sequence(artifact_frames(b, args))
        routed_seq = [g["filtctl"] & 0x0F for _v, g in of[1:]
                      if g.get("filtctl") is not None]
        pct, n, oc, dc, off, audible = compare(om, dm, routed_seq=routed_seq)
        on, _ = describe(om) if om else (["n/a"], 0)
        dn, _ = describe(dm) if dm else (["n/a"], 0)
        shown = "n/a" if pct is None else f"{pct:.1f}"
        note = ""
        if pct is None:
            note = "   <== no $D418 rows on one side"
            bad.append((base, "unmeasured"))
        elif routed == 0.0 and set(om) <= {0x00}:
            # Nothing routed AND no passband ever selected: there is no filter
            # behaviour here to reproduce. Counting this as a pass is the
            # `exercised()` trap -- 0 == 0 reported as agreement.
            unexercised.append(base)
            note = "   (filter never exercised in this window -- NOT a pass)"
        elif routed == 0.0:
            # A real difference with nil severity: the original selects a
            # passband but feeds no voice into the filter, so the bits choose
            # among silent outputs.
            note = "   (no voice routed to the filter -- passband inaudible)"
        elif audible == 0 and pct is not None and pct < a.min:
            # Every disagreeing frame is one the original does not route.
            note = (f"   (all {n - round(n * pct / 100)} mismatches on frames "
                    f"the original does not route -- inaudible)")
        elif pct < a.min:
            # "original modulates, ours does not" is a LABEL for a failure, not
            # a trigger for one. Firing it independently of the agreement score
            # called `Alf_TV_Theme`, `Dragon_Sword` and `Slimbo4` broken at
            # 100.0%: the original's only "change" is its initial off -> mode
            # transition, and our build simply starts on the right mode. A
            # genuinely static build against a modulating original cannot reach
            # the threshold anyway -- `Hopscotch` sat at 87.2%.
            why = (f"static vs {oc} changes" if oc and not dc else f"{pct:.1f}%")
            nparts = len(glob.glob(os.path.join(
                build_dir, base + cfg["suffix"].replace("01", "*"))))
            if nparts > 1 and not asserted_window and span is None:
                # Our part 1 may have looped inside this window. Over-run can
                # only MANUFACTURE disagreement, so this is not counted as a
                # pass either -- it is simply not established. With a recorded
                # span there is nothing to be unsure about: the window IS part 1.
                unconfirmed.append((base, why, nparts))
                note = f"   <== UNCONFIRMED ({nparts} parts; window may over-run part 1)"
            else:
                note = ("   <== original MODULATES, ours is static" if oc and not dc
                        else "   <== mode mismatch")
                bad.append((base, why))
        if derived:
            note += f"   [{secs}s = its own part 1]"
        rshow = "n/a" if routed is None else f"{100.0 * routed:.0f}%"
        if audible is not None and pct is not None and pct < a.min:
            rshow += f"/{audible}a"      # audible mismatches
        print(f"{base:<28s} {'/'.join(on):<14s} {'/'.join(dn):<14s} "
              f"{oc:5d} {dc:5d} {off:>4d} {shown:>7s} {rshow:>7s}{note}")

    ok = len(builds) - len(bad) - len(unexercised) - len(dead) - len(unconfirmed)
    if unconfirmed:
        print(f"\n{len(unconfirmed)} file(s) UNCONFIRMED -- multi-part builds "
              f"whose part 1 may end inside this window, so the mismatch may be "
              f"our own loop rather than the build. Re-run with an explicit "
              f"--seconds that fits part 1 (`Domino_Dancing` reads 99.0% at 28s "
              f"and 100.0% at the 12s its part actually spans).")
        for name, why, nparts in unconfirmed:
            print(f"    {name} ({why}, {nparts} parts)")
    if sampled:
        print(f"\n!! SAMPLE of {len(builds)} -- not a corpus verdict")
    if dead:
        print(f"\n!! {len(dead)} file(s) have NO REFERENCE TRACE. siddump drove "
              f"no voice on the original, so a comparison would be against "
              f"silence. This is a TOOLING gap for that player, not a result: "
              f"`SID/LFT/*` are validated against a simulator, not siddump.")
        print(f"   {', '.join(sorted(dead)[:10])}"
              f"{' ...' if len(dead) > 10 else ''}")
    print(f"\n{ok}/{len(builds)} builds select the original's passband "
          f"(or route nothing through the filter, where it cannot be heard)")
    if unexercised:
        print(f"  {len(unexercised)} file(s) NOT COUNTED EITHER WAY: the "
              f"original never routes a voice and never selects a passband in "
              f"this window, so there is nothing to reproduce. Widen "
              f"--seconds before reading this as a corpus verdict.")
        print(f"    {', '.join(sorted(unexercised)[:10])}"
              f"{' ...' if len(unexercised) > 10 else ''}")
    if bad:
        # NOT "rebuild these, the builder is already correct". That was the
        # message until `Eagles`, `In_the_Mood` and `Roadblaster` came back at
        # 0.0% AFTER a rebuild, emitting mode `off` -- no passband at all. A
        # rebuild distinguishes the two causes; it does not presume one.
        print("FAILED -- rebuild these first; if it survives a rebuild the "
              "builder is at fault, not the artifact:")
        for name, why in bad:
            print(f"  {name} ({why})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
