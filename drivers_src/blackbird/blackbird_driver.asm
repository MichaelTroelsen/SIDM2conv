; ==========================================================================
; Blackbird (Linus Åkesson / "lft") SF2 driver — Stage B1
; ==========================================================================
; Forked from drivers_src/romuzak/romuzak_driver.asm (per docs/players/
; PLAYBOOK.md §2/§6: every native Stage-B driver in this project is a fork
; of the same ~1,300-line SID Factory II driver). The sequencer/orderlist/
; instrument-select/note-trigger machinery and the wave/pulse/filter/FM
; TABLE STEPPERS below are UNCHANGED from romuzak_driver.asm — only the
; DIGI engine (romuzak-specific, not needed for Blackbird B1) was stripped
; out to keep this fork minimal. Blackbird's own programs (wavetable/
; filttable/fxtable, RE'd + validated byte-exact in
; docs/players/BLACKBIRD.md's "Stage B synth engine" section) are
; TRANSLATED into this shared engine's WAVE/PULSETAB/FILTER/FMTAB table
; format by bin/build_blackbird_native_song.py — no new 6502 stepper logic
; is written here.
;
; Build: py -3 bin/build_blackbird_driver_full.py
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
; ($b9/$ba free since B9 deleted pulse_step's PULSETAB indirect pointer.
;  NB $ea/$eb collide with vhold[1]/vhold[2] -- do not reuse those.)
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
; pulse-width modulation: the 12-bit pulse HI byte is FIXED at the
; instrument's base and the LO byte sweeps as a triangle (unused by the
; Blackbird B1 table-driven pulse programs, kept for driver-shape parity).
pw_lo       = $b3           ; $b3,$b4,$b5  per-voice current pulse-width lo
pw_dir      = $b6           ; $b6,$b7,$b8  0 = sweeping up, 1 = down
PWSTEP   = $08           ; pulse-width lo delta per frame
PWMIN    = $08
PWMAX    = $f8
; --- filter (one global SID resource) ---
filt_lo     = $bc           ; 16-bit current cutoff lo
filt_hi     = $bd           ; 16-bit current cutoff hi (high byte -> $D416)
FILT_RES   = $f0         ; unused (kept for driver-shape parity)
FILT_ROUTE = $01
FILT_MODE  = $10
FILTTOP    = $8900
FILTBOT    = $7300
FILTSTEP   = $00c0
; --- wave program runner (STANDARD SF2II wave table, col-major 256x2:
;     col0=waveform byte, col1=semitone(00-7f add / 80-df abs) or jump-target;
;     one row advanced per frame; col0 $7f = jump to col1 index). ------------
VWI     = $1980          ; per-voice current wave-program row (3)
VGMASK  = $1983          ; per-voice $D404 AND-mask: $ff gated-on, $fe gated-off (3)
VIWAVE  = $1986          ; per-voice instrument wave-program start row (3)
ws_row  = $ee            ; wave_step scratch: resolved row
ws_grd  = $ef            ; wave_step scratch: $7f-jump chase guard
; --- B9: pulse-width ACCUMULATOR (replaces the whole PULSETAB row-cursor
;     engine -- see wave_step below and docs/players/BLACKBIRD.md's B9).
;     Blackbird's pulse width is an 8-bit accumulator stepped in lockstep
;     with the WAVE row: a wave row whose waveform byte has bit6 set carries
;     a delta in the SAME row's col1, and the SID pulse registers get
;     pwprepare[PW_ACC] written to BOTH $D402 and $D403. That is lft's own
;     structure (player.s 272-317) ported 1:1, not an approximation of its
;     output -- so it is exact for any note length, never truncates, and
;     never drifts. B8's VPC/VPLO/VPHI/VPADL/VPADH/PPTR_*/VIPUL_* are all
;     gone: they described an independently-paced pulse cursor that real
;     hardware does not have.
PW_ACC  = $198c          ; per-voice 8-bit pulse-width accumulator (3)
; --- filter program runner (STANDARD SF2II filter table, col-major 256x3:
;     9Y YY RB = set passband/cutoff/res/bitmask; 0X XX YY = add to cutoff each
;     frame for YY; 7f -- XX = jump. ONE global SID filter; started when a note
;     from an instrument with flag $40 triggers (filter index = instr col3).
;     Cutoff held as 16-bit F_CUT (high byte -> $D416). -----------------------
F_IDX   = $199e          ; filter-program row
F_CNT   = $199f          ; frames left on current row
F_CLO   = $19a0          ; 16-bit cutoff lo
F_CHI   = $19a1          ; 16-bit cutoff hi (-> $D416)
F_ADLO  = $19a2          ; per-frame cutoff add lo
F_ADHI  = $19a3          ; per-frame cutoff add hi
F_MODE  = $19a4          ; SID mode bits for $D418 high nibble (from passband)
F_ACT   = $19a5          ; 1 = a filter program is running
VIFLAGS = $19a6          ; per-voice instrument flags byte (col2) (3)
VIFILT  = $19a9          ; per-voice instrument filter-program start row (3)
; --- FM offset-list runner (per-frame pitch program): per-voice frequency
;     accumulator that walks the FM table (FMTAB ROW-major, 3 bytes/entry:
;     lo,hi,dur) via a 16-bit pointer from the note's instrument FM-start,
;     adding the signed offset to FM_ACC each frame; freq written = vfreq +
;     FM_ACC. dur 0 = freeze. Each note's pitch envelope is selected PER NOTE
;     by the $c0-$ff sequence command (index -> IFM_LO/IFM_HI -> VIFM -> FMP),
;     decoupled from the instrument. ------------
FM_ON     = $19ac        ; per-voice: 1 = FM running (3)
FM_IDX    = $19af        ; per-voice: (legacy, unused) (3)
FM_CNT    = $19b2        ; per-voice: frames left on current entry (3)
FM_ACC_LO = $19b5        ; per-voice: accumulated freq offset lo (3)
FM_ACC_HI = $19b8        ; per-voice: accumulated freq offset hi (3)
FM_OFF_LO = $19bb        ; per-voice: current entry offset lo (3)
FM_OFF_HI = $19be        ; per-voice: current entry offset hi (3)
vbasenote = $19c1        ; per-voice: base note index (note+transpose) for the
                         ; wave-table semitone column; wave_step recomputes
                         ; vfreq = freqtable[vbasenote + col1] each frame (3)
FMP_LO    = $19c4        ; per-voice: current FMTAB read pointer lo (3)
FMP_HI    = $19c7        ; per-voice: current FMTAB read pointer hi (3)
VIFM_LO   = $19ca        ; per-voice: current instrument's FM-start addr lo (3)
VIFM_HI   = $19cd        ; per-voice: current instrument's FM-start addr hi (3)
; ($19d0-$19db: freed by B9's removal of PPTR_LO/HI + VIPUL_LO/HI)
SWTOG     = $19dc        ; swing-tempo phase toggle (ported from the MoN driver, which
                         ; ported it from the MoN ROM's own $E2 toggle at $1134-$1138):
                         ; EOR #$ff per row; negative phase reloads TEMPO2 (the SHORT
                         ; period), positive reloads TEMPO (long). Blackbird's real
                         ; zp_tempo/m_groove XOR alternation (see BLACKBIRD.md's tempo
                         ; section) is the same shape -- two frame-counts ping-ponging
                         ; forever -- so this existing mechanism is reused as-is rather
                         ; than porting new asm. B3: do_row no longer reads the compile-time
                         ; #TEMPO/#TEMPO2 immediates directly -- it reads the LIVE
                         ; CUR_TEMPO/CUR_TEMPO2 pair below, which a new row-indexed tempo
                         ; SCHEDULE (tempo_sched_* tables, near the end of this file)
                         ; overwrites every time ROW_CNT reaches Blackbird's real next
                         ; mid-song tempo/groove OOB record -- Fargo alone has 22 of these
                         ; (see BLACKBIRD.md); B2 only modelled the first.
CUR_TEMPO  = $19dd       ; B3: live long-phase frame count, read by do_row instead of
                         ; #TEMPO -- do_init seeds it from TEMPO, the schedule updates it.
CUR_TEMPO2 = $19de       ; B3: live short-phase frame count (from TEMPO2 / schedule).
ROW_CNT_LO = $19df       ; B3: 16-bit row/tick counter, incremented once per do_row call --
ROW_CNT_HI = $19e0       ; this IS Blackbird's own tick grid (one do_row = one execute()
                         ; cycle on real hardware, per BLACKBIRD.md's tempo-model section --
                         ; the same unit blackbird_driver11.py's Stage A already maps 1:1
                         ; onto Driver 11 rows), so the schedule's row indices (derived by
                         ; counting the validated simulator's own execute() calls) line up
                         ; exactly with this counter with no rescaling.
TEMPO_SCHED_IDX = $19e1  ; B3: 0-based index of the NEXT unconsumed schedule entry --
                         ; 8-bit, matches the tables' own <=64-entry cap ($1595-$16cb's
                         ; 311-byte gap between the code and the reserved playback-state
                         ; region comfortably fits 64*4=256 bytes; the tables are placed
                         ; there, unpinned, right after the ollo/olhi tables below).

        .include "layout.inc"
INSTR_AD    = INSTR + 0*32
INSTR_SR    = INSTR + 1*32
INSTR_FLAGS = INSTR + 2*32   ; flags ($40 = start filter program)
INSTR_FILT  = INSTR + 3*32   ; filter-program start row
INSTR_PULSE = INSTR + 4*32   ; pulse-program index (unused; the real per-
                              ; instrument pulse-program ADDRESS lives in the
                              ; INSTR_PUL_LO/HI tables from layout.inc, which
                              ; need 16 bits and so can't live in this
                              ; single-byte column -- see set_instr_v, B8)
INSTR_WAVE  = INSTR + 5*32

; --- Block-2 playback-state region (editor reads these) -------------------
ST_FIRST    = $16cc
ST_LAST     = $1702
ST_STATE    = $16d0       ; m_DriverStateAddress: $80 playing / $40 stopped.
ST_TCNT     = $16d1       ; m_TempoCounterAddress: 0 on the frame a new row ticks.
ST_PLAY     = $16d2       ; internal: 1 = playing, 0 = stopped/idle.
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
        lda #$ff
        sta SWTOG                ; swing-tempo toggle: first do_row call uses TEMPO (long) --
                                  ; EXPERIMENT: flipped from $00 to test phase empirically
                                  ; against the validated simulator (see build script output)
        lda #TEMPO
        sta CUR_TEMPO             ; B3: live pair starts as the song's first tempo/groove
        lda #TEMPO2                ; pair (same values TEMPO/TEMPO2 always held); the row-
        sta CUR_TEMPO2              ; indexed schedule below takes over from here.
        lda #$00
        sta ROW_CNT_LO
        sta ROW_CNT_HI
        sta TEMPO_SCHED_IDX
        ; B7 (part-boundary priming, 2026-07-19, docs/players/BLACKBIRD.md's
        ; "B7" section): a part that starts mid-song (row0>0) is NOT the
        ; song's own true start -- on real hardware a voice that's mid-
        ; sustain (or silently resting, holding whatever a much earlier
        ; note last wrote) keeps its REAL per-voice engine state; this
        ; shared engine's do_init used to unconditionally COLD-START every
        ; part identically to part 1 (all zeroed/default), discarding that
        ; real state. Every field below is now read from a PRIME_*_TAB
        ; table (3 bytes, one per voice, X-indexed exactly like this SAME
        ; loop's existing per-voice fields), generated per-part by
        ; bin/build_blackbird_native_song.py's _compute_prime_consts from
        ; the validated full-song simulator's OWN real state at this
        ; part's start frame -- for a part starting at row0==0 (the song's
        ; true start, e.g. Fargo's only part, or Glyptodont's part 1),
        ; _compute_prime_consts emits EXACTLY the old literal defaults
        ; (verified explicitly, see the report), so this is a genuine
        ; no-op for every part that doesn't need priming, not a behavior
        ; change gated by a runtime flag.
        ldx #$02
iv:     lda PRIME_VWF_TAB,x
        sta vwf,x
        lda #$00
        sta vhold,x
        sta vtrans,x
        lda PRIME_VWI_TAB,x       ; primed wave-program row (0 for a part
        sta VWI,x                 ; starting at the song's true row 0)
        lda PRIME_VIWAVE_TAB,x
        sta VIWAVE,x
        lda #$00
        sta vfreq_lo,x            ; recomputed fresh every frame by wave_step's
        sta vfreq_hi,x            ; own ws_sok path -- no priming needed here
        ; B9: PULSE priming is now ONE byte per voice. B8 needed seven
        ; (PPTR_LO/HI, VPC, VPLO, VPHI, VPADL, plus an aux PULSETAB program
        ; just to give the cursor a stable address) because the pulse ran on
        ; its own row cursor whose whole position had to be reconstructed.
        ; With the pulse stepped by the WAVE row, PRIME_VWI (set just above)
        ; already positions the pulse program too -- so the only state left
        ; is the accumulator itself, which is genuine per-voice runtime state
        ; the boundary snapshot carries directly (`v.pwidth`). This is an
        ; EXACT resume of the mid-sweep phase -- the specific thing B8's punch
        ; list named as impossible under the output-byte encoding.
        lda PRIME_PW_ACC_TAB,x
        sta PW_ACC,x
        lda PRIME_VGMASK_TAB,x
        sta VGMASK,x              ; primed gate state ($fe old default = off)
        ; B8: genuine mid-program FM resume (B7 forced this flat/off). The
        ; note-parameterization B7 named as the blocker is real but solvable
        ; -- the validated simulator's snapshot carries BOTH the bundle in
        ; flight (currfx + pendnote select the program) AND the position
        ; within it (fxpos), and FM's cumulative accumulator means the
        ; absolute pitch offset is just FM_ACC, which the builder can write
        ; directly. FM_ON=0 (with everything else 0) reproduces B7's
        ; flat/idle behaviour exactly whenever the position can't be
        ; resolved, so this degrades safely rather than guessing.
        lda PRIME_FM_ON_TAB,x
        sta FM_ON,x
        lda PRIME_FM_ACC_LO_TAB,x  ; the load-bearing one: FM is a cumulative
        sta FM_ACC_LO,x             ; accumulator, so the voice's whole
        lda PRIME_FM_ACC_HI_TAB,x    ; current pitch offset lives here
        sta FM_ACC_HI,x
        lda PRIME_FM_OFF_LO_TAB,x
        sta FM_OFF_LO,x
        lda PRIME_FM_OFF_HI_TAB,x
        sta FM_OFF_HI,x
        lda PRIME_FM_CNT_TAB,x
        sta FM_CNT,x
        lda PRIME_FMP_LO_TAB,x
        sta FMP_LO,x
        lda PRIME_FMP_HI_TAB,x
        sta FMP_HI,x
        lda PRIME_VIFM_LO_TAB,x   ; primed FM bundle pointer (old default =
        sta VIFM_LO,x              ; program 0's own address, reproduced
        lda PRIME_VIFM_HI_TAB,x    ; exactly by _compute_prime_consts' own
        sta VIFM_HI,x               ; "no owner instrument" branch)
        lda PRIME_VBASENOTE_TAB,x
        sta vbasenote,x           ; base note index (set on each note trigger)
        lda PRIME_FLAGS_TAB,x     ; primed instrument flags ($40 = filter-
        sta VIFLAGS,x              ; carrying) -- old default left this
                                    ; untouched (uninitialized-but-effectively-
                                    ; 0 on a fresh load); now explicit
        lda PRIME_VIFILT_TAB,x    ; primed instrument's own filter-program
        sta VIFILT,x               ; start row (same "left untouched" note)
        ; orderlist ptr = OL_x ; then load the first pattern (THIS part's
        ; own freshly-built sequence/orderlist always starts fresh at its
        ; own beginning regardless of priming -- not Blackbird engine state)
        lda ollo,x
        sta vol_lo,x
        lda olhi,x
        sta vol_hi,x
        jsr next_pattern         ; sets vsp[x] + vtrans[x] from the orderlist
        ldy sidbase,x
        lda PRIME_AD_TAB,x       ; primed AD/SR straight to the SID registers
        sta SID+5,y               ; (AD/SR are only ever written at a genuine
        lda PRIME_SR_TAB,x         ; instrument trigger, never recomputed per-
        sta SID+6,y                ; frame -- see _compute_prime_consts)
        ; B9 -- SECOND REAL BUG, found by measuring rather than reasoning.
        ; PW_ACC alone is NOT sufficient priming. Roughly half of both
        ; corpus files' instruments have wave programs with NO bit6 rows at
        ; all (B5's "freeze-only" case), so wave_step never writes $D402/3
        ; for them -- on real hardware that is correct and deliberate: the
        ; register simply KEEPS whatever the last pulse-writing instrument
        ; left in it, possibly from many seconds earlier. do_init clears the
        ; whole SID, so without this the driver held a hard 0 forever on
        ; those voices while the simulator held a real value.
        ; Measured on Fargo before this fix: voice 2 (which does have pulse
        ; rows) was 0/400 frames mismatched -- exact -- while voices 0 and 1
        ; were 400/400, driver $00 vs simulator $08 on every single frame.
        ; So: seed the REGISTER itself from the boundary snapshot's own
        ; $D402 byte. A voice with pulse rows overwrites it on its first
        ; pulse row (harmless); a voice without them keeps it forever
        ; (correct). B8 got this effect via PRIME_PULSE -> VPLO -> pl_wr's
        ; every-frame rewrite; B9 writes it once, directly, which is what
        ; real hardware does.
        lda PRIME_D402_TAB,x
        sta SID+2,y
        sta SID+3,y
        dex
        bmi iv_done               ; B7 lengthened this loop body past a signed
        jmp iv                     ; 8-bit branch's range -- bpl->jmp trampoline
iv_done:                            ; (same idiom as pn_adv/advw elsewhere in
                                     ; this file for an out-of-range branch)
        ; Blackbird's global filter engine (filttable/everyframe) runs
        ; CONTINUOUSLY from frame 0 regardless of which instrument is
        ; selected -- it is never gated on/off, only REPOSITIONED (F_IDX)
        ; by instruments whose ins_filt[i] != 0 (see BlackbirdSim.execute():
        ; `if fv != 0: self.zp_filtpos = fv` -- a no-op, not a disable, when
        ; fv==0). That's a real architectural difference from this shared
        ; engine's F_ACT gate (elsewhere: off until a flag-$40 note starts
        ; it) -- Blackbird B1 keeps F_ACT permanently 1 from init instead of
        ; the usual $00, so filt_prog_step runs every frame unconditionally,
        ; matching real hardware; pn_note's flag-$40 check still gates the
        ; REPOSITION (F_IDX/F_CNT reset), unchanged, matching the real
        ; per-instrument fv==0-is-a-no-op semantics exactly.
        lda #$01
        sta F_ACT
        ; B7: PRIME_F_IDX/F_CNT/F_ADHI/F_CLO/F_CHI/F_MODE generalize
        ; FILT_INIT_ROW's own existing idea (priming the filter's STARTUP
        ; walk position, previously only ever correct at a song's true row
        ; 0) to an ARBITRARY mid-song part boundary: PRIME_F_IDX is the
        ; real translated row the global filter program is actually AT when
        ; this part begins (found via a position lookup against whichever
        ; program -- default, or the instrument that last repositioned it
        ; -- currently governs it); PRIME_F_CNT/F_ADHI resume an in-flight
        ; multi-frame ADD ramp exactly where real hardware left it (0/0 for
        ; a genuine row-start, forcing the SAME fresh fp_load real hardware
        ; would take there); PRIME_F_CLO/F_CHI/F_MODE/PRIME_D417 are the
        ; REAL captured cutoff/mode/resonance -- required because fp_apply's
        ; ADD mode always continues from whatever F_CLO/F_CHI already hold,
        ; not re-derived from row content the way a SET row would be. For a
        ; part starting at row0==0, _compute_prime_consts's own "prime is
        ; None" branch reproduces this block's OLD literal defaults exactly
        ; (PRIME_F_IDX=FILT_INIT_ROW=0, PRIME_F_CNT=0, rest 0) -- verified,
        ; see the report.
        lda #PRIME_F_IDX
        sta F_IDX
        lda #PRIME_F_MODE
        sta F_MODE
        lda #PRIME_F_CLO
        sta F_CLO
        lda #PRIME_F_CHI
        sta F_CHI
        lda #PRIME_F_CNT
        sta F_CNT
        lda #$00
        sta F_ADLO                ; F_ADLO is always 0 for every row this
                                    ; driver's translator emits (see fp_apply's
                                    ; own comment below)
        lda #PRIME_F_ADHI
        sta F_ADHI
        lda #PRIME_D417
        sta $d417
        lda #$01
        sta zp_tcnt
        sta ST_PLAY              ; INIT = play: enable do_play
        lda #$80
        sta ST_STATE             ; report "playing"
        rts

; --- PLAY -----------------------------------------------------------------
;     Runs the player MULTISPEED times per call. SF2II calls do_play once per
;     PAL video frame (50 Hz). MULTISPEED comes from layout.inc (1 = single-speed).
do_play:
        lda ST_PLAY              ; idle until SF2II issues play (INIT); STOP clears
        bne dp_go
        rts
dp_go:
        lda #$80
        sta ST_STATE             ; report "playing" to SF2II (drives follow cursor)
        lda #$01
        sta ST_TCNT              ; non-zero unless a row ticks this frame (do_row)
        inc ST_TICK
        lda F_MODE               ; filter passband bits (from the filter program)
        ora #$0f                 ; + main volume: keep the gated SID voices at full vol
        sta SID_VOL
        lda #MULTISPEED
        sta ms_cnt
dp_tick:
        dec zp_tcnt
        bne dp_vib
        jsr do_row               ; row tick: step the sequencer
dp_vib:
        ; filt_prog_step runs AFTER do_row so a note's RESET (pr_note sets
        ; F_IDX=VIFILT/F_CNT=0) takes effect on the SAME frame as the note.
        ; B9: there is no separate pulse pass any more -- wave_step writes
        ; $D402/3 itself, from the same row it writes $D404 from, exactly as
        ; lft's own `vloop` does.
        jsr filt_prog_step       ; global filter program -> $D415/6/7 + mode
        jsr wave_step            ; wave-program -> $D404 + $D402/3 + vfreq
        jsr fm_step               ; per-voice freq -> $D400/1 (+ FM accumulate)
        dec ms_cnt
        bne dp_tick              ; next multispeed tick this frame
        rts

; --- per-voice wave-program runner (standard 2-col wave table, like Driver 11:
;     col0 = waveform (or $7f jump marker), col1 = signed semitone offset (or,
;     on a $7f row, the jump-target row). ONE row per frame. -----------------
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
        ; B9 -- A REAL BUG, found by building it the other way first: this
        ; USED to read `WAVE+256,y` here as a signed semitone offset and add
        ; it to vbasenote. col1 was described as "free" for Blackbird because
        ; the translator only ever WROTE 0x00 there -- but the driver was
        ; still READING it every frame, and a +0 offset is simply an
        ; invisible no-op, not an unused column. The moment col1 started
        ; carrying pulse deltas, every pulse row silently transposed its own
        ; voice by up to +127 semitones. Measured: Fargo freq 87.7% -> 71.2%
        ; and overall 94.1% -> 80.9% on the first B9 build.
        ;
        ; The fix is not to move the pulse delta elsewhere but to delete the
        ; read: Blackbird wave rows genuinely carry no semitone offset (pitch
        ; is the separate fx/FM engine, and the translator has always emitted
        ; a literal 0x00), so `vbasenote + 0` == `vbasenote`. This is exactly
        ; equivalent to the old code for every Blackbird program ever emitted,
        ; and it is what makes col1 actually free rather than nominally free.
        ; NOTE for anyone re-forking this driver for another player: the
        ; semitone column is a real shared-engine feature and this deletion
        ; is Blackbird-specific.
        lda VIFLAGS,x            ; DRUM instrument (flag $20)? col1 = freq HI
        and #$20                 ;   byte -- not emitted by this translator,
        bne ws_drum              ;   kept for driver-shape parity only
        lda vbasenote,x
        cmp #$70                 ; clamp (pr_note already rejects >= $70)
        bcc ws_sok
        lda #$6f
ws_sok:
        asl                      ; note index -> freqtable word offset
        tay
        lda freqtable,y          ; vfreq = freqtable[clamped note]
        sta vfreq_lo,x
        lda freqtable+1,y
        sta vfreq_hi,x
ws_w404:
        ldy ws_row               ; restore resolved row + reload waveform for $D404
        lda WAVE,y
        and VGMASK,x             ; apply gate mask (on=$ff, off=$fe)
ws_write:
        ldy sidbase,x
        sta SID+4,y
        ; --- B9: PULSE, stepped in lockstep with THIS wave row ------------
        ; A still holds the byte just written to $D404. lft's own test
        ; (player.s: `sta $d404,x` / `asl` / `bpl nopulse`): bit6 of the
        ; waveform byte IS the "this row carries pulse" flag. The gate mask
        ; applied above only ever clears bit0, so testing the masked byte is
        ; identical to testing the raw one.
        asl                      ; bit6 -> bit7
        bpl ws_nopulse
        ldy ws_row
        lda WAVE+256,y           ; col1 = the pulse delta (lft's `lda
        bmi ws_pwset             ;   wavetable+1,y` / `bmi pwset`)
        clc                      ; bit7 CLEAR -> ACCUMULATE. lft inherits the
        adc PW_ACC,x             ;   carry from his own `tya; adc #2` wavepos
        jmp ws_pwsto             ;   advance; that carry is a fixed property
ws_pwset:                        ;   of the row, so the translator FOLDS it
        asl                      ;   into the stored delta at build time and
ws_pwsto:                        ;   this add is a clean CLC one (see
        sta PW_ACC,x             ;   _pulse_col1). bit7 SET -> absolute, and
        tay                      ;   lft's `asl` doubles it -- reproduced
        lda pwprepare,y          ;   exactly.
        ldy sidbase,x
        sta SID+2,y              ; the SAME full byte to BOTH $D402 and
        sta SID+3,y              ; $D403 -- B5's Bug 2, unchanged
ws_nopulse:
        ldy ws_row               ; advance one row for next frame
        iny
        tya
        sta VWI,x
        dex
        bmi ws_done              ; (bpl ws_l now out of branch range)
        jmp ws_l
ws_done:
        rts
; DRUM wave row: col1 = freq HIGH byte written to vfreq_hi, KEEPING vfreq_lo.
; Not used by Blackbird B1 (no drum-flag instruments emitted); kept for parity.
ws_drum:                         ; Y still = resolved row (ws_row) from ws_have
        lda WAVE+256,y           ; col1 = freq high byte
        beq ws_w404              ; 0 -> keep note pitch (onset / settle)
        sta vfreq_hi,x
        jmp ws_w404

; --- B9: `pulse_step` DELETED. Blackbird's pulse width is not an
;     independently-paced program with its own row cursor -- it is an
;     8-bit accumulator stepped by the WAVE row (see wave_step's B9
;     block above and PW_ACC's declaration). The ~105 bytes of row-
;     cursor/decode logic that used to live here, and the PULSETAB it
;     walked, are both gone for Blackbird content.


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
        ; Blackbird's real m_cutoff is a FLAT 8-BIT accumulator with signed-
        ; overflow drop (BLACKBIRD.md's "Stage B synth engine": ADD mode
        ; "silently drops (both the state update AND the $D416 write) on
        ; signed overflow for that frame").
        ;
        ; SECOND REAL BUG FOUND (this session, task priority 2 -- the B4-
        ; flagged "tie-fix's ramp rate still doesn't fully converge" residual):
        ; the FIRST attempt at this overflow check (committed as B4) tested
        ; signed overflow on F_CHI's OWN raw byte -- but F_CHI holds the
        ; UNBIASED $D416 register value directly (0-255 unsigned, e.g. it's
        ; exactly what gets `sta $d416` below), NOT the value real hardware
        ; actually runs the signed-overflow test on. BlackbirdSim.everyframe()
        ; (the validated oracle) keeps a SEPARATE internal `m_cutoff`
        ; accumulator that is $D416's value XOR $80 (`self.w(22,
        ; (self.m_cutoff ^ 0x80) & 0xFF)` -- a classic 6502 bias-128 trick:
        ; XOR-by-$80 is congruent to +-128 mod 256, so it re-centers the
        ; UNSIGNED 0-255 register range onto the SIGNED -128..127 range with
        ; 0 and 255 at the two ends next to each other, exactly where a
        ; genuine wrap should be detected. Checking signed overflow on that
        ; BIASED value is what correctly fires only at the register's own
        ; real 0/255 wrap boundary. Checking it directly on the raw unbiased
        ; F_CHI byte instead (as this code did before this fix) fires at the
        ; WRONG boundary -- the raw value's own $7F/$80 signed-byte midpoint,
        ; which is just an ordinary point in the middle of the legitimate
        ; 0-255 cutoff range. Confirmed via direct trace on Glyptodont's
        ; voice2 instrument-4 tied run (the same run B4's Bug 3 fixed the
        ; wave/filter tied-restart on): the simulator's $D416 climbs smoothly
        ; from $7f up through $84, $89, ... toward $ff with NO drop at all,
        ; while the old driver code froze dead at $7f for ~65 frames (every
        ; ADD row-reload after that point kept re-triggering the SAME false
        ; "overflow" since ANY positive delta added to a raw byte already at
        ; $7f signed-overflows), then jumped away only when the NEXT row (a
        ; genuine SET, which bypasses this check entirely) loaded. Fixed by
        ; reproducing the sim's exact bias-128 recipe: XOR F_CHI by $80
        ; before the add (entering the biased/internal space), explicit CLC
        ; for the add's carry-in (matching BlackbirdSim's own `adc(delta,
        ; m_cutoff, carry_in=0)` -- always 0 there, since Blackbird's own
        ; m_cutoff accumulator, unlike this shared engine's general F_CLO/
        ; F_CHI 16-bit-cutoff design, has no lower-byte carry to chain; safe
        ; regardless since F_ADLO is always 0 for every row this driver's
        ; translator emits -- Blackbird has no sub-byte cutoff precision to
        ; encode, so F_CLO's own add never carries in practice either way),
        ; then XOR the result back by $80 before storing to F_CHI -- so
        ; F_CHI keeps holding the plain unbiased register value everywhere
        ; else in this driver (fp_write's `sta $d416` and fp_set's own
        ; direct writes are both untouched), only this ADD-mode overflow
        ; test itself operates in the biased space, exactly mirroring the
        ; validated oracle.
        lda F_CLO
        clc
        adc F_ADLO
        sta tmpf                 ; candidate new F_CLO -- not committed yet
        lda F_CHI
        eor #$80                 ; -> biased/internal m_cutoff representation
        clc                      ; carry_in=0, matching BlackbirdSim's adc() call
        adc F_ADHI
        bvs fp_ovf                ; signed overflow (in the BIASED space) ->
                                   ; drop BOTH the state update and this
                                   ; frame's $D415/6 write -- the real 0/255
                                   ; register wrap, not the $7f/$80 midpoint
        eor #$80                 ; -> back to the real unbiased $D416 value
        sta F_CHI
        lda tmpf
        sta F_CLO
        lda F_CNT
        beq fp_write
        dec F_CNT
fp_write:
        lda F_CLO
        sta $d415
        lda F_CHI
        sta $d416
        rts
fp_ovf:
        ; state frozen (F_CLO/F_CHI left untouched) and no $D415/6 write this
        ; frame -- row-walk bookkeeping (F_CNT) still advances normally,
        ; matching real hardware exactly (only the cutoff commit is skipped).
        lda F_CNT
        beq fp_ovf_done
        dec F_CNT
fp_ovf_done:
        rts

; --- per-voice FM offset-list runner (trace-driven): writes $D400/1 = vfreq +
;     FM_ACC every frame. For FM-on voices, walk FMTAB from FM_IDX, accumulating
;     the current signed offset into FM_ACC for its duration; dur 0 = freeze. --
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
        ; --- B3: row-indexed tempo schedule ----------------------------------
        ; ROW_CNT is Blackbird's own tick counter (1 per do_row call = 1 per real
        ; execute() cycle -- see ROW_CNT_LO's declaration above). Real hardware
        ; overwrites zp_tempo/m_groove directly from an inline 2-byte OOB record
        ; the instant the note stream delivers one (BLACKBIRD.md's tempo
        ; section) -- Fargo alone has 22 of these. tempo_sched_row_{lo,hi}[idx]
        ; holds the row at which the NEXT one lands (derived by counting the
        ; validated simulator's own execute() calls, bin/build_blackbird_native
        ; _song.py's extract_tempo_schedule()); tempo_sched_t1/t2[idx] hold the
        ; new long/short frame counts (already converted //7+1). On a match we
        ; also FORCE SWTOG so THIS row uses the new pair's LONG value first --
        ; real hardware's zp_master=zp_tempo commit is immediate and doesn't
        ; care about the prior alternation's parity, so neither should this.
        inc ROW_CNT_LO
        bne rc_hi_done
        inc ROW_CNT_HI
rc_hi_done:
        ldx TEMPO_SCHED_IDX
        cpx #TEMPO_SCHED_LEN
        bcs sk_sched
        lda tempo_sched_row_lo,x
        cmp ROW_CNT_LO
        bne sk_sched
        lda tempo_sched_row_hi,x
        cmp ROW_CNT_HI
        bne sk_sched
        lda tempo_sched_t1,x
        sta CUR_TEMPO
        lda tempo_sched_t2,x
        sta CUR_TEMPO2
        inc TEMPO_SCHED_IDX
        lda #$ff
        sta SWTOG                ; force long-phase (see comment above)
sk_sched:
        ; swing-tempo reload: alternate CUR_TEMPO2 (short) and CUR_TEMPO (long)
        ; per row, short phase first (ported verbatim from drivers_src/mon's
        ; SWTOG mechanism -- see the SWTOG declaration above). B3: reads the
        ; LIVE pair (schedule-updated) instead of the compile-time #TEMPO/
        ; #TEMPO2 immediates B1/B2 used.
        lda SWTOG
        eor #$ff
        sta SWTOG
        bmi dr_short
        lda CUR_TEMPO
        jmp dr_setcnt
dr_short:
        lda CUR_TEMPO2
dr_setcnt:
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
        ; carry when the operand is far above A -- splitting on $80 first keeps
        ; every compare within +-$7f, where its carry is correct.
        cmp #$80
        bcc pr_note              ; $00-$7f -> note
        cmp #$c0
        bcs pr_setprog           ; $c0-$ff -> set per-note synth program (FM+pulse)
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
        ; start addr (IPULSE_LO/HI); pr_note restarts both.
        and #$3f
        tay
        lda IFM_LO,y
        sta VIFM_LO,x
        lda IFM_HI,y
        sta VIFM_HI,x
        ; B8: the PULSE program is NO LONGER selected here. On real
        ; hardware the pulse-width program is part of the INSTRUMENT's wave
        ; program (BlackbirdSim.everyframe reads its pulse rows out of the
        ; SAME wavetable walk that produces $D404, seeded by ins_wave[i]) --
        ; it is per-instrument, exactly like WAVE, and has nothing to do
        ; with the per-note fx/arp bundle. Bundling the two meant that
        ; whenever the 64-slot cap forced a merge, the surviving bundle
        ; dragged a FOREIGN instrument's pulse program along with its FM
        ; program. Measured directly: Fargo held waveform at 98.9% (so the
        ; wave walk, and therefore the instrument, was provably correct)
        ; while pulse read 14.3% and the driver swept where the validated
        ; simulator held a constant. Moving the selection to set_instr_v
        ; also shrinks the bundle vocabulary to distinct (fx, note) pairs
        ; alone, which cuts clustering pressure independently.
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
        ; B9: NO pulse restart here. On real hardware a note-on resets the
        ; voice's WAVE position (`vs.wavepos = ins_wave[i]` in execute(), the
        ; VWI reload just below) but deliberately does NOT touch `v_pwidth` --
        ; the width accumulator carries across notes, which is precisely the
        ; continuity B8's from-zero output capture could not express. Since
        ; the pulse program now IS the wave program, resetting VWI restarts
        ; the delta sequence while PW_ACC keeps its phase: correct by
        ; construction, with no extra code.
        ; WAVE + FILTER restart -- NOT-TIED ONLY (real bug found + fixed this
        ; session, see BLACKBIRD.md/task report): this used to live under the
        ; `pn_tied:` label below, so BOTH the tied and not-tied paths fell
        ; through into it -- every tied note was silently restarting the
        ; wave program AND repositioning the global filter, when real
        ; hardware's BlackbirdSim.execute() explicitly does NEITHER for a
        ; legato note (`y = vs.pendins; ... if y == 0xFF: pass  # legato --
        ; no register effect here` -- wavepos/ins_wave and zp_filtpos are
        ; ONLY touched in the genuine-instrument-select branch, which legato
        ; explicitly bypasses). Found via a live py65 trace on Glyptodont: a
        ; 17-note tied chromatic run (voice 2, ticks 56-72, instrument 4)
        ; was retriggering the filter's SET row every single tick instead of
        ; letting its lone ADD ramp run uninterrupted for ~40+ ticks, as real
        ; hardware does -- confirmed the sim's own $D416 trace climbs
        ; smoothly for ~220 frames with no reset, while the (buggy) driver
        ; cycled the same 5 values (40-44) forever. FM restart (below,
        ; `pn_tied:`'s own remaining body) stays UNCONDITIONAL -- real
        ; hardware's fx/arp position (`vs.fxpos`) resets on EVERY note
        ; including tied ones (`prepare3`'s `vs.pendfx = vs.currfx` has no
        ; tie/pendins gate at all), so that part was already correct.
        lda VIWAVE,x             ; restart the wave program at the instrument's row
        sta VWI,x
        lda #$ff
        sta VGMASK,x             ; gate on (wave_step keeps the gate asserted)
        lda VIFLAGS,x            ; flag $40 -> (re)start the filter program
        and #$40
        beq pn_tied
        lda VIFILT,x
        sta F_IDX
        lda #$00
        sta F_CNT                ; force reload next frame
        lda #$01
        sta F_ACT
pn_tied:
        ; (re)start the FM offset-list at this note's FM program (set per note by
        ; the $c0-$ff command). The trigger frame shows the BASE pitch (FM_ACC=0);
        ; the first FM delta is applied the NEXT frame. ALWAYS runs (tied or
        ; not) -- see the comment above.
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
        ; B8 made PULSE per-INSTRUMENT rather than per-note-bundle. B9 goes
        ; one step further and makes it per-WAVE-ROW, which is what hardware
        ; actually does -- so there is no pulse pointer to load here at all:
        ; INSTR_WAVE (below) selects the wave program, and the wave program
        ; carries its own pulse deltas in col1.
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

; B7 (part-boundary priming): 3-byte-per-voice tables, X-indexed exactly
; like ollo/olhi above, referencing the PLAIN SCALAR PRIME_<field>0/1/2
; constants layout.inc defines (see _write_prime_consts's own comment for
; why these tables live HERE -- a real, already-`*=`-positioned code
; location -- rather than inside layout.inc itself, which is `.include`d
; before any origin directive).
PRIME_VWI_TAB:
        .byte PRIME_VWI0, PRIME_VWI1, PRIME_VWI2
PRIME_VIWAVE_TAB:
        .byte PRIME_VIWAVE0, PRIME_VIWAVE1, PRIME_VIWAVE2
PRIME_VGMASK_TAB:
        .byte PRIME_VGMASK0, PRIME_VGMASK1, PRIME_VGMASK2
PRIME_VBASENOTE_TAB:
        .byte PRIME_VBASENOTE0, PRIME_VBASENOTE1, PRIME_VBASENOTE2
PRIME_AD_TAB:
        .byte PRIME_AD0, PRIME_AD1, PRIME_AD2
PRIME_SR_TAB:
        .byte PRIME_SR0, PRIME_SR1, PRIME_SR2
PRIME_FLAGS_TAB:
        .byte PRIME_FLAGS0, PRIME_FLAGS1, PRIME_FLAGS2
PRIME_VIFILT_TAB:
        .byte PRIME_VIFILT0, PRIME_VIFILT1, PRIME_VIFILT2
PRIME_VWF_TAB:
        .byte PRIME_VWF0, PRIME_VWF1, PRIME_VWF2
PRIME_VIFM_LO_TAB:
        .byte PRIME_VIFM_LO0, PRIME_VIFM_LO1, PRIME_VIFM_LO2
PRIME_VIFM_HI_TAB:
        .byte PRIME_VIFM_HI0, PRIME_VIFM_HI1, PRIME_VIFM_HI2
PRIME_PW_ACC_TAB:
        .byte PRIME_PW_ACC0, PRIME_PW_ACC1, PRIME_PW_ACC2
PRIME_D402_TAB:
        .byte PRIME_D4020, PRIME_D4021, PRIME_D4022

; B8: genuine mid-program FM resume state (see do_init's own comments)
PRIME_FM_ON_TAB:
        .byte PRIME_FM_ON0, PRIME_FM_ON1, PRIME_FM_ON2
PRIME_FMP_LO_TAB:
        .byte PRIME_FMP_LO0, PRIME_FMP_LO1, PRIME_FMP_LO2
PRIME_FMP_HI_TAB:
        .byte PRIME_FMP_HI0, PRIME_FMP_HI1, PRIME_FMP_HI2
PRIME_FM_CNT_TAB:
        .byte PRIME_FM_CNT0, PRIME_FM_CNT1, PRIME_FM_CNT2
PRIME_FM_ACC_LO_TAB:
        .byte PRIME_FM_ACC_LO0, PRIME_FM_ACC_LO1, PRIME_FM_ACC_LO2
PRIME_FM_ACC_HI_TAB:
        .byte PRIME_FM_ACC_HI0, PRIME_FM_ACC_HI1, PRIME_FM_ACC_HI2
PRIME_FM_OFF_LO_TAB:
        .byte PRIME_FM_OFF_LO0, PRIME_FM_OFF_LO1, PRIME_FM_OFF_LO2
PRIME_FM_OFF_HI_TAB:
        .byte PRIME_FM_OFF_HI0, PRIME_FM_OFF_HI1, PRIME_FM_OFF_HI2

; B3: row-indexed tempo schedule (see do_row + CUR_TEMPO's declaration above).
; Placed here, UNPINNED, in the natural ~311-byte gap between the code above
; (ends ~$1595) and the reserved playback-state region ($16cc-$1702) -- 4
; parallel <=64-entry byte tables (256 bytes worst case), well inside the gap.
; TEMPO_SCHED_LEN comes from layout.inc (per-song, generated by
; bin/build_blackbird_native_song.py's extract_tempo_schedule()).
tempo_sched_row_lo:
        .include "tempo_sched_row_lo.inc"
tempo_sched_row_hi:
        .include "tempo_sched_row_hi.inc"
tempo_sched_t1:
        .include "tempo_sched_t1.inc"
tempo_sched_t2:
        .include "tempo_sched_t2.inc"

; ==========================================================================
; B9 MEMORY-MAP RESHUFFLE -- read this before adding ANY table.
; ==========================================================================
; The driver owns $1000-$19FF, with two holes it must not touch: SF2II's
; reserved playback-state region $16CC-$1702, and this driver's OWN private
; state block $1980-$19E1 (VWI..TEMPO_SCHED_IDX). EDIT_BASE is $1A00.
;
; B8 put freqtable + the FM prime tables + tempo_sched ABOVE the reserved
; region (pinned at $1710) because do_init and 11 new PRIME_*_TABs had
; outgrown the ~311-byte low gap. B9 reverses that pressure: deleting
; pulse_step (-107 bytes) and collapsing 7 pulse prime fields to 1 (-18
; bytes of table, -22 of do_init) reopens the low gap, and B9 needs a
; CONTIGUOUS 256-byte home for pwprepare that will not fit above.
;
; So: everything small (all PRIME_*_TABs + tempo_sched) now lives here in
; the low gap, and the two big fixed tables get the space above the reserved
; region all to themselves. The `.cerror` below is a REAL assemble-time
; guard on the low gap -- B8's own hard-won lesson was that a table quietly
; landing on live state ($1800 = VWI) corrupts at RUNTIME, not at assembly,
; so this is checked rather than reasoned about. bin/build_blackbird_driver_
; full.py's assemble() adds the matching checks for the two protected
; regions on the emitted image.
        .cerror * > $16CC, "low-gap tables overran SF2II's reserved $16CC region"

        * = $1710
pwprepare:
        ; B9: Blackbird's fixed 256-entry pulse-width lookup, indexed by the
        ; PW_ACC accumulator (see wave_step). Page-ALIGNED at $1710? No --
        ; $1710 is not a page boundary, so `lda pwprepare,y` costs one extra
        ; cycle on the ~50% of indices that cross into $1800. That is a
        ; deliberate trade: a genuine page alignment would have to be $1800,
        ; which collides with nothing today but leaves freqtable no
        ; contiguous home below $1980. Correctness is unaffected either way
        ; (alignment is purely a cycle optimisation), and this driver is not
        ; cycle-bound.
        .include "pwprepare.inc"

        * = $1810
freqtable:
        ; Pinned ABOVE the playback-state region ($16cc-$1702) so it can
        ; never collide with it, exactly as before -- only the address moved
        ; ($1710 -> $1810) to make room for pwprepare.
        .include "freqtable.inc"

        .cerror * > $1980, "freqtable overran the driver's private state block at $1980"
