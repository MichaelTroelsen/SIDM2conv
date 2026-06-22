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
fmptr       = $ec           ; working pointer into FMTAB (fm_step indirect read) (2)
pptr        = $b9           ; working pointer into PULSETAB (pulse_step indirect read) (2)
                            ; ($ea/$eb collide with vhold[1]/vhold[2]!)
ms_cnt      = $f0           ; multispeed tick countdown within one video frame
tmpf        = $f6           ; freq/ADSR temp (lo/hi)
widx        = $f5           ; wave-index temp
pending_dur = $f4           ; duration parsed this event
tieflag     = $f1           ; nonzero if the current note is a TIE ($90-$9f dur):
                            ; legato continuation -> no gate re-attack, pulse free-runs
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
; --- pulse program runner (ROW-major PULSETAB, 3 bytes/entry, walked via a
;     16-bit pointer exactly like FM — removes the old 256-row col-major cap so a
;     full-length song's pulse envelopes (1000s of frames -> 100s of rows) fit:
;     8X XX YY = set 12-bit width (X|XX) for YY frames; 0X XX YY = add (X|XX) to
;     width each frame for YY; 7f -- -- = freeze (end). The per-note pulse program
;     is selected by the $c0-$ff command (index -> IPULSE_LO/HI -> VIPUL -> PPTR),
;     decoupled from the instrument. (No longer a render-in-editor table.) -------
VPC     = $180c          ; per-voice frames left on current row (3)
VPLO    = $180f          ; per-voice current 12-bit pulse lo (3)
VPHI    = $1812          ; per-voice current 12-bit pulse hi (3)
VPADL   = $1815          ; per-voice per-frame add lo (3)
VPADH   = $1818          ; per-voice per-frame add hi (3)
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
; --- FM offset-list runner (TRACE-DRIVEN pitch program): per-voice frequency
;     accumulator that walks the FM table (FMTAB ROW-major, 3 bytes/entry:
;     lo,hi,dur) via a 16-bit pointer from the note's instrument FM-start,
;     adding the signed offset to FM_ACC each frame; freq written = vfreq +
;     FM_ACC. dur 0 = freeze. Row-major + 16-bit ptr removes the old 256-entry
;     cap so full-length Galway slides (1000s of frames) fit. Each note's pitch
;     envelope is selected PER NOTE by the $c0-$ff sequence command (index ->
;     IFM_LO/IFM_HI -> VIFM -> FMP), decoupled from the instrument. ------------
FM_ON     = $182c        ; per-voice: 1 = FM running (3)
FM_IDX    = $182f        ; per-voice: (legacy, unused) (3)
FM_CNT    = $1832        ; per-voice: frames left on current entry (3)
FM_ACC_LO = $1835        ; per-voice: accumulated freq offset lo (3)
FM_ACC_HI = $1838        ; per-voice: accumulated freq offset hi (3)
FM_OFF_LO = $183b        ; per-voice: current entry offset lo (3)
FM_OFF_HI = $183e        ; per-voice: current entry offset hi (3)
vbasenote = $1841        ; per-voice: base note index (note+transpose) for the
                         ; wave-table semitone column; wave_step recomputes
                         ; vfreq = freqtable[vbasenote + col1] each frame (3)
FMP_LO    = $1844        ; per-voice: current FMTAB read pointer lo (3)
FMP_HI    = $1847        ; per-voice: current FMTAB read pointer hi (3)
VIFM_LO   = $184a        ; per-voice: current instrument's FM-start addr lo (3)
VIFM_HI   = $184d        ; per-voice: current instrument's FM-start addr hi (3)
PPTR_LO   = $1850        ; per-voice: current PULSETAB read pointer lo (3)
PPTR_HI   = $1853        ; per-voice: current PULSETAB read pointer hi (3)
VIPUL_LO  = $1856        ; per-voice: current cmd's pulse-program start addr lo (3)
VIPUL_HI  = $1859        ; per-voice: current cmd's pulse-program start addr hi (3)

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
; (SF2II writes the SID channel offsets 0,7,14 to $16cc-$16ce, so keep our
;  state bytes clear of that range.)
ST_STATE    = $16d0       ; m_DriverStateAddress: $80 playing / $40 stopped.
                          ; SF2II reads this to drive the play cursor (follow)
                          ; and to detect a self-stop.
ST_TCNT     = $16d1       ; m_TempoCounterAddress: 0 on the frame a new row
                          ; ticks (SF2II advances its follow cursor on 0).
ST_PLAY     = $16d2       ; internal: 1 = playing, 0 = stopped/idle. SF2II calls
                          ; STOP on load + on the stop key, INIT on play, so this
                          ; gates do_play (no playback until the user presses play).
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
        sta VPC,x                ; pulse: VPC=0 -> reload on the first frame
        sta VPLO,x
        sta VPHI,x
        sta VPADL,x
        sta VPADH,x
        lda #$fe
        sta VGMASK,x             ; start gated off
        lda #$00
        sta FM_ON,x              ; FM idle until a note triggers
        sta FM_ACC_LO,x
        sta FM_ACC_HI,x
        sta FM_CNT,x
        sta FMP_LO,x
        sta FMP_HI,x
        lda IFM_LO               ; default FM = program 0 (flat) until a cmd selects
        sta VIFM_LO,x
        lda IFM_HI
        sta VIFM_HI,x
        lda IPULSE_LO            ; default pulse = program 0 until a cmd selects
        sta VIPUL_LO,x
        sta PPTR_LO,x            ; point the read pointer at it
        lda IPULSE_HI
        sta VIPUL_HI,x
        sta PPTR_HI,x
        lda #$00
        sta vbasenote,x          ; base note index (set on each note trigger)
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
        sta ST_PLAY              ; INIT = play: enable do_play
        lda #$80
        sta ST_STATE             ; report "playing"
        rts

; --- PLAY -----------------------------------------------------------------
;     Runs the player MULTISPEED times per call. SF2II calls do_play once per
;     PAL video frame (50 Hz), but the original is CIA-multispeed (Galway's
;     Wizball = 4 play-calls/frame). Trace data is per-play-call, so to match
;     the real wall-clock speed the driver replays MULTISPEED play-ticks each
;     video frame. MULTISPEED comes from layout.inc (1 = single-speed). --------
do_play:
        lda ST_PLAY              ; idle until SF2II issues play (INIT); STOP clears
        bne dp_go
        rts
dp_go:
.if DIGI_SPIKE
        jmp digi_stream          ; FEASIBILITY SPIKE: stream a $D418 square wave
.endif
        lda #$80
        sta ST_STATE             ; report "playing" to SF2II (drives follow cursor)
        lda #$01
        sta ST_TCNT              ; non-zero unless a row ticks this frame (do_row)
        inc ST_TICK
        lda F_MODE               ; filter passband bits (from the filter program)
        ora #$0f                 ; + main volume
        sta SID_VOL
        lda #MULTISPEED
        sta ms_cnt
dp_tick:
        dec zp_tcnt
        bne dp_vib
        jsr do_row               ; row tick: step the sequencer
dp_vib:
        ; filt_prog_step / pulse_step run AFTER do_row so a note's RESET (pr_note
        ; sets F_IDX=VIFILT/F_CNT=0 for the filter, PPTR=VIPUL/VPC=0 for the pulse)
        ; takes effect on the SAME frame as the note — else the cutoff/pulse sweep
        ; lags one frame (audible on the lead's per-note resonant pluck + ramp).
        jsr filt_prog_step       ; global filter program -> $D415/6/7 + mode
        jsr pulse_step           ; per-voice pulse-program -> $D402/3 each tick
        jsr wave_step            ; wave-program -> $D404 + recompute vfreq
        jsr fm_step              ; per-voice freq -> $D400/1 (+ FM accumulate)
        dec ms_cnt
        bne dp_tick              ; next multispeed tick this frame
        rts

; --- per-voice wave-program runner (standard 2-col wave table, like Driver 11:
;     col0 = waveform (or $7f jump marker), col1 = signed semitone offset (or,
;     on a $7f row, the jump-target row). ONE row per frame. Each frame: resolve
;     $7f jumps, write $D404 = waveform & gate-mask, and apply col1 as a signed
;     semitone offset to the note (vfreq = freqtable[vbasenote + col1], clamped
;     to [0,$6f]); fm_step then writes vfreq. col1 $00 => no offset. The trace
;     build emits the full per-frame Galway pitch envelope this way — one row
;     per frame with the settled tail looped — keeping the wave table in SF2II's
;     native 2-column format so it renders + edits + PLAYS in stock SF2II. -----
wave_step:
        ldx #$02
ws_l:
        ldy VWI,x                ; current row
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
        sty ws_row               ; resolved row (never $7f)
        lda WAVE+256,y           ; col1 = signed semitone offset
        bmi ws_neg               ; bit7 set -> negative offset
        clc                      ; positive: vbasenote + offset, clamp high to $6f
        adc vbasenote,x
        cmp #$70
        bcc ws_sok
        lda #$6f
        bne ws_sok               ; $6f != 0 -> always taken (near branch, no jmp)
ws_neg:
        clc                      ; negative: vbasenote + offset, clamp low to $00
        adc vbasenote,x
        bcs ws_sok               ; carry set -> no underflow
        lda #$00
ws_sok:
        asl                      ; note index -> freqtable word offset
        tay
        lda freqtable,y          ; vfreq = freqtable[clamped note]
        sta vfreq_lo,x
        lda freqtable+1,y
        sta vfreq_hi,x
        ldy ws_row               ; restore resolved row + reload waveform for $D404
        lda WAVE,y
        and VGMASK,x             ; apply gate mask (on=$ff, off=$fe)
ws_write:
        ldy sidbase,x
        sta SID+4,y
        ldy ws_row               ; advance one row for next frame
        iny
        tya
        sta VWI,x
        dex
        bmi ws_done              ; (bpl ws_l now out of branch range)
        jmp ws_l
ws_done:
        rts

; --- per-voice pulse-program runner: walk the standard pulse table (set/add/
;     jump), applying the per-frame add and writing $D402/3 each frame. --------
pulse_step:
        ldx #$02
pl_l:
        lda VPC,x
        bne pl_apply             ; still on current row -> just apply the add
        ; row expired -> load the next PULSETAB entry via the 16-bit pointer
        lda PPTR_LO,x
        sta pptr
        lda PPTR_HI,x
        sta pptr+1
        ldy #$00
        lda (pptr),y             ; byte0 = cmd nibble | width-hi nibble (or $7f)
        cmp #$7f
        bne pl_decode
        ; $7f = freeze: add 0, hold, do NOT advance the pointer
        lda #$00
        sta VPADL,x
        sta VPADH,x
        lda #$ff
        sta VPC,x
        jmp pl_apply
pl_decode:
        sta tmpf                 ; byte0
        ldy #$02
        lda (pptr),y             ; byte2 = frame count
        sta VPC,x
        lda PPTR_LO,x            ; advance pointer by 3 bytes (row-major)
        clc
        adc #$03
        sta PPTR_LO,x
        bcc pl_b1
        inc PPTR_HI,x
pl_b1:
        ldy #$01
        lda (pptr),y             ; byte1 = width lo
        sta tmpf+1
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

; --- per-voice FM offset-list runner (trace-driven): writes $D400/1 = vfreq +
;     FM_ACC every frame. For FM-on voices, walk FMTAB from FM_IDX, accumulating
;     the current signed offset into FM_ACC for its duration; dur 0 = freeze. The
;     offset list is the real per-frame pitch envelope captured from the player. -
fm_step:
        ldx #$02
fm_l:
        lda FM_ON,x
        bne fm_run
        jmp fm_write             ; FM off -> freq = vfreq (FM_ACC stays 0)
fm_run:
        lda FM_CNT,x
        beq fm_load              ; current entry expired -> load next
        jmp fm_add
fm_load:
        lda FMP_LO,x             ; point fmptr at the current row-major entry
        sta fmptr
        lda FMP_HI,x
        sta fmptr+1
        ldy #$02
        lda (fmptr),y            ; byte 2 = dur
        bne fm_haveent
        ; dur 0 -> freeze: offset 0, hold, do not advance
        lda #$00
        sta FM_OFF_LO,x
        sta FM_OFF_HI,x
        lda #$ff
        sta FM_CNT,x
        jmp fm_add
fm_haveent:
        sta FM_CNT,x
        ldy #$00
        lda (fmptr),y            ; byte 0 = offset lo
        sta FM_OFF_LO,x
        iny
        lda (fmptr),y            ; byte 1 = offset hi
        sta FM_OFF_HI,x
        lda FMP_LO,x             ; advance pointer by 3 bytes
        clc
        adc #$03
        sta FMP_LO,x
        bcc fm_add
        inc FMP_HI,x
fm_add:
        lda FM_ACC_LO,x          ; FM_ACC += signed offset
        clc
        adc FM_OFF_LO,x
        sta FM_ACC_LO,x
        lda FM_ACC_HI,x
        adc FM_OFF_HI,x
        sta FM_ACC_HI,x
        lda FM_CNT,x
        beq fm_write
        dec FM_CNT,x
fm_write:
        ldy sidbase,x            ; freq = vfreq + FM_ACC
        lda vfreq_lo,x
        clc
        adc FM_ACC_LO,x
        sta SID+0,y
        lda vfreq_hi,x
        adc FM_ACC_HI,x
        sta SID+1,y
        dex
        bmi fm_done
        jmp fm_l
fm_done:
        rts
do_row:
        lda #$00
        sta ST_TCNT              ; a new row ticked this frame (SF2II follow cursor++)
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
        ; Classify by the HIGH BIT first ($00-$7f = note, $80+ = cmd/instr/dur).
        ; SF2II's 6510 emulator computes CMP's carry from bit7 of (A-operand)
        ; rather than (A>=operand), so a wide compare like `cmp #$c0` mis-sets
        ; carry when the operand is far above A (e.g. note $19 vs $c0) and the
        ; note is misread as a command -> silent playback. Splitting on $80
        ; first keeps every compare within +-$7f, where its carry is correct.
        cmp #$80
        bcc pr_note              ; $00-$7f -> note
        cmp #$c0
        bcs pr_setprog           ; $c0-$ff -> set per-note synth program (slide+pulse)
        cmp #$a0
        bcs pr_setinst           ; $a0-$bf -> set instrument
        sta tieflag              ; $80-$9f -> duration; bit $10 = tie marker
        and #$0f
        sta pending_dur
        lda tieflag
        and #$10                 ; isolate tie bit -> tieflag (0 or $10)
        sta tieflag
        jsr advw
        jmp pr_read
pr_setprog:
        ; $c0-$ff: select this voice's PER-NOTE synth program (a bundle of FM
        ; slide + pulse-width envelope), decoupled from the instrument. index =
        ; byte & $3f selects both the FM-start pointer (IFM) and the pulse-program
        ; start addr (IPULSE_LO/HI); pr_note restarts both. Lets a long song
        ; carry many distinct slide+pulse shapes without inflating the <=32
        ; instrument table (timbre = instrument; slide+pulse = this command).
        and #$3f
        tay
        lda IFM_LO,y
        sta VIFM_LO,x
        lda IFM_HI,y
        sta VIFM_HI,x
        lda IPULSE_LO,y
        sta VIPUL_LO,x
        lda IPULSE_HI,y
        sta VIPUL_HI,x
        jsr advw
        jmp pr_read
pr_setinst:
        and #$1f
        jsr set_instr_v
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
pn_adv:
        jmp advw                 ; trampoline (advw now out of branch range)
pn_not_off:
        cmp #$7e
        beq pn_adv
        cmp #$70
        bcs pn_adv
        clc                      ; apply transpose
        adc vtrans,x
        sta vbasenote,x          ; base note index for the wave-table semitone col
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
        lda tieflag              ; TIE -> change pitch only: no gate re-attack, and
        bne pn_tied              ; leave the pulse program free-running (legato)
        lda vwf,x                ; retrigger: gate off then on
        and #$fe
        sta SID+4,y
        lda vwf,x
        ora #$01
        sta SID+4,y
        lda VIPUL_LO,x           ; restart the pulse program too (16-bit pointer)
        sta PPTR_LO,x
        lda VIPUL_HI,x
        sta PPTR_HI,x
        lda #$00
        sta VPC,x                ; force reload on the next frame
pn_tied:
        lda VIWAVE,x             ; restart the wave program at the instrument's row
        sta VWI,x
        lda #$ff
        sta VGMASK,x             ; gate on (wave_step keeps the gate asserted)
        ; (re)start the FM offset-list at this note's FM program (set per note by
        ; the $c0-$ff command). The trigger frame shows the BASE pitch (FM_ACC=0);
        ; the first FM delta is applied the NEXT frame — matching the real SID,
        ; whose frequency at the onset frame is the base note before any slide
        ; accumulates. (FM_CNT=1 + FM_OFF=0 holds zero for this frame, then
        ; FM_CNT hits 0 next frame and loads entry 0.) Applying the first delta on
        ; the trigger frame put every FM-modulated voice 1 frame ahead of the
        ; trace (audible phase-shift on the lead + arps).
        lda VIFM_LO,x
        sta FMP_LO,x
        lda VIFM_HI,x
        sta FMP_HI,x
        lda #$00
        sta FM_ACC_LO,x
        sta FM_ACC_HI,x
        sta FM_OFF_LO,x          ; no offset on the trigger frame
        sta FM_OFF_HI,x
        lda #$01
        sta FM_CNT,x             ; hold base this frame; load entry 0 next frame
        sta FM_ON,x
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
        ; Neither FM nor pulse is tied to the instrument any more — both are
        ; selected per note by the $c0-$ff command (see pr_setprog). The
        ; instrument sets only timbre: AD/SR/flags/filter/waveform.
        tay
        lda INSTR_AD,y
        sta tmpf
        lda INSTR_SR,y
        sta tmpf+1
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
        lda #$00
        sta ST_PLAY              ; STOP: gate do_play off (silent, no advance)
        lda #$40
        sta ST_STATE             ; report "stopped"
        ldx #$18
cz:     lda #$00
        sta SID,x
        dex
        bpl cz
        rts

.if DIGI_SPIKE
; --- FEASIBILITY SPIKE ----------------------------------------------------
; Tests whether stock SF2II renders SUB-FRAME $D418 writes from do_play as audio
; (the digi/volume trick). Silences the 3 voices, then busy-streams a ~800 Hz
; square to the master-volume register for ~one frame's worth of cycles. If
; SF2II's reSID is cycle-accurate on register writes, the user hears a clean
; tone; if it only snapshots registers per frame, it stays silent.
digi_stream:
        lda #$80
        sta ST_STATE             ; keep SF2II's "playing" state so it keeps calling
        ldx #$18
dsz:    lda #$00                 ; silence all SID voices ($D400-$D418 -> 0)
        sta SID,x
        dex
        bpl dsz
        ldy #$10                 ; ~16 square periods (fits a frame's cycle budget)
dsl:    lda #$0f                 ; volume full
        sta SID_VOL
        ldx #$40
dd1:    dex
        bne dd1
        lda #$00                 ; volume zero
        sta SID_VOL
        ldx #$40
dd2:    dex
        bne dd2
        dey
        bne dsl
        rts
.endif

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
