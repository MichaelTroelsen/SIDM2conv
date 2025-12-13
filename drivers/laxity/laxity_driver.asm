; ============================================================================
; Laxity SF2 Driver Wrapper
; ============================================================================
; Wraps the relocated Laxity NewPlayer v21 for SID Factory II compatibility
;
; Memory Map:
;   $0D7E-$0DFF: This wrapper (~130 bytes)
;   $0E00-$16FF: Relocated Laxity player (from $1000, offset -$0200)
;   $1700-$18FF: SF2 header blocks
;   $1900+:      Music data (orderlists, tables)
;
; Author: SIDM2 Project
; Date: 2025-12-13
; ============================================================================

.cpu "6502"

; ============================================================================
; Constants
; ============================================================================

; SF2 Standard Addresses
SF2_LOAD_ADDR       = $0D7E     ; Standard SF2 load address
SF2_FILE_ID         = $1337     ; SF2 file identification marker

; Relocated Laxity Addresses (original + offset -$0200)
LAXITY_INIT         = $0E00     ; Init routine (was $1000)
LAXITY_PLAY         = $0EA1     ; Play routine (was $10A1)

; Laxity Player Data Addresses (relocated)
LAXITY_TEMPO        = $0F83     ; Tempo counter (was $1183)
LAXITY_STATUS       = $0F81     ; Player status (was $1181)

; SID Chip Registers
SID_BASE            = $D400
SID_FREQ_LO1        = SID_BASE + $00
SID_FREQ_HI1        = SID_BASE + $01
SID_PW_LO1          = SID_BASE + $02
SID_PW_HI1          = SID_BASE + $03
SID_CONTROL1        = SID_BASE + $04
SID_AD1             = SID_BASE + $05
SID_SR1             = SID_BASE + $06

SID_FREQ_LO2        = SID_BASE + $07
SID_FREQ_HI2        = SID_BASE + $08
SID_CONTROL2        = SID_BASE + $0B
SID_AD2             = SID_BASE + $0C
SID_SR2             = SID_BASE + $0D

SID_FREQ_LO3        = SID_BASE + $0E
SID_FREQ_HI3        = SID_BASE + $0F
SID_CONTROL3        = SID_BASE + $12
SID_AD3             = SID_BASE + $13
SID_SR3             = SID_BASE + $14

SID_FILTER_FC_LO    = SID_BASE + $15
SID_FILTER_FC_HI    = SID_BASE + $16
SID_FILTER_RES_FILT = SID_BASE + $17
SID_FILTER_MODE_VOL = SID_BASE + $18


; ============================================================================
; SF2 Driver Header
; ============================================================================

* = SF2_LOAD_ADDR

; SF2 File ID (must be first!)
.word SF2_FILE_ID           ; $1337 - SF2 identification marker

; SF2 Driver Entry Points (standard offsets)
sf2_init:
    jmp init_routine        ; +$02: Init entry point
sf2_play:
    jmp play_routine        ; +$05: Play entry point
sf2_stop:
    jmp stop_routine        ; +$08: Stop entry point


; ============================================================================
; Init Routine
; ============================================================================
; Called by SF2 to initialize the player
; Input: A = song number (0-based)
; ============================================================================

init_routine:
    ; Store song number (Laxity uses X register)
    tax

    ; Silence SID chip before init
    jsr silence_sid

    ; Call relocated Laxity init routine
    ; (Laxity init expects song number in X)
    jsr LAXITY_INIT

    ; Return
    rts


; ============================================================================
; Play Routine
; ============================================================================
; Called every frame (50Hz PAL / 60Hz NTSC) by SF2
; ============================================================================

play_routine:
    ; Check if player is active
    lda LAXITY_STATUS
    bmi _play               ; Bit 7 = player active
    rts                     ; Not active, return

_play:
    ; Call relocated Laxity play routine
    jsr LAXITY_PLAY
    rts


; ============================================================================
; Stop Routine
; ============================================================================
; Called by SF2 to stop playback
; ============================================================================

stop_routine:
    ; Mark player as inactive
    lda #$00
    sta LAXITY_STATUS

    ; Silence SID chip
    jsr silence_sid

    rts


; ============================================================================
; Silence SID Chip
; ============================================================================
; Silences all three SID voices and resets filters
; ============================================================================

silence_sid:
    ; Gate off all voices
    lda #$00
    sta SID_CONTROL1
    sta SID_CONTROL2
    sta SID_CONTROL3

    ; Clear frequencies
    sta SID_FREQ_LO1
    sta SID_FREQ_HI1
    sta SID_FREQ_LO2
    sta SID_FREQ_HI2
    sta SID_FREQ_LO3
    sta SID_FREQ_HI3

    ; Clear pulse widths
    sta SID_PW_LO1
    sta SID_PW_HI1

    ; Set ADSR to instant (fast decay)
    lda #$00
    sta SID_AD1
    sta SID_SR1
    sta SID_AD2
    sta SID_SR2
    sta SID_AD3
    sta SID_SR3

    ; Clear filter
    lda #$00
    sta SID_FILTER_FC_LO
    sta SID_FILTER_FC_HI
    sta SID_FILTER_RES_FILT

    ; Set volume to 0
    sta SID_FILTER_MODE_VOL

    rts


; ============================================================================
; Padding to end of wrapper space
; ============================================================================
; Ensure wrapper doesn't exceed $0DFF
; ============================================================================

.if (* > $0DFF)
    .error "Wrapper code exceeds $0DFF! Size: ", * - SF2_LOAD_ADDR, " bytes"
.endif

; Fill rest of wrapper space with zeros up to $0E00
; (where relocated Laxity player begins)
.fill ($0E00 - *), $00

; ============================================================================
; Relocated Laxity Player Binary
; ============================================================================
; The relocated player binary will be inserted here during build
; Address: $0E00-$16FF (3328 bytes)
; ============================================================================

* = $0E00
relocated_player:
    ; Placeholder - will be replaced with actual relocated binary
    .binary "laxity_player_relocated.bin"


; ============================================================================
; SF2 Header Blocks
; ============================================================================
; Metadata for SF2 editor integration
; Address: $1700+ (~69 bytes)
; ============================================================================

* = $1700
sf2_header:
    ; Placeholder - will be replaced with actual header binary
    .binary "laxity_driver_header.bin"


; ============================================================================
; Music Data Area
; ============================================================================
; Reserved space for song data (orderlists, sequences, tables)
; Address: $1900+ (variable size)
; ============================================================================

* = $1900
music_data:
    ; This will be populated by the conversion process
    ; Contains:
    ; - Orderlists (3 tracks)
    ; - Sequences (packed note data)
    ; - Instrument table (already in relocated player at $186B)
    ; - Wave table (already in relocated player at $18CB)
    ; - Pulse table (already in relocated player at $183B)
    ; - Filter table (already in relocated player at $181E)


; ============================================================================
; Build Information
; ============================================================================
; Wrapper size:        130 bytes (approx)
; Wrapper load addr:   $0D7E
; Player start:        $0E00
; Player size:         3328 bytes
; Header start:        $1700
; Header size:         69 bytes
; Music data start:    $1900
; ============================================================================
