"""Tests for sidm2.zetrex_yp_detector — F1 (sequences) wire-up for the
3-file Zetrex/YP cluster (v3.5.16).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.zetrex_yp_detector import detect_zetrex_yp_layout


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


class TestDetectZetrexYP:
    @pytest.mark.parametrize("name,expected_lo,expected_hi", [
        ('Jewels.sid', 0xE849, 0xE859),
        ('Waste.sid',  0xE961, 0xE96C),
        ('Racer.sid',  0xE849, 0xE86C),
    ])
    def test_detects_zetrex_yp_file(self, name, expected_lo, expected_hi):
        c64, load = _load_c64(name)
        result = detect_zetrex_yp_layout(c64, load)
        assert result is not None, f"{name} should match Zetrex/YP"
        assert result.ptr_lo_addr == expected_lo
        assert result.ptr_hi_addr == expected_hi


class TestRejectsNonZetrexYP:
    @pytest.mark.parametrize("path,name", [
        (ROOT / 'SID' / 'Stinsens_Last_Night_of_89.sid', 'Stinsen'),
        (ROOT / 'SID' / 'Beast.sid',                     'Beast'),
        (ROOT / 'SID' / 'Angular.sid',                   'Angular'),
        (ROOT / 'SID' / 'Unboxed_Ending_8580.sid',       'Unboxed'),
    ])
    def test_rejects_np21_files(self, path, name):
        if not path.exists(): pytest.skip(f"missing {name}")
        buf = open(path, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do+1] << 8); c64 = buf[do+2:]
        else:
            c64 = buf[do:]
        assert detect_zetrex_yp_layout(c64, load) is None

    @pytest.mark.parametrize("name", [
        '2000_A_D.sid',              # Wizax-A
        'Cool_as_Wize_Title.sid',    # Wizax-B
        'Galax_it_y.sid',             # 1988 2000 A.D.
        'Atom_Rock.sid',              # Flexible Arts
        'James_Bond_Theme_Remix.sid',
        'Fast_Stuff_1.sid',
    ])
    def test_rejects_other_v20_files(self, name):
        c64, load = _load_c64(name)
        assert detect_zetrex_yp_layout(c64, load) is None


class TestPipelineIntegration:
    def test_conversion_succeeds_for_all_3(self):
        import subprocess
        CONVERTER = ROOT / 'scripts' / 'sid_to_sf2.py'
        for name in ('Jewels.sid', 'Waste.sid', 'Racer.sid'):
            sid = ROOT / 'SID' / 'Laxity' / name
            sf2 = ROOT / 'bin' / f'_test_zyp_{name.replace(".sid", "")}.sf2'
            sf2.unlink(missing_ok=True)
            sf2.with_suffix('.txt').unlink(missing_ok=True)
            rc = subprocess.run(
                [sys.executable, str(CONVERTER), str(sid), str(sf2)],
                capture_output=True, text=True, cwd=str(ROOT)
            )
            assert rc.returncode == 0, f"{name}: convert failed:\n{rc.stderr[-500:]}"
            assert sf2.exists() and sf2.stat().st_size > 1024
            sf2.unlink(missing_ok=True)
            sf2.with_suffix('.txt').unlink(missing_ok=True)

    def test_jewels_zig64_stub_at_1000(self):
        """For Zetrex/YP at load $E000, zig64 needs a JMP stub at $1000
        because the embedded binary doesn't cover that address. Verify
        the converter writes JMP INIT_HANDLER (0x0F90) there."""
        import subprocess
        CONVERTER = ROOT / 'scripts' / 'sid_to_sf2.py'
        sid = ROOT / 'SID' / 'Laxity' / 'Jewels.sid'
        sf2 = ROOT / 'bin' / '_test_zyp_stub.sf2'
        sf2.unlink(missing_ok=True)
        sf2.with_suffix('.txt').unlink(missing_ok=True)
        subprocess.run([sys.executable, str(CONVERTER), str(sid), str(sf2)],
                       capture_output=True, text=True, cwd=str(ROOT))
        data = open(sf2, 'rb').read()
        load = data[0] | (data[1] << 8)
        off = 2 + (0x1000 - load)
        # Expect JMP $0F90 (INIT_HANDLER) at $1000
        assert data[off] == 0x4C, f"$1000 should be JMP opcode (4C), got ${data[off]:02X}"
        target = data[off+1] | (data[off+2] << 8)
        assert target == 0x0F90, f"$1000 JMP target should be $0F90, got ${target:04X}"
        # Expect JMP $0F94 (PLAY_HANDLER) at $1003
        assert data[off+3] == 0x4C
        target2 = data[off+4] | (data[off+5] << 8)
        assert target2 == 0x0F94, f"$1003 JMP target should be $0F94, got ${target2:04X}"
        sf2.unlink(missing_ok=True)
        sf2.with_suffix('.txt').unlink(missing_ok=True)
