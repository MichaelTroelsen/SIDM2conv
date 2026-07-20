; B10: Blackbird's contiguous freq_msb + freq_lsb + pwprepare region,
; read verbatim from this song's play-data template at offset 817 (463 bytes). Byte-identical across every
; v1.2-exact rip (asserted at build time, see write_freqblob).
;   +0   freq_msb   (96 bytes)
;   +96  freq_lsb  (111 bytes, overlaps freq_msb by 15)
;   +207 pwprepare (256 bytes, indexed by PW_ACC)
        .byte $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $01
        .byte $01, $01, $01, $01, $01, $01, $01, $01, $01, $01, $01, $02, $02, $02, $02, $02
        .byte $02, $02, $03, $03, $03, $03, $03, $04, $04, $04, $04, $05, $05, $05, $06, $06
        .byte $06, $07, $07, $08, $08, $09, $09, $0a, $0a, $0b, $0c, $0d, $0d, $0e, $0f, $10
        .byte $11, $12, $13, $14, $15, $17, $18, $1a, $1b, $1d, $1f, $20, $22, $24, $27, $29
        .byte $2b, $2e, $31, $34, $37, $3a, $3e, $41, $45, $49, $4e, $52, $57, $5c, $62, $68
        .byte $6e, $75, $7c, $83, $8b, $93, $9c, $a5, $af, $b9, $c4, $d0, $dd, $ea, $f8, $07
        .byte $16, $27, $39, $4b, $5f, $74, $8a, $a1, $ba, $d4, $f0, $0e, $2d, $4e, $71, $96
        .byte $be, $e7, $14, $42, $74, $a9, $e0, $1b, $5a, $9c, $e2, $2d, $7b, $cf, $27, $85
        .byte $e8, $51, $c1, $37, $b4, $38, $c4, $59, $f7, $9d, $4e, $0a, $d0, $a2, $81, $6d
        .byte $67, $70, $89, $b2, $ed, $3b, $9c, $13, $a0, $45, $02, $da, $ce, $e0, $11, $64
        .byte $da, $76, $39, $26, $40, $89, $04, $b4, $9c, $c0, $23, $c8, $b4, $eb, $72, $4c
        .byte $80, $12, $08, $68, $39, $80, $45, $90, $68, $d6, $e3, $99, $00, $24, $10, $8f
        .byte $7f, $6f, $5f, $4f, $3f, $2f, $1f, $0f, $fe, $ee, $de, $ce, $be, $ae, $9e, $8e
        .byte $7e, $6e, $6e, $5e, $4e, $3e, $2e, $1e, $0e, $fd, $ed, $dd, $cd, $bd, $ad, $9d
        .byte $8d, $7d, $6d, $5d, $5d, $4d, $3d, $2d, $1d, $0d, $fc, $ec, $dc, $cc, $bc, $ac
        .byte $9c, $8c, $7c, $6c, $5c, $4c, $4c, $3c, $2c, $1c, $0c, $fb, $eb, $db, $cb, $bb
        .byte $ab, $9b, $8b, $7b, $6b, $5b, $4b, $3b, $3b, $2b, $1b, $0b, $fa, $ea, $da, $ca
        .byte $ba, $aa, $9a, $8a, $7a, $6a, $5a, $4a, $3a, $2a, $2a, $1a, $0a, $f9, $e9, $d9
        .byte $c9, $b9, $a9, $99, $89, $79, $69, $59, $49, $39, $29, $19, $19, $09, $f8, $e8
        .byte $d8, $c8, $b8, $a8, $98, $88, $78, $68, $58, $48, $38, $28, $18, $08, $08, $08
        .byte $08, $18, $28, $38, $48, $58, $68, $78, $88, $98, $a8, $b8, $c8, $d8, $e8, $f8
        .byte $09, $19, $19, $29, $39, $49, $59, $69, $79, $89, $99, $a9, $b9, $c9, $d9, $e9
        .byte $f9, $0a, $1a, $2a, $2a, $3a, $4a, $5a, $6a, $7a, $8a, $9a, $aa, $ba, $ca, $da
        .byte $ea, $fa, $0b, $1b, $2b, $3b, $3b, $4b, $5b, $6b, $7b, $8b, $9b, $ab, $bb, $cb
        .byte $db, $eb, $fb, $0c, $1c, $2c, $3c, $4c, $4c, $5c, $6c, $7c, $8c, $9c, $ac, $bc
        .byte $cc, $dc, $ec, $fc, $0d, $1d, $2d, $3d, $4d, $5d, $5d, $6d, $7d, $8d, $9d, $ad
        .byte $bd, $cd, $dd, $ed, $fd, $0e, $1e, $2e, $3e, $4e, $5e, $6e, $6e, $7e, $8e, $9e
        .byte $ae, $be, $ce, $de, $ee, $fe, $0f, $1f, $2f, $3f, $4f, $5f, $6f, $7f, $8f
