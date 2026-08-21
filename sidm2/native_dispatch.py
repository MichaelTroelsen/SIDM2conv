"""Which native builder owns this SID? Probe the parsers, do not trust player-id.

ROADMAP A4 asked for registry entries so `sid-to-sf2.bat` would auto-route the
`bin/` players. Measured 2026-08-17, that cannot work: `PLAYER_REGISTRY` keys on
`player-id.exe` strings and those verdicts are MANY-TO-MANY with the builders.
Sampling 12 files spread across each of 10 corpora, `Matt_Gray` files report
`Soundmonitor` on 10 of 12, and a `DMC` verdict captures 4 HardTrack and 2 SDI
files. Only three families are clean enough to route on the string:

    Galway      Martin_Galway     12/12
    Hubbard     Rob_Hubbard       11/12
    Blackbird   Blackbird/LFT + LFT 11/12 (1 unidentified)

So the discriminator is each parser's own signature-based locate, which every
family already implements and which every family already refuses loudly when it
does not match ("tables not located", "decoded no notes", "not an SDI play+3
rip"). This module turns those refusals into a dispatch decision.

CHEAP BY CONSTRUCTION. A probe constructs the parser's module object, which
runs its locate and raises. It does NOT build, render, emulate or siddump, so
dispatching a file costs milliseconds and is safe to run beside a corpus job.

ORDER IS NOT A GUESS AND MUST NOT BECOME ONE. `PROBE_ORDER` below is only
meaningful if the parsers are actually mutually exclusive on real files; where
two accept the same file the first one wins silently, which is the failure mode
that makes a dispatcher worse than no dispatcher. `dispatch()` therefore takes
`first_match=False` by default and reports EVERY family that accepts the file,
so a collision is visible rather than hidden. Callers that want a single answer
opt into `first_match=True` and accept the ordering.
"""
from __future__ import annotations

# player-id.exe verdicts that are reliable enough to use as a PREFILTER.
# Everything else is measured noise -- see the module docstring.
RELIABLE_PLAYER_IDS = {
    "Martin_Galway": "galway",
    "Rob_Hubbard": "hubbard",
    "Blackbird/LFT": "blackbird",
    "LFT": "blackbird",
}


def _probe_dmc(path):
    """Constructing DMCModule is NOT a discriminator -- measured 2026-08-17, it
    accepts every file in every corpus, because _locate finds plausible-looking
    tables anywhere. The real refusal is at DECODE ("decoded no notes on any
    voice"), so the probe has to go that far."""
    from sidm2.dmc_parser import load_sid, DMCModule, decode_song
    d, la, _h = load_sid(path)
    m = DMCModule(d, la)
    voices = decode_song(m, tick_budget=400)
    if not any(voices[v] for v in range(len(voices))):
        raise ValueError("decoded no notes on any voice")
    return {"load": la, "notes": sum(len(v) for v in voices)}


def _probe_sdi(path):
    from sidm2.sdi_parser import load_sid, SDIModule, is_sdi_play3
    d, la, h = load_sid(path)
    if not is_sdi_play3(d, la, h):
        raise ValueError("not an SDI play+3 rip")
    m = SDIModule(d, la)
    return {"load": la, "tables": getattr(m, "lay", None)}


def _probe_mon(path):
    from sidm2.mon_parser import load_sid, MON
    d, la, _h = load_sid(path)
    m = MON(d, la)
    # KNOWN GAP: MON has no cheap predicate and no decode-level refusal wired in
    # here, so this probe still accepts everything. Until that is closed, `mon`
    # must never be used as a first_match answer -- see the module docstring.
    return {"load": la, "tables": getattr(m, "lay", None), "weak": True}


def _probe_hubbard(path):
    from sidm2.hubbard_parser import load_sid, HubbardModule
    d, la, _h = load_sid(path)
    m = HubbardModule(d, la)
    return {"load": la, "tables": getattr(m, "lay", None)}


def _probe_soundmonitor(path):
    """soundmonitor_parser ships its own predicate, exactly as sdi_parser does.
    Constructing the module alone accepts everything."""
    from sidm2.soundmonitor_parser import load_sid, SoundMonitorModule, is_soundmonitor
    d, la, h = load_sid(path)
    if not is_soundmonitor(d, la, h):
        raise ValueError("not a Sound Monitor rip")
    m = SoundMonitorModule(d, la)
    return {"load": la, "tables": getattr(m, "lay", None)}


def _probe_blackbird(path):
    from sidm2.blackbird_parser import locate_blackbird
    r = locate_blackbird(path)
    if not r:
        raise ValueError("locate_blackbird found nothing")
    return {"tables": r}


def _probe_mattgray(path):
    """TWO CALLER ERRORS WERE STACKED HERE AND THE FIRST HID THE SECOND. This
    probe used to do `d, la, _h = load_sid(path)` and `MattGrayParser(d, la)`.
    But mattgray's `load_sid` returns SIX values (body, load, init, play, songs,
    start), not three, and `MattGrayParser` takes FOUR arguments. The unpack
    raised first, so the arity error on the constructor was never even reached.

    `locate()` finds every table by signature and raises when any one is not
    identifiable, so this is a real predicate -- see SIGNATURE.

    AND A THIRD CALLER ERROR HID BEHIND THOSE TWO, THIS TIME WITH NO ARITY TO
    GIVE IT AWAY. The version above probed the WHOLE PSID image, which is only
    one of the two shapes `parse_sid` handles. A Matt Gray RELOCATING
    COMPILATION carries one self-contained tune per subtune and materialises
    each as its own blob at its own address (`relocating_subtunes` /
    `relocating_subtunes_v2`); `parse_sid` splits it and parses the blob with
    `MattGrayParser(blob, dst, dst, dst + 2)`. Run against the unsplit image
    there is no single table set to find, so `locate()` refused -- CORRECTLY,
    and for a reason that read as a verdict about the file.

    IT WAS WRONG ON EXACTLY THE FILES THE STAGE B CORPUS IS BUILT FROM.
    `Last_Ninja_2` (13 blobs, v1) refused with "could not locate the
    track-pointer tables" and `Tusker` (4 blobs, v2) with "play address
    unreadable: address $e002 outside image $1000-$413f" -- both have shipped
    `out/mattgray_native` artifacts, and Last Ninja 2 sub 0 is the headline
    measurement in CLAUDE.md. `locate()` succeeds on blob 0 of both.

    So the probe now mirrors `parse_sid`'s own dispatch rather than half of it.
    That is the general lesson and it is worth more than this fix: a probe that
    models FEWER shapes than the builder reports the builder's own corpus as
    foreign, and nothing about the failure looks like a bug.
    """
    from sidm2.mattgray_parser import (load_sid, MattGrayParser,
                                       relocating_subtunes,
                                       relocating_subtunes_v2)
    body, load, init, play, songs, _start = load_sid(path)
    blobs = (relocating_subtunes(body, load, init, songs)
             or relocating_subtunes_v2(body, load, init, songs))
    if blobs:
        # Blob 0 is representative: every blob is a self-contained tune in the
        # same format, so locating one is the predicate. Probing all 13 would
        # cost 13x for no extra discrimination.
        blob, dst = blobs[0]
        p = MattGrayParser(blob, dst, dst, dst + 2)
        return {"load": dst, "init": dst, "play": dst + 2,
                "relocating": True, "subtunes": len(blobs),
                "tables": p.locate()}
    p = MattGrayParser(body, load, init, play)
    return {"load": load, "init": init, "play": play,
            "relocating": False, "tables": p.locate()}


def _probe_hardtrack(path):
    """THE SHAPE DIFFERENCE THAT LEFT THIS FAMILY UNPROBED: HardTrackModule takes
    `(load, data)` -- the inverse of every other parser's `(data, la)` -- and reads
    the PSID header itself, so this probe goes through the `from_sid` classmethod
    instead of the shared `load_sid`. That is the whole of the old TODO.

    It is a SIGNATURE probe and a strict one, which is why `hardtrack` joins
    SIGNATURE rather than CONSTRUCT_ONLY. Four independent 6502 opcode patterns
    (init, pattern-pointer, frequency, instrument) must EACH match exactly once,
    and the PSID init/play vector must be the module's own `load`/`load+3` entry
    -- a wrapped rip is refused rather than decoded as instance 0. Every one of
    those refusals is a HardTrackError, which subclasses ValueError, so `probe`
    reads them as rejections through its normal path while a genuine caller
    error still surfaces as ProbeBug.
    """
    from sidm2.hardtrack_parser import HardTrackModule
    m = HardTrackModule.from_sid(path)
    return {"load": m.load, "init_off": m.init_off,
            "instrument_base": m.instrument_base,
            "tables": (m.pattern_lo, m.freq_lo_table)}


# Most specific first. See the docstring: this order only decides `first_match`,
# and dispatch() reports collisions rather than letting the order hide them.
PROBE_ORDER = (
    ("blackbird", _probe_blackbird),
    ("sdi", _probe_sdi),
    ("hardtrack", _probe_hardtrack),
    ("mattgray", _probe_mattgray),
    ("dmc", _probe_dmc),
    ("mon", _probe_mon),
    ("hubbard", _probe_hubbard),
    ("soundmonitor", _probe_soundmonitor),
)


# A PROBE BUG MUST NOT LOOK LIKE A REFUSAL. Catching Exception broadly here hid
# a real one: `is_soundmonitor(data, la, h)` was called with two arguments, the
# TypeError was swallowed as "not a Sound Monitor rip", and the family silently
# rejected its OWN corpus while the run still looked clean. Parser refusals are
# ValueError/IndexError/KeyError; a TypeError, AttributeError or NameError is my
# code being wrong and has to surface.
BUG_EXCEPTIONS = (TypeError, AttributeError, NameError, ImportError)

# AND THE TAXONOMY ABOVE HAS NOW FAILED ONCE, THE SAME WAY, IN THE SAME FILE.
# `_probe_mattgray` unpacked mattgray's 6-value `load_sid` into three names.
# CPython raises ValueError for a wrong-arity unpack -- and ValueError is the
# canonical REFUSAL type here, so the broad handler below recorded my bug as the
# file's verdict. The family reported "accepts nothing anywhere, including its
# own corpus" for as long as the probe existed, and the second error stacked
# behind it (MattGrayParser takes four arguments, not two) was never reached.
#
# These two messages are generated by the interpreter, never by a parser, so
# matching them is safe in a way that matching a parser's prose would not be.
# A refusal that happens to be a ValueError is untouched.
UNPACK_BUG_MESSAGES = ("too many values to unpack", "not enough values to unpack")


class ProbeBug(Exception):
    """A probe called its parser wrongly. Never a verdict about the file."""


def probe(player, path):
    """(True, evidence) or (False, reason). Raises ProbeBug on a caller error."""
    fn = dict(PROBE_ORDER).get(player)
    if fn is None:
        return False, "no probe implemented"
    try:
        return True, fn(path)
    except BUG_EXCEPTIONS as e:
        raise ProbeBug("%s probe is broken: %s: %s"
                       % (player, type(e).__name__, e)) from e
    except ValueError as e:
        if any(m in str(e) for m in UNPACK_BUG_MESSAGES):
            raise ProbeBug("%s probe unpacked its loader wrongly: %s"
                           % (player, e)) from e
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])
    except Exception as e:                      # a refusal IS the reject signal
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


# ---------------------------------------------------------------- ranking ---
# RANK BY EVIDENCE STRENGTH, because boolean accept is refuted. Two designs
# already failed by measurement and are recorded in ROADMAP A4: routing on
# `player-id` strings (many-to-many with the builders) and taking the first
# family that does not raise (`dmc` and `mon` accept all 48 files in the spread
# sample, so first-match misroutes everything).
#
# The one property that actually separates the families is whether the parser
# HAS A SIGNATURE IT CAN REJECT ON. Measured over the 48-file spread sample:
#
#   blackbird     accepts  1 of 48   `locate_blackbird` finds nothing elsewhere
#   sdi           accepts  3 of 48   gated by `is_sdi_play3`
#   soundmonitor  accepts  4 of 48   gated by `is_soundmonitor`
#   hubbard       accepts  8 of 48   NO predicate -- construction alone
#   dmc           accepts 48 of 48   `_locate` finds plausible tables anywhere
#   mon           accepts 48 of 48   no predicate, no decode-level refusal
#   mattgray      accepts  0 of 48   <- WAS TWO PROBE BUGS IN A ROW, neither a
#                                      property of the parser. Fixed 2026-08-21;
#                                      it now accepts 13 of 55 Gray_Matt files
#                                      and 0 of the other 679 measured, and is a
#                                      SIGNATURE family because `locate()` raises
#                                      when a table is not identifiable.
#
# THE MATTGRAY LINE ABOVE MOVED TWICE IN ONE DAY AND THE SECOND MOVE IS THE ONE
# WORTH READING. The first fix (a 6-value loader unpacked into 3 names) took it
# 0 -> 11. The second took it 11 -> 13, and those two files are `Last_Ninja_2`
# and `Tusker` -- both of which have shipped `out/mattgray_native` artifacts, and
# Last Ninja 2 sub 0 is CLAUDE.md's headline Matt Gray measurement. The probe
# modelled only ONE of the two shapes `parse_sid` handles, missing the
# relocating compilation, so it called the builder's own corpus foreign. See
# `_probe_mattgray`.
#
# THE CHECK THAT CAUGHT IT IS THE ONE THAT VALIDATED HARDTRACK: compare the
# accept set against the SHIPPED corpus, not against itself. Now every one of
# the 8 built songs is accepted (inclusion, not the equality HardTrack got --
# 5 accepted songs have no artifact, which is a build backlog and not a parser
# property). The remaining 42 refusals fall into 4 named classes: 23 whose play
# routine is not the MoN music_play shim, 10 with PSID play=$0000 (RSID/self-IRQ
# -- there is no play vector to read, so no static locate can ever claim them),
# 8 where the tables are genuinely not locatable, and 1 whose play vector points
# outside the loaded image.
#
# THREE NESTED DENOMINATORS, AND THEY ARE THREE QUESTIONS RATHER THAN THREE
# DISAGREEING ANSWERS -- the same trap CLAUDE.md already records for SDI's
# 343/348/324. Do not conflate them:
#
#   13  this probe accepts        -- `locate()` identifies every table
#   11  `parse_sid` decodes       -- tables AND the sequencer walk completes
#    8  Stage B has artifacts     -- decoded, built and emitted
#
# The 13 -> 11 step is `Pogo_Stick_Olympics` and `Warriors`, which fail with
# "pattern at $1517/$2517 has no $ff terminator": their tables ARE located and
# the WALK is what breaks. That is precisely the distinction CLAUDE.md draws
# when it says the located tables "validate the TABLES, not the sequencer walk",
# so the probe is not made stricter to match -- it answers the table question,
# which is the one a dispatcher asks. Tightening it to require a full decode
# would turn a cheap signature predicate into `_probe_dmc`.
#
# The 11 -> 8 step is a BUILD BACKLOG, not a parser property: five accepted
# songs simply have no artifact yet.
#
# A REFUTED SCORING RULE, RECORDED SO IT IS NOT RETRIED: `_probe_dmc` returns a
# decoded note count, and the obvious next move is to threshold it. Measured, it
# does not separate -- real DMC files run min 73 / median 302 / max 1200 while
# `blackbird` is 1200 across the board, `soundmonitor` medians 1082 and
# `mattgray` 895. DMC's own median is LOWER than several families it would have
# to be told apart from, and the 1200s are a saturation artifact of
# `tick_budget=400`. Note count is not evidence of ownership.
SIGNATURE = frozenset({"blackbird", "sdi", "soundmonitor", "hardtrack", "mattgray"})
CONSTRUCT_ONLY = frozenset({"dmc", "mon", "hubbard"})
# A family with no probe at all: it can never accept and can never be ranked.
# Kept as a named set rather than deleted, because an unclassified family is
# invisible -- the classification test asserts these three sets cover
# PROBE_ORDER exactly, and `hardtrack` was found missing by that test on its
# first run.
#
# NOW EMPTY. `hardtrack` was the only member and is a SIGNATURE family as of
# `_probe_hardtrack`, measured 2026-08-21 over all 150 files of SID/Shogoon:
#
#   accepted                  33   ranked `hardtrack`, confident, 0 collisions
#   no init signature        111
#   signature, then refused    6   3x "2 player instances", 1x "3 player
#                                  instances", 2x PSID init/play != module entry
#
# THE ACCEPT SET IS EXACTLY THE SHIPPED STAGE B CORPUS -- the same 33 song names
# as `out/hardtrack_native`, set-equal in both directions. That is external
# ground truth rather than self-consistency, and it is why the 6 post-signature
# refusals are correct rather than misses: a wrapped or multi-instance rip is
# refused instead of decoded as instance 0.
#
# ONE PREDICTION IN THIS MODULE IS REFUTED BY THAT MEASUREMENT. The note here
# used to say `Pollena_2000` is a HardTrack file which `is_sdi_play3` claimed
# unopposed, and that a HardTrack probe would give the ranking something to
# COLLIDE with, turning a confident misroute into an honest abstention. It does
# not: `_probe_hardtrack` finds NO init signature in that file at all, so there
# is no collision and `Pollena_2000` still ranks `sdi`, confident. It also has
# no artifact in `out/hardtrack_native` and is named in neither HARDTRACK.md nor
# CLAUDE.md, so the premise -- that it is a HardTrack file -- is unsupported.
# Either it is not one, or it is a variant this signature does not cover; the
# probe cannot tell those apart, and neither can this comment. What is settled
# is that adding the probe did NOT fix that misroute, and any future claim that
# it did should be checked against this paragraph.
UNPROBED = frozenset()


def rank(path, player_id=None):
    """Rank the accepting families by evidence strength and answer only when the
    evidence supports ONE.

    Returns {"best": player|None, "confident": bool, "why": str,
             "signature": [...], "weak": [...], "dispatch": <dispatch() result>}.

    `best` is None whenever the evidence does not single out a family. That is
    the point: a dispatcher that always answers is worse than one that abstains,
    because a misroute produces a wrong SF2 rather than an error.
    """
    d = dispatch(path, player_id=player_id)
    acc = d["accepted"]
    sig = [p for p in acc if p in SIGNATURE]
    weak = [p for p in acc if p not in SIGNATURE]
    best, confident = None, False
    if len(sig) == 1:
        best, confident = sig[0], True
        why = "unique signature match (%s); %d construct-only family/families " \
              "also accept and are not evidence" % (sig[0], len(weak))
    elif len(sig) > 1:
        why = "signature collision: %s both accept" % ", ".join(sig)
    else:
        # A THIRD REFUTED DESIGN, measured in this module rather than argued.
        # The tempting move here is to corroborate: no signature family
        # accepted, so promote a construct-only family when `player-id` names
        # one of the three verdicts measured reliable. Implemented and measured
        # over the same 48-file sample, it answers 6 more files and gets 2 of
        # them WRONG -- `Eagles` (truth dmc) and `Something_Green` (truth mon)
        # both report `Rob_Hubbard`. Only 4 of the 7 `Rob_Hubbard` verdicts in
        # the sample are Hubbard files, which does not match the 11/12 figure
        # RELIABLE_PLAYER_IDS is built on. Precision FELL, 75.0% -> 71.4%.
        #
        # Two weak signals do not compose into a strong one: a probe that
        # accepts everything carries no information about this file, and
        # combining it with a verdict that has false positives just launders the
        # guess. So there is no corroboration path -- abstain instead.
        why = ("no signature-bearing family accepted; %d construct-only "
               "family/families accept and cannot discriminate"
               % len(weak))
    return {"best": best, "confident": confident, "why": why,
            "signature": sig, "weak": weak, "dispatch": d}


def dispatch(path, player_id=None, first_match=False):
    """Which native builders accept this file?

    Returns {"accepted": [player, ...], "rejected": {player: reason},
             "prefilter": player_or_None}. `accepted` with more than one entry is
    a COLLISION and the caller must not silently take the first unless it asked
    for `first_match`.
    """
    order = [p for p, _ in PROBE_ORDER]
    pre = RELIABLE_PLAYER_IDS.get(player_id) if player_id else None
    if pre and pre in order:                    # prefilter only reorders; it
        order.remove(pre)                       # never excludes, because the
        order.insert(0, pre)                    # verdicts are not exhaustive
    accepted, rejected = [], {}
    for p in order:
        ok, info = probe(p, path)
        if ok:
            accepted.append(p)
            if first_match:
                break
        else:
            rejected[p] = info
    return {"accepted": accepted, "rejected": rejected, "prefilter": pre}
