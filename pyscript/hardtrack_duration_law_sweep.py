#!/usr/bin/env python3
"""Audit the HardTrack duration off-by-one: does gg[i] == og[i+1]?

THE LAW. On the affected songs the built render's inter-onset gap `i` equals the
ORIGINAL's gap `i+1` -- the sequencer walk consumes each note's duration one note
early, so every note is held for its SUCCESSOR's length. `shift` below is the
agreement rate of that relation; `identity` is the rate of gg[i] == og[i], which
is what a healthy file scores instead.

WHY THIS IS A TRACKED SCRIPT RATHER THAN A NUMBER IN A DOC. The figure has been
measured wrong twice, both times by reading the `.span` sidecar as FRAMES. It is
SECONDS -- `bin/build_mon_native_song.py:_write_span` says so, and
`fidelity_common.part_span` repeats it. Read as frames, Shogoon-Rave gets a
4-second window instead of 24, too few onsets to measure, and the law appears to
be REFUTED. An audit that cannot be re-run is how that survived a cycle.

Two guards make a green reading mean something:

  * `n` is printed on every row and a row with fewer than MIN_N gaps is reported
    `few` rather than scored. A 100.0% over 3 gaps is not evidence -- this repo
    has shipped exactly that mistake (`fidelity_common.underpowered`).
  * `identity` is printed BESIDE `shift` always. A file where BOTH are high is
    not confirming the law, it is telling you the gaps are too uniform to
    discriminate (a constant gap sequence satisfies every shift trivially), and
    the row is flagged `flat`.

Usage:
    python pyscript/hardtrack_duration_law_sweep.py [--voice N] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2.fidelity_common import (  # noqa: E402
    part_span, psid_wrap, siddump_frames_full, siddump_note_onsets)
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo  # noqa: E402

BUILD_DIR = os.path.join(ROOT, "out", "hardtrack_native")
SID_DIR = os.path.join(ROOT, "SID", "Shogoon")

#: Below this many gaps a percentage is not reported -- see the module docstring.
MIN_N = 8

#: A gap series with fewer than this many DISTINCT values cannot discriminate a
#: shift from an identity, so the row is flagged rather than scored.
MIN_DISTINCT = 3

#: A row whose `shift` AND `identity` are BOTH at or above this cannot
#: discriminate between the law and its negation, however many distinct
#: values it carries -- see `measure`. Such rows are reported separately
#: and are NOT counted toward the LAW total.
AMBIG_BOTH = 90.0

#: The render lead the law is stated at: `offset[k] == og[k] - 3`. Swept over
#: -12..+12 per file rather than assumed, and it comes back -3 on every law row
#: independently -- a row whose best fit is some other C is not the law at a
#: different constant, it is a row the law does not describe (Intrigue fits
#: -12 at 0.0%, which is the sweep reporting that nothing fits).
LEAD_C = -3


def gate_onsets(frames, voice, f0, f1):
    """Gate-RISE frames for `voice` within [f0, f1)."""
    out, prev = [], False
    for i in range(f0, min(f1, len(frames))):
        on = bool(frames[i][0][voice]["wf"] & 1)
        if on and not prev:
            out.append(i)
        prev = on
    return out


def note_onsets(path, secs, voice, f1):
    """UNBRACKETED note-row frames -- siddump's own idea of a new note.

    NOT the same series as `gate_onsets`, and the difference is the whole reason
    this option exists. HardTrack ties and gates off from the pattern stream, so
    a new note row need not raise the gate and a re-gate need not carry a new
    note. The duration law was originally stated over THIS series; measuring it
    over gate rises and reporting the disagreement as a refutation would be
    comparing two different questions.
    """
    o = siddump_note_onsets(path, ["-a0", "-t%d" % secs])
    v = o[voice] if isinstance(o, (list, tuple)) else o.get(voice, [])
    return sorted({fr for fr, _n in v if fr < f1})


def gaps(ons):
    return [b - a for a, b in zip(ons, ons[1:])]


def agreement(a, b):
    """(matches, n) over the overlapping prefix -- never a percentage here, so a
    caller cannot accidentally average two rows of different weight."""
    n = min(len(a), len(b))
    return sum(x == y for x, y in zip(a[:n], b[:n])), n


def best_offset_c(ours, orig, og):
    """THE 2026-09-04 RELATION, recovered: `offset[k] == og[k] + C`, C swept.

    The original corpus table was measured this way -- per-note ABSOLUTE
    position, count-matched, with C swept per file -- and its script was never
    tracked. That is the whole reason a table claiming `law-exact` on
    Griffin_Score, Intrigue and For_Astoria_6 could not be defended when the
    gap-shift sweep read them CLEAN: there was nothing left to re-run.

    It is computed here BESIDE `shift` rather than instead of it, because the two
    are equivalent by telescoping and that equivalence is the check. From
    `ours[k] - orig[k] == og[k] + C` at every k,

        gg[k] = ours[k+1] - ours[k] = (orig[k+1] + og[k+1]) - (orig[k] + og[k])
              = og[k+1]

    -- C cancels. So a row cannot be law-exact under one relation and clean
    under the other ON THE SAME SERIES IN THE SAME WINDOW. When they disagree
    the series or the window differs, never the law, and `measure` says so.

    Returns (C, hits, n). C is None when the counts leave too few notes to fit.
    """
    n = min(len(ours), len(orig), len(og))
    if n < MIN_N:
        return (None, 0, n)
    off = [ours[k] - orig[k] for k in range(n)]
    best = (None, -1, n)
    for C in range(-12, 13):
        h = sum(off[k] == og[k] + C for k in range(n))
        if h > best[1]:
            best = (C, h, n)
    return best


def _probe(sf2_path, tmpdir):
    """PSID-wrap a built .sf2 so siddump will play it.

    The probe is named after the ARTIFACT and lives in a caller-owned temp dir:
    a shared constant filename is invisible while a sweep is serial and scores
    one song against another's audio the moment it is not (see
    `dmc_native_sweep._probe`, where that cost a corpus re-measure).
    """
    sf2 = open(sf2_path, "rb").read()
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(bytearray(sf2), info)
    stem = os.path.splitext(os.path.basename(sf2_path))[0]
    probe = os.path.join(tmpdir, "_ht_law_%s.sid" % stem)
    open(probe, "wb").write(psid_wrap(bytes(sf2[2:]), sla, 0x1000, 0x1003))
    return probe


def songs():
    """(stem, original .sid, part01 artifact) for every built HardTrack song."""
    out = []
    for f in sorted(os.listdir(BUILD_DIR)) if os.path.isdir(BUILD_DIR) else []:
        if not f.endswith("_part01.sf2"):
            continue
        stem = f[:-len("_part01.sf2")]
        orig = os.path.join(SID_DIR, stem + ".sid")
        if os.path.exists(orig):
            out.append((stem, orig, os.path.join(BUILD_DIR, f)))
    return out


def aligned_fit(oo, po):
    """THE LAW IS AN ALIGNMENT ARTIFACT, and this is the measurement that shows it.

    siddump FORCE-DISPLAYS every register on its first row (`CLAUDE.md`'s standing
    caveat), so frame 0 carries an "onset" that is not a note-on. The ORIGINAL
    always shows it. OUR RENDER shows it only when its own first note does not
    fire at frame ~1 -- a voice whose first note sits at tick 0 fires there and
    MERGES with the force-display, costing our list one leading entry.

    Compare the two lists index-by-index without accounting for that and the
    whole voice reads one note late, which is exactly `shift`. Measured over the
    settled set: 17 of 17 LAW files have their voice's first note at tick 0, and
    0 of 6 CLEAN files do -- a complete, exceptionless split.

    So: drop the original's frame-0 entry, then try our list BOTH ways and keep
    the better constant-offset fit. Returns (pct, C, n, which) where `which` says
    which hypothesis won -- "ours-real" (our first note merged with the phantom)
    or "ours-phantom" (our render shows its own).
    """
    o = oo[1:] if oo and oo[0] <= 2 else list(oo)
    best = (0.0, None, 0, None)
    for which, p_ in (("ours-real", list(po)),
                      ("ours-phantom", po[1:] if po and po[0] <= 2 else list(po))):
        n = min(len(o), len(p_))
        if n < MIN_N:
            continue
        for C in range(-16, 17):
            h = sum(p_[k] == o[k] + C for k in range(n))
            if 100.0 * h / n > best[0]:
                best = (100.0 * h / n, C, n, which)
    return best


def measure(stem, orig, part, voice, tmpdir, kind="gate"):
    """One row. `span` is SECONDS -- the unit that has been misread twice."""
    secs = part_span(part)
    if not secs:
        return dict(song=stem, status="no-span")
    f0, f1, t = 0, int(secs) * 50, int(secs) + 2
    probe = _probe(part, tmpdir)
    try:
        if kind == "note":
            oo = note_onsets(orig, t, voice, f1)
            po = note_onsets(probe, t, voice, f1)
        else:
            oo = gate_onsets(siddump_frames_full(orig, ["-a0", "-t%d" % t]),
                             voice, f0, f1)
            po = gate_onsets(siddump_frames_full(probe, ["-a0", "-t%d" % t]),
                             voice, f0, f1)
    finally:
        if os.path.exists(probe):
            os.remove(probe)
    og, gg = gaps(oo), gaps(po)
    counts = (len(oo), len(po))
    if not og or not gg:
        return dict(song=stem, status="silent", secs=int(secs))
    sm, sn = agreement(gg, og[1:])          # THE LAW: ours i == original's i+1
    im, inn = agreement(gg, og)             # the control: ours i == original's i
    oc, oh, on = best_offset_c(po, oo, og)
    ap, ac, an, aw = aligned_fit(oo, po)
    row = dict(song=stem, secs=int(secs), n=sn, counts=counts,
               shift=(100.0 * sm / sn if sn else None),
               identity=(100.0 * im / inn if inn else None),
               offset_c=oc, offset_law=(100.0 * oh / on if on else None),
               distinct=len(set(og)),
               aligned=(ap if aw else None), aligned_c=ac, aligned_n=an,
               aligned_via=aw)
    # THE CROSS-CHECK, not a second opinion: the relations are equivalent by
    # telescoping (see `best_offset_c`), so a split verdict means the two runs
    # were not over the same series or the same window. Name it on the row
    # rather than printing two numbers and letting a reader pick.
    # ONLY ON A ROW BIG ENOUGH FOR BOTH RELATIONS TO HAVE AN OPINION. Below
    # MIN_N `best_offset_c` declines and returns C=None, while `shift` still
    # divides by its 2 or 5 gaps and prints a confident 100.0 -- so comparing
    # them there reports a DISAGREEMENT whose real content is that one side
    # refused. Measured: Ritual_II_tune_2 (n=2) and Trance (n=5) were the only
    # two rows the first version of this check flagged, and neither is a
    # disagreement about the law. `None` means "not asked", which must stay
    # distinguishable from False.
    row["relations_agree"] = (
        None if sn < MIN_N else
        (row["shift"] == 100.0) == (oc == LEAD_C and row["offset_law"] == 100.0))
    if sn < MIN_N:
        row["status"] = "few"
    elif row["distinct"] < MIN_DISTINCT:
        row["status"] = "flat"
    elif (row["shift"] or 0) >= AMBIG_BOTH and (row["identity"] or 0) >= AMBIG_BOTH:
        # BOTH HIGH MEANS THE MEASURE CANNOT DISCRIMINATE, and this is the guard
        # MIN_DISTINCT cannot provide. `shift` and `identity` ask opposite
        # questions; a row answering YES to both is answering neither, because a
        # sufficiently PERIODIC original satisfies the shift trivially -- the
        # module docstring says so and nothing enforced it until now.
        #
        # Distinctness cannot see this: the degenerate rows carry 3 to 6
        # distinct values. Teekkno reads shift 100.0 AND identity 99.0 over 524
        # gaps, and was counted toward the headline LAW figure; Shogoon-Rave,
        # the file the law was originally attributed on, reads 100.0 / 93.5.
        # Tribute_to_Laxity (100.0 / 12.5) is what a discriminating row looks
        # like.
        row["status"] = "ambiguous"
    else:
        row["status"] = "ok"
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--voice", type=int, default=1,
                    help="0-based voice (default 1, the voice the law was found on)")
    ap.add_argument("--json", help="write the rows here as JSON")
    # DEFAULT IS "note", CHANGED 2026-09-10, AND THE REASON IS THE WHOLE POINT.
    # It used to be "gate", and a bare run therefore printed LAW: 0 of 33 --
    # which reads exactly like a refutation and was recorded as one across three
    # separate cycles. It is not. Under gate rises the build reproduces the
    # original's gaps (identity 100.0 on 26 of 27 scored), and when gg == og the
    # rate of gg[i] == og[i+1] is ALGEBRAICALLY the original's own self-shift
    # rate -- the build drops out of the number entirely.
    #
    # Same corpus, same artifacts, same script, --onsets note: LAW 20 of 33 with
    # 6 clean controls, reproducing the recorded figure song for song.
    # Tribute_to_Laxity settles which reading is informative: shift 100.0 while
    # the original is only 12.9% self-shifted.
    #
    # MIN_DISTINCT cannot screen the degenerate case -- those files carry 3 to 6
    # distinct values. PERIODICITY, not flatness, is what destroys it.
    ap.add_argument("--onsets", choices=("gate", "note"), default="note",
                    help="onset definition: siddump's unbracketed NOTE rows "
                         "(default -- the reading the law was stated over and "
                         "the one that discriminates), or gate rises, where the "
                         "measure is degenerate whenever identity is high")
    ap.add_argument("--only", nargs="*", help="restrict to these song stems")
    a = ap.parse_args(argv)

    todo = songs()
    if a.only:
        todo = [t for t in todo if t[0] in set(a.only)]
    if not todo:
        print("no built HardTrack part01 artifacts under out/hardtrack_native", file=sys.stderr)
        return 1

    rows = []
    with tempfile.TemporaryDirectory(prefix="ht_law_") as tmp:
        print("onset definition: %s" % a.onsets)
        print("%-28s %5s %5s %8s %9s %5s %10s %5s  %s"
              % ("song", "span", "n", "shift%", "identity%", "dist",
                 "offsetlaw%", "C", "status"))
        for stem, orig, part in todo:
            r = measure(stem, orig, part, a.voice, tmp, a.onsets)
            rows.append(r)
            print("%-28s %5s %5s %8s %9s %5s %10s %5s  %s"
                  % (r["song"], r.get("secs", "-"), r.get("n", "-"),
                     "-" if r.get("shift") is None else "%.1f" % r["shift"],
                     "-" if r.get("identity") is None else "%.1f" % r["identity"],
                     r.get("distinct", "-"),
                     "-" if r.get("offset_law") is None else "%.1f" % r["offset_law"],
                     "-" if r.get("offset_c") is None else "%d" % r["offset_c"],
                     r["status"]))

    ok = [r for r in rows if r["status"] == "ok"]
    law = [r for r in ok if r["shift"] == 100.0]
    clean = [r for r in ok if r["identity"] and r["identity"] >= 90.0
             and (r["shift"] or 0) < 90.0]
    print()
    print("scored %d of %d songs (%d few, %d flat, %d silent/no-span)"
          % (len(ok), len(rows),
             sum(r["status"] == "few" for r in rows),
             sum(r["status"] == "flat" for r in rows),
             sum(r["status"] in ("silent", "no-span") for r in rows)))
    ambig = [r for r in rows if r["status"] == "ambiguous"]
    # ---------------------------------------------------------------------
    # THE LAW IS REFUTED, and this block is what refutes it. `shift` below is
    # retained because it is the historical figure every earlier record quotes,
    # NOT because it measures a defect. See `aligned_fit`: the original always
    # carries siddump's force-display onset at frame 0 and our render carries it
    # only when its own first note does not fire at frame ~1, so an
    # index-by-index comparison reads a whole voice one note late.
    al = [r for r in rows if r.get("aligned") is not None]
    ok = [r for r in al if r["aligned"] >= 99.0]
    print()
    print("ALIGNED  ours[j]==orig_real[j]+C once the frame-0 force-display is")
    print("         accounted for: %d of %d rows at >=99%%%s"
          % (len(ok), len(al),
             ("  (C: " + ", ".join(sorted({str(r["aligned_c"]) for r in ok})) + ")")
             if ok else ""))
    if al:
        via = {}
        for r in al:
            via[r["aligned_via"]] = via.get(r["aligned_via"], 0) + 1
        print("         hypothesis chosen: %s"
              % ", ".join("%s=%d" % kv for kv in sorted(via.items())))
    print("         ^ a row that is 'LAW' under `shift` and >=99% here carries NO")
    print("           duration defect -- the two numbers disagree because the")
    print("           SERIES were misaligned, never because the player is late.")
    print()
    print("LAW  gg[i]==og[i+1] at EXACTLY 100.0%%: %d   (discriminating rows only)"
          % len(law))
    print("AMBIGUOUS  shift AND identity both >=%.0f: %d  (%s)"
          % (AMBIG_BOTH, len(ambig),
             ", ".join(r["song"] for r in ambig) or "none"))
    if ambig:
        print("  ^ NOT counted as law OR clean: a periodic original satisfies the")
        print("    shift trivially, so these rows answer neither question.")
    print("CLEAN  identity>=90 and shift<90     : %d  (%s)"
          % (len(clean), ", ".join(r["song"] for r in clean) or "none"))

    # THE CROSS-CHECK IS A HEADLINE, NOT A COLUMN. A reader comparing `shift`
    # against `offsetlaw` by eye is how the 2026-09-04 table went unchallenged
    # for six days, so the disagreement count is printed whether it is zero or
    # not -- a check that only speaks up when it fires is indistinguishable from
    # a check that is not running.
    split = [r for r in rows if r.get("relations_agree") is False]
    print("RELATIONS  gg[i]==og[i+1] vs offset[k]==og[k]%+d, same series and"
          % LEAD_C)
    print("           window: %d of %d rows DISAGREE%s"
          % (len(split), sum(r.get("relations_agree") is not None
                             for r in rows),
             (" (%s)" % ", ".join(r["song"] for r in split)) if split else ""))
    if split:
        print("  ^ The relations are EQUIVALENT by telescoping, so a disagreement")
        print("    is in the SERIES or the WINDOW, not in the law. Do not pick the")
        print("    more convenient number -- find out which input differs.")
    if a.json:
        json.dump(rows, open(a.json, "w", encoding="utf-8"), indent=1)
        print("wrote", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
