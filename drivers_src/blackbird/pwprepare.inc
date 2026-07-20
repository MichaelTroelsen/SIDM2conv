; Blackbird's fixed pulse-width lookup (`pwprepare`), read verbatim
; from this song's own play-data template at offset 1024. 256 bytes,
; byte-identical across every v1.2-exact rip (asserted at build time,
; see write_pwprepare). Indexed by the 8-bit pulse accumulator PW_ACC.
        .byte $8f, $7f, $6f, $5f, $4f, $3f, $2f, $1f, $0f, $fe, $ee, $de, $ce, $be, $ae, $9e
        .byte $8e, $7e, $6e, $6e, $5e, $4e, $3e, $2e, $1e, $0e, $fd, $ed, $dd, $cd, $bd, $ad
        .byte $9d, $8d, $7d, $6d, $5d, $5d, $4d, $3d, $2d, $1d, $0d, $fc, $ec, $dc, $cc, $bc
        .byte $ac, $9c, $8c, $7c, $6c, $5c, $4c, $4c, $3c, $2c, $1c, $0c, $fb, $eb, $db, $cb
        .byte $bb, $ab, $9b, $8b, $7b, $6b, $5b, $4b, $3b, $3b, $2b, $1b, $0b, $fa, $ea, $da
        .byte $ca, $ba, $aa, $9a, $8a, $7a, $6a, $5a, $4a, $3a, $2a, $2a, $1a, $0a, $f9, $e9
        .byte $d9, $c9, $b9, $a9, $99, $89, $79, $69, $59, $49, $39, $29, $19, $19, $09, $f8
        .byte $e8, $d8, $c8, $b8, $a8, $98, $88, $78, $68, $58, $48, $38, $28, $18, $08, $08
        .byte $08, $08, $18, $28, $38, $48, $58, $68, $78, $88, $98, $a8, $b8, $c8, $d8, $e8
        .byte $f8, $09, $19, $19, $29, $39, $49, $59, $69, $79, $89, $99, $a9, $b9, $c9, $d9
        .byte $e9, $f9, $0a, $1a, $2a, $2a, $3a, $4a, $5a, $6a, $7a, $8a, $9a, $aa, $ba, $ca
        .byte $da, $ea, $fa, $0b, $1b, $2b, $3b, $3b, $4b, $5b, $6b, $7b, $8b, $9b, $ab, $bb
        .byte $cb, $db, $eb, $fb, $0c, $1c, $2c, $3c, $4c, $4c, $5c, $6c, $7c, $8c, $9c, $ac
        .byte $bc, $cc, $dc, $ec, $fc, $0d, $1d, $2d, $3d, $4d, $5d, $5d, $6d, $7d, $8d, $9d
        .byte $ad, $bd, $cd, $dd, $ed, $fd, $0e, $1e, $2e, $3e, $4e, $5e, $6e, $6e, $7e, $8e
        .byte $9e, $ae, $be, $ce, $de, $ee, $fe, $0f, $1f, $2f, $3f, $4f, $5f, $6f, $7f, $8f
