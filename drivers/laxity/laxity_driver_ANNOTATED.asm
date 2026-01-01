;==============================================================================
; laxity_driver.asm
; Annotated 6502 Assembly Disassembly
;==============================================================================
;
; PLAYER: Laxity NewPlayer v21
;
;==============================================================================
; MEMORY MAP
;==============================================================================
;
; LAXITY NEWPLAYER V21 TABLE ADDRESSES (Verified):
; $18DA   Wave Table - Waveforms (32 bytes)
; $190C   Wave Table - Note Offsets (32 bytes)
; $1837   Pulse Table (4-byte entries)
; $1A1E   Filter Table (4-byte entries)
; $1A6B   Instrument Table (8×8 bytes, column-major)
; $199F   Sequence Pointers (3 voices × 2 bytes)
;
;==============================================================================
; SID REGISTER REFERENCE
;==============================================================================
; $D400-$D406   Voice 1 (Frequency, Pulse, Control, ADSR)
; $D407-$D40D   Voice 2 (Frequency, Pulse, Control, ADSR)
; $D40E-$D414   Voice 3 (Frequency, Pulse, Control, ADSR)
; $D415-$D416   Filter Cutoff (11-bit)
; $D417         Filter Resonance/Routing
; $D418         Volume/Filter Mode
;
;==============================================================================
; CODE
;==============================================================================

;==============================================================================
; SYMBOL TABLE
;==============================================================================
;
; Total Symbols: 29
; Breakdown: 25 hardware, 2 subroutine, 2 unknown
;
; Address    Type         Name                     Refs     Description
; ---------- ------------ ------------------------ -------- --------------------
; $0D7E      Subroutine   SID Update               -        Update SID registers (music playback)
; $0D81      Subroutine   Subroutine               -        Subroutine
; $0E00      Unknown      addr_0e00                1c       Referenced address
; $0EA1      Unknown      addr_0ea1                1c       Referenced address
; $D400      Hardware     voice_1_frequency_low    -        Voice 1 Frequency Low
; $D401      Hardware     voice_1_frequency_high   -        Voice 1 Frequency High
; $D402      Hardware     voice_1_pulse_width_low  -        Voice 1 Pulse Width Low
; $D403      Hardware     voice_1_pulse_width_high -        Voice 1 Pulse Width High
; $D404      Hardware     voice_1_control_register -        Voice 1 Control Register
; $D405      Hardware     voice_1_attack/decay     -        Voice 1 Attack/Decay
; $D406      Hardware     voice_1_sustain/release  -        Voice 1 Sustain/Release
; $D407      Hardware     voice_2_frequency_low    -        Voice 2 Frequency Low
; $D408      Hardware     voice_2_frequency_high   -        Voice 2 Frequency High
; $D409      Hardware     voice_2_pulse_width_low  -        Voice 2 Pulse Width Low
; $D40A      Hardware     voice_2_pulse_width_high -        Voice 2 Pulse Width High
; $D40B      Hardware     voice_2_control_register -        Voice 2 Control Register
; $D40C      Hardware     voice_2_attack/decay     -        Voice 2 Attack/Decay
; $D40D      Hardware     voice_2_sustain/release  -        Voice 2 Sustain/Release
; $D40E      Hardware     voice_3_frequency_low    -        Voice 3 Frequency Low
; $D40F      Hardware     voice_3_frequency_high   -        Voice 3 Frequency High
; $D410      Hardware     voice_3_pulse_width_low  -        Voice 3 Pulse Width Low
; $D411      Hardware     voice_3_pulse_width_high -        Voice 3 Pulse Width High
; $D412      Hardware     voice_3_control_register -        Voice 3 Control Register
; $D413      Hardware     voice_3_attack/decay     -        Voice 3 Attack/Decay
; $D414      Hardware     voice_3_sustain/release  -        Voice 3 Sustain/Release
; $D415      Hardware     filter_cutoff_low        -        Filter Cutoff Low
; $D416      Hardware     filter_cutoff_high       -        Filter Cutoff High
; $D417      Hardware     filter_resonance/routing -        Filter Resonance/Routing
; $D418      Hardware     volume/filter_mode       -        Volume/Filter Mode
;==============================================================================
;
; Legend:
;   Refs: c=calls, r=reads, w=writes
;   Types: subroutine, data, hardware, unknown
;==============================================================================
;
;==============================================================================
; CALL GRAPH
;==============================================================================
;
; Entry Points (2):
;   - SID Update [$0D7E]
;   - Subroutine [$0D81]
;
; Call Hierarchy:
;
; SID Update [$0D7E]
; └─> JSR $0E00
;
; Subroutine [$0D81]
; └─> JSR $0EA1
;
; Statistics:
;   - Total subroutines: 2
;   - Maximum call depth: 1 levels
;   - Recursive calls: 0
;==============================================================================
;
;==============================================================================
; ENHANCED REGISTER ANALYSIS
;==============================================================================
;
; Total Register Lifecycles: 0
; Total Dependencies Tracked: 0
; Dead Code Instances: 0
;
; Register Lifecycles by Register:
;   A: 0 lifecycle(s)
;   X: 0 lifecycle(s)
;   Y: 0 lifecycle(s)
;
; REGISTER LIFECYCLE DETAILS (First 20)
; ----------------------------------------------------------------------------
; Reg Load@    Uses   Death@   Status     Instruction
;
;==============================================================================
;
; Laxity SF2 Driver Wrapper; Wraps relocated Laxity NewPlayer v21 with SF2 interface;; Memory Layout:; $0D7E-$0DFF   SF2 Wrapper (130 bytes); $0E00-$16FF   Relocated Laxity Player (2.3 KB); $1700-$18FF   SF2 Header Blocks (512 bytes); $1900+        Music Data*=$0D7E; SF2 Driver Entry Points; These addresses are fixed for SF2 compatibility; Init routine ($0D7E); Initializes SID and Laxity player;------------------------------------------------------------------------------
; Subroutine: SID Update
; Address: $0D7E
; Purpose: Update SID registers (music playback)
; Inputs: None
; Outputs: A
; Modifies: A
; Calls: $0E00
; Accesses: SID chip registers
;------------------------------------------------------------------------------
sf2_init:    ; Initialize SID chip    LDA #$00  ; Load Accumulator
    STA $D418           ; Master volume off        ; Initialize all voice control registers;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: Clear 3 memory locations
; Type: Memory Clear
; Addresses: $D404, $D40B, $D412
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    LDA #$00  ; Load Accumulator
    STA $D404           ; Voice 1 Control    STA $D40B           ; Voice 2 Control    STA $D412           ; Voice 3 Control        ; Call relocated Laxity init routine at $0E00    JSR $0E00           ; Laxity init        RTS  ; Return from Subroutine
; Padding to $0D81.align $0D81; Play routine ($0D81); Executes one frame of music;------------------------------------------------------------------------------
; Subroutine: Subroutine
; Address: $0D81
; Purpose: Subroutine
; Inputs: None
; Calls: $0EA1
;------------------------------------------------------------------------------
sf2_play:    ; Call relocated Laxity play routine    ; Laxity play entry was originally at $10A1    ; After relocation to $0E00, it's at $0E00 + ($10A1 - $1000) = $0EA1    JSR $0EA1           ; Laxity play        RTS  ; Return from Subroutine
; Padding to $0D84.align $0D84; Stop routine ($0D84); Stops music and silences SIDsf2_stop:    ; Silence all voices;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: Clear 3 memory locations
; Type: Memory Clear
; Addresses: $D404, $D40B, $D412
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    LDA #$00  ; Load Accumulator
    STA $D404           ; Voice 1 Control    STA $D40B           ; Voice 2 Control    STA $D412           ; Voice 3 Control        ; Kill all oscillators    LDA #$00  ; Load Accumulator
    STA $D418           ; Master volume off        RTS  ; Return from Subroutine
; Fill to end of wrapper.align $0E00