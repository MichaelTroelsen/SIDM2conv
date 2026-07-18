		.ext	unpackbufs
		.ext	zp_base

		.ext	INS_RESTART
		.ext	INS_RESTART2

		.ext	fxtable
		.ext	wavetable
		.ext	filttable

		.ext	fx_start
		.ext	ins_ad
		.ext	ins_sr
		.ext	ins_wave
		.ext	ins_filt

		.ext	streamstart

zp_bufs		= zp_base+$0	; words at 0-1, 7-8, e-f
zp_inptr	= zp_base+$2	; word
zp_trwpos	= zp_base+$4
zp_pendoob	= zp_base+$5
zp_master	= zp_base+$6
zp_filtpos	= zp_base+$9
zp_tempo	= zp_base+$a
zp_extsync	= zp_base+$d

; =============================================================================
; Encoding (in order of appearence)
;	f9-ff	Out-of-band data		only in voice 3
;	c9-f8	Arpeggio
;	80	Gate off			\_ at most one
;	81	Legato				|
;	83-b2	Instrument			/
;	00-7f	Note (lsb is delay-bit)		\_ at most one
;	b8-c7	Delay (low 4 bits)		/
; =============================================================================

; =============================================================================
; Entry points at * and *+3
; (12 for jsr/rts)
; Prepare1, 12 + 17 + 336 + 165 + 563	= 1093
; Prepare2, 12 + 17 + 336 + 197 + 563	= 1125
; Prepare3, 12 + 17 + 336 + 206 + 563	= 1134
; Execute, 12 + 9 + 541 + 563		= 1125
; --> 18 rasterlines max
; =============================================================================

#if REPEAT
		.seg	seg_rplay
#else
		.seg	seg_play
#endif

playorg
		jmp	initroutine
playroutine
		.(
		lax	`zp_master
		beq	do_execute

		sbx	#7
+stx_unpackvoice
		stx	`zp_master
		cpx	#3*7
		bcs	nounpack

		jmp	unpackvoice
nounpack
		jmp	everyframe
do_execute
		jmp	execute
		.)

; =============================================================================
; Run timer, fetch oob and fx commands
; 63 + 2 * 47 - 1 + 9 = 165
; =============================================================================

prepare1
		.(
vloop
		inc	v_trtimer,x
		bmi	vskip

		lda	(zp_bufs,x)
		cmp	#$f9
		bcc	no_oob

		sta	`zp_pendoob
		inc	`zp_bufs,x
		lda	(zp_bufs,x)
		clc
no_oob
		sbc	#$c8-1
		bcc	no_fx

		inc	`zp_bufs,x
		sta	v_currfx,x
		sta	v_pendfx,x
no_fx
vskip
		txa
		sbx	#7
		bpl	vloop

		lda	#<prepare2
		sta	preparejmp+1
		jmp	everyframe
		.)

; =============================================================================
; Check timer, fetch ins command, peek at note command, do hard restart
; 3 * 63 - 1 + 9 = 197
; =============================================================================

prepare2
		.(
vloop
		lda	v_trtimer,x
		bmi	vskip

		lda	(zp_bufs,x)
		bpl	got_note

		cmp	#$b8
		bcs	vskip

		inc	`zp_bufs,x
		sbc	#$82-1

		bmi	got_special

		sta	v_currins,x
noteback
		sta	v_pendins,x

		cmp	#INS_RESTART+1
		bcc	norestart

		lda	#0
		sta	$d406,x
		lda	#$fe
		sta	v_wavemask,x
norestart
vskip
		txa
		sbx	#7
		bpl	vloop

		lda	#<prepare3
		sta	preparejmp+1
		jmp	everyframe
got_note
		lda	v_currins,x
		bpl	noteback	; always
got_special
		sta	v_pendins,x
		bmi	vskip		; always
		.)

; =============================================================================
; Check timer, fetch note or delay-command
; 3 * 69 - 1 = 206
; =============================================================================

prepare3
		.(
vloop
		lda	v_trtimer,x
		bmi	vskip

		lda	(zp_bufs,x)
		bmi	got_delay

		lsr
		sta	v_pendnote,x

		lda	v_pendins,x
		bne	alreadyins	; gate-off or legato

		lda	v_currins,x
		sta	v_pendins,x
alreadyins
		lda	v_currfx,x
		sta	v_pendfx,x

		lda	#$ff
		rol
got_delay
		ora	#$f0
		sta	v_trtimer,x
		inc	`zp_bufs,x
vskip
		txa
		sbx	#7
		bpl	vloop

		;jmp	everyframe
		.)

; =============================================================================
; Code that runs on each frame. Reads the fx-, wave- and filter tables.
; 2 + (31 + 46 + 89) * 3 - 2 + 65 = 563 cycles
; =============================================================================

everyframe
		.(
		ldx	#14
vloop
		ldy	v_fxpos,x
		lda	fxtable+1,y
		bmi	dofxjump

		lda	#0
dofxjump
		sec
		adc	v_fxpos,x
		sta	v_fxpos,x
		lda	fxtable,y
		beq	fixedfreq
	; 31
		.(
		clc
		adc	v_basepitch,x
		ror
		bcc	fractional_x0
fractional_x1
		lsr
		tay
		bcc	fractional_01
fractional_11
		lda	freq_lsb,y
		; no clc, adds small consistent error
		adc	freq_lsb+19+1,y
		sta	$d400,x
		lda	freq_msb,y
		adc	freq_msb+19+1,y
		jmp	freqdone1
+fixedfreq
		lda	#$ff
		sta	$d400,x
		bmi	freqdone1	; always
fractional_01
		lda	freq_lsb+19,y
		;clc
		adc	freq_lsb+1,y
		sta	$d400,x
		lda	freq_msb+19,y
		adc	freq_msb+1,y
		jmp	freqdone1
fractional_x0
		lsr
		tay
		bcs	fractional_10
fractional_00
		lda	freq_lsb+24,y
		sta	$d400,x
		lda	freq_msb+24,y
		jmp	freqdone1
fractional_10
		lda	freq_lsb+12,y
		; no clc, adds small consistent error
		adc	freq_lsb+12+1,y
		sta	$d400,x
		lda	freq_msb+12,y
		adc	freq_msb+12+1,y
freqdone1
		sta	$d401,x
freqdone
		.)
	; 46
		ldy	v_wavepos,x
		lda	wavetable,y
		cmp	#$c0
		bcc	nojump

		;sec
		adc	v_wavepos,x
		tay
		lda	wavetable,y
nojump
		and	v_wavemask,x
		sta	$d404,x
		asl
		bpl	nopulse

		tya
		;clc
		adc	#2
		sta	v_wavepos,x

		lda	wavetable+1,y
		bmi	pwset

		;clc
		adc	v_pwidth,x
		.byt	$80	; nop imm, eats the asl
pwset
		asl

		sta	v_pwidth,x
		tay
		lda	pwprepare,y
		sta	$d402,x
		sta	$d403,x
postpulse
		txa
		sbx	#7
		bmi	vdone

		jmp	vloop
nopulse
		iny
		tya
		sta	v_wavepos,x
		jmp	postpulse
	; 89
vdone
	; * 3 - 2
		.)

		.(
		ldy	`zp_filtpos
		lda	filttable+3,y
		bmi	filtjump

		lda	#2
filtjump
		sec
		adc	`zp_filtpos
		sta	`zp_filtpos

		lda	filttable,y
		sta	$d418
		lda	filttable+1,y
		sta	$d417
		lda	filttable+2,y
		asl
		bcs	coset

		cmp	#$80
		ror
		;clc
+m_cutoff	= * + 1
		adc	#$80
		bvs	filtdone
coset
		sta	m_cutoff
		eor	#$80
		sta	$d416
filtdone
		.)
	; 65
		rts

; =============================================================================
; Execute pending events.
; 136 + 385 + 20 = 541
; =============================================================================

sync_error
		; main thread not waiting for sync. i/o trouble? hold playback
		jmp	everyframe
execute
		.(
		lda	`zp_pendoob
		lsr
		bcc	no_sync

		lsr	`zp_extsync
		bcc	sync_error
no_sync
		lsr
		bcc	no_tempo

		tax
		lda	`zp_inptr
		;sec
		sbc	#2
		sta	`zp_inptr
		bcs	noc1

		dec	`zp_inptr+1
noc1
		ldy	#2
		lda	(zp_inptr),y
		sta	`zp_tempo
		dey
		lda	(zp_inptr),y
		sta	m_groove
		txa
no_tempo
		lsr
		bcc	no_eos

		lda	`zp_inptr
		;sec
		sbc	#2
		sta	`zp_inptr
		bcs	noc2

		dec	`zp_inptr+1
noc2
		ldy	#2
		lda	(zp_inptr),y
		tax
		dey
		lda	(zp_inptr),y
		sta	`zp_inptr
		stx	`zp_inptr+1
#if REPEAT
		lda	`zp_pendoob
		and	#1
		bne	norepeat

		ldx	`zp_bufs+14
		stx	v_trwpos+14
		lax	`zp_bufs+7
		sbx	#256-7
		stx	v_trwpos+7
		lax	`zp_bufs+0
		sbx	#256-7
		stx	v_trwpos+0
norepeat
#endif
no_eos
		lda	#0
		sta	`zp_pendoob
		.)
	;108 - 4 (at most one page crossing) + 32 (repeat)

		.(
		ldx	#14
vloop
		lda	v_pendnote,x
		asl
		asl
		sta	v_basepitch,x

		ldy	v_pendfx,x
		beq	no_fx

		lda	fx_start-1,y
		sta	v_fxpos,x
no_fx
		ldy	v_pendins,x
		beq	ins_done

		bpl	no_special

		tya
		cmp	#$fe		; fe = gate off, ff = legato
		bne	ins_done

		sta	v_wavemask,x
		beq	ins_done	; always
no_special
	; 37
		cpy	#INS_RESTART2+1
		bcc	restart01

		lda	#$0f
		sta	$d406,x
restart01
		lda	#$ff		; counter = 0..9
		sta	v_wavemask,x	; counter = 2..11

		lda	ins_filt-1,y	; counter = 7..16
		beq	nograbfilt	; counter = 11..20

		sta	`zp_filtpos	; counter = 13..22
nograbfilt
		lda	ins_wave-1,y	; counter = 14..25
		sta	v_wavepos,x	; counter = 18..29

		cpy	#INS_RESTART+1	; counter = 23..34
		bcc	norestart	; counter = 25..36

		lda	#$00		; counter = 27..38
		sta	$d405,x		; counter = 29..40
		lda	#$01		; counter = 34..45
		sta	$d404,x		; counter = 36..47

		; Hard-restart 1
		; Gate is enabled with adsr=0000
		; and the correct adsr is set immediately afterwards.
		; Hard-restart 2
		; Switch to rate 0 with counter > 32
		; to trigger second wraparound.
		; Decay rate bug is avoided for both cases.
norestart
		lda	ins_ad-1,y
		sta	$d405,x
		lda	ins_sr-1,y
		sta	$d406,x
ins_done
		lda	#0
		sta	v_pendfx,x
		sta	v_pendins,x

		txa
		sbx	#7
		bpl	vloop
		.)
	;2 + 3 * 128 - 1 = 385

		lda	`zp_tempo
		sta	`zp_master
m_groove	= * + 1
		eor	#0
		sta	`zp_tempo

		lda	#<prepare1
		sta	preparejmp+1
		jmp	everyframe

; =============================================================================
; Unpack more track data for voice x/7 (0-2).
; 37 + 34 + 7 * 18 - 1 + 18 = 214 (read 7 bytes)
; 38 + 55 + 229 - 1 + 15 = 336 (copy 10 notes)
; Copying 10 notes would require 10 * 24 = 240 cycles.
; But the cruncher ensures that the copy loop needs at most 229 cycles.
; =============================================================================

stopstream
		ldx	`zp_trwpos
		lda	#$c0		; keep reading $c0 after end of song
		ldy	#1
		bne	poststop	; always

unpackvoice
		.(
		lda	`zp_bufs+1,x
		sta	m_buf2+2
		sta	m_buf3+2

		; time to unpack the next piece of compressed data?

		lda	v_trwpos,x
		cmp	`zp_bufs,x	; writepos - readpos = bytes_in_buf
		bmi	postunpack	; at least 128 bytes in buf, hold the flow

		sta	`zp_trwpos

		; control byte is tttttnnn
		; if t = 0, read n literal bytes
		; if t > 0, copy n + 3 bytes with transpose t - 16, offset follows
		; t = 0, n = 0 indicates stream end

		ldy	#0
		lax	(zp_inptr),y
		and	#$f8
		bne	copy
	; 37

		; literal

		lda	m_buf2+2
		sta	m_buf1+2

		txa
		beq	stopstream

		tay

		eor	#$ff	; 01 -> fe, 02 -> fd...
		clc
		adc	`zp_inptr
		sta	`zp_inptr
		bcs	noc1

		dec	`zp_inptr+1
noc1
		ldx	`zp_trwpos
	; 34
litloop
		lda	(zp_inptr),y
+poststop
+m_buf1
		sta	!0,x
		inx
		dey
		bne	litloop
	; 18 * 7 - 1

		txa
		jmp	postliteral
copy
		lsr
		lsr
		;clc
		sbc	#$20-1
		sta	m_transp
		lda	#$07
		sbx	#$fd	; x becomes number of bytes to copy

		lda	`zp_inptr
		;clc
		sbc	#2-1
		sta	`zp_inptr
		bcs	noc2

		dec	`zp_inptr+1
noc2
		txa
		clc
		adc	`zp_trwpos
		sta	m_copyend

		iny
#if REPEAT
		clc
		adc	(zp_inptr),y
		tax
#else
		lax	(zp_inptr),y
#endif
		ldy	`zp_trwpos
	; 51 + 4 (repeat)
copyloop
+m_buf2
		lda	!0,x
		bmi	notransp

		clc
m_transp	= * + 1
		adc	#0
notransp
+m_buf3
		sta	!0,y
		inx
		iny
m_copyend	= * + 1
		cpy	#0
		bne	copyloop

		tya
postliteral
		ldx	`zp_master
		sta	v_trwpos,x
		.)
postunpack
		ldx	#14
preparejmp
		jmp	prepare1	; opcode replaced with rts during init

; =============================================================================
; Data
; =============================================================================

v_pwidth
		.byt	0
v_trwpos
		.byt	0
v_pendnote
		.byt	0
v_pendfx
		.byt	0
v_pendins
		.byt	0
v_wavemask
		.byt	$fe
v_trtimer
		.byt	$ff

		.byt	0,0,0,0,0,$fe,$ff
		.byt	0,0,0,0,0,$fe,$ff
v_fxpos
		.byt	0
v_currfx
		.byt	0
v_currins
		.byt	0
v_basepitch
		.byt	0
v_wavepos
		.byt	0
		.byt	0,0
		.dsb	7,0
		.dsb	5,0

		.dsb	(playorg + $400 - 207 - *), $ee
freq_msb
		.byt	$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01
		.byt	$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$02,$02,$02,$02,$02
		.byt	$02,$02,$03,$03,$03,$03,$03,$04,$04,$04,$04,$05,$05,$05,$06,$06
		.byt	$06,$07,$07,$08,$08,$09,$09,$0a,$0a,$0b,$0c,$0d,$0d,$0e,$0f,$10
		.byt	$11,$12,$13,$14,$15,$17,$18,$1a,$1b,$1d,$1f,$20,$22,$24,$27,$29
		.byt	$2b,$2e,$31,$34,$37,$3a,$3e,$41,$45,$49,$4e,$52,$57,$5c,$62,$68

		; tables overlap with 15 bytes
freq_lsb
		.byt	$6e,$75,$7c,$83,$8b,$93,$9c,$a5,$af,$b9,$c4,$d0,$dd,$ea,$f8,$07
		.byt	$16,$27,$39,$4b,$5f,$74,$8a,$a1,$ba,$d4,$f0,$0e,$2d,$4e,$71,$96
		.byt	$be,$e7,$14,$42,$74,$a9,$e0,$1b,$5a,$9c,$e2,$2d,$7b,$cf,$27,$85
		.byt	$e8,$51,$c1,$37,$b4,$38,$c4,$59,$f7,$9d,$4e,$0a,$d0,$a2,$81,$6d
		.byt	$67,$70,$89,$b2,$ed,$3b,$9c,$13,$a0,$45,$02,$da,$ce,$e0,$11,$64
		.byt	$da,$76,$39,$26,$40,$89,$04,$b4,$9c,$c0,$23,$c8,$b4,$eb,$72,$4c
		.byt	$80,$12,$08,$68,$39,$80,$45,$90,$68,$d6,$e3,$99,$00,$24,$10

		; this becomes page-aligned
pwprepare
		.byt	$8f,$7f,$6f,$5f,$4f,$3f,$2f,$1f,$0f,$fe,$ee,$de,$ce,$be,$ae,$9e
		.byt	$8e,$7e,$6e,$6e,$5e,$4e,$3e,$2e,$1e,$0e,$fd,$ed,$dd,$cd,$bd,$ad
		.byt	$9d,$8d,$7d,$6d,$5d,$5d,$4d,$3d,$2d,$1d,$0d,$fc,$ec,$dc,$cc,$bc
		.byt	$ac,$9c,$8c,$7c,$6c,$5c,$4c,$4c,$3c,$2c,$1c,$0c,$fb,$eb,$db,$cb
		.byt	$bb,$ab,$9b,$8b,$7b,$6b,$5b,$4b,$3b,$3b,$2b,$1b,$0b,$fa,$ea,$da
		.byt	$ca,$ba,$aa,$9a,$8a,$7a,$6a,$5a,$4a,$3a,$2a,$2a,$1a,$0a,$f9,$e9
		.byt	$d9,$c9,$b9,$a9,$99,$89,$79,$69,$59,$49,$39,$29,$19,$19,$09,$f8
		.byt	$e8,$d8,$c8,$b8,$a8,$98,$88,$78,$68,$58,$48,$38,$28,$18,$08,$08
		.byt	$08,$08,$18,$28,$38,$48,$58,$68,$78,$88,$98,$a8,$b8,$c8,$d8,$e8
		.byt	$f8,$09,$19,$19,$29,$39,$49,$59,$69,$79,$89,$99,$a9,$b9,$c9,$d9
		.byt	$e9,$f9,$0a,$1a,$2a,$2a,$3a,$4a,$5a,$6a,$7a,$8a,$9a,$aa,$ba,$ca
		.byt	$da,$ea,$fa,$0b,$1b,$2b,$3b,$3b,$4b,$5b,$6b,$7b,$8b,$9b,$ab,$bb
		.byt	$cb,$db,$eb,$fb,$0c,$1c,$2c,$3c,$4c,$4c,$5c,$6c,$7c,$8c,$9c,$ac
		.byt	$bc,$cc,$dc,$ec,$fc,$0d,$1d,$2d,$3d,$4d,$5d,$5d,$6d,$7d,$8d,$9d
		.byt	$ad,$bd,$cd,$dd,$ed,$fd,$0e,$1e,$2e,$3e,$4e,$5e,$6e,$6e,$7e,$8e
		.byt	$9e,$ae,$be,$ce,$de,$ee,$fe,$0f,$1f,$2f,$3f,$4f,$5f,$6f,$7f,$8f

#if REPEAT
		.seg	seg_rinit
#else
		.seg	seg_init
#endif

initroutine
		.(
		lda	#<streamstart
		sta	`zp_inptr
		lda	#>streamstart
		sta	`zp_inptr+1

		lda	#<prepare1
		sta	preparejmp+1
		lda	#0
		sta	`zp_extsync
		sta	`zp_pendoob
		sta	`zp_filtpos

		ldx	#$18
clr
		sta	$d400,x
		dex
		bpl	clr

		lda	#$80
		sta	m_cutoff

		ldy	#>(unpackbufs+$200)
		ldx	#14
vloop1
		sty	`zp_bufs+1,x
		dey
		lda	#0
		sta	`zp_bufs,x
		sta	v_trwpos,x
		sta	v_pendfx,x
		sta	v_pendins,x
		lda	#$ff
		sta	v_trtimer,x
		sbx	#7
		bpl	vloop1

		lda	#$60
		sta	preparejmp
		ldx	#7
		jsr	stx_unpackvoice
		jsr	playroutine
		lda	#$4c
		sta	preparejmp

		lda	#3*7
		sta	`zp_master

		rts
		.)
