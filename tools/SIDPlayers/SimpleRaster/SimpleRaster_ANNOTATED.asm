;==============================================================================
; SimpleRaster.asm
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

* = PlayerADDR//; =============================================================================//; INITIALIZATION ENTRY POINT//; =============================================================================InitIRQ: {    sei                                 //; Disable interrupts during setup    //; Configure memory mapping    lda #$35                            //; Enable KERNAL, BASIC, and I/O    sta $01  ; Store Accumulator
    //; Wait for stable raster position    jsr VSync  ; Jump to Subroutine
    //; Blank screen during initialization    lda #$00  ; Load Accumulator
    sta $d011                           //; Turn off display    sta $d020                           //; Black border    //; Initialize the music    jsr SIDInit  ; Jump to Subroutine
    //; Ensure we're at a stable position    jsr VSync  ; Jump to Subroutine
    //; Disable NMI interrupts to prevent interference    jsr NMIFix  ; Jump to Subroutine
    //; Set up interrupt vectors    lda #<MusicIRQ  ; Load Accumulator
    sta $fffe  ; Store Accumulator
    lda #>MusicIRQ  ; Load Accumulator
    sta $ffff  ; Store Accumulator
    //; Configure first raster position    ldx #0  ; Load X Register
    jsr SetNextRaster  ; Jump to Subroutine
    //; Configure interrupt sources    lda #$7f  ; Load Accumulator
    sta $dc0d                           //; Disable CIA interrupts    lda $dc0d                           //; Acknowledge any pending    lda #$01  ; Load Accumulator
    sta $d01a                           //; Enable raster interrupts    lda #$01  ; Load Accumulator
    sta $d019                           //; Clear any pending raster interrupt    cli                                 //; Enable interrupts    //; Main loop - the music plays via interruptsForever:    jmp Forever  ; Jump
}//; =============================================================================//; VERTICAL SYNC ROUTINE//; =============================================================================//; Waits for the vertical blank period to ensure stable timing//; Registers: Preserves allVSync: {    bit $d011                           //; Wait for raster to leave    bpl *-3                             //; the vertical blank area    bit $d011                           //; Wait for raster to enter    bmi *-3                             //; the vertical blank area    rts  ; Return from Subroutine
}//; =============================================================================//; RASTER POSITION SETUP//; =============================================================================//; Sets up the next raster interrupt position based on the current call index//; Input: X = interrupt index (0 to NumCallsPerFrame-1)//; Registers: Corrupts ASetNextRaster: {    lda D012_Values, x                  //; Get raster line low byte    sta $d012  ; Voice 1 Frequency High
    lda $d011                           //; Get current VIC control register    and #$7f                            //; Clear raster high bit    ora D011_Values, x                  //; Set raster high bit if needed    sta $d011  ; Voice 1 Frequency High
    rts  ; Return from Subroutine
}//; =============================================================================//; MAIN MUSIC INTERRUPT HANDLER//; =============================================================================//; Handles music playback and visual feedback//; Automatically manages multiple calls per frame for multi-speed tunesMusicIRQ: {    //; Increment call countercallCount:    ldx #0                              //; Self-modifying counter    inx  ; Increment X
    cpx #NumCallsPerFrame  ; Compare with X
    bne JustPlayMusic  ; Branch if Not Equal
    //; Frame boundary reached - update visual feedbackColChangeFrame:    ldy #$c0                            //; Self-modifying color index    iny  ; Increment Y
    bne !skip+  ; Branch if Not Equal
    inc $d020                           //; Change background color    ldy #$c0                            //; Reset color cycle!skip:    sty ColChangeFrame + 1              //; Store new color index    ldx #0                              //; Reset call counterJustPlayMusic:    stx callCount + 1                   //; Store updated counter    //; Visual CPU usage indicator    inc $d020                           //; Flash border during playback    jsr SIDPlay                         //; Call the music player    dec $d020                           //; Restore border color    //; Set up next interrupt    ldx callCount + 1  ; Load X Register
    jsr SetNextRaster  ; Jump to Subroutine
    //; Acknowledge interrupt    asl $d019                           //; Clear raster interrupt flag    rti}//; =============================================================================//; DATA SECTION - Raster Line Timing//; =============================================================================.var FrameHeight = 312 // TODO: NTSC!D011_Values: .fill NumCallsPerFrame, (>(mod(250 + ((FrameHeight * i) / NumCallsPerFrame), 312))) * $80D012_Values: .fill NumCallsPerFrame, (<(mod(250 + ((FrameHeight * i) / NumCallsPerFrame), 312)))//; =============================================================================//; INCLUDES//; =============================================================================//; Import common utility routines.import source "../INC/NMIFix.asm"           //; NMI interrupt protection//; =============================================================================//; END OF FILE//; =============================================================================