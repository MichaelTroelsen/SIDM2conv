# Siddump Trace Modification - Status

## Goal

Modify siddump to log memory read addresses during playback, helping us find where sequence data is stored.

## Attempt Made

Created automated patching system:
- ✅ `apply_siddump_trace_patch.py` - Python script to patch files
- ✅ `tools/siddump_trace.patch` - Patch file showing changes
- ✅ `tools/BUILD_SIDDUMP_TRACE.md` - Build instructions
- ✅ `tools/build_siddump_trace.bat` - Automated build script

## Problem Encountered

**Compilation Error**: The MEM() macro is used for both reads AND writes. When replaced with a function call:
- ✅ Reads work fine (returns value)
- ❌ Writes fail (can't assign to function return value)

Operations like ASL, DEC, INC, ROL, ROR need to modify memory in-place:
```c
ASL(MEM(address));  // Needs: mem[addr] = shifted_value
```

This can't work with: `MEM(address) = value` when MEM() is a function.

## Solutions

### Option 1: RetroDebugger (RECOMMENDED)

Use RetroDebugger's built-in memory watch and breakpoints:
- ✅ No compilation needed
- ✅ Visual interface
- ✅ Full debugging features
- ⚠️ Requires manual investigation

**See**: `RETRODEBUGGER_SEQUENCE_INVESTIGATION.md`

### Option 2: Manual Siddump Modification (SIMPLE)

Add explicit logging in main loop instead of wrapping MEM():

```c
// In playback loop, after cpuexecute():
if (trace_enabled && frames < 10)
{
  fprintf(trace_log, "Frame %d: Check addresses...\n", frames);
  // Log specific addresses we want to check
}
```

**See**: `tools/SIDDUMP_TRACE_SIMPLE.md`

### Option 3: Python Memory Analysis

Analyze the SID file directly without runtime tracing:

```python
# Check static memory content at suspected addresses
with open('SID/file.sid', 'rb') as f:
    data = f.read()

# Check various potential sequence locations
# (Already created multiple analysis scripts for this)
```

**See**: `find_sequences_simple.py`, `analyze_all_sequence_candidates.py`

### Option 4: Advanced CPU Emulation

Implement proper read/write separation in CPU emulator:
- Separate MEM_READ() and MEM_WRITE() macros
- Track only reads, not writes
- More complex modification

⚠️ **Time-consuming, not recommended**

## Current Recommendation

**Use RetroDebugger** - it's the most direct path:

1. ✅ Already installed
2. ✅ Built-in memory watching
3. ✅ Breakpoint system
4. ✅ No compilation needed
5. ✅ Visual debugging

The investigation guide is ready: `RETRODEBUGGER_SEQUENCE_INVESTIGATION.md`

## Files Created

| File | Purpose | Status |
|------|---------|--------|
| `apply_siddump_trace_patch.py` | Auto-patch script | ✅ Works |
| `tools/siddump_trace.patch` | Patch definitions | ✅ Created |
| `tools/BUILD_SIDDUMP_TRACE.md` | Build guide | ✅ Complete |
| `tools/build_siddump_trace.bat` | Build script | ✅ Ready |
| `tools/SIDDUMP_TRACE_SIMPLE.md` | Simple alternatives | ✅ Complete |
| `tools/cpu_trace.c` | Modified CPU (partial) | ⚠️ Incomplete |

## Lessons Learned

1. **MEM() macro dual-use** - Used for both reads and writes
2. **C macro limitations** - Can't easily wrap lvalue operations
3. **Alternative approaches needed** - RetroDebugger is simpler
4. **Python analysis sufficient** - Static file analysis may be enough

## Next Steps

1. ✅ Document siddump modification attempt
2. ✅ Provide RetroDebugger guide
3. ⏭️ User uses RetroDebugger OR manual siddump modification
4. ⏭️ Get correct sequence addresses
5. ⏭️ Complete extraction and conversion
