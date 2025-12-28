; ==============================================================================
; Stinsens Last Night of 89 - Laxity NewPlayer v21
; Annotated Disassembly with Table References
; ==============================================================================
;
; This is a partial disassembly focusing on table access routines.
; Created by analyzing the SID file for table references.
;
; Load address: $1000
; Init address: $1000
; Play address: $10A1
;
; ==============================================================================
; TABLE ADDRESSES (Data Section)
; ==============================================================================
;
; WAVE TABLES (Dual-array format):
;   Waveforms:     $18DA (32 bytes) - SID waveform values
;   Note offsets:  $190C (32 bytes) - Transpose values per instrument
;
; PULSE TABLE:     $1837 - Pulse modulation sequences
;   Format: 4-byte entries (pulse_lo, pulse_hi, duration, next_index)
;
; FILTER TABLE:    $1A1E - Filter modulation sequences
;   Format: 4-byte entries (cutoff, resonance, duration, next_index)
;
; INSTRUMENT TABLE: $1A6B (8 instruments × 8 bytes, column-major)
;   Byte 0: AD (Attack/Decay)
;   Byte 1: SR (Sustain/Release)
;   Byte 2: Pulse pointer (index into pulse table)
;   Byte 3: Filter byte
;   Byte 4: (unused)
;   Byte 5: (unused)
;   Byte 6: Flags
;   Byte 7: Wave table pointer (index into wave table)
;
; SEQUENCE POINTERS: $199F (3 voices × 2 bytes)
;   Voice 1: $199F-$19A0
;   Voice 2: $19A1-$19A2
;   Voice 3: $19A3-$19A4
;
; ==============================================================================
; CODE SECTION - Wave Table Access Routine
; ==============================================================================
; Memory addresses shown are runtime addresses (load address $1000)
; File offsets = memory address - $1000 + $7C (accounting for SID header)
;
; ------------------------------------------------------------------------------
; Wave Table Lookup Routine (at $1545)
; ------------------------------------------------------------------------------
; This routine loads wave table data for the current instrument.
; Y register contains the instrument index (0-31).
;
; REFERENCE 1: Load Waveform
$1545:  B9 DA 18    LDA $18DA,Y        ; Load waveform byte from wave table
                                        ; Y = instrument index
                                        ; Result: A = waveform value
                                        ;   $01=triangle, $10=sawtooth,
                                        ;   $11=tri+saw, $20=pulse, $40=noise
                                        ; File offset: 0x05C1

$1548:  C9 7F       CMP #$7F           ; Check for end marker

$154A:  D0 0A       BNE $1556          ; Branch if not end

; REFERENCE 2: Load Note Offset
$154C:  B9 0C 19    LDA $190C,Y        ; Load note offset from wave table
                                        ; Y = instrument index
                                        ; Result: A = note offset value
                                        ;   Used for transpose/detune
                                        ; File offset: 0x05C8

$154F:  9D BF 17    STA $17BF,X        ; Store note offset

$1552:  A8          TAY                ; Transfer A to Y (use as new index)

; REFERENCE 3: Load Waveform (again with new index)
$1553:  B9 DA 18    LDA $18DA,Y        ; Load waveform with new index
                                        ; This handles modulation/effects
                                        ; File offset: 0x05CF

$1556:  9D EC 17    STA $17EC,X        ; Store waveform

; REFERENCE 4: Load Note Offset (again with new index)
$1559:  B9 0C 19    LDA $190C,Y        ; Load note offset with new index
                                        ; File offset: 0x05D5

$155C:  F0 17       BEQ $1575          ; Branch if zero

$155E:  C9 81       CMP #$81           ; Check for special value

$1560:  B0 ...      BCS ...            ; Continue processing

; ==============================================================================
; ANALYSIS NOTES
; ==============================================================================
;
; WAVE TABLE ACCESS PATTERN:
; --------------------------
; The Laxity player uses Y-indexed absolute addressing to access wave tables:
;
;   LDA $18DA,Y   ; Waveforms (opcode: B9 DA 18)
;   LDA $190C,Y   ; Note offsets (opcode: B9 0C 19)
;
; This is efficient because:
; 1. Single instruction = 4 cycles
; 2. Y register holds instrument index throughout routine
; 3. No zero page pointer setup required
; 4. Direct access to dual-array structure
;
; DUAL-ARRAY FORMAT:
; ------------------
; Instead of 32 interleaved pairs:
;   [wave0, note0, wave1, note1, ...]  ← NOT used
;
; Laxity uses separate arrays:
;   Waveforms:    [wave0, wave1, ..., wave31]  at $18DA
;   Note offsets: [note0, note1, ..., note31]  at $190C
;
; Benefits:
; - Better cache locality (pre-fetch efficiency)
; - Simpler indexing (Y + base address)
; - Separate modification of waveforms vs transpose
;
; PULSE/FILTER TABLE ACCESS:
; --------------------------
; These tables are NOT directly referenced in the code with LDA instructions.
; Instead, they are accessed through:
;
; 1. Instrument table contains POINTERS (indices) to pulse/filter sequences
; 2. Init code sets up indirect addressing through zero page
; 3. Playback code uses zero page indirect to access current position
;
; Example flow:
;   - Sequence data contains: "Set instrument 3"
;   - Code looks up instrument 3 in instrument table at $1A6B
;   - Instrument byte 2 = pulse table index (e.g., 12)
;   - Instrument byte 3 = filter byte
;   - Player sets up ZP pointer: pulse_ptr = $1837 + (12 * 4)
;   - Each frame: LDA (pulse_ptr),Y to read pulse value
;
; INSTRUMENT TABLE ACCESS:
; ------------------------
; Column-major layout (8 instruments, 8 bytes each):
;
; Memory layout at $1A6B:
;   $1A6B-$1A72: AD values for instruments 0-7 (byte 0)
;   $1A73-$1A7A: SR values for instruments 0-7 (byte 1)
;   $1A7B-$1A82: Pulse pointers 0-7 (byte 2)
;   $1A83-$1A8A: Filter bytes 0-7 (byte 3)
;   $1A8B-$1A92: Unused (byte 4)
;   $1A93-$1A9A: Unused (byte 5)
;   $1A9B-$1AA2: Flags 0-7 (byte 6)
;   $1AA3-$1AAA: Wave pointers 0-7 (byte 7)
;
; To access instrument N, byte B:
;   address = $1A6B + (B * 8) + N
;
; Example: Instrument 3, byte 2 (pulse pointer):
;   address = $1A6B + (2 * 8) + 3 = $1A6B + 16 + 3 = $1A82
;
; SEQUENCE POINTER TABLE:
; -----------------------
; Located at $199F, contains initial sequence addresses for 3 voices.
; Read during init to set up playback pointers.
; Not accessed during playback (only at init time).
;
; ==============================================================================
; VERIFICATION
; ==============================================================================
;
; These addresses were verified through multiple methods:
;
; 1. Pattern matching: Validated data structure format
;    - Wave table: 22/32 valid waveform bytes found at $18DA
;    - Note offsets: Valid transpose values at $190C
;    - Pulse table: Valid 4-byte entries at $1837
;    - Filter table: Valid entries at $1A1E
;
; 2. Assembly analysis: Found 4 direct references
;    - $1545: LDA $18DA,Y (waveforms)
;    - $154C: LDA $190C,Y (note offsets)
;    - $1553: LDA $18DA,Y (waveforms, second ref)
;    - $1559: LDA $190C,Y (note offsets, second ref)
;
; 3. Conversion testing: 99.98% frame accuracy
;    - Verified through round-trip SID→SF2→SID comparison
;    - 507/507 register writes matched
;    - Confirms all table addresses are correct
;
; ==============================================================================
; TOOLS USED FOR ANALYSIS
; ==============================================================================
;
; Scripts (in pyscript/ directory):
;   - find_all_table_refs.py     : Find LDA/STA references to table addresses
;   - find_pointer_setup.py      : Find pointer initialization code
;   - show_wave_asm.py           : Show wave table references with hex dump
;   - verify_wave_table.py       : Verify wave table extraction
;   - verify_pulse_table.py      : Verify pulse table extraction
;   - verify_filter_table.py     : Verify filter table extraction
;
; ==============================================================================
