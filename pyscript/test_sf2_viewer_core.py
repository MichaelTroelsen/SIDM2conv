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

