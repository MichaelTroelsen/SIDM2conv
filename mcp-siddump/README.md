# mcp-siddump

MCP server exposing SIDM2's `tools/sidm2-sid-trace.exe` (a cycle-accurate
6502/SID emulator built on [zig64](https://github.com/M64GitHub/zig64)) as
SID register-write tracing tools.

Traces every write a running C64 program makes to `$D400-$D418` (the SID
chip's registers), frame by frame — useful for verifying that a
reverse-engineered player reconstruction actually behaves like the real
thing, not just that it assembles.

## Tools

- **`trace_sid(sid_path, frames=50, subtune=0)`** — trace an existing
  `.sid` file. Extracts load address and PSID-declared init/play addresses
  from the header automatically.
- **`trace_prg(prg_path, init_addr, play_addr, frames=50, subtune=0)`** —
  trace a raw `.prg` with explicit entry points (e.g. a hand-assembled
  reconstruction with no SID header).
- **`diff_traces(trace_a, trace_b)`** — compare two traces (the `writes`
  list from either tool above) for an exact register/value/cycle match;
  returns the index of the first divergence if any.

## Setup

```
pip install -r requirements.txt
```

No other dependencies — `sidm2-sid-trace.exe` is a standalone native binary,
already checked into `../tools/`.

## Register with an MCP client

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "sidm2-siddump": {
      "command": "python",
      "args": ["mcp-siddump/server.py"]
    }
  }
}
```

(Already added to this project's own `.mcp.json`.)

## Origin

This wraps exactly the same tracer invocation SIDM2 already uses internally
in `sidm2/zig64_audio_gate.py` (its post-build audio-safety gate) — this
server just exposes it as MCP tools instead of an internal Python function,
so it's usable from any MCP client, not just SIDM2's own conversion
pipeline.
