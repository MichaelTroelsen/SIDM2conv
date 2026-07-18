;---------------------------------------
;SDI speedplayer 2.1 (c)20/12/2012 SHAPE
;  Geir Tjelta & Glenn Rune Gallefoss
;---------------------------------------
sid      = $d400
mzero    = $fe   ;player zeropage(fe+ff)
speed    = 8     ;calls per frame
system   = 1     ;1=pal 0=ntsc
;---------------------------------------
rem{CBM-@}4ch  = 1  ;1 = ignore 4th channel
rem{CBM-@}det  = 0  ;1 = ignore detune (z8/z9)
rem{CBM-@}gout = 0  ;1 = ignore gate timeout
rem{CBM-@}1wf  = 0  ;1 = ignore 1st WFPRG byte
rem{CBM-@}wfd  = 0  ;1 = ignore fe wf hold cmd
rem{CBM-@}adsr = 1  ;1 = ignore fd wf adsr cmd
rem{CBM-@}mp   = 1  ;1 = ignore fb wf puls cmd
rem{CBM-@}wfr  = 1  ;1 = ignore fa wfp rep cmd
rem{CBM-@}wf0  = 1  ;1 = ignore f0-f7 wf d415
rem{CBM-@}puw  = 1  ;1 = ignore eb-ee wf pulse
rem{CBM-@}pu   = 0  ;1 = ignore pulse routine
rem{CBM-@}we2  = 1  ;1 = ignore e2-e7 wf noise
rem{CBM-@}arp  = 0  ;1 = ignore arp routine
rem{CBM-@}fi   = 0  ;1 = ignore filter routine
rem{CBM-@}fspd = 1  ;1 = ignore filter speed
rem{CBM-@}glid = 0  ;1 = ignore glide routine
rem{CBM-@}vib  = 0  ;1 = ignore vibrato rout
rem{CBM-@}cc   = 1  ;1 = ignore crazy com vib
rem{CBM-@}fad  = 1  ;1 = ignore fadeout routin
rem{CBM-@}gat  = 1  ;1 = ignore seq GAT/FLGcmd
rem{CBM-@}f20  = 1  ;1 = ignore seq 20 filtcmd
rem{CBM-@}wfo  = 1  ;1 = ignore seq wf ora cmd
rem{CBM-@}voff = 0  ;1 = ignore voice on/off
rem{CBM-@}trkl = 1  ;1 = max $ff track size
rem{CBM-@}tp   = 0  ;1 = ignore tempo programs
;NB!!^^ Enter song's tempo in offset "s"
;Save cycles if only single tempos used.
;---------------------------------------
rem{CBM-@}opt  = 0  ;1 = select spdchan
spdchan  = %00000111
;---------------------------------------
frqsum   = rem{CBM-@}det*rem{CBM-@}cc
gatsum   = rem{CBM-@}gout*rem{CBM-@}adsr
addsum   = rem{CBM-@}glid*rem{CBM-@}vib

         *= $0c00

vzp      = $05
fzp      = $07
dzp      = $08

clock    = $0568+6+$28
tun      = $0590+6+$28
fch      = $05b8+6+$28

vscr     = $0798+$28

         sei
         cld
         jsr $ff84
         ldy #1
         lda #$81
         bit $d011
         bmi *-3
         bit $d011
         bpl *-3
         ldx #$72
         dex
         bpl *-1
         bit $d011
         bmi pa1
         tya
         dey
pa1      sty $02a6
         sta $dc0e
         lda #<info
         ldy #>info
         jsr $ab1e
         lda #$2f
         sta tun+2
         lda #s-c-1
         jsr getall
         stx tun+3
         sta tun+4
         lda #$16
         sta $d018
         sei
         lda #<int
         sta $0314
         lda #>int
         sta $0315
         lda #$7f
         sta $dc0d         
         ldx #1
         stx $d01a
         dex
         stx zz+1
         stx fzp
         stx dzp
         stx $d012
         bit $dc0d
         cli
         jmp start
         
ffe4     jsr $ff9f
         jsr $ffe4
         beq *-6

kfade    cmp #$46
         bne ksp
         lda #$1f
         jsr fadeout
         jmp ffe4
         *= *-((*-kfade)*rem{CBM-@}fad)

ksp      ldx zz+1
         cmp #$20
         bne kpl
         jmp start
kpl
         cmp #$2b
         bne kmin
         inx
         cpx #s-c
         bcc *+4
         ldx #0
         jmp start

kmin     cmp #$2d
         bne voic
         dex
         bpl *+4
         ldx #s-c-1
         jmp start

voic     cmp #$31
         bcc vo1
         cmp #$34
         bcs vo1
         sec
         sbc #$31
         tax
         beq *+11
         clc
         lda #0
         adc #7
         dex
         bne *-3
         tax
         lda seqbyte,x
         bmi vo1
         lda voff+1
         eor chanon,x
         sta voff+1
         *= *-((*-voic)*rem{CBM-@}voff)
vo1      jmp ffe4
start    sei
         stx zz+1
zz       ldx #0
         jsr init
         jsr setod
         cli
         jmp ffe4


int      inc $d019

         lda fzp
         cmp #speed
         bcc sp2
         lda #$1b
         sta dd11+1
         lda #0
         sta fzp
         sta dzp
sp2      php
         lda dzp
         sta $d012
dd11     lda #$1b
         sta $d011
pal      lda #312/speed
         *= *-((*-pal)*(1-system))
ntsc     lda #262/speed
         *= *-((*-ntsc)*system)
         clc
         adc dzp
         sta dzp
         bcc sp5
         lda #$9b
         sta dd11+1
sp5      plp
         beq spol
         lda #$0b
         sta $d020
         jsr splay
         lda #0
         sta $d020
         beq sp4
spol     dec $d020
         jsr play
         lda #0
         sta $d020
         lda #$7f
         sta $dc00
         lda $dc01
         cmp #$fd
         beq spol
         cmp #$df
         beq gogg
         jsr tod
r{CBM-@}voffx  jsr voices
         *= *-((*-r{CBM-@}voffx)*rem{CBM-@}voff)
vo{CBM-@}fi2   jsr fchan
         *= *-((*-vo{CBM-@}fi2)*rem{CBM-@}fi)
         jsr song
sp4      inc fzp
         jmp $ea81

gogg     jsr $fda3
         jsr $fd15
         jsr $e518
         sei
         jmp $9000

song     lda zz+1
         jsr getall
         stx tun
         sta tun+1
         rts
getall   pha
         lsr a
         lsr a
         lsr a
         lsr a
         tay
         lda tall,y
         tax
         pla
         and #$0f
         tay
         lda tall,y
         rts
setod    lda #0
         sta $dc0f
         sta $dc0b
         sta $dc0a
         sta $dc09
         sta $dc08
         sta $d020
         sta $d021
         bit $dc08         
         rts
tod      lda #$3a
         sta clock+2
         ldy #4
         lda $dc09
         jsr getod
         ldy #1
         lda $dc0a
getod    tax
         and #$0f
         ora #$30
         sta clock,y
         txa
         lsr a
         lsr a
         lsr a
         lsr a
         ora #$30
         dey
         sta clock,y
         rts
voices   lda #<vscr+8+(4*(1-rem{CBM-@}4ch))
         sta vzp
         lda #>vscr+8+(4*(1-rem{CBM-@}4ch))
         sta vzp+1
         ldx #channels*7
vo4      ldy #2
         lda voff+1
         and chanon,x
         bne vo2
vo3      lda off,y
         sta (vzp),y
         dey
         bpl vo3
         bne vo5

vo2      lda on,y
         sta (vzp),y
         dey
         bpl vo2
vo5      lda vzp
         sec
         sbc #$04
         bcs *+4
         dec vzp+1
         sta vzp
         txa
         sec
         sbc #7
         tax
         bpl vo4
         rts

fchan    lda filtch+1
vo{CBM-@}fi    ora filtena+1
         *= *-((*-vo{CBM-@}fi)*rem{CBM-@}f20)

         ldx #$30
         lsr a
         bcc *+4
         ldx #$31
         stx fch

         ldx #$30
         lsr a
         bcc *+4
         ldx #$31
         stx fch+2

         ldx #$30
         lsr a
         bcc *+4
         ldx #$31
         stx fch+4
         rts
         *= *-((*-fchan)*rem{CBM-@}fi)

tall     .text "0123456789"
         .byte 1,2,3,4,5,6
off      .byte $0f,$06,$06
on       .byte $0f,$0e,$20
info     .byte $05,$93,$08,$1e
         .text "SDI v2.1 Speed Player"
         .byte $0d,$0d
         .byte $5f
         .text "    :FFWD"
         .byte $0d
         .text "SPACE:Restart"
         .byte $0d
         .text "+/-  :Subtunes"
         .byte $0d
         .text "1-3  :Voices"
         .byte $0d
         .text "F    :Fade"
         .byte $0d
         .text "CBM  :Exit"
         .byte $0d,$0d,$0d
         .text "Clock:"
         .byte $0d
         .text "Song :"
         .byte $0d
         .text "Fchan:"
         .byte 0

;------------------START OF DRIVER/DATA-

         *= $1000

         jmp init    ;Call with X
         jmp play
r{CBM-@}fad3   jmp fadeout ;negative # =down
         *= *-((*-r{CBM-@}fad3)*rem{CBM-@}fad)
         jmp splay

         .text "-speed player v2.1 "
         .text "by gt+grg-"

chanon   = *
chanoff  = *+1
trklo    = *+2
trkhi    = *+3
tdelay   = *+4
tracky   = *+5
trackhi  = *+6
         .byte $01,$fe,0,0,0,0,0
         .byte $02,$fd,0,0,0,0,0
         .byte $04,$fb,0,0,0,0,0
chanx    .byte $80,$7f,0,0,0,0,0

transp   = *+1
dur      = *+2
duration = *+3
seqp     = *+4
sound2   = *+5
note2    = *+6
         .byte $00,0,0,0,0,0,0
         .byte $07,0,0,0,0,0,0
         .byte $0e,0,0,0,0,0,0
fadeco   .byte 0,0,0,0,0,0,0
release  = *
seqsust  = *+1
seqbyte  = *+2
filtre   = *+3
glidadd2 = *+4
wf{CBM-@}ora   = *+5
wf{CBM-@}ora2  = *+6
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
arpnum2  = *
arple    = *+1
srco     = *+2
sound    = *+3
note     = *+4
gate     = *+5
gatedec  = *+6
         .byte $80,0,0,0,0,0,0
         .byte $80,0,0,0,0,0,0
         .byte $80,0,0,0,0,0,0
         .byte $00
arpnum   = *
attack   = *+1
sustain  = *+2
glidadd  = *+3
glidto   = *+4
addlo    = *+5
addhi    = *+6
         .byte $80,0,0,0,0,0,0
         .byte $80,0,0,0,0,0,0
         .byte $80,0,0,0,0,0,0
arpde    = *
addval{CBM-@}l = *+1
addval{CBM-@}h = *+2
vible    = *+3
vibwid   = *+4
vibdir   = *+5
vibdec   = *+6
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0

pulsco   = *
pulseor  = *+1
pulsdel  = *+2
pulsle   = *+3
pulsle2  = *+4
pulsdec  = *+5
pulsdec2 = *+6
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
pulslo   = *
pulslo2  = *+1
pulshi   = *+2
pulshi2  = *+3
pulshld  = *+4 ;uses 2 but needs only 1
         ;6 free
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0

wf       = *
wfp      = *+1
wf{CBM-@}del   = *+2
wf{CBM-@}repet = *+3
detunlo  = *+4
detunhi  = *+5
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0
         .byte 0,0,0,0,0,0,0

filtspd  .byte 0
         *= *-((*-filtspd)*rem{CBM-@}fspd)



splay    ldx #$0e
lop1     lda voff+1
         bne *+5
         jmp clear{CBM-@}wav
         *= *-((*-lop1)*rem{CBM-@}voff)
speed1   jsr spulse
         ldx #$07
         jsr spulse
         ldx #0
         *= *-((*-speed1)*rem{CBM-@}opt)
         
speed2   lda #spdchan
         and chanon,x
         beq zoff
         jsr spulse
zoff     lda chanx,x
         tax
         bpl speed2
         rts
         *= *-((*-speed2)*(1-rem{CBM-@}opt))


spulse
r{CBM-@}mp8    stx x+1
         *= *-((*-r{CBM-@}mp8)*rem{CBM-@}mp)
pulse
;----------------------MULTI PULSE ROUT-
r{CBM-@}mp1    lda pulsle2,x
         beq pulse3
         dec pulsco,x
         bne pulse2
         lda pulsdel,x
         sta pulsco,x
         lda pulseor,x
         eor #1
         sta pulseor,x
pulse2   lda pulseor,x
         beq pulse3
         inx
         *= *-((*-r{CBM-@}mp1)*rem{CBM-@}mp)
;----------------------PULSE PROGRAM----
pulse3   lda pulsle,x
         bmi no{CBM-@}pulse
         bne go{CBM-@}pulse
no{CBM-@}pulse
r{CBM-@}mp7    ldx x+1
         *= *-((*-r{CBM-@}mp7)*rem{CBM-@}mp)
jpwf     rts
         .word wfrout 
go{CBM-@}pulse asl a
         asl a
         tay
         stx mzero+1
         lda pulsdec,x
         bne bn22
         sta pulshld,x
         lda #2
         sta pulsdec,x
         bcs bn22
         lda p+1-4,y
         bne ph1
         lda p+2-4,y
         sta pulshld,x
ph1
         lda p-4,y
         and #$f0
         sta pulslo,x
         lda p-4,y
         and #$0f
         sta pulshi,x
         jmp set{CBM-@}puls

bn22     lda pulshld,x
         beq ph2
         dec pulshld,x
         bne set{CBM-@}puls
         beq ph3

ph2
         lda p+1-4,y
         lsr a
         lsr a
         lsr a
         lsr a
         tax
         stx upper2+1
         lda p+1-4,y
         and #$0f
         cmp upper2+1
         bcc bn24+1
         sta upper2+1
bn24     lda #$aa
         stx lower2+1
         ldx mzero+1
         lda #$90
         dec pulsdec,x
         bne *+4
         lda #$b0
         sta branch2
         inc pulsdec,x
         lda pulslo,x
branch2  bcc bn26
         clc
         adc p+2-4,y
         sta pulslo,x
         lda pulshi,x
         adc #0
         sta pulshi,x
upper2   cmp #0
         bcs bn29
         bcc set{CBM-@}puls
bn26     sec
         sbc p+2-4,y
         sta pulslo,x
         lda pulshi,x
         sbc #0
         sta pulshi,x
         bcc *+6
lower2   cmp #0
         bcs set{CBM-@}puls
         inc pulshi,x
bn29     lda #0
         sta pulslo,x
ph3      lda p+3-4,y
         bpl *+5
         dec pulsdec,x
         dec pulsdec,x
         bne set{CBM-@}puls
         and #$7f
         sta pulsle,x
;----------------------SET PULSE VALUES-
set{CBM-@}puls
r{CBM-@}mp5    lda pulslo,x
         sta sid+2,x
         lda pulshi,x
         sta sid+3,x
         *= *-((*-r{CBM-@}mp5)*(1-rem{CBM-@}mp))

r{CBM-@}mp6    txa
         tay
         ldx x+1
         lda pulslo,y
         sta sid+2,x
         lda pulshi,y
         sta sid+3,x
         *= *-((*-r{CBM-@}mp6)*rem{CBM-@}mp)
snop     nop
         *= *-((*-pulse)*rem{CBM-@}pu)

;----------------------SET FREQUENCIES--
wfrout
r{CBM-@}det5   lda addlo,x
r{CBM-@}det6   clc
         adc detunlo,x
         *= *-((*-r{CBM-@}det6)*rem{CBM-@}det)
         sta frq{CBM-@}l+1
         lda addhi,x
r{CBM-@}det7   adc detunhi,x
         *= *-((*-r{CBM-@}det7)*rem{CBM-@}det)
         sta frq{CBM-@}h+1
         *= *-((*-r{CBM-@}det5)*frqsum)

;----------------------WAVEFORM PROGRAM-
wfrout2  ldy wfp,x
         lda w,y
         cmp #$ff
         bne wf{CBM-@}loop

r{CBM-@}wfr1   lda wf{CBM-@}repet,x
         beq norep
         dec wf{CBM-@}repet,x
         bne norep
         iny
         bne wfrout2+3
         *= *-((*-r{CBM-@}wfr1)*rem{CBM-@}wfr)
norep
         lda f,y
         tay
         lda w,y
wf{CBM-@}loop
;----------------------Program delay----
r{CBM-@}wfd1   cmp #$fe
         bne wf{CBM-@}loop2
         lda f,y
         sta wf{CBM-@}del,x
         iny
         tya
         sta wfp,x
         lda w,y
         *= *-((*-r{CBM-@}wfd1)*rem{CBM-@}wfd)
wf{CBM-@}loop2
;----------------------ADSR command-----
r{CBM-@}adsr   cmp #$fd
         bne wf{CBM-@}loop3
         iny
         lda release,x
         lsr a
         bcc no{CBM-@}adsr
         lda f-1,y
         cmp #$80
         and #$7f
         sta gatedec,x
         bcs *+7
         lda #$ff
         sta gate,x
         lda w,y
         sta sid+5,x
         lda f,y
         sta sid+6,x
no{CBM-@}adsr  iny
         lda w,y
         *= *-((*-r{CBM-@}adsr)*rem{CBM-@}adsr)
wf{CBM-@}loop3
;----------------------Multi pulse------
r{CBM-@}mp2    cmp #$fb
         bne wf{CBM-@}loop5
         lda f,y
         sta pulsle2,x
         lda #1
         sta pulsco,x
         lsr a
         sta pulsdec2,x
         iny
         lda w,y
         sta pulseor,x
         lda f,y
         sta pulsdel,x
         iny
         lda w,y
         *= *-((*-r{CBM-@}mp2)*rem{CBM-@}mp)

;----------------------WF Repeat--------
wf{CBM-@}loop5
r{CBM-@}wfr2   cmp #$fa
         bne wf{CBM-@}loop4
         lda f,y
         sta wf{CBM-@}repet,x
         iny
         lda w,y
         *= *-((*-r{CBM-@}wfr2)*rem{CBM-@}wfr)

wf{CBM-@}loop4 cmp #$f0
         bcc wf{CBM-@}puls
         sta sid+$15
         iny
         lda w,y
         *= *-((*-wf{CBM-@}loop4)*rem{CBM-@}wf0)

;----------------------GET WAVEFORM-----
wf{CBM-@}puls  cmp #$ee
         bne wf{CBM-@}puls2
         lda f,y
         sta pulslo,x
         sta sid+2,x
         and #$0f
         sta pulshi,x
         bpl wf{CBM-@}pulshi

wf{CBM-@}puls2 cmp #$ed
         bne wf{CBM-@}puls3
         lda pulslo,x
         sec
         sbc f,y
         sta pulslo,x
         sta sid+2,x
         bcs wf{CBM-@}pulshi+3
         dec pulshi,x
         bcc wf{CBM-@}pulsa

wf{CBM-@}puls3 cmp #$ec
         bne wf{CBM-@}puls4
         lda pulslo,x
         clc
         adc f,y
         sta pulslo,x
         sta sid+2,x
         bcc wf{CBM-@}pulshi+3
         inc pulshi,x
wf{CBM-@}pulsa lda pulshi,x
         jmp wf{CBM-@}pulshi

wf{CBM-@}puls4 cmp #$eb
         bne wf{CBM-@}loop6
         lda f,y
         sta sid+2,x
wf{CBM-@}pulshi
         sta sid+3,x
         iny
         lda w,y
         *= *-((*-wf{CBM-@}puls)*rem{CBM-@}puw)
wf{CBM-@}loop6
r{CBM-@}arp3
         cmp #$e2
         bcs wf{CBM-@}kik
         *= *-((*-r{CBM-@}arp3)*rem{CBM-@}we2)
         cmp #$90
         bcc *+4
         and #$7f
         *= *-((*-r{CBM-@}arp3)*rem{CBM-@}arp)
wf{CBM-@}kik
         sta wf,x
         and gate,x
r{CBM-@}wfo6   ora wf{CBM-@}ora,x
         *= *-((*-r{CBM-@}wfo6)*rem{CBM-@}wfo)
         sta sid+4,x
         iny

;----------------------WF delay counter-
r{CBM-@}wfd2   lda wf{CBM-@}del,x
         beq bn57
         dec wf{CBM-@}del,x
         jmp bn572
         *= *-((*-r{CBM-@}wfd2)*rem{CBM-@}wfd)
bn57     tya
         sta wfp,x
bn572
r{CBM-@}arp4   bcc wf{CBM-@}stand
;----------------------Arpeggio PRG-----
         lda arpnum,x
         bmi wf{CBM-@}stand
         tay
         sec
         lda arpde,x
         sbc #$40
         bcs *+5
         lda ad+1,y
         sta arpde,x
         ldy arple,x
         bcs *+5
         inc arple,x
         lda a,y
         bpl bn48
         bcs bn48
         pha
         ldy arpnum,x
         lda ad,y
         sta arple,x
         pla
         bne bn48
         *= *-((*-r{CBM-@}arp4)*rem{CBM-@}arp)

wf{CBM-@}stand lda f-1,y
         bmi bn44
bn48     clc
         adc note,x
bn44     and #$7f
         tay

         lda freqlo,y
fcode    clc
frq{CBM-@}l    adc #0
         sta sid+0,x
         lda freqhi,y
frq{CBM-@}h    adc #0
         *= *-((*-fcode)*frqsum)

fcode2   clc
         adc addlo,x
         *= *-((*-fcode2)*addsum)
         sta sid+0,x
         lda freqhi,y
fcode3   adc addhi,x
         *= *-((*-fcode3)*addsum)
         *= *-((*-fcode2)*(1-frqsum))
         sta sid+1,x
         rts

        

clear{CBM-@}wav
         sta sid+$04
         sta sid+$0b
         sta sid+$12
         jmp fade
         *= *-((*-clear{CBM-@}wav)*rem{CBM-@}voff)

channels = 3-rem{CBM-@}4ch

play     ldx #channels*7
voff     lda #0
         beq clear{CBM-@}wav
         *= *-((*-voff)*rem{CBM-@}voff)
r{CBM-@}pu13   lda #$60
         sta snop
         sta jpwf
         *= *-((*-r{CBM-@}pu13)*rem{CBM-@}pu)
;-----------------------CONDUCTOR/TEMPO-
r{CBM-@}4ch1
         bpl noc2
         *= *-((*-r{CBM-@}4ch1)*rem{CBM-@}voff)

         ldy duration+21
         bpl no{CBM-@}conduct
         lda tempo+1
         beq cond{CBM-@}dur
         cmp cur{CBM-@}tem+1
         beq cond{CBM-@}seq
noc2     jmp no{CBM-@}conduct

cond{CBM-@}dur lda dur+21
         sta duration+21

r{CBM-@}fi8    lda release+21
         asl a
         asl a
         asl a
         asl a
         sta setfi+1

         lda glidadd2+21
         bmi no{CBM-@}conduct
         sty glidadd2+21
         beq restfi
         sty filtsnd+1
         lsr a
         lsr a
         sta filtle+1
         lda #0
         sta filtdec+1
f{CBM-@}spd3   sta filtspd
         *= *-((*-f{CBM-@}spd3)*rem{CBM-@}fspd)
         beq no{CBM-@}conduct
restfi   sta filtre
         sta filtre+7
         sta filtre+14
         *= *-((*-r{CBM-@}fi8)*rem{CBM-@}fi)
         bpl no{CBM-@}conduct

cond{CBM-@}seq stx x+1
         lda #$7f
         sta arpnum2+21
         jmp seq{CBM-@}cond
cond{CBM-@}ret
r{CBM-@}voff1  lda voff+1
         bmi cond{CBM-@}on
         lda #0
         sta trk{CBM-@}tran+1
         beq no{CBM-@}conduct
         *= *-((*-r{CBM-@}voff1)*rem{CBM-@}voff)
cond{CBM-@}on  lda arpnum2+21
         bmi set{CBM-@}tem
         cmp #$7f
         beq no{CBM-@}conduct
         cmp #$40
         bcs setband
         lsr a
set{CBM-@}tem  sta tem{CBM-@}prg+1
         lda #0
         sta tem{CBM-@}y+1
r{CBM-@}fi9    beq no{CBM-@}conduct
         *= *-((*-r{CBM-@}fi9)*rem{CBM-@}fi)
setband
r{CBM-@}fi10   asl a
         asl a
         asl a
         sta band+1
         *= *-((*-r{CBM-@}fi10)*rem{CBM-@}fi)
no{CBM-@}conduct
         ldx #(channels-1)*7
         *= *-((*-r{CBM-@}4ch1)*rem{CBM-@}4ch)

;-----------------------PLAYER LOOP POS-
part1    stx x+1
r{CBM-@}gout1  lda gatedec,x
         beq bn71
         dec gatedec,x
         bne bn71
         lda #$fe
         sta gate,x
bn71
         *= *-((*-r{CBM-@}gout1)*gatsum)
         lda duration,x
         bpl bn33
tempo    lda #0
         beq setval

cur{CBM-@}tem  cmp #0
         beq *+5
bn33     jmp part2
         jmp sequ2

;-------------------SET TIE/GLIDE/NOTE--
setval   lda dur,x
         sta duration,x

r{CBM-@}voff2  lda voff+1
         and chanon,x
         beq bn33
         *= *-((*-r{CBM-@}voff2)*rem{CBM-@}voff)

         ldy note2,x
r{CBM-@}gat2   bmi r{CBM-@}gat1
         *= *-((*-r{CBM-@}gat2)*rem{CBM-@}gat)
         cpy #$5f
         beq forcevib

r{CBM-@}gli1   lda glidadd2,x
         sta glidadd,x
         bne r{CBM-@}gli2
         *= *-((*-r{CBM-@}gli1)*rem{CBM-@}glid)

fcode4   lda #0
         *= *-((*-fcode4)*(1-rem{CBM-@}glid))

         sta addlo,x
         sta addhi,x
         *= *-((*-fcode4)*addsum)

         tya
         sta note,x

bn27     lda #0
         sta vibdec,x
         *= *-((*-bn27)*rem{CBM-@}vib)

r{CBM-@}arp1   lda arpnum2,x
         sta arpnum,x
         bmi tie{CBM-@}note
         sta arpde,x
         tay
         lda ad,y
         sta arple,x
         *= *-((*-r{CBM-@}arp1)*rem{CBM-@}arp)

;--------------------SET INSTRUMENTS----
tie{CBM-@}note lda srco,x
         bne set{CBM-@}snd
         jsr wfrout
         jmp sid{CBM-@}next

r{CBM-@}gat1   tya
         sta gate,x
         jmp part2
         *= *-((*-r{CBM-@}gat1)*rem{CBM-@}gat)

forcevib lda glidadd2,x
         beq bn33
r{CBM-@}vib1   lsr a
         lsr a
         sta vible,x
         lda #0
         sta vibdec,x
         *= *-((*-r{CBM-@}vib1)*rem{CBM-@}vib)
         jmp glide

r{CBM-@}gli2   tya
         sta glidto,x
         bpl bn27
         *= *-((*-r{CBM-@}gli2)*rem{CBM-@}glid)

set{CBM-@}snd  sta gate,x
         ldy sound2,x
         lda seqsust,x
         cmp #1
         lda z2,y
         bcc bn21
         and #$0f
         ora seqsust,x
bn21     sta mzero+1
         and #$f0
         sta sustain,x
         ora #$0f
         sta sid+6,x

         lda wf,x
         ora #1
         sta sid+4,x

r{CBM-@}det1   lda z8,y
         sta detunhi,x
         lda z9,y
         sta detunlo,x
         *= *-((*-r{CBM-@}det1)*rem{CBM-@}det)

r{CBM-@}gout2  lda z3,y
         and #$1f
         asl a
         sta gatedec,x
         *= *-((*-r{CBM-@}gout2)*gatsum)

r{CBM-@}fi1    lda filtre,x
         bmi bn37
         lda z6,y
         sta filtre,x
         asl a
         bne bn45
         bcs bn37
         lda filtch+1
         and chanoff,x
         bcc bn37-3

bn45     lsr a
         sta filtle+1
         lda #0
         sta filtdec+1
f{CBM-@}spd4   sta filtspd
         *= *-((*-f{CBM-@}spd4)*rem{CBM-@}fspd)
         sty filtsnd+1
         lda filtch+1
         ora chanon,x
         sta filtch+1
         *= *-((*-r{CBM-@}fi1)*rem{CBM-@}fi)

bn37     lda z4,y
         sta vible,x
         *= *-((*-bn37)*rem{CBM-@}vib)

         lda z5,y
         beq no{CBM-@}puls
r{CBM-@}pu1    bpl pulw{CBM-@}val
         *= *-((*-r{CBM-@}pu1)*rem{CBM-@}pu)

         and #$7f
         sta sid+2,x
         sta sid+3,x
r{CBM-@}op3    lda #0
         sta pulsle2,x
         *= *-((*-r{CBM-@}op3)*rem{CBM-@}mp)
no{CBM-@}puls
r{CBM-@}pu2    lda pulsle,x
         ora #$80
         bne puls{CBM-@}off
pulw{CBM-@}val asl a
         asl a
         tay
         bcc puls{CBM-@}on
         lda sound2,x
         cmp sound,x
         beq puls{CBM-@}end

puls{CBM-@}on  lda #0
r{CBM-@}mp4    sta pulsle2,x
         *= *-((*-r{CBM-@}mp4)*rem{CBM-@}mp)
         sta pulsdec,x
         lda p-4,y
         sta sid+2,x
         sta sid+3,x
         tya
         lsr a
         lsr a
puls{CBM-@}off sta pulsle,x
puls{CBM-@}end
         *= *-((*-r{CBM-@}pu2)*rem{CBM-@}pu)

         ldy sound2,x
         lda z1,y
         ldy attack,x
         bne setatt
         ldy seqsust,x
         beq newsust
         lda #0
         beq newsust
setatt   lda #0
         sta attack,x
         sta seqsust,x
r{CBM-@}gout3  sta gatedec,x
         *= *-((*-r{CBM-@}gout3)*gatsum)
         tya
newsust  sta sid+5,x
         lda mzero+1
         sta sid+6,x

         lda #0
         sta srco,x
r{CBM-@}wfd3   sta wf{CBM-@}del,x
         *= *-((*-r{CBM-@}wfd3)*rem{CBM-@}wfd)
r{CBM-@}wfr3   sta wf{CBM-@}repet,x
         *= *-((*-r{CBM-@}wfr3)*rem{CBM-@}wfr)

r{CBM-@}pu3    lda sound2,x
         sta sound,x
         tay
         *= *-((*-r{CBM-@}pu3)*rem{CBM-@}pu)
r{CBM-@}pu4    ldy sound2,x
         *= *-((*-r{CBM-@}pu4)*(1-rem{CBM-@}pu))
         lda z0,y

r{CBM-@}1wf1   tay
         iny
         tya
         *= *-((*-r{CBM-@}1wf1)*rem{CBM-@}1wf)
r{CBM-@}1wf2   clc
         adc #1
         *= *-((*-r{CBM-@}1wf2)*(1-rem{CBM-@}1wf))
         sta wfp,x

r{CBM-@}1wf3   lda w-1,y
r{CBM-@}arp2   cmp #$90
         bcc *+4
         and #$7f
         *= *-((*-r{CBM-@}arp2)*rem{CBM-@}arp)
         sta sid+4,x

         lda f-1,y
         bmi frq{CBM-@}lock
         clc
         adc note,x
frq{CBM-@}lock and #$7f
         tay
         lda freqlo,y
r{CBM-@}det2   clc
         adc detunlo,x
         *= *-((*-r{CBM-@}det2)*rem{CBM-@}det)
         sta sid+0,x
         lda freqhi,y
r{CBM-@}det3   adc detunhi,x
         *= *-((*-r{CBM-@}det3)*rem{CBM-@}det)
         sta sid+1,x
         *= *-((*-r{CBM-@}1wf3)*rem{CBM-@}1wf)
         jmp sid{CBM-@}next


;----------------SEQUENCER--------------
sequ2    lda #0
         sta glidadd2,x
seq{CBM-@}cond
         ldy seqbyte,x
r{CBM-@}voff3  bpl bn54
         lda voff+1
         and chanoff,x
         sta voff+1

r{CBM-@}4ch5   cpx #21
         bne sequ2-3
         jmp cond{CBM-@}ret
         *= *-((*-r{CBM-@}4ch5)*rem{CBM-@}4ch)
r{CBM-@}4ch6   jmp sid{CBM-@}next
         *= *-((*-r{CBM-@}4ch6)*(1-rem{CBM-@}4ch))
         *= *-((*-r{CBM-@}voff3)*rem{CBM-@}voff)

bn54     lda sl,y
         sta mzero
         lda sh,y
         sta mzero+1

r{CBM-@}wfo1   lda #$ff
         sta wf{CBM-@}ora2,x
         *= *-((*-r{CBM-@}wfo1)*rem{CBM-@}wfo)

r201     lda #bn32-fxjmp-2
         sta fxjmp+1
         *= *-((*-r201)*rem{CBM-@}f20)

         ldy seqp,x
         lda (mzero),y
         cmp #$5f
         beq bn6
         cmp #$f0
         bcc bn4
         and #$0f
         sta release,x
         bpl bn6

bn4      cmp #$c0
         bcc bn13
         and #$3f
         asl a
         sta arpnum2,x
         tax
         lda ad+1,x
         and #$3f
x        ldx #0
         bpl bn15

bn13     cmp #$a0
         bcc bn14
         and #$1f
         asl a
         asl a
         sta glidadd2,x
r202     bpl bn6
         *= *-((*-r202)*(1-rem{CBM-@}f20))

com20    bne bn6
         lda #comfx-fxjmp-2
         sta fxjmp+1
         bne bn6
         *= *-((*-com20)*rem{CBM-@}f20)

bn14     cmp #$80
         bcc bn7
         sta arpnum2,x
         and #$3f
r{CBM-@}wfo2   sta wf{CBM-@}ora2,x
         *= *-((*-r{CBM-@}wfo2)*rem{CBM-@}wfo)

bn15     sta sound2,x
r{CBM-@}fi2    sta filtre,x
         *= *-((*-r{CBM-@}fi2)*rem{CBM-@}fi)

         lda #0
r{CBM-@}wfo3   sta wf{CBM-@}ora,x
         *= *-((*-r{CBM-@}wfo3)*rem{CBM-@}wfo)

         sta seqsust,x
bn6      iny
         lda (mzero),y
         cmp #$df
         bcc bn7
         beq dur{CBM-@}20
         and #$3f
         bne bn12
dur{CBM-@}20   iny
         lda (mzero),y
         bne bn12

r{CBM-@}4ch7   cmp #$5f
         beq note2ch4
         and #$7f
         sta note2ch4+1
note2ch4 lda #0
         clc
         adc transp+21
         sta trk{CBM-@}tran+1
         jmp track{CBM-@}conduct
         *= *-((*-r{CBM-@}4ch7)*rem{CBM-@}4ch)

bn7      cmp #$80
         bcs bn56
         cmp #$60
         bcc bn56
         and #$1f
bn12     sta dur,x
         iny
         lda (mzero),y
         cmp #$f0
         bcc bn56
         and #$0f
         sta release,x
         lda #$5f
bn56
r{CBM-@}4ch2   cpx #21
         beq r{CBM-@}4ch7
         *= *-((*-r{CBM-@}4ch2)*rem{CBM-@}4ch)

         cmp #$5f
fxjmp    bne bn32
         sta ack+1
         sta note2,x
         lda release,x
         bmi track{CBM-@}conduct
         ora sustain,x
         sta sid+6,x
         lda #$fe
         sta gate,x
         sta release,x
         bne track{CBM-@}conduct

comfx    lsr a
         lda filtena+1
         bcs disafi
         ora chanon,x
         bne disaf2
disafi   and chanoff,x
disaf2   sta filtena+1
         lda #$5f
         sta ack+1
         bne note{CBM-@}5f
         *= *-((*-comfx)*rem{CBM-@}f20)

r{CBM-@}gat4   adc #0
         eor #$ff
         sta note2,x
         lda #$5f
         sta ack+1
         bne track{CBM-@}conduct
         *= *-((*-r{CBM-@}gat4)*rem{CBM-@}gat)

bn32     sta ack+1
         and #$7f
r{CBM-@}gat3   beq r{CBM-@}gat4
         *= *-((*-r{CBM-@}gat3)*rem{CBM-@}gat)
         clc
trk{CBM-@}tran adc #0
         clc
         *= *-((*-trk{CBM-@}tran)*rem{CBM-@}4ch)
         adc transp,x
note{CBM-@}5f  sta note2,x

track{CBM-@}conduct
         iny
         lda (mzero),y
         beq *+3
         tya
         sta seqp,x
         bne trk{CBM-@}end

track{CBM-@}init
         ldy tdelay,x
         beq bn61
         dec tdelay,x
         bpl trk{CBM-@}end

bn61     lda tracky,x ;16-bit
         sta mzero
         lda trackhi,x
         sta mzero+1
         *= *-((*-bn61)*rem{CBM-@}trkl)
r{CBM-@}trkl1  lda trklo,x  ;8-bit
         sta mzero
         lda trkhi,x
         sta mzero+1
         ldy tracky,x
         *= *-((*-r{CBM-@}trkl1)*(1-rem{CBM-@}trkl))

         lda (mzero),y
         bpl bn28
         cmp #$f7
         bcc t{CBM-@}del
r{CBM-@}stop   beq bn28
         *= *-((*-r{CBM-@}stop)*rem{CBM-@}voff)

r{CBM-@}trkl2  and #7
         sta bn36+1
         iny
         clc
         lda trklo,x
         adc (mzero),y
         sta mzero
         lda trkhi,x
bn36     adc #0
         sta mzero+1
         dey
         *= *-((*-r{CBM-@}trkl2)*rem{CBM-@}trkl)
r{CBM-@}trkl3  iny
         lda (mzero),y
         tay
         *= *-((*-r{CBM-@}trkl3)*(1-rem{CBM-@}trkl))
         lda (mzero),y
t{CBM-@}del    cmp #$c0
         bcc bn62
         and #$3f
         sta tdelay,x
         iny
         lda (mzero),y
         bpl bn28
bn62     sec
         sbc #$a0
         sta transp,x
         iny
         lda (mzero),y
bn28     sta seqbyte,x
r{CBM-@}trkl4  tya
         sec
         adc mzero
         sta tracky,x
         lda #0
         adc mzero+1
         sta trackhi,x
         *= *-((*-r{CBM-@}trkl4)*rem{CBM-@}trkl)
r{CBM-@}trkl5  iny
         tya
         sta tracky,x
         *= *-((*-r{CBM-@}trkl5)*(1-rem{CBM-@}trkl))
trk{CBM-@}end  cpx #21
         beq rrts
         *= *-((*-trk{CBM-@}end)*rem{CBM-@}4ch)

ack      lda #0
         cmp #$5f
         beq bn66
         lda release,x
         bcs tie{CBM-@}att
         bmi no{CBM-@}sust
         asl a
         asl a
         asl a
         asl a
         sta seqsust,x
no{CBM-@}sust  lda #$ff
         sta release,x
         sta srco,x

         ldy sound2,x
         lda z3,y
         asl a
         bmi no{CBM-@}rls
         and #$40
         beq no{CBM-@}hard
         adc #$e0
         sta sid+6,x
         lda #$0f
         sta sid+5,x
no{CBM-@}hard  lda #$fe
         sta gate,x
         and wf,x
r{CBM-@}wfo5   ora wf{CBM-@}ora,x
         *= *-((*-r{CBM-@}wfo5)*rem{CBM-@}wfo)
         sta sid+4,x
no{CBM-@}rls   jmp sid{CBM-@}next
rrts     jmp cond{CBM-@}ret
         *= *-((*-rrts)*rem{CBM-@}4ch)
tie{CBM-@}att  bmi r{CBM-@}wfo4
         asl a
         asl a
         asl a
         asl a
         sta attack,x
         lda #$f0
         bne no{CBM-@}sust-3

r{CBM-@}wfo4   lda wf{CBM-@}ora2,x
         bmi bn66
         sta wf{CBM-@}ora,x
         *= *-((*-r{CBM-@}wfo4)*rem{CBM-@}wfo)
bn66     jsr wfrout
         jmp sid{CBM-@}next
part2
r{CBM-@}pu10   jsr pulse
         *= *-((*-r{CBM-@}pu10)*rem{CBM-@}pu)
;----------------------GLIDE ROUTINE----
glide    lda glidadd,x
         bmi glide{CBM-@}it
         bne *+5
         jmp vibrato
         ora #$80
         sta glidadd,x
         jmp getadd
glide{CBM-@}it ldy note,x
         sty mzero+1
         lda addlo,x
         clc
         adc freqlo,y
         sta mzero
         lda addhi,x
         adc freqhi,y
         pha
         ldy glidto,x
         lda mzero
         cmp freqlo,y
         pla
         sbc freqhi,y

bn65     lda addlo,x
         bcc bn11
         sbc addval{CBM-@}l,x
         sta addlo,x
         lda #$b0
         sta addor
         lda addhi,x
         sbc addval{CBM-@}h,x
         jmp bn19

bn11     adc addval{CBM-@}l,x
         sta addlo,x
         lda #$90
         sta addor
         lda addhi,x
         adc addval{CBM-@}h,x
bn19     sta addhi,x
         sta mzero

         lda addlo,x
         ldx mzero+1
         clc
         adc freqlo,x
         php
         cmp freqlo,y
         lda mzero
         adc freqhi,x
         plp
         sbc freqhi,y
         ldx x+1
addor    bcc bn60
         tya
         sta note,x
         lda #0
         sta glidadd,x
         sta addlo,x
         sta addhi,x
bn60     jsr wfrout
         jmp sid{CBM-@}next

         *= *-((*-glide)*rem{CBM-@}glid)

;----------------------VIBRATO ROUTINE--

vibrato  lda vible,x
         beq bn63
         asl a
         adc vible,x
         tay
         lda vibdec,x
         bne bn16
         sta addlo,x
         sta addhi,x
         lda v-3,y
r{CBM-@}det4   beq detun
         cmp #$fe
         beq detun2
         *= *-((*-r{CBM-@}det4)*rem{CBM-@}det)

         sta vibdec,x
         lda v+1-3,y
         cmp #$80
         and #$7f
         sta vibwid,x
         ror a
         sta vibdir,x
         lda v+2-3,y
         *= *-((*-vibrato)*rem{CBM-@}vib)

getadd   and #$7f
         sta mzero
         lda note,x
         lsr a
         clc
         adc mzero
         cmp #$60
         bcc *+6
         and #$1f
         ora #$60
         tay
         lda #0
         bcc bn17
         lda freqhi-$60,y
bn17     sta addval{CBM-@}h,x
         lda freqhi,y
         sta addval{CBM-@}l,x
bn63     jsr wfrout
         jmp sid{CBM-@}next
         *= *-((*-bn63)*rem{CBM-@}vib)
         *= *-((*-getadd)*addsum)

detun    inc vible,x
detun2   lda v+1-3,y
         sta detunlo,x
         lda v+2-3,y
         sta detunhi,x
         jmp wfrout
         *= *-((*-detun)*rem{CBM-@}det)

bn16     cmp #$ff
         beq bn53
         dec vibdec,x
         bne bn53
         inc vible,x
bn53
;----------------------CRAZY COMET FX---
cc1      lda v+2-3,y
         bpl bn59
         and #3
andcount and #0
         bne bn59
         sta frq{CBM-@}l+1
         sta frq{CBM-@}h+1
         bne bn59
         jsr wfrout2
         jmp sid{CBM-@}next

         *= *-((*-cc1)*rem{CBM-@}cc)
;----------------------ADD/SUB FREQUENCY
bn59     lda addlo,x
         ldy vibdir,x
         bmi bn1
         clc
         adc addval{CBM-@}l,x
         sta addlo,x
         lda addhi,x
         adc addval{CBM-@}h,x
         jmp bn2
bn1      sec
         sbc addval{CBM-@}l,x
         sta addlo,x
         lda addhi,x
         sbc addval{CBM-@}h,x
bn2      sta addhi,x
         dey
         tya
         sta mzero
         bit mzero
         bvc bn3
         eor #$7f
         ora vibwid,x
bn3      sta vibdir,x
         *= *-((*-detun)*rem{CBM-@}vib)

         jsr wfrout

sid{CBM-@}next lda chanx,x
         bmi cc2
         tax
         jmp part1

cc2      inc andcount+1
         *= *-((*-cc2)*rem{CBM-@}cc)

r{CBM-@}pu12   lda #$ea
         sta snop
         lda #$4c
         sta jpwf
         *= *-((*-r{CBM-@}pu12)*rem{CBM-@}pu)

         
r{CBM-@}fad4
fade     lda #0
         beq nofade
         dec fadeco
         bpl nofade
         clc
         adc #1
         lsr a
         sta fadeco
         ldy #0
         bcc fadedwn
voiceon
r{CBM-@}voff4  lda #0
         sta voff+1
         *= *-((*-r{CBM-@}voff4)*rem{CBM-@}voff)
         lda vol+1
         cmp #$0f
         bcc fadeup
         sty fade+1
         bcs nofade
fadedwn  dec vol+1
         bpl nofade
r{CBM-@}voff5  lda voff+1
         sta voiceon+1
         sty voff+1
         *= *-((*-r{CBM-@}voff5)*rem{CBM-@}voff)
         sty fade+1
fadeup   inc vol+1

nofade
         *= *-((*-r{CBM-@}fad4)*rem{CBM-@}fad)

r{CBM-@}fi3
setfi    lda #0
         beq filtok
f{CBM-@}spd6   ldx #0
         stx filtspd
         *= *-((*-f{CBM-@}spd6)*rem{CBM-@}fspd)
         jmp fidir
         *= *-((*-setfi)*rem{CBM-@}4ch)
filtok
f{CBM-@}spd1   dec filtspd
         bmi fspeed
         jmp filtch
fspeed   lda #0
         sta filtspd
         *= *-((*-f{CBM-@}spd1)*rem{CBM-@}fspd)

filtle   lda #0
         asl a
         bne *+5
         jmp filtch
         asl a
         tay
filtdec  lda #0
         bne bn38
         lda #2
         sta filtdec+1
         lda #$b0
         sta branch
         bcs bn38

filtsnd  ldx #0
r{CBM-@}4ch4   bmi fivoice4
         *= *-((*-r{CBM-@}4ch4)*rem{CBM-@}4ch)

         lda fi+1-4,y  ;frame v2.1
         bne *+7       ;
         lda fi+2-4,y  ;
         bne *+5       ;

         lda z7,x
         tax
         asl a
         asl a
         asl a
         asl a
         sta res+1
         txa
         and #$f0
         sta band+1
fivoice4 lda fi-4,y
         sta cutoff+1

bn38     lda fi+1-4,y
         bne *+8       ;frame v2.1
         lda cutoff+1  ;
         jmp bn42      ;

         asl a
         asl a
         asl a
         asl a
         tax
         stx upper+1
         lda fi+1-4,y
         and #$f0
         cmp upper+1
         bcc bn43+1
         sta upper+1
bn43     lda #$aa
         stx lower+1

cutoff   lda #0
branch   bcc bn39
         clc
         adc fi+2-4,y
upper    cmp #0
         bcc bn40
         bcs bn42

bn39     sec
         sbc fi+2-4,y
lower    cmp #0
         bcs bn40
bn42     ldx fi+3-4,y
         bpl *+5
         dec filtdec+1
         dec filtdec+1
         bne bn41
         stx filtle+1
bn41     ldx #$90
         stx branch
bn40     sta cutoff+1

fidir    sta sid+$16
filtch   lda #0
filtena  ora #0
         *= *-((*-filtena)*rem{CBM-@}f20)
res      ora #0
         sta sid+$17
         *= *-((*-r{CBM-@}fi3)*rem{CBM-@}fi)

vol      lda #$0f
r{CBM-@}fi4
band     ora #0
         *= *-((*-r{CBM-@}fi4)*rem{CBM-@}fi)
         sta sid+$18

r{CBM-@}voff6  lda voff+1
         beq bn8
         *= *-((*-r{CBM-@}voff6)*rem{CBM-@}voff)

         dec tempo+1
         bpl bn8

         dec duration
         dec duration+7
         dec duration+14
r{CBM-@}4ch3   dec duration+21
         *= *-((*-r{CBM-@}4ch3)*rem{CBM-@}4ch)

tem{CBM-@}prg  lda #0

r{CBM-@}tp     bmi tem{CBM-@}num
         tay
         lda tem{CBM-@}p,y
         clc
tem{CBM-@}y    adc #0
         tay
         lda tem{CBM-@}d,y
         bpl tpl
         ldy #$ff
         sty tem{CBM-@}y+1
tpl      inc tem{CBM-@}y+1
tem{CBM-@}num  and #$7f
         *= *-((*-r{CBM-@}tp)*rem{CBM-@}tp)

         sta tempo+1
         cmp #3
         bcc *+4
         lda #2
         sta cur{CBM-@}tem+1
bn8      rts

;pal tuned freqtable:
;(ntsc freqtable is on release disk)

freqhi   .byte $01,$01,$01,$01,$01,$01
         .byte $01,$01,$01,$01,$01,$02
         .byte $02,$02,$02,$02,$02,$02
         .byte $03,$03,$03,$03,$03,$04
         .byte $04,$04,$04,$05,$05,$05
         .byte $06,$06,$06,$07,$07,$08
         .byte $08,$09,$09,$0a,$0a,$0b
         .byte $0c,$0d,$0d,$0e,$0f,$10
         .byte $11,$12,$13,$14,$15,$17
         .byte $18,$1a,$1b,$1d,$1f,$20
         .byte $22,$24,$27,$29,$2b,$2e
         .byte $31,$34,$37,$3a,$3e,$41
         .byte $45,$49,$4e,$52,$57,$5c
         .byte $62,$68,$6e,$75,$7c,$83
         .byte $8b,$93,$9c,$a5,$af,$b9
         .byte $c4,$d0,$dd,$ea,$f8,$ff
freqlo   .byte $16,$27,$39,$4b,$5f,$74
         .byte $8a,$a1,$ba,$d4,$f0,$0e
         .byte $2d,$4e,$71,$96,$be,$e7
         .byte $14,$42,$74,$a9,$e0,$1b
         .byte $5a,$9c,$e2,$2d,$7b,$cf
         .byte $27,$85,$e8,$51,$c1,$37
         .byte $b4,$38,$c4,$59,$f7,$9d
         .byte $4e,$0a,$d0,$a2,$81,$6d
         .byte $67,$70,$89,$b2,$ed,$3b
         .byte $9c,$13,$a0,$45,$02,$da
         .byte $ce,$e0,$11,$64,$da,$76
         .byte $39,$26,$40,$89,$04,$b4
         .byte $9c,$c0,$23,$c8,$b4,$eb
         .byte $72,$4c,$80,$12,$08,$68
         .byte $39,$80,$45,$90,$68,$d6
         .byte $e3,$99,$00,$24,$10,$ff


init
r{CBM-@}voff7
         lda c,x
         sta voff+1
r{CBM-@}fad5   sta voiceon+1
         *= *-((*-r{CBM-@}fad5)*rem{CBM-@}fad)
         *= *-((*-r{CBM-@}voff7)*rem{CBM-@}voff)

         lda s,x
         sta tem{CBM-@}prg+1
         lda #1
         sta tempo+1
         sta cur{CBM-@}tem+1

r{CBM-@}fi5    lda fs,x
f{CBM-@}spd2   tay
         and #$0f
         sta fspeed+1
         tya
         *= *-((*-f{CBM-@}spd2)*rem{CBM-@}fspd)
         lsr a
         lsr a
         lsr a
         lsr a
         sta filtena+1
         *= *-((*-r{CBM-@}fi5)*rem{CBM-@}fi)

r{CBM-@}fad2   lda fv,x
         pha
         and #$0f
         sta vol+1
         *= *-((*-r{CBM-@}fad2)*rem{CBM-@}fad)

         lda #$60
trin1    sta trk{CBM-@}end
         *= *-((*-trin1)*rem{CBM-@}4ch)
trin2    sta ack
         *= *-((*-trin2)*(1-rem{CBM-@}4ch))

         ldy tp,x
         ldx #channels*7
bn52     lda voff+1
         and chanon,x
         beq bn74
         *= *-((*-bn52)*rem{CBM-@}voff)
         lda #0
         sta tdelay,x
         sta dur,x
         sta seqp,x
         sta transp,x
r{CBM-@}trkl6  sta tracky,x
         *= *-((*-r{CBM-@}trkl6)*(1-rem{CBM-@}trkl))
t40      cpx #3*7
         bcs t44
         *= *-((*-t40)*rem{CBM-@}4ch)
         sta pulsle2,x
         sta srco,x
r{CBM-@}fi6    sta filtre,x   ;fi subtune fix
         *= *-((*-r{CBM-@}fi6)*rem{CBM-@}fi)

r{CBM-@}wfr4   sta wf{CBM-@}repet,x
         *= *-((*-r{CBM-@}wfr4)*rem{CBM-@}wfr)
t44      lda #$fe
         sta note2,x
         sta duration,x
         sta sound,x
         lda tl,y
         sta trklo,x
r{CBM-@}trkl7  sta tracky,x
         *= *-((*-r{CBM-@}trkl7)*rem{CBM-@}trkl)
         lda th,y
         sta trkhi,x
r{CBM-@}trkl8  sta trackhi,x
         *= *-((*-r{CBM-@}trkl8)*rem{CBM-@}trkl)

         tya
         pha
         jsr track{CBM-@}init
         pla
         tay

t43      dey
bn74     lda chanx,x
         tax
         bpl bn52

         ldx #$14
         lda #0
         sta sid+0,x
         dex
         bpl *-4
cc3      sta andcount+1
         *= *-((*-cc3)*rem{CBM-@}cc)
r{CBM-@}tp2    sta tem{CBM-@}y+1
         *= *-((*-r{CBM-@}tp2)*rem{CBM-@}tp)

r{CBM-@}fi7    sta setfi+1
         *= *-((*-r{CBM-@}fi7)*rem{CBM-@}4ch)
f{CBM-@}spd5   sta filtspd
         *= *-((*-f{CBM-@}spd5)*rem{CBM-@}fspd)
         sta filtch+1
         ldy #$07
         sty sid+$15
         *= *-((*-r{CBM-@}fi7)*rem{CBM-@}fi)

trin3    sta trk{CBM-@}tran+1
         sta note2ch4+1
         lda #$e0
         sta trk{CBM-@}end
         *= *-((*-trin3)*rem{CBM-@}4ch)

trin4    lda #$a9
         sta ack
         *= *-((*-trin4)*(1-rem{CBM-@}4ch))

r{CBM-@}pu11   lda #$ea
         sta snop
         lda #$4c
         sta jpwf         
         *= *-((*-r{CBM-@}pu11)*rem{CBM-@}pu)

r{CBM-@}fad1   pla
         and #$f0
fadeout  sta fade+1
         sta fadeco
         *= *-((*-r{CBM-@}fad1)*rem{CBM-@}fad)
         rts

