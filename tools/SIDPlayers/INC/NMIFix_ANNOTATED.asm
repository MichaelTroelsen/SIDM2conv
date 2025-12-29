;==============================================================================
; NMIFix.asm
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

NMIFix:		lda #$35  ; Load Accumulator
		sta $01  ; Store Accumulator
		lda #<!JustRTI+  ; Load Accumulator
		sta $FFFA  ; Store Accumulator
		lda #>!JustRTI+  ; Load Accumulator
		sta $FFFB  ; Store Accumulator
		lda #$00  ; Load Accumulator
		sta $DD0E  ; Store Accumulator
		sta $DD04  ; Store Accumulator
		sta $DD05  ; Store Accumulator
		lda #$81  ; Load Accumulator
		sta $DD0D  ; Store Accumulator
		lda #$01  ; Load Accumulator
		sta $DD0E  ; Store Accumulator
		rts  ; Return from Subroutine
	!JustRTI:		rti