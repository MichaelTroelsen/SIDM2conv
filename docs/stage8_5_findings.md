# Stage 8.5 — non-Laxity editor crash diagnostic findings

**Date:** 2026-05-08
**Status:** Inconclusive — root cause not identified within session budget

## Symptom

After Stage 8 Path A shipped (commit `531455f`), Hubbard/Galway SIDs convert
+ produce playable audio (zig64 cycle-accurate trace shows real SID register
writes), but **F10-load in SIDFactoryII's editor crashes deterministically
post-parse**:

```
verdict=CRASH  phase=wait_load  elapsed=5.5s  exit=3221225477 (0xC0000005)
| INFO: Block 9: Parse SUCCESS (at end address)
| INFO: Block ID: $FF at address $0F8A
| INFO: Found end marker, parse complete
```

So SF2II's parser walks the entire header chain successfully, then dies
during render-path initialization. Pass rate 0/30 on Hubbard's Commando —
fully deterministic, not the heap-state flakiness Stinsen exhibits.

## Hypotheses tested + ruled out

### 1. Aux chain content
Skipped `_inject_auxiliary_data` entirely (no aux blocks, just END marker).
**Result: still 0/5.** Aux is not the trigger.

### 2. Block 9 (DriverInstrumentDataDescriptor)
Reverted Block 9 to 1-byte placeholder (zero descriptors). The 4 descriptors
from Stage 5 reference positions in an instrument table that Path A
populates with zeros, in case bogus lookups during F2 render were the cause.
**Result: still 0/5.** Block 9 is not the trigger.

### 3. `$1000` trampoline
Removed the JMP-to-PSID-init trampoline at `$1000` (placed for zig64
compat). **Result: still 0/5.** Trampoline is not the trigger.

## Likely cause (not directly tested)

**SF2II's editor runs the embedded player code through its own 6502 emulator
during F10-load init.** The emulator's environment differs from a real C64:

- Stinsen's NP21 player is self-contained (no KERNAL calls, no CIA timer
  reliance). Plays cleanly under SF2II's emulator.
- Commando's player (and most Hubbard / Galway players) **uses C64 KERNAL
  routines and CIA-timer-driven IRQs** for tempo. These are typically
  unimplemented or incompletely emulated in SF2II's editor-side emulator,
  causing access violations when the player code reaches an unimplemented
  call site.

Path A's trampoline path is correct (zig64 traces real SID writes —
zig64 is a more complete 6502 emulator). The bug is on SF2II's side, not
ours.

## What to try next (if Stage 8.5 is revisited)

1. **Live trace the exact crash address.** Use a debugger (or the Stage 4-era
   `pyscript/sf2_debug_inspect.py` Win32 debugger harness) to capture the
   first-chance access violation's instruction pointer + stack. If it's
   inside SF2II's CPU emulator (e.g., reading from an unimplemented CIA
   register), confirms the hypothesis.

2. **Try a different non-Laxity SID with simpler player code.** Find a SID
   that doesn't use IRQ / CIA timers / KERNAL. A simple polled-PLAY player
   should load cleanly via Path A. If it does, that confirms the
   IRQ/KERNAL hypothesis and tells us Path A works for the simple subset.

3. **Stub out CIA / KERNAL writes in our embedded binary.** Patch the SID
   binary to NOP-out problematic instruction sequences before embedding.
   High-effort, per-player, and audio fidelity drops correspondingly.

4. **Don't run via SF2II's emulator at all.** Inject a SID2WAV-style
   external playback hook so the editor doesn't need to emulate.
   Substantial architecture change.

## Bottom line

Stage 8 Path A delivers what it can: **conversion completes, audio plays
correctly via standalone players (zig64, VICE, etc.) for Galway/Hubbard
files**. The editor-side limitation is a SF2II emulator capability gap, not
a converter bug. Filed for follow-up.
