; Laxity SF2 Driver Wrapper
; Wraps relocated Laxity NewPlayer v21 with SF2 interface
;
; Memory Layout:
; $0D7E-$0DFF   SF2 Wrapper (130 bytes)
; $0E00-$16FF   Relocated Laxity Player (2.3 KB)
; $1700-$18FF   SF2 Header Blocks (512 bytes)
; $1900+        Music Data

*=$0D7E

; SF2 Driver Entry Points
; These addresses are fixed for SF2 compatibility

; Init routine ($0D7E)
; Initializes SID and Laxity player
sf2_init:
    ; Initialize SID chip
    LDA #$00
    STA $D418           ; Master volume off
    
    ; Initialize all voice control registers
    LDA #$00
    STA $D404           ; Voice 1 Control
    STA $D40B           ; Voice 2 Control
    STA $D412           ; Voice 3 Control
    
    ; Call relocated Laxity init routine at $0E00
    JSR $0E00           ; Laxity init
    
    RTS

; Padding to $0D81
.align $0D81

; Play routine ($0D81)
; Executes one frame of music
sf2_play:
    ; Call relocated Laxity play routine
    ; Laxity play entry was originally at $10A1
    ; After relocation to $0E00, it's at $0E00 + ($10A1 - $1000) = $0EA1
    JSR $0EA1           ; Laxity play
    
    RTS

; Padding to $0D84
.align $0D84

; Stop routine ($0D84)
; Stops music and silences SID
sf2_stop:
    ; Silence all voices
    LDA #$00
    STA $D404           ; Voice 1 Control
    STA $D40B           ; Voice 2 Control
    STA $D412           ; Voice 3 Control
    
    ; Kill all oscillators
    LDA #$00
    STA $D418           ; Master volume off
    
    RTS

; Fill to end of wrapper
.align $0E00
