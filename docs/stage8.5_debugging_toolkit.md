# Stage 8.5 debugging toolkit

Tools for chasing the load-addr-dependent F10-load crash in SF2II
([Stage 8.5](../README.md), commit `e3efadc`). All three crash classes
share a Heisenbug-style heap-perturbation problem: any in-process
diagnostic (logging, debugger spawn) shifts the heap layout enough to
mask the OOB read.

## Files

- `appverifier-setup.bat` — one-time setup script. **Run as Administrator**.
  Configures `appverif.exe` to enable Heaps + Memory + Locks checks on
  `SIDFactoryII.exe`, plus enables WER LocalDumps with `DumpType=2` (full
  dumps) so every crash captures full memory + stack.
- `pyscript/sf2_debug_inspect_v2.py` — extended Python debugger
  (DEBUG_PROCESS spawn / DebugActiveProcess attach / hardware
  write-watchpoint via Dr0-Dr3 / dbghelp stack walks).

## Workflow

### Quick path: AppVerifier + WER LocalDumps

1. **One-time setup (admin)**:
   ```cmd
   ; Right-click appverifier-setup.bat → "Run as administrator"
   ```

2. **Reproduce the crash with instrumentation**:
   ```bat
   py -3 pyscript/sf2_pass_rate.py bin/_action.sf2 5
   ```
   Each CRASH trial now writes a full minidump under
   `%LOCALAPPDATA%\CrashDumps\SIDFactoryII.exe.<pid>.dmp`. AppVerifier
   halts the process at the **writing** instruction (not 5 functions
   later when the corrupted pointer is dereferenced), so the dump's PC
   points directly at the bug.

3. **Inspect the latest dump**:
   ```bat
   py -3 pyscript/sf2_crash_analyze.py
   ```
   Prints the crash PC, RVA in `SIDFactoryII.exe`, and disassembly
   around the crash.

4. **Disable when done** — AppVerifier slows SF2II 2-5x:
   ```cmd
   appverif.exe /n SIDFactoryII.exe
   ```

### Hardware watchpoint path (no admin)

Use this if AppVerifier is unavailable or you want to track a *specific*
address that gets corrupted (e.g., the high byte of a `m_MainTextField`
pointer).

1. **Find the target address**: under the patched x86 SF2II at
   `C:\Users\mit\AppData\Local\Temp\sf2-src\sidfactory2\Release\`, the
   per-component bracket logging dumps `m_MainTextField` at every
   iteration. Pick a corruption-firing run and note the `&m_MainTextField`
   storage address (different from the *value* it holds — the storage
   address is the byte that gets stray-written).

2. **Set the watchpoint and run**:
   ```bat
   py -3 pyscript/sf2_debug_inspect_v2.py --watch 0x000001fffe004248 bin/_action.sf2
   ```
   The debugger spawns SF2II under `DEBUG_PROCESS`, drives F10-load,
   and after 3 seconds installs a hardware write-watchpoint on every
   thread of the process. When any thread writes the watched bytes,
   the CPU traps; v2 prints PC, register file, code at PC, and
   dbghelp-resolved stack walk.

   **Catch**: HW watchpoints are per-thread. New threads created
   *after* watchpoint installation get empty Dr0-Dr3 and won't trap.
   The 3-second deferral is intended to land after F10-load has
   spawned its rendering threads. Tune via the `time.sleep(3.0)` in
   `deferred_install`.

3. **Attach to a running SF2II instead of spawning**:
   ```bat
   py -3 pyscript/sf2_debug_inspect_v2.py --attach <pid> --watch 0x... bin/_action.sf2
   ```
   `DebugActiveProcess` mode skips DEBUG_PROCESS heap-fill behaviour;
   slightly less perturbative than spawn mode (bug may fire that
   doesn't fire under spawn).

## DR layout reference (x86-64)

```
DR0..DR3   four 64-bit address registers (one watchpoint each)
DR6        status register (bits 0-3 indicate which DRn fired)
DR7        control register, per-DRn 4-bit groups:
   bit 0  L0 = local enable for DR0
   bit 16-17  R/W on DR0:
       00 = exec    01 = write    10 = io    11 = read|write
   bit 18-19  LEN on DR0:
       00 = 1B      01 = 2B       10 = 8B    11 = 4B
   (bits 2-7 / 20-31 same pattern for DR1, DR2, DR3)
```

`sf2_debug_inspect_v2.py:make_dr7()` builds these bit-fields.

## Why these two paths together

AppVerifier catches the *first* OOB byte access — every byte read or
write past an allocation boundary halts the process at the offending
instruction. That nails down WHERE the bug fires in SF2II's source.

HW watchpoints help when AppVerifier ISN'T available (no admin) and
you want to track a specific corruption target post-mortem. You give
it the address that you've observed gets corrupted (e.g., from the
patched binary's bracket logs), and any write to that address — from
any function — triggers the trap. The stack walk then identifies the
calling chain.

The full Stage 8.5 background — including the 5 different "fix
attempts that didn't work" and the file-class breakdown — lives in
the project memory at `~/.claude/projects/.../memory/stage8.5-load-addr-crash.md`.
