"""Blackbird emits no `.span`, and its prune fork is correct BECAUSE of that.

`bin/build_blackbird_native_song.py` carries a verbatim fork of MoN's
`prune_stale_parts` that globs `.sf2` ONLY. The MoN original globs `.sf2`,
`.sf2.span` and `.sf2.prov`; the fork missed that fix, which is what its own
import comment says happened.

That omission is HARMLESS TODAY -- pruning sidecars that are never written is a
no-op -- and it is one commit from being silently wrong. The moment anything
teaches this builder to emit a span or a prov, the prune leaves orphaned
sidecars beyond partNN: the phantom-file inventory `prune_stale_parts` exists to
prevent, and the shape that let `out/dmc` accumulate 352 stale spans.

So these tests pin the COUPLING rather than either half alone. If a span ever
appears, the first test fails and names the prune fork as the thing to update.
Adding the globs pre-emptively was rejected: dead code nothing exercises is how
the fork drifted from its original in the first place.

Why Blackbird legitimately has no spans, in one line: `_write_span` bounds a
comparison against a siddump of the original, and siddump cannot drive an LFT
rip at all -- the builder drives `BlackbirdSim` instead. Full reasoning in
docs/players/BLACKBIRD.md.
"""
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

BUILDER = os.path.join(_ROOT, "bin", "build_blackbird_native_song.py")
OUT = os.path.join(_ROOT, "out", "blackbird")


def _prune_source():
    """The body of the Blackbird fork's prune_stale_parts, comments stripped.

    Comments are removed because this file DISCUSSES `.span` at length while
    never globbing it -- a naive substring test would read the prose as code,
    which is the exact confusion this module exists to prevent.
    """
    src = open(BUILDER, encoding="utf-8").read()
    i = src.index("def prune_stale_parts(")
    j = src.index("\ndef ", i + 1)
    body = src[i:j]
    body = body[body.index('"""', body.index('"""') + 3) + 3:]   # drop docstring
    return "\n".join(ln.split("#", 1)[0] for ln in body.splitlines()
                     if not ln.strip().startswith("#"))


@pytest.mark.skipif(not os.path.isdir(OUT), reason="out/blackbird not built")
def test_no_span_or_prov_sidecar_exists_so_the_sf2_only_prune_is_correct():
    """THE COUPLING. If this fails, the prune fork must gain the sidecar globs.

    Not "spans are bad" -- if Blackbird gains a span for a good reason, that is
    fine. What is not fine is gaining one while prune_stale_parts still globs
    `.sf2` only, because then a rebuild-at-fewer-parts strands the sidecars.
    """
    names = os.listdir(OUT)
    spans = [n for n in names if n.endswith(".span") or n.endswith(".prov")]
    assert spans == [], (
        "Blackbird now emits sidecars (%s). bin/build_blackbird_native_song.py's "
        "prune_stale_parts globs '.sf2' only -- add '.sf2.span'/'.sf2.prov' to it, "
        "matching bin/build_mon_native_song.py, or these will be stranded beyond "
        "partNN on a rebuild that packs into fewer parts." % spans[:5])
    assert any(n.endswith(".sf2") for n in names), "no artifacts at all -- vacuous"


def test_the_builder_never_writes_a_span():
    """The emitter half, pinned at the source so it holds without a built corpus.

    `_write_span` is MoN's; the Blackbird builder imports build_mon_native_song
    as BM for its staging machinery but must not be calling that particular
    piece of it.
    """
    src = open(BUILDER, encoding="utf-8").read()
    code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines()
                     if not ln.strip().startswith("#"))
    assert "_write_span" not in code, "the builder now writes spans -- see the coupling test"
    assert "BM._write_span" not in code


def test_the_prune_fork_globs_sf2_only_and_that_is_the_thing_being_pinned():
    """Pins WHAT the fork does, so a change to it is deliberate rather than drift.

    The MoN original this was forked from globs three patterns. Recording the
    difference here means the next person to touch either copy sees that they
    diverge on purpose, not by accident.
    """
    body = _prune_source()
    assert '_part*.sf2"' in body or "_part*.sf2'" in body
    assert ".sf2.span" not in body, "the fork gained a span glob -- update BLACKBIRD.md"
    assert ".sf2.prov" not in body

    mon = open(os.path.join(_ROOT, "bin", "build_mon_native_song.py"),
               encoding="utf-8").read()
    i = mon.index("def prune_stale_parts(")
    mon_body = mon[i:mon.index("\ndef ", i + 1)]
    # the ORIGINAL does glob all three -- if it stops, this comparison is stale
    assert ".sf2.span" in mon_body and ".sf2.prov" in mon_body, (
        "build_mon_native_song's prune no longer globs sidecars; the divergence "
        "recorded in docs/players/BLACKBIRD.md needs re-checking")
