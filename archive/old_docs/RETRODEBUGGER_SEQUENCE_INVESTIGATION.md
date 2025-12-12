# RetroDebugger Investigation - Finding Sequence Data Locations

## Problem Statement

The sequence extraction from SF2-packed Stinsen SID file is incorrect. We need to find the actual memory addresses where the player reads sequence data during playback.

## What We Know

### File Structure
- **File**: `SID/Stinsens_Last_Night_of_89.sid`
- **Size**: 6,201 bytes
- **Load address**: $1000
- **Init address**: $1000
- **Play address**: $1006
- **PSID header**: 0x7E bytes

### Orderlists (Confirmed Correct)
- Voice 0 orderlist at: File 0x0AEE (Memory $1AEE)
- Voice 1 orderlist at: File 0x0B1A (Memory $1B1A)
- Voice 2 orderlist at: File 0x0B31 (Memory $1B31)

### What Orderlists Reference
- Voice 0 uses sequences: 01, 02, 03, 04, 05, 0E, 0F, 11, 13, 14, 15, 1B, 1C, 1F, 20
- Voice 1 uses sequences: 00, 06, 07, 12, 16, 17, 18, 1D, 21, 25
- Voice 2 uses sequences: 08, 09, 0A, 0B, 0C, 0D, 10, 19, 1A, 1E, 22, 23, 24, 26

Total: 39 unique sequence numbers (0x00-0x26)

## What We Need to Find

1. **Where is the sequence pointer table?**
   - This table maps sequence numbers (0x00-0x26) to memory addresses
   - Could be 39 × 2 = 78 bytes of pointers
   - Or could use split format (low bytes, then high bytes)

2. **Where is the actual sequence data?**
   - Sequence data is 3 bytes per entry: [Instrument] [Command] [Note]
   - Likely stored contiguously with END markers (7F) between sequences

## Investigation Steps with RetroDebugger

### Step 1: Load the SID File

1. Open RetroDebugger: `tools\RetroDebugger v 0.64.68\RetroDebugger.exe`
2. File → Load SID → `SID/Stinsens_Last_Night_of_89.sid`
3. The file should load and start playing

### Step 2: Find Where Player Reads Orderlist

1. Open Memory View (View → Memory)
2. Go to orderlist address: $1AEE (Voice 0)
3. Set a **read breakpoint** at $1AEE
4. Restart playback (Debug → Restart)
5. When breakpoint hits, examine the code

**What to look for:**
- The player code that reads from the orderlist
- This code should also read from a sequence pointer table nearby
- Or it might calculate sequence addresses dynamically

### Step 3: Trace Sequence Pointer Reads

Once you find the orderlist reading code:

1. Look for subsequent reads after reading an orderlist entry
2. The player likely does:
   ```
   - Read sequence number from orderlist
   - Use it as index to read from pointer table
   - Jump to that address to read sequence data
   ```

3. Set breakpoints on any suspicious pointer table locations
4. Watch what addresses get dereferenced

### Step 4: Alternative - Watch Zero Page Pointers

Many 6502 players use zero-page pointers ($FC/$FD is common):

1. Open Memory View → Zero Page ($00-$FF)
2. Watch addresses $FC and $FD during playback
3. When these change, they might point to current sequence
4. Note what values they get set to

### Step 5: Manual Memory Search

If breakpoints don't work, manually search memory:

1. Look for regions that contain 3-byte patterns:
   - First byte: 0x00-0x1F (instrument number)
   - Second byte: 0x00-0xFF (command)
   - Third byte: 0x00-0x5F or special markers (note)

2. **Key addresses to check** (from disassembly):
   - $199F-$19A5 (mentioned in one disassembly)
   - $1A1C-$1A21 (split pointer format - tried, seems wrong)
   - Anywhere between $1800-$1AEE

3. Look for END markers (0x7F) which separate sequences

### Step 6: Validate Your Findings

Once you find a potential sequence location:

1. Check if it contains data matching orderlist references
2. Sequence 0x00 should be first, 0x01 second, etc.
3. Cross-reference with orderlists:
   - If Voice 0 uses sequence 0x0E, jump to that location
   - Verify it contains musical data (notes, instruments)

## Information Needed

Please provide the following from RetroDebugger:

1. **Sequence pointer table location:**
   - Memory address: $____
   - Format: (Little-endian pairs? Split format?)
   - First 10 bytes (hex): __ __ __ __ __ __ __ __ __ __

2. **Actual sequence data start addresses:**
   - Sequence 0x00 starts at: $____
   - Sequence 0x01 starts at: $____
   - Sequence 0x02 starts at: $____
   - (Or address of contiguous sequence data block)

3. **How sequence numbers map to addresses:**
   - Direct pointers?
   - Calculated offsets?
   - Other method?

## Quick Test

If you find what you think is sequence 0x00:

1. Voice 1 orderlist starts with sequence 0x00
2. Load Voice 1 orderlist at $1B1A
3. Read first byte: should be A0 (transpose) or 00 (sequence number)
4. If it's 00, the next address accessed should be sequence 0x00

## Expected Output Format

Please provide:

```
SEQUENCE LOCATIONS FOUND:

Pointer table at: $____ (file offset 0x____)
Format: [description]

Pointer table contents (first 20 bytes):
00: __ __ __ __ __ __ __ __ __ __ __ __ __ __ __ __ __ __ __ __

Sequence data regions:
- Sequence 0x00 at: $____ (file offset 0x____)
- Sequence 0x01 at: $____ (file offset 0x____)
OR
- All sequences start at: $____ (contiguous block)

Sample data from sequence 0x00 (first 9 bytes):
  [__] [__] [__]  ; Entry 1: Inst, Cmd, Note
  [__] [__] [__]  ; Entry 2
  [__] [__] [__]  ; Entry 3
```

## File Offset Conversion

To convert memory addresses to file offsets:

```python
file_offset = 0x7E + (memory_addr - 0x1000)
```

Example:
- Memory $1AEE → File offset 0x0AEE
- Memory $1B1A → File offset 0x0B1A
