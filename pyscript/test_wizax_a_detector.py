"""Tests for sidm2.wizax_a_detector — F1 (sequences) wire-up for the
4-file Wizax-A cluster (v3.5.15).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.wizax_a_detector import detect_wizax_a_layout


def _load_c64(name):
    sid = ROOT / 'SID' / 'Laxity' / name
    if not sid.exists():
        pytest.skip(f"missing {name}")
    buf = open(sid, 'rb').read()
    do = (buf[6] << 8) | buf[7]
    load = (buf[8] << 8) | buf[9]
    if load == 0:
        load = buf[do] | (buf[do + 1] << 8); c64 = buf[do + 2:]
    else:
        c64 = buf[do:]
    return c64, load


class TestDetectWizaxA:
    @pytest.mark.parametrize("name,expected_lo,expected_hi", [
        ('2000_A_D.sid',         0x150C, 0x153D),
        ('Fight_TST_II.sid',     0x184A, 0x18B8),
        ('Hall_of_Fame.sid',     0xC73E, 0xC773),
        ('Min_Axel_F.sid',       0x1774, 0x179C),
    ])
    def test_detects_wizax_a_file(self, name, expected_lo, expected_hi):
        c64, load = _load_c64(name)
        result = detect_wizax_a_layout(c64, load)
        assert result is not None, f"{name} should match Wizax-A"
        assert result.ptr_lo_addr == expected_lo
        assert result.ptr_hi_addr == expected_hi


class TestRejectsNonWizaxA:
    @pytest.mark.parametrize("path,name", [
        (ROOT / 'SID' / 'Stinsens_Last_Night_of_89.sid', 'Stinsen'),
        (ROOT / 'SID' / 'Beast.sid',                     'Beast'),
        (ROOT / 'SID' / 'Angular.sid',                   'Angular'),
        (ROOT / 'SID' / 'Unboxed_Ending_8580.sid',       'Unboxed'),
    ])
    def test_rejects_np21_files(self, path, name):
        """NP21 canonical files have different signatures (no
        $A9 00 8D 04 D4... voice-clear sequence at the right offset)."""
        if not path.exists(): pytest.skip(f"missing {name}")
        buf = open(path, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do+1] << 8); c64 = buf[do+2:]
        else:
            c64 = buf[do:]
        assert detect_wizax_a_layout(c64, load) is None

    @pytest.mark.parametrize("name", [
        'Cool_as_Wize_Title.sid',   # Wizax-B (different player)
        'Galax_it_y.sid',           # 1988 2000 A.D.
        'Jewels.sid',                # Zetrex/YP
        'Atom_Rock.sid',             # Flexible Arts
        'James_Bond_Theme_Remix.sid',
        'Fast_Stuff_1.sid',
    ])
    def test_rejects_other_v20_files(self, name):
        """Other V20 variants must NOT match Wizax-A's signature."""
        c64, load = _load_c64(name)
        assert detect_wizax_a_layout(c64, load) is None

    def test_rejects_random_binary(self):
        """All-zero binary should not match."""
        assert detect_wizax_a_layout(bytes(0x2000), 0x1000) is None


class TestPipelineIntegration:
    """The Wizax-A pipeline redirects driver11 to laxity_raw_np21,
    which extracts patterns and patches ch_seq_ptr at file-specific
    addresses (not NP21's $0A1C/$0A1F)."""

    def test_conversion_succeeds(self):
        """Convert all 4 Wizax-A files — must not error."""
        import subprocess
        CONVERTER = ROOT / 'scripts' / 'sid_to_sf2.py'
        for name in ('2000_A_D.sid', 'Fight_TST_II.sid',
                     'Hall_of_Fame.sid', 'Min_Axel_F.sid'):
            sid = ROOT / 'SID' / 'Laxity' / name
            sf2 = ROOT / 'bin' / f'_test_wzx_{name.replace(".sid", "")}.sf2'
            sf2.unlink(missing_ok=True)
            sf2.with_suffix('.txt').unlink(missing_ok=True)
            rc = subprocess.run(
                [sys.executable, str(CONVERTER), str(sid), str(sf2)],
                capture_output=True, text=True, cwd=str(ROOT)
            )
            assert rc.returncode == 0, f"{name}: convert failed:\n{rc.stderr[-500:]}"
            assert sf2.exists() and sf2.stat().st_size > 1024, \
                f"{name}: SF2 too small ({sf2.stat().st_size if sf2.exists() else 0} bytes)"
            # Cleanup
            sf2.unlink(missing_ok=True)
            sf2.with_suffix('.txt').unlink(missing_ok=True)

    def test_patches_wizax_a_ptr_table_not_np21_default(self):
        """After conversion, the Wizax-A ptr table should be modified
        (not NP21's $0A1C/$0A1F). Verify by reading the SF2 bytes at
        $150C in the converted 2000_A_D.sf2 — should be POINT-AT-SHADOW
        addresses, not the original $156E/$1570/$1589."""
        import subprocess
        CONVERTER = ROOT / 'scripts' / 'sid_to_sf2.py'
        sid = ROOT / 'SID' / 'Laxity' / '2000_A_D.sid'
        sf2 = ROOT / 'bin' / '_test_wzx_patch.sf2'
        sf2.unlink(missing_ok=True)
        sf2.with_suffix('.txt').unlink(missing_ok=True)
        rc = subprocess.run(
            [sys.executable, str(CONVERTER), str(sid), str(sf2)],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        assert rc.returncode == 0
        # Read file content at $150C (Wizax-A ptr_lo table)
        data = open(sf2, 'rb').read()
        load = data[0] | (data[1] << 8)
        off = 2 + (0x150C - load)
        # The original V0 ptr_lo was $6E (from $156E). After patching it
        # should be DIFFERENT (pointing at shadow buffer).
        v0_lo_patched = data[off]
        assert v0_lo_patched != 0x6E, \
            f"V0 ptr_lo NOT patched (still $6E); expected shadow addr"
        sf2.unlink(missing_ok=True)
        sf2.with_suffix('.txt').unlink(missing_ok=True)
