"""Tests for `sf2_viewer_core`'s driver detection.

The corpus (SF2/, out/hardtrack/) is on disk here, so these run against real
files rather than synthetic headers -- which matters, because the bug they pin
was invisible to any synthetic test: it turned on a constant that is identical
in every SF2 ever written.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)


# --------------------------------------------------------------------------
# Driver detection. $0D7E is the SF2 CONTAINER load address, shared by every
# driver, so it cannot identify one.
# --------------------------------------------------------------------------

def _sf2(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *parts)


def test_normalize_driver_name_folds_screen_codes():
    """Driver names ship in two encodings and only one is ASCII.

    `Angular.sf2` stores L,$01,$18,$09,$14,$19 -- screen codes for A-Z --
    while `Balance.sf2` stores plain "Laxity". A substring test against the
    display string alone silently misses every screen-code file, which is how
    the first attempt at this fix un-detected genuine Laxity SF2s.
    """
    from sf2_viewer_core import SF2Parser
    assert SF2Parser._normalize_driver_name('L\x01\x18\x09\x14\x19') == 'LAXITY'
    assert SF2Parser._normalize_driver_name('Laxity') == 'LAXITY'
    assert 'DRIVER' in SF2Parser._normalize_driver_name('D\x12\x09\x16\x05\x12 11.00')


@pytest.mark.skipif(not os.path.isdir(_sf2('SF2')), reason='SF2 corpus absent')
def test_laxity_detection_is_not_the_container_load_address():
    """Regression: the detector used to return True for EVERY SF2.

    It tested `load_address == 0x0D7E`, which is the container's address and is
    identical for Laxity and Driver 11 alike, plus "some non-zero byte at
    $0E00", which any non-empty file satisfies. Genuine Laxity files parsed
    fine so nobody noticed, while Driver 11 files failed into a fallback and
    printed three "invalid sequence address $0000" warnings.
    """
    import glob
    from sf2_viewer_core import SF2Parser

    lax = sorted(glob.glob(_sf2('SF2', '*.sf2')))[:6]
    d11 = sorted(glob.glob(_sf2('out', 'hardtrack', '*.sf2')))[:3]
    if not lax or not d11:
        pytest.skip('need both a Laxity and a Driver 11 SF2')

    for p in lax:
        pr = SF2Parser(p); pr.parse()
        assert pr.load_address == 0x0D7E                    # same for both
        assert pr.is_laxity_driver, os.path.basename(p)
    for p in d11:
        pr = SF2Parser(p); pr.parse()
        assert pr.load_address == 0x0D7E                    # ...which is the point
        assert not pr.is_laxity_driver, os.path.basename(p)


@pytest.mark.skipif(not os.path.isdir(_sf2('out', 'hardtrack')), reason='no Driver 11 SF2s')
def test_driver11_orderlist_is_not_read_from_the_laxity_offset():
    """Regression: every Driver 11 orderlist position exported as `A000`.

    `_parse_music_data` derived column 1 from the hardcoded LAXITY file offset
    $1766, which on a Driver 11 file lands in a run of zeros -- so the unpacker
    dutifully produced 'transpose $A0, sequence 0' for every position of all
    three tracks. The real address is in the Music Data block's word at offset
    12 ($242A on all five files here).

    Checked structurally rather than against a golden dump. The strong
    invariant is CONTIGUITY: the emitter numbers sequences 0..N with no gaps, so
    a correct orderlist references exactly max+1 distinct sequences. All five
    files satisfy that (Zakplus 62 refs / max $3D, Love_tune_2 30 / $1D, ...),
    and the broken read could not -- it referenced sequence 0 and nothing else.

    Track lengths are deliberately NOT asserted equal: voices loop at different
    points, and Hopscotch really is 44/48/48.
    """
    import glob
    from sf2_viewer_core import SF2Parser

    paths = sorted(glob.glob(_sf2('out', 'hardtrack', '*.sf2')))
    if not paths:
        pytest.skip('no Driver 11 SF2s built')
    for p in paths:
        name = os.path.basename(p)
        pr = SF2Parser(p); pr.parse()
        assert not pr.is_laxity_driver, name
        tracks = pr.orderlist_unpacked
        assert len(tracks) == 3, name
        assert all(tracks), f'{name}: an empty track'
        seqs = [tuple(e['sequence'] for e in t) for t in tracks]
        assert len(set(seqs)) == 3, f'{name}: tracks are identical'
        used = {s for t in seqs for s in t}
        assert used == set(range(max(used) + 1)), f'{name}: gaps in {sorted(used)}'
        assert max(used) > 0, f'{name}: only sequence 0 referenced (the old bug)'


@pytest.mark.skipif(not os.path.isdir(_sf2('SF2')), reason='SF2 corpus absent')
def test_laxity_orderlist_comes_from_the_block_word_too():
    """The Laxity exception is gone: the block word is right for that driver too.

    This test previously pinned the OPPOSITE -- the hardcoded `$1766` offset --
    on the grounds that choosing needed Laxity ground truth. That ground truth
    exists, and all three forms agree the constant is wrong:

      * the block's word layout is identical across both drivers (word16 -
        word12 == $300, three tracks of $100), and the constant is a fixed
        $24e0 for every Laxity file here while word12 moves per file;
      * a correct orderlist terminates on all three tracks and references
        exactly max+1 distinct sequences -- word12 passes 47/47, the constant
        0/47;
      * `laxity_parser` decodes Angular's source SID independently, and word12
        matches its shape while the constant yields 253 entries of sequence
        $7F.

    Both assertions below are load-bearing: the address must come from the
    block, and the resulting orderlist must satisfy the invariant.
    """
    import glob
    from sf2_viewer_core import SF2Parser, BlockType

    paths = sorted(glob.glob(_sf2('SF2', '*.sf2')))[:6]
    if not paths:
        pytest.skip('no Laxity SF2s')
    checked = 0
    for p in paths:
        pr = SF2Parser(p); pr.parse()
        if not pr.is_laxity_driver:
            continue
        d = pr.blocks[BlockType.MUSIC_DATA][1]
        assert pr.music_data_info.orderlist_address == d[12] | (d[13] << 8)
        assert pr.music_data_info.orderlist_address != pr.load_address + (0x1766 - 4)
        seqs = [e['sequence'] for tr in pr.orderlist_unpacked for e in tr]
        assert seqs, f'{os.path.basename(p)}: no orderlist entries'
        assert set(seqs) == set(range(max(seqs) + 1)), (
            f'{os.path.basename(p)}: sequences {sorted(set(seqs))[:12]} not contiguous')
        checked += 1
    assert checked, 'no Laxity files were checked'



# --- the Laxity payload base -------------------------------------------------
# These pin the fix for "the two-stage decode produces wave_ptr errors on an SF2
# payload". The suspect was the PSIDHeader's init_address; it is not, and that is
# measured rather than argued -- SF2Parser already carries the real one in
# driver_common.init_address and feeding it changes nothing. The cause is that
# sidm2.laxity_parser's table constants are offsets from the PLAYER BASE while
# the code added them to the FILE's load address. The two coincide at $1000 for a
# raw SID, which is why it only showed on an SF2 wrapper.

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parsed_sf2(name):
    """Parse an SF2 by basename. Named _parsed_sf2, not _sf2: this module
    already has a _sf2() that returns a PATH, and shadowing it broke four
    passing tests when these were first appended."""
    from sf2_viewer_core import SF2Parser
    p = SF2Parser(os.path.join(_ROOT, "SF2", name))
    p.parse()
    return p


def test_laxity_payload_rebases_on_the_player_not_the_file_load_address():
    p = _parsed_sf2("Angular.sf2")
    assert p.is_laxity_driver
    assert p.load_address == 0x0D7E, hex(p.load_address)
    data, base = p.laxity_payload()
    assert base == 0x1000, hex(base)
    # the payload really starts at the base, not merely claims to
    assert len(data) == len(p.data[2:]) - (0x1000 - 0x0D7E)


def test_the_instrument_table_constant_lands_in_code_off_the_file_load_address():
    """The concrete reason the anchor matters, kept as bytes rather than prose.

    load+$0A6B = $17E9 on this file and the bytes there are 8D 18 D4 -- STA
    $D418, i.e. player code. At the player base the same constant reaches the
    real table, whose first bytes match the raw SID's byte for byte.
    """
    from sidm2.laxity_parser import LAXITY_INSTR_TABLE_OFFSET as INS
    p = _parsed_sf2("Angular.sf2")
    raw = p.data[2:]
    wrong = raw[(p.load_address + INS) - p.load_address:][:3]
    data, base = p.laxity_payload()
    right = data[INS:INS + 3]
    assert bytes(wrong) != bytes(right)
    assert bytes(right) == bytes([0x03, 0xF8, 0x80]), bytes(right).hex()


def test_every_laxity_sf2_on_disk_can_be_rebased():
    """The base is a CHECKED constant, not an assumed one.

    All 47 Laxity SF2s load at $0D7E; if one ever does not, laxity_payload()
    must refuse rather than slice at a negative offset. This is the test that
    turns "$1000 looked right on the file I tried" into an invariant.
    """
    import glob
    seen = 0
    for f in sorted(glob.glob(os.path.join(_ROOT, "SF2", "*.sf2"))):
        try:
            from sf2_viewer_core import SF2Parser
            p = SF2Parser(f)
            p.parse()
        except Exception:
            continue
        if not p.is_laxity_driver:
            continue
        seen += 1
        assert p.load_address <= 0x1000, (os.path.basename(f), hex(p.load_address))
        assert p.laxity_payload() is not None, os.path.basename(f)
    assert seen >= 40, seen


def test_laxity_payload_refuses_when_the_load_is_above_the_player_base():
    """Refusing beats slicing at a negative offset."""
    p = _parsed_sf2("Angular.sf2")
    p.load_address = 0x2000
    assert p.laxity_payload() is None


def test_laxity_sf2_decodes_through_both_stages_not_the_packed_heuristic():
    """Angular's SF2 must decode to the same shape as its raw SID.

    Before: {0:64, 1:667, 2:24, 3:7, 4:30} from the packed-sequence heuristic --
    sequence 1 over-reading to 667 entries against a declared length of 75, which
    the A/B listening page had to refuse outright.
    After: 197/174/139, which is exactly what SID/Angular.sid yields.

    Counts, not note names. The decoded NOTES do not match the SF2II ground truth
    (D-1/D#-1/F#-1 against the editor's C-4/A-3/A-4) and it is not yet known
    whether that is the container-vs-payload sequence numbering mismatch or a real
    decode error -- see sf2-sequence-numbering-differs-from-laxity-payload-indices.
    Pinning the names here would pin a claim nobody has established.
    """
    p = _parsed_sf2("Angular.sf2")
    assert p.is_laxity_driver
    # THESE COUNTS ARE THE ORDERLISTS, NOT SEQUENCES, and they are pinned here as
    # CURRENT BEHAVIOUR rather than as correct. ch_seq_ptr points at orderlists
    # (docs/players/LAXITY.md), so these three bodies are orderlist bytes decoded
    # with the sequence grammar, over-running their $FF terminator because the
    # extractor stops on $7F. Angular really has 14 sequences, and
    # _parse_laxity_real_sequences() decodes them -- it is not routed by default
    # because that changes self.sequences from per-voice to per-file and breaks
    # abpage's row_schedule. Update this when the dispatch flips.
    counts = [len(v) for _, v in sorted(p.sequences.items())]
    assert counts == [197, 174, 139], counts


def _angular_real_sequences():
    """Angular through the real sequence table, bypassing the default dispatch."""
    p = _parsed_sf2("Angular.sf2")
    p.sequences = {}
    assert p._parse_laxity_real_sequences() is True
    return p


def test_angular_ground_truth_matches_the_sf2ii_editor_capture():
    """The SF2II capture, checkable at last -- five cycles could not reach it.

    Ground truth (SID Factory II, Ctrl+P + F1): T3 reads
    'A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4'. That is sequence 07 rows 7..14, exact and
    with NO transpose, which pins the note naming at the same time:
    octave = value // 12, class = value % 12, 0 = C-0.

    A PREVIOUS CYCLE REJECTED THIS TABLE AND WAS WRONG. It compared entries
    0/1/2 against T1/T2/T3, but the orderlists name 01/02/05 and the rows shown
    live in 07 -- so it was reading the right table at the wrong indices.
    """
    names = "C C# D D# E F F# G G# A A# B".split()

    def nm(v):
        return "+++" if not v else "%s-%d" % (names[v % 12], v // 12)

    p = _angular_real_sequences()
    rows = [nm(e.note) for e in p.sequences[7]]
    assert rows[7:15] == ["A-4", "G-4", "B-4", "G-4", "D-4", "C-5", "B-4", "G-4"], rows[:16]
    # the T1/T2 line's 'C-4 --- A-3' is rows 1..3 of the same sequence
    assert rows[1:4] == ["C-4", "+++", "A-3"], rows[:6]


def test_angular_orderlists_are_read_as_orderlists():
    """Three per-voice orderlists: a transpose byte, then sequence NUMBERS.

    The editor names T1/T2/T3 as sequences 01/02/05 and these are where that
    comes from -- the first entry of each voice's orderlist.
    """
    p = _angular_real_sequences()
    assert [ol[0] for ol in p.laxity_orderlists] == [0x87, 0x93, 0x87]
    assert [ol[1] for ol in p.laxity_orderlists] == [0x01, 0x02, 0x05]
    assert p.laxity_orderlists[2][1:] == [5, 6, 3, 4, 3, 7, 10, 10, 11, 12, 11, 13]


def test_sequence_table_locate_is_unique_or_refuses():
    """The locate is an exhaustive scan, so a TIE must refuse rather than pick.

    The shape is self-verifying -- bodies start at table + 2N, so entry 0 must
    equal that -- and across all 47 Laxity SF2s on disk it yields exactly one
    candidate 22 times, none 25 times, and two candidates NEVER. This pins both
    halves: Angular resolves uniquely, and a buffer with no such structure
    returns None instead of guessing.
    """
    p = _parsed_sf2("Angular.sf2")
    data, base = p.laxity_payload()
    tbl, count, ptrs = p.laxity_locate_seq_table(data, base)
    assert (tbl, count) == (0x1B1C, 14)
    assert ptrs[0] == tbl + 2 * count          # the constraint that makes it unique
    assert ptrs == sorted(ptrs)
    assert p.laxity_locate_seq_table(bytes(4096), 0x1000) is None


def test_the_two_stage_reader_declines_rather_than_returning_empty():
    """laxity_payload() returning None must mean 'decline', so the dispatch falls
    through to the older readers instead of publishing an empty result."""
    p = _parsed_sf2("Angular.sf2")
    p.load_address = 0x2000          # above the player base -> cannot re-base
    p.sequences = {}
    assert p._parse_laxity_two_stage() is False
    assert p.sequences == {}
