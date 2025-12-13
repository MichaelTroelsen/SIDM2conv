# Phase 6: Pointer Patching Analysis

**Date**: 2025-12-13
**Status**: Fundamental architectural issue discovered
**Conclusion**: Data injection alone is insufficient - requires pointer patching or redesign

---

## Executive Summary

Attempted to fix the Laxity driver by adjusting the orderlist injection address from $1900 to $1700 (where the relocated player expects data). However, this made the situation **worse** - accuracy dropped from 0.18% to 0.12%, and register writes dropped from 3,023 to only **25**.

**Root Cause**: The relocated Laxity player contains embedded data with hardcoded internal pointers. Simply injecting new music data at any location doesn't work because the player's code doesn't know to look there.

---

## What We Tried

### Attempt 1: Inject at $1900 (Original Plan)
**File**: `sidm2/sf2_writer.py` line 1358
```python
orderlist_start = 0x1900
```

**Result**: 0.18% accuracy, 3,023 register writes
- Player uses embedded default data
- Injected data at $1900 is never read

### Attempt 2: Inject at $1700 (Relocated Location)
**File**: `sidm2/sf2_writer.py` line 1359
```python
orderlist_start = 0x1700  # Where relocated player expects data
```

**Result**: 0.12% accuracy, **25** register writes (98% WORSE!)
- Overwrote critical SF2 header data at $1700
- Destroyed addresses like $0E00 (player start), $0EA1 (play routine)
- Player can barely execute

### Attempt 3: Full Block Write
**File**: `sidm2/sf2_writer.py` lines 1379-1381
```python
# Initialize full 256-byte block with $00
for i in range(256):
    self.output[track_offset + i] = 0x00
```

**Purpose**: Ensure we fully overwrite template data, not just partial
**Result**: Didn't help - still 0.12% accuracy because we're overwriting wrong area

---

## Key Discoveries

### 1. Original Orderlist Locations
**Finding**: Stinsens SID has orderlists at $1898, not $1900!

```
Original Laxity SID (load=$1000):
  Track 1 orderlist: $1898 (16 entries)
  Track 2 orderlist: $1998 (likely)
  Track 3 orderlist: $1A98 (likely)

After -$0200 relocation:
  Track 1: $1698
  Track 2: $1798
  Track 3: $1898
```

**Implication**: The relocated player expects orderlists around $1698-$1898, not $1700-$1900.

### 2. SF2 Headers at $1700
**Finding**: The driver template has critical data at $1700:

```
$1700: 01                      Block 01 (Descriptor)
$1701: "Laxity NewPlayer v21"  ASCII name
$171E: 02 7E 0D                Block 02 start
$1720: 00 0E                   $0E00 - player start address
$1722: A1 0E                   $0EA1 - play routine address
$1724: 84 0D                   $0D84 - stop routine address
$1740: 00 19 00 1A 00 1C ...   More critical addresses
```

**Implication**: Overwriting $1700 with orderlists destroys addresses the player/wrapper needs!

### 3. Player Architecture
**Finding**: The relocated Laxity player is a complete, self-contained unit:

```
$0E00-$16FF: Relocated Player (2,304 bytes)
  - Player CODE (init, play routines)
  - Embedded DATA from reference SID:
    * Orderlists at $1698-$1898
    * Sequences after orderlists
    * Tables (instruments, wave, pulse, filter)
  - Internal POINTERS referencing embedded data
```

**Implication**: The player's code has hardcoded pointers to specific memory addresses where IT expects to find data. These pointers were adjusted during relocation (-$0200), but they still point to the embedded data locations, not any new location we inject data at.

---

## Why Data Injection Fails

### The Problem
```
1. We load template with relocated player
   Player code at $0E00 contains pointers like:
   - LDA $1698  ; Load from track 1 orderlist
   - LDA $1798  ; Load from track 2 orderlist

2. We inject new orderlists at $1700
   New data is at $1700-$1900

3. Player executes
   Player code still does: LDA $1698
   This reads from EMBEDDED data, not injected data!
```

### Example Scenario
```assembly
; Player code at $0E50 (hypothetical)
LDA $1698,X    ; Read orderlist entry (Track 1)
              ; This address was relocated from $1898
              ; Points to EMBEDDED orderlist from reference SID

; What we need:
LDA $1700,X    ; Read from NEW injected orderlist
              ; But we can't change this without patching!
```

---

## Why $1700 Injection Was Worse

When we injected at $1700, we overwrote SF2 header blocks that contain:
- Player entry point addresses ($0E00, $0EA1, $0D84)
- Table addresses
- Music data pointers

The SF2 wrapper or player initialization might read these addresses. By overwriting them with $00 (orderlist data), we broke the initialization, causing the player to barely execute (only 25 register writes vs 14,595).

---

## Architectural Analysis

### What We Have
```
Memory Layout:
$0D7E: SF2 Wrapper
       - init: JSR relocated_laxity_init ($0E00)
       - play: JSR relocated_laxity_play ($0EA1)

$0E00: Relocated Laxity Player
       - CODE with embedded pointers
       - Pointers: LDA $1698, LDA $1798, etc.
       - These point to embedded data

$1698: Embedded orderlists (from reference SID)
$1700: SF2 Headers (critical addresses)
$1900: Injected orderlists (IGNORED by player!)
```

### What We Need
```
Option A: Patch Pointers
  - Find all LDA/STA $16XX-$18XX in player code
  - Change to LDA/STA $17XX-$19XX (or wherever we put new data)
  - Requires disassembly + pattern matching

Option B: Extract Code Only
  - Extract ONLY player code (not embedded data)
  - Initialize zero-page pointers to new data location
  - Requires understanding player's ZP usage

Option C: Runtime Initialization
  - Modify wrapper to set up pointers before calling player
  - Write orderlist addresses to player's pointer locations
  - Requires knowing which memory locations hold pointers
```

---

## Pointer Finding Attempts

### Search Results
We searched for orderlist pointer patterns in the driver:
- Pattern: 3 consecutive addresses spaced $100 apart
- Expected: $1700, $1800, $1900 or $1698, $1798, $1898
- **Result**: NO MATCHES FOUND

**Interpretation**: The pointers are NOT stored as a simple table. They are:
1. Scattered throughout player code as instruction operands
2. Part of self-modifying code
3. Calculated at runtime
4. Stored in zero-page and modified dynamically

### Evidence
```
Search for: addr2 = addr1 + $100, addr3 = addr2 + $100
In range: $1600-$1A00
Found: NOTHING
```

This means we can't just patch a pointer table. We need to either:
1. Disassemble and find ALL references
2. Use runtime setup
3. Redesign the driver architecture

---

## Memory Layout Conflict

### The Collision
```
$0D7E-$0DFF: SF2 Wrapper (130 bytes)
$0E00-$16FF: Relocated Player (2,304 bytes)
             Includes embedded data at:
             - $1698-$1898: Original orderlists
             - Tables, sequences

$1700-$18FF: SF2 Headers (512 bytes)
             Contains critical addresses!
             BLOCKS where we might want to put data

$1900+:      Free space for new data
             But player doesn't look here!
```

### The Dilemma
- Player expects data at $1698-$1898 (embedded locations)
- SF2 headers are at $1700-$18FF (overlap!)
- We can't put data at $1698 (would overwrite player code end)
- We can't put data at $1700 (would overwrite headers)
- We can't put data at $1900 (player won't find it)

**No good location exists without pointer patching!**

---

## Solutions Comparison

### Option A: Binary Pointer Patching
**Approach**: Find and patch address operands in player code

**Process**:
1. Disassemble player with SIDwinder
2. Find all `LDA/STA/LDX/LDY $16XX-$18XX` instructions
3. Calculate which ones are orderlist references
4. Patch operands to point to new location ($1900+)
5. Reassemble or binary patch

**Pros**:
- Uses existing player code (proven to work)
- No runtime overhead
- Once patched, works like native

**Cons**:
- Requires accurate disassembly
- Must distinguish data refs from code refs
- Self-modifying code makes this complex
- Fragile (breaks if player structure changes)

**Complexity**: High
**Time**: 12-24 hours
**Success Probability**: 40%

### Option B: Code-Only Extraction
**Approach**: Extract player CODE without embedded data

**Process**:
1. Identify exact boundary where player code ends and data begins
2. Extract only code portion for relocation
3. Set up zero-page pointers to new data at init time
4. Requires understanding Laxity's ZP usage ($F0-$FF)

**Pros**:
- Clean separation of code and data
- No embedded data conflicts
- Flexible data placement

**Cons**:
- Hard to find exact code/data boundary
- Must understand ZP pointer structure
- Requires player initialization knowledge
- More work than patching

**Complexity**: Very High
**Time**: 24-40 hours
**Success Probability**: 30%

### Option C: Hybrid NP20 Driver
**Approach**: Give up on Laxity driver, improve NP20 conversion

**Process**:
1. Revert to using NP20 driver for Laxity files
2. Improve table extraction and conversion
3. Focus on optimizing NP20 format translation
4. Accept 1-8% accuracy as baseline, aim for 10-20%

**Pros**:
- NP20 driver already works
- Can iterate on conversion quality
- Lower complexity
- Proven architecture

**Cons**:
- Never achieves 70-90% accuracy goal
- Still has format conversion losses
- Less satisfying outcome

**Complexity**: Low
**Time**: 8-12 hours
**Success Probability**: 90%

### Option D: Manual Pointer Analysis (NEW - RECOMMENDED)
**Approach**: Use runtime analysis to find pointer locations

**Process**:
1. Run original Laxity SID in debugger/tracer
2. Watch which memory locations are READ during playback
3. Identify access patterns to $1698-$1898 (orderlists)
4. Find which CODE addresses perform those reads
5. Disassemble those specific addresses to find pointer locations
6. Patch just those locations

**Pros**:
- Data-driven approach
- Only patches what's actually used
- Can verify with debugging
- More reliable than blind searching

**Cons**:
- Requires debugging tools (VICE monitor or RetroDebugger)
- Still complex but more focused
- Need to understand 6502 addressing modes

**Complexity**: Medium-High
**Time**: 8-16 hours
**Success Probability**: 60%

---

## Recommendation

### Short Term (Next Session)
**Use Option D: Manual Pointer Analysis**

1. Use VICE monitor or RetroDebugger to trace original Laxity SID
2. Log all reads from $1898-$1A98 range (orderlists)
3. Identify which instructions access orderlists
4. Disassemble relocated player at those offsets (-$0200)
5. Patch the 3-6 key pointer locations
6. Test with one file

### Medium Term
**If Option D works**:
- Document pointer locations
- Automate patching in `_inject_laxity_music_data()`
- Test with all 4 Laxity files
- Measure accuracy improvement

**If Option D fails**:
- Fall back to Option C (Hybrid NP20)
- Document learnings
- Close Laxity driver as experimental

### Long Term
Consider complete redesign:
- Build SF2 driver from scratch that natively supports Laxity format
- Or partner with SF2 editor developer for proper Laxity integration

---

## Lessons Learned

### What Worked
1. ✅ Relocation engine successfully adjusted 373 address references
2. ✅ SF2 wrapper integration works correctly
3. ✅ Driver loads and initializes without crashes
4. ✅ Infrastructure and tooling are solid

### What Didn't Work
1. ❌ Assumption that relocated player would use injected data
2. ❌ Simple memory address calculations without understanding pointer architecture
3. ❌ Trying to find pointers by pattern matching
4. ❌ Injecting data without verifying player actually reads it

### Key Insights
1. **Relocation ≠ Repointing**: Relocating code adjusts its internal references, but doesn't make it look for data in new locations
2. **Embedded vs External Data**: A player with embedded data has pointers baked into its code
3. **Headers Have Addresses**: SF2 headers aren't just metadata - they contain critical runtime addresses
4. **Testing is Essential**: We should have tested after each change, not batched them

---

## Technical Debt

### Current State
- Laxity driver exists but doesn't work (0.12% accuracy)
- Code quality is good but architecture is flawed
- Documentation is comprehensive
- 3 commits worth of investigation

### Cleanup Needed
1. Either fix pointers OR revert to NP20
2. Update PHASE6_STATUS.md with new findings
3. Document final decision
4. Remove non-functional code if abandoning Laxity driver

---

## Next Steps

### Option 1: Continue (Use Manual Pointer Analysis)
```bash
# 1. Extract player binary
xxd drivers/laxity/sf2driver_laxity_00.prg > player.hex

# 2. Run original SID in VICE with tracing
x64 -logfile trace.log test_laxity_pipeline/Stinsens_Last_Night_of_89.sid

# 3. In VICE monitor, set watchpoints
watch load $1898
watch load $1998
watch load $1A98

# 4. Run and collect access addresses
g  # go
[watch triggers show which PC accessed orderlists]

# 5. Disassemble those PC addresses in relocated player
# 6. Patch the operands to point to $1900/$1A00/$1B00
# 7. Test
```

### Option 2: Abandon (Revert to NP20)
```python
# Change complete_pipeline_with_validation.py line 170
['python', 'scripts/sid_to_sf2.py', ..., '--driver', 'np20', ...]

# Focus on improving NP20 table conversion quality
# Accept 1-8% as baseline, aim for 10-20% with optimizations
```

---

## Conclusion

The Laxity driver implementation revealed a fundamental architectural challenge: **you cannot simply inject data into a relocated player that has embedded data with hardcoded pointers**.

The player's code contains specific memory addresses where it expects to find orderlists, sequences, and tables. When we relocate the code, those addresses are adjusted, but they still point to the player's embedded data, not to any new data we inject.

**Three paths forward**:
1. **Patch pointers** (medium-high complexity, 60% success)
2. **Extract code only** (very high complexity, 30% success)
3. **Use NP20 driver** (low complexity, 90% success, lower accuracy)

**Recommendation**: Try manual pointer analysis for 1-2 sessions. If unsuccessful, revert to NP20 and document Laxity driver as experimental/incomplete.

**Time invested**: ~12 hours across Phases 5-6
**Outcome**: Valuable learning about player architecture and relocation limits
**Status**: Needs decision on next steps

---

**Last Updated**: 2025-12-13 23:00
**Commit**: 0670669
**Accuracy**: 0.12% (25 register writes vs 14,595 expected)
