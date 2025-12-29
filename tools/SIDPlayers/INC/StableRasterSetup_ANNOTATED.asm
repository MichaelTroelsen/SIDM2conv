;==============================================================================
; StableRasterSetup.asm
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

#importonce//; =============================================================================//; SetupStableRaster - Initialize stable raster interrupts//; //; This routine must be aligned to avoid page-crossing penalties during//; critical timing loops. It uses CIA timer B to compensate for interrupt//; jitter, ensuring pixel-perfect raster effects.//;//; Based on the technique from Spindle by lft (www.linusakesson.net/software/spindle/)//;//; Registers: Corrupts A, X, Y//; =============================================================================.align 128									//; Critical for timing accuracySetupStableRaster: {	//; Wait for vertical blank to ensure clean start	bit $d011  ; Voice 1 Frequency High
	bmi *-3  ; Branch if Minus
	bit $d011  ; Voice 1 Frequency High
	bpl *-3  ; Branch if Plus
	//; Get current raster line	ldx $d012  ; Voice 1 Frequency High
	inx  ; Increment X
ResyncLoop:	//; Wait for exact raster line match	cpx $d012  ; Voice 1 Frequency High
	bne *-3  ; Branch if Not Equal
	//; Initialize CIA timer B for jitter compensation	ldy #0  ; Load Y Register
	sty $dc07								//; Timer B high byte = 0	lda #62									//; Timer B low byte = 62	sta $dc06								//; Total = 63 cycles	//; Configure interrupts	iny										//; Y = 1	sty $d01a								//; Enable raster interrupts	dey  ; Decrement Y
	dey										//; Y = 255	sty $dc02								//; Data direction register	//; Waste exact cycles for synchronization	cmp (0,x)								//; 6 cycles	cmp (0,x)								//; 6 cycles	cmp (0,x)								//; 6 cycles	//; Start timer B in one-shot mode	lda #$11  ; Load Accumulator
	sta $dc0f  ; Store Accumulator
	//; Check if we're still on the expected line	txa  ; Transfer X to A
	inx  ; Increment X
	inx  ; Increment X
	cmp $d012  ; Voice 1 Frequency High
	bne ResyncLoop							//; If not, try again	//; Disable all CIA interrupts	lda #$7f  ; Load Accumulator
	sta $dc0d								//; CIA 1	sta $dd0d								//; CIA 2	//; Clear any pending interrupts	lda $dc0d  ; Load Accumulator
	lda $dd0d  ; Load Accumulator
	//; Final synchronization	bit $d011  ; Voice 1 Frequency High
	bpl *-3  ; Branch if Plus
	bit $d011  ; Voice 1 Frequency High
	bmi *-3  ; Branch if Minus
	//; Enable raster interrupts	lda #$01  ; Load Accumulator
	sta $d01a  ; Voice 1 Frequency High
	rts  ; Return from Subroutine
}//; =============================================================================//; TECHNICAL NOTES://; ----------------//; This routine achieves stable rasters by://; 1. Synchronizing to a specific raster line//; 2. Using CIA timer B to measure and compensate for jitter//; 3. Carefully counting cycles to ensure consistent timing//;//; The alignment to 128 bytes prevents timing variations from page crossings//; in branch instructions, which would add an extra cycle and break the//; synchronization.//; =============================================================================