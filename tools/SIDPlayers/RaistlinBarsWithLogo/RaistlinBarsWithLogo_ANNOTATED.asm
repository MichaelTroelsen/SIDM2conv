;==============================================================================
; RaistlinBarsWithLogo.asm
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

#if D400_SHADOW && D401_SHADOW && D404_SHADOW && D406_SHADOW && D407_SHADOW && D408_SHADOW && D40B_SHADOW && D40D_SHADOW && D40E_SHADOW && D40F_SHADOW && D412_SHADOW && D414_SHADOW {	#define USE_INBUILT_SID_REGISTER_MIRRORING	.print "Using inbuilt SID register mirrors!" }#else {	#define USE_MANUAL_SID_REGISTER_MIRRORING }#endif* = PlayerADDR	jmp Initialize					//; Entry point for the player//; =============================================================================//; CONFIGURATION CONSTANTS//; =============================================================================//; Display layout.const NUM_FREQUENCY_BARS = 40.const LOGO_HEIGHT = 10.const TOP_SPECTRUM_HEIGHT = 9.const BOTTOM_SPECTRUM_HEIGHT = 3.const SONG_TITLE_LINE = 23//.const ARTIST_NAME_LINE = .const SPECTRUM_START_LINE = 11.const REFLECTION_SPRITES_YVAL = 50 + (SPECTRUM_START_LINE + TOP_SPECTRUM_HEIGHT) * 8 + 3.eval setSeed(55378008)//; Memory configuration.const VIC_BANK = 3						//; $C000-$FFFF.const VIC_BANK_ADDRESS = VIC_BANK * $4000.const SCREEN_0_OFFSET = 0				//; $C000-C3E7.const SCREEN_1_OFFSET = 1				//; $C400-C7E7.const CHARSET_OFFSET = 1				//; $C800-CFFF.const BITMAP_OFFSET = 1				//; $E000-FF3F.const SPRITE_BASE_INDEX = $40			//; $D000-?//; Calculated addresses.const SCREEN_0_ADDRESS = VIC_BANK_ADDRESS + (SCREEN_0_OFFSET * $400).const SCREEN_1_ADDRESS = VIC_BANK_ADDRESS + (SCREEN_1_OFFSET * $400).const CHARSET_ADDRESS = VIC_BANK_ADDRESS + (CHARSET_OFFSET * $800).const BITMAP_ADDRESS = VIC_BANK_ADDRESS + (BITMAP_OFFSET * $2000).const SPRITES_ADDRESS = VIC_BANK_ADDRESS + (SPRITE_BASE_INDEX * $40).const SPRITE_POINTERS_0 = SCREEN_0_ADDRESS + $3F8.const SPRITE_POINTERS_1 = SCREEN_1_ADDRESS + $3F8//; VIC register values.const D018_VALUE_0 = (SCREEN_0_OFFSET * 16) + (CHARSET_OFFSET * 2).const D018_VALUE_1 = (SCREEN_1_OFFSET * 16) + (CHARSET_OFFSET * 2).const D018_VALUE_BITMAP = (SCREEN_1_OFFSET * 16) + (BITMAP_OFFSET * 8)//; Calculated bar values.const MAX_BAR_HEIGHT = TOP_SPECTRUM_HEIGHT * 8 - 1.const WATER_REFLECTION_HEIGHT = BOTTOM_SPECTRUM_HEIGHT * 8.const MAIN_BAR_OFFSET = MAX_BAR_HEIGHT - 8.const REFLECTION_OFFSET = WATER_REFLECTION_HEIGHT - 7//; Color palette configuration.const NUM_COLOR_PALETTES = 3.const COLORS_PER_PALETTE = 8//; =============================================================================//; EXTERNAL RESOURCES//; =============================================================================.var file_charsetData = LoadBinary("CharSet.map").var file_waterSpritesData = LoadBinary("WaterSprites.map")#if USERDEFINES_KoalaFile.var file_logo = LoadBinary(KoalaFile, BF_KOALA)#else.var file_logo = LoadBinary("../../logos/default.kla", BF_KOALA)#endif.var logo_BGColor = file_logo.getBackgroundColor()//; Song metadata.var SONG_TITLE_LENGTH = min(SIDName.size(), 40)//.var ARTIST_NAME_LENGTH = min(SIDAuthor.size(), 40)//; =============================================================================//; INITIALIZATION//; =============================================================================Initialize: {	sei  ; Set Interrupt Disable
	//; Wait for stable raster before setup	bit $d011  ; Voice 1 Frequency High
	bpl *-3  ; Branch if Plus
	bit $d011  ; Voice 1 Frequency High
	bmi *-3  ; Branch if Minus
	//; Turn off display during initialization	lda #$00  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
	sta $d020  ; Voice 1 Pulse Width Low
	//; System setup	jsr SetupStableRaster  ; Jump to Subroutine
	jsr SetupSystem  ; Jump to Subroutine
	jsr NMIFix  ; Jump to Subroutine
	//; Initialize display	jsr InitializeVIC  ; Jump to Subroutine
	jsr ClearScreens  ; Jump to Subroutine
	jsr DisplaySongInfo  ; Jump to Subroutine
	ldy #$00  ; Load Y Register
	lda #$00  ; Load Accumulator
!loop:	sta barHeights - 2, y  ; Store Accumulator
	sta smoothedHeights - 2, y  ; Store Accumulator
	iny  ; Increment Y
	cpy #NUM_FREQUENCY_BARS + 4  ; Compare with Y
	bne !loop-  ; Branch if Not Equal
	//; Wait for stable raster before enabling display	bit $d011  ; Voice 1 Frequency High
	bpl *-3  ; Branch if Plus
	bit $d011  ; Voice 1 Frequency High
	bmi *-3  ; Branch if Minus
	//; Enable display	lda #$7b  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
	lda #logo_BGColor  ; Load Accumulator
	sta $d021  ; Voice 1 Pulse Width Low
	//; Setup interrupts	jsr SetupInterrupts  ; Jump to Subroutine
	//; Initialize music	jsr SetupMusic  ; Jump to Subroutine
	cli  ; Clear Interrupt Disable
	//; Main loop - wait for visualization updatesMainLoop:	lda visualizationUpdateFlag  ; Load Accumulator
	beq MainLoop  ; Branch if Equal
	jsr ApplySmoothing  ; Jump to Subroutine
	jsr RenderBars  ; Jump to Subroutine
	lda #$00  ; Load Accumulator
	sta visualizationUpdateFlag  ; Store Accumulator
	//; Toggle double buffer	lda currentScreenBuffer  ; Load Accumulator
	eor #$01  ; Logical XOR
	sta currentScreenBuffer  ; Store Accumulator
	jmp MainLoop  ; Jump
}//; =============================================================================//; SYSTEM SETUP//; =============================================================================SetupSystem: {	lda #$35  ; Load Accumulator
	sta $01  ; Store Accumulator
	//; Set VIC bank	lda #(63 - VIC_BANK)  ; Load Accumulator
	sta $dd00  ; Store Accumulator
	lda #VIC_BANK  ; Load Accumulator
	sta $dd02  ; Store Accumulator
	rts  ; Return from Subroutine
}//; =============================================================================//; VIC INITIALIZATION//; =============================================================================.const SKIP_REGISTER = $e1InitializeVIC: {	//; Apply VIC register configuration	ldx #VICConfigEnd - VICConfigStart - 1  ; Load X Register
!loop:	lda VICConfigStart, x  ; Load Accumulator
	cmp #SKIP_REGISTER  ; Compare with A
	beq !skip+  ; Branch if Equal
	sta $d000, x  ; Voice 1 Frequency Low
!skip:	dex  ; Decrement X
	bpl !loop-  ; Branch if Plus
	//; Initialize color palette	jsr InitializeColors  ; Jump to Subroutine
	rts  ; Return from Subroutine
}//; =============================================================================//; INTERRUPT SETUP//; =============================================================================SetupInterrupts: {	//; Set IRQ vectors	lda #<MainIRQ  ; Load Accumulator
	sta $fffe  ; Store Accumulator
	lda #>MainIRQ  ; Load Accumulator
	sta $ffff  ; Store Accumulator
	//; Setup raster interrupt	lda #251  ; Load Accumulator
	sta $d012  ; Voice 1 Frequency High
	lda #$7b  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
	//; Enable raster interrupts	lda #$01  ; Load Accumulator
	sta $d01a  ; Voice 1 Frequency High
	sta $d019  ; Voice 1 Frequency High
	rts  ; Return from Subroutine
}//; =============================================================================//; MAIN INTERRUPT HANDLER//; =============================================================================MainIRQ: {	pha	txa  ; Transfer X to A
	pha	tya  ; Transfer Y to A
	pha	lda #D018_VALUE_BITMAP  ; Load Accumulator
	sta $d018  ; Voice 1 Frequency High
	lda #$18  ; Load Accumulator
	sta $d016  ; Voice 1 Frequency High
	lda #$3b  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
	lda #logo_BGColor  ; Load Accumulator
	sta $d021  ; Voice 1 Pulse Width Low
	ldy currentScreenBuffer  ; Load Y Register
	lda D018Values, y  ; Load Accumulator
	sta SpectrometerD018 + 1  ; Store Accumulator
	//; Signal visualization update	inc visualizationUpdateFlag  ; Increment Memory
	//; Play music and analyze	jsr PlayMusicWithAnalysis  ; Jump to Subroutine
	//; Update bar animations	jsr UpdateBarDecay  ; Jump to Subroutine
	jsr UpdateColors  ; Jump to Subroutine
	jsr UpdateSprites  ; Jump to Subroutine
	//; Frame counter	inc frameCounter  ; Increment Memory
	bne !skip+  ; Branch if Not Equal
	inc frame256Counter  ; Increment Memory
!skip:	lda #50 + (LOGO_HEIGHT * 8)  ; Load Accumulator
	sta $d012  ; Voice 1 Frequency High
	lda #$3b  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
		lda #<SpectrometerDisplayIRQ  ; Load Accumulator
	sta $fffe  ; Store Accumulator
	lda #>SpectrometerDisplayIRQ  ; Load Accumulator
	sta $ffff  ; Store Accumulator
	//; Acknowledge interrupt	lda #$01  ; Load Accumulator
	sta $d01a  ; Voice 1 Frequency High
	sta $d019  ; Voice 1 Frequency High
	pla	tay  ; Transfer A to Y
	pla	tax  ; Transfer A to X
	pla	rti}SpectrometerDisplayIRQ:	pha	txa  ; Transfer X to A
	pha	tya  ; Transfer Y to A
	pha	ldx #4  ; Load X Register
!loop:	dex  ; Decrement X
	bpl !loop-  ; Branch if Plus
	nop	lda #$1b  ; Load Accumulator
	sta $d011  ; Voice 1 Frequency High
	lda #$00  ; Load Accumulator
	sta $d021  ; Voice 1 Pulse Width Low
SpectrometerD018:	lda #$00  ; Load Accumulator
	sta $d018  ; Voice 1 Frequency High
	lda #$08  ; Load Accumulator
	sta $d016  ; Voice 1 Frequency High
	//; Signal visualization update	inc visualizationUpdateFlag  ; Increment Memory
	lda #251  ; Load Accumulator
	sta $d012  ; Voice 1 Frequency High
	lda #<MainIRQ  ; Load Accumulator
	sta $fffe  ; Store Accumulator
	lda #>MainIRQ  ; Load Accumulator
	sta $ffff  ; Store Accumulator
	//; Acknowledge interrupt	lda #$01  ; Load Accumulator
	sta $d01a  ; Voice 1 Frequency High
	sta $d019  ; Voice 1 Frequency High
	pla	tay  ; Transfer A to Y
	pla	tax  ; Transfer A to X
	pla	rti//; =============================================================================//; MUSIC PLAYBACK WITH ANALYSIS//; =============================================================================PlayMusicWithAnalysis: {	#if USE_MANUAL_SID_REGISTER_MIRRORING		//; First playback - normal music playing with state preservation		jsr BackupSIDMemory  ; Jump to Subroutine
		jsr SIDPlay  ; Jump to Subroutine
		jsr RestoreSIDMemory  ; Jump to Subroutine
		//; Second playback - capture SID registers		lda $01  ; Load Accumulator
		pha		lda #$30  ; Load Accumulator
		sta $01  ; Store Accumulator
		jsr SIDPlay  ; Jump to Subroutine
		ldy #24  ; Load Y Register
	!loop:		lda $d400, y  ; Voice 1 Frequency Low
		sta sidRegisterMirror, y  ; Store Accumulator
		dey  ; Decrement Y
		bpl !loop-  ; Branch if Plus
		pla		sta $01  ; Store Accumulator
	#endif // USE_MANUAL_SID_REGISTER_MIRRORING	#if USE_INBUILT_SID_REGISTER_MIRRORING		jsr SIDPlay  ; Jump to Subroutine
		//; todo: we should change all this so that we don't need to do any copying at all		lda D400_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 0 + (0 * 7)  ; Store Accumulator
		lda D401_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 1 + (0 * 7)  ; Store Accumulator
		lda D404_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 4 + (0 * 7)  ; Store Accumulator
		lda D406_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 6 + (0 * 7)  ; Store Accumulator
		lda D407_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 0 + (1 * 7)  ; Store Accumulator
		lda D408_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 1 + (1 * 7)  ; Store Accumulator
		lda D40B_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 4 + (1 * 7)  ; Store Accumulator
		lda D40D_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 6 + (1 * 7)  ; Store Accumulator
		lda D40E_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 0 + (2 * 7)  ; Store Accumulator
		lda D40F_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 1 + (2 * 7)  ; Store Accumulator
		lda D412_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 4 + (2 * 7)  ; Store Accumulator
		lda D414_SHADOW_REGISTER  ; Load Accumulator
		sta sidRegisterMirror + 6 + (2 * 7)  ; Store Accumulator
	#endif // USE_INBUILT_SID_REGISTER_MIRRORING	//; Analyze captured registers	jmp AnalyzeSIDRegisters  ; Jump
}//; =============================================================================//; SID REGISTER ANALYSIS//; =============================================================================AnalyzeSIDRegisters: {	//; Process each voice	.for (var voice = 0; voice < 3; voice++) {		//; Check if voice is active		lda sidRegisterMirror + (voice * 7) + 4		//; Control register		bmi !skipVoice+									//; Skip if noise		and #$01										//; Check gate		beq !skipVoice+  ; Branch if Equal
		//; Get frequency and map to bar position		ldy sidRegisterMirror + (voice * 7) + 1		//; Frequency high		cpy #4  ; Compare with Y
		bcc !lowFreq+  ; Branch if Carry Clear
		//; High frequency lookup		ldx frequencyToBarHi, y  ; Load X Register
		jmp !gotBar+  ; Jump
	!lowFreq:		//; Low frequency lookup		ldx sidRegisterMirror + (voice * 7) + 0		//; Frequency low		txa  ; Transfer X to A
		lsr		lsr		ora multiply64Table, y  ; Logical OR
		tay  ; Transfer A to Y
		ldx frequencyToBarLo, y  ; Load X Register
	!gotBar:		//; Process envelope		lda sidRegisterMirror + (voice * 7) + 6		//; SR register		pha		//; Set release rate for this voice		and #$0f  ; Logical AND
		tay  ; Transfer A to Y
		lda releaseRateHi, y  ; Load Accumulator
		sta voiceReleaseHi + voice  ; Store Accumulator
		lda releaseRateLo, y  ; Load Accumulator
		sta voiceReleaseLo + voice  ; Store Accumulator
		//; Check sustain level		pla		lsr		lsr		lsr		lsr		tay  ; Transfer A to Y
		lda sustainToHeight, y  ; Load Accumulator
		//; Update bar if higher than current		cmp barHeights, x  ; Compare with A
		bcc !skipVoice+  ; Branch if Carry Clear
		sta barHeights, x  ; Store Accumulator
		lda #0  ; Load Accumulator
		sta barHeightsLo, x  ; Store Accumulator
		lda #voice  ; Load Accumulator
		sta barVoiceMap, x  ; Store Accumulator
	!skipVoice:	}	rts  ; Return from Subroutine
}//; =============================================================================//; BAR ANIMATION//; =============================================================================UpdateBarDecay: {	//; Apply decay to each bar based on its voice's release rate	ldx #NUM_FREQUENCY_BARS - 1  ; Load X Register
!loop:	ldy barVoiceMap, x  ; Load Y Register
	//; 16-bit subtraction for smooth decay	sec  ; Set Carry
	lda barHeightsLo, x  ; Load Accumulator
	sbc voiceReleaseLo, y	sta barHeightsLo, x  ; Store Accumulator
	lda barHeights, x  ; Load Accumulator
	sbc voiceReleaseHi, y	bpl !positive+  ; Branch if Plus
	//; Clamp to zero	lda #$00  ; Load Accumulator
	sta barHeightsLo, x  ; Store Accumulator
!positive:	sta barHeights, x  ; Store Accumulator
	dex  ; Decrement X
	bpl !loop-  ; Branch if Plus
	rts  ; Return from Subroutine
}//; =============================================================================//; SMOOTHING ALGORITHM//; =============================================================================ApplySmoothing: {	//; Apply gaussian-like smoothing for natural movement	ldx #0  ; Load X Register
!loop:	lda barHeights, x  ; Load Accumulator
	lsr	ldy barHeights - 2, x  ; Load Y Register
	adc div16, y	ldy barHeights - 1, x  ; Load Y Register
	adc div16mul3, y	ldy barHeights + 1, x  ; Load Y Register
	adc div16mul3, y	ldy barHeights + 2, x  ; Load Y Register
	adc div16, y	sta smoothedHeights, x  ; Store Accumulator
	inx  ; Increment X
	cpx #NUM_FREQUENCY_BARS  ; Compare with X
	bne !loop-  ; Branch if Not Equal
	rts  ; Return from Subroutine
}//; =============================================================================//; RENDERING//; =============================================================================RenderBars: {	//; Update colors first	ldy #NUM_FREQUENCY_BARS  ; Load Y Register
!colorLoop:	dey  ; Decrement Y
	bmi !colorsDone+  ; Branch if Minus
	ldx smoothedHeights, y  ; Load X Register
	lda heightToColor, x  ; Load Accumulator
	cmp previousColors, y  ; Compare with A
	beq !colorLoop-  ; Branch if Equal
	sta previousColors, y  ; Store Accumulator
	//; Update main bars	.for (var line = 0; line < TOP_SPECTRUM_HEIGHT; line++) {		sta $d800 + ((SPECTRUM_START_LINE + line) * 40) + ((40 - NUM_FREQUENCY_BARS) / 2), y  ; Store Accumulator
	}	//; Update reflection with darker color	tax  ; Transfer A to X
	lda darkerColorMap, x  ; Load Accumulator
	.for (var line = 0; line < BOTTOM_SPECTRUM_HEIGHT; line++) {		sta $d800 + ((SPECTRUM_START_LINE + TOP_SPECTRUM_HEIGHT + BOTTOM_SPECTRUM_HEIGHT - 1 - line) * 40) + ((40 - NUM_FREQUENCY_BARS) / 2), y  ; Store Accumulator
	}	jmp !colorLoop-  ; Jump
!colorsDone:	//; Render to appropriate screen buffer	lda currentScreenBuffer  ; Load Accumulator
	beq !renderScreen1+  ; Branch if Equal
	//; Render to screen 0	jmp RenderToScreen0  ; Jump
!renderScreen1:	//; Render to screen 1	jmp RenderToScreen1  ; Jump
}//; Screen-specific rendering routinesRenderToScreen0: {	ldy #NUM_FREQUENCY_BARS  ; Load Y Register
!loop:	dey  ; Decrement Y
	bpl !continue+  ; Branch if Plus
	rts  ; Return from Subroutine
!continue:	lda smoothedHeights, y  ; Load Accumulator
	cmp previousHeightsScreen0, y  ; Compare with A
	beq !loop-  ; Branch if Equal
	sta previousHeightsScreen0, y  ; Store Accumulator
	tax  ; Transfer A to X
	//; Draw main bar	.for (var line = 0; line < TOP_SPECTRUM_HEIGHT; line++) {		lda barCharacterMap - MAIN_BAR_OFFSET + (line * 8), x  ; Load Accumulator
		sta SCREEN_0_ADDRESS + ((SPECTRUM_START_LINE + line) * 40) + ((40 - NUM_FREQUENCY_BARS) / 2), y  ; Store Accumulator
	}	//; Draw reflection	txa  ; Transfer X to A
	lsr	tax  ; Transfer A to X
	.for (var line = 0; line < BOTTOM_SPECTRUM_HEIGHT; line++) {		lda barCharacterMap - REFLECTION_OFFSET + (line * 8), x  ; Load Accumulator
		clc  ; Clear Carry
		adc #10		sta SCREEN_0_ADDRESS + ((SPECTRUM_START_LINE + TOP_SPECTRUM_HEIGHT + BOTTOM_SPECTRUM_HEIGHT - 1 - line) * 40) + ((40 - NUM_FREQUENCY_BARS) / 2), y  ; Store Accumulator
	}	jmp !loop-  ; Jump
}RenderToScreen1: {	ldy #NUM_FREQUENCY_BARS  ; Load Y Register
!loop:	dey  ; Decrement Y
	bpl !continue+  ; Branch if Plus
	rts  ; Return from Subroutine
!continue:	lda smoothedHeights, y  ; Load Accumulator
	cmp previousHeightsScreen1, y  ; Compare with A
	beq !loop-  ; Branch if Equal
	sta previousHeightsScreen1, y  ; Store Accumulator
	tax  ; Transfer A to X
	//; Draw main bar	.for (var line = 0; line < TOP_SPECTRUM_HEIGHT; line++) {		lda barCharacterMap - MAIN_BAR_OFFSET + (line * 8), x  ; Load Accumulator
		sta SCREEN_1_ADDRESS + ((SPECTRUM_START_LINE + line) * 40) + ((40 - NUM_FREQUENCY_BARS) / 2), y  ; Store Accumulator
	}	//; Draw reflection	txa  ; Transfer X to A
	lsr	tax  ; Transfer A to X
	.for (var line = 0; line < BOTTOM_SPECTRUM_HEIGHT; line++) {		lda barCharacterMap - REFLECTION_OFFSET + (line * 8), x  ; Load Accumulator
		clc  ; Clear Carry
		adc #20		sta SCREEN_1_ADDRESS + ((SPECTRUM_START_LINE + TOP_SPECTRUM_HEIGHT + BOTTOM_SPECTRUM_HEIGHT - 1 - line) * 40) + ((40 - NUM_FREQUENCY_BARS) / 2), y  ; Store Accumulator
	}	jmp !loop-  ; Jump
}//; =============================================================================//; COLOR MANAGEMENT//; =============================================================================UpdateColors: {	//; Update color cycling on 256-frame boundaries	lda frameCounter  ; Load Accumulator
	bne !done+  ; Branch if Not Equal
	inc frame256Counter  ; Increment Memory
	lda #$00  ; Load Accumulator
	sta colorUpdateIndex  ; Store Accumulator
	//; Cycle to next palette	ldx currentPalette  ; Load X Register
	inx  ; Increment X
	cpx #NUM_COLOR_PALETTES  ; Compare with X
	bne !setPalette+  ; Branch if Not Equal
	ldx #$00  ; Load X Register
!setPalette:	stx currentPalette  ; Store X Register
	//; Update palette pointers	lda colorPalettesLo, x  ; Load Accumulator
	sta !readColor+ + 1  ; Store Accumulator
	lda colorPalettesHi, x  ; Load Accumulator
	sta !readColor+ + 2  ; Store Accumulator
!done:	//; Gradual color update	ldx colorUpdateIndex  ; Load X Register
	bmi !exit+  ; Branch if Minus
	lda #$0b							//; Default color	ldy heightToColorIndex, x  ; Load Y Register
	bmi !useDefault+  ; Branch if Minus
!readColor:	lda colorPalettes, y  ; Load Accumulator
!useDefault:	sta heightToColor, x  ; Store Accumulator
	inc colorUpdateIndex  ; Increment Memory
	lda colorUpdateIndex  ; Load Accumulator
	cmp #MAX_BAR_HEIGHT + 5  ; Compare with A
	bne !exit+  ; Branch if Not Equal
	lda #$ff  ; Load Accumulator
	sta colorUpdateIndex  ; Store Accumulator
!exit:	rts  ; Return from Subroutine
}//; =============================================================================//; SPRITE ANIMATION//; =============================================================================UpdateSprites: {	ldx spriteAnimationIndex  ; Load X Register
	//; Update X positions from sine table	lda spriteSineTable, x  ; Load Accumulator
	.for (var i = 0; i < 8; i++) {		sta $d000 + (i * 2)  ; Voice 1 Frequency Low
		.if (i != 7) {			clc  ; Clear Carry
			adc #$30					//; 48 pixels between sprites		}	}	ldy #$c0  ; Load Y Register
	lda $d000 + (5 * 2)  ; Voice 1 Frequency Low
	bmi !skip+  ; Branch if Minus
	ldy #$e0  ; Load Y Register
!skip:	sty $d010  ; Voice 1 Frequency High
	//; Update sprite pointers	lda frameCounter  ; Load Accumulator
	lsr	lsr	and #$07  ; Logical AND
	ora #SPRITE_BASE_INDEX  ; Logical OR
	.for (var i = 0; i < 8; i++) {		sta SPRITE_POINTERS_0 + i  ; Store Accumulator
		sta SPRITE_POINTERS_1 + i  ; Store Accumulator
	}	clc  ; Clear Carry
	lda spriteAnimationIndex  ; Load Accumulator
	adc #$01	and #$7f  ; Logical AND
	sta spriteAnimationIndex  ; Store Accumulator
	rts  ; Return from Subroutine
}//; =============================================================================//; UTILITY FUNCTIONS//; =============================================================================ClearScreens: {	lda #$20  ; Load Accumulator
	ldx #$00  ; Load X Register
!loop:	.for (var i = 0; i < 4; i++)	{		sta $d800 + (i * $100), x  ; Store Accumulator
		sta SCREEN_0_ADDRESS + (i * $100), x  ; Store Accumulator
		sta SCREEN_1_ADDRESS + (i * $100), x  ; Store Accumulator
	}	inx  ; Increment X
	bne !loop-  ; Branch if Not Equal
	//; Calculate how many bytes to copy	.const LOGO_BYTES = LOGO_HEIGHT * 40	.const FULL_PAGES = floor(LOGO_BYTES / 256)	.const REMAINING_BYTES = mod(LOGO_BYTES, 256)	//; Copy the logo data	ldx #0  ; Load X Register
	//; Copy full pages	.if (FULL_PAGES > 0) {		!loop:		.for (var page = 0; page < FULL_PAGES; page++) {			lda COLOR_COPY_DATA + (page * $100), x  ; Load Accumulator
			sta $d800 + (page * $100), x  ; Store Accumulator
			lda SCREEN_COPY_DATA + (page * $100), x  ; Load Accumulator
			sta SCREEN_0_ADDRESS + (page * $100), x  ; Store Accumulator
			sta SCREEN_1_ADDRESS + (page * $100), x  ; Store Accumulator
			inx  ; Increment X
			bne !loop-  ; Branch if Not Equal
		}	}	//; Copy remaining bytes	.if (REMAINING_BYTES > 0) {		!loop:			lda COLOR_COPY_DATA + (FULL_PAGES * $100), x  ; Load Accumulator
			sta $d800 + (FULL_PAGES * $100), x  ; Store Accumulator
			lda SCREEN_COPY_DATA + (FULL_PAGES * $100), x  ; Load Accumulator
			sta SCREEN_0_ADDRESS + (FULL_PAGES * $100), x  ; Store Accumulator
			sta SCREEN_1_ADDRESS + (FULL_PAGES * $100), x  ; Store Accumulator
			inx  ; Increment X
			cpx #REMAINING_BYTES  ; Compare with X
			bne !loop-  ; Branch if Not Equal
	}	rts  ; Return from Subroutine
}DisplaySongInfo: {	//; Setup title colors	ldx #79  ; Load X Register
!loop:	lda #$01							//; White for title	sta $d800 + (SONG_TITLE_LINE * 40), x  ; Store Accumulator
//	lda #$0f							//; Light gray for artist//	sta $d800 + (ARTIST_NAME_LINE * 40), x	dex  ; Decrement X
	bpl !loop-  ; Branch if Plus
	//; Display song title	ldy #0  ; Load Y Register
!titleLoop:	lda songTitle, y  ; Load Accumulator
	beq !titleDone+  ; Branch if Equal
	sta SCREEN_0_ADDRESS + (SONG_TITLE_LINE * 40) + ((40 - SONG_TITLE_LENGTH) / 2), y  ; Store Accumulator
	sta SCREEN_1_ADDRESS + (SONG_TITLE_LINE * 40) + ((40 - SONG_TITLE_LENGTH) / 2), y  ; Store Accumulator
	ora #$80							//; Reversed for second line	sta SCREEN_0_ADDRESS + ((SONG_TITLE_LINE + 1) * 40) + ((40 - SONG_TITLE_LENGTH) / 2), y  ; Store Accumulator
	sta SCREEN_1_ADDRESS + ((SONG_TITLE_LINE + 1) * 40) + ((40 - SONG_TITLE_LENGTH) / 2), y  ; Store Accumulator
	iny  ; Increment Y
	cpy #40  ; Compare with Y
	bne !titleLoop-  ; Branch if Not Equal
!titleDone:	//; Display artist name//	ldy #0//!artistLoop://	lda artistName, y//	beq !artistDone+//	sta SCREEN_0_ADDRESS + (ARTIST_NAME_LINE * 40) + ((40 - ARTIST_NAME_LENGTH) / 2), y//	sta SCREEN_1_ADDRESS + (ARTIST_NAME_LINE * 40) + ((40 - ARTIST_NAME_LENGTH) / 2), y//	ora #$80							//; Reversed for second line//	sta SCREEN_0_ADDRESS + ((ARTIST_NAME_LINE + 1) * 40) + ((40 - ARTIST_NAME_LENGTH) / 2), y//	sta SCREEN_1_ADDRESS + ((ARTIST_NAME_LINE + 1) * 40) + ((40 - ARTIST_NAME_LENGTH) / 2), y//	iny//	cpy #40//	bne !artistLoop-//!artistDone:	rts  ; Return from Subroutine
}InitializeColors: {	//; Initialize bar colors	ldx #0  ; Load X Register
!loop:	lda #$0b							//; Default cyan	ldy heightToColorIndex, x  ; Load Y Register
	bmi !useDefault+  ; Branch if Minus
	lda colorPalettes, y  ; Load Accumulator
!useDefault:	sta heightToColor, x  ; Store Accumulator
	inx  ; Increment X
	cpx #MAX_BAR_HEIGHT + 5  ; Compare with X
	bne !loop-  ; Branch if Not Equal
	rts  ; Return from Subroutine
}SetupMusic: {	//; Clear SID	ldy #24  ; Load Y Register
	lda #$00  ; Load Accumulator
!loop:	sta $d400, y  ; Voice 1 Frequency Low
	dey  ; Decrement Y
	bpl !loop-  ; Branch if Plus
	//; Initialize player	lda #$00  ; Load Accumulator
	jmp SIDInit  ; Jump
}//; =============================================================================//; DATA SECTION - VIC Configuration//; =============================================================================VICConfigStart:	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 0 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 1 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 2 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 3 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 4 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 5 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 6 X,Y	.byte $00, REFLECTION_SPRITES_YVAL	//; Sprite 7 X,Y	.byte $00							//; Sprite X MSB	.byte SKIP_REGISTER					//; D011	.byte SKIP_REGISTER					//; D012	.byte SKIP_REGISTER					//; D013	.byte SKIP_REGISTER					//; D014	.byte $ff							//; Sprite enable	.byte $18							//; D016	.byte $00							//; Sprite Y expand	.byte D018_VALUE_BITMAP				//; Memory setup	.byte SKIP_REGISTER					//; D019	.byte SKIP_REGISTER					//; D01A	.byte $00							//; Sprite priority	.byte $00							//; Sprite multicolor	.byte $ff							//; Sprite X expand	.byte $00							//; Sprite-sprite collision	.byte $00							//; Sprite-background collision	.byte $00							//; Border color	.byte $00							//; Background color	.byte $00, $00						//; Extra colors	.byte $00, $00, $00					//; Sprite extra colors	.byte $00, $00, $00, $00			//; Sprite colors 0-3	.byte $00, $00, $00, $00			//; Sprite colors 4-7VICConfigEnd://; =============================================================================//; DATA SECTION - Animation State//; =============================================================================visualizationUpdateFlag:	.byte $00frameCounter:				.byte $00frame256Counter:			.byte $00currentScreenBuffer:		.byte $00spriteAnimationIndex:		.byte $00colorUpdateIndex:			.byte $00currentPalette:				.byte $00D018Values:					.byte D018_VALUE_0, D018_VALUE_1//; =============================================================================//; DATA SECTION - Bar State//; =============================================================================barHeightsLo:				.fill NUM_FREQUENCY_BARS, 0barVoiceMap:				.fill NUM_FREQUENCY_BARS, 0previousHeightsScreen0:		.fill NUM_FREQUENCY_BARS, 255previousHeightsScreen1:		.fill NUM_FREQUENCY_BARS, 255previousColors:				.fill NUM_FREQUENCY_BARS, 255.byte $00, $00barHeights:					.fill NUM_FREQUENCY_BARS, 0.byte $00, $00smoothedHeights:			.fill NUM_FREQUENCY_BARS, 0//; =============================================================================//; DATA SECTION - Voice State//; =============================================================================voiceReleaseHi:				.fill 3, 0voiceReleaseLo:				.fill 3, 0sidRegisterMirror:			.fill 32, 0//; =============================================================================//; DATA SECTION - Calculations//; =============================================================================.align 128div16:						.fill 128, i / 16.0div16mul3:					.fill 128, (3 * i) / 16.0multiply64Table:			.fill 4, i * 64//; Color tablesdarkerColorMap:				.byte $00, $0c, $09, $0e, $06, $09, $0b, $08							.byte $02, $0b, $02, $0b, $0b, $05, $06, $0c//; =============================================================================//; DATA SECTION - Color Palettes//; =============================================================================colorPalettes:	.byte $09, $04, $05, $05, $0d, $0d, $0f, $01		//; Purple/pink	.byte $09, $06, $0e, $0e, $03, $03, $0f, $01		//; Blue/cyan	.byte $09, $02, $0a, $0a, $07, $07, $0f, $01		//; Red/orangecolorPalettesLo:			.fill NUM_COLOR_PALETTES, <(colorPalettes + i * COLORS_PER_PALETTE)colorPalettesHi:			.fill NUM_COLOR_PALETTES, >(colorPalettes + i * COLORS_PER_PALETTE)heightToColorIndex:			.byte $ff							.fill MAX_BAR_HEIGHT + 4, max(0, min(floor(((i * COLORS_PER_PALETTE) + (random() * (MAX_BAR_HEIGHT * 0.8) - (MAX_BAR_HEIGHT * 0.4))) / MAX_BAR_HEIGHT), COLORS_PER_PALETTE - 1))heightToColor:				.fill MAX_BAR_HEIGHT + 5, $0b//; =============================================================================//; DATA SECTION - Display Mapping//; =============================================================================	.align 256	.fill MAX_BAR_HEIGHT, 224barCharacterMap:	.fill 8, 225 + i	.fill MAX_BAR_HEIGHT, 233//; =============================================================================//; DATA SECTION - Animation Data//; =============================================================================spriteSineTable:			.fill 128, 11.5 + 11.5*sin(toRadians(i*360/128))//; =============================================================================//; DATA SECTION - Song Information//; =============================================================================songTitle:					.text SIDName.substring(0, SONG_TITLE_LENGTH)							.byte 0//artistName:					.text SIDAuthor.substring(0, ARTIST_NAME_LENGTH)//							.byte 0SCREEN_COPY_DATA:	.fill LOGO_HEIGHT * 40, file_logo.getScreenRam(i)COLOR_COPY_DATA:	.fill LOGO_HEIGHT * 40, file_logo.getColorRam(i)//; =============================================================================//; INCLUDES//; =============================================================================#if USE_MANUAL_SID_REGISTER_MIRRORING.import source "../INC/MemoryPreservation.asm"#endif // USE_MANUAL_SID_REGISTER_MIRRORING.import source "../INC/NMIFix.asm".import source "../INC/StableRasterSetup.asm".align 256.import source "../INC/FreqTable.asm"//; =============================================================================//; SPRITE DATA//; =============================================================================* = SPRITES_ADDRESS "Water Sprites"	.fill file_waterSpritesData.getSize(), file_waterSpritesData.get(i)//; =============================================================================//; CHARSET DATA//; =============================================================================* = CHARSET_ADDRESS "Font"	.fill min($700, file_charsetData.getSize()), file_charsetData.get(i)* = CHARSET_ADDRESS + (224 * 8) "Bar Chars"//; First, the chars for the main bar	.byte $00, $00, $00, $00, $00, $00, $00, $00	.byte $00, $00, $00, $00, $00, $00, $00, $7C	.byte $00, $00, $00, $00, $00, $00, $7C, $BE	.byte $00, $00, $00, $00, $00, $7C, $BE, $BE	.byte $00, $00, $00, $00, $7C, $14, $BE, $BE	.byte $00, $00, $00, $7C, $BE, $14, $BE, $BE	.byte $00, $00, $7C, $BE, $BE, $14, $BE, $BE	.byte $00, $7C, $BE, $BE, $BE, $14, $BE, $BE	.byte $7C, $14, $BE, $BE, $BE, $14, $BE, $BE	.byte $BE, $14, $BE, $BE, $BE, $14, $BE, $BE//; reflection chars - frame 1 is &55 (for flicker)	.byte $00, $00, $00, $00, $00, $00, $00, $00	.byte $54, $00, $00, $00, $00, $00, $00, $00	.byte $aa, $54, $00, $00, $00, $00, $00, $00	.byte $54, $aa, $54, $00, $00, $00, $00, $00	.byte $aa, $54, $aa, $54, $00, $00, $00, $00	.byte $54, $aa, $54, $aa, $54, $00, $00, $00	.byte $aa, $54, $aa, $54, $aa, $54, $00, $00	.byte $54, $aa, $54, $aa, $54, $aa, $54, $00	.byte $aa, $54, $aa, $54, $aa, $54, $aa, $54	.byte $54, $aa, $54, $aa, $54, $aa, $54, $aa//; reflection chars - frame 2 is &AA (for flicker)	.byte $00, $00, $00, $00, $00, $00, $00, $00	.byte $aa, $00, $00, $00, $00, $00, $00, $00	.byte $54, $aa, $00, $00, $00, $00, $00, $00	.byte $aa, $54, $aa, $00, $00, $00, $00, $00	.byte $54, $aa, $54, $aa, $00, $00, $00, $00	.byte $aa, $54, $aa, $54, $aa, $00, $00, $00	.byte $54, $aa, $54, $aa, $54, $aa, $00, $00	.byte $aa, $54, $aa, $54, $aa, $54, $54, $00	.byte $54, $aa, $54, $aa, $54, $aa, $54, $aa	.byte $aa, $54, $aa, $54, $aa, $54, $aa, $54//; =============================================================================//; BITMAP DATA//; =============================================================================* = BITMAP_ADDRESS "Bitmap"	.fill LOGO_HEIGHT * (40 * 8), file_logo.getBitmap(i)//; =============================================================================//; END OF FILE//; =============================================================================