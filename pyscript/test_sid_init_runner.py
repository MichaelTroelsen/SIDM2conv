"""Regression tests for sidm2.sid_init_runner — particularly the
trace_play_reads contract: the returned `reads` set must contain
ONLY addresses the player accessed during PLAY ticks, NOT the entire
64KB address space.

The previous bug: the post-PLAY snapshot loop iterated `new_mem[i]`
through the TracingMemory's `__getitem__` override, which added every
i in 0..0xFFFF to `reads` — making the set useless as a candidate
filter in the ch_seq_ptr autodetector.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

py65 = pytest.importorskip("py65.devices.mpu6502")

from sidm2.sid_init_runner import trace_play_reads


def parse_psid(p):
    buf = open(p, 'rb').read()
    do = (buf[6] << 8) | buf[7]
    load = (buf[8] << 8) | buf[9]
    init = (buf[10] << 8) | buf[11]
    play = (buf[12] << 8) | buf[13]
    if load == 0:
        load = buf[do] | (buf[do + 1] << 8)
        c64 = buf[do + 2:]
    else:
        c64 = buf[do:]
    return load, init, play, bytes(c64)


class TestTracePlayReads:
    def test_reads_set_is_bounded_not_full_64k(self):
        """The reads set after trace_play_reads must NOT contain all
        65536 addresses — that would mean the snapshot loop polluted
        it (the bug fixed in this commit)."""
        sid = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            pytest.skip(f"missing {sid}")
        load, init, play, c64 = parse_psid(str(sid))
        result = trace_play_reads(c64, load, init, play, n_ticks=3)
        assert result is not None, "Stinsen INIT/PLAY should run cleanly"
        snapshot, reads = result
        # Stinsen typically reads 200-2000 addresses across 3 PLAY ticks.
        # Anything close to 65536 means the snapshot loop polluted it.
        assert len(reads) < 5000, (
            f"reads set has {len(reads)} addresses — likely polluted by "
            f"the snapshot loop (bug regression)"
        )
        # And: reads must contain SOMETHING — at least the SID register
        # range or the c64 binary's PLAY entry.
        assert len(reads) > 50, (
            f"reads set too sparse ({len(reads)}) — trace_play_reads "
            f"may not have captured PLAY-time accesses"
        )

    def test_reads_set_includes_play_entry(self):
        """The first instruction at play_addr must be in `reads` —
        that's the very first byte fetched during PLAY."""
        sid = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            pytest.skip(f"missing {sid}")
        load, init, play, c64 = parse_psid(str(sid))
        result = trace_play_reads(c64, load, init, play, n_ticks=1)
        assert result is not None
        _snapshot, reads = result
        assert play in reads, (
            f"play_addr ${play:04X} not in reads — instruction-fetch "
            f"tracing is broken"
        )

    def test_snapshot_matches_runtime_memory(self):
        """The snapshot must capture actual post-PLAY memory state,
        not be all zeros."""
        sid = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            pytest.skip(f"missing {sid}")
        load, init, play, c64 = parse_psid(str(sid))
        result = trace_play_reads(c64, load, init, play, n_ticks=1)
        assert result is not None
        snapshot, _reads = result
        assert len(snapshot) == 0x10000
        # Spot-check: the c64 binary itself must be in the snapshot at
        # its load address.
        for i in range(min(len(c64), 256)):
            assert snapshot[load + i] == c64[i], (
                f"snapshot[${load + i:04X}] = ${snapshot[load + i]:02X} "
                f"!= c64[{i}] = ${c64[i]:02X}"
            )
