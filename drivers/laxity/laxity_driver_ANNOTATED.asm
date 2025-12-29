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

; Laxity SF2 Driver Wrapper; Wraps relocated Laxity NewPlayer v21 with SF2 interface;; Memory Layout:; $0D7E-$0DFF   SF2 Wrapper (130 bytes); $0E00-$16FF   Relocated Laxity Player (2.3 KB); $1700-$18FF   SF2 Header Blocks (512 bytes); $1900+        Music Data*=$0D7E; SF2 Driver Entry Points; These addresses are fixed for SF2 compatibility; Init routine ($0D7E); Initializes SID and Laxity playersf2_init:    ; Initialize SID chip    LDA #$00  ; Load Accumulator
    STA $D418           ; Master volume off        ; Initialize all voice control registers    LDA #$00  ; Load Accumulator
    STA $D404           ; Voice 1 Control    STA $D40B           ; Voice 2 Control    STA $D412           ; Voice 3 Control        ; Call relocated Laxity init routine at $0E00    JSR $0E00           ; Laxity init        RTS  ; Return from Subroutine
; Padding to $0D81.align $0D81; Play routine ($0D81); Executes one frame of musicsf2_play:    ; Call relocated Laxity play routine    ; Laxity play entry was originally at $10A1    ; After relocation to $0E00, it's at $0E00 + ($10A1 - $1000) = $0EA1    JSR $0EA1           ; Laxity play        RTS  ; Return from Subroutine
; Padding to $0D84.align $0D84; Stop routine ($0D84); Stops music and silences SIDsf2_stop:    ; Silence all voices    LDA #$00  ; Load Accumulator
    STA $D404           ; Voice 1 Control    STA $D40B           ; Voice 2 Control    STA $D412           ; Voice 3 Control        ; Kill all oscillators    LDA #$00  ; Load Accumulator
    STA $D418           ; Master volume off        RTS  ; Return from Subroutine
; Fill to end of wrapper.align $0E00