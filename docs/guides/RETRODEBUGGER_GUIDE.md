# RetroDebugger MCP Guide

**Real-time, live 6502/C64 debugging via the `mcp__retrodebugger__*` tool set**

**Version**: RetroDebugger v0.64.68 (`tools/RetroDebugger v0.64.68/`)
**Access method**: MCP tools (`mcp__retrodebugger__*`) — NOT the raw HTTP/JSON API described in
`docs/TOOLS_REFERENCE.md`'s older RetroDebugger section. That section documents the tool's
underlying REST API as a *future integration option*; this guide documents the MCP tool layer
that is **already connected and working today**.
**Last Updated**: 2026-07-19 (first written after the Blackbird/Fargo live-trace session)

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Tool Reference](#tool-reference)
4. [Worked Example: Live-Tracing a Compressed Note Stream](#worked-example-live-tracing-a-compressed-note-stream)
5. [Gotchas and Practical Tips](#gotchas-and-practical-tips)
6. [When to Use RetroDebugger vs siddump / SIDwinder / zig64](#when-to-use-retrodebugger-vs-siddump--sidwinder--zig64)
7. [See Also](#see-also)

---

## Overview

RetroDebugger is a real 6502 emulator (VICE core + reSID) with a full debugger: breakpoints,
memory read/write, live disassembly, CPU single-stepping, snapshots, and warp-speed execution.
Unlike SIDM2's own `zig64`-based tracer (`tools/sidm2-sid-trace.exe`), which only drives a
program through a simple INIT/PLAY harness, RetroDebugger runs a **complete, interactive C64**
— useful whenever you need to actually watch a player's internal state evolve over real playback
time, not just capture SID register writes.

If the deferred-tool list shows `mcp__retrodebugger__*` names without full schemas, load them
first:

```
ToolSearch("select:mcp__retrodebugger__retro_load,mcp__retrodebugger__retro_continue,mcp__retrodebugger__retro_cpu_status,...")
```

(loading one tool from this server tends to make the rest of the server's tools available too,
but it's safest to explicitly select everything you expect to need in one call).

---

## Quick Start

```
1. retro_list_platforms()                          # see what's running ("c64" is the usual one)
2. retro_load(path="C:/.../SID/some_file.sid")      # loads AND starts playing immediately
3. retro_cpu_status(platform="c64")                 # confirm it's alive — PC should be moving
4. retro_disassemble(platform="c64", address=X, lines=N)   # look around, live, at real code
5. retro_breakpoint_add(platform="c64", address=X)  # stop at the interesting spot
6. retro_continue(platform="c64")                   # resume until the breakpoint fires
7. retro_cpu_status(...) / retro_memory_read(...)   # inspect state at the breakpoint
```

A `.sid` file loads and starts running on its own — no separate "run" step, and audio plays
through the host machine's speakers in real time (useful as a sanity check: if you can hear it,
the load worked).

---

## Tool Reference

### Platform control
| Tool | Purpose |
|------|---------|
| `retro_list_platforms()` | Lists `c64`/`c64u`/`atari800`/`nes` and whether each is running |
| `retro_start_platform(platform)` | Starts the emulation thread |
| `retro_stop_platform(platform)` | **Stops the thread — but in practice this behaved like a pause, not a hard reset** (CPU registers/PC were still readable afterward, and `retro_start_platform` resumed cleanly). Prefer `retro_pause` for the same effect with clearer intent. |
| `retro_pause(platform)` | Pause emulation (the intentionally-named counterpart to `retro_continue`) |
| `retro_reset(platform, hard=true)` | Reset the machine (hard or soft) — **doesn't reliably work on a `.sid`-loaded session**: observed doing nothing (CPU state kept executing from exactly where it was, not from a reset vector) when the loaded program is running under the SID-player harness rather than a real boot/disk. Don't rely on it to silence audio — see "Silencing audio" below. |
| `retro_load(path)` | Load a PRG/SID/XEX/ROM file — starts running immediately |
| `retro_warp(platform, enabled)` | Toggle warp speed (no frame-rate cap) — combine with polling `retro_cpu_counters` to fast-forward to a target frame without single-stepping |

### Execution control
| Tool | Purpose |
|------|---------|
| `retro_continue(platform)` | Resume until the next breakpoint or a manual pause |
| `retro_step_instruction(platform)` | Execute exactly one CPU instruction |
| `retro_step_cycle(platform)` | Execute exactly one CPU clock cycle |
| `retro_step_subroutine(platform)` | Step *over* a `JSR` — runs until that routine returns |
| `retro_cpu_jump(platform, address)` | Force the PC to a specific address |

### Breakpoints and watches
| Tool | Purpose |
|------|---------|
| `retro_breakpoint_add/remove/list(platform, address)` | Plain CPU (execution) breakpoints |
| `retro_memory_breakpoint_add(platform, address, access="write"\|"read", comparison, value)` | **Break on a memory access**, not just execution — e.g. "pause the instant this zero-page pointer is written", far more targeted than polling with `retro_continue` in a loop. Wasn't used in the first Blackbird trace session; should be the default choice for "notify me when X changes" instead of manual continue/read cycles. |
| `retro_memory_breakpoint_remove/list(platform, ...)` | Manage memory breakpoints |
| `retro_watch_add/remove/list(platform, address, name)` | Named watches (informational, doesn't pause) |

### CPU / machine state
| Tool | Purpose |
|------|---------|
| `retro_cpu_status(platform)` | `a`, `x`, `y`, `p`, `sp`, `pc`, raster position, etc. |
| `retro_cpu_counters(platform)` | `cycle`, `instruction`, and — usefully — a running **`frame`** counter (great for "how far into the song are we") |
| `retro_machine_state(platform)` | Broader machine state snapshot |
| `retro_code_map(platform, startAddress, endAddress)` | Which address ranges have actually executed (code vs. data, discovered live) |

### Memory
| Tool | Purpose |
|------|---------|
| `retro_memory_read(platform, address, length)` | Returns **base64-encoded** bytes — decode before use (`base64.b64decode(...)`) |
| `retro_memory_write(platform, address, data)` | Write base64-encoded bytes into RAM |
| `retro_memory_search(platform, value, startAddress, endAddress)` | Find every address currently holding a given byte value (e.g. hunting for a lives/score counter) |
| `retro_search_pattern(platform, pattern, executedOnly, ...)` | Search for an opcode pattern, e.g. `"STA $D400,X"`, `"LDA #??"` — restricted to executed regions by default |
| `retro_segment_read/write(platform, segment)` | Read/set the active *debug symbol* segment (if the loaded program has segment metadata) |

### Disassembly / assembly
| Tool | Purpose |
|------|---------|
| `retro_disassemble(platform, address, lines)` | Live disassembly starting at an address; returns structured instructions **and** a preformatted text block. Capped at ~64 instructions per call regardless of the `lines` you request — issue multiple calls to cover a longer range. |
| `retro_assemble(platform, address, code)` | Assemble 6502 source and write the bytes directly into memory (atomic — nothing is written if any line fails) |

### Snapshots
| Tool | Purpose |
|------|---------|
| `retro_snapshot_save/load(platform, path)` | Save/load a full state snapshot to/from a file |
| `retro_snapshot_quick_save/quick_load(platform, slot 1-9)` | Same, using the UI's numbered quick-slots |

### Input (for interactive programs, not usually needed for SID tracing)
| Tool | Purpose |
|------|---------|
| `retro_input_key(platform, key, action)` | Press/release a keyboard key |
| `retro_input_joystick(platform, axes, action, port)` | Press/release joystick directions/buttons |
| `retro_input_joystick_state(platform, port)` | Read current joystick state |

---

## Worked Example: Live-Tracing a Compressed Note Stream

From the 2026-07-19 Blackbird (LFT) player session (`docs/players/BLACKBIRD.md`), tracing
`SID/LFT/Fargo.sid`'s note-stream decompressor:

```python
retro_list_platforms()                       # confirm "c64" exists
retro_load(path="C:/.../SID/LFT/Fargo.sid")  # loads + starts playing (audio audible)

# Found unpackvoice's address by cross-checking a live disassembly against the compiler's
# own relocation manifest (player.h) rather than guessing:
retro_disassemble(platform="c64", address=4096, lines=400)  # $1000 = playorg for this file
# -> saw "$100F: JMP $1259", matching the byte-offset math from the static template exactly

retro_breakpoint_add(platform="c64", address=4716)  # $126C = unpackvoice+11, the actual
                                                     # control-byte fetch (NOT unpackvoice's
                                                     # entry point, which fires on every no-op
                                                     # service call too)
retro_continue(platform="c64")
retro_cpu_status(platform="c64")   # X = voice index (0/7/14); A = free "L" (running decode
                                    # length for that voice) left over from an earlier LDA
retro_memory_read(platform="c64", address=226, length=2)  # zp_inptr (lo,hi) -> compute ptr
retro_memory_read(platform="c64", address=<ptr-1>, length=2)  # [offset_byte, control_byte]
```

To skip ahead many frames instead of single-stepping, use warp + poll counters, then pause and
re-arm the breakpoint once close to the target:

```python
retro_breakpoint_remove(platform="c64", address=4716)
retro_warp(platform="c64", enabled=True)
retro_continue(platform="c64")
retro_cpu_counters(platform="c64")   # poll repeatedly; "frame" climbs fast under warp
# ... once frame is close to the target ...
retro_pause(platform="c64")
retro_warp(platform="c64", enabled=False)
retro_breakpoint_add(platform="c64", address=4716)
retro_continue(platform="c64")       # resumes precise single-hit tracing from here
```

This combination (relocation-manifest-derived addresses + a breakpoint placed past the
uninteresting early-out branch + reading "free" register state + warp-to-approach) recovered
concrete ground truth (voice attribution order, control-byte values, transpose math) that a
purely static/offline decoder couldn't reconstruct on its own. Full writeup and captured data:
`docs/players/BLACKBIRD.md`, `memory/blackbird-lft-player.md`.

---

## Gotchas and Practical Tips

- **`retro_stop_platform` vs `retro_pause`**: both appeared to just pause (CPU state survived,
  `retro_start_platform` resumed cleanly) — but `retro_pause` is the tool actually named for
  this, prefer it to avoid ambiguity about whether a "stop" might someday mean a real teardown.
- **Break past the entry point, not at it**: a routine's entry often fires on every call
  including cheap early-out no-ops (e.g. "is there still enough buffered data? if so, return").
  Disassemble the routine first and place the breakpoint at the specific instruction that only
  executes on the interesting path.
- **Free state at a breakpoint**: registers can carry values loaded several instructions earlier
  that are still sitting there, unmodified, when a breakpoint fires — check the surrounding
  disassembly for what's still "live" in `A`/`X`/`Y` before doing an extra memory read to fetch
  something you might already have for free.
- **Memory reads are base64-encoded** — always decode (`base64.b64decode`) before interpreting
  bytes; it's easy to misread the raw JSON string as already being bytes.
- **Prefer `retro_memory_breakpoint_add` over manual polling** when watching for "notify me when
  this address changes" — it pauses execution automatically on the write/read instead of
  requiring a `continue` + `read` loop driven by hand.
- **`retro_disassemble` caps out around 64 instructions per call** regardless of the requested
  `lines` — plan on multiple calls (using `nextAddress` from the previous result) to cover a
  longer stretch of code.
- **Use `retro_cpu_counters`'s `frame` field**, not `rasterY`, to track "how far into the song
  are we" across many breakpoint hits — `rasterY` only tells you position within the *current*
  frame (0-311) and resets every frame.
- **This is a real machine, not zig64's simplified INIT/PLAY harness** — it will play files that
  zig64 can't trace at all (e.g. RSID files with self-installed IRQ handlers). If zig64 reports
  suspicious results (e.g. 0 SID writes) on a file that clearly has music, cross-check it here
  before assuming the file is broken.
- **Silencing audio when you're done — `retro_reset` is NOT reliable for this**: a `.sid` file
  keeps playing through real speakers as long as the platform is running, and neither
  `retro_pause` nor `retro_reset(hard=true)` reliably stops an already-sounding tone (`retro_pause`
  freezes CPU state but doesn't clear the SID's held oscillator/volume; `retro_reset` was observed
  doing nothing at all on a SID-harness-loaded session — the CPU just kept executing from the
  exact same PC instead of jumping to a reset vector). **The reliable fix is to write zeros
  directly over the SID register range instead**, which mutes it immediately regardless of what
  the CPU is doing:
  ```python
  import base64
  retro_memory_write(platform="c64", address=54272,          # $D400
                      data=base64.b64encode(bytes(25)).decode())  # 25 zero bytes = $D400-$D418
  retro_pause(platform="c64")
  ```
  `$D418` (the last of the 25 bytes, master volume/filter-select) is the one that matters most —
  zeroing it alone kills all audible output even if the oscillators are still conceptually
  "running". **Do this at the end of every RetroDebugger session** before moving on to other
  work, not just when something sounds obviously wrong — a loaded SID keeps playing through the
  user's speakers in the background otherwise.
- **Long manual trace loops don't scale in a single chat turn** — for anything beyond a handful
  of breakpoint hits, delegate the mechanical continue/read/log loop to a background agent (see
  the `Agent` tool) rather than driving dozens of round-trips by hand.

---

## When to Use RetroDebugger vs siddump / SIDwinder / zig64

| Need | Best tool |
|------|-----------|
| Batch frame-by-frame register dump for many files | `siddump_complete.py` |
| Cycle-accurate register trace of a normal PSID (known init/play) | `sidm2-sid-trace.exe` (zig64) |
| RSID with a self-installed IRQ handler, or zig64 reports 0 writes | `vsid-trace.js` (VICE wrapper, see `CLAUDE.md`) or RetroDebugger |
| Understanding *why* a player does something — live CPU state, register contents at a specific instruction, self-modifying code, ring-buffer contents | **RetroDebugger** (this guide) |
| Reverse-engineering an unknown compression/scheduling scheme where a static/offline model keeps getting the order wrong | **RetroDebugger** — get ground truth from the real CPU instead of guessing further |
| Disassembly for documentation/annotation | `SIDwinder.exe -disassemble` (best quality, batch-friendly) |

---

## See Also

- `docs/TOOLS_REFERENCE.md` — the older RetroDebugger section describing its raw HTTP/JSON API
  (a different, not-currently-used access path; MCP is what SIDM2 actually drives it through)
- `tools/RETRODEBUGGER_ANALYSIS.md` — deep source-code architecture analysis of the tool itself
- `docs/players/BLACKBIRD.md` — the first real usage of this MCP tool set in SIDM2, tracing
  Fargo.sid's note-stream decompressor
- `docs/players/PLAYBOOK.md` — the general cross-player RE method this guide's technique feeds into
