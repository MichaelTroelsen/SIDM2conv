"""`inject_sequences` flattens every note's duration, and the path IS production.

THE TASK ASKED WHICH OF TWO THINGS THIS IS, and the answer is neither of the
comfortable ones. It is not dead code, and it is not a documented limit that no
shipped path reaches: the branch is reachable from a production conversion, so
these tests pin the CURRENT behaviour and the REACHABILITY rather than asserting
a fix that cannot be made from this module.

THE REACHABILITY CHAIN, established by reading the call sites, not the imports:
    sidm2/conversion_pipeline.py:567,1082,1385   SF2Writer(...)          production
      -> sidm2/sf2_writer.py:271                 inject_music_data_into_template
        -> driver11_section_injectors.py:977     if data.sequences and
                                                    driver_info.sequence_start:
          -> inject_sequences(...)               DEFAULT_DURATION = 0x80

WHICH CONVERSIONS REACH IT, which is the part that decides how much it matters:
  * sidm2/laxity_analyzer.py:596 builds ExtractedData with `sequences=[]`, so
    the `if data.sequences` guard is False and the NATIVE LAXITY PATH NEVER
    REACHES THIS. That path is the 99.93-100% one, and it is unaffected.
  * sidm2/sf2_player_parser.py:448,520,586 DOES populate `sequences`, so the
    SF2-exported -> Driver 11 path reaches it. That is the path CLAUDE.md rates
    at 100%.

WHY IT CANNOT BE FIXED HERE. models.py's SequenceEvent carries `instrument`,
`command`, `note` and nothing else -- there is no duration field for the
injector to read, which is exactly what its own TODO says. Threading one
requires writing sidm2/models.py, which is NOT in this task's declared touches,
so this module records the finding instead of half-making the change.

THE LOSS IS TWO-SIDED, and the second half is not in the TODO: a source duration
byte that arrives as `event.note` in [0x80, 0x9F] is `continue`d -- dropped
outright -- and then a fresh DEFAULT_DURATION is written for the note that
follows. So the injector does not merely fail to carry a duration it was given;
it discards one when it is handed it.
"""
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from sidm2 import driver11_section_injectors as INJ    # noqa: E402
from sidm2.models import SequenceEvent                  # noqa: E402

SRC = os.path.join(_ROOT, "sidm2", "driver11_section_injectors.py")


def test_sequence_event_has_no_duration_field_at_all():
    """The reason the injector cannot preserve a duration, pinned at the source.

    If a `duration` field ever appears here, this test fails and that is the
    signal to go back and thread it through inject_sequences -- which is the
    fix this task could not make from inside its own touches.
    """
    fields = set(getattr(SequenceEvent, "__dataclass_fields__", {}))
    assert fields == {"instrument", "command", "note"}, fields
    assert "duration" not in fields, (
        "SequenceEvent now carries a duration -- inject_sequences must stop "
        "writing DEFAULT_DURATION and use it")


def test_default_duration_is_written_for_every_note():
    """Behaviour pin: a constant, unconditional, once per surviving event."""
    src = open(SRC, encoding="utf-8").read()
    assert re.search(r"^\s*DEFAULT_DURATION\s*=\s*0x80\s*$", src, re.M)
    body = src[src.index("def inject_sequences("):]
    body = body[:body.index("\ndef ", 1)]
    assert "output[seq_offset] = DEFAULT_DURATION" in body, (
        "the unconditional duration write is gone -- if it was replaced by a "
        "real duration, update this module's docstring and the task record")


def test_a_source_duration_byte_is_DROPPED_not_carried():
    """The half the TODO does not mention. A note byte in [0x80,0x9F] is skipped.

    Asserted on the source rather than by running the injector, because
    inject_sequences needs a driver_info/template pair this test has no honest
    way to fabricate -- and a fabricated one would pin my fixture, not the code.
    """
    src = open(SRC, encoding="utf-8").read()
    body = src[src.index("def inject_sequences("):]
    body = body[:body.index("\ndef ", 1)]
    code = "\n".join(ln.split("#", 1)[0] for ln in body.splitlines())
    assert re.search(r"if\s+0x80\s*<=\s*event\.note\s*<=\s*0x9F\s*:\s*\n\s*continue",
                     code), "the skip is gone -- re-check whether durations now survive"


def test_the_production_reachability_chain_is_still_there():
    """If any link breaks, the blast radius recorded above is wrong.

    This is the assertion that stops the finding going stale: the whole verdict
    rests on SF2Writer being production and reaching this injector.
    """
    writer = open(os.path.join(_ROOT, "sidm2", "sf2_writer.py"), encoding="utf-8").read()
    assert "driver11_section_injectors.inject_music_data_into_template(" in writer
    inj = open(SRC, encoding="utf-8").read()
    assert re.search(r"if\s+data\.sequences\s+and\s+driver_info\.sequence_start\s*:\s*\n"
                     r"\s*inject_sequences\(", inj), (
        "the guard that decides which conversions reach the flattening changed")
    pipe = open(os.path.join(_ROOT, "sidm2", "conversion_pipeline.py"), encoding="utf-8").read()
    assert "SF2Writer(extracted" in pipe, "SF2Writer is no longer used by the pipeline"


def test_the_laxity_path_is_exempt_because_it_ships_no_sequences():
    """Laxity builds ExtractedData with sequences=[], so the guard is False.

    Pinned because it is the reason this defect does NOT touch the 99.93-100%
    native path -- and if that ever changes, the blast radius grows silently.
    """
    lax = open(os.path.join(_ROOT, "sidm2", "laxity_analyzer.py"), encoding="utf-8").read()
    assert re.search(r"sequences\s*=\s*\[\]", lax), (
        "laxity_analyzer no longer passes an empty sequences list -- the native "
        "Laxity path may now reach inject_sequences and get flattened durations")


# ---------------------------------------------------------------------------
# GROUND TRUTH: what a file SID FACTORY II ITSELF WROTE actually contains.
#
# This question has now flipped three times in this repo's records, so it is
# pinned against a file no analysis of ours produced:
# bin/music/Driver 11 Test - Arpeggio.sf2, shipped with the editor.
#
# THE ANSWER: the on-disk Driver 11 sequence stream is the PACKED,
# variable-length, self-describing grammar -- $C0+ command, $A0-$BF instrument,
# $80-$9F duration, $00-$7E note, $7F end -- and it DOES carry duration bytes.
# SF2_FORMAT_SPEC.md's "three columns per row" is the EDITOR's view of it.
#
# A RETRACTION THIS PINS, because it was published in runs.jsonl and would
# otherwise be believed: a later cycle claimed "Driver 11 and Laxity are two
# formats, so sf2_player_parser's fixed 3-byte triples are CORRECT for Driver
# 11". That is FALSE. Read as triples, this real file yields 0 of 8 rows with a
# legal instrument byte. The triples are a mis-parse, the comment above
# (78d7ef2) was right, and sf2_player_parser is the defect.
# ---------------------------------------------------------------------------

_SF2II_REFERENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bin", "music", "Driver 11 Test - Arpeggio.sf2")

# The packed run inside that file, at raw offset 0x19AE (address $272A).
_PACKED_RUN = bytes([0xC1, 0xA0, 0x80, 0x30, 0x30, 0x00, 0xC2, 0x81,
                     0x30, 0x30, 0xC3, 0x80, 0x2E, 0x00, 0x2E, 0x2E,
                     0x00, 0xC4, 0x2E, 0x00, 0x81, 0x2E, 0x7F])


def _reference_or_skip():
    if not os.path.exists(_SF2II_REFERENCE):
        pytest.skip("SF2II reference file not in this tree: %s" % _SF2II_REFERENCE)
    return _SF2II_REFERENCE


def test_the_editors_own_file_carries_the_packed_grammar_at_that_offset():
    """The bytes are read from disk, not asserted from memory.

    If the shipped file ever changes, this fails loudly rather than letting the
    two tests below pass against a stale constant.
    """
    with open(_reference_or_skip(), "rb") as fh:
        data = fh.read()
    assert data[0x19AE:0x19AE + len(_PACKED_RUN)] == _PACKED_RUN, (
        "the reference file's packed run moved or changed; re-locate it before "
        "trusting the two tests below")


def test_driver11_on_disk_sequences_ARE_packed_and_DO_carry_durations():
    """unpack_sequence parses SF2II's own bytes cleanly, terminator and all."""
    _reference_or_skip()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sf2_viewer_core import unpack_sequence
    rows = unpack_sequence(_PACKED_RUN)
    assert rows, "the packed grammar did not parse SF2II's own sequence bytes"
    # $81 appears twice in the run -> duration 1. A format with no duration byte
    # could not produce a non-zero duration here.
    assert any(r["duration"] > 0 for r in rows), (
        "no row carried a duration, yet $81 is present in the on-disk bytes")
    assert any(0xC0 <= r["command"] <= 0xFF for r in rows), "no command byte decoded"
    assert any(0xA0 <= r["instrument"] <= 0xBF for r in rows), "no instrument byte decoded"


def test_reading_that_same_run_as_FIXED_TRIPLES_is_incoherent():
    """The refutation, made mechanical.

    sf2_player_parser reads (instrument, command, note) 3-byte groups. Against
    real Driver 11 bytes that yields instrument values outside $A0-$BF on every
    single group -- which is what "mis-parse" means here, and why the triples
    cannot be the on-disk truth for this driver.
    """
    _reference_or_skip()
    triples = [_PACKED_RUN[i:i + 3] for i in range(0, 24, 3)
               if len(_PACKED_RUN[i:i + 3]) == 3]
    legal = [t for t in triples if 0xA0 <= t[0] <= 0xBF]
    assert len(legal) == 0, (
        "a triple reading now yields %d legal instrument bytes of %d -- if this "
        "ever becomes non-zero the refutation needs re-deriving, not editing"
        % (len(legal), len(triples)))
