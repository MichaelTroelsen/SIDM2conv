"""Tests for sidm2/laxity_parser.py -- specifically its sequence-pointer gate.

WHY THIS FILE EXISTS. `LaxityParser` locates its sequences through `ch_seq_ptr`,
a split lo/hi pair at `load+$0A1C` / `load+$0A1F`. That is the playroutine's
RUNTIME current-sequence pointer, which the player rewrites as it walks the
orderlist -- before init it holds whatever the assembler left there. The old
validity test was `seq_addr > 0 and seq_addr < 0x10000`, i.e. "is it a 16-bit
number", which every value trivially is.

Measured across the corpus docs/players/LAXITY.md:8 names -- SID/Laxity/, 286
files -- that constant yields a usable locate on SEVEN. The other 279 were handed
values like $007F, $4141 and $0000, and on SID/Angular.sid the three voice
pointers are $0334/$0341/$0336: all BELOW the $1000 load address, so not in the
loaded image at all. The parser extracted "sequences" from them anyway and
nothing downstream could tell.

The gate added here is a REFUSAL, not a locate. It does not find the right
sequences; it stops the wrong ones being returned as though they were right.
Finding them is separate, still-open work.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.laxity_parser import (                                  # noqa: E402
    LaxityParser,
    LAXITY_SEQ_PTRS_LO_OFFSET,
    LAXITY_SEQ_PTRS_HI_OFFSET,
    locate_seq_ptr_table,
)
from sidm2.sid_parser import SIDParser                             # noqa: E402

ANGULAR = ROOT / "SID" / "Angular.sid"


def _angular():
    p = SIDParser(str(ANGULAR))
    header = p.parse_header()
    data, load = p.get_c64_data(header)
    return data, load


def _synthetic(seq_addr: int, load: int = 0x1000, size: int = 0x2000,
               body: bool = False) -> bytes:
    """A buffer whose ch_seq_ptr points all three voices at `seq_addr`.

    `body=True` also writes a short well-formed sequence AT that address --
    duration, note, rest, instrument, note, then $7F END. Without it the buffer
    is all zeros, the extractor finds nothing to return, and an ACCEPT is
    indistinguishable from a REFUSAL: the accept test would pass for the wrong
    reason no matter what the gate did.
    """
    d = bytearray(size)
    for voice in range(3):
        d[LAXITY_SEQ_PTRS_LO_OFFSET + voice] = seq_addr & 0xFF
        d[LAXITY_SEQ_PTRS_HI_OFFSET + voice] = (seq_addr >> 8) & 0xFF
    if body and load <= seq_addr < load + size:
        off = seq_addr - load
        d[off:off + 7] = bytes([0x80, 0x15, 0x00, 0xA3, 0x34, 0x00, 0x7F])
    return bytes(d)


@pytest.mark.skipif(not ANGULAR.exists(), reason="SID/Angular.sid not present")
def test_angulars_ch_seq_ptr_really_is_below_the_load_address():
    """The premise, pinned. If this ever stops holding, the test below is
    measuring nothing and would pass vacuously."""
    data, load = _angular()
    lo = LAXITY_SEQ_PTRS_LO_OFFSET
    hi = LAXITY_SEQ_PTRS_HI_OFFSET
    addrs = [data[lo + v] | (data[hi + v] << 8) for v in range(3)]
    assert addrs == [0x0334, 0x0341, 0x0336], addrs
    assert all(a < load for a in addrs), (addrs, load)


@pytest.mark.skipif(not ANGULAR.exists(), reason="SID/Angular.sid not present")
def test_angular_locates_its_real_sequence_table():
    """WAS test_a_pointer_below_the_load_address_is_refused_not_extracted_from,
    and it asserted Angular yields NOTHING.

    That premise died with the constant. It was true only because the parser
    read ch_seq_ptr at a hardcoded offset that is wrong for Angular, producing
    three below-load pointers ($0334/$0341/$0336) which the out-of-image gate
    then refused. locate_seq_ptr_table now finds Angular's real table at $1907
    by code signature, so the honest assertion is the positive one: these are
    the addresses, independently confirmed by decoding them to three clean NP21
    bodies ('87 01 01 ... FF', 73/59/45 bytes).

    The REFUSAL is still pinned, by the two synthetic tests below and by
    test_a_file_whose_locate_refuses_yields_nothing -- it just cannot be pinned
    on a file the locate now handles correctly.
    """
    data, load = _angular()
    assert locate_seq_ptr_table(data, load) == (0x1907, 0x190A)
    result = LaxityParser(data, load).parse()
    # the three bodies decoded from $1AF2 / $1B00 / $1B0E
    assert [len(s) for s in result.sequences] == [73, 59, 45]
    assert result.sequences[0][:8] == bytes([0x87, 1, 1, 1, 1, 1, 1, 8])
    # $7F is END in the SEQUENCE grammar (CLAUDE.md); the $FF the locator's
    # scorer scans for is the raw table terminator. Two different markers --
    # the scorer only needs a consistent stop, not the grammar's one.
    assert result.sequences[0][-1] == 0x7F
    assert result.orderlists == [[0], [1], [2]]


def test_a_file_whose_locate_refuses_yields_nothing():
    """The refusal, pinned on a REAL file rather than a synthetic one.

    Ocean_Reloaded is the single file in SID/ where no candidate survives the
    validity filter, so locate_seq_ptr_table returns None, the parser falls back
    to the constants, and those point out of image. Refusing beats guessing.
    If this file ever starts decoding, that is a result -- update the test.
    """
    path = ROOT / "SID" / "Ocean_Reloaded.sid"
    if not path.exists():
        pytest.skip("SID/Ocean_Reloaded.sid not present")
    p = SIDParser(str(path))
    header = p.parse_header()
    data, load = p.get_c64_data(header)
    assert LaxityParser(data, load).parse().sequences == []


def test_an_address_inside_the_loaded_image_is_still_accepted():
    """The gate must not over-reject: a pointer that IS in the image is used.
    Without this, 'refuse everything' would pass the test above."""
    load = 0x1000
    data = _synthetic(seq_addr=0x1500, load=load, size=0x2000, body=True)
    result = LaxityParser(data, load).parse()
    assert result.sequences, "an in-image pointer must yield its sequence"
    assert result.orderlists != [[], [], []], (
        "an in-image pointer must be accepted, got %r" % (result.orderlists,)
    )


def test_the_upper_bound_is_the_end_of_the_data_not_the_end_of_memory():
    """$FFFF-style garbage is inside the 64K space and outside the image; the
    old check accepted it precisely because it only tested the former."""
    load = 0x1000
    data = _synthetic(seq_addr=0xFFF0, load=load, size=0x2000)   # image ends $3000
    result = LaxityParser(data, load).parse()
    assert result.sequences == []
    assert all(ol == [] for ol in result.orderlists), result.orderlists


def test_address_zero_is_refused():
    """$0000 was accepted by the old `seq_addr > 0` clause only by accident of
    ordering; it is below every realistic load address."""
    load = 0x1000
    data = _synthetic(seq_addr=0x0000, load=load, size=0x2000)
    result = LaxityParser(data, load).parse()
    assert result.sequences == []


def test_refusal_is_not_an_exception():
    """Downstream callers (laxity_analyzer, scripts/convert_all) iterate
    `.sequences`. The gate must return empty, never raise, or a locate failure
    becomes a conversion crash."""
    load = 0x1000
    data = _synthetic(seq_addr=0x0334, load=load, size=0x2000)
    result = LaxityParser(data, load).parse()          # must not raise
    assert result is not None
    assert result.sequences == []
