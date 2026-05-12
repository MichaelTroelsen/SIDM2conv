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


class Test2000ADClusterSignature:
    """The 1988 2000 A.D. player signature should match Galax_it_y + Echo_Beat
    (same player at different load addrs) but NOT James_Bond_Theme_Remix
    (1988 2000 A.D. copyright but different player code)."""

    def test_galax_matches_cluster(self):
        c64, load, cprt = _load_c64('Galax_it_y.sid')
        result = detect_vibrants_v20(c64, load, cprt)
        assert result is not None
        assert '2000 A.D. cluster' in result, f"Galax should hit cluster suffix, got: {result}"

    def test_echo_beat_matches_cluster(self):
        c64, load, cprt = _load_c64('Echo_Beat.sid')
        result = detect_vibrants_v20(c64, load, cprt)
        assert result is not None
        assert '2000 A.D. cluster' in result, f"Echo_Beat should hit cluster suffix, got: {result}"

    def test_james_bond_does_not_match_cluster(self):
        """James_Bond_Theme_Remix.sid has copyright '1988 2000 A.D.' but
        different player code — must NOT match the cluster signature."""
        c64, load, cprt = _load_c64('James_Bond_Theme_Remix.sid')
        result = detect_vibrants_v20(c64, load, cprt)
        # Should still detect as V20 (copyright + size), but not as
        # cluster (player signature differs)
        assert result is not None
        assert '2000 A.D. cluster' not in result, f"James_Bond should NOT hit cluster suffix, got: {result}"


class TestZetrexYPClusterSignature:
    """1988 Zetrex (Jewels + Waste) and 1987 Yield Point (Racer) share
    the same player binary at load $E000. The cluster signature should
    match all three."""

    @pytest.mark.parametrize("name", [
        'Jewels.sid',
        'Waste.sid',
        'Racer.sid',
    ])
    def test_matches_cluster(self, name):
        c64, load, cprt = _load_c64(name)
        result = detect_vibrants_v20(c64, load, cprt)
        assert result is not None
        assert 'Zetrex / 1987 Yield Point cluster' in result, \
            f"{name} should hit Zetrex/YP cluster suffix, got: {result}"

    def test_2000_ad_files_not_in_zetrex_cluster(self):
        """Cluster suffixes must be mutually exclusive — Galax/Echo_Beat
        match 2000 A.D., not Zetrex/YP."""
        for name in ('Galax_it_y.sid', 'Echo_Beat.sid'):
            c64, load, cprt = _load_c64(name)
            result = detect_vibrants_v20(c64, load, cprt)
            assert result is not None
            assert 'Zetrex / 1987 Yield Point cluster' not in result, \
                f"{name} should NOT hit Zetrex cluster, got: {result}"


class TestWizaxClusters:
    """1987 Wizax 2004 splits into 2 sub-clusters by player code:
    Wizax-A (2000_A_D + Fight_TST_II + Hall_of_Fame) uses STA abs;
    Wizax-B (Cool_as_Wize_Title) uses STA abs,X/Y indexed."""

    @pytest.mark.parametrize("name", [
        '2000_A_D.sid',
        'Fight_TST_II.sid',
        'Hall_of_Fame.sid',
    ])
    def test_wizax_a(self, name):
        c64, load, cprt = _load_c64(name)
        result = detect_vibrants_v20(c64, load, cprt)
        assert result is not None
        assert 'Wizax-A variant' in result, \
            f"{name} should hit Wizax-A cluster, got: {result}"

    def test_wizax_b(self):
        c64, load, cprt = _load_c64('Cool_as_Wize_Title.sid')
        result = detect_vibrants_v20(c64, load, cprt)
        assert result is not None
        assert 'Wizax-B variant' in result, \
            f"Cool_as_Wize_Title should hit Wizax-B cluster, got: {result}"

    def test_wizax_clusters_mutually_exclusive(self):
        """Wizax-A files must NOT match Wizax-B, and vice versa."""
        for name in ('2000_A_D.sid', 'Fight_TST_II.sid', 'Hall_of_Fame.sid'):
            c64, load, cprt = _load_c64(name)
            result = detect_vibrants_v20(c64, load, cprt)
            assert 'Wizax-B variant' not in result
        c64, load, cprt = _load_c64('Cool_as_Wize_Title.sid')
        result = detect_vibrants_v20(c64, load, cprt)
        assert 'Wizax-A variant' not in result


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
