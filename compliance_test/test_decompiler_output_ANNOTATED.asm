;==============================================================================
; test_decompiler_output.asm
; Annotated 6502 Assembly Disassembly
;==============================================================================
;
; AUTHOR: Laxity, youtH & SMC
; PLAYER: Laxity NewPlayer v21
;
;==============================================================================
; MEMORY MAP
;==============================================================================
;
; LAXITY NEWPLAYER V21 TABLE ADDRESSES (Verified):
; $18DA   Wave Table - Waveforms (32 bytes)
; $190C   Wave Table - Note Offsets (32 bytes)
; $1837   Pulse Table (4-byte entries)
; $1A1E   Filter Table (4-byte entries)
; $1A6B   Instrument Table (8×8 bytes, column-major)
; $199F   Sequence Pointers (3 voices × 2 bytes)
;
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

;==============================================================================
; SYMBOL TABLE
;==============================================================================
;
; Total Symbols: 140
; Breakdown: 25 hardware, 2 subroutine, 113 unknown
;
; Address    Type         Name                     Refs     Description
; ---------- ------------ ------------------------ -------- --------------------
; $A000      Subroutine   Utility                  -        Utility or helper function
; $A006      Subroutine   Utility                  -        Utility or helper function
; $A06F      Unknown      addr_a06f                -        Referenced address
; $A13C      Unknown      addr_a13c                -        Referenced address
; $A1E7      Unknown      addr_a1e7                -        Referenced address
; $A221      Unknown      addr_a221                -        Referenced address
; $A2A5      Unknown      addr_a2a5                -        Referenced address
; $A2A7      Unknown      addr_a2a7                1w       Referenced address
; $A33B      Unknown      addr_a33b                -        Referenced address
; $A33E      Unknown      addr_a33e                -        Referenced address
; $A35D      Unknown      addr_a35d                -        Referenced address
; $A398      Unknown      addr_a398                -        Referenced address
; $A3A4      Unknown      addr_a3a4                1w       Referenced address
; $A3E5      Unknown      addr_a3e5                -        Referenced address
; $A41B      Unknown      addr_a41b                -        Referenced address
; $A433      Unknown      addr_a433                -        Referenced address
; $A480      Unknown      addr_a480                -        Referenced address
; $A49E      Unknown      addr_a49e                -        Referenced address
; $A4A1      Unknown      addr_a4a1                -        Referenced address
; $A511      Unknown      addr_a511                -        Referenced address
; $A54C      Unknown      addr_a54c                -        Referenced address
; $A55F      Unknown      addr_a55f                -        Referenced address
; $A59B      Unknown      addr_a59b                -        Referenced address
; $A5A1      Unknown      addr_a5a1                -        Referenced address
; $A600      Unknown      addr_a600                -        Referenced address
; $A679      Unknown      addr_a679                -        Referenced address
; $A6B9      Unknown      addr_a6b9                -        Referenced address
; $A6C8      Unknown      addr_a6c8                5r       Referenced address
; $A6C9      Unknown      addr_a6c9                1r       Referenced address
; $A728      Unknown      addr_a728                5r       Referenced address
; $A729      Unknown      addr_a729                1r       Referenced address
; $A788      Unknown      addr_a788                1r       Referenced address
; $A798      Unknown      addr_a798                1r       Referenced address
; $A79E      Unknown      addr_a79e                1r       Referenced address
; $A7A4      Unknown      addr_a7a4                1r       Referenced address
; $A7A7      Unknown      addr_a7a7                1r,1w    Referenced address
; $A7A8      Unknown      addr_a7a8                1r,2w    Referenced address
; $A7A9      Unknown      addr_a7a9                1r,2w    Referenced address
; $A7AA      Unknown      addr_a7aa                2r,3w    Referenced address
; $A7AB      Unknown      addr_a7ab                1r,2w    Referenced address
; $A7AC      Unknown      addr_a7ac                1r,1w    Referenced address
; $A7AD      Unknown      addr_a7ad                1r,2w    Referenced address
; $A7AE      Unknown      addr_a7ae                1r,1w    Referenced address
; $A7AF      Unknown      addr_a7af                1r,1w    Referenced address
; $A7B0      Unknown      addr_a7b0                2r,2w    Referenced address
; $A7B1      Unknown      addr_a7b1                2r,2w    Referenced address
; $A7B2      Unknown      addr_a7b2                2r,1w    Referenced address
; $A7B3      Unknown      addr_a7b3                1r,3w    Referenced address
; $A7B4      Unknown      addr_a7b4                3r,4w    Referenced address
; $A7B5      Unknown      addr_a7b5                2r,3w    Referenced address
; $A7B6      Unknown      addr_a7b6                1r,2w    Referenced address
; $A7B9      Unknown      addr_a7b9                1r,1w    Referenced address
; $A7BC      Unknown      addr_a7bc                3r,2w    Referenced address
; $A7BF      Unknown      addr_a7bf                1r,2w    Referenced address
; $A7C2      Unknown      addr_a7c2                1r,1w    Referenced address
; $A7C5      Unknown      addr_a7c5                1r,1w    Referenced address
; $A7C8      Unknown      addr_a7c8                6r,3w    Referenced address
; $A7CB      Unknown      addr_a7cb                3r,1w    Referenced address
; $A7CE      Unknown      addr_a7ce                2r,2w    Referenced address
; $A7D1      Unknown      addr_a7d1                3r,2w    Referenced address
; $A7D4      Unknown      addr_a7d4                1r,1w    Referenced address
; $A7D7      Unknown      addr_a7d7                1r,1w    Referenced address
; $A7DA      Unknown      addr_a7da                3r,1w    Referenced address
; $A7DD      Unknown      addr_a7dd                1w       Referenced address
; $A7E0      Unknown      addr_a7e0                6r,1w    Referenced address
; $A7E3      Unknown      addr_a7e3                5r,3w    Referenced address
; $A7E6      Unknown      addr_a7e6                2r,4w    Referenced address
; $A7E9      Unknown      addr_a7e9                3r,3w    Referenced address
; $A7EC      Unknown      addr_a7ec                2r,3w    Referenced address
; $A7EF      Unknown      addr_a7ef                4r,6w    Referenced address
; $A7F2      Unknown      addr_a7f2                5r,3w    Referenced address
; $A7F5      Unknown      addr_a7f5                4r,3w    Referenced address
; $A7F8      Unknown      addr_a7f8                3r,5w    Referenced address
; $A7FB      Unknown      addr_a7fb                1r,1w    Referenced address
; $A7FE      Unknown      addr_a7fe                1r,1w    Referenced address
; $A801      Unknown      addr_a801                7r,9w    Referenced address
; $A804      Unknown      addr_a804                7r,9w    Referenced address
; $A807      Unknown      addr_a807                1r,2w    Referenced address
; $A80A      Unknown      addr_a80a                1r,1w    Referenced address
; $A80D      Unknown      addr_a80d                2r,2w    Referenced address
; $A810      Unknown      addr_a810                2r,2w    Referenced address
; $A813      Unknown      addr_a813                1r,2w    Referenced address
; $A816      Unknown      addr_a816                1r,4w    Referenced address
; $A819      Unknown      addr_a819                1r,4w    Referenced address
; $A81C      Unknown      addr_a81c                1r,3w    Referenced address
; $A81F      Unknown      addr_a81f                5r,3w    Referenced address
; $A820      Unknown      addr_a820                1w       Referenced address
; $A821      Unknown      addr_a821                1w       Referenced address
; $A822      Unknown      addr_a822                1r       Referenced address
; $A823      Unknown      addr_a823                2r       Referenced address
; $A824      Unknown      addr_a824                1r       Referenced address
; $A834      Unknown      addr_a834                1r       Referenced address
; $A844      Unknown      addr_a844                4r       Referenced address
; $A854      Unknown      addr_a854                1r       Referenced address
; $A864      Unknown      addr_a864                1r       Referenced address
; $A874      Unknown      addr_a874                1r       Referenced address
; $A884      Unknown      addr_a884                2r       Referenced address
; $A8A8      Unknown      addr_a8a8                4r       Referenced address
; $A8CC      Unknown      addr_a8cc                5r       Referenced address
; $A8F0      Unknown      addr_a8f0                1r       Referenced address
; $A8F1      Unknown      addr_a8f1                1r       Referenced address
; $A8F2      Unknown      addr_a8f2                2r       Referenced address
; $A924      Unknown      addr_a924                2r       Referenced address
; $A956      Unknown      addr_a956                2r       Referenced address
; $A96F      Unknown      addr_a96f                2r       Referenced address
; $A988      Unknown      addr_a988                2r       Referenced address
; $A9A1      Unknown      addr_a9a1                4r       Referenced address
; $A9B2      Unknown      addr_a9b2                2r       Referenced address
; $A9C3      Unknown      addr_a9c3                3r       Referenced address
; $A9D4      Unknown      addr_a9d4                2r       Referenced address
; $AA1F      Unknown      addr_aa1f                2r       Referenced address
; $AA24      Unknown      addr_aa24                1r       Referenced address
; $AA27      Unknown      addr_aa27                1r       Referenced address
; $AA2A      Unknown      addr_aa2a                1r       Referenced address
; $AA7A      Unknown      addr_aa7a                1r       Referenced address
; $D400      Hardware     voice_1_frequency_low    -        Voice 1 Frequency Low
; $D401      Hardware     voice_1_frequency_high   -        Voice 1 Frequency High
; $D402      Hardware     voice_1_pulse_width_low  -        Voice 1 Pulse Width Low
; $D403      Hardware     voice_1_pulse_width_high -        Voice 1 Pulse Width High
; $D404      Hardware     voice_1_control_register -        Voice 1 Control Register
; $D405      Hardware     voice_1_attack/decay     -        Voice 1 Attack/Decay
; $D406      Hardware     voice_1_sustain/release  -        Voice 1 Sustain/Release
; $D407      Hardware     voice_2_frequency_low    -        Voice 2 Frequency Low
; $D408      Hardware     voice_2_frequency_high   -        Voice 2 Frequency High
; $D409      Hardware     voice_2_pulse_width_low  -        Voice 2 Pulse Width Low
; $D40A      Hardware     voice_2_pulse_width_high -        Voice 2 Pulse Width High
; $D40B      Hardware     voice_2_control_register -        Voice 2 Control Register
; $D40C      Hardware     voice_2_attack/decay     -        Voice 2 Attack/Decay
; $D40D      Hardware     voice_2_sustain/release  -        Voice 2 Sustain/Release
; $D40E      Hardware     voice_3_frequency_low    -        Voice 3 Frequency Low
; $D40F      Hardware     voice_3_frequency_high   -        Voice 3 Frequency High
; $D410      Hardware     voice_3_pulse_width_low  -        Voice 3 Pulse Width Low
; $D411      Hardware     voice_3_pulse_width_high -        Voice 3 Pulse Width High
; $D412      Hardware     voice_3_control_register -        Voice 3 Control Register
; $D413      Hardware     voice_3_attack/decay     -        Voice 3 Attack/Decay
; $D414      Hardware     voice_3_sustain/release  -        Voice 3 Sustain/Release
; $D415      Hardware     filter_cutoff_low        -        Filter Cutoff Low
; $D416      Hardware     filter_cutoff_high       -        Filter Cutoff High
; $D417      Hardware     filter_resonance/routing -        Filter Resonance/Routing
; $D418      Hardware     volume/filter_mode       -        Volume/Filter Mode
;==============================================================================
;
; Legend:
;   Refs: c=calls, r=reads, w=writes
;   Types: subroutine, data, hardware, unknown
;==============================================================================
;
; SIDdecompiler output; Generated by Python SIDdecompiler (100% compatible);; Original file: Broware; Author: Laxity, youtH & SMC; Released: 2022 Onslaught/Offence;; Load address: $A000; Init address: $A000; Play address: $A006;* = $A000;------------------------------------------------------------------------------
; Subroutine: Utility
; Address: $A000 - $A046
; Purpose: Utility or helper function
; Cycles: 84-93 (typically 87)
; Frame %: 0.4%-0.5% (typically 0.4% of NTSC frame)
; Budget remaining: 19569 cycles (99.6%)
; Inputs: None
; Outputs: A, X
; Modifies: A, X
;------------------------------------------------------------------------------
init:$a000: 4c b9 a6     JMP  $a6b9          play:;------------------------------------------------------------------------------
; Subroutine: Utility
; Address: $A006 - $A046
; Purpose: Utility or helper function
; Cycles: 81-90 (typically 84)
; Frame %: 0.4%-0.5% (typically 0.4% of NTSC frame)
; Budget remaining: 19572 cycles (99.6%)
; Inputs: None
; Outputs: A, X
; Modifies: A, X
;------------------------------------------------------------------------------
$a006: a9 00        LDA  #$00           $a008: 2c a8 a7     BIT  $a7a8          $a00b: 30 44        BMI  la051          $a00d: 70 38        BVS  la047          $a00f: a2 75        LDX  #$75           la011:$a011: 9d a9 a7     STA  $a7a9,x        $a014: ca           DEX                 $a015: d0 fa        BNE  la011          $a017: ae a9 a7     LDX  $a7a9          $a01a: bd 22 a8     LDA  $a822,x        $a01d: 8d a7 a7     STA  $a7a7          $a020: 8d ab a7     STA  $a7ab          $a023: bd 23 a8     LDA  $a823,x        $a026: 29 0f        AND  #$0f           $a028: 8d ac a7     STA  $a7ac          $a02b: bd 23 a8     LDA  $a823,x        $a02e: 29 70        AND  #$70           $a030: 8d ad a7     STA  $a7ad          $a033: a9 02        LDA  #$02           $a035: 8d aa a7     STA  $a7aa          $a038: 8d 1f a8     STA  $a81f          $a03b: 8d 20 a8     STA  $a820          $a03e: 8d 21 a8     STA  $a821          $a041: a9 80        LDA  #$80           $a043: 8d a8 a7     STA  $a7a8          $a046: 60           RTS                 la051:$a051: ce aa a7     DEC  $a7aa          $a054: 10 17        BPL  la06d          $a056: ae ab a7     LDX  $a7ab          $a059: bd 1f aa     LDA  $aa1f,x        $a05c: 8d aa a7     STA  $a7aa          $a05f: e8           INX                 $a060: bd 1f aa     LDA  $aa1f,x        $a063: c9 7f        CMP  #$7f           $a065: d0 03        BNE  la06a          $a067: ae a7 a7     LDX  $a7a7          la06a:$a06a: 8e ab a7     STX  $a7ab          la06d:$a06d: a2 02        LDX  #$02           la06f:$a06f: bd 1f a8     LDA  $a81f,x        $a072: c9 01        CMP  #$01           $a074: d0 39        BNE  la0af          $a076: bd bc a7     LDA  $a7bc,x        $a079: d0 34        BNE  la0af          $a07b: fe bc a7     INC  $a7bc,x        $a07e: bd 24 aa     LDA  $aa24,x        $a081: 85 02        STA  $02            $a083: bd 27 aa     LDA  $aa27,x        $a086: 85 03        STA  $03            $a088: bc b9 a7     LDY  $a7b9,x        $a08b: b1 02        LDA  ($02),y        $a08d: 10 09        BPL  la098          $a08f: 38           SEC                 $a090: e9 a0        SBC  #$a0           $a092: 9d d7 a7     STA  $a7d7,x        $a095: c8           INY                 $a096: b1 02        LDA  ($02),y        la098:$a098: 9d c2 a7     STA  $a7c2,x        $a09b: c8           INY                 $a09c: b1 02        LDA  ($02),y        $a09e: c9 ff        CMP  #$ff           $a0a0: d0 04        BNE  la0a6          la0a6:$a0a6: 98           TYA                 $a0a7: 9d b9 a7     STA  $a7b9,x        $a0aa: a9 00        LDA  #$00           $a0ac: 9d bf a7     STA  $a7bf,x        la0af:$a0af: ad aa a7     LDA  $a7aa          $a0b2: d0 05        BNE  la0b9          $a0b4: de b6 a7     DEC  $a7b6,x        $a0b7: 30 03        BMI  la0bc          la0b9:$a0b9: 4c 3c a1     JMP  $a13c          la0bc:$a0bc: bc c2 a7     LDY  $a7c2,x        $a0bf: b9 2a aa     LDA  $aa2a,y        $a0c2: 85 02        STA  $02            $a0c4: b9 7a aa     LDA  $aa7a,y        $a0c7: 85 03        STA  $03            $a0c9: bc bf a7     LDY  $a7bf,x        $a0cc: b1 02        LDA  ($02),y        $a0ce: 10 27        BPL  la0f7          $a0d0: c9 c0        CMP  #$c0           $a0d2: 90 08        BCC  la0dc          $a0d4: 9d d1 a7     STA  $a7d1,x        $a0d7: c8           INY                 $a0d8: b1 02        LDA  ($02),y        $a0da: 10 1b        BPL  la0f7          la0dc:$a0dc: c9 a0        CMP  #$a0           $a0de: 90 08        BCC  la0e8          $a0e0: 9d ce a7     STA  $a7ce,x        $a0e3: c8           INY                 $a0e4: b1 02        LDA  ($02),y        $a0e6: 10 0f        BPL  la0f7          la0e8:$a0e8: c9 90        CMP  #$90           $a0ea: 90 03        BCC  la0ef          $a0ec: fe c8 a7     INC  $a7c8,x        la0ef:$a0ef: 29 0f        AND  #$0f           $a0f1: 9d c5 a7     STA  $a7c5,x        $a0f4: c8           INY                 $a0f5: b1 02        LDA  ($02),y        la0f7:$a0f7: 9d cb a7     STA  $a7cb,x        $a0fa: f0 04        BEQ  la100          $a0fc: c9 7e        CMP  #$7e           $a0fe: d0 05        BNE  la105          la100:$a100: fe c8 a7     INC  $a7c8,x        $a103: d0 06        BNE  la10b          la105:$a105: bd d7 a7     LDA  $a7d7,x        $a108: 9d da a7     STA  $a7da,x        la10b:$a10b: c8           INY                 $a10c: 98           TYA                 $a10d: 9d bf a7     STA  $a7bf,x        $a110: b1 02        LDA  ($02),y        $a112: c9 7f        CMP  #$7f           $a114: d0 03        BNE  la119          $a116: de bc a7     DEC  $a7bc,x        la119:$a119: bd c5 a7     LDA  $a7c5,x        $a11c: 9d b6 a7     STA  $a7b6,x        $a11f: bd d1 a7     LDA  $a7d1,x        $a122: 10 13        BPL  la137          $a124: 29 3f        AND  #$3f           $a126: a8           TAY                 $a127: b9 84 a8     LDA  $a884,y        $a12a: 29 f0        AND  #$f0           $a12c: f0 09        BEQ  la137          la137:$a137: a9 02        LDA  #$02           $a139: 9d 1f a8     STA  $a81f,x        la13c:$a13c: bc 1f a8     LDY  $a81f,x        $a13f: 30 3a        BMI  la17b          $a141: c0 03        CPY  #$03           $a143: 10 36        BPL  la17b          $a145: bd c8 a7     LDA  $a7c8,x        $a148: d0 31        BNE  la17b          $a14a: c0 01        CPY  #$01           $a14c: f0 23        BEQ  la171          $a14e: c0 00        CPY  #$00           $a150: f0 2c        BEQ  la17e          $a152: bd ce a7     LDA  $a7ce,x        $a155: 29 1f        AND  #$1f           $a157: a8           TAY                 $a158: b9 44 a8     LDA  $a844,y        $a15b: 10 0f        BPL  la16c          $a15d: 29 0f        AND  #$0f           $a15f: a8           TAY                 $a160: b9 f0 a8     LDA  $a8f0,y        $a163: 9d 16 a8     STA  $a816,x        $a166: b9 f1 a8     LDA  $a8f1,y        $a169: 9d 19 a8     STA  $a819,x        la16c:$a16c: a9 fe        LDA  #$fe           $a16e: 9d 1c a8     STA  $a81c,x        la171:$a171: bd e3 a7     LDA  $a7e3,x        $a174: c9 04        CMP  #$04           $a176: b0 03        BCS  la17b          $a178: 4c 5f a5     JMP  $a55f          la17b:$a17b: 4c 98 a3     JMP  $a398          la17e:$a17e: a9 ff        LDA  #$ff           $a180: 9d 1c a8     STA  $a81c,x        $a183: bd ce a7     LDA  $a7ce,x        $a186: 10 36        BPL  la1be          $a188: 29 1f        AND  #$1f           $a18a: 9d d4 a7     STA  $a7d4,x        $a18d: 9d ce a7     STA  $a7ce,x        $a190: a8           TAY                 $a191: b9 24 a8     LDA  $a824,y        $a194: 9d fb a7     STA  $a7fb,x        $a197: 9d 16 a8     STA  $a816,x        $a19a: b9 34 a8     LDA  $a834,y        $a19d: 9d fe a7     STA  $a7fe,x        $a1a0: 9d 19 a8     STA  $a819,x        $a1a3: b9 44 a8     LDA  $a844,y        $a1a6: 29 20        AND  #$20           $a1a8: f0 08        BEQ  la1b2          la1b2:$a1b2: ad b2 a7     LDA  $a7b2          $a1b5: 3d a4 a7     AND  $a7a4,x        $a1b8: 8d b2 a7     STA  $a7b2          $a1bb: 4c e7 a1     JMP  $a1e7          la1be:$a1be: bc d4 a7     LDY  $a7d4,x        $a1c1: bd fb a7     LDA  $a7fb,x        $a1c4: 9d 16 a8     STA  $a816,x        $a1c7: bd fe a7     LDA  $a7fe,x        $a1ca: 9d 19 a8     STA  $a819,x        $a1cd: bd e3 a7     LDA  $a7e3,x        $a1d0: c9 03        CMP  #$03           $a1d2: f0 18        BEQ  la1ec          $a1d4: c9 04        CMP  #$04           $a1d6: d0 0f        BNE  la1e7          $a1d8: bd f5 a7     LDA  $a7f5,x        $a1db: 9d f8 a7     STA  $a7f8,x        $a1de: bd f2 a7     LDA  $a7f2,x        $a1e1: 9d ef a7     STA  $a7ef,x        $a1e4: 4c ec a1     JMP  la1ec          la1e7:$a1e7: a9 00        LDA  #$00           $a1e9: 9d e3 a7     STA  $a7e3,x        la1ec:$a1ec: b9 44 a8     LDA  $a844,y        $a1ef: 29 10        AND  #$10           $a1f1: 4a           LSR                 $a1f2: 09 01        ORA  #$01           $a1f4: 9d 13 a8     STA  $a813,x        $a1f7: b9 44 a8     LDA  $a844,y        $a1fa: 29 40        AND  #$40           $a1fc: f0 12        BEQ  la210          $a1fe: 0a           ASL                 $a1ff: 8d b3 a7     STA  $a7b3          $a202: b9 54 a8     LDA  $a854,y        $a205: 8d b5 a7     STA  $a7b5          $a208: ce b5 a7     DEC  $a7b5          $a20b: a9 00        LDA  #$00           $a20d: 8d b4 a7     STA  $a7b4          la210:$a210: b9 74 a8     LDA  $a874,y        $a213: 9d e6 a7     STA  $a7e6,x        $a216: b9 64 a8     LDA  $a864,y        $a219: 9d e9 a7     STA  $a7e9,x        $a21c: a9 00        LDA  #$00           $a21e: 9d ec a7     STA  $a7ec,x        la221:$a221: bd d1 a7     LDA  $a7d1,x        $a224: 30 03        BMI  la229          $a226: 4c 3e a3     JMP  $a33e          la229:$a229: 29 3f        AND  #$3f           $a22b: 9d d1 a7     STA  $a7d1,x        $a22e: a8           TAY                 $a22f: b9 84 a8     LDA  $a884,y        $a232: 29 0f        AND  #$0f           $a234: a8           TAY                 $a235: b9 88 a7     LDA  $a788,y        $a238: 8d a7 a2     STA  $a2a7          $a23b: bc d1 a7     LDY  $a7d1,x        $a23e: 4c a5 a2     JMP  $a2a5          $a252: b9 a8 a8     LDA  $a8a8,y        $a255: 9d f2 a7     STA  $a7f2,x        $a258: b9 cc a8     LDA  $a8cc,y        $a25b: 9d ef a7     STA  $a7ef,x        $a25e: a9 03        LDA  #$03           $a260: 4c 3b a3     JMP  $a33b          la263:$a263: b9 a8 a8     LDA  $a8a8,y        $a266: 30 2f        BMI  la297          $a268: 9d f2 a7     STA  $a7f2,x        $a26b: 9d ef a7     STA  $a7ef,x        $a26e: b9 cc a8     LDA  $a8cc,y        $a271: 9d f5 a7     STA  $a7f5,x        $a274: 9d f8 a7     STA  $a7f8,x        $a277: a9 04        LDA  #$04           $a279: 4c 3b a3     JMP  la33b          la2a5:$a2a5: 38           SEC                 $a2a6: b0 bb        BCS  la263          $a2a8: b9 cc a8     LDA  $a8cc,y        $a2ab: 29 0f        AND  #$0f           $a2ad: 9d ef a7     STA  $a7ef,x        $a2b0: b9 a8 a8     LDA  $a8a8,y        $a2b3: 18           CLC                 $a2b4: 69 01        ADC  #$01           $a2b6: 9d f2 a7     STA  $a7f2,x        $a2b9: 4a           LSR                 $a2ba: 90 02        BCC  la2be          $a2bc: 09 80        ORA  #$80           la2be:$a2be: 9d f5 a7     STA  $a7f5,x        $a2c1: a9 02        LDA  #$02           $a2c3: 9d f8 a7     STA  $a7f8,x        $a2c6: 4c 3b a3     JMP  la33b          $a2c9: b9 a8 a8     LDA  $a8a8,y        $a2cc: 9d 16 a8     STA  $a816,x        $a2cf: b9 cc a8     LDA  $a8cc,y        $a2d2: 9d 19 a8     STA  $a819,x        $a2d5: 4c 3e a3     JMP  la33e          $a2ed: b9 cc a8     LDA  $a8cc,y        $a2f0: 9d e6 a7     STA  $a7e6,x        $a2f3: 4c 3e a3     JMP  la33e          la33b:$a33b: 9d e3 a7     STA  $a7e3,x        la33e:$a33e: bd c8 a7     LDA  $a7c8,x        $a341: d0 06        BNE  la349          $a343: bd cb a7     LDA  $a7cb,x        $a346: 4c 5d a3     JMP  $a35d          la349:$a349: bd cb a7     LDA  $a7cb,x        $a34c: f0 39        BEQ  la387          $a34e: c9 7e        CMP  #$7e           $a350: f0 39        BEQ  la38b          $a352: a8           TAY                 $a353: 18           CLC                 $a354: 7d da a7     ADC  $a7da,x        $a357: dd e0 a7     CMP  $a7e0,x        $a35a: f0 34        BEQ  la390          $a35c: 98           TYA                 la35d:$a35d: 9d dd a7     STA  $a7dd,x        $a360: 18           CLC                 $a361: 7d da a7     ADC  $a7da,x        $a364: 9d e0 a7     STA  $a7e0,x        $a367: a8           TAY                 $a368: bd e3 a7     LDA  $a7e3,x        $a36b: c9 03        CMP  #$03           $a36d: f0 10        BEQ  la37f          $a36f: c9 04        CMP  #$04           $a371: f0 0c        BEQ  la37f          $a373: b9 28 a7     LDA  $a728,y        $a376: 9d 01 a8     STA  $a801,x        $a379: b9 c8 a6     LDA  $a6c8,y        $a37c: 9d 04 a8     STA  $a804,x        la37f:$a37f: bd c8 a7     LDA  $a7c8,x        $a382: d0 07        BNE  la38b          $a384: 4c a1 a5     JMP  $a5a1          la387:$a387: a9 fe        LDA  #$fe           $a389: d0 02        BNE  la38d          la38b:$a38b: a9 ff        LDA  #$ff           la38d:$a38d: 9d 1c a8     STA  $a81c,x        la390:$a390: a9 00        LDA  #$00           $a392: 9d c8 a7     STA  $a7c8,x        $a395: 4c 00 a6     JMP  $a600          la398:$a398: bd e3 a7     LDA  $a7e3,x        $a39b: a8           TAY                 $a39c: b9 98 a7     LDA  $a798,y        $a39f: 8d a4 a3     STA  $a3a4          $a3a2: 38           SEC                 $a3a3: b0 00        BCS  la3a5          la3a5:$a3a5: 4c 11 a5     JMP  $a511          $a3a8: 4c 33 a4     JMP  $a433          $a3ab: 4c a1 a4     JMP  $a4a1          $a3c7: bc e0 a7     LDY  $a7e0,x        $a3ca: b9 29 a7     LDA  $a729,y        $a3cd: f9 28 a7     SBC  $a728,y        $a3d0: 85 02        STA  $02            $a3d2: b9 c9 a6     LDA  $a6c9,y        $a3d5: f9 c8 a6     SBC  $a6c8,y        $a3d8: 85 03        STA  $03            $a3da: bd f5 a7     LDA  $a7f5,x        $a3dd: c9 80        CMP  #$80           $a3df: 29 00        AND  #$00           $a3e1: 7d ef a7     ADC  $a7ef,x        $a3e4: a8           TAY                 la3e5:$a3e5: 88           DEY                 $a3e6: 30 07        BMI  la3ef          $a3e8: 46 03        LSR  $03            $a3ea: 66 02        ROR  $02            $a3ec: 4c e5 a3     JMP  $a3e5          la3ef:$a3ef: bd f8 a7     LDA  $a7f8,x        $a3f2: 29 01        AND  #$01           $a3f4: d0 14        BNE  la40a          $a3f6: bd 01 a8     LDA  $a801,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit addition with carry propagation
; Type: 16-bit Addition
; Result: $a801,x/$a804,x = $a804,x + $02 (with carry)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a3f9: 18           CLC                 $a3fa: 65 02        ADC  $02            $a3fc: 9d 01 a8     STA  $a801,x        $a3ff: bd 04 a8     LDA  $a804,x        $a402: 65 03        ADC  $03            $a404: 9d 04 a8     STA  $a804,x        $a407: 4c 1b a4     JMP  $a41b          la40a:$a40a: bd 01 a8     LDA  $a801,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit subtraction with borrow propagation
; Type: 16-bit Subtraction
; Result: $a801,x/$a804,x = $a804,x - $02 (with borrow)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a40d: 38           SEC                 $a40e: e5 02        SBC  $02            $a410: 9d 01 a8     STA  $a801,x        $a413: bd 04 a8     LDA  $a804,x        $a416: e5 03        SBC  $03            $a418: 9d 04 a8     STA  $a804,x        la41b:$a41b: bd f5 a7     LDA  $a7f5,x        $a41e: 29 7f        AND  #$7f           $a420: 18           CLC                 $a421: 69 01        ADC  #$01           $a423: dd f2 a7     CMP  $a7f2,x        $a426: 90 05        BCC  la42d          $a428: fe f8 a7     INC  $a7f8,x        $a42b: a9 00        LDA  #$00           la42d:$a42d: 9d f5 a7     STA  $a7f5,x        $a430: 4c 11 a5     JMP  la511          la433:$a433: bc e0 a7     LDY  $a7e0,x        $a436: b9 28 a7     LDA  $a728,y        $a439: 85 02        STA  $02            $a43b: b9 c8 a6     LDA  $a6c8,y        $a43e: 85 03        STA  $03            $a440: bd 01 a8     LDA  $a801,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit subtraction with borrow propagation
; Type: 16-bit Subtraction
; Result: $a801,x/$a804,x = $a804,x - $02 (with borrow)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a443: 38           SEC                 $a444: e5 02        SBC  $02            $a446: 9d 01 a8     STA  $a801,x        $a449: bd 04 a8     LDA  $a804,x        $a44c: e5 03        SBC  $03            $a44e: 9d 04 a8     STA  $a804,x        $a451: 30 18        BMI  la46b          $a453: bd 01 a8     LDA  $a801,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit subtraction with borrow propagation
; Type: 16-bit Subtraction
; Result: $a801,x/$a804,x = $a804,x - $a7ef,x (with borrow)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a456: 38           SEC                 $a457: fd ef a7     SBC  $a7ef,x        $a45a: 9d 01 a8     STA  $a801,x        $a45d: bd 04 a8     LDA  $a804,x        $a460: fd f2 a7     SBC  $a7f2,x        $a463: 9d 04 a8     STA  $a804,x        $a466: 10 25        BPL  la48d          $a468: 4c 80 a4     JMP  $a480          la46b:$a46b: bd 01 a8     LDA  $a801,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit addition with carry propagation
; Type: 16-bit Addition
; Result: $a801,x/$a804,x = $a804,x + $a7ef,x (with carry)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a46e: 18           CLC                 $a46f: 7d ef a7     ADC  $a7ef,x        $a472: 9d 01 a8     STA  $a801,x        $a475: bd 04 a8     LDA  $a804,x        $a478: 7d f2 a7     ADC  $a7f2,x        $a47b: 9d 04 a8     STA  $a804,x        $a47e: 30 0d        BMI  la48d          la480:$a480: a5 02        LDA  $02            $a482: 9d 01 a8     STA  $a801,x        $a485: a5 03        LDA  $03            $a487: 9d 04 a8     STA  $a804,x        $a48a: 4c 9e a4     JMP  $a49e          la48d:$a48d: bd 01 a8     LDA  $a801,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit addition with carry propagation
; Type: 16-bit Addition
; Result: $a801,x/$a804,x = $a804,x + $02 (with carry)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a490: 18           CLC                 $a491: 65 02        ADC  $02            $a493: 9d 01 a8     STA  $a801,x        $a496: bd 04 a8     LDA  $a804,x        $a499: 65 03        ADC  $03            $a49b: 9d 04 a8     STA  $a804,x        la49e:$a49e: 4c 11 a5     JMP  la511          la4a1:$a4a1: bc f8 a7     LDY  $a7f8,x        $a4a4: de ef a7     DEC  $a7ef,x        $a4a7: 10 1b        BPL  la4c4          $a4a9: c8           INY                 $a4aa: b9 d4 a9     LDA  $a9d4,y        $a4ad: 30 0b        BMI  la4ba          $a4af: c9 70        CMP  #$70           $a4b1: 30 07        BMI  la4ba          $a4b3: 29 0f        AND  #$0f           $a4b5: 18           CLC                 $a4b6: 7d f5 a7     ADC  $a7f5,x        $a4b9: a8           TAY                 la4ba:$a4ba: 98           TYA                 $a4bb: 9d f8 a7     STA  $a7f8,x        $a4be: bd f2 a7     LDA  $a7f2,x        $a4c1: 9d ef a7     STA  $a7ef,x        la4c4:$a4c4: b9 d4 a9     LDA  $a9d4,y        $a4c7: 18           CLC                 $a4c8: 7d e0 a7     ADC  $a7e0,x        $a4cb: a8           TAY                 $a4cc: b9 28 a7     LDA  $a728,y        $a4cf: 9d 01 a8     STA  $a801,x        $a4d2: b9 c8 a6     LDA  $a6c8,y        $a4d5: 9d 04 a8     STA  $a804,x        $a4d8: 4c 11 a5     JMP  la511          la511:$a511: bc e9 a7     LDY  $a7e9,x        $a514: b9 56 a9     LDA  $a956,y        $a517: c9 7f        CMP  #$7f           $a519: d0 0c        BNE  la527          $a51b: b9 88 a9     LDA  $a988,y        $a51e: dd e9 a7     CMP  $a7e9,x        $a521: f0 3c        BEQ  la55f          $a523: 9d e9 a7     STA  $a7e9,x        $a526: a8           TAY                 la527:$a527: b9 56 a9     LDA  $a956,y        $a52a: 10 0c        BPL  la538          $a52c: 9d 10 a8     STA  $a810,x        $a52f: b9 6f a9     LDA  $a96f,y        $a532: 9d 0d a8     STA  $a80d,x        $a535: 4c 4c a5     JMP  $a54c          la538:$a538: 85 02        STA  $02            $a53a: bd 0d a8     LDA  $a80d,x        ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit addition with carry propagation
; Type: 16-bit Addition
; Result: $a80d,x/$a810,x = $a810,x + $a96f,y (with carry)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a53d: 18           CLC                 $a53e: 79 6f a9     ADC  $a96f,y        $a541: 9d 0d a8     STA  $a80d,x        $a544: bd 10 a8     LDA  $a810,x        $a547: 65 02        ADC  $02            $a549: 9d 10 a8     STA  $a810,x        la54c:$a54c: bd ec a7     LDA  $a7ec,x        $a54f: fe ec a7     INC  $a7ec,x        $a552: d9 88 a9     CMP  $a988,y        $a555: d0 08        BNE  la55f          $a557: fe e9 a7     INC  $a7e9,x        $a55a: a9 00        LDA  #$00           $a55c: 9d ec a7     STA  $a7ec,x        la55f:$a55f: bc e6 a7     LDY  $a7e6,x        $a562: b9 f2 a8     LDA  $a8f2,y        $a565: c9 7f        CMP  #$7f           $a567: d0 0a        BNE  la573          $a569: b9 24 a9     LDA  $a924,y        $a56c: 9d e6 a7     STA  $a7e6,x        $a56f: a8           TAY                 $a570: b9 f2 a8     LDA  $a8f2,y        la573:$a573: 9d 13 a8     STA  $a813,x        $a576: b9 24 a9     LDA  $a924,y        $a579: f0 17        BEQ  la592          $a57b: c9 81        CMP  #$81           $a57d: b0 04        BCS  la583          $a57f: 18           CLC                 $a580: 7d e0 a7     ADC  $a7e0,x        la583:$a583: 29 7f        AND  #$7f           $a585: a8           TAY                 $a586: b9 28 a7     LDA  $a728,y        $a589: 9d 07 a8     STA  $a807,x        $a58c: b9 c8 a6     LDA  $a6c8,y        $a58f: 4c 9b a5     JMP  $a59b          la592:$a592: bd 01 a8     LDA  $a801,x        $a595: 9d 07 a8     STA  $a807,x        $a598: bd 04 a8     LDA  $a804,x        la59b:$a59b: 9d 0a a8     STA  $a80a,x        $a59e: fe e6 a7     INC  $a7e6,x        la5a1:$a5a1: bc 9e a7     LDY  $a79e,x        $a5a4: bd 07 a8     LDA  $a807,x        $a5a7: 99 00 d4     STA  $d400,y  ; Voice 1 Frequency Low
$a5aa: bd 0a a8     LDA  $a80a,x        $a5ad: 99 01 d4     STA  $d401,y  ; Voice 1 Frequency High
$a5b0: bd 19 a8     LDA  $a819,x        $a5b3: 99 06 d4     STA  $d406,y  ; Voice 1 Sustain/Release
$a5b6: bd 16 a8     LDA  $a816,x        $a5b9: 99 05 d4     STA  $d405,y  ; Voice 1 Attack/Decay
$a5bc: bd 0d a8     LDA  $a80d,x        $a5bf: 99 02 d4     STA  $d402,y  ; Voice 1 Pulse Width Low
$a5c2: bd 10 a8     LDA  $a810,x        $a5c5: 99 03 d4     STA  $d403,y  ; Voice 1 Pulse Width High
$a5c8: bd 13 a8     LDA  $a813,x        $a5cb: 3d 1c a8     AND  $a81c,x        $a5ce: 99 04 d4     STA  $d404,y  ; Voice 1 Control Register
$a5d1: bd 1f a8     LDA  $a81f,x        $a5d4: d0 2a        BNE  la600          $a5d6: bd c8 a7     LDA  $a7c8,x        $a5d9: f0 25        BEQ  la600          $a5db: bd e3 a7     LDA  $a7e3,x        $a5de: c9 03        CMP  #$03           $a5e0: f0 1b        BEQ  la5fd          $a5e2: c9 04        CMP  #$04           $a5e4: f0 17        BEQ  la5fd          $a5e6: bd cb a7     LDA  $a7cb,x        $a5e9: f0 12        BEQ  la5fd          $a5eb: c9 7e        CMP  #$7e           $a5ed: f0 0e        BEQ  la5fd          $a5ef: 18           CLC                 $a5f0: 7d da a7     ADC  $a7da,x        $a5f3: dd e0 a7     CMP  $a7e0,x        $a5f6: f0 05        BEQ  la5fd          $a5f8: a9 00        LDA  #$00           $a5fa: 9d e3 a7     STA  $a7e3,x        la5fd:$a5fd: 4c 21 a2     JMP  $a221          la600:$a600: bd 1f a8     LDA  $a81f,x        $a603: 30 03        BMI  la608          $a605: de 1f a8     DEC  $a81f,x        la608:$a608: ca           DEX                 $a609: 30 03        BMI  la60e          $a60b: 4c 6f a0     JMP  $a06f          la60e:$a60e: ad b3 a7     LDA  $a7b3          $a611: 30 69        BMI  la67c          $a613: f0 6c        BEQ  la681          $a615: ac b5 a7     LDY  $a7b5          $a618: ad b4 a7     LDA  $a7b4          $a61b: ce b4 a7     DEC  $a7b4          $a61e: c9 00        CMP  #$00           $a620: d0 44        BNE  la666          $a622: c8           INY                 $a623: b9 a1 a9     LDA  $a9a1,y        $a626: c9 7f        CMP  #$7f           $a628: d0 12        BNE  la63c          $a62a: 98           TYA                 $a62b: d9 c3 a9     CMP  $a9c3,y        $a62e: d0 08        BNE  la638          $a630: a9 00        LDA  #$00           $a632: 8d b3 a7     STA  $a7b3          $a635: 4c 81 a6     JMP  la681          la63c:$a63c: b9 a1 a9     LDA  $a9a1,y        $a63f: 10 1f        BPL  la660          $a641: 29 70        AND  #$70           $a643: 8d ad a7     STA  $a7ad          $a646: b9 a1 a9     LDA  $a9a1,y        $a649: 29 0f        AND  #$0f           $a64b: 8d b1 a7     STA  $a7b1          $a64e: b9 b2 a9     LDA  $a9b2,y        $a651: 8d b0 a7     STA  $a7b0          $a654: b9 c3 a9     LDA  $a9c3,y        $a657: 8d ae a7     STA  $a7ae          $a65a: ee b4 a7     INC  $a7b4          $a65d: 4c 79 a6     JMP  $a679          la660:$a660: b9 c3 a9     LDA  $a9c3,y        $a663: 8d b4 a7     STA  $a7b4          la666:$a666: ad b0 a7     LDA  $a7b0          ;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
; PATTERN DETECTED: 16-bit addition with carry propagation
; Type: 16-bit Addition
; Result: $a7b0/$a7b1 = $a7b1 + $a9b2,y (with carry)
;~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
$a669: 18           CLC                 $a66a: 79 b2 a9     ADC  $a9b2,y        $a66d: 8d b0 a7     STA  $a7b0          $a670: ad b1 a7     LDA  $a7b1          $a673: 79 a1 a9     ADC  $a9a1,y        $a676: 8d b1 a7     STA  $a7b1          la679:$a679: 8c b5 a7     STY  $a7b5          la67c:$a67c: a9 40        LDA  #$40           $a67e: 8d b3 a7     STA  $a7b3          la681:$a681: ad b1 a7     LDA  $a7b1          $a684: 85 02        STA  $02            $a686: ad b0 a7     LDA  $a7b0          $a689: 46 02        LSR  $02            $a68b: 6a           ROR                 $a68c: aa           TAX                 $a68d: 46 02        LSR  $02            $a68f: 6a           ROR                 $a690: 46 02        LSR  $02            $a692: 6a           ROR                 $a693: 46 02        LSR  $02            $a695: 6a           ROR                 $a696: a8           TAY                 $a697: ad ae a7     LDA  $a7ae          $a69a: 0d af a7     ORA  $a7af          $a69d: 8d 17 d4     STA  $d417  ; Filter Resonance/Routing
$a6a0: 8c 16 d4     STY  $d416  ; Filter Cutoff High
$a6a3: 8a           TXA                 $a6a4: 29 07        AND  #$07           $a6a6: 8d 15 d4     STA  $d415  ; Filter Cutoff Low
$a6a9: ad ac a7     LDA  $a7ac          $a6ac: 0d ad a7     ORA  $a7ad          $a6af: 8d 18 d4     STA  $d418  ; Volume/Filter Mode
$a6b2: ad b2 a7     LDA  $a7b2          $a6b5: 8d af a7     STA  $a7af          $a6b8: 60           RTS                 la6b9:$a6b9: 8d a9 a7     STA  $a7a9          $a6bc: a9 00        LDA  #$00           $a6be: 8d a8 a7     STA  $a7a8          $a6c1: 60           RTS                 