"""`_extract_sequences_from_sf2` read the FILE TAIL and called it music.

THE DEFECT, measured rather than reasoned about. The sequence region is derived
as `0x0903 - load_addr + 2`. $0903 is BELOW the load address of every SF2 file
in this tree, so the subtraction is negative -- and a negative index in Python
does not raise, it reads from the END of the buffer. Measured: 364 of 364
out/*.sf2 (load $0D7E -> -1145), 42 of the 46 marker-carrying SIDs, and SID
Factory II's own bin/music/Driver 11 Test - Arpeggio.sf2 (same -1145).

WHAT IT PRODUCED on that reference file, whose real content is TWO sequences:

    235 sequences, orderlists [623, 0, 11]
    seq0 event 0: instrument=$01 command=$FF note=$84

Neither $01 nor $FF is a legal value for those fields. The output was
confidently wrong, returned rc=0, and warned about nothing.

WHAT THIS FIXES AND WHAT IT DOES NOT. It makes the parser REFUSE, matching this
repo's own convention (fidelity_common.run_siddump raises rather than returning
'' on failure; SDIModule.__init__ raises). The caller at sf2_player_parser.py
already wraps the call in try/except and keeps empty sequences, so a refusal
degrades to "no sequences plus a warning" rather than to a crash -- which is the
honest answer.

IT DOES NOT MAKE THE PARSER CORRECT. Even at a valid offset it reads FIXED
3-byte (instrument, command, note) groups, and the on-disk Driver 11 stream is
the PACKED variable-length grammar. That is pinned separately, against the
editor's own bytes, in pyscript/test_driver11_section_injectors.py, where a
triple reading yields 0 of 7 legal instrument bytes.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from sidm2.sf2_player_parser import SF2PlayerParser      # noqa: E402
from sidm2.errors import InvalidInputError               # noqa: E402

_REFERENCE = os.path.join(_ROOT, "bin", "music", "Driver 11 Test - Arpeggio.sf2")


def _extract(data, load_addr):
    inst = SF2PlayerParser.__new__(SF2PlayerParser)
    return SF2PlayerParser._extract_sequences_from_sf2(inst, data, load_addr)


def test_a_load_address_above_0903_is_REFUSED_not_read_from_the_tail():
    """The whole defect in one assertion.

    Synthetic rather than file-based so it holds even in a tree without SF2II's
    files: any load address above $0903 drives the offset negative.
    """
    data = bytes([0x7E, 0x0D]) + bytes(4096)      # load $0D7E, as every real file
    with pytest.raises(InvalidInputError):
        _extract(data, 0x0D7E)


def test_the_refusal_names_the_constant_and_the_load_address():
    """A refusal a caller cannot act on is only half the fix.

    The message has to say WHICH constant and WHICH load address disagree,
    because the next reader's question is 'is the constant wrong or is this file
    unusual?' -- and the answer here is the constant.
    """
    data = bytes([0x7E, 0x0D]) + bytes(4096)
    with pytest.raises(InvalidInputError) as ei:
        _extract(data, 0x0D7E)
    msg = str(ei.value)
    assert "0903" in msg, "the refusal does not name the constant it derives from"
    assert "0D7E" in msg, "the refusal does not name the load address"


def test_a_load_address_BELOW_0903_still_parses():
    """The guard must not refuse the case the constant WAS written for.

    A file loading at $0801 puts the region at a positive offset, so the guard
    has to let it through -- otherwise this is a disable, not a fix.
    """
    data = bytes([0x01, 0x08]) + bytes(8192)
    sequences, orderlists = _extract(data, 0x0801)
    assert isinstance(sequences, list) and isinstance(orderlists, list)
    assert len(orderlists) == 3


@pytest.mark.skipif(not os.path.exists(_REFERENCE),
                    reason="SF2II reference file not in this tree")
def test_the_editors_own_file_is_refused_rather_than_yielding_235_sequences():
    """The regression this exists to prevent, on a real file.

    Before the guard this returned 235 sequences and orderlists [623, 0, 11]
    for a file containing two sequences. If the guard is ever removed, this
    goes back to passing silently with nonsense -- so the assertion is that it
    RAISES, not that some count is right.
    """
    with open(_REFERENCE, "rb") as fh:
        data = fh.read()
    load_addr = data[0] | (data[1] << 8)
    assert load_addr == 0x0D7E, "reference file's load address moved"
    with pytest.raises(InvalidInputError):
        _extract(data, load_addr)


# ---------------------------------------------------------------------------
# THE PACKED-STREAM DECODE, pinned against the editor's OWN unpacker.
#
# sf2_player_parser used to walk the sequence region as fixed 3-byte
# (instrument, command, note) groups. The on-disk Driver 11 stream is
# variable-length and self-describing, and SF2 II's own file is the disproof:
# read as triples it yields 0 of 7 legal instrument bytes.
#
# The reference bytes below are VERBATIM from bin/music/Driver 11 Test -
# Arpeggio.sf2 at raw offset 0x19AE (address $272A, load $0D7E) -- SF2 II's own
# shipped file, which no analysis of ours produced. They are inlined rather than
# read from disk so these tests run on any clone and cannot go stale against a
# moved offset; pyscript/test_driver11_section_injectors.py separately pins that
# the file still carries them AT that offset.
#
# The assertion is EQUIVALENCE with pyscript/sf2_viewer_core.unpack_sequence,
# not a hand-written expectation. That matters: a hand-written expectation is
# just this decoder's output copied down, and would pass for any grammar I
# happened to implement. unpack_sequence is documented from the editor source
# and predates this change, so agreeing with it is evidence.
# ---------------------------------------------------------------------------

_EDITOR_SEQUENCE = bytes([
    0xC1, 0xA0, 0x80, 0x30, 0x30, 0x00, 0xC2, 0x81, 0x30, 0x30, 0xC3, 0x80,
    0x2E, 0x00, 0x2E, 0x2E, 0x00, 0xC4, 0x2E, 0x00, 0x81, 0x2E, 0x7F,
])


def _viewer_unpack(blob):
    """pyscript/sf2_viewer_core.unpack_sequence, as (instrument, command, note)."""
    import sf2_viewer_core
    return [(e["instrument"], e["command"], e["note"])
            for e in sf2_viewer_core.unpack_sequence(blob)]


def test_the_decode_matches_the_editors_own_unpacker_event_for_event():
    """THE TEST THIS CHANGE EXISTS FOR.

    Same bytes, two independently-written decoders, identical event stream.
    """
    from sidm2.sf2_player_parser import unpack_packed_sequence

    got, offset = unpack_packed_sequence(_EDITOR_SEQUENCE, 0)
    ours = [(e.instrument, e.command, e.note) for e in got]
    theirs = _viewer_unpack(_EDITOR_SEQUENCE)

    # unpack_sequence stops AT the end marker and does not emit it; ours emits
    # it so the caller can see a terminated sequence. Compare the common part
    # and assert the terminator separately rather than hiding the difference.
    assert ours[-1] == (0x80, 0x80, 0x7F), ours[-1]
    assert ours[:-1] == theirs, (
        "decoders disagree:\n  ours   %s\n  viewer %s" % (ours[:-1], theirs))
    assert offset == len(_EDITOR_SEQUENCE), offset


def test_the_old_fixed_triple_walk_would_NOT_have_matched():
    """The positive control: without it, the test above proves nothing.

    If the two decoders agreed on this blob no matter what, agreement would be
    a property of the input rather than of the fix. Reading the same bytes as
    fixed triples gives a different length AND illegal instrument bytes, which
    is exactly the defect that motivated the change.
    """
    triples = [(_EDITOR_SEQUENCE[i], _EDITOR_SEQUENCE[i + 1], _EDITOR_SEQUENCE[i + 2])
               for i in range(0, len(_EDITOR_SEQUENCE) - 2, 3)]
    legal_instr = [t for t in triples if 0xA0 <= t[0] <= 0xBF]
    assert not legal_instr, (
        "the triple reading suddenly yields legal instrument bytes %s -- the "
        "premise of this change needs re-checking" % legal_instr)
    assert len(triples) != len(_viewer_unpack(_EDITOR_SEQUENCE))


def test_duration_is_EXPANDED_into_sustain_rows_not_dropped():
    """`$81` = duration 1, so its note must be followed by one $7E sustain.

    SequenceEvent has no duration field and this change deliberately did not
    add one -- the editor's unpacker expands duration the same way, so the two
    streams stay comparable. If someone later adds the field and stops
    expanding, this fails and the equivalence test above fails with it.
    """
    from sidm2.sf2_player_parser import unpack_packed_sequence

    got, _ = unpack_packed_sequence(bytes([0xA0, 0x81, 0x30, 0x7F]), 0)
    notes = [e.note for e in got]
    assert notes == [0x30, 0x7E, 0x7F], notes
    assert got[0].instrument == 0xA0
    assert got[1].instrument == 0x80, "a sustain row must not repeat the instrument"


def test_a_gate_off_expands_to_gate_off_rows_not_sustains():
    """Note $00 with a duration sustains as $00, not $7E -- mirrored from
    unpack_sequence, where the sustain value is conditional on the note."""
    from sidm2.sf2_player_parser import unpack_packed_sequence

    got, _ = unpack_packed_sequence(bytes([0x82, 0x00, 0x7F]), 0)
    assert [e.note for e in got] == [0x00, 0x00, 0x00, 0x7F], [e.note for e in got]


def test_the_decoder_reports_where_the_next_sequence_starts():
    """Sequences are stored back to back, so a wrong end offset silently
    shifts every later sequence. Two concatenated sequences must decode
    independently."""
    from sidm2.sf2_player_parser import unpack_packed_sequence

    blob = bytes([0xA0, 0x30, 0x7F]) + bytes([0xA1, 0x40, 0x7F])
    first, off = unpack_packed_sequence(blob, 0)
    assert off == 3, off
    second, off2 = unpack_packed_sequence(blob, off)
    assert off2 == 6, off2
    assert [e.note for e in first] == [0x30, 0x7F]
    assert [e.note for e in second] == [0x40, 0x7F]
    assert second[0].instrument == 0xA1


# ---------------------------------------------------------------------------
# CHARACTERISATION AGAINST THE EDITOR'S OWN SHIPPED EXPORTS (bin/music/*.sf2).
#
# Traced 2026-09-05, this module had 118 of 713 lines executed by its own test
# file, and only TWO functions had any body coverage -- unpack_packed_sequence
# and _extract_sequences_from_sf2. Every other function showed one line: its
# `def`. That included the whole public entry path.
#
# These pin WHAT IS, not what should be. They use `_parse_sf2_tables`, which
# takes SF2 bytes directly and so can run on real material -- unlike `extract()`,
# which needs an SF2-EXPORTED SID, and there are ZERO of those in the 1,524-file
# SID/ corpus (runs.jsonl:sf2-exported-100pct-is-by-construction-never-measured).
# That is why the entry path stays uncovered here and is not an oversight.
# ---------------------------------------------------------------------------

from pathlib import Path as _Path                                  # noqa: E402

_MUSIC = _Path(__file__).resolve().parent.parent / "bin" / "music"
_D11 = _MUSIC / "Driver 11 Test - Arpeggio.sf2"


def _tables(path):
    from sidm2.sf2_player_parser import SF2PlayerParser
    inst = SF2PlayerParser.__new__(SF2PlayerParser)
    blob = path.read_bytes()
    load = int.from_bytes(blob[:2], "little")
    return SF2PlayerParser._parse_sf2_tables(inst, blob, load), load


@pytest.mark.skipif(not _D11.exists(), reason="bin/music/Driver 11 Test - Arpeggio.sf2 absent")
def test_a_real_driver11_export_yields_its_nine_tables():
    """The baseline the fixed-triples work needed and did not have.

    Recorded from SF2 II's own shipped file so a future change to table
    discovery has something to differ from. The counts are geometry, not
    content -- three of these four files carry different music.
    """
    tables, load = _tables(_D11)
    assert load == 0x0D7E, hex(load)
    assert set(tables) == {"Commands", "Instruments", "Wave", "Pulse", "Filter",
                           "Arpeggio", "Tempo", "HR", "Init"}, sorted(tables)
    assert tables["Instruments"]["columns"] == 6
    assert tables["Instruments"]["rows"] == 32
    assert tables["Wave"]["columns"] == 2 and tables["Wave"]["rows"] == 256
    assert tables["Filter"]["columns"] == 3 and tables["Filter"]["rows"] == 256
    assert tables["HR"]["rows"] == 16


@pytest.mark.skipif(not _MUSIC.is_dir(), reason="bin/music absent")
def test_all_four_driver11_exports_share_ONE_table_geometry():
    """This is the measurable content of the docs' 'by construction' claim.

    docs/players/DRIVER11.md argues SF2-exported files convert at 100% because
    'it already uses Driver 11's structure'. The checkable part of that is that
    the structure is FIXED per driver, and here it is: four different songs,
    one geometry.
    """
    files = sorted(_MUSIC.glob("Driver 11 Test - *.sf2"))
    assert len(files) == 4, [f.name for f in files]
    geoms = set()
    for f in files:
        t, load = _tables(f)
        assert load == 0x0D7E, (f.name, hex(load))
        # POSITIVE CONTROL, PER FILE. Without it this test passes when the
        # parse returns NOTHING: four empty geometries are trivially identical,
        # so `len(geoms) == 1` holds for the completely broken case. A mutation
        # stubbing the parse to {} passed this test until this line was added.
        assert len(t) == 9, "%s parsed to %d tables, expected 9" % (f.name, len(t))
        geoms.add(tuple(sorted((k, v["address"], v["columns"], v["rows"])
                               for k, v in t.items())))
    assert len(geoms) == 1, "the four Driver 11 exports no longer agree"


@pytest.mark.skipif(not _MUSIC.is_dir(), reason="bin/music absent")
def test_table_geometry_is_PER_DRIVER_so_one_constant_cannot_serve_all():
    """Why a hardcoded table offset is the wrong shape for this parser.

    Across the 11 shipped exports there are SIX distinct geometries, and table
    COUNT alone runs 4..9 -- Driver 11 has nine (with Arpeggio and HR), Drivers
    12/13/15/16 have four. `sidm2/sf2_packer.py` carries fixed
    SEQUENCE/INSTRUMENT/WAVE/PULSE/FILTER offsets; this test records that such
    constants describe at most one driver.

    POSITIVE CONTROL FIRST: if _parse_sf2_tables returned nothing the
    'six geometries' count would be meaningless.
    """
    files = sorted(_MUSIC.glob("*.sf2"))
    assert len(files) >= 10, [f.name for f in files]
    geoms, counts = set(), []
    for f in files:
        t, _ = _tables(f)
        assert t, "%s parsed to NO tables -- control failed" % f.name
        counts.append(len(t))
        geoms.add(tuple(sorted((k, v["address"], v["columns"], v["rows"])
                               for k, v in t.items())))
    assert min(counts) == 4 and max(counts) == 9, sorted(set(counts))
    assert len(geoms) == 6, (
        "%d distinct table geometries across %d exports, was 6" % (len(geoms), len(files)))


@pytest.mark.skipif(not _MUSIC.is_dir(), reason="bin/music absent")
def test_only_driver11_loads_at_0d7e_the_rest_load_at_0dfe():
    """Recorded because $0D7E is the load address every $0903-derived offset
    goes negative against, and it is NOT universal even among these 11."""
    by_load = {}
    for f in sorted(_MUSIC.glob("*.sf2")):
        load = int.from_bytes(f.read_bytes()[:2], "little")
        by_load.setdefault(load, []).append(f.name)
    assert set(by_load) == {0x0D7E, 0x0DFE}, {hex(k): v for k, v in by_load.items()}
    assert all(n.startswith("Driver 11 ") for n in by_load[0x0D7E]), by_load[0x0D7E]
    assert not any(n.startswith("Driver 11 ") for n in by_load[0x0DFE]), by_load[0x0DFE]
