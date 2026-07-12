"""MCP server exposing SIDM2's sidm2-sid-trace tool as SID register-write tracing.

Wraps tools/sidm2-sid-trace.exe (built from zig64, a cycle-accurate 6502/SID
emulator: https://github.com/M64GitHub/zig64) so an MCP client can trace the
$D400-$D418 register writes a C64 program makes, frame by frame, and diff two
traces against each other.

Built for the sid-reference-project knowledge base's verification loop: a
player knowledge card only becomes `status: verified` once its documented
init/play reconstruction is assembled and its register-write trace confirmed
to match a reference trace (see sid-reference-project/knowledge/README.md).
That's exactly what trace_prg / trace_sid / diff_traces exist to do — this
server has no dependency on that project and is generically useful for any
C64/SID register-level verification.

Reuses the exact subprocess invocation and .sid->.prg extraction logic
already proven in sidm2/zig64_audio_gate.py (SIDM2's own post-build audio
safety gate), just exposed as MCP tools instead of an internal Python
function.
"""
from __future__ import annotations

import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="sidm2-siddump",
    instructions=(
        "Trace SID chip register writes ($D400-$D418) from C64 programs "
        "using SIDM2's cycle-accurate zig64-based tracer. Use trace_sid for "
        "an existing .sid file, trace_prg for a raw .prg with explicit "
        "init/play addresses (e.g. a hand-assembled reconstruction), and "
        "diff_traces to check whether two traces are register-write-identical."
    ),
)

DEFAULT_TRACER = Path(__file__).resolve().parent.parent / "tools" / "sidm2-sid-trace.exe"


def _run_tracer(tracer: Path, prg_path: Path, frames: int, init_addr: int,
                 play_addr: int, subtune: int) -> list[dict]:
    args = [str(tracer), str(prg_path), str(frames),
            f"{init_addr:04x}", f"{play_addr:04x}", str(subtune)]
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(
            f"sidm2-sid-trace exited {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    rows = []
    for line in result.stderr.splitlines():
        line = line.strip()
        if not line or line.startswith("frame,") or line.startswith("---") or "," not in line:
            continue
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            frame = int(parts[0])
            cycle = int(parts[1])
        except ValueError:
            continue
        rows.append({
            "frame": frame,
            "cycle": cycle,
            "register": parts[2],
            "old_val": parts[3],
            "new_val": parts[4],
        })
    return rows


def _sid_to_prg(sid_path: Path) -> tuple[bytes, int, int]:
    """Extract (prg_bytes, init_addr, play_addr) from a PSID/RSID file.

    Same extraction logic as sidm2/zig64_audio_gate.py's verify_sf2_audio().
    """
    data = sid_path.read_bytes()
    data_offset = struct.unpack(">H", data[6:8])[0]
    load_addr = struct.unpack(">H", data[8:10])[0]
    init_addr = struct.unpack(">H", data[10:12])[0]
    play_addr = struct.unpack(">H", data[12:14])[0]
    content = data[data_offset:]
    if load_addr == 0:
        load_addr = struct.unpack("<H", content[:2])[0]
        content = content[2:]
    prg_bytes = struct.pack("<H", load_addr) + content
    return prg_bytes, init_addr, play_addr


@mcp.tool()
def trace_prg(
    prg_path: str,
    init_addr: str,
    play_addr: str,
    frames: int = 50,
    subtune: int = 0,
    tracer_path: Optional[str] = None,
) -> dict:
    """Trace SID register writes from a raw .prg file.

    Args:
        prg_path: path to a C64 .prg (2-byte load address + binary).
        init_addr: init routine address, hex string (e.g. "1000" or "$1000").
        play_addr: play routine address, hex string (e.g. "10a1").
        frames: number of PAL frames to run PLAY for (default 50 = 1 second).
        subtune: subtune number passed to INIT in the accumulator (default 0).
        tracer_path: override path to sidm2-sid-trace.exe (defaults to
            SIDM2's tools/sidm2-sid-trace.exe).

    Returns a dict with `write_count` and `writes`: a list of
    {frame, cycle, register, old_val, new_val} in execution order — one
    entry per actual SID register write (not one per frame).
    """
    tracer = Path(tracer_path) if tracer_path else DEFAULT_TRACER
    if not tracer.exists():
        raise FileNotFoundError(f"sidm2-sid-trace.exe not found at {tracer}")
    prg = Path(prg_path)
    if not prg.exists():
        raise FileNotFoundError(f"prg file not found: {prg}")

    writes = _run_tracer(
        tracer, prg, frames,
        int(init_addr.lstrip("$"), 16), int(play_addr.lstrip("$"), 16),
        subtune,
    )
    return {"write_count": len(writes), "writes": writes}


@mcp.tool()
def trace_sid(
    sid_path: str,
    frames: int = 50,
    subtune: int = 0,
    tracer_path: Optional[str] = None,
) -> dict:
    """Trace SID register writes from a PSID/RSID .sid file.

    Extracts the load address and PSID-declared init/play addresses from the
    .sid header automatically (no need to know them up front), builds a temp
    .prg, and traces it the same way trace_prg does.

    Args:
        sid_path: path to a .sid file.
        frames: number of PAL frames to run PLAY for (default 50 = 1 second).
        subtune: subtune number passed to INIT in the accumulator (default 0).
        tracer_path: override path to sidm2-sid-trace.exe.

    Returns a dict with `init_addr`, `play_addr` (as read from the SID
    header), `write_count`, and `writes` (same shape as trace_prg).
    """
    tracer = Path(tracer_path) if tracer_path else DEFAULT_TRACER
    if not tracer.exists():
        raise FileNotFoundError(f"sidm2-sid-trace.exe not found at {tracer}")
    sid = Path(sid_path)
    if not sid.exists():
        raise FileNotFoundError(f"sid file not found: {sid}")

    prg_bytes, init_addr, play_addr = _sid_to_prg(sid)
    with tempfile.NamedTemporaryFile(suffix=".prg", delete=False) as f:
        f.write(prg_bytes)
        tmp_prg = Path(f.name)
    try:
        writes = _run_tracer(tracer, tmp_prg, frames, init_addr, play_addr, subtune)
    finally:
        tmp_prg.unlink(missing_ok=True)

    return {
        "init_addr": f"${init_addr:04x}",
        "play_addr": f"${play_addr:04x}",
        "write_count": len(writes),
        "writes": writes,
    }


@mcp.tool()
def diff_traces(trace_a: list[dict], trace_b: list[dict]) -> dict:
    """Compare two register-write traces (as returned by trace_prg/trace_sid's
    `writes` list) for an exact match.

    Cycle numbers are compared too (not just register/value) — two
    functionally-identical players rarely diverge in cycle timing unless one
    genuinely takes a different code path. If you need a timing-tolerant
    comparison, pre-filter the `cycle` key out of both lists before calling
    this.

    Returns a dict with `match` (bool), `first_divergence` (the first index
    where the two traces differ, or null if they match / one is a prefix of
    the other), and `length_a` / `length_b`.
    """
    first_divergence = None
    for i, (a, b) in enumerate(zip(trace_a, trace_b)):
        if a != b:
            first_divergence = i
            break
    else:
        if len(trace_a) != len(trace_b):
            first_divergence = min(len(trace_a), len(trace_b))

    return {
        "match": first_divergence is None,
        "first_divergence": first_divergence,
        "length_a": len(trace_a),
        "length_b": len(trace_b),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
