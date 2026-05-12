"""Tests for the Vibrants V20 advisory detector (v3.5.11).

These files use pre-NP21 player variants and should be flagged so the
conversion pipeline can skip the NP21 autodetect path (which lifts
garbage 2-14 byte "patterns" from these files' freq LUTs and confuses
the SF2 editor view).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.vibrants_v20_detector import detect_vibrants_v20, V20_MAX_SIZE


def _load_c64(name):
    sid_path = ROOT / 'SID' / 'Laxity' / name
    if not sid_path.exists():
        pytest.skip(f"missing {name}")
    buf = open(sid_path, 'rb').read()
    do = (buf[6] << 8) | buf[7]
    load = (buf[8] << 8) | buf[9]
    c64 = buf[do:] if load else buf[do+2:]
    if not load: load = buf[do] | (buf[do+1] << 8)
    cprt = buf[0x56:0x76].split(b'\x00')[0].decode('latin-1', errors='replace')
    return c64, load, cprt


class TestDetect:
    def test_empty_copyright_returns_none(self):
        assert detect_vibrants_v20(b'\x00' * 0x800, 0x1000, '') is None

    def test_non_vibrants_copyright_returns_none(self):
        # SF2-exported files have very different copyright strings
        assert detect_vibrants_v20(b'\x00' * 0x800, 0x1000,
                                    '2023 Some Studio') is None

    def test_large_file_returns_none(self):
        """Files > V20_MAX_SIZE are too big for V20 — even with a matching
        copyright, the heuristic skips them (NP21 binaries are 8 KB+)."""
        big_data = b'\x00' * (V20_MAX_SIZE + 1)
        assert detect_vibrants_v20(big_data, 0x1000, '1987 Wizax') is None


class TestKnownV20Files:
    """Each of the 14 Class-C inventory files should match the detector."""

    @pytest.mark.parametrize("name", [
        '2000_A_D.sid',
        'Cool_as_Wize_Title.sid',
        'Fight_TST_II.sid',
        'Hall_of_Fame.sid',
        'Magic_Sound.sid',
        'Min_Axel_F.sid',
        'Galax_it_y.sid',
        'Echo_Beat.sid',
        'James_Bond_Theme_Remix.sid',
        'Jewels.sid',
        'Waste.sid',
        'Racer.sid',
        'Atom_Rock.sid',
        # Fast_Stuff_1 has copyright "1990 Laxity" — not in V20 hint list
        # since "Laxity" alone is ambiguous (could be NP21 author too).
        # Skip from this test.
    ])
    def test_detects(self, name):
        c64, load, cprt = _load_c64(name)
        result = detect_vibrants_v20(c64, load, cprt)
        assert result is not None, f"{name} (cprt={cprt!r}, size={len(c64)}) should match V20"


class TestCanonicalFilesDoNotMatch:
    """Stinsen + Unboxed + Beast + Angular must NOT be flagged as V20
    (their copyright strings don't contain V20 labels and they're
    larger than V20_MAX_SIZE anyway)."""

    @pytest.mark.parametrize("name", [
        'Stinsens_Last_Night_of_89.sid',
        'Unboxed_Ending_8580.sid',
        'Beast.sid',
        'Angular.sid',
    ])
    def test_not_v20(self, name):
        sid_path = ROOT / 'SID' / name
        if not sid_path.exists():
            pytest.skip(f"missing {name}")
        buf = open(sid_path, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        c64 = buf[do:] if load else buf[do+2:]
        if not load: load = buf[do] | (buf[do+1] << 8)
        cprt = buf[0x56:0x76].split(b'\x00')[0].decode('latin-1', errors='replace')
        assert detect_vibrants_v20(c64, load, cprt) is None
