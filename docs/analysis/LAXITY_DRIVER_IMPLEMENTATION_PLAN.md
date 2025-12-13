# Laxity SF2 Driver - Implementation Plan

**Date**: 2025-12-12
**Version**: 1.0
**Status**: Design Phase

---

## Executive Summary

This document outlines a concrete implementation plan for creating a Laxity NewPlayer v21 driver for SID Factory II, enabling direct conversion of Laxity SID files to editable SF2 format with 70-90% expected accuracy.

**Key Insight**: Instead of reverse-engineering SF2's proprietary driver code or building from scratch, we'll **extract and wrap** the Laxity player code itself, creating a hybrid driver that combines Laxity's player with SF2's file format.

---

## Research Findings Summary

### SF2 Driver Binary Analysis

**Common Structure**:
```
Offset    Driver 11                 NP20
--------  -----------------------  -----------------------
$0000-01  7E 0D (load addr)        7E 0D (load addr)
$0002-03  37 13 (header marker)   37 13 (header marker)
$0004-05  01 29 (unknown)          01 18 (unknown)
$0006+    Version string           Version string
          "11.00.00 - T S"         "NP20. 4.00.00"
```

**Key Observations**:
- All drivers load at $0D7E
- Standard header marker: $1337 (little-endian: $37 $13)
- Version string embedded in binary
- Driver code starts around $0280
- Header blocks define table locations

### Laxity Player Structure

**Memory Map** (from Stinsen's Last Night of 89):
```
Address     Content
---------   -------
$1000       Init routine entry
$10A1       Play routine entry
$1000-$19FF Player code (~2.5KB)
$1900-$1A1E Orderlist data
$1A1E-$1A3A Filter table
$1A3B-$1A6A Pulse table
$1A6B-$1ACB Instruments
$1ACB+      Wave tables
```

**Player Interface**:
```asm
; Init: JSR $1000
;   Input: A = song number ($00)
;   Modifies: All registers
;
; Play: JSR $10A1
;   Called every frame (50/60 Hz)
;   Modifies: All registers
```

---

## Implementation Approach: Hybrid Driver

### Architecture

```
┌──────────────────────────────────────────────────┐
│ SF2 File Header ($0000-$0D7D)                    │
│  - PSID v2 header (if exported as .sid)          │
│  - Or direct load address $0D7E                  │
├──────────────────────────────────────────────────┤
│ Driver Wrapper Code ($0D7E-$0DFF)               │
│  - SF2 init entry → jumps to Laxity init        │
│  - SF2 play entry → jumps to Laxity play        │
│  - Memory setup code                             │
├──────────────────────────────────────────────────┤
│ Laxity Player Code ($0E00-$16FF)                │
│  - Original Laxity init routine (relocated)      │
│  - Original Laxity play routine (relocated)      │
│  - Table processing code                         │
│  - SID register writes                           │
├──────────────────────────────────────────────────┤
│ SF2 Header Blocks ($1700-$18FF)                  │
│  - Block 1: Driver descriptor                    │
│  - Block 2: Entry points ($0D7E, $0D81)         │
│  - Block 3: Table definitions                    │
│  - Block 4-9: Metadata                           │
│  - Block 255: End marker                         │
├──────────────────────────────────────────────────┤
│ Music Data Tables ($1900+)                       │
│  - Order lists                                   │
│  - Filter table ($1A1E)                          │
│  - Pulse table ($1A3B)                           │
│  - Instruments ($1A6B)                           │
│  - Wave tables ($1ACB+)                          │
└──────────────────────────────────────────────────┘
```

### Memory Relocation Strategy

**Challenge**: Laxity expects to run at $1000, SF2 loads at $0D7E.

**Solution**: Relocate Laxity player by $0E00 - $1000 = -$0200 (512 bytes lower).

**Relocation Steps**:
1. Extract player code ($1000-$19FF) from reference SID
2. Scan for absolute address references
3. Subtract $0200 from all addresses in range $1000-$19FF
4. Update self-modifying code targets
5. Write relocated code at $0E00

**Critical Code Patterns to Relocate**:
```asm
; Absolute addressing
LDA $1234    ; Becomes LDA $1034
STA $1567    ; Becomes STA $1367

; Absolute indexed
LDA $1234,X  ; Becomes LDA $1034,X

; Jump/Branch targets (within player code)
JMP $15A0    ; Becomes JMP $13A0
JSR $1234    ; Becomes JSR $1034

; DO NOT relocate:
; - Zero page addresses ($00-$FF)
; - SID registers ($D400-$D7FF)
; - External addresses (outside $1000-$19FF)
```

---

## Implementation Phases

### Phase 1: Extract Reference Player Code

**Input**: Known good Laxity SID file (e.g., Stinsen's Last Night of 89)

**Process**:
1. Load SID file
2. Get load address from header
3. Extract bytes from load_addr to load_addr + $A00
4. Save as binary blob

**Output**: `laxity_player_reference.bin` (2560 bytes)

**Python Script**:
```python
def extract_laxity_player(sid_path, output_bin):
    """Extract Laxity player code from SID file."""
    with open(sid_path, 'rb') as f:
        sid_data = f.read()

    # Parse PSID header
    load_addr = struct.unpack('<H', sid_data[8:10])[0]
    if load_addr == 0:
        load_addr = struct.unpack('<H', sid_data[0x7C:0x7E])[0]

    data_offset = struct.unpack('>H', sid_data[6:8])[0]

    # Extract player code (assumed to be ~2.5KB)
    player_start = data_offset
    player_end = data_offset + 0xA00
    player_code = sid_data[player_start:player_end]

    with open(output_bin, 'wb') as f:
        f.write(player_code)

    return load_addr, len(player_code)
```

### Phase 2: Disassemble and Analyze

**Process**:
1. Disassemble player code with SIDwinder
2. Identify all absolute address references
3. Map table access patterns
4. Document self-modifying code locations
5. Identify zero-page usage

**Tools**:
```bash
# Disassemble reference SID
tools/SIDwinder.exe disassemble SID/reference.sid laxity_player.asm

# Analyze for absolute addressing modes
grep -E "LDA \$[0-9A-F]{4}|STA \$[0-9A-F]{4}|JMP \$[0-9A-F]{4}" laxity_player.asm
```

**Expected Findings**:
- ~50-100 absolute address references
- 5-10 self-modifying code locations
- 10-20 zero-page variables

### Phase 3: Create Relocation Script

**Script**: `scripts/relocate_laxity_player.py`

**Algorithm**:
```python
def relocate_player_code(code_bytes, old_base, new_base):
    """
    Relocate 6502 code from old_base to new_base.

    Args:
        code_bytes: Original player code
        old_base: Original load address (e.g., 0x1000)
        new_base: New load address (e.g., 0x0E00)

    Returns:
        Relocated code bytes
    """
    relocated = bytearray(code_bytes)
    delta = new_base - old_base  # e.g., -0x200

    # Scan for addressing mode patterns
    i = 0
    while i < len(relocated) - 2:
        opcode = relocated[i]

        # Absolute addressing: 3-byte instructions
        if opcode in ABSOLUTE_OPCODES:
            addr_lo = relocated[i+1]
            addr_hi = relocated[i+2]
            addr = (addr_hi << 8) | addr_lo

            # If address is in player code range, relocate it
            if old_base <= addr < (old_base + len(code_bytes)):
                new_addr = addr + delta
                relocated[i+1] = new_addr & 0xFF
                relocated[i+2] = (new_addr >> 8) & 0xFF

            i += 3
        else:
            i += 1

    return bytes(relocated)

ABSOLUTE_OPCODES = {
    # LDA absolute
    0xAD,
    # STA absolute
    0x8D,
    # JMP absolute
    0x4C,
    # JSR absolute
    0x20,
    # ... (complete list of ~40 opcodes)
}
```

### Phase 4: Build Driver Wrapper

**Code**: `drivers/laxity_driver_wrapper.asm`

```asm
; Laxity NewPlayer v21 SF2 Driver
; Wrapper for original Laxity player code
; Load address: $0D7E

.org $0D7E

;===========================================
; SF2 Entry Points
;===========================================

sf2_init:
    ; Save song number
    sta song_number

    ; Call Laxity init (relocated)
    lda song_number
    jsr laxity_init_relocated
    rts

sf2_play:
    ; Call Laxity play (relocated)
    jsr laxity_play_relocated
    rts

song_number:
    .byte $00

;===========================================
; Laxity Player Code (Relocated from $1000 to $0E00)
;===========================================

.org $0E00

laxity_init_relocated:
    ; Relocated Laxity init code
    ; (Inserted by Python script)
    .incbin "laxity_player_relocated.bin", 0, $00A1

laxity_play_relocated:
    ; Relocated Laxity play code
    ; (Inserted by Python script)
    .incbin "laxity_player_relocated.bin", $00A1, $09FF

;===========================================
; SF2 Header Blocks
;===========================================

.org $1700

header_blocks:
    ; Block 1: Driver descriptor
    .byte $01              ; Block ID
    .byte $20              ; Block size
    .byte "Laxity NP21"    ; Driver name
    .byte $00              ; Null terminator
    ; ... (more header data)

    ; Block 2: Entry points
    .byte $02              ; Block ID
    .byte $06              ; Block size
    .word $0D7E            ; Init address
    .word $0D81            ; Play address

    ; Block 3: Table definitions
    .byte $03              ; Block ID
    .byte $40              ; Block size
    ; Instrument table
    .byte $01              ; Table ID
    .word $1A6B            ; Address
    .byte $20              ; Rows (32 instruments)
    .byte $08              ; Columns
    ; Pulse table
    .byte $02              ; Table ID
    .word $1A3B            ; Address
    .byte $10              ; Rows
    .byte $04              ; Columns
    ; Filter table
    .byte $03              ; Table ID
    .word $1A1E            ; Address
    .byte $08              ; Rows
    .byte $04              ; Columns
    ; Wave table
    .byte $04              ; Table ID
    .word $1ACB            ; Address
    .byte $80              ; Rows (128 entries)
    .byte $02              ; Columns

    ; Block 255: End marker
    .byte $FF
```

### Phase 5: Create Conversion Pipeline

**Modify**: `scripts/sid_to_sf2.py`

**Add Function**:
```python
def convert_with_laxity_driver(sid_path, output_sf2):
    """Convert Laxity SID using custom Laxity driver."""

    # 1. Load and parse SID
    memory, load_addr, init_addr, play_addr = load_sid(sid_path)

    # 2. Extract tables using existing extractor
    instruments = extract_instruments(memory, load_addr)
    wave_table = extract_wave_table(memory, load_addr)
    pulse_table = extract_pulse_table(memory, load_addr)
    filter_table = extract_filter_table(memory, load_addr)
    sequences = extract_sequences_runtime(sid_path)  # Use siddump

    # 3. Load Laxity driver template
    with open('drivers/laxity_driver.prg', 'rb') as f:
        driver_template = bytearray(f.read())

    # 4. Inject tables at Laxity-specific offsets
    # (Tables are already in Laxity format from extraction!)
    inject_table(driver_template, 0x1A6B, instruments)
    inject_table(driver_template, 0x1A3B, pulse_table)
    inject_table(driver_template, 0x1A1E, filter_table)
    inject_table(driver_template, 0x1ACB, wave_table)
    inject_sequences(driver_template, 0x1900, sequences)

    # 5. Write SF2 file
    with open(output_sf2, 'wb') as f:
        f.write(driver_template)

    print(f"Converted to Laxity driver SF2: {output_sf2}")
```

### Phase 6: Testing

**Test Plan**:

1. **Smoke Test**: Load SF2 in editor
   - SF2 opens without error
   - Player initializes
   - No crashes

2. **Playback Test**: Compare audio
   - Export SF2 to SID
   - Compare WAVs (original vs exported)
   - Check siddump accuracy

3. **Editing Test**: Modify tables
   - Edit instrument parameters
   - Change wave table
   - Verify changes take effect

4. **Batch Test**: Convert all 18 files
   - Run conversion pipeline
   - Calculate accuracy scores
   - Compare with Driver 11 results

**Success Criteria**:
- ✅ SF2 loads in editor
- ✅ Playback accuracy > 60%
- ✅ At least 10/18 files > 70% accuracy
- ⚠️ Table editing may not work (acceptable for v1.0)

---

## Risks and Mitigations

### Risk 1: Relocation Breaks Code

**Probability**: High
**Impact**: Critical

**Mitigation**:
- Test with unmodified player first (at original address $1000)
- Relocate incrementally (identify each broken reference)
- Use SIDwinder trace to debug

### Risk 2: Zero-Page Conflicts

**Probability**: Medium
**Impact**: High

**Mitigation**:
- Map Laxity's zero-page usage
- Check SF2 editor's zero-page usage (if accessible)
- Reserve Laxity's ZP addresses

### Risk 3: Self-Modifying Code

**Probability**: High
**Impact**: Medium

**Mitigation**:
- Identify SMC via disassembly
- Manually verify relocations
- Test each SMC location

### Risk 4: SF2 Editor Compatibility

**Probability**: Low
**Impact**: High

**Mitigation**:
- Study existing driver headers carefully
- Test loading in SF2 immediately
- May need hex editing adjustments

---

## Timeline Estimate

**Phase 1**: Extract player code - 2 hours
**Phase 2**: Disassembly analysis - 4 hours
**Phase 3**: Relocation script - 8 hours
**Phase 4**: Driver wrapper - 6 hours
**Phase 5**: Conversion pipeline - 4 hours
**Phase 6**: Testing and debugging - 16 hours

**Total**: ~40 hours (~1 week full-time)

---

## Deliverables

1. **Documentation**:
   - This implementation plan ✅
   - Relocation analysis document
   - Testing results report

2. **Code**:
   - `scripts/extract_laxity_player.py`
   - `scripts/relocate_laxity_player.py`
   - `drivers/laxity_driver_wrapper.asm`
   - `drivers/laxity_driver.prg` (assembled)

3. **Modified Scripts**:
   - `scripts/sid_to_sf2.py` (add `--driver laxity` option)
   - `complete_pipeline_with_validation.py` (support Laxity driver)

4. **Test Results**:
   - Accuracy comparison (Driver 11 vs Laxity driver)
   - Validation dashboard update
   - Example SF2 files

---

## Next Immediate Steps

1. **Extract reference player** from Stinsen's Last Night of 89
2. **Disassemble** and identify address references
3. **Create minimal test**: Player at original $1000, verify playback
4. **Implement relocation**: Move to $0E00, fix references
5. **Build wrapper**: Create SF2 entry points

**First Concrete Action**: Run extraction script on reference SID file.

---

## References

- `docs/analysis/LAXITY_SF2_DRIVER_RESEARCH.md` - Background research
- `docs/reference/STINSENS_PLAYER_DISASSEMBLY.md` - Player code analysis
- `LAXITY_NP20_RESEARCH_REPORT.md` - Format compatibility study
- Driver binary analysis (this session)

---

## Status

**Phase**: Design Complete
**Next**: Begin Phase 1 (Extract Player Code)
**Confidence**: High (80% for playback, 40% for full editing)
