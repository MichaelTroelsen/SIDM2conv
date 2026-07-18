# tools/ — external binaries and the zig64 tracer

Third-party Windows executables used as optional fallbacks, plus SIDM2's own SID register
tracer. Nothing here is required for a normal conversion — the Python implementations in
`pyscript/` cover the same ground cross-platform.

## SIDM2's own tracer

| File | Purpose |
|---|---|
| `sidm2-sid-trace.exe` | Cycle-accurate 6502/SID register tracer built on [zig64](https://github.com/M64GitHub/zig64). Emits CSV on stderr. |
| `sidm2_sid_trace.zig` | **Source of truth** for the above — this repo, not the zig64 checkout. |

Usage: `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex] [subtune]`

It fails closed: on an unresolved IRQ handler or zero SID writes it prints `FAILED:` and exits
non-zero rather than emitting an empty trace. **Check the exit code**, do not just parse stderr.
Use at least 200 frames before calling a file broken — a too-short window is indistinguishable
from a broken trace.

Rebuild: copy `sidm2_sid_trace.zig` into the zig64 checkout at `src/examples/`, run `zig build`,
and copy `zig-out/bin/sidm2-sid-trace.exe` back here. See `CLAUDE.md` for the full note.

## Third-party fallbacks

| File | Purpose | Python equivalent |
|---|---|---|
| `siddump.exe` | SID emulator / frame dump | `pyscript/siddump_complete.py` |
| `player-id.exe` | Player type detection | — |
| `SIDwinder.exe` | Disassembler (+ `SIDwinder.cfg`) | `pyscript/sidwinder_trace.py` |
| `SIDdecompiler.exe` | Memory layout analyzer | — |
| `SID2WAV.EXE` | SID to WAV | `sidm2/vsid_wrapper.py` (VICE, preferred) |

Each carries its own licence, separate from this project's.

Built from source in this repo, each with its own README: `sf2pack/` (SF2 → SID packer with 6502
relocation) and `sf2export/` (SF2 → SID exporter).

## Note on the previous contents of this file

Until 2026-07-18 this file was SIDwinder's own README (v0.2.6), describing a different product and
promising `tools/exomizer.exe` and `tools/KickAss.jar` — neither of which is present, and neither of
which SIDM2 needs. See issue #12.
