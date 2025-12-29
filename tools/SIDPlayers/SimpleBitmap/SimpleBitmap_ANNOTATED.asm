;==============================================================================
; SimpleBitmap.asm
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

* = PlayerADDR//; =============================================================================//; EXTERNAL RESOURCES//; =============================================================================#if USERDEFINES_KoalaFile.var file_bitmap = LoadBinary(KoalaFile, BF_KOALA)#else.var file_bitmap = LoadBinary("../../Bitmaps/default.kla", BF_KOALA)#endif.var logo_BGColor = file_bitmap.getBackgroundColor()//; =============================================================================//; MEMORY LAYOUT CONFIGURATION//; =============================================================================.const BitmapMAPData = $a000           //; Bitmap data location (8K).const BitmapCOLData = $8800           //; Color RAM source data.const BitmapSCRData = $8c00           //; Screen RAM data//; =============================================================================//; INITIALIZATION ENTRY POINT//; =============================================================================InitIRQ: {    sei                                 //; Disable interrupts during setup    //; Configure memory mapping    lda #$35                            //; Enable KERNAL, BASIC, and I/O    sta $01  ; Store Accumulator
    //; Wait for stable raster position    jsr VSync  ; Jump to Subroutine
    //; Blank screen during initialization    lda #$00  ; Load Accumulator
    sta $d011                           //; Turn off display    sta $d020                           //; Black border    sta $d021                           //; Black background    //; Initialize the music    jsr SIDInit  ; Jump to Subroutine
    //; Ensure stable timing    jsr VSync  ; Jump to Subroutine
    //; Disable NMI interrupts    jsr NMIFix  ; Jump to Subroutine
    //; ==========================================================================    //; COLOR RAM INITIALIZATION    //; ==========================================================================    //; Copy color data to hardware color RAM at $D800    ldy #$00  ; Load Y Register
!loop:    //; Unrolled loop for faster color RAM initialization    lda BitmapCOLData + (0 * 256), y   //; Copy first page    sta $d800         + (0 * 256), y  ; Store Accumulator
    lda BitmapCOLData + (1 * 256), y   //; Copy second page    sta $d800         + (1 * 256), y  ; Store Accumulator
    lda BitmapCOLData + (2 * 256), y   //; Copy third page    sta $d800         + (2 * 256), y  ; Store Accumulator
    lda BitmapCOLData + (3 * 256), y   //; Copy fourth page (partial)    sta $d800         + (3 * 256), y  ; Store Accumulator
    iny  ; Increment Y
    bne !loop-  ; Branch if Not Equal
	lda #logo_BGColor  ; Load Accumulator
    sta $d021  ; Voice 1 Pulse Width Low
    //; ==========================================================================    //; INTERRUPT SYSTEM SETUP    //; ==========================================================================    //; Set up interrupt vectors    lda #<MusicIRQ  ; Load Accumulator
    sta $fffe  ; Store Accumulator
    lda #>MusicIRQ  ; Load Accumulator
    sta $ffff  ; Store Accumulator
    //; Configure interrupt sources    lda #$7f  ; Load Accumulator
    sta $dc0d                           //; Disable CIA interrupts    lda $dc0d                           //; Acknowledge any pending    lda #$01  ; Load Accumulator
    sta $d01a                           //; Enable raster interrupts    lda #$01  ; Load Accumulator
    sta $d019                           //; Clear any pending raster interrupt    //; Wait for stable position before enabling display    jsr VSync  ; Jump to Subroutine
    //; Configure first raster position    ldx #0  ; Load X Register
    jsr SetNextRaster  ; Jump to Subroutine
    //; ==========================================================================    //; VIC-II BITMAP MODE CONFIGURATION    //; ==========================================================================    //; Set VIC bank (bank 0: $0000-$3FFF)    lda #$01                            //; Select VIC bank 0    sta $dd00  ; Store Accumulator
    lda #$3e                            //; Configure CIA data direction    sta $dd02  ; Store Accumulator
    //; Configure VIC memory pointers    lda #$38                            //; Screen at $0C00, bitmap at $2000    sta $d018                           //; (relative to VIC bank)    //; Set display mode    lda #$18                            //; Multicolor mode on    sta $d016  ; Voice 1 Frequency High
    lda #$00                            //; Sprites off    sta $d015  ; Voice 1 Frequency High
    //; Enable bitmap display    lda $d011  ; Voice 1 Frequency High
    and #$80                            //; Preserve raster high bit    ora #$3b                            //; Bitmap mode, display on, 25 rows    sta $d011  ; Voice 1 Frequency High
    cli                                 //; Enable interrupts    //; Main loop - music plays via interruptsForever:    jmp Forever  ; Jump
}//; =============================================================================//; VERTICAL SYNC ROUTINE//; =============================================================================//; Waits for the vertical blank period to ensure stable timing//; Registers: Preserves allVSync: {    bit $d011                           //; Wait for raster to leave    bpl *-3                             //; the vertical blank area    bit $d011                           //; Wait for raster to enter    bmi *-3                             //; the vertical blank area    rts  ; Return from Subroutine
}//; =============================================================================//; RASTER POSITION SETUP//; =============================================================================//; Sets up the next raster interrupt position based on the current call index//; Input: X = interrupt index (0 to NumCallsPerFrame-1)//; Registers: Corrupts ASetNextRaster: {    lda D012_Values, x                  //; Get raster line low byte    sta $d012  ; Voice 1 Frequency High
    lda $d011                           //; Get current VIC control register    and #$7f                            //; Clear raster high bit    ora D011_Values, x                  //; Set raster high bit if needed    sta $d011  ; Voice 1 Frequency High
    rts  ; Return from Subroutine
}//; =============================================================================//; MAIN MUSIC INTERRUPT HANDLER//; =============================================================================//; Handles music playback for multi-speed tunes//; No visual effects to maintain clean bitmap displayMusicIRQ: {    //; Track which call this is within the framecallCount:    ldx #0                              //; Self-modifying counter    inx  ; Increment X
    cpx #NumCallsPerFrame  ; Compare with X
    bne JustPlayMusic  ; Branch if Not Equal
    ldx #0                              //; Reset counter at frame boundaryJustPlayMusic:    stx callCount + 1                   //; Store updated counter    //; Play the music    jsr SIDPlay  ; Jump to Subroutine
    //; Set up next interrupt    ldx callCount + 1  ; Load X Register
    jsr SetNextRaster  ; Jump to Subroutine
    //; Acknowledge interrupt    asl $d019                           //; Clear raster interrupt flag    rti}//; =============================================================================//; INCLUDES//; =============================================================================//; Import common utility routines.import source "../INC/NMIFix.asm"           //; NMI interrupt protection//; =============================================================================//; DATA SECTION - Raster Line Timing//; =============================================================================.var FrameHeight = 312 // TODO: NTSC!D011_Values: .fill NumCallsPerFrame, (>(mod(250 + ((FrameHeight * i) / NumCallsPerFrame), 312))) * $80D012_Values: .fill NumCallsPerFrame, (<(mod(250 + ((FrameHeight * i) / NumCallsPerFrame), 312)))//; =============================================================================//; BITMAP DATA SEGMENTS//; =============================================================================//; These are placed at specific memory locations for VIC-II access* = BitmapMAPData "Bitmap MAP"	.fill file_bitmap.getBitmapSize(), file_bitmap.getBitmap(i)* = BitmapSCRData "Bitmap SCR"	.fill file_bitmap.getScreenRamSize(), file_bitmap.getScreenRam(i)* = BitmapCOLData "Bitmap COL"	.fill file_bitmap.getColorRamSize(), file_bitmap.getColorRam(i)//; =============================================================================//; END OF FILE//; =============================================================================