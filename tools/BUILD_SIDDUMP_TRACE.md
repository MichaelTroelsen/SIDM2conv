# Building Modified Siddump with Memory Tracing

## What This Does

Creates a modified version of siddump that logs memory reads during playback. This will help us find where sequence data is stored by showing which memory addresses the player reads from.

## Changes Made

1. **Added `-trace` option** - Enables memory read logging
2. **Logs reads from $1800-$1C00** - Music data region
3. **First 10 frames only** - Reduces log size
4. **Output format**: `Frame PC MemAddr Value`

## Build Instructions

### Option 1: Manual Patching (Windows)

1. **Backup original files**:
   ```batch
   copy siddump.c siddump.c.orig
   copy cpu.c cpu.c.orig
   copy cpu.h cpu.h.orig
   ```

2. **Apply changes**:

   **In `cpu.c`** - Add after includes:
   ```c
   #include "cpu.h"

   extern int trace_enabled;
   extern int trace_frame;
   extern FILE *trace_log;
   ```

   **In `cpu.c`** - Replace `#define MEM(address) (mem[address])` with:
   ```c
   static inline unsigned char mem_read_tracked(unsigned short address)
   {
     unsigned char value = mem[address];

     if (trace_enabled && trace_log && trace_frame >= 0 && trace_frame < 10)
     {
       if (address >= 0x1800 && address < 0x1C00)
       {
         extern unsigned short pc;
         fprintf(trace_log, "F%02d PC:%04X -> [%04X]=%02X\n",
                 trace_frame, pc, address, value);
         fflush(trace_log);
       }
     }

     return value;
   }

   #define MEM(address) mem_read_tracked(address)
   ```

   **In `cpu.h`** - Add after existing externs:
   ```c
   extern int trace_enabled;
   extern int trace_frame;
   extern FILE *trace_log;
   ```

   **In `siddump.c`** - Add after includes:
   ```c
   int trace_enabled = 0;
   int trace_frame = -1;
   FILE *trace_log = NULL;
   ```

   **In `siddump.c`** - Add in argument parsing (around line 150):
   ```c
   if (!strcmp(argv[c], "-trace"))
   {
     trace_log = fopen("siddump_trace.txt", "w");
     trace_enabled = 1;
   }
   ```

   **In `siddump.c`** - In playback loop, set frame number:
   ```c
   trace_frame = frames;  // Before cpuexecute()
   ```

   **In `siddump.c`** - At end of main():
   ```c
   if (trace_log) fclose(trace_log);
   ```

3. **Compile**:
   ```batch
   gcc -o siddump_trace.exe siddump.c cpu.c -lm -O2
   ```

### Option 2: Using Patch File (if patch.exe available)

```batch
patch -p0 < siddump_trace.patch
gcc -o siddump_trace.exe siddump.c cpu.c -lm -O2
```

### Option 3: Automated Script

Run the provided `build_siddump_trace.bat`:
```batch
build_siddump_trace.bat
```

## Usage

```batch
siddump_trace.exe -trace SID/Stinsens_Last_Night_of_89.sid -t1
```

This will:
1. Play the first 50 frames
2. Log memory reads to `siddump_trace.txt`
3. Focus on addresses $1800-$1C00 (music data region)

## Output Format

```
F00 PC:1006 -> [1A70]=A0
F00 PC:1008 -> [1A71]=0E
F00 PC:100A -> [1A72]=0F
F01 PC:1010 -> [1A73]=0F
...
```

Format: `Frame PC:address -> [memory_addr]=value`

## Finding Sequence Data

1. Run with trace: `siddump_trace.exe -trace SID/Stinsens_Last_Night_of_89.sid -t1`

2. Analyze `siddump_trace.txt`:
   - Look for **repeated 3-byte patterns** (inst, cmd, note)
   - Look for **sequential addresses** being read
   - Note which addresses are accessed most frequently

3. Memory addresses accessed = where sequences are stored!

## Expected Results

You should see:
- **Sequence data reads**: 3 consecutive addresses
- **Frequent access**: Same region accessed every frame
- **Pattern**: Address increments by 3 each step

Example:
```
F00 PC:1080 -> [1A70]=00   ; Instrument
F00 PC:1082 -> [1A71]=04   ; Command
F00 PC:1084 -> [1A72]=2C   ; Note
F01 PC:1080 -> [1A73]=01   ; Next instrument
F01 PC:1082 -> [1A74]=00   ; Next command
F01 PC:1084 -> [1A75]=30   ; Next note
```

This tells us sequences start at $1A70!

## Troubleshooting

**Compilation errors**:
- Make sure you're in the `tools/` directory
- Ensure gcc is installed (MinGW or similar)

**No output file**:
- Check that `-trace` option is specified
- File will be created in current directory

**Empty trace file**:
- Check that SID file plays correctly first
- Try increasing address range (change 0x1800-0x1C00)

**Too much output**:
- Reduce frames: `-t1` (default ~50 frames)
- Narrow address range in code

## Next Steps

Once you have the trace:
1. Identify sequence start addresses
2. Confirm with pattern analysis
3. Extract sequences using correct addresses
4. Complete the conversion!
