# Simple Siddump Memory Trace - Manual Method

## Problem with Automated Approach

The MEM() macro is used for both reads and writes. Replacing it breaks write operations (ASL, DEC, etc.). Instead, we'll add explicit logging in the main playback loop.

## Simple Manual Modification

### Step 1: Add to siddump.c (after includes)

```c
FILE *trace_log = NULL;
int trace_enabled = 0;
```

### Step 2: Add in main() argument parsing

```c
if (!strcmp(argv[c], "-trace"))
{
  trace_log = fopen("siddump_trace.txt", "w");
  trace_enabled = 1;
}
```

### Step 3: Add logging in playback loop (after each cpuexecute call)

```c
// After: cpuexecute(playaddress);
if (trace_enabled && trace_log && frames < 10)
{
  // Log which memory regions were recently accessed
  // Scan the sequence data region
  fprintf(trace_log, "Frame %d:\n", frames);

  // Check orderlists
  fprintf(trace_log, "  Orderlist V0 [$1AEE]: %02X %02X %02X\n",
          mem[0x1AEE], mem[0x1AEF], mem[0x1AF0]);
  fprintf(trace_log, "  Orderlist V1 [$1B1A]: %02X %02X %02X\n",
          mem[0x1B1A], mem[0x1B1B], mem[0x1B1C]);
  fprintf(trace_log, "  Orderlist V2 [$1B31]: %02X %02X %02X\n",
          mem[0x1B31], mem[0x1B32], mem[0x1B33]);

  // Check potential sequence locations
  fprintf(trace_log, "  Data [$1A70]: %02X %02X %02X\n",
          mem[0x1A70], mem[0x1A71], mem[0x1A72]);
  fprintf(trace_log, "  Data [$1A9B]: %02X %02X %02X\n",
          mem[0x1A9B], mem[0x1A9C], mem[0x1A9D]);

  fflush(trace_log);
}
```

### Step 4: Cleanup (before return 0)

```c
if (trace_log) fclose(trace_log);
```

### Step 5: Compile

```batch
gcc -o siddump_trace.exe siddump.c cpu.c -lm -O2
```

## Even Simpler: Use Python to Analyze Memory

Instead of modifying C code, let's use Python to examine the SID file memory at specific points:

```python
#!/usr/bin/env python3
"""Examine memory regions during playback."""

# Read SID file
with open('SID/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    data = f.read()

# Memory starts at offset 0x7E
def get_mem(addr):
    offset = 0x7E + (addr - 0x1000)
    if offset >= 0 and offset < len(data):
        return data[offset]
    return 0

# Check orderlists
print("Orderlists:")
print(f"  Voice 0 [$1AEE]: {get_mem(0x1AEE):02X} {get_mem(0x1AEF):02X} {get_mem(0x1AF0):02X}")
print(f"  Voice 1 [$1B1A]: {get_mem(0x1B1A):02X} {get_mem(0x1B1B):02X} {get_mem(0x1B1C):02X}")
print(f"  Voice 2 [$1B31]: {get_mem(0x1B31):02X} {get_mem(0x1B32):02X} {get_mem(0x1B33):02X}")

# Check potential sequence locations
print("\nPotential sequences:")
for addr in [0x1A70, 0x1A9B, 0x1AB3, 0x1800, 0x1900, 0x1A00]:
    b1, b2, b3 = get_mem(addr), get_mem(addr+1), get_mem(addr+2)
    print(f"  [{addr:04X}]: {b1:02X} {b2:02X} {b3:02X}")
```

## Best Alternative: Use RetroDebugger

Since modifying siddump is complex, **RetroDebugger** remains the best option:

1. Load SID in RetroDebugger
2. Set read breakpoint on orderlist ($1AEE)
3. Step through execution
4. See where sequence data is actually read from

See: `RETRODEBUGGER_SEQUENCE_INVESTIGATION.md` for complete guide.

## Or: Analyze Existing Siddump Output

We already have siddump output showing notes play correctly. The sequence data MUST be somewhere. Let's use binary analysis:

1. **Known**: Orderlists at $1AEE, $1B1A, $1B31 reference 39 sequences
2. **Known**: Sequences are 3-byte entries
3. **Search**: Find where those 39 sequences are stored

Run: `python find_sequences_by_pattern.py` (to be created)

This searches for contiguous 3-byte pattern data that matches the sequence count and structure.
