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
