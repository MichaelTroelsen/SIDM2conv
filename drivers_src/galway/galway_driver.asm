; ==========================================================================
; Galway SF2 driver — B2/B3: 3-voice sequencer with orderlist chaining
; ==========================================================================
; Native SID Factory II driver (descriptor type 0x00). Three voices, each
; walking its own ORDERLIST (a list of pattern indices + transpose) -> the
; sequence-pointer table -> packed sequences (notes/instruments/durations).
; Plays arbitrary multi-pattern songs. Galway's real FM/PM synth comes next.
;
; Build: py -3 bin/build_galway_driver_full.py
; ==========================================================================
        .cpu "6502"

SID         = $d400
SID_VOL     = $d418

; per-voice state (indexed 0..2)
vsp_lo      = $e0           ; current sequence ptr lo
vsp_hi      = $e3           ; current sequence ptr hi
vwf         = $e6           ; current waveform byte
vhold       = $e9           ; sustain countdown (rows to hold)
vol_lo      = $c0           ; orderlist read ptr lo
vol_hi      = $c3           ; orderlist read ptr hi
vtrans      = $c6           ; current transpose offset (signed)
vpwbase     = $b0           ; $b0,$b1,$b2  per-voice pulse-width base (hi byte)
vfreq_lo    = $d0           ; $d0,$d1,$d2  per-voice base note frequency lo
vfreq_hi    = $d3           ; $d3,$d4,$d5  per-voice base note frequency hi
vib_phase   = $d6           ; $d6,$d7,$d8  per-voice vibrato phase
vib_delay   = $d9           ; $d9,$da,$db  frames before vibrato starts
VIBSPD   = $10           ; vibrato phase increment per frame
VIBDLY   = $0c           ; delay (frames) before vibrato kicks in
; scratch
wptr        = $fa           ; working pointer (seq / orderlist)
tmpf        = $f6           ; freq/ADSR temp (lo/hi)
widx        = $f5           ; wave-index temp
pending_dur = $f4           ; duration parsed this event
np_guard    = $f3           ; orderlist-walk guard (anti-runaway)
sidoff      = $f8           ; SID register offset for current voice
zp_guard    = $f9           ; sequence-parse guard (anti-runaway)
zp_tcnt     = $fc           ; shared tempo countdown
; pulse-width modulation: faithful to Galway — the 12-bit pulse HI byte is FIXED
; at the instrument's base and the LO byte sweeps as a triangle. Matches the real
; Wizball trace (pw_hi $08 held; pw_lo ramps +8/frame), not the old coarse
; hi-nibble swing. Per-voice current-lo + sweep direction.
pw_lo       = $b3           ; $b3,$b4,$b5  per-voice current pulse-width lo
pw_dir      = $b6           ; $b6,$b7,$b8  0 = sweeping up, 1 = down
PWSTEP   = $08           ; pulse-width lo delta per frame (Galway uses +8)
PWMIN    = $08
PWMAX    = $f8
; --- filter (one global SID resource): high-resonance low-pass with a downward
;     cutoff sweep that RESTARTS on each routed-voice note. Tuned to Galway's
;     real Wizball filter (res $F, voice-1 routed, LP, cutoff $8900->$7300). ---
filt_lo     = $bc           ; 16-bit current cutoff lo
filt_hi     = $bd           ; 16-bit current cutoff hi (high byte -> $D416)
FILT_RES   = $f0         ; resonance (high nibble of $D417 res_control)
FILT_ROUTE = $01         ; voices routed to the filter (bit n = voice n); v0 lead
FILT_MODE  = $10         ; low-pass mode (OR'd into $D418 with the volume nibble)
FILTTOP    = $8900       ; cutoff sweep start (reset on each routed note)
FILTBOT    = $7300       ; cutoff sweep floor
FILTSTEP   = $00c0       ; cutoff decrement per frame (16-bit; ~0.75 hi/frame)
; --- wave program runner (STANDARD SF2II wave table, col-major 256x2:
;     col0=waveform byte, col1=semitone(00-7f add / 80-df abs) or jump-target;
;     one row advanced per frame; col0 $7f = jump to col1 index). The editor
;     renders these programs and the driver plays them. State in scratch RAM
;     ($1800-$18xx, free between the driver end and the edit area). -----------
VWI     = $1800          ; per-voice current wave-program row (3)
VGMASK  = $1803          ; per-voice $D404 AND-mask: $ff gated-on, $fe gated-off (3)
VIWAVE  = $1806          ; per-voice instrument wave-program start row (3)
ws_row  = $ee            ; wave_step scratch: resolved row
ws_grd  = $ef            ; wave_step scratch / pulse_step $7f-jump guard
; --- pulse program runner (STANDARD SF2II pulse table, col-major 256x3:
;     8X XX YY = set 12-bit width (X|XX) for YY frames; 0X XX YY = add (X|XX) to
;     width each frame for YY; 7f -- XX = jump (self = end). Replaces the old
;     hand-tuned PWM; editor renders the programs and the driver plays them. ---
VPI     = $1809          ; per-voice pulse-program row (3)
VPC     = $180c          ; per-voice frames left on current row (3)
VPLO    = $180f          ; per-voice current 12-bit pulse lo (3)
VPHI    = $1812          ; per-voice current 12-bit pulse hi (3)
VPADL   = $1815          ; per-voice per-frame add lo (3)
VPADH   = $1818          ; per-voice per-frame add hi (3)
VIPULSE = $181b          ; per-voice instrument pulse-program start row (3)
; --- filter program runner (STANDARD SF2II filter table, col-major 256x3:
;     9Y YY RB = set passband/cutoff/res/bitmask; 0X XX YY = add to cutoff each
;     frame for YY; 7f -- XX = jump. ONE global SID filter; started when a note
;     from an instrument with flag $40 triggers (filter index = instr col3).
;     Cutoff held as 16-bit F_CUT (high byte -> $D416). -----------------------
F_IDX   = $181e          ; filter-program row
F_CNT   = $181f          ; frames left on current row
F_CLO   = $1820          ; 16-bit cutoff lo
F_CHI   = $1821          ; 16-bit cutoff hi (-> $D416)
F_ADLO  = $1822          ; per-frame cutoff add lo
F_ADHI  = $1823          ; per-frame cutoff add hi
F_MODE  = $1824          ; SID mode bits for $D418 high nibble (from passband)
F_ACT   = $1825          ; 1 = a filter program is running
VIFLAGS = $1826          ; per-voice instrument flags byte (col2) (3)
VIFILT  = $1829          ; per-voice instrument filter-program start row (3)

        .include "layout.inc"
INSTR_AD    = INSTR + 0*32
INSTR_SR    = INSTR + 1*32
INSTR_FLAGS = INSTR + 2*32   ; flags ($40 = start filter program)
INSTR_FILT  = INSTR + 3*32   ; filter-program start row
INSTR_PULSE = INSTR + 4*32   ; pulse-program start row
INSTR_WAVE  = INSTR + 5*32

; --- Block-2 playback-state region (editor reads these) -------------------
ST_FIRST    = $16cc
ST_LAST     = $1702
ST_TICK     = $16db

        * = ST_FIRST
        .fill ST_LAST - ST_FIRST + 1, 0

; ==========================================================================
        * = $1000
drv_init:   jmp do_init
drv_play:   jmp do_play
drv_stop:   jmp do_stop

; --- INIT -----------------------------------------------------------------
do_init:
        ldx #$18
ci:     lda #$00
        sta SID,x
        dex
        bpl ci
        ldx #(ST_LAST - ST_FIRST)
cs:     lda #$00
        sta ST_FIRST,x
        dex
        bpl cs
        ldx #$02
iv:     lda #$41
        sta vwf,x
        lda #$00
        sta vhold,x
        sta vtrans,x
        lda #$00
        sta VWI,x                ; wave program starts at row 0
        sta VIWAVE,x
        sta vfreq_lo,x
        sta vfreq_hi,x
        sta VPI,x                ; pulse program: row 0, force reload (VPC=0)
        sta VPC,x
        sta VPLO,x
        sta VPHI,x
        sta VPADL,x
        sta VPADH,x
        sta VIPULSE,x
        lda #$fe
        sta VGMASK,x             ; start gated off
        lda #$ff
        sta vib_delay,x          ; no vibrato until a note triggers
        ; orderlist ptr = OL_x ; then load the first pattern
        lda ollo,x
        sta vol_lo,x
        lda olhi,x
        sta vol_hi,x
        jsr next_pattern         ; sets vsp[x] + vtrans[x] from the orderlist
        dex
        bpl iv
        lda #$00                 ; filter program idle until a flag-$40 note
        sta F_ACT
        sta F_MODE
        sta F_CLO
        sta F_CHI
        sta F_CNT
        lda #$01
        sta zp_tcnt
        rts

; --- PLAY -----------------------------------------------------------------
do_play:
        inc ST_TICK
        lda F_MODE               ; filter passband bits (from the filter program)
        ora #$0f                 ; + main volume
        sta SID_VOL
        jsr pulse_step           ; per-voice pulse-program -> $D402/3 each frame
        jsr filt_prog_step       ; global filter program -> $D415/6/7 + mode
        dec zp_tcnt
        bne dp_vib
        jsr do_row               ; row tick: step the sequencer
dp_vib:
        jsr vib_update           ; per-voice vibrato (frequency modulation)
        jsr wave_step            ; per-voice wave-program -> $D404 each frame
        rts

; --- per-voice wave-program runner: resolve $7f jumps, write $D404 = waveform &
;     gate-mask, advance one row. (Semitone offset deferred — Galway leads +0.) -
wave_step:
        ldx #$02
ws_l:
        ldy VWI,x
        lda #$08
        sta ws_grd
ws_read:
        lda WAVE,y               ; col0 = waveform (or $7f jump marker)
        cmp #$7f
        bne ws_have
        lda WAVE+256,y           ; col1 = jump target row
        tay
        dec ws_grd
        bne ws_read
        lda #$00                 ; $7f-loop guard tripped -> silence
        sty ws_row
        jmp ws_write
ws_have:
        sty ws_row               ; remember the resolved row
        and VGMASK,x             ; apply gate mask (on=$ff, off=$fe)
ws_write:
        ldy sidbase,x
        sta SID+4,y
        ldy ws_row               ; advance to the next row for next frame
        iny
        tya
        sta VWI,x
        dex
        bpl ws_l
        rts

; --- per-voice pulse-program runner: walk the standard pulse table (set/add/
;     jump), applying the per-frame add and writing $D402/3 each frame. --------
pulse_step:
        ldx #$02
pl_l:
        lda VPC,x
        bne pl_apply             ; still on current row -> just apply the add
        lda #$08
        sta ws_grd               ; $7f-jump guard
        ldy VPI,x
pl_read:
        lda PULSE,y              ; byte0 = cmd nibble | width-hi nibble
        cmp #$7f
        bne pl_decode
        sty tmpf                 ; jump row: target = byte2
        lda PULSE+512,y
        cmp tmpf
        beq pl_end               ; self-jump -> end (freeze)
        sta VPI,x                ; (STA abs,x is valid; STY abs,x is not)
        tay
        dec ws_grd
        bne pl_read
pl_end:
        lda #$00
        sta VPADL,x
        sta VPADH,x
        lda #$ff
        sta VPC,x
        jmp pl_apply
pl_decode:
        sta tmpf                 ; byte0
        lda PULSE+256,y          ; byte1 = width lo
        sta tmpf+1
        lda PULSE+512,y          ; byte2 = frame count
        sta VPC,x
        iny                      ; advance past this row
        tya
        sta VPI,x
        lda tmpf
        bmi pl_set               ; bit7 set -> 8X (set width)
        and #$0f                 ; 0X (add): VPAD = (byte0&0f):byte1
        sta VPADH,x
        lda tmpf+1
        sta VPADL,x
        jmp pl_apply
pl_set:
        lda tmpf                 ; 8X: pulse = (byte0&0f):byte1, add = 0
        and #$0f
        sta VPHI,x
        lda tmpf+1
        sta VPLO,x
        lda #$00
        sta VPADL,x
        sta VPADH,x
pl_apply:
        lda VPLO,x               ; pulse += add (12-bit)
        clc
        adc VPADL,x
        sta VPLO,x
        lda VPHI,x
        adc VPADH,x
        and #$0f
        sta VPHI,x
        lda VPC,x                ; consume a frame
        beq pl_wr
        dec VPC,x
pl_wr:
        ldy sidbase,x
        lda VPLO,x
        sta SID+2,y
        lda VPHI,x
        sta SID+3,y
        dex
        bmi pl_done              ; (bpl pl_l would branch too far -> use jmp)
        jmp pl_l
pl_done:
        rts

; --- global filter-program runner: walk the standard filter table (set passband/
;     cutoff/res/bitmask, add-to-cutoff, jump), writing $D415/6 (cutoff), $D417
;     (res+routing) and F_MODE (passband -> $D418 high nibble). Restarted by a
;     flag-$40 note (see pr_note). Cutoff held 16-bit, hi byte -> $D416. -------
filt_prog_step:
        lda F_ACT
        bne fp_run
        rts
fp_run:
        lda F_CNT
        beq fp_load              ; F_CNT==0 -> load next row
        jmp fp_apply             ; else just apply the per-frame add
fp_load:
        lda #$08
        sta ws_grd
        ldy F_IDX
fp_read:
        lda FILTER,y             ; byte0
        cmp #$7f
        bne fp_dec
        sty tmpf                 ; jump row: target = byte2
        lda FILTER+512,y
        cmp tmpf
        beq fp_freeze
        sta F_IDX
        tay
        dec ws_grd
        bne fp_read
fp_freeze:
        lda #$00
        sta F_ADLO
        sta F_ADHI
        lda #$ff
        sta F_CNT
        jmp fp_apply
fp_dec:
        cmp #$90
        bcs fp_set               ; byte0 >= $90 -> set-filter row
        ; --- 0X add-to-cutoff: F_AD = ((byte0&f):byte1) << 4 ---
        and #$0f
        sta tmpf+1               ; XXX hi nibble
        lda FILTER+256,y         ; byte1 = XXX low 8 bits
        pha
        asl
        asl
        asl
        asl
        sta F_ADLO               ; byte1 << 4
        pla
        lsr
        lsr
        lsr
        lsr                      ; byte1 >> 4
        sta tmpf
        lda tmpf+1
        asl
        asl
        asl
        asl                      ; (XXX hi) << 4
        ora tmpf
        sta F_ADHI
        lda FILTER+512,y         ; byte2 = frames
        sta F_CNT
        iny
        tya
        sta F_IDX
        jmp fp_apply
fp_set:
        ; --- 9Y YY RB set-filter: passband X, cutoff Y:byte1, res:bitmask byte2 ---
        sta tmpf                 ; byte0 = X:Y
        lsr
        lsr
        lsr
        lsr                      ; X (passband)
        and #$07
        asl
        asl
        asl
        asl                      ; (X&7) << 4 = SID mode bits
        sta F_MODE
        lda tmpf
        and #$0f                 ; Y = cutoff hi nibble
        asl
        asl
        asl
        asl                      ; Y << 4
        sta tmpf+1
        lda FILTER+256,y         ; byte1 = cutoff low 8 bits
        pha
        lsr
        lsr
        lsr
        lsr                      ; byte1 >> 4
        ora tmpf+1
        sta F_CHI                ; cutoff hi -> $D416
        pla
        asl
        asl
        asl
        asl
        sta F_CLO
        lda FILTER+512,y         ; byte2 = R:B -> res_control
        sta $d417
        lda #$00
        sta F_ADLO
        sta F_ADHI
        lda #$01
        sta F_CNT
        iny
        tya
        sta F_IDX
fp_apply:
        lda F_CLO                ; cutoff += add (16-bit)
        clc
        adc F_ADLO
        sta F_CLO
        lda F_CHI
        adc F_ADHI
        sta F_CHI
        lda F_CNT
        beq fp_write
        dec F_CNT
fp_write:
        lda F_CLO
        sta $d415
        lda F_CHI
        sta $d416
        rts

; --- per-voice vibrato: after a short delay, oscillate each voice's frequency
;     around its base note (a gentle triangle, +-~64) -------------------------
vib_update:
        ldx #$02
vu_l:   lda vib_delay,x
        beq vu_apply
        dec vib_delay,x
        jmp vu_next              ; still in delay: leave freq at base
vu_apply:
        lda vib_phase,x
        clc
        adc #VIBSPD
        sta vib_phase,x
        ; triangle magnitude 0..127 from the phase
        bpl vu_pos
        eor #$ff                 ; phase >= 128 -> 255-phase
vu_pos:
        sec
        sbc #$40                 ; centre -> signed delta -64..+63
        sta tmpf                 ; delta (signed byte)
        ldy sidbase,x
        clc                      ; freq = base + sign_extend(delta)
        adc vfreq_lo,x
        sta SID+0,y
        lda tmpf
        bmi vu_neg
        lda #$00
        jmp vu_hi
vu_neg: lda #$ff
vu_hi:  adc vfreq_hi,x
        sta SID+1,y
vu_next:
        dex
        bpl vu_l
        rts
do_row:
        lda #TEMPO
        sta zp_tcnt
        ldx #$00
vloop:
        lda vhold,x
        beq vparse
        dec vhold,x
        jmp vnext
vparse:
        lda sidbase,x
        sta sidoff
        lda vsp_lo,x
        sta wptr
        lda vsp_hi,x
        sta wptr+1
        lda #$20
        sta zp_guard
        lda #$00
        sta pending_dur
        jsr parse_one
        lda wptr
        sta vsp_lo,x
        lda wptr+1
        sta vsp_hi,x
        lda pending_dur
        sta vhold,x
vnext:
        inx
        cpx #$03
        bne vloop
        rts

; --- parse one packed event for voice X (sidoff/wptr set) -----------------
parse_one:
pr_read:
        dec zp_guard
        bne pr_go
        rts                      ; guard expired -> bail this row (suspends)
pr_go:
        ldy #$00
        lda (wptr),y
        cmp #$7f
        bne pr_cmd
        ; end of sequence -> advance the orderlist to the next pattern
        jsr next_pattern
        lda vsp_lo,x
        sta wptr
        lda vsp_hi,x
        sta wptr+1
        jmp pr_read
pr_cmd:
        cmp #$c0
        bcc pr_instr
        jsr advw                 ; command byte: skip
        jmp pr_read
pr_instr:
        cmp #$a0
        bcc pr_dur
        and #$1f
        jsr set_instr_v
        jsr advw
        jmp pr_read
pr_dur:
        cmp #$80
        bcc pr_note
        and #$0f
        sta pending_dur
        jsr advw
        jmp pr_read
pr_note:
        cmp #$00
        bne pn_not_off
        lda #$fe                 ; gate off: wave_step keeps writing gate-off
        sta VGMASK,x
        lda vwf,x
        and #$fe
        ldy sidoff
        sta SID+4,y
        jmp advw
pn_not_off:
        cmp #$7e
        beq advw
        cmp #$70
        bcs advw
        clc                      ; apply transpose
        adc vtrans,x
        asl
        tay
        lda freqtable,y
        sta tmpf
        lda freqtable+1,y
        sta tmpf+1
        lda tmpf                 ; remember the base freq for vibrato
        sta vfreq_lo,x
        lda tmpf+1
        sta vfreq_hi,x
        lda #$00
        sta vib_phase,x
        lda #VIBDLY
        sta vib_delay,x
        ldy sidoff
        lda tmpf
        sta SID+0,y
        lda tmpf+1
        sta SID+1,y
        lda vwf,x                ; retrigger: gate off then on
        and #$fe
        sta SID+4,y
        lda vwf,x
        ora #$01
        sta SID+4,y
        lda VIWAVE,x             ; restart the wave program at the instrument's row
        sta VWI,x
        lda #$ff
        sta VGMASK,x             ; gate on
        lda VIPULSE,x            ; restart the pulse program too
        sta VPI,x
        lda #$00
        sta VPC,x                ; force reload on the next frame
        lda VIFLAGS,x            ; flag $40 -> (re)start the filter program
        and #$40
        beq pn_nofilt
        lda VIFILT,x
        sta F_IDX
        lda #$00
        sta F_CNT                ; force reload next frame
        lda #$01
        sta F_ACT
pn_nofilt:
        jmp advw

pr_ret:
        rts

advw:
        inc wptr
        bne advw_done
        inc wptr+1
advw_done:
        rts

; --- advance voice X's orderlist to the next pattern: set vsp[x]+vtrans[x] --
next_pattern:
        lda #$20
        sta np_guard
        lda vol_lo,x             ; wptr = orderlist read pointer
        sta wptr
        lda vol_hi,x
        sta wptr+1
np_read:
        dec np_guard
        beq np_ret
        ldy #$00
        lda (wptr),y
        cmp #$ff
        beq np_ff
        cmp #$fe
        beq np_fe
        cmp #$80
        bcc np_seq
        ; transposition byte: offset = (val & $7f) - $20
        and #$7f
        sec
        sbc #$20
        sta vtrans,x
        jsr ol_adv
        jmp np_read
np_seq:
        ; sequence index -> vsp[x] from the seq pointer table
        tay
        lda SEQPTRLO,y
        sta vsp_lo,x
        lda SEQPTRHI,y
        sta vsp_hi,x
        jsr ol_adv               ; step past the index
        lda wptr                 ; save orderlist pointer back
        sta vol_lo,x
        lda wptr+1
        sta vol_hi,x
np_ret:
        rts
np_fe:
        ; end, no loop -> restart this voice's orderlist
        lda ollo,x
        sta wptr
        lda olhi,x
        sta wptr+1
        jmp np_read
np_ff:
        ; end with loop -> orderlist start + loop index (byte after $FF)
        ldy #$01
        lda (wptr),y
        clc
        adc ollo,x
        sta wptr
        lda olhi,x
        adc #$00
        sta wptr+1
        jmp np_read

; advance the working orderlist pointer by 1
ol_adv:
        inc wptr
        bne ol_adv_done
        inc wptr+1
ol_adv_done:
        rts

; set instrument for voice X: A = index
set_instr_v:
        tay
        lda INSTR_AD,y
        sta tmpf
        lda INSTR_SR,y
        sta tmpf+1
        lda INSTR_PULSE,y        ; pulse-program start row
        sta VIPULSE,x
        lda INSTR_FLAGS,y        ; flags ($40 = start filter program)
        sta VIFLAGS,x
        lda INSTR_FILT,y         ; filter-program start row
        sta VIFILT,x
        lda INSTR_WAVE,y
        sta VIWAVE,x             ; instrument's wave-program start row
        tay
        lda WAVE,y
        sta vwf,x                ; first waveform (for pr_note's gate toggle)
        ldy sidoff
        lda tmpf
        sta SID+5,y
        lda tmpf+1
        sta SID+6,y
        rts

; --- STOP -----------------------------------------------------------------
do_stop:
        ldx #$18
cz:     lda #$00
        sta SID,x
        dex
        bpl cz
        rts

; SID voice register offsets
sidbase:
        .byte $00, $07, $0e
; per-voice filter-routing bit (AND with FILT_ROUTE -> is this voice filtered?)
frbits:
        .byte $01, $02, $04
; per-voice orderlist start addresses (from the layout)
ollo:
        .byte <OL0, <OL1, <OL2
olhi:
        .byte >OL0, >OL1, >OL2

; Pin the note->freq table ABOVE the playback-state region ($16cc-$1702) so it
; can never collide with it (SF2II reads/writes that state every frame; an
; overlapping freqtable would be corrupted -> crash). The gap $1703-$1A00 (edit
; base) is free. Routines live $1000-~$1623, well below the state region.
        * = $1710
freqtable:
        .include "freqtable.inc"
