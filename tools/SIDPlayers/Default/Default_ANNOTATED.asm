;==============================================================================
; Default.asm
; Annotated 6502 Assembly Disassembly
;==============================================================================
;
;
;==============================================================================
; MEMORY MAP
;==============================================================================
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

* = PlayerADDRInitIRQ:    sei  ; Set Interrupt Disable
    lda #$35  ; Load Accumulator
    sta $01  ; Store Accumulator
    jsr VSync  ; Jump to Subroutine
	lda #$00  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
	sta $d020  ; Voice 1 Pulse Width Low
    jsr SIDInit  ; Jump to Subroutine
    jsr VSync  ; Jump to Subroutine
    jsr NMIFix  ; Jump to Subroutine
    lda #<MusicIRQ  ; Load Accumulator
    sta $fffe  ; Store Accumulator
    lda #>MusicIRQ  ; Load Accumulator
    sta $ffff  ; Store Accumulator
    ldx #0  ; Load X Register
    jsr SetNextRaster  ; Jump to Subroutine
    lda #$7f  ; Load Accumulator
    sta $dc0d  ; Store Accumulator
    lda $dc0d  ; Load Accumulator
    lda #$01  ; Load Accumulator
    sta $d01a  ; Voice 1 Frequency High
    lda #$01  ; Load Accumulator
    sta $d019  ; Voice 1 Frequency High
    cli  ; Clear Interrupt Disable
Forever:    jmp Forever  ; Jump
VSync:	bit	$d011  ; Voice 1 Frequency High
	bpl	*-3  ; Branch if Plus
	bit	$d011  ; Voice 1 Frequency High
	bmi	*-3  ; Branch if Minus
    rts  ; Return from Subroutine
SetNextRaster:    lda D012_Values, x  ; Load Accumulator
    sta $d012  ; Voice 1 Frequency High
    lda $d011  ; Voice 1 Frequency High
    and #$7f  ; Logical AND
    ora D011_Values, x  ; Logical OR
    sta $d011  ; Voice 1 Frequency High
    rts  ; Return from Subroutine
MusicIRQ:callCount:    ldx #0  ; Load X Register
    inx  ; Increment X
    cpx #NumCallsPerFrame  ; Compare with X
    bne JustPlayMusic  ; Branch if Not Equal
ColChangeFrame:    ldy #$c0  ; Load Y Register
    iny  ; Increment Y
    bne !skip+  ; Branch if Not Equal
    inc $d020  ; Voice 1 Pulse Width Low
    ldy #$c0  ; Load Y Register
!skip:    sty ColChangeFrame + 1  ; Store Y Register
    ldx #0  ; Load X Register
JustPlayMusic:    stx callCount + 1  ; Store X Register
    jsr SIDPlay  ; Jump to Subroutine
    ldx callCount + 1  ; Load X Register
    jsr SetNextRaster  ; Jump to Subroutine
    asl $d019  ; Voice 1 Frequency High
    rti//; =============================================================================//; DATA SECTION - Raster Line Timing//; =============================================================================.var FrameHeight = 312 // TODO: NTSC!D011_Values: .fill NumCallsPerFrame, (>(mod(250 + ((FrameHeight * i) / NumCallsPerFrame), 312))) * $80D012_Values: .fill NumCallsPerFrame, (<(mod(250 + ((FrameHeight * i) / NumCallsPerFrame), 312))).import source "../INC/NMIFix.asm"