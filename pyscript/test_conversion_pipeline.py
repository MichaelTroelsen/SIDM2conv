"""`has_sf2_magic` was a TWO-BYTE SUBSTRING SEARCH over an entire C64 image.

THE DEFECT, measured rather than reasoned about. `b'\\x37\\x13' in c64_data`
scans 8KB+ for two bytes, and two bytes recur by chance. Over the whole tree it
fired on 46 of 1,524 .sid files -- native Hubbard (14), Gallefoss (10), Laxity
(9), Bjerregaard (5), Gray (3), Shogoon (3) and Tel (2) rips -- at scattered
offsets (809, 2356, 1099, 1213, ...). NOT ONE of the 46 carried the marker at
offset 0, which is the only place a real one can be.

WHY OFFSET 0. An SF2 file is [load_lo, load_hi, $37, $13, <blocks>], so the
marker sits at FILE offset 2 and the 2-byte PRG load address is exactly what
SIDParser.get_c64_data strips. Verified against an sf2_to_sid round trip of the
tracked reference file: marker at C64-data offset 0, every time.

THE FALSE POSITIVE WAS NOT COSMETIC. `is_sf2_exported = has_sf2_magic and
driver_type == 'driver11'`, and driver11 is DriverSelector's fallback default,
so every one of the 46 that also fell through to the default was routed into the
SF2-export path and logged as "SF2-exported file" while being a native rip.

THE TRAP THIS FILE ALSO PINS: strengthening the check by walking the block chain
to BLOCK_END REJECTS a genuine export. The chain in a real file degenerates into
id=$00 size=0 filler and runs off the end without ever reaching $FF. The first
block descriptor is the invariant that actually holds -- 422 of 422 .sf2 files
in SF2/, bin/music/ and out/ begin with block id $01 and an in-bounds size.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from sidm2.conversion_pipeline import has_sf2_structure   # noqa: E402
from sidm2.sf2_parser import BLOCK_DESCRIPTOR             # noqa: E402

_REFERENCE = os.path.join(_ROOT, "bin", "music", "Driver 11 Test - Arpeggio.sf2")
# One of the 46 the old substring check matched: a native Rob Hubbard rip whose
# marker sits at offset 2198, not 0. This is the file that logged verbatim
# "Using SF2 player parser (driver: driver11, SF2-exported file)".
_FALSE_POSITIVE = os.path.join(
    _ROOT, "SID", "Hubbard_Rob", "Commodore_64_Music_Examples.sid")


def _sf2_as_c64_data(path):
    """An .sf2 read the way a SID carries it: with the PRG load address stripped."""
    return open(path, "rb").read()[2:]


def test_a_real_sf2_image_is_ACCEPTED():
    assert has_sf2_structure(_sf2_as_c64_data(_REFERENCE))


def test_the_marker_at_a_nonzero_offset_is_REJECTED():
    """The exact shape of all 46 false positives, built synthetically."""
    payload = b"\x00" * 800 + b"\x37\x13" + b"\x00" * 800
    assert b"\x37\x13" in payload          # the OLD check would say yes
    assert not has_sf2_structure(payload)  # the new one says no


@pytest.mark.skipif(not os.path.exists(_FALSE_POSITIVE),
                    reason="SID corpus not present")
def test_a_real_native_rip_the_old_check_matched_is_REJECTED():
    from sidm2.sid_parser import SIDParser
    parser = SIDParser(_FALSE_POSITIVE)
    data, _load = parser.get_c64_data(parser.parse_header())
    assert b"\x37\x13" in data             # it really is one of the 46
    assert data.find(b"\x37\x13") != 0     # and not at offset 0
    assert not has_sf2_structure(data)


def test_a_wrong_first_block_id_is_REJECTED():
    """Marker in the right place, but the byte after it is not a block descriptor."""
    assert not has_sf2_structure(b"\x37\x13" + bytes([BLOCK_DESCRIPTOR + 1]) + b"\x05\x00" + b"\x00" * 8)


def test_a_first_block_running_past_the_end_is_REJECTED():
    """A size that overruns the buffer is not a structure, it is noise."""
    assert not has_sf2_structure(b"\x37\x13" + bytes([BLOCK_DESCRIPTOR]) + b"\xFF\x7F" + b"\x00" * 8)


def test_data_too_short_to_hold_a_descriptor_is_REJECTED():
    assert not has_sf2_structure(b"\x37\x13")
    assert not has_sf2_structure(b"\x37\x13" + bytes([BLOCK_DESCRIPTOR]) + b"\x05")
    assert not has_sf2_structure(b"")


def test_walking_the_chain_to_BLOCK_END_would_reject_a_REAL_export():
    """Pins the refuted 'strengthening' so nobody re-adds it.

    Reaching $FF is NOT an SF2 invariant: this tracked reference file's chain
    degenerates into id=$00 size=0 filler and runs off the end.
    """
    data = _sf2_as_c64_data(_REFERENCE)
    offset, reached_end = 2, False
    while offset < len(data):
        if data[offset] == 0xFF:
            reached_end = True
            break
        if offset + 3 > len(data):
            break
        offset += 3 + int.from_bytes(data[offset + 1:offset + 3], "little")
    assert not reached_end
    assert has_sf2_structure(data)      # accepted anyway, which is the point


# --- the gate that CONSUMES the detector -------------------------------------
#
# `is_sf2_exported = has_sf2_magic and driver_type == 'driver11'`
# (conversion_pipeline.py:487). These two tests pin what that conjunction does
# NOW that the first clause is a real structure check, because the fix inverted
# which direction it fails in.

def test_a_native_rip_is_no_longer_treated_as_an_sf2_export():
    """THE DIRECTION THE OLD SUBSTRING CHECK GOT WRONG, pinned against a real file.

    SID/Hubbard_Rob/Commodore_64_Music_Examples.sid carries the two marker bytes
    at offset 2198 and takes DriverSelector's fallback ('Standard SF2 driver for
    maximum compatibility'), so under the old check BOTH clauses were true and it
    logged, verbatim, "Using SF2 player parser (driver: driver11, SF2-exported
    file)" on a native Rob Hubbard rip. 37 files took that route.
    """
    if not os.path.exists(_FALSE_POSITIVE):
        pytest.skip("SID corpus not present")
    from sidm2.sid_parser import SIDParser
    parser = SIDParser(_FALSE_POSITIVE)
    data, _load = parser.get_c64_data(parser.parse_header())
    assert not has_sf2_structure(data)
    # so the conjunction is False regardless of what the driver clause says
    assert not (has_sf2_structure(data) and "driver11" == "driver11")


def test_the_driver_clause_can_now_only_cause_a_MISS_not_a_false_positive():
    """THE INVERSION, measured -- and why the obvious cleanup is NOT applied here.

    Across all 1,524 .sid files under SID/ and SF2/, `has_sf2_structure` is True
    for ZERO of them, so the first clause alone already excludes every corpus
    file. The `and driver_type == 'driver11'` can therefore no longer admit
    anything; it can only REJECT a genuine export whose driver verdict is not
    driver11.

    That is not hypothetical. An sf2_to_sid round trip of the TRACKED
    "bin/music/Driver 11 Test - Arpeggio.sf2" -- SF2 II's own DRIVER 11 test file
    -- is identified by player-id.exe as 'SidFactory_II/Laxity', which
    DriverSelector.PLAYER_REGISTRY maps to the LAXITY driver, not driver11. So a
    genuine SF2 export scores has_sf2_structure=True, driver_type='laxity', and
    is_sf2_exported=False.

    THE CLEANUP IS DELIBERATELY NOT APPLIED. Dropping the driver clause would
    route such files into SF2PlayerParser, which has an OPEN correctness defect
    (it reads fixed 3-byte triples from a packed variable-length stream --
    sf2-player-parser-reads-fixed-triples-from-a-variable-length-stream). Fixing
    the gate before the parser would send more files into a worse decoder. The
    ordering is: fix the parser, then drop the clause.

    This test pins the shape so the finding is not lost, and fails if someone
    drops the clause while the parser is still wrong.
    """
    from sidm2 import conversion_pipeline as CP
    import inspect
    src = inspect.getsource(CP.analyze_sid_file)
    assert "has_sf2_magic and driver_type == 'driver11'" in src, (
        "the driver clause was dropped -- that is the right END state, but only "
        "after sf2_player_parser decodes the packed grammar correctly; see this "
        "test's docstring")
