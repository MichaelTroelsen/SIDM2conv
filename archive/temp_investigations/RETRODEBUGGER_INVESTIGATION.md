# Using RetroDebugger to Find Sequence Locations

## Objective
Find the actual memory addresses where Track 1, Track 2, and Track 3 data starts in the Stinsens SID file.

## Steps to Investigate

### 1. Load the SID File
```
Open: C:\Users\mit\claude\c64server\SIDM2\tools\RetroDebugger v0.64.68\RetroDebugger.exe
Load: C:\Users\mit\claude\c64server\SIDM2\SID\Stinsens_Last_Night_of_89.sid
```

### 2. Check Known Data Locations

From our analysis, we know:
- **Load address**: $1000
- **Wave table**: Found in file
- **Pulse table**: Found in file
- **Filter table**: Found in file
- **Instruments**: Found in file
- **Tempo table**: Ends at approximately $1A9A (file offset 0x0A9A)

### 3. Look for Sequence Pointers

The disassembly mentions sequence pointers at **$199F-$19A5**:
- $199F-$19A0: Voice 1 sequence pointer
- $19A1-$19A2: Voice 2 sequence pointer
- $19A3-$19A4: Voice 3 sequence pointer

**In RetroDebugger:**
1. Open memory view
2. Go to address $199F
3. Read the 6 bytes as three 16-bit little-endian pointers
4. Note what addresses they point to

Example: If bytes are `9F 00 E2 7F 00 2C`, then:
- Voice 1 pointer = $009F
- Voice 2 pointer = $7FE2
- Voice 3 pointer = $2C00

### 4. Check If Pointers Are Relative

These pointers might be:
- **Absolute addresses** (point directly to memory location)
- **Relative offsets** (need to add to a base address)
- **Page offsets** (high byte = page, low byte = offset)

**Test:**
1. Go to the address indicated by Voice 1 pointer
2. Check if the data there looks like sequence data:
   - 3-byte entries: [Instrument] [Command] [Note]
   - Instrument: 0x00-0x1F or 0x80+
   - Note: 0x00-0x5F or 0x7E/0x7F/0x80 markers

### 5. Find Actual Sequence Start Addresses

If the pointers don't work, look manually:

**Search for sequence-like data AFTER the known tables:**
1. After Wave/Pulse/Filter/Instrument tables
2. Before Tempo table (around $1A00-$1A9A)
3. Look for patterns of 3-byte entries

**Sequence data characteristics:**
- Repeating patterns of 3 bytes
- Instrument bytes (0x00-0x1F range)
- Note bytes (0x00-0x5F or special markers)
- Gate markers: 0x7E (+++), 0x80 (---)
- End markers: 0x7F

### 6. Verify With Orderlists

We know the orderlists reference sequences:
- Voice 0 uses: 01, 02, 03, 04, 05, 0E, 0F, 11, 13, 14, 15, 1B, 1C, 1F, 20
- Voice 1 uses: 00, 06, 07, 12, 16, 17, 18, 1D, 21, 25
- Voice 2 uses: 08, 09, 0A, 0B, 0C, 0D, 10, 19, 1A, 1E, 22, 23, 24, 26

If the pointers work correctly, we should be able to:
1. Index into the sequence data using these numbers
2. Find the actual sequence for each number
3. Verify it contains musical data

## What We Need

Please use RetroDebugger to find:

1. **What are the 6 bytes at memory address $199F-$19A4?**
   (This confirms/corrects the pointer values)

2. **What's at the memory address those pointers point to?**
   (Does it look like sequence data?)

3. **Where does sequence data actually start in memory?**
   (Manual search if pointers don't work)

4. **For each voice, what memory address does the sequence data begin?**
   - Track 1 (Voice 0) starts at: $____
   - Track 2 (Voice 1) starts at: $____
   - Track 3 (Voice 2) starts at: $____

## Expected Memory Layout

```
$1000-$1XXX: Player code
$1XXX-$1XXX: Wave table
$1XXX-$1XXX: Pulse table
$1XXX-$1XXX: Filter table
$1XXX-$1XXX: Instrument table
$1XXX-$199E: Other data
$199F-$19A4: Sequence pointers (?)
$1XXX-$1XXX: Track 1 sequences
$1XXX-$1XXX: Track 2 sequences
$1XXX-$1XXX: Track 3 sequences
$1A9A: Tempo table
$1AEE: Voice 0 orderlist
$1B1A: Voice 1 orderlist
$1B31: Voice 2 orderlist
```

## Alternative Approach

If the above doesn't work, we can:
1. Set a breakpoint when the player reads sequence data
2. Watch which memory addresses it accesses
3. Trace back to find the start of each track
