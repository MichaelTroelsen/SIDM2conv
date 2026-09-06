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
    locate_seq_table,
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
    """Angular's sequences come from the SEQUENCE TABLE, not from ch_seq_ptr.

    THIS TEST PREVIOUSLY PINNED THE DEFECT, which is worth recording because it
    looked like a passing test the whole time. It asserted three bodies of
    73/59/45 bytes and quoted their opening as '87 01 01 01 01 01 01 08' -- and
    that IS the defect, in the assertion: those bytes are Angular's ORDERLIST for
    voice 0 ($1AF2), a transpose byte followed by twelve sequence NUMBERS and an
    $FF. The parser terminates on $7F, an orderlist ends on $FF, so it ran past
    the end and kept scanning; 73/59/45 are how far it got, not the size of
    anything. The old assertion `orderlists == [[0], [1], [2]]` is the same
    mistake seen from the other side -- three "sequences" that are really the
    three orderlists, so each voice appeared to play exactly one.

    What ch_seq_ptr locates is still correct and still pinned below; it simply
    points at orderlists rather than at sequences. Derivation: 34ed351 and
    docs/players/LAXITY.md.
    """
    data, load = _angular()
    # ch_seq_ptr is unchanged -- it was never the wrong table, only the wrong
    # GRAMMAR was applied to what it points at.
    assert locate_seq_ptr_table(data, load) == (0x1907, 0x190A)

    # the real sequence table: split lo[14]/hi[14] at $1B1C, bodies from $1B38
    tbl, count, ptrs = locate_seq_table(data, load)
    assert (tbl, count) == (0x1B1C, 14)
    assert ptrs[0] == tbl + 2 * count

    result = LaxityParser(data, load).parse()
    assert len(result.sequences) == 14
    # bodies are cut at the NEXT POINTER, so lengths are structural rather than
    # scanned -- and none of them is a 73/59/45 over-read
    assert [len(s) for s in result.sequences] == [
        3, 84, 86, 75, 60, 81, 81, 56, 84, 86, 54, 50, 51, 57]
    assert sum(len(s) for s in result.sequences) == ptrs[-1] - ptrs[0] + len(
        result.sequences[-1])

    # and the orderlists are now what the voices actually PLAY: twelve numbers
    # each, indexing the table directly, with the $87/$93 transpose bytes
    # dropped rather than read as sequence 135/147.
    assert result.orderlists == [
        [1, 1, 1, 1, 1, 1, 8, 8, 8, 8, 8, 8],
        [2, 2, 2, 2, 2, 2, 9, 9, 9, 9, 9, 9],
        [5, 6, 3, 4, 3, 7, 10, 10, 11, 12, 11, 13]]
    assert all(n < count for voice in result.orderlists for n in voice)


def test_a_table_the_orderlists_contradict_is_DECLINED_not_truncated():
    """A located table smaller than the numbers the song plays is refused.

    Rudolph_in_the_Kitchen locates a 13-entry table at $12E9, but its voices
    name sequences up to $22. Both cannot be true, and truncating to 13 would
    hand back a table that is silently missing most of the song -- so the
    parser declines the whole stage and the older reader answers instead.
    This is locate_seq_table's own tie-refusal convention applied one layer up.

    Measured over SID/Laxity/ (286 files): 21 locate, 17 are used, and 4 are
    declined here -- Farfisa, Flappy_Hero_March, Hand_Interludes_Side_3 and
    this one. If a future change makes one of them consistent, that is a
    result; update the count rather than deleting the check.
    """
    path = ROOT / "SID" / "Laxity" / "Rudolph_in_the_Kitchen.sid"
    if not path.exists():
        pytest.skip("SID/Laxity/Rudolph_in_the_Kitchen.sid not present")
    p = SIDParser(str(path))
    data, load = p.get_c64_data(p.parse_header())
    tbl, count, _ = locate_seq_table(data, load)
    assert (tbl, count) == (0x12E9, 13)
    result = LaxityParser(data, load).parse()
    # NOT 13: the table was declined, so this is the fallback reader's answer
    assert len(result.sequences) != count

    # POSITIVE CONTROL, and it is load-bearing. `!= count` alone is vacuously
    # true whenever the table stage does nothing at all -- a mutation that
    # disables the stage outright leaves the assertion above GREEN. Pairing it
    # with a file the stage does accept means the two together can only pass
    # when the stage is running AND declining selectively.
    ok = ROOT / "SID" / "Laxity" / "First_Tune.sid"
    if not ok.exists():
        pytest.skip("SID/Laxity/First_Tune.sid not present")
    p2 = SIDParser(str(ok))
    d2, l2 = p2.get_c64_data(p2.parse_header())
    _, n2, _ = locate_seq_table(d2, l2)
    assert n2 == 4
    assert len(LaxityParser(d2, l2).parse().sequences) == n2


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


# --- LAXITY_INSTR_TABLE_OFFSET is load-relative and the player is not ---------

def _laxity_sids():
    import io
    import contextlib
    from pathlib import Path
    from sidm2.driver_selector import DriverSelector
    root = Path(__file__).resolve().parent.parent
    out = []
    for f in sorted((root / "SID").rglob("*.sid")):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                if DriverSelector().select_driver(f).driver_name == "laxity":
                    out.append(f)
        except Exception:                                     # noqa: BLE001
            continue
    return out


def test_the_instrument_offset_is_the_same_bug_73780fa_fixed_for_seq_ptrs():
    """LAXITY_INSTR_TABLE_OFFSET resolves against the LOAD ADDRESS, and the
    player is assembled per song, so the constant cannot be right for more than
    a handful of files.

    73780fa established this for LAXITY_SEQ_PTRS_*_OFFSET and replaced the
    lookup with locate_seq_ptr_table. The instrument constant was left behind,
    and it is wrong on the same inputs for the same reason.

    MEASURED 2026-09-03 over all 241 laxity-routed SIDs in SID/:

        distinct (located lo_base - load_address) values      114
        files where that offset equals the constant $0A1C       3
        files where load + $0A6B is OUTSIDE the loaded data    69
        files with a located seq-ptr                          180
        of those, constant == lo_base + $4F                     3
        where it disagrees (n=177): median |error| 1011 bytes
                                    min 8, max 2544

    An 8x8 instrument table is 64 bytes, so a 1,011-byte median error is not a
    near miss -- it reads unrelated memory.

    THIS TEST DELIBERATELY PINS THE DEFECT, NOT A FIX. No replacement is
    shipped. `table_extraction.find_instrument_table` cannot arbitrate -- it
    returns NOTHING for 180 of the 180 files that have a located seq-ptr.

    AN ORACLE WAS FOUND, AND IT REFUTES BOTH CANDIDATES (2026-09-04).
    `sidm2.instrument_map.locate_instrument_table` ranks candidate layouts by
    how many onset ADSR values they explain, and `key_reliability` grades
    whether the ADSR key is trustworthy at all. Run over the files where the two
    hypotheses disagree and both land inside the image:

        file      key         cands  top candidate    CONSTANT $1A6B   DELTA
        Chaser    reliable     2148  $1963 hits 8/9   ABSENT           rank 974, 2 hits
        Dreamy    reliable       75  $1AFE hits 4/4   ABSENT           ABSENT
        Balance   reliable      171  $1B51 hits 5/6   ABSENT           ABSENT
        Beast     reliable      258  $1B3D hits 7/8   ABSENT           ABSENT

    ABSENT means the address does not reach `min_hits=2` in ANY layout -- fewer
    than two of the observed ADSR values are found there at all. On four files
    whose key the grader calls RELIABLE, the shipped constant explains
    essentially nothing, and `lo_base + $4F` is no better. The uniform-layout
    argument that made the delta attractive does not survive contact with the
    ADSRs the player actually writes.

    WHAT IS NOT CLAIMED: that the top-ranked candidate IS the table. With 75 to
    2,148 candidates the ranking is doing a lot of work, and a best fit among
    hundreds is not proof. The strong result here is the ABSENCE, which needs no
    ranking to be believed.

    The test asserts the measured shape, so it fails if someone fixes the
    constant, changes the locate, or lands a validator -- at which point this
    docstring is the thing to update. See
    laxity-table-constants-are-load-relative-but-the-tables-are-absolute.
    """
    import pytest
    from sidm2.sid_parser import SIDParser
    from sidm2.laxity_parser import (locate_seq_ptr_table,
                                     LAXITY_SEQ_PTRS_LO_OFFSET,
                                     LAXITY_INSTR_TABLE_OFFSET)
    import io
    import contextlib

    files = _laxity_sids()
    if len(files) < 50:
        pytest.skip("no Laxity corpus on this machine")

    delta = LAXITY_INSTR_TABLE_OFFSET - LAXITY_SEQ_PTRS_LO_OFFSET
    assert delta == 0x4F, "the internal layout gap moved; re-measure before trusting this test"

    offsets, outside, located, agree = set(), 0, 0, 0
    for f in files:
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                sp = SIDParser(str(f))
                h = sp.parse_header()
                data, load = sp.get_c64_data(h)
                loc = locate_seq_ptr_table(data, load)
        except Exception:                                     # noqa: BLE001
            continue
        addr = load + LAXITY_INSTR_TABLE_OFFSET
        if not (load <= addr < load + len(data)):
            outside += 1
        if loc:
            located += 1
            offsets.add(loc[0] - load)
            if addr == loc[0] + delta:
                agree += 1

    # THE POINT: the offset is not a property of the format, it is per-song.
    assert len(offsets) > 50, (
        "the located seq-ptr offset is no longer widely variable (%d distinct) "
        "-- if the player stopped being assembled per song, this whole task is "
        "moot and the constant may be defensible again" % len(offsets))
    assert agree < located // 10, (
        "the load-relative constant now agrees with the located base on %d of "
        "%d files -- if something fixed this, update the docstring above"
        % (agree, located))
    assert outside > 10, (
        "load + $0A6B now lands inside the data on nearly every file (%d "
        "outside) -- re-measure" % outside)


# ---------------------------------------------------------------------------
# The SF2II orderlist panel cannot confirm a locate, and this pins WHY.
#
# The converter writes a Driver-11-shaped orderlist STUB into every emitted
# Laxity SF2 -- transpose $A0 with sequences 0/1/2 -- because the Laxity driver
# plays from the embedded NP21 payload and the editor only needs enough of an
# orderlist to open the file. Measured 2026-09-05, that stub is byte-identical
# on Angular, Cascade and Cycles. So an SF2II panel showing `00 01 02` is
# showing the stub, not the song, and it reads the same on every file.
#
# The test below is the half that can be checked without converting anything:
# no file's REAL orderlist starts 00/01/02, so the stub can never accidentally
# agree with a correct locate. That makes "the editor disagrees with our
# locate" worthless as evidence -- it disagrees with all 14, including Angular,
# whose 01/02/05 is independently proven. Delete this pin only alongside the
# LAXITY.md section it backs.
# ---------------------------------------------------------------------------

_ORDERLIST_FILES = [
    "Angular", "Omniphunk", "Stinsens_Last_Night_of_89", "Balance", "Beast",
    "Cascade", "Chaser", "Colorama", "Cycles", "Delicate", "Dreams", "Dreamy",
    "Phoenix_Code_End_Tune", "Unboxed_Ending_8580",
]

_SF2_ORDERLIST_STUB = (0x00, 0x01, 0x02)


def _first_entries(name):
    """(voice0, voice1, voice2) first orderlist numbers, or None if refused."""
    from sidm2.laxity_parser import read_orderlist_numbers

    path = ROOT / "SID" / (name + ".sid")
    if not path.exists():
        return "missing"
    p = SIDParser(str(path))
    data, load = p.get_c64_data(p.parse_header())
    loc = locate_seq_ptr_table(data, load)
    if loc is None:
        return None
    nums = read_orderlist_numbers(data, load, loc[0], loc[1])
    if nums is None:
        return None
    return tuple(v[0] if v else None for v in nums)


def test_no_real_orderlist_starts_with_the_sf2_stub_00_01_02():
    """The editor's panel value is unreachable by any correct locate.

    POSITIVE CONTROL FIRST: at least ten files must actually produce a reading.
    Without it this passes vacuously the moment the locate stops working --
    "no file equals 00 01 02" is trivially true of an empty set, and that is
    exactly the shape (`score_pct` returning None over zero frames) this repo
    has shipped a confident wrong number from before.
    """
    read = {}
    for name in _ORDERLIST_FILES:
        got = _first_entries(name)
        if got in (None, "missing"):
            continue
        read[name] = got

    assert len(read) >= 10, (
        "positive control failed: only %d of %d files produced an orderlist "
        "reading, so the assertion below would be vacuous"
        % (len(read), len(_ORDERLIST_FILES)))

    same = {n: v for n, v in read.items() if v == _SF2_ORDERLIST_STUB}
    assert not same, (
        "%s start with the SF2 stub 00/01/02 -- if that is genuinely the "
        "song's orderlist the editor panel becomes ambiguous for that file, "
        "and the LAXITY.md claim that a panel reading is never evidence needs "
        "revisiting" % sorted(same))


def test_angulars_proven_orderlist_is_the_one_the_panel_contradicts():
    """The single file with independent ground truth, pinned as 01/02/05.

    docs/players/LAXITY.md derives these from the payload bytes `87 01`,
    `93 02`, `87 05`. A 2026-09-05 SF2II capture of a converted Angular showed
    `00 01 02` instead. Both cannot describe the same object, and this test
    fixes which one the parser reports -- so if the locate ever drifts toward
    the stub, it fails here rather than being read as the editor agreeing.
    """
    if not ANGULAR.exists():
        pytest.skip("SID/Angular.sid not present")
    assert _first_entries("Angular") == (0x01, 0x02, 0x05)


# ---------------------------------------------------------------------------
# THE LOCATE, CONFIRMED BY THE PLAYER'S OWN FETCHES (2026-09-06)
#
# locate_seq_ptr_table finds ch_seq_ptr by CODE SIGNATURE -- two `LDA abs,X`
# whose operands are 3 apart. ~20 neighbouring 3-byte per-voice tables share
# that shape in every file, so "the table is read" discriminates NOTHING: the
# player reads all of them. What only the REAL table can do is supply the base
# addresses of the indirect-indexed `(zp),Y` fetches that walk sequence data.
#
# So: emulate init + N play calls, record every address reached through (zp),Y,
# and ask whether the pointers STORED in the located table are among them.
#
# This replaces the verify's prescribed SF2II ground truth, which two earlier
# cycles showed CANNOT work: the editor's orderlist panel displays a converter
# STUB that is byte-identical across files (a0 00 fe ff...), so it disagrees
# with every file by construction, including the confirmed ones.
# ---------------------------------------------------------------------------

CONFIRMED_THREE = ["Angular", "Omniphunk", "Stinsens_Last_Night_of_89"]

# The eleven the locate accepted on the validity filter alone. "Unboxed" is the
# Ending rip -- Unboxed_Intro/Turn_Disk are NOT located at all and are outside
# this population.
THE_ELEVEN = ["Balance", "Beast", "Cascade", "Chaser", "Colorama", "Cycles",
              "Delicate", "Dreams", "Dreamy", "Phoenix_Code_End_Tune",
              "Unboxed_Ending_8580"]


def _sid_path(stem):
    """ROOT and pytest come from this module's existing header; there is no
    second import block."""
    for sub in ("SID", "SID/Laxity"):
        cand = ROOT / sub / ("%s.sid" % stem)
        if cand.exists():
            return str(cand)
    return None


def _load_sid_body(path):
    d = open(path, "rb").read()
    doff = int.from_bytes(d[6:8], "big")
    load = int.from_bytes(d[8:10], "big")
    init = int.from_bytes(d[10:12], "big")
    play = int.from_bytes(d[12:14], "big")
    body = d[doff:]
    if load == 0:
        load = body[0] | (body[1] << 8)
        body = body[2:]
    return body, load, init, play


def _indirect_reads(path, frames=200, budget=400000):
    """Every address the play routine reaches through (zp),Y."""
    from sidm2.cpu6502_emulator import CPU6502Emulator

    class _T(CPU6502Emulator):
        def __init__(self):
            super().__init__(capture_writes=False)
            self.ind = set()

        def addr_indirect_y(self):
            a = super().addr_indirect_y()
            self.ind.add(a)
            return a

    body, load, init, play = _load_sid_body(path)
    t = _T()
    t.load_memory(body, load)
    t.reset(pc=init, a=0)
    t.run_until_return()
    for _ in range(frames):
        t.reset(pc=play)
        n = 0
        while n < budget and t.run_instruction():
            n += 1
    return t.ind, body, load


def _fetch_score(body, load, lo_b, hi_b, ind):
    """How many of the 3 stored pointers the player actually fetched from."""
    if not (0 <= lo_b - load < len(body) - 3 and 0 <= hi_b - load < len(body) - 3):
        return None
    return sum((body[lo_b - load + i] | (body[hi_b - load + i] << 8)) in ind
               for i in range(3))


def _candidates(body):
    """Every `LDA abs,X` operand pair 3 apart -- the confusion set the code
    signature cannot separate. The two instructions need NOT be adjacent
    (Angular's are 6 bytes apart); assuming they were found ZERO candidates in
    the first version of this check and made it silently vacuous."""
    ops = {body[i + 1] | (body[i + 2] << 8)
           for i in range(len(body) - 3) if body[i] == 0xBD}
    return [(a, a + 3) for a in sorted(ops) if a + 3 in ops]


def _score_stem(stem):
    path = _sid_path(stem)
    if path is None:
        pytest.skip("%s.sid not present" % stem)
    body, load, _i, _p = _load_sid_body(path)
    loc = locate_seq_ptr_table(body, load)
    assert loc is not None, "%s: locate returned None" % stem
    lo_b, hi_b = loc
    ind, body, load = _indirect_reads(path)
    return _fetch_score(body, load, lo_b, hi_b, ind), body, load, lo_b, hi_b, ind


def test_the_fetch_check_DISCRIMINATES_before_it_is_believed():
    """NEGATIVE CONTROL, and it comes first. If every candidate scored 3/3 the
    result below would be vacuous agreement, which is the exact shape this repo
    keeps shipping. On Angular exactly ONE of 22 candidates scores 3/3 and it is
    the located one; both historical CONSTANTS score less; an off-by-one
    degrades rather than passing."""
    s, body, load, lo_b, hi_b, ind = _score_stem("Angular")
    assert s == 3, s
    winners = [(a, b) for a, b in _candidates(body)
               if _fetch_score(body, load, a, b, ind) == 3]
    assert len(_candidates(body)) > 10, "confusion set too small to be a control"
    assert winners == [(lo_b, hi_b)], winners
    # the constants this locate replaced
    assert _fetch_score(body, load, load + 0x099F, load + 0x09A2, ind) < 3
    assert _fetch_score(body, load, load + 0x0A1C, load + 0x0A1F, ind) < 3
    # and it is not a range that passes by being near-enough
    assert _fetch_score(body, load, lo_b + 2, hi_b + 2, ind) < 3


@pytest.mark.parametrize("stem", CONFIRMED_THREE)
def test_the_three_independently_confirmed_files_agree(stem):
    """The instrument must reproduce the answers already known by other means."""
    assert _score_stem(stem)[0] == 3, stem


@pytest.mark.parametrize("stem", THE_ELEVEN)
def test_the_eleven_plausible_files_are_now_confirmed(stem):
    """The task's whole question: the locate accepted these on the validity
    filter alone, and conversion output cannot tell a right locate from a wrong
    one because the emitted SF2 is byte-identical either way."""
    assert _score_stem(stem)[0] == 3, stem
