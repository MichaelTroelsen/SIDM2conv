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
