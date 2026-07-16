"""zig64-based post-build audio verification gate.

The py65-based ch_seq_ptr safety gate (sidm2/ch_seq_safety_gate.py) catches
most cases where patching $1A1C/$1A1F (or the Wizax-A/Zetrex-YP redirect
addresses) corrupts player code. But py65 can't simulate CIA-IRQ-driven
players like the 1987-1990 Zetrex/Yield Point cluster: their INIT
installs a CIA timer pointing at the play address, and the gate's
py65 trace sees a stale/incomplete state after INIT. The gate then
incorrectly says SAFE for files where the patch actually corrupts audio
under cycle-accurate emulation.

Canonical case: Edie_Ball.sid. Bytes at $E849/$E86C ARE used by the
player as ch_seq_ptr (verified via py65 read tracing at PC $E0B7/$E0BC).
The patch correctly redirects to a shadow buffer. BUT Edie_Ball V0's
byte stream uses an early `$FF $5B` (loop to offset 91) that falls
INSIDE V1's stream region in the original — a shared-stream design
where V0 effectively continues into V1's data. The converter's shadow
pre-fill writes only V0's body bytes (8 zeros) + `$FF $5B` + zeros.
The player then loops to offset 91 of V0's shadow slot, which is zero,
producing silence where the original had real music.

This module runs zig64 (cycle-accurate) on the built SF2 vs the
original SID. If audio diverges, the caller can revert the ch_seq_ptr
patch and re-emit. ~50ms per call (200ms for 16-frame two-side trace),
acceptable for one-shot conversion.
"""
from __future__ import annotations
import json
import os
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

# --------------------------------------------------------------------------
# The RSID fallback (VICE)
#
# zig64 drives a tune by CALLING its PSID-declared play address once per frame.
# RSID files that install their own IRQ declare play=$0000: there is nothing to
# call, and zig64 has no autonomous VIC/CIA interrupt delivery, so the player
# can never run. Those files are untraceable here — the tracer says so (exit
# non-zero + FAILED) rather than emitting an empty trace.
#
# `vsid-trace.js` (in the separate sid-reference-project) wraps VICE's vsid,
# which runs a full emulated C64, so the machine drives the player. Measured:
# 21 of SIDM2's 22 untraceable RSIDs trace under it.
#
# CRITICAL — NEVER MIX THE TWO TOOLS IN ONE COMPARISON. Verified on Stinsen
# (a PSID both drive): the (register, value) sequence is IDENTICAL across all
# 90 writes, but FRAME ATTRIBUTION IS OFFSET BY ONE (zig64 frame 1 == vsid
# frame 0). This gate compares (frame, register, value), so a mixed comparison
# would diverge on every row. If zig64 fails on either side, BOTH sides are
# re-traced with vsid.
# --------------------------------------------------------------------------
_VSID_TRACE_JS_DEFAULT = Path(
    r"C:\Users\mit\claude\sid-reference-project\scripts\dev\vsid-trace.js")


def _vsid_trace_js() -> Optional[Path]:
    """Path to the VICE wrapper, or None if unavailable.

    Override with $VSID_TRACE_JS. It lives in a separate project and needs
    node + VICE's vsid.exe, so absence is normal and simply disables the
    fallback (the gate then fails closed on RSID, as before).
    """
    env = os.environ.get("VSID_TRACE_JS")
    cand = Path(env) if env else _VSID_TRACE_JS_DEFAULT
    return cand if cand.exists() else None


def _trace_vsid(sid_path: Path, frames: int,
                script: Path) -> Optional[List[Tuple[str, str, str]]]:
    """Trace a .sid via VICE. Returns rows in _trace's format, or None.

    --changed-only is REQUIRED: vsid records redundant writes (re-writing a
    register's current value), zig64 only value-changing ones. The wrapper
    emits zig64's own register names, so rows are directly comparable.
    """
    try:
        r = subprocess.run(
            ["node", str(script), str(sid_path), "--frames", str(frames),
             "--json", "--changed-only"],
            capture_output=True, text=True, timeout=300,
        )
    except (OSError, subprocess.SubprocessError):
        return None          # node missing / vsid blew up → no evidence
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
    except (ValueError, TypeError):
        return None
    rows: List[Tuple[str, str, str]] = []
    for fr in d.get("frames", []):
        f = str(fr.get("frame"))
        for w in fr.get("writes", []):
            reg, val = w.get("register"), w.get("value")
            if reg is None or val is None:
                continue
            rows.append((f, reg, "$%02X" % val))
    return rows or None


def _trace(prg_path: Path, frames: int, init_addr: int, play_addr: int,
           tracer: Path) -> Optional[List[Tuple[str, str, str]]]:
    """Run zig64 and return (frame, register, value) tuples.

    Returns None if the tracer could not produce a trustworthy trace (it
    exited non-zero or reported an explicit FAILED diagnostic). None means
    "no evidence", which is NOT the same as an empty trace and must never
    be compared for equality — see verify_sf2_audio.
    """
    r = subprocess.run([str(tracer), str(prg_path), str(frames),
                        f"{init_addr:04x}", f"{play_addr:04x}"],
                       capture_output=True, text=True)
    # The tracer signals an untraceable file both ways; honour either. Its
    # FAILED line contains commas, so it must be rejected before parsing or
    # it would simply be filtered out and look like a clean empty trace.
    if r.returncode != 0 or "FAILED:" in r.stderr:
        return None
    rows = []
    for L in r.stderr.splitlines():
        if not L or L.startswith("frame") or L.startswith("---"):
            continue
        if "," not in L:
            continue
        p = L.split(",")
        if len(p) >= 5:
            rows.append((p[0], p[2], p[4]))
    return rows


def _verify_via_vsid(sf2_bytes: bytes, sid_path: Path, sf2_init_addr: int,
                     sf2_play_addr: int, frames: int):
    """Re-trace BOTH sides under VICE. -> (sid_rows, sf2_rows), either None.

    The original .sid goes to vsid as-is (RSID and all). The SF2 is a raw PRG,
    so it is wrapped in a minimal PSID declaring its Driver 11 entry points —
    vsid then drives it exactly as zig64 would have.
    """
    script = _vsid_trace_js()
    if script is None:
        return None, None        # fallback unavailable → stay fail-closed
    from sidm2.fidelity_common import psid_wrap

    sf2_load = struct.unpack("<H", sf2_bytes[:2])[0]
    psid = psid_wrap(sf2_bytes[2:], sf2_load, sf2_init_addr, sf2_play_addr)
    with tempfile.NamedTemporaryFile(suffix=".sid", delete=False) as f:
        f.write(psid)
        sf2_sid_path = Path(f.name)
    try:
        return (_trace_vsid(sid_path, frames, script),
                _trace_vsid(sf2_sid_path, frames, script))
    finally:
        sf2_sid_path.unlink(missing_ok=True)


def verify_sf2_audio(sf2_bytes: bytes, sid_path: Path,
                      sf2_init_addr: int, sf2_play_addr: int,
                      sid_init_addr: int, sid_play_addr: int,
                      tracer_path: Optional[Path] = None,
                      frames: int = 16) -> bool:
    """Return True iff the SF2's audio (via cycle-accurate zig64 trace)
    matches the original SID byte-identically over the first `frames`
    PAL frames.

    Args:
        sf2_bytes: the built SF2 PRG bytes (load addr + content)
        sid_path: path to the original .sid file
        sf2_init_addr, sf2_play_addr: entry points to trace in the SF2
                                       (typically Block 2 declared addrs,
                                        e.g. $0F90/$0F94)
        sid_init_addr, sid_play_addr: entry points to trace in the SID
                                       (PSID-declared init/play)
        tracer_path: path to sidm2-sid-trace.exe (defaults to
                      tools/sidm2-sid-trace.exe relative to project root)
        frames: how many PLAY frames to trace. 16 is enough to catch
                most patches; larger windows are more thorough but
                slower. 16 frames = ~50ms wall clock total.

    Returns:
        True if every (frame, register, value) tuple matches.
        False if any divergence is detected, OR if the comparison could not
        be made at all (tracer failure / empty reference trace) — the gate
        fails closed, since verifying nothing is not a pass. The one
        deliberate exception is a missing tracer binary, which still returns
        True to preserve behaviour on systems without zig64 installed.

    If zig64 cannot drive the file at all (an RSID installing its own IRQ),
    BOTH sides are automatically re-traced under VICE when that wrapper is
    available — see _verify_via_vsid. Without it such files stay unverifiable
    and the gate returns False.
    """
    if tracer_path is None:
        # Default: tools/sidm2-sid-trace.exe relative to package root
        pkg_root = Path(__file__).resolve().parent.parent
        tracer_path = pkg_root / "tools" / "sidm2-sid-trace.exe"
    if not tracer_path.exists():
        # No tracer available → can't verify; assume safe (preserve
        # existing behavior on systems without zig64).
        return True

    # Build a temp PRG from the SID file (load_addr LE + binary)
    d = sid_path.read_bytes()
    do = struct.unpack(">H", d[6:8])[0]
    la = struct.unpack(">H", d[8:10])[0]
    c = d[do:]
    if la == 0:
        la = struct.unpack("<H", c[:2])[0]
        c = c[2:]
    sid_prg_bytes = struct.pack("<H", la) + c

    with tempfile.NamedTemporaryFile(suffix=".prg", delete=False) as f:
        f.write(sid_prg_bytes)
        sid_prg_path = Path(f.name)
    with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
        f.write(sf2_bytes)
        sf2_prg_path = Path(f.name)

    try:
        sid_rows = _trace(sid_prg_path, frames, sid_init_addr,
                           sid_play_addr, tracer_path)
        sf2_rows = _trace(sf2_prg_path, frames, sf2_init_addr,
                           sf2_play_addr, tracer_path)
        if sid_rows is None or sf2_rows is None:
            # zig64 could not drive one side — almost always an RSID whose
            # play=$0000 player it cannot reach. Retry BOTH sides under VICE.
            # Both, never one: the tools disagree on frame attribution by 1.
            sid_rows, sf2_rows = _verify_via_vsid(
                sf2_bytes, sid_path, sf2_init_addr, sf2_play_addr, frames)
    finally:
        sid_prg_path.unlink(missing_ok=True)
        sf2_prg_path.unlink(missing_ok=True)

    # Fail closed: absence of evidence is not evidence of a match. A tracer
    # failure (None) or an empty reference trace means we verified NOTHING —
    # returning True there certified unchecked output (two empty traces used
    # to compare equal and pass, e.g. any SF2 built from an RSID whose IRQ the
    # tracer cannot drive, such as SID/Laxity/Broken_Ass.sid).
    if sid_rows is None or sf2_rows is None:
        return False
    if not sid_rows:
        return False
    if len(sid_rows) != len(sf2_rows):
        return False
    for a, b in zip(sid_rows, sf2_rows):
        if a != b:
            return False
    return True
