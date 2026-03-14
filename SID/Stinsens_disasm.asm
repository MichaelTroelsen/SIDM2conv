* = $1000
$1000 jmp j1692
$1003 jmp j169B
$1006 lda #$00
$1008 bit a1781
$100B bmi b1051
$100D bvs b1047
$100F ldx #$75
b1011:
$1011 sta f1782,x          ; [SMC] STA writes to code region at $1782 ; x-ref: $1015
$1014 dex
$1015 bne b1011
$1017 ldx f1782
$101A lda f17FB,x
$101D sta a1780            ; [SMC] STA writes to code region at $1780
$1020 sta a1784            ; [SMC] STA writes to code region at $1784
$1023 lda f17FC,x
$1026 and #$0f
$1028 sta a1785            ; [SMC] STA writes to code region at $1785
$102B lda f17FC,x
$102E and #$70
$1030 sta a1786            ; [SMC] STA writes to code region at $1786
$1033 lda #$02
$1035 sta a1783            ; [SMC] STA writes to code region at $1783
$1038 sta a17F8            ; [SMC] STA writes to code region at $17F8
$103B sta a17F9            ; [SMC] STA writes to code region at $17F9
$103E sta a17FA            ; [SMC] STA writes to code region at $17FA
$1041 lda #$80
$1043 sta a1781            ; [SMC] STA writes to code region at $1781
$1046 rts
b1047:
$1047 sta $d404            ; x-ref: $100d; Voice 1: Control Register
$104A sta $d40b            ; Voice 2: Control Register
$104D sta $d412            ; Voice 3: Control Register
$1050 rts
b1051:
$1051 dec a1783            ; x-ref: $100b
$1054 bpl b106D
$1056 ldx a1784
$1059 lda f1A19,x
$105C sta a1783            ; [SMC] STA writes to code region at $1783
$105F inx
$1060 lda f1A19,x
$1063 cmp #$7f
$1065 bne b106A
$1067 ldx a1780
b106A:
$106A stx a1784            ; [SMC] STX writes to code region at $1784 ; x-ref: $1065
b106D:
$106D ldx #$02             ; x-ref: $1054
j106F:
$106F lda a17F8,x          ; x-ref: $15ec
$1072 cmp #$01
$1074 bne b10AF
$1076 lda f1795,x
$1079 bne b10AF
$107B inc f1795,x
$107E lda f1A1C,x
$1081 sta aFC
$1083 lda f1A1F,x
$1086 sta aFD
$1088 ldy f1792,x
$108B lda (aFC),y
$108D bpl b1098
$108F sec
$1090 sbc #$a0
$1092 sta f17B0,x          ; [SMC] STA writes to code region at $17B0
$1095 iny
$1096 lda (aFC),y
b1098:
$1098 sta f179B,x          ; [SMC] STA writes to code region at $179B ; x-ref: $108d
$109B iny
$109C lda (aFC),y
$109E cmp #$ff
$10A0 bne b10A6
$10A2 iny
$10A3 lda (aFC),y
$10A5 tay
b10A6:
$10A6 tya                  ; x-ref: $10a0
$10A7 sta f1792,x          ; [SMC] STA writes to code region at $1792
$10AA lda #$00
$10AC sta f1798,x          ; [SMC] STA writes to code region at $1798
b10AF:
$10AF lda a1783            ; x-ref: $1074, $1079
$10B2 bne b1121
$10B4 dec f178F,x
$10B7 bpl b1121
$10B9 ldy f179B,x
$10BC lda f1A22,y
$10BF sta aFC
$10C1 lda f1A49,y
$10C4 sta aFD
$10C6 ldy f1798,x
$10C9 lda (aFC),y
$10CB bpl b10F4
$10CD cmp #$c0
$10CF bcc b10D9
$10D1 sta f17AA,x          ; [SMC] STA writes to code region at $17AA
$10D4 iny
$10D5 lda (aFC),y
$10D7 bpl b10F4
b10D9:
$10D9 cmp #$a0             ; x-ref: $10cf
$10DB bcc b10E5
$10DD sta f17A7,x          ; [SMC] STA writes to code region at $17A7
$10E0 iny
$10E1 lda (aFC),y
$10E3 bpl b10F4
b10E5:
$10E5 cmp #$90             ; x-ref: $10db
$10E7 bcc b10EC
$10E9 inc f17A1,x
b10EC:
$10EC and #$0f             ; x-ref: $10e7
$10EE sta f179E,x          ; [SMC] STA writes to code region at $179E
$10F1 iny
$10F2 lda (aFC),y
b10F4:
$10F4 sta f17A4,x          ; [SMC] STA writes to code region at $17A4 ; x-ref: $10cb, $10d7, $10e3
$10F7 beq b10FD
$10F9 cmp #$7e
$10FB bne b1102
b10FD:
$10FD inc f17A1,x          ; x-ref: $10f7
$1100 bne b1108
b1102:
$1102 lda f17B0,x          ; x-ref: $10fb
$1105 sta f17B3,x          ; [SMC] STA writes to code region at $17B3
b1108:
$1108 iny                  ; x-ref: $1100
$1109 tya
$110A sta f1798,x          ; [SMC] STA writes to code region at $1798
$110D lda f179E,x
$1110 sta f178F,x          ; [SMC] STA writes to code region at $178F
$1113 lda #$02
$1115 sta a17F8,x          ; [SMC] STA writes to code region at $17F8
$1118 lda (aFC),y
$111A cmp #$7f
$111C bne b1121
$111E dec f1795,x
b1121:
$1121 ldy a17F8,x          ; x-ref: $10b2, $10b7, $111c
$1124 bmi b115C
$1126 lda f17A1,x
$1129 bne b115C
$112B cpy #$01
$112D beq b1152
$112F cpy #$00
$1131 beq b115F
$1133 lda f17A7,x
$1136 and #$1f
$1138 tay
$1139 lda f1825,y
$113C bpl b114D
$113E and #$0f
$1140 tay
$1141 lda f18D8,y
$1144 sta f17EF,x          ; [SMC] STA writes to code region at $17EF
$1147 lda f18D9,y
$114A sta f17F2,x          ; [SMC] STA writes to code region at $17F2
b114D:
$114D lda #$fe             ; x-ref: $113c
$114F sta f17F5,x          ; [SMC] STA writes to code region at $17F5
b1152:
$1152 lda f17BC,x          ; x-ref: $112d
$1155 cmp #$04
$1157 bcs b115C
$1159 jmp j1540
b115C:
$115C jmp j1379            ; x-ref: $1124, $1129, $1157
b115F:
$115F lda #$ff             ; x-ref: $1131
$1161 sta f17F5,x          ; [SMC] STA writes to code region at $17F5
$1164 lda f17A7,x
$1167 bpl b119F
$1169 and #$1f
$116B sta f17AD,x          ; [SMC] STA writes to code region at $17AD
$116E sta f17A7,x          ; [SMC] STA writes to code region at $17A7
$1171 tay
$1172 lda f17FD,y
$1175 sta f17D4,x          ; [SMC] STA writes to code region at $17D4
$1178 sta f17EF,x          ; [SMC] STA writes to code region at $17EF
$117B lda f1811,y
$117E sta f17D7,x          ; [SMC] STA writes to code region at $17D7
$1181 sta f17F2,x          ; [SMC] STA writes to code region at $17F2
$1184 lda f1825,y
$1187 and #$20
$1189 beq b1193
$118B lda a178B
$118E ora f177A,x
$1191 bne b1199
b1193:
$1193 lda a178B            ; x-ref: $1189
$1196 and f177D,x
b1199:
$1199 sta a178B            ; [SMC] STA writes to code region at $178B ; x-ref: $1191
$119C jmp j11C8
b119F:
$119F ldy f17AD,x          ; x-ref: $1167
$11A2 lda f17D4,x
$11A5 sta f17EF,x          ; [SMC] STA writes to code region at $17EF
$11A8 lda f17D7,x
$11AB sta f17F2,x          ; [SMC] STA writes to code region at $17F2
$11AE lda f17BC,x
$11B1 cmp #$03
$11B3 beq b11CD
$11B5 cmp #$04
$11B7 bne j11C8
$11B9 lda f17CE,x
$11BC sta f17D1,x          ; [SMC] STA writes to code region at $17D1
$11BF lda f17CB,x
$11C2 sta f17C8,x          ; [SMC] STA writes to code region at $17C8
$11C5 jmp b11CD
j11C8:
$11C8 lda #$00             ; x-ref: $119c, $11b7
$11CA sta f17BC,x          ; [SMC] STA writes to code region at $17BC
b11CD:
$11CD lda f1825,y          ; x-ref: $11b3, $11c5
$11D0 and #$10
$11D2 lsr a
$11D3 ora #$01
$11D5 sta f17EC,x          ; [SMC] STA writes to code region at $17EC
$11D8 lda f1825,y
$11DB and #$40
$11DD beq b11F1
$11DF asl a
$11E0 sta a178C            ; [SMC] STA writes to code region at $178C
$11E3 lda f1839,y
$11E6 sta a178E            ; [SMC] STA writes to code region at $178E
$11E9 dec a178E
$11EC lda #$00
$11EE sta a178D            ; [SMC] STA writes to code region at $178D
b11F1:
$11F1 lda f1861,y          ; x-ref: $11dd
$11F4 sta f17BF,x          ; [SMC] STA writes to code region at $17BF
$11F7 lda f184D,y
$11FA sta f17C2,x          ; [SMC] STA writes to code region at $17C2
$11FD lda #$00
$11FF sta f17C5,x          ; [SMC] STA writes to code region at $17C5
* = $1200
j1202:
$1202 lda f17AA,x          ; x-ref: $15de
$1205 bmi b120A
$1207 jmp j131F
b120A:
$120A and #$3f             ; x-ref: $1205
$120C sta f17AA,x          ; [SMC] STA writes to code region at $17AA
$120F tay
$1210 lda f1875,y
$1213 and #$0f
$1215 tay
$1216 lda f1761,y
$1219 sta a1288            ; [SMC] STA writes to code region at $1288
$121C ldy f17AA,x
$121F jmp j1286
$1222 lda f1896,y
$1225 sta f17CB,x          ; [SMC] STA writes to code region at $17CB
$1228 lda f18B7,y
$122B sta f17C8,x          ; [SMC] STA writes to code region at $17C8
$122E lda #$01
$1230 jmp j131C
$1233 lda f1896,y
$1236 sta f17CB,x          ; [SMC] STA writes to code region at $17CB
$1239 lda f18B7,y
$123C sta f17C8,x          ; [SMC] STA writes to code region at $17C8
$123F lda #$03
$1241 jmp j131C
$1244 lda f1896,y
$1247 bmi b1278
$1249 sta f17CB,x          ; [SMC] STA writes to code region at $17CB
$124C sta f17C8,x          ; [SMC] STA writes to code region at $17C8
$124F lda f18B7,y
$1252 sta f17CE,x          ; [SMC] STA writes to code region at $17CE
$1255 sta f17D1,x          ; [SMC] STA writes to code region at $17D1
$1258 lda #$04
$125A jmp j131C
$125D lda f1896,y
$1260 sta f17CB,x          ; [SMC] STA writes to code region at $17CB
$1263 and #$7f
$1265 sta f17C8,x          ; [SMC] STA writes to code region at $17C8
$1268 lda f18B7,y
$126B sta f17D1,x          ; [SMC] STA writes to code region at $17D1
$126E lda #$00
$1270 sta f17CE,x          ; [SMC] STA writes to code region at $17CE
$1273 lda #$05
$1275 jmp j131C
b1278:
$1278 jmp j131A            ; x-ref: $1247
$127B lda f18B7,y
$127E and #$0f
$1280 sta a1785            ; [SMC] STA writes to code region at $1785
$1283 jmp j131F
j1286:
$1286 sec                  ; x-ref: $121f
$1287 bcs b12CE
$1289 lda f18B7,y
$128C and #$0f
$128E sta f17C8,x          ; [SMC] STA writes to code region at $17C8
$1291 lda f1896,y
$1294 clc
$1295 adc #$01
$1297 sta f17CB,x          ; [SMC] STA writes to code region at $17CB
$129A lsr a
$129B bcc b129F
$129D ora #$80
b129F:
$129F sta f17CE,x          ; [SMC] STA writes to code region at $17CE ; x-ref: $129b
$12A2 lda #$02
$12A4 sta f17D1,x          ; [SMC] STA writes to code region at $17D1
$12A7 jmp j131C
$12AA lda f1896,y
$12AD sta f17EF,x          ; [SMC] STA writes to code region at $17EF
$12B0 lda f18B7,y
$12B3 sta f17F2,x          ; [SMC] STA writes to code region at $17F2
$12B6 jmp j131F
$12B9 lda f1896,y
$12BC sta f17D4,x          ; [SMC] STA writes to code region at $17D4
$12BF sta f17EF,x          ; [SMC] STA writes to code region at $17EF
$12C2 lda f18B7,y
$12C5 sta f17D7,x          ; [SMC] STA writes to code region at $17D7
$12C8 sta f17F2,x          ; [SMC] STA writes to code region at $17F2
$12CB jmp j131F
b12CE:
$12CE lda f18B7,y          ; x-ref: $1287
$12D1 sta f17BF,x          ; [SMC] STA writes to code region at $17BF
$12D4 jmp j131F
$12D7 lda #$80
$12D9 sta a178C            ; [SMC] STA writes to code region at $178C
$12DC lda f18B7,y
$12DF sta a178E            ; [SMC] STA writes to code region at $178E
$12E2 dec a178E
$12E5 lda #$00
$12E7 sta a178D            ; [SMC] STA writes to code region at $178D
$12EA jmp j131F
$12ED lda f18B7,y
$12F0 sta f17C2,x          ; [SMC] STA writes to code region at $17C2
$12F3 lda #$00
$12F5 sta f17C5,x          ; [SMC] STA writes to code region at $17C5
$12F8 jmp j131F
$12FB lda f18B7,y
$12FE sta a1780            ; [SMC] STA writes to code region at $1780
$1301 sta a1784            ; [SMC] STA writes to code region at $1784
$1304 tay
$1305 lda f1A1A,y
$1308 cmp #$7f
$130A beq b130F
$130C inc a1784
b130F:
$130F lda f1A19,y          ; x-ref: $130a
$1312 tay
$1313 dey
$1314 sty a1783            ; [SMC] STY writes to code region at $1783
$1317 jmp j131F
j131A:
$131A lda #$00             ; x-ref: $1278
j131C:
$131C sta f17BC,x          ; [SMC] STA writes to code region at $17BC ; x-ref: $1230, $1241, $125a, $1275, $12a7
j131F:
$131F lda f17A1,x          ; x-ref: $1207, $1283, $12b6, $12cb, $12d4, ...
$1322 bne b132A
$1324 lda f17A4,x
$1327 jmp j133E
b132A:
$132A lda f17A4,x          ; x-ref: $1322
$132D beq b1368
$132F cmp #$7e
$1331 beq b136C
$1333 tay
$1334 clc
$1335 adc f17B3,x
$1338 cmp f17B9,x
$133B beq b1371
$133D tya
j133E:
$133E sta f17B6,x          ; [SMC] STA writes to code region at $17B6 ; x-ref: $1327
$1341 clc
$1342 adc f17B3,x
$1345 sta f17B9,x          ; [SMC] STA writes to code region at $17B9
$1348 tay
$1349 lda f17BC,x
$134C cmp #$03
$134E beq b1360
$1350 cmp #$04
$1352 beq b1360
$1354 lda f1701,y
$1357 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$135A lda f16A1,y
$135D sta f17DD,x          ; [SMC] STA writes to code region at $17DD
b1360:
$1360 lda f17A1,x          ; x-ref: $134e, $1352
$1363 bne b136C
$1365 jmp j1582
b1368:
$1368 lda #$fe             ; x-ref: $132d
$136A bne b136E
b136C:
$136C lda #$ff             ; x-ref: $1331, $1363
b136E:
$136E sta f17F5,x          ; [SMC] STA writes to code region at $17F5 ; x-ref: $136a
b1371:
$1371 lda #$00             ; x-ref: $133b
$1373 sta f17A1,x          ; [SMC] STA writes to code region at $17A1
$1376 jmp j15E1
j1379:
$1379 lda f17BC,x          ; x-ref: $115c
$137C tay
$137D lda f1771,y
$1380 sta a1385            ; [SMC] STA writes to code region at $1385
$1383 sec
$1384 bcs b138C
$1386 jmp j14F2
$1389 jmp j1414
b138C:
$138C jmp j1482            ; x-ref: $1384
$138F jmp j14BC
$1392 lda f17DA,x
$1395 clc
$1396 adc f17C8,x
$1399 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
f139C:
$139C lda f17DD,x          ; x-ref: $1736
$139F adc f17CB,x
$13A2 sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$13A5 jmp j14F2
$13A8 ldy f17B9,x
$13AB lda f1702,y
$13AE sbc f1701,y
$13B1 sta aFC
$13B3 lda f16A2,y
$13B6 sbc f16A1,y
$13B9 sta aFD
$13BB lda f17CE,x
$13BE cmp #$80
$13C0 and #$00
$13C2 adc f17C8,x
$13C5 tay
j13C6:
$13C6 dey                  ; x-ref: $13cd
$13C7 bmi b13D0
$13C9 lsr aFD
$13CB ror aFC
$13CD jmp j13C6
b13D0:
$13D0 lda f17D1,x          ; x-ref: $13c7
$13D3 and #$01
$13D5 bne b13EB
$13D7 lda f17DA,x
$13DA clc
$13DB adc aFC
$13DD sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$13E0 lda f17DD,x
$13E3 adc aFD
$13E5 sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$13E8 jmp j13FC
b13EB:
$13EB lda f17DA,x          ; x-ref: $13d5
$13EE sec
$13EF sbc aFC
$13F1 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$13F4 lda f17DD,x
$13F7 sbc aFD
$13F9 sta f17DD,x          ; [SMC] STA writes to code region at $17DD
j13FC:
$13FC lda f17CE,x          ; x-ref: $13e8
$13FF and #$7f
* = $1400
$1401 clc
$1402 adc #$01
$1404 cmp f17CB,x
$1407 bcc b140E
$1409 inc f17D1,x
$140C lda #$00
b140E:
$140E sta f17CE,x          ; [SMC] STA writes to code region at $17CE ; x-ref: $1407
$1411 jmp j14F2
j1414:
$1414 ldy f17B9,x          ; x-ref: $1389
$1417 lda f1701,y
$141A sta aFC
$141C lda f16A1,y
$141F sta aFD
$1421 lda f17DA,x
$1424 sec
$1425 sbc aFC
$1427 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$142A lda f17DD,x
$142D sbc aFD
$142F sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$1432 bmi b144C
$1434 lda f17DA,x
$1437 sec
$1438 sbc f17C8,x
$143B sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$143E lda f17DD,x
$1441 sbc f17CB,x
$1444 sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$1447 bpl b146E
$1449 jmp j1461
b144C:
$144C lda f17DA,x          ; x-ref: $1432
$144F clc
$1450 adc f17C8,x
$1453 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$1456 lda f17DD,x
$1459 adc f17CB,x
$145C sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$145F bmi b146E
j1461:
$1461 lda aFC              ; x-ref: $1449
$1463 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$1466 lda aFD
$1468 sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$146B jmp j147F
b146E:
$146E lda f17DA,x          ; x-ref: $1447, $145f
$1471 clc
$1472 adc aFC
$1474 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$1477 lda f17DD,x
$147A adc aFD
$147C sta f17DD,x          ; [SMC] STA writes to code region at $17DD
j147F:
$147F jmp j14F2            ; x-ref: $146b
j1482:
$1482 ldy f17D1,x          ; x-ref: $138c
$1485 dec f17C8,x
$1488 bpl b14A5
$148A iny
$148B lda f19D7,y
$148E bmi b149B
$1490 cmp #$70
$1492 bmi b149B
$1494 and #$0f
$1496 clc
$1497 adc f17CE,x
$149A tay
b149B:
$149B tya                  ; x-ref: $148e, $1492
$149C sta f17D1,x          ; [SMC] STA writes to code region at $17D1
$149F lda f17CB,x
$14A2 sta f17C8,x          ; [SMC] STA writes to code region at $17C8
b14A5:
$14A5 lda f19D7,y          ; x-ref: $1488
$14A8 clc
$14A9 adc f17B9,x
$14AC tay
$14AD lda f1701,y
$14B0 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$14B3 lda f16A1,y
$14B6 sta f17DD,x          ; [SMC] STA writes to code region at $17DD
$14B9 jmp j14F2
j14BC:
$14BC dec f17C8,x          ; x-ref: $138f
$14BF bpl j14F2
$14C1 lda f17CB,x
$14C4 bmi b14CC
$14C6 inc f17CE,x
$14C9 jmp j14D1
b14CC:
$14CC dec f17CE,x          ; x-ref: $14c4
$14CF and #$7f
j14D1:
$14D1 sta f17C8,x          ; [SMC] STA writes to code region at $17C8 ; x-ref: $14c9
$14D4 dec f17D1,x
$14D7 bne b14DE
$14D9 lda #$00
$14DB sta f17BC,x          ; [SMC] STA writes to code region at $17BC
b14DE:
$14DE lda f17B9,x          ; x-ref: $14d7
$14E1 clc
$14E2 adc f17CE,x
$14E5 tay
$14E6 lda f1701,y
$14E9 sta f17DA,x          ; [SMC] STA writes to code region at $17DA
$14EC lda f16A1,y
$14EF sta f17DD,x          ; [SMC] STA writes to code region at $17DD
j14F2:
$14F2 ldy f17C2,x          ; x-ref: $1386, $13a5, $1411, $147f, $14b9, ...
$14F5 lda f193E,y
$14F8 cmp #$7f
$14FA bne b1508
$14FC lda f1970,y
$14FF cmp f17C2,x
$1502 beq j1540
$1504 sta f17C2,x          ; [SMC] STA writes to code region at $17C2
$1507 tay
b1508:
$1508 lda f193E,y          ; x-ref: $14fa
$150B bpl b1519
$150D sta f17E9,x          ; [SMC] STA writes to code region at $17E9
$1510 lda f1957,y
$1513 sta f17E6,x          ; [SMC] STA writes to code region at $17E6
$1516 jmp j152D
b1519:
$1519 sta aFC              ; x-ref: $150b
$151B lda f17E6,x
$151E clc
$151F adc f1957,y
$1522 sta f17E6,x          ; [SMC] STA writes to code region at $17E6
$1525 lda f17E9,x
$1528 adc aFC
$152A sta f17E9,x          ; [SMC] STA writes to code region at $17E9
j152D:
$152D inc f17C5,x          ; x-ref: $1516
$1530 lda f17C5,x
$1533 cmp f1970,y
$1536 bcc j1540
$1538 inc f17C2,x
$153B lda #$00
$153D sta f17C5,x          ; [SMC] STA writes to code region at $17C5
j1540:
$1540 ldy f17BF,x          ; x-ref: $1159, $1502, $1536
$1543 lda f18DA,y
$1546 cmp #$7f
$1548 bne b1554
$154A lda f190C,y
$154D sta f17BF,x          ; [SMC] STA writes to code region at $17BF
$1550 tay
$1551 lda f18DA,y
b1554:
$1554 sta f17EC,x          ; [SMC] STA writes to code region at $17EC ; x-ref: $1548
$1557 lda f190C,y
$155A beq b1573
$155C cmp #$81
$155E bcs b1564
$1560 clc
$1561 adc f17B9,x
b1564:
$1564 and #$7f             ; x-ref: $155e
$1566 tay
$1567 lda f1701,y
$156A sta f17E0,x          ; [SMC] STA writes to code region at $17E0
$156D lda f16A1,y
$1570 jmp j157C
b1573:
$1573 lda f17DA,x          ; x-ref: $155a
$1576 sta f17E0,x          ; [SMC] STA writes to code region at $17E0
$1579 lda f17DD,x
j157C:
$157C sta f17E3,x          ; [SMC] STA writes to code region at $17E3 ; x-ref: $1570
$157F inc f17BF,x
j1582:
$1582 ldy f1777,x          ; x-ref: $1365
$1585 lda f17E0,x
$1588 sta $d400,y          ; Voice 1: Frequency Control - Low-Byte
$158B lda f17E3,x
$158E sta $d401,y          ; Voice 1: Frequency Control - High-Byte
$1591 lda f17F2,x
$1594 sta $d406,y          ; Voice 1: Sustain / Release Cycle Control
$1597 lda f17EF,x
$159A sta $d405,y          ; Voice 1: Attack / Decay Cycle Control
$159D lda f17E6,x
$15A0 sta $d402,y          ; Voice 1: Pulse Waveform Width - Low-Byte
$15A3 lda f17E9,x
$15A6 sta $d403,y          ; Voice 1: Pulse Waveform Width - High-Nybble
$15A9 lda f17EC,x
$15AC and f17F5,x
$15AF sta $d404,y          ; Voice 1: Control Register
$15B2 lda a17F8,x
$15B5 bne j15E1
$15B7 lda f17A1,x
$15BA beq j15E1
$15BC lda f17BC,x
$15BF cmp #$03
$15C1 beq b15DE
$15C3 cmp #$04
$15C5 beq b15DE
$15C7 lda f17A4,x
$15CA beq b15DE
$15CC cmp #$7e
$15CE beq b15DE
$15D0 clc
$15D1 adc f17B3,x
$15D4 cmp f17B9,x
$15D7 beq b15DE
$15D9 lda #$00
$15DB sta f17BC,x          ; [SMC] STA writes to code region at $17BC
b15DE:
$15DE jmp j1202            ; x-ref: $15c1, $15c5, $15ca, $15ce, $15d7
j15E1:
$15E1 lda a17F8,x          ; x-ref: $1376, $15b5, $15ba
$15E4 bmi b15E9
$15E6 dec a17F8,x
b15E9:
$15E9 dex                  ; x-ref: $15e4
$15EA bmi b15EF
$15EC jmp j106F
b15EF:
$15EF lda a178C            ; x-ref: $15ea
$15F2 bmi b1655
$15F4 beq b165A
$15F6 ldy a178E
$15F9 dec a178D
$15FC bpl b163F
$15FE iny
$15FF lda f1989,y
* = $1600
$1602 cmp #$7f
$1604 bne b1618
$1606 tya
$1607 cmp f19BD,y
$160A bne b1614
$160C lda #$00
$160E sta a178C            ; [SMC] STA writes to code region at $178C
$1611 jmp b165A
b1614:
$1614 lda f19BD,y          ; x-ref: $160a
$1617 tay
b1618:
$1618 lda f1989,y          ; x-ref: $1604
$161B bpl b1639
$161D and #$70
$161F sta a1786            ; [SMC] STA writes to code region at $1786
$1622 lda f1989,y
$1625 and #$0f
$1627 sta a178A            ; [SMC] STA writes to code region at $178A
$162A lda f19A3,y
$162D sta a1789            ; [SMC] STA writes to code region at $1789
$1630 lda f19BD,y
$1633 sta a1787            ; [SMC] STA writes to code region at $1787
$1636 jmp j1652
b1639:
$1639 lda f19BD,y          ; x-ref: $161b
$163C sta a178D            ; [SMC] STA writes to code region at $178D
b163F:
$163F lda a1789            ; x-ref: $15fc
$1642 clc
$1643 adc f19A3,y
$1646 sta a1789            ; [SMC] STA writes to code region at $1789
$1649 lda a178A
$164C adc f1989,y
$164F sta a178A            ; [SMC] STA writes to code region at $178A
j1652:
$1652 sty a178E            ; [SMC] STY writes to code region at $178E ; x-ref: $1636
b1655:
$1655 lda #$40             ; x-ref: $15f2
$1657 sta a178C            ; [SMC] STA writes to code region at $178C
b165A:
$165A lda a178A            ; x-ref: $15f4, $1611
$165D sta aFC
$165F lda a1789
$1662 lsr aFC
$1664 ror a
$1665 tax
$1666 lsr aFC
$1668 ror a
$1669 lsr aFC
$166B ror a
$166C lsr aFC
$166E ror a
$166F tay
$1670 lda a1787
$1673 ora a1788
$1676 sta $d417            ; Filter Resonance Control / Voice Input Control
$1679 sty $d416            ; Filter Cutoff Frequency: High-Byte
$167C txa
$167D and #$07
$167F sta $d415            ; Filter Cutoff Frequency: Low-Nybble
$1682 lda a1785
$1685 ora a1786
$1688 sta $d418            ; Select Filter Mode and Volume
$168B lda a178B
$168E sta a1788            ; [SMC] STA writes to code region at $1788
$1691 rts
j1692:
$1692 sta f1782            ; [SMC] STA writes to code region at $1782 ; x-ref: $1000
$1695 lda #$00
$1697 sta a1781            ; [SMC] STA writes to code region at $1781
$169A rts
j169B:
$169B lda #$40             ; x-ref: $1003
$169D sta a1781            ; [SMC] STA writes to code region at $1781
$16A0 rts
f16A1:
$16A1 ora (p01,x)          ; x-ref: $135a, $13b6, $141c, $14b3, $14ec, ...
$16A3 ora (p01,x)
$16A5 ora (p01,x)
$16A7 ora (p01,x)
$16A9 ora (p01,x)
$16AB ora (p02,x)
$16AD .byte $02            ; Invalid or partial instruction
$16AE .byte $02            ; Invalid or partial instruction
$16AF .byte $02            ; Invalid or partial instruction
$16B0 .byte $02            ; Invalid or partial instruction
$16B1 .byte $02            ; Invalid or partial instruction
$16B2 .byte $02            ; Invalid or partial instruction
$16B3 .byte $03            ; Invalid or partial instruction
$16B4 .byte $03            ; Invalid or partial instruction
$16B5 .byte $03            ; Invalid or partial instruction
$16B6 .byte $03            ; Invalid or partial instruction
$16B7 .byte $03            ; Invalid or partial instruction
$16B8 .byte $04            ; Invalid or partial instruction
$16B9 .byte $04            ; Invalid or partial instruction
$16BA .byte $04            ; Invalid or partial instruction
$16BB .byte $04            ; Invalid or partial instruction
$16BC ora a05
$16BE ora a06
$16C0 asl a06
$16C2 .byte $07            ; Invalid or partial instruction
$16C3 .byte $07            ; Invalid or partial instruction
$16C4 php
$16C5 php
$16C6 ora #$09
$16C8 asl a
$16C9 asl a
$16CA .byte $0b            ; Invalid or partial instruction
$16CB .byte $0c            ; Invalid or partial instruction
$16CC ora a0E0D
$16CF .byte $0f            ; Invalid or partial instruction
$16D0 bpl b16E3
$16D2 .byte $12            ; Invalid or partial instruction
$16D3 .byte $13            ; Invalid or partial instruction
$16D4 .byte $14            ; Invalid or partial instruction
$16D5 ora f17,x
$16D7 clc
$16D8 .byte $1a            ; Invalid or partial instruction
$16D9 .byte $1b            ; Invalid or partial instruction
$16DA ora f201F,x
$16DD .byte $22            ; Invalid or partial instruction
$16DE bit a27
$16E0 and #$2b
$16E2 rol a3431
$16E5 .byte $37            ; Invalid or partial instruction
$16E6 .byte $3a            ; Invalid or partial instruction
$16E7 rol f4541,x
$16EA eor #$4e
$16EC .byte $52            ; Invalid or partial instruction
$16ED .byte $57            ; Invalid or partial instruction
$16EE .byte $5c            ; Invalid or partial instruction
$16EF .byte $62            ; Invalid or partial instruction
$16F0 pla
$16F1 ror a7C75
$16F4 .byte $83            ; Invalid or partial instruction
$16F5 .byte $8b            ; Invalid or partial instruction
$16F6 .byte $93            ; Invalid or partial instruction
$16F7 .byte $9c            ; Invalid or partial instruction
$16F8 lda aAF
$16FA lda fD0C4,y
$16FD cmp fF8EA,x
$1700 sbc f2716,x
$1703 sec
$1704 .byte $4b            ; Invalid or partial instruction
$1705 .byte $5f            ; Invalid or partial instruction
$1706 .byte $73            ; Invalid or partial instruction
$1707 txa
$1708 lda (pBA,x)
$170A .byte $d4            ; Invalid or partial instruction
$170B beq b171B
$170D and a714E
$1710 stx fBD,y
$1712 .byte $e7            ; Invalid or partial instruction
$1713 .byte $13            ; Invalid or partial instruction
$1714 .byte $42            ; Invalid or partial instruction
$1715 .byte $74            ; Invalid or partial instruction
$1716 lda #$e0
$1718 .byte $1b            ; Invalid or partial instruction
$1719 .byte $5a            ; Invalid or partial instruction
$171A .byte $9b            ; Invalid or partial instruction
b171B:
$171B .byte $e2            ; x-ref: $170b, $173d; Invalid or partial instruction
$171C bit aCE7B
$171F .byte $27            ; Invalid or partial instruction
$1720 sta aE8
$1722 eor (pC1),y
$1724 .byte $37            ; Invalid or partial instruction
$1725 ldy f37,x
$1727 cpy a57
$1729 sbc f9C,x
$172B lsr $d009            ; Sprite 4 Y Pos
$172E .byte $a3            ; Invalid or partial instruction
$172F .byte $82            ; Invalid or partial instruction
$1730 ror a6E68
$1733 dey
$1734 .byte $af            ; Invalid or partial instruction
$1735 .byte $eb            ; Invalid or partial instruction
$1736 and f139C,y
$1739 lda (p46,x)
$173B .byte $04            ; Invalid or partial instruction
$173C .byte $dc            ; Invalid or partial instruction
$173D bne b171B
$173F bpl b179F
$1741 dec f72,x
$1743 sec
$1744 rol a42
$1746 sty aB808
$1749 ldy #$b8
$174B jsr eACBC
$174E cpx a70
$1750 jmp j1884
$1753 bpl f17C5
$1755 rti
$1756 bvs f1798
$1758 sei
$1759 cli
$175A iny
$175B cpx #$98
$175D php
$175E bmi a1780
$1760 rol @w a0099
$1763 tax
$1764 .byte $bb            ; Invalid or partial instruction
$1765 .byte $d4            ; Invalid or partial instruction
$1766 and a2D2D
$1769 and (f0030,x)
$176B lsr a6445
$176E .byte $72            ; Invalid or partial instruction
$176F .byte $f2            ; Invalid or partial instruction
$1770 and a0C00
$1773 .byte $22            ; Invalid or partial instruction
$1774 .byte $03            ; Invalid or partial instruction
$1775 asl a09
f1777:
$1777 brk                  ; x-ref: $1582
$1778 .byte $07            ; Invalid or partial instruction
$1779 asl a0201
$177C .byte $04            ; Invalid or partial instruction
f177D:
$177D inc fFBFD,x          ; x-ref: $1196
a1780:
$1780 brk                  ; x-ref: $101d, $1067, $12fe, $175e
a1781:
$1781 rti                  ; x-ref: $1008, $1043, $1697, $169d
f1782:
$1782 brk                  ; x-ref: $1011, $1017, $1692
a1783:
$1783 ora (p01,x)          ; x-ref: $1035, $1051, $105c, $10af, $1314
a1785:
$1785 .byte $0f            ; x-ref: $1028, $1280, $1682; Invalid or partial instruction
a1786:
$1786 bpl f177A            ; x-ref: $1030, $161f, $1685
a1788:
$1788 brk                  ; x-ref: $1673, $168e
a1789:
$1789 and #$10             ; x-ref: $162d, $163f, $1646, $165f
a178B:
$178B brk                  ; x-ref: $118b, $1193, $1199, $168b
a178C:
$178C brk                  ; x-ref: $11e0, $12d9, $15ef, $160e, $1657
a178D:
$178D .byte $ff            ; x-ref: $11ee, $12e7, $15f9, $163c; Invalid or partial instruction
a178E:
$178E .byte $04            ; x-ref: $11e6, $11e9, $12df, $12e2, $15f6, ...; Invalid or partial instruction
f178F:
$178F ora (p01,x)          ; x-ref: $10b4, $1110
$1791 ora (p02,x)
$1793 .byte $02            ; Invalid or partial instruction
$1794 .byte $02            ; Invalid or partial instruction
f1795:
$1795 ora (p01,x)          ; x-ref: $1076, $107b, $111e
$1797 ora (p00,x)
$1799 brk
$179A brk
f179B:
$179B asl a0A00            ; x-ref: $1098, $10b9
f179E:
$179E .byte $0b            ; x-ref: $10ee, $110d; Invalid or partial instruction
b179F:
$179F .byte $0f            ; x-ref: $173f; Invalid or partial instruction
$17A0 asl a
f17A1:
$17A1 brk                  ; x-ref: $10e9, $10fd, $1126, $131f, $1360, ...
$17A2 brk
$17A3 brk
f17A4:
$17A4 brk                  ; x-ref: $10f4, $1324, $132a, $15c7
$17A5 brk
$17A6 ror f0100,x
$17A9 php
f17AA:
$17AA .byte $1a            ; x-ref: $10d1, $1202, $120c, $121c; Invalid or partial instruction
$17AB brk
$17AC .byte $1f            ; Invalid or partial instruction
f17AD:
$17AD brk                  ; x-ref: $116b, $119f
$17AE ora (p08,x)
f17B0:
$17B0 brk                  ; x-ref: $1092, $1102
$17B1 brk
$17B2 brk
f17B3:
$17B3 .byte $0c            ; x-ref: $1105, $1335, $1342, $15d1; Invalid or partial instruction
$17B4 brk
$17B5 brk
f17B6:
$17B6 and #$0e             ; x-ref: $133e
$17B8 .byte $1a            ; Invalid or partial instruction
f17B9:
$17B9 and f0E,x            ; x-ref: $1338, $1345, $13a8, $1414, $14a9, ...
$17BB .byte $1a            ; Invalid or partial instruction
f17BC:
$17BC .byte $04            ; x-ref: $1152, $11ae, $11ca, $131c, $1349, ...; Invalid or partial instruction
$17BD brk
$17BE brk
f17BF:
$17BF .byte $03            ; x-ref: $11f4, $12d1, $1540, $154d, $157f; Invalid or partial instruction
$17C0 php
$17C1 rol a
f17C2:
$17C2 asl a                ; x-ref: $11fa, $12f0, $14f2, $14ff, $1504, ...
$17C3 .byte $04            ; Invalid or partial instruction
$17C4 ora a03
$17C6 ora (a03),y
f17C8:
$17C8 ora (p00,x)          ; x-ref: $11c2, $122b, $123c, $124c, $1265, ...
$17CA .byte $03            ; Invalid or partial instruction
f17CB:
$17CB ora (p00,x)          ; x-ref: $11bf, $1225, $1236, $1249, $1260, ...
$17CD ora a3D
$17CF brk
$17D0 .byte $02            ; Invalid or partial instruction
f17D1:
$17D1 and f0B00,x          ; x-ref: $11bc, $1255, $126b, $12a4, $13d0, ...
f17D4:
$17D4 ora p00              ; x-ref: $1175, $11a2, $12bc
$17D6 brk
f17D7:
$17D7 .byte $3a            ; x-ref: $117e, $11a8, $12c5; Invalid or partial instruction
$17D8 .byte $f7            ; Invalid or partial instruction
$17D9 tay
f17DA:
$17DA and fE271,y          ; x-ref: $1357, $1392, $1399, $13d7, $13dd, ...
f17DD:
$17DD .byte $17            ; x-ref: $135d, $139c, $13a2, $13e0, $13e5, ...; Invalid or partial instruction
$17DE .byte $02            ; Invalid or partial instruction
$17DF .byte $04            ; Invalid or partial instruction
f17E0:
$17E0 and fE271,y          ; x-ref: $156a, $1576, $1585
f17E3:
$17E3 .byte $17            ; x-ref: $157c, $158b; Invalid or partial instruction
$17E4 .byte $02            ; Invalid or partial instruction
$17E5 .byte $04            ; Invalid or partial instruction
f17E6:
$17E6 rts                  ; x-ref: $1513, $151b, $1522, $159d
$17E7 .byte $80            ; Invalid or partial instruction
$17E8 rti
f17E9:
$17E9 .byte $ef            ; x-ref: $150d, $1525, $152a, $15a3; Invalid or partial instruction
$17EA .byte $83            ; Invalid or partial instruction
$17EB ldy f41,x
$17ED eor (p20,x)
f17EF:
$17EF ora p00              ; x-ref: $1144, $1178, $11a5, $12ad, $12bf, ...
$17F1 brk
f17F2:
$17F2 .byte $3a            ; x-ref: $114a, $1181, $11ab, $12b3, $12c8, ...; Invalid or partial instruction
$17F3 .byte $f7            ; Invalid or partial instruction
$17F4 .byte $ab            ; Invalid or partial instruction
f17F5:
$17F5 inc HW_VEC_IRQ_LO,x  ; x-ref: $114f, $1161, $136e, $15ac; IRQ
a17F8:
$17F8 .byte $ff            ; x-ref: $1038, $106f, $1115, $1121, $15b2, ...; Invalid or partial instruction
a17F9:
$17F9 .byte $ff            ; x-ref: $103b; Invalid or partial instruction
a17FA:
$17FA .byte $ff            ; x-ref: $103e; Invalid or partial instruction
f17FB:
$17FB brk                  ; x-ref: $101a
f17FC:
$17FC .byte $0f            ; x-ref: $1023, $102b; Invalid or partial instruction
f17FD:
$17FD ora p00              ; x-ref: $1172
$17FF brk
$1800 .byte $02            ; Invalid or partial instruction
* = $1800
$1800 .byte $02            ; Invalid or partial instruction
$1801 .byte $02            ; Invalid or partial instruction
$1802 brk
$1803 .byte $02            ; Invalid or partial instruction
$1804 brk
$1805 brk
$1806 brk
$1807 bpl b1829
$1809 ldy #$e0
$180B bne b180D
b180D:
$180D brk                  ; x-ref: $180b
$180E ora p00
$1810 brk
f1811:
$1811 .byte $3a            ; x-ref: $117b; Invalid or partial instruction
$1812 .byte $f7            ; Invalid or partial instruction
$1813 inc f07,x
$1815 .byte $f7            ; Invalid or partial instruction
$1816 .byte $67            ; Invalid or partial instruction
$1817 dey
$1818 dey
$1819 tay
$181A pha
$181B bit a3A
$181D and a03
$181F .byte $03            ; Invalid or partial instruction
$1820 .byte $12            ; Invalid or partial instruction
$1821 txa
$1822 ror a78
$1824 .byte $f7            ; Invalid or partial instruction
f1825:
$1825 .byte $80            ; x-ref: $1139, $1184, $11cd, $11d8; Invalid or partial instruction
$1826 cpy #$c0
$1828 cpy #$c0
$182A brk
$182B cpy #$c0
$182D .byte $80            ; Invalid or partial instruction
$182E brk
$182F .byte $80            ; Invalid or partial instruction
$1830 .byte $80            ; Invalid or partial instruction
$1831 brk
$1832 .byte $80            ; Invalid or partial instruction
$1833 .byte $80            ; Invalid or partial instruction
$1834 ldy #$80
$1836 .byte $80            ; Invalid or partial instruction
$1837 .byte $80            ; Invalid or partial instruction
$1838 cpy #$00
$183A brk
$183B asl a0B
$183D ora a0F00
$1840 bpl b1842
b1842:
$1842 brk                  ; x-ref: $1840
$1843 brk
$1844 brk
$1845 brk
$1846 brk
$1847 brk
$1848 .byte $0b            ; Invalid or partial instruction
$1849 brk
$184A brk
$184B brk
$184C asl a09,x
$184E brk
$184F .byte $07            ; Invalid or partial instruction
$1850 brk
$1851 brk
$1852 brk
$1853 brk
$1854 brk
$1855 brk
$1856 brk
$1857 brk
$1858 brk
$1859 brk
$185A brk
$185B brk
$185C brk
$185D brk
$185E asl a0713
f1861:
$1861 brk                  ; x-ref: $11f1
$1862 .byte $04            ; Invalid or partial instruction
$1863 ora #$0e
$1865 .byte $04            ; Invalid or partial instruction
$1866 brk
$1867 ora (p16),y
$1869 clc
$186A .byte $1a            ; Invalid or partial instruction
$186B ora f301F,x
$186E .byte $1b            ; Invalid or partial instruction
$186F .byte $22            ; Invalid or partial instruction
$1870 bit a27
$1872 brk
$1873 .byte $02            ; Invalid or partial instruction
$1874 .byte $2b            ; Invalid or partial instruction
f1875:
$1875 .byte $02            ; x-ref: $1210; Invalid or partial instruction
$1876 .byte $02            ; Invalid or partial instruction
$1877 ora (p01,x)
$1879 .byte $03            ; Invalid or partial instruction
$187A .byte $03            ; Invalid or partial instruction
$187B .byte $03            ; Invalid or partial instruction
$187C .byte $03            ; Invalid or partial instruction
$187D .byte $03            ; Invalid or partial instruction
$187E .byte $03            ; Invalid or partial instruction
$187F .byte $03            ; Invalid or partial instruction
$1880 .byte $03            ; Invalid or partial instruction
$1881 .byte $03            ; Invalid or partial instruction
$1882 .byte $03            ; Invalid or partial instruction
$1883 .byte $03            ; Invalid or partial instruction
j1884:
$1884 .byte $03            ; x-ref: $1750; Invalid or partial instruction
$1885 php
$1886 php
$1887 brk
$1888 brk
$1889 brk
$188A asl a
$188B .byte $02            ; Invalid or partial instruction
$188C .byte $03            ; Invalid or partial instruction
$188D .byte $03            ; Invalid or partial instruction
$188E .byte $03            ; Invalid or partial instruction
$188F .byte $03            ; Invalid or partial instruction
$1890 .byte $02            ; Invalid or partial instruction
$1891 .byte $02            ; Invalid or partial instruction
$1892 .byte $02            ; Invalid or partial instruction
$1893 php
$1894 .byte $0b            ; Invalid or partial instruction
$1895 php
f1896:
$1896 ora (f0080,x)        ; x-ref: $1222, $1233, $1244, $125d, $1291, ...
$1898 .byte $03            ; Invalid or partial instruction
$1899 .byte $04            ; Invalid or partial instruction
$189A ora (p01,x)
$189C ora (p01,x)
$189E ora (p01,x)
$18A0 ora (p01,x)
f18A2:
$18A2 ora (p01,x)          ; x-ref: $1cf1, $1d31, $1dc4, $2265, $247c
$18A4 ora (p01,x)
$18A6 brk
$18A7 brk
$18A8 .byte $ff            ; Invalid or partial instruction
$18A9 .byte $ff            ; Invalid or partial instruction
$18AA .byte $ff            ; Invalid or partial instruction
$18AB brk
$18AC ora (p01,x)
$18AE ora (p01,x)
$18B0 ora (p00,x)
$18B2 .byte $02            ; Invalid or partial instruction
f18B3:
$18B3 brk                  ; x-ref: $26e6, $2726
$18B4 brk
$18B5 brk
$18B6 brk
f18B7:
$18B7 brk                  ; x-ref: $1228, $1239, $124f, $1268, $127b, ...
$18B8 brk
$18B9 .byte $03            ; Invalid or partial instruction
$18BA .byte $03            ; Invalid or partial instruction
$18BB brk
$18BC .byte $04            ; Invalid or partial instruction
$18BD php
$18BE .byte $0c            ; Invalid or partial instruction
b18BF:
$18BF bpl b18D5            ; x-ref: $18c9
$18C1 clc
$18C2 .byte $1c            ; Invalid or partial instruction
$18C3 jsr e2824
$18C6 bit a1428
$18C9 beq b18BF
$18CB .byte $80            ; Invalid or partial instruction
$18CC .byte $13            ; Invalid or partial instruction
$18CD cpy #$30
$18CF and f39,x
$18D1 and @w f0030,x
$18D4 ldy #$00
$18D6 and #$ab
f18D8:
$18D8 .byte $0f            ; x-ref: $1141; Invalid or partial instruction
f18D9:
$18D9 brk                  ; x-ref: $1147
f18DA:
$18DA and (p21,x)          ; x-ref: $1543, $1551
$18DC eor (p7F,x)
$18DE sta (f41,x)
$18E0 eor (f41,x)
$18E2 .byte $7f            ; Invalid or partial instruction
$18E3 sta (f41,x)
$18E5 .byte $80            ; Invalid or partial instruction
$18E6 .byte $80            ; Invalid or partial instruction
$18E7 .byte $7f            ; Invalid or partial instruction
$18E8 sta (p01,x)
$18EA .byte $7f            ; Invalid or partial instruction
$18EB sta (p15,x)
$18ED ora (p11),y
$18EF .byte $7f            ; Invalid or partial instruction
$18F0 sta (p7F,x)
$18F2 and (p7F,x)
$18F4 and (p11,x)
$18F6 .byte $7f            ; Invalid or partial instruction
$18F7 eor (p7F),y
$18F9 ora f40,x
$18FB .byte $7f            ; Invalid or partial instruction
$18FC .byte $53            ; Invalid or partial instruction
$18FD .byte $7f            ; Invalid or partial instruction
$18FE sta (p01,x)
$1900 .byte $7f            ; Invalid or partial instruction
$1901 eor (p7F,x)
$1903 jsr e817F
$1906 eor (f40,x)
$1908 .byte $80            ; Invalid or partial instruction
$1909 .byte $7f            ; Invalid or partial instruction
$190A .byte $13            ; Invalid or partial instruction
$190B .byte $7f            ; Invalid or partial instruction
f190C:
$190C .byte $80            ; x-ref: $154a, $1557; Invalid or partial instruction
$190D .byte $80            ; Invalid or partial instruction
$190E brk
$190F .byte $02            ; Invalid or partial instruction
$1910 cpy #$a1
$1912 txs
$1913 brk
$1914 .byte $07            ; Invalid or partial instruction
$1915 cpy aAC
$1917 cpy #$bc
$1919 .byte $0c            ; Invalid or partial instruction
$191A cpy #$00
b191C:
$191C .byte $0f            ; x-ref: $198a; Invalid or partial instruction
$191D cpy #$00
$191F ror f74,x
$1921 .byte $14            ; Invalid or partial instruction
$1922 ldy f12,x
$1924 brk
$1925 clc
$1926 brk
$1927 brk
$1928 .byte $1b            ; Invalid or partial instruction
$1929 brk
$192A ora @w f00C5,x
$192D jsr s2200
$1930 cpy #$00
$1932 and p00
$1934 .byte $27            ; Invalid or partial instruction
$1935 brk
$1936 and #$c7
$1938 ldx aC0A5
$193B rol a3000
f193E:
$193E dey                  ; x-ref: $14f5, $1508
b193F:
$193F brk                  ; x-ref: $196d
$1940 sta (p00,x)
$1942 brk
$1943 .byte $0f            ; Invalid or partial instruction
$1944 .byte $7f            ; Invalid or partial instruction
$1945 dey
$1946 .byte $7f            ; Invalid or partial instruction
$1947 dey
$1948 .byte $0f            ; Invalid or partial instruction
$1949 .byte $0f            ; Invalid or partial instruction
$194A brk
$194B .byte $7f            ; Invalid or partial instruction
$194C dey
b194D:
$194D brk                  ; x-ref: $195b
$194E .byte $0f            ; Invalid or partial instruction
$194F brk
$1950 .byte $7f            ; Invalid or partial instruction
$1951 stx p00
$1953 .byte $0f            ; Invalid or partial instruction
$1954 brk
$1955 .byte $0f            ; Invalid or partial instruction
$1956 .byte $7f            ; Invalid or partial instruction
f1957:
$1957 brk                  ; x-ref: $1510, $151f
$1958 brk
$1959 bvs b199B
$195B bpl b194D
$195D brk
$195E brk
$195F brk
$1960 brk
$1961 ldy #$f0
$1963 bpl b1965
b1965:
$1965 brk                  ; x-ref: $1963
$1966 .byte $80            ; Invalid or partial instruction
$1967 beq b1979
$1969 brk
$196A brk
$196B .byte $80            ; Invalid or partial instruction
$196C .byte $80            ; Invalid or partial instruction
$196D bmi b193F
$196F brk
f1970:
$1970 brk                  ; x-ref: $14fc, $1533
$1971 ora (p00,x)
$1973 .byte $04            ; Invalid or partial instruction
$1974 jsr e0420
$1977 brk
$1978 .byte $07            ; Invalid or partial instruction
b1979:
$1979 brk                  ; x-ref: $1967
$197A ora p20
$197C jsr @w e000A
$197F .byte $0f            ; Invalid or partial instruction
$1980 bmi b19B2
$1982 bpl b1984
b1984:
$1984 bpl b1996            ; x-ref: $1982
$1986 bmi b19B8
$1988 asl f9F,x
$198A bcc b191C
$198C bcc b199D
$198E .byte $7f            ; Invalid or partial instruction
$198F ldy a90
$1991 cmp (pA5,x)
$1993 .byte $7f            ; Invalid or partial instruction
$1994 lda #$7f
b1996:
$1996 lda #$7f             ; x-ref: $1984
$1998 lda #$97
$199A asl aA97F
b199D:
$199D .byte $0f            ; x-ref: $198c; Invalid or partial instruction
$199E .byte $7f            ; Invalid or partial instruction
$199F .byte $9f            ; Invalid or partial instruction
$19A0 brk
$19A1 .byte $e2            ; Invalid or partial instruction
$19A2 .byte $7f            ; Invalid or partial instruction
f19A3:
$19A3 brk                  ; x-ref: $162a, $1643
$19A4 bit a3A24
$19A7 .byte $ff            ; Invalid or partial instruction
$19A8 brk
$19A9 bmi b19FA
$19AB bvs b1A1D
$19AD brk
$19AE brk
$19AF brk
$19B0 brk
$19B1 brk
b19B2:
$19B2 brk                  ; x-ref: $1980
$19B3 brk
$19B4 bpl b19B6
b19B6:
$19B6 brk                  ; x-ref: $19b4
$19B7 ldx p00
b19B9:
$19B9 brk                  ; x-ref: $1a1c
$19BA brk
$19BB brk
$19BC brk
f19BD:
$19BD .byte $f2            ; x-ref: $1607, $1614, $1630, $1639; Invalid or partial instruction
$19BE .byte $f2            ; Invalid or partial instruction
$19BF .byte $f2            ; Invalid or partial instruction
$19C0 .byte $f2            ; Invalid or partial instruction
$19C1 bpl b19C8
$19C3 .byte $f2            ; Invalid or partial instruction
$19C4 .byte $02            ; Invalid or partial instruction
$19C5 .byte $f2            ; Invalid or partial instruction
$19C6 .byte $f2            ; Invalid or partial instruction
$19C7 asl a
b19C8:
$19C8 .byte $f2            ; x-ref: $19c1; Invalid or partial instruction
$19C9 .byte $0b            ; Invalid or partial instruction
$19CA .byte $f2            ; Invalid or partial instruction
$19CB ora (pF2,x)
$19CD .byte $f2            ; Invalid or partial instruction
$19CE .byte $02            ; Invalid or partial instruction
$19CF .byte $12            ; Invalid or partial instruction
$19D0 .byte $f2            ; Invalid or partial instruction
$19D1 clc
$19D2 ora pF2,x
$19D4 ora (pF2,x)
$19D6 clc
f19D7:
$19D7 brk                  ; x-ref: $148b, $14a5
$19D8 .byte $fc            ; Invalid or partial instruction
$19D9 .byte $f7            ; Invalid or partial instruction
$19DA bvs b19DC
b19DC:
$19DC .byte $fb            ; x-ref: $19da; Invalid or partial instruction
$19DD inc a70,x
$19DF brk
$19E0 sbc f70F8,x
$19E3 brk
$19E4 .byte $fb            ; Invalid or partial instruction
$19E5 inc a70,x
$19E7 brk
$19E8 .byte $fb            ; Invalid or partial instruction
$19E9 .byte $f7            ; Invalid or partial instruction
$19EA bvs b19EC
b19EC:
$19EC .byte $fc            ; x-ref: $19ea; Invalid or partial instruction
$19ED sbc @w a70,y
$19F0 .byte $fb            ; Invalid or partial instruction
$19F1 sed
$19F2 bvs b19F4
b19F4:
$19F4 sbc f70F9,x          ; x-ref: $19f2
$19F7 brk
$19F8 sbc f70FA,x
$19FB brk
$19FC sbc f70F5,y
$19FF brk
$1A00 .byte $fa            ; Invalid or partial instruction
* = $1A00
$1A00 .byte $fa            ; Invalid or partial instruction
$1A01 inc a70,x
$1A03 brk
$1A04 inc f70F8,x
$1A07 brk
$1A08 inc fF5F9,x
$1A0B bvs b1A0D
b1A0D:
$1A0D .byte $fb            ; x-ref: $1a0b; Invalid or partial instruction
$1A0E sbc @w a70,y
$1A11 inc f70F9,x
$1A14 brk
$1A15 .byte $ff            ; Invalid or partial instruction
$1A16 sbc f70F8,x
f1A19:
$1A19 .byte $03            ; x-ref: $1059, $1060, $130f; Invalid or partial instruction
f1A1A:
$1A1A .byte $04            ; x-ref: $1305; Invalid or partial instruction
$1A1B .byte $7f            ; Invalid or partial instruction
f1A1C:
$1A1C bvs b19B9            ; x-ref: $107e
$1A1E .byte $b3            ; Invalid or partial instruction
f1A1F:
$1A1F .byte $1a            ; x-ref: $1083; Invalid or partial instruction
$1A20 .byte $1a            ; Invalid or partial instruction
$1A21 .byte $1a            ; Invalid or partial instruction
f1A22:
$1A22 cmp (pD5),y          ; x-ref: $10bc
$1A24 .byte $f7            ; Invalid or partial instruction
$1A25 .byte $97            ; Invalid or partial instruction
$1A26 cpx aBA57
$1A29 .byte $3b            ; Invalid or partial instruction
$1A2A .byte $fc            ; Invalid or partial instruction
$1A2B ldx a4730
$1A2E lsr f2875,x
$1A31 jmp e806E
$1A34 sta fCBA9,y
$1A37 rol aBA99
$1A3A .byte $db            ; Invalid or partial instruction
$1A3B .byte $a7            ; Invalid or partial instruction
$1A3C lda f25CD,y
$1A3F .byte $f3            ; Invalid or partial instruction
$1A40 lda (p62),y
$1A42 lda aC0B9
$1A45 sbc (p31,x)
$1A47 .byte $af            ; Invalid or partial instruction
$1A48 bmi b1A64
$1A4A .byte $1a            ; Invalid or partial instruction
$1A4B .byte $1a            ; Invalid or partial instruction
$1A4C .byte $1b            ; Invalid or partial instruction
$1A4D .byte $1b            ; Invalid or partial instruction
$1A4E .byte $1c            ; Invalid or partial instruction
$1A4F .byte $1c            ; Invalid or partial instruction
$1A50 ora f1E1D,x
$1A53 .byte $1f            ; Invalid or partial instruction
$1A54 .byte $1f            ; Invalid or partial instruction
$1A55 .byte $1f            ; Invalid or partial instruction
$1A56 .byte $1f            ; Invalid or partial instruction
$1A57 jsr s2020
$1A5A jsr s2020
$1A5D jsr s2121
$1A60 and (p21,x)
$1A62 .byte $22            ; Invalid or partial instruction
$1A63 .byte $22            ; Invalid or partial instruction
b1A64:
$1A64 .byte $22            ; x-ref: $1a48; Invalid or partial instruction
$1A65 .byte $23            ; Invalid or partial instruction
$1A66 .byte $23            ; Invalid or partial instruction
$1A67 bit a25
$1A69 and a25
$1A6B and a25
$1A6D rol a26
$1A6F .byte $27            ; Invalid or partial instruction
$1A70 ldy #$0e
$1A72 .byte $0f            ; Invalid or partial instruction
$1A73 .byte $0f            ; Invalid or partial instruction
$1A74 .byte $0f            ; Invalid or partial instruction
$1A75 .byte $0f            ; Invalid or partial instruction
$1A76 ora (p01),y
$1A78 ora p01
$1A7A .byte $04            ; Invalid or partial instruction
$1A7B ldy a0302
$1A7E ldy #$13
$1A80 .byte $14            ; Invalid or partial instruction
$1A81 .byte $13            ; Invalid or partial instruction
$1A82 ora f0E,x
$1A84 ora (p01),y
$1A86 ora p01
$1A88 .byte $04            ; Invalid or partial instruction
$1A89 ldy a1B02
$1A8C ldy #$13
$1A8E .byte $14            ; Invalid or partial instruction
$1A8F .byte $13            ; Invalid or partial instruction
$1A90 ora f1C,x
$1A92 .byte $1c            ; Invalid or partial instruction
$1A93 .byte $1c            ; Invalid or partial instruction
$1A94 .byte $1c            ; Invalid or partial instruction
$1A95 ldy a1F02
$1A98 jsr @w e00FF
$1A9B ldy #$00
$1A9D .byte $12            ; Invalid or partial instruction
$1A9E asl a06
$1AA0 asl f07
$1AA2 and a25
$1AA4 asl f17,x
$1AA6 asl a06
$1AA8 clc
$1AA9 and a25
$1AAB asl a06
$1AAD asl a06
$1AAF ora fFF21,x
$1AB2 brk
$1AB3 ldy #$0a
$1AB5 asl a
$1AB6 .byte $0b            ; Invalid or partial instruction
$1AB7 .byte $0c            ; Invalid or partial instruction
$1AB8 ldx #$0a
$1ABA ldy #$10
$1ABC php
$1ABD ora #$19
$1ABF ldy aA00D
$1AC2 .byte $0b            ; Invalid or partial instruction
$1AC3 bpl b1ACD
$1AC5 ora #$1a
$1AC7 ldy a230D
$1ACA bit a26
$1ACC ldy #$1e
b1ACE:
$1ACE .byte $22            ; x-ref: $1b02; Invalid or partial instruction
$1ACF .byte $ff            ; Invalid or partial instruction
$1AD0 brk
$1AD1 .byte $8f            ; Invalid or partial instruction
$1AD2 brk
b1AD3:
$1AD3 brk                  ; x-ref: $1b06
$1AD4 .byte $7f            ; Invalid or partial instruction
$1AD5 cpy aA0
$1AD7 sta (f39,x)
$1AD9 and fC439,y
$1ADC lda #$39
$1ADE cpy aA0
$1AE0 .byte $83            ; Invalid or partial instruction
$1AE1 and f3980,y
$1AE4 brk
$1AE5 .byte $83            ; Invalid or partial instruction
$1AE6 and f81C5,y
$1AE9 .byte $3a            ; Invalid or partial instruction
$1AEA cmp aA9
$1AEC .byte $3a            ; Invalid or partial instruction
$1AED cpy aA0
$1AEF sta f39
$1AF1 cpy aA9
$1AF3 sta (f39,x)
$1AF5 and fCA7F,y
$1AF8 ldy #$81
$1AFA bmi b1B2C
$1AFC .byte $80            ; Invalid or partial instruction
$1AFD bmi b1AFF
b1AFF:
$1AFF dex                  ; x-ref: $1afd
$1B00 lda #$81
a1B02:
$1B02 bmi b1ACE            ; x-ref: $1a89
$1B04 ldy #$83
$1B06 bmi b1AD3
$1B08 .byte $80            ; Invalid or partial instruction
$1B09 .byte $2b            ; Invalid or partial instruction
$1B0A brk
$1B0B cpy a85
$1B0D and aA9C4
$1B10 sta (p2D,x)
$1B12 bne b1B41
$1B14 and aA0C4
$1B17 .byte $80            ; Invalid or partial instruction
$1B18 and a8100
$1B1B and aA9C4
$1B1E and aA0CA
$1B21 rol a802E
$1B24 rol aCA00
$1B27 lda #$81
$1B29 rol aA0CA
b1B2C:
$1B2C .byte $83            ; x-ref: $1afa; Invalid or partial instruction
$1B2D rol a80CB
$1B30 and #$00
$1B32 cpy a85
$1B34 .byte $2b            ; Invalid or partial instruction
$1B35 cpy aA9
$1B37 sta (p2B,x)
$1B39 bne b1B66
$1B3B .byte $2b            ; Invalid or partial instruction
$1B3C cpy aA0
$1B3E .byte $80            ; Invalid or partial instruction
$1B3F .byte $2b            ; Invalid or partial instruction
$1B40 brk
b1B41:
$1B41 sta (p2B,x)          ; x-ref: $1b12
$1B43 cpy aA9
$1B45 .byte $2b            ; Invalid or partial instruction
$1B46 dex
$1B47 ldy #$2d
$1B49 and a2D80
$1B4C brk
$1B4D dex
$1B4E lda #$81
$1B50 and aA0CA
$1B53 .byte $83            ; Invalid or partial instruction
$1B54 and a80CB
$1B57 plp
$1B58 brk
$1B59 dec a85
$1B5B and #$80
$1B5D and #$00
$1B5F dec aA9
$1B61 sta (p29,x)
$1B63 dec aA0
$1B65 .byte $80            ; Invalid or partial instruction
b1B66:
$1B66 and #$00             ; x-ref: $1b39
$1B68 sta (p29,x)
$1B6A dec aA9
$1B6C and #$29
$1B6E dex
$1B6F ldy #$2b
$1B71 .byte $2b            ; Invalid or partial instruction
$1B72 .byte $80            ; Invalid or partial instruction
$1B73 .byte $2b            ; Invalid or partial instruction
$1B74 brk
$1B75 dex
$1B76 lda #$81
$1B78 .byte $2b            ; Invalid or partial instruction
$1B79 dex
$1B7A ldy #$83
$1B7C .byte $2b            ; Invalid or partial instruction
$1B7D .byte $cb            ; Invalid or partial instruction
$1B7E .byte $80            ; Invalid or partial instruction
$1B7F rol p00
$1B81 cpy a2985
$1B84 cpy a81A9
$1B87 and #$d0
$1B89 and #$29
$1B8B cpy a80A0
$1B8E and #$00
$1B90 and #$00
$1B92 cpy a81A9
$1B95 and #$7f
$1B97 .byte $cb            ; Invalid or partial instruction
$1B98 lda #$81
$1B9A and #$cb
$1B9C ldy #$80
$1B9E and #$00
$1BA0 .byte $83            ; Invalid or partial instruction
$1BA1 and #$80
$1BA3 and #$00
$1BA5 .byte $cb            ; Invalid or partial instruction
$1BA6 lda #$81
$1BA8 and #$cb
$1BAA ldy #$83
$1BAC and #$80
$1BAE and #$00
$1BB0 .byte $cb            ; Invalid or partial instruction
$1BB1 lda #$81
$1BB3 and #$c8
$1BB5 ldy #$80
b1BB7:
$1BB7 .byte $2b            ; x-ref: $1be6; Invalid or partial instruction
$1BB8 brk
$1BB9 cmp a2D85
$1BBC cmp a81A9
$1BBF and aCB2D
$1BC2 ldy #$80
$1BC4 .byte $2b            ; Invalid or partial instruction
$1BC5 brk
$1BC6 .byte $2b            ; Invalid or partial instruction
$1BC7 brk
$1BC8 .byte $83            ; Invalid or partial instruction
$1BC9 .byte $2b            ; Invalid or partial instruction
$1BCA .byte $80            ; Invalid or partial instruction
$1BCB .byte $2b            ; Invalid or partial instruction
$1BCC brk
$1BCD .byte $cb            ; Invalid or partial instruction
$1BCE lda #$2b
$1BD0 brk
$1BD1 .byte $cb            ; Invalid or partial instruction
$1BD2 ldy #$2b
$1BD4 brk
$1BD5 .byte $83            ; Invalid or partial instruction
$1BD6 .byte $2b            ; Invalid or partial instruction
$1BD7 iny
$1BD8 sta (p2D,x)
$1BDA iny
$1BDB lda #$2d
$1BDD dec a2EA0
$1BE0 dec a2EA9
$1BE3 .byte $cf            ; Invalid or partial instruction
$1BE4 ldy #$83
$1BE6 bmi b1BB7
$1BE8 lda #$81
$1BEA bmi b1C6B
$1BEC dec aA9
$1BEE sta (p35,x)
$1BF0 dec aA0
$1BF2 .byte $80            ; Invalid or partial instruction
$1BF3 and p00,x
$1BF5 and p00,x
$1BF7 .byte $83            ; Invalid or partial instruction
$1BF8 and f0080,x
$1BFA and p00,x
$1BFC dec aA9
$1BFE sta (p35,x)
$1C00 dec aA0
* = $1C00
$1C00 dec aA0
b1C02:
$1C02 .byte $80            ; x-ref: $1c3c; Invalid or partial instruction
$1C03 and p00,x
$1C05 .byte $c7            ; Invalid or partial instruction
$1C06 .byte $83            ; Invalid or partial instruction
$1C07 .byte $37            ; Invalid or partial instruction
$1C08 sta (f37,x)
$1C0A .byte $c7            ; Invalid or partial instruction
$1C0B lda #$37
$1C0D dec aA0
$1C0F stx p35
$1C11 .byte $80            ; Invalid or partial instruction
$1C12 brk
$1C13 cmp #$34
$1C15 brk
$1C16 .byte $34            ; Invalid or partial instruction
$1C17 brk
$1C18 .byte $83            ; Invalid or partial instruction
$1C19 .byte $34            ; Invalid or partial instruction
$1C1A sta (p34,x)
$1C1C cmp #$a9
$1C1E .byte $34            ; Invalid or partial instruction
$1C1F cmp #$a0
$1C21 .byte $80            ; Invalid or partial instruction
$1C22 .byte $34            ; Invalid or partial instruction
$1C23 brk
$1C24 dex
$1C25 .byte $83            ; Invalid or partial instruction
$1C26 and f0081,x
$1C28 and fCA,x
$1C2A lda #$35
$1C2C cmp #$a0
$1C2E .byte $83            ; Invalid or partial instruction
$1C2F .byte $34            ; Invalid or partial instruction
$1C30 .byte $80            ; Invalid or partial instruction
$1C31 .byte $34            ; Invalid or partial instruction
$1C32 brk
$1C33 dec f0081
$1C35 bmi b1BFD
$1C37 lda #$30
$1C39 dec aA0
$1C3B .byte $83            ; Invalid or partial instruction
$1C3C bmi b1C02
$1C3E .byte $80            ; Invalid or partial instruction
$1C3F .byte $32            ; Invalid or partial instruction
$1C40 brk
$1C41 sta a32
$1C43 cpy aA9
$1C45 sta (a32,x)
$1C47 bne b1C7B
$1C49 .byte $32            ; Invalid or partial instruction
$1C4A bne b1C7E
$1C4C bne b1C80
$1C4E .byte $32            ; Invalid or partial instruction
$1C4F bne b1C83
$1C51 bne b1C85
$1C53 .byte $32            ; Invalid or partial instruction
$1C54 bne b1C88
$1C56 .byte $7f            ; Invalid or partial instruction
$1C57 dec aA0
$1C59 sta (p35,x)
$1C5B and p35,x
$1C5D dec aA9
$1C5F and fC6,x
$1C61 ldy #$83
$1C63 and f0080,x
$1C65 and p00,x
$1C67 .byte $c7            ; Invalid or partial instruction
$1C68 .byte $83            ; Invalid or partial instruction
$1C69 .byte $37            ; Invalid or partial instruction
$1C6A .byte $80            ; Invalid or partial instruction
b1C6B:
$1C6B .byte $37            ; x-ref: $1bea; Invalid or partial instruction
$1C6C brk
$1C6D .byte $c7            ; Invalid or partial instruction
$1C6E lda #$37
$1C70 brk
$1C71 dec aA0
$1C73 stx p35
$1C75 .byte $80            ; Invalid or partial instruction
$1C76 brk
$1C77 iny
$1C78 .byte $32            ; Invalid or partial instruction
$1C79 brk
$1C7A cmp #$81
$1C7C .byte $34            ; Invalid or partial instruction
$1C7D .byte $34            ; Invalid or partial instruction
b1C7E:
$1C7E .byte $34            ; x-ref: $1c4a; Invalid or partial instruction
$1C7F cmp #$a9
$1C81 .byte $80            ; Invalid or partial instruction
$1C82 .byte $34            ; Invalid or partial instruction
b1C83:
$1C83 brk                  ; x-ref: $1c4f
$1C84 cmp #$a0
$1C86 .byte $83            ; Invalid or partial instruction
$1C87 .byte $34            ; Invalid or partial instruction
b1C88:
$1C88 .byte $80            ; x-ref: $1c54; Invalid or partial instruction
$1C89 .byte $34            ; Invalid or partial instruction
$1C8A brk
$1C8B dex
$1C8C .byte $83            ; Invalid or partial instruction
$1C8D and f0081,x
$1C8F and fCA,x
$1C91 lda #$80
$1C93 and p00,x
$1C95 cmp #$a0
$1C97 .byte $83            ; Invalid or partial instruction
$1C98 .byte $34            ; Invalid or partial instruction
$1C99 .byte $80            ; Invalid or partial instruction
$1C9A .byte $34            ; Invalid or partial instruction
$1C9B brk
$1C9C dec a83
$1C9E bmi b1CD0
$1CA0 cpy f0080
$1CA2 .byte $32            ; Invalid or partial instruction
$1CA3 brk
$1CA4 sta a32
$1CA6 cpy aA9
$1CA8 sta (a32,x)
$1CAA bne b1CDE
$1CAC .byte $32            ; Invalid or partial instruction
$1CAD bne b1CE1
$1CAF bne b1CE3
$1CB1 .byte $32            ; Invalid or partial instruction
$1CB2 bne b1CE6
$1CB4 bne b1CE8
$1CB6 .byte $32            ; Invalid or partial instruction
$1CB7 bne b1CEB
$1CB9 .byte $7f            ; Invalid or partial instruction
$1CBA lda (a83,x)
$1CBC ora (pA6),y
$1CBE sta (p3C,x)
$1CC0 .byte $a7            ; Invalid or partial instruction
$1CC1 eor aA2
$1CC3 clc
$1CC4 .byte $a7            ; Invalid or partial instruction
$1CC5 pha
$1CC6 ldy f0080
$1CC8 ora (p00),y
$1CCA lda (a83,x)
$1CCC ora (f0081),y
$1CCE brk
$1CCF ldx p3C
$1CD1 .byte $a7            ; Invalid or partial instruction
$1CD2 .byte $43            ; Invalid or partial instruction
$1CD3 ldx #$18
$1CD5 .byte $a7            ; Invalid or partial instruction
$1CD6 pha
$1CD7 ldy a83
$1CD9 ora fA1,x
$1CDB .byte $1a            ; Invalid or partial instruction
$1CDC ldx f0081
b1CDE:
$1CDE and f41A7,y          ; x-ref: $1caa
b1CE1:
$1CE1 ldx #$18             ; x-ref: $1cad
b1CE3:
$1CE3 .byte $a7            ; x-ref: $1caf; Invalid or partial instruction
$1CE4 pha
$1CE5 ldy f0080
$1CE7 .byte $1a            ; Invalid or partial instruction
b1CE8:
$1CE8 brk                  ; x-ref: $1cb4
$1CE9 lda (a83,x)
b1CEB:
$1CEB .byte $1a            ; x-ref: $1cb7; Invalid or partial instruction
$1CEC sta (p00,x)
$1CEE ldx f39
$1CF0 .byte $a7            ; Invalid or partial instruction
$1CF1 rol f18A2,x
$1CF4 .byte $a7            ; Invalid or partial instruction
$1CF5 pha
$1CF6 ldy a1F
$1CF8 bcc b1D0D
$1CFA brk
$1CFB lda (a83,x)
$1CFD ora pA6,x
$1CFF sta (p3C,x)
$1D01 .byte $a7            ; Invalid or partial instruction
$1D02 rti
$1D03 ldx #$18
$1D05 .byte $a7            ; Invalid or partial instruction
$1D06 pha
$1D07 ldy f0080
$1D09 ora p00,x
$1D0B lda (a83,x)
b1D0D:
$1D0D ora f0081,x          ; x-ref: $1cf8
$1D0F brk
$1D10 ldx p34
$1D12 .byte $a7            ; Invalid or partial instruction
$1D13 .byte $3c            ; Invalid or partial instruction
$1D14 ldx #$18
$1D16 .byte $a7            ; Invalid or partial instruction
$1D17 eor aA3
$1D19 bit fA1
$1D1B ora a83,x
$1D1D asl pA6,x
$1D1F sta (a3A,x)
$1D21 .byte $a7            ; Invalid or partial instruction
$1D22 eor (aA2,x)
$1D24 clc
$1D25 .byte $a7            ; Invalid or partial instruction
$1D26 lsr a
$1D27 ldy p16
$1D29 lda (a83,x)
$1D2B asl a
$1D2C sta (p00,x)
$1D2E ldx p35
$1D30 .byte $a7            ; Invalid or partial instruction
$1D31 rol f18A2,x
$1D34 .byte $a7            ; Invalid or partial instruction
$1D35 lsr aA4
$1D37 clc
$1D38 sta (p1A),y
$1D3A .byte $7f            ; Invalid or partial instruction
$1D3B lda (a83,x)
$1D3D clc
$1D3E ldx f0081
$1D40 .byte $43            ; Invalid or partial instruction
$1D41 .byte $a7            ; Invalid or partial instruction
$1D42 pha
$1D43 ldx #$83
$1D45 clc
$1D46 ldy f0080
$1D48 clc
$1D49 brk
$1D4A lda (a83,x)
$1D4C ora (f0080),y
$1D4E ora fA600,x
$1D51 sta (p43,x)
$1D53 .byte $a7            ; Invalid or partial instruction
$1D54 eor aA2
$1D56 clc
$1D57 lda (p15,x)
$1D59 ldy a18
$1D5B sta (f17),y
$1D5D lda (a83,x)
$1D5F asl pA6,x
$1D61 sta (f41,x)
$1D63 .byte $a7            ; Invalid or partial instruction
$1D64 lsr aA2
$1D66 .byte $83            ; Invalid or partial instruction
$1D67 clc
$1D68 ldy f0080
$1D6A asl p00,x
$1D6C lda (f0081,x)
$1D6E .byte $1b            ; Invalid or partial instruction
$1D6F sta (p16),y
$1D71 .byte $0f            ; Invalid or partial instruction
$1D72 .byte $a7            ; Invalid or partial instruction
$1D73 eor (pA6,x)
$1D75 .byte $43            ; Invalid or partial instruction
$1D76 ldx #$18
$1D78 lda (a1F,x)
$1D7A ldy a1B
$1D7C sta (p1A),y
$1D7E lda (a83,x)
$1D80 ora f81A6,y
$1D83 rti
$1D84 lda (p15,x)
$1D86 ldx #$18
$1D88 ldy a10
$1D8A sta f0E,x
$1D8C sta (p1A,x)
$1D8E ldx f40
$1D90 .byte $a7            ; Invalid or partial instruction
$1D91 eor (aA2,x)
$1D93 clc
$1D94 lda (p15,x)
$1D96 .byte $a3            ; Invalid or partial instruction
$1D97 bit fA1
$1D99 .byte $80            ; Invalid or partial instruction
$1D9A ora p00,x
$1D9C .byte $83            ; Invalid or partial instruction
$1D9D .byte $17            ; Invalid or partial instruction
$1D9E ldx f0081
$1DA0 rol f43A7,x
$1DA3 ldx #$83
$1DA5 clc
$1DA6 ldy f0080
$1DA8 ora (p00),y
$1DAA lda (a85,x)
$1DAC .byte $13            ; Invalid or partial instruction
$1DAD ldx f0081
$1DAF .byte $3b            ; Invalid or partial instruction
$1DB0 .byte $a7            ; Invalid or partial instruction
$1DB1 eor (aA2,x)
$1DB3 clc
$1DB4 lda (f0080,x)
$1DB6 ora (p00),y
$1DB8 ldy f0081
$1DBA .byte $13            ; Invalid or partial instruction
$1DBB sta (p15),y
$1DBD lda (a83,x)
$1DBF asl pA6,x
$1DC1 sta (a3A,x)
$1DC3 .byte $a7            ; Invalid or partial instruction
$1DC4 rol f18A2,x
$1DC7 .byte $a7            ; Invalid or partial instruction
$1DC8 eor aA4
$1DCA .byte $80            ; Invalid or partial instruction
$1DCB ora (p00),y
$1DCD lda (a85,x)
$1DCF asl a
$1DD0 .byte $a7            ; Invalid or partial instruction
$1DD1 sta (a3A,x)
$1DD3 ldx a3E
$1DD5 ldx #$18
$1DD7 ldx p43
$1DD9 .byte $a3            ; Invalid or partial instruction
$1DDA .byte $83            ; Invalid or partial instruction
$1DDB bit fA1
$1DDD clc
$1DDE ldx f0081
$1DE0 .byte $3c            ; Invalid or partial instruction
$1DE1 .byte $a7            ; Invalid or partial instruction
$1DE2 rti
$1DE3 ldx #$18
$1DE5 .byte $a7            ; Invalid or partial instruction
$1DE6 eor aA4
$1DE8 .byte $80            ; Invalid or partial instruction
$1DE9 .byte $13            ; Invalid or partial instruction
$1DEA brk
$1DEB lda (a85,x)
b1DED:
$1DED .byte $0c            ; x-ref: $1e2b; Invalid or partial instruction
$1DEE ldx f0081
$1DF0 .byte $37            ; Invalid or partial instruction
$1DF1 .byte $a7            ; Invalid or partial instruction
$1DF2 .byte $3c            ; Invalid or partial instruction
$1DF3 .byte $b3            ; Invalid or partial instruction
$1DF4 clc
$1DF5 .byte $a7            ; Invalid or partial instruction
$1DF6 .byte $83            ; Invalid or partial instruction
$1DF7 .byte $43            ; Invalid or partial instruction
$1DF8 .byte $b3            ; Invalid or partial instruction
$1DF9 sta (a18,x)
$1DFB .byte $7f            ; Invalid or partial instruction
$1DFC .byte $87            ; Invalid or partial instruction
$1DFD brk
$1DFE tay
$1DFF .byte $80            ; Invalid or partial instruction
$1E00 .byte $37            ; Invalid or partial instruction
* = $1E00
$1E00 .byte $37            ; Invalid or partial instruction
$1E01 cpy #$92
$1E03 and f81C3,y
$1E06 ror f8300,x
$1E09 .byte $37            ; Invalid or partial instruction
$1E0A brk
$1E0B and fC3,x
$1E0D sta (a007E,x)
$1E0F brk
$1E10 .byte $83            ; Invalid or partial instruction
$1E11 .byte $34            ; Invalid or partial instruction
$1E12 cpy #$93
$1E14 and p00,x
$1E16 cmp (f37,x)
$1E18 brk
$1E19 .byte $80            ; Invalid or partial instruction
$1E1A .byte $32            ; Invalid or partial instruction
$1E1B cpy #$94
f1E1D:
$1E1D .byte $34            ; x-ref: $1a50; Invalid or partial instruction
$1E1E sta (p00,x)
$1E20 cmp (a83,x)
$1E22 bmi b1DE7
$1E24 ror @w f0089,x
$1E27 .byte $80            ; Invalid or partial instruction
$1E28 and f8300
$1E2B bmi b1DED
$1E2D .byte $93            ; Invalid or partial instruction
$1E2E .byte $32            ; Invalid or partial instruction
$1E2F cmp (p34,x)
$1E31 cpy #$91
$1E33 and fC3,x
$1E35 sta a007E
$1E37 cmp (f0081,x)
$1E39 .byte $32            ; Invalid or partial instruction
$1E3A .byte $83            ; Invalid or partial instruction
$1E3B brk
$1E3C tax
$1E3D sta (p3C,x)
$1E3F bcc b1E7F
$1E41 brk
$1E42 .byte $43            ; Invalid or partial instruction
$1E43 brk
$1E44 cmp (p35),y
$1E46 brk
$1E47 sta (f41,x)
$1E49 cmp (f0080),y
$1E4B .byte $3a            ; Invalid or partial instruction
$1E4C brk
$1E4D rol a8100,x
$1E50 .byte $3c            ; Invalid or partial instruction
$1E51 sta (a3E),y
$1E53 sta (p3C),y
$1E55 cmp (f0080),y
$1E57 and f0088,x
$1E59 brk
$1E5A tay
$1E5B .byte $80            ; Invalid or partial instruction
$1E5C .byte $37            ; Invalid or partial instruction
$1E5D cpy #$92
$1E5F and f81C3,y
$1E62 ror f8300,x
$1E65 .byte $3c            ; Invalid or partial instruction
$1E66 brk
$1E67 and fC3,x
$1E69 sta (a007E,x)
$1E6B brk
$1E6C .byte $83            ; Invalid or partial instruction
$1E6D .byte $34            ; Invalid or partial instruction
$1E6E cpy #$93
$1E70 and p00,x
$1E72 cmp (f37,x)
$1E74 brk
$1E75 and f8000,y
$1E78 rol fC0,x
$1E7A sty f37,x
$1E7C .byte $c3            ; Invalid or partial instruction
$1E7D sta (a007E,x)
b1E7F:
$1E7F .byte $89            ; x-ref: $1e3f; Invalid or partial instruction
$1E80 brk
$1E81 .byte $80            ; Invalid or partial instruction
$1E82 bmi b1E84
b1E84:
$1E84 and fC0,x            ; x-ref: $1e82
$1E86 .byte $92            ; Invalid or partial instruction
$1E87 .byte $37            ; Invalid or partial instruction
b1E88:
$1E88 .byte $93            ; x-ref: $1f03; Invalid or partial instruction
$1E89 and f34C1,y
$1E8C and fC3,x
$1E8E ror f3E81,x
$1E91 .byte $83            ; Invalid or partial instruction
$1E92 brk
$1E93 tax
$1E94 sta (p3C,x)
$1E96 bcc b1ED6
$1E98 brk
$1E99 eor p00
$1E9B cmp (a3A),y
$1E9D brk
$1E9E sta (f41,x)
$1EA0 bcc b1EE0
$1EA2 brk
$1EA3 cmp (p35),y
$1EA5 brk
$1EA6 tay
$1EA7 .byte $3c            ; Invalid or partial instruction
$1EA8 cpy #$92
$1EAA rol f3C93,x
$1EAD .byte $7f            ; Invalid or partial instruction
$1EAE .byte $c3            ; Invalid or partial instruction
$1EAF sty a007E
$1EB1 .byte $82            ; Invalid or partial instruction
$1EB2 brk
$1EB3 tay
$1EB4 .byte $80            ; Invalid or partial instruction
$1EB5 and f92C0,y
$1EB8 .byte $3a            ; Invalid or partial instruction
$1EB9 .byte $93            ; Invalid or partial instruction
$1EBA and f7EC3,y
$1EBD brk
$1EBE .byte $80            ; Invalid or partial instruction
$1EBF and fC0,x
$1EC1 .byte $92            ; Invalid or partial instruction
$1EC2 .byte $37            ; Invalid or partial instruction
$1EC3 .byte $93            ; Invalid or partial instruction
$1EC4 and fC3,x
$1EC6 ror f8000,x
$1EC9 bmi b1E8B
$1ECB .byte $92            ; Invalid or partial instruction
$1ECC .byte $32            ; Invalid or partial instruction
$1ECD .byte $93            ; Invalid or partial instruction
$1ECE rol a84C3
$1ED1 ror @w f0088,x
$1ED4 .byte $80            ; Invalid or partial instruction
$1ED5 and f8300
$1ED8 and (fC0),y
$1EDA sta (a32),y
$1EDC cmp (f0080,x)
$1EDE .byte $34            ; Invalid or partial instruction
$1EDF .byte $82            ; Invalid or partial instruction
b1EE0:
$1EE0 brk                  ; x-ref: $1ea0
$1EE1 sta (f37,x)
$1EE3 .byte $83            ; Invalid or partial instruction
$1EE4 and fC3,x
$1EE6 ror f3281,x
$1EE9 .byte $80            ; Invalid or partial instruction
$1EEA and a3700
$1EED cpy #$92
$1EEF and f3797,y
$1EF2 .byte $c3            ; Invalid or partial instruction
$1EF3 .byte $83            ; Invalid or partial instruction
$1EF4 ror @w a85,x
b1EF7:
$1EF7 .byte $80            ; x-ref: $1f75; Invalid or partial instruction
$1EF8 .byte $32            ; Invalid or partial instruction
$1EF9 brk
$1EFA .byte $34            ; Invalid or partial instruction
$1EFB cpy #$92
$1EFD and f91,x
$1EFF .byte $34            ; Invalid or partial instruction
$1F00 cmp (a32,x)
a1F02:
$1F02 brk                  ; x-ref: $1a95
$1F03 bmi b1E88
$1F05 .byte $32            ; Invalid or partial instruction
$1F06 .byte $c3            ; Invalid or partial instruction
$1F07 .byte $87            ; Invalid or partial instruction
$1F08 ror @w a83,x
$1F0B .byte $80            ; Invalid or partial instruction
$1F0C .byte $32            ; Invalid or partial instruction
$1F0D brk
$1F0E .byte $34            ; Invalid or partial instruction
$1F0F brk
$1F10 .byte $34            ; Invalid or partial instruction
$1F11 cpy #$92
$1F13 and f91,x
$1F15 .byte $34            ; Invalid or partial instruction
$1F16 cmp (f0080,x)
$1F18 .byte $32            ; Invalid or partial instruction
$1F19 .byte $82            ; Invalid or partial instruction
$1F1A brk
$1F1B sta (f0030,x)
$1F1D .byte $80            ; Invalid or partial instruction
$1F1E .byte $32            ; Invalid or partial instruction
$1F1F cpy #$92
$1F21 .byte $34            ; Invalid or partial instruction
$1F22 .byte $c3            ; Invalid or partial instruction
$1F23 .byte $83            ; Invalid or partial instruction
$1F24 ror f3291,x
$1F27 bcc b1F5C
$1F29 bcc b1F5D
$1F2B .byte $93            ; Invalid or partial instruction
$1F2C bmi b1EF1
$1F2E ror fAB7F,x
$1F31 sta (p29,x)
$1F33 .byte $c2            ; Invalid or partial instruction
$1F34 ror f8329,x
$1F37 and p29,x
$1F39 sta (p29,x)
$1F3B .byte $c2            ; Invalid or partial instruction
$1F3C ror f2929,x
$1F3F and fD2,x
$1F41 ror f2983,x
$1F44 sta (a27,x)
$1F46 .byte $7f            ; Invalid or partial instruction
$1F47 .byte $ab            ; Invalid or partial instruction
$1F48 sta (p29,x)
$1F4A .byte $c2            ; Invalid or partial instruction
$1F4B ror f8329,x
$1F4E and p29,x
$1F50 sta (p29,x)
$1F52 .byte $c2            ; Invalid or partial instruction
$1F53 ror f2929,x
$1F56 and fD2,x
$1F58 ror f2983,x
$1F5B sta (p28,x)
b1F5D:
$1F5D .byte $7f            ; x-ref: $1f29; Invalid or partial instruction
$1F5E .byte $ab            ; Invalid or partial instruction
$1F5F sta (p29,x)
$1F61 .byte $c2            ; Invalid or partial instruction
$1F62 ror f8329,x
$1F65 and p29,x
$1F67 sta (p29,x)
$1F69 .byte $c2            ; Invalid or partial instruction
$1F6A ror f2929,x
$1F6D and fD2,x
$1F6F ror f2983,x
$1F72 sta (p2D,x)
$1F74 .byte $7f            ; Invalid or partial instruction
$1F75 bcs b1EF7
$1F77 .byte $37            ; Invalid or partial instruction
$1F78 dec f92,x
$1F7A and f8FC3,y
$1F7D brk
$1F7E .byte $80            ; Invalid or partial instruction
$1F7F bmi b1F81
b1F81:
$1F81 bmi b1F83            ; x-ref: $1f7f
b1F83:
$1F83 sta (f0030,x)        ; x-ref: $1f81
$1F85 sta (a32),y
$1F87 sta (p35),y
$1F89 .byte $80            ; Invalid or partial instruction
$1F8A .byte $37            ; Invalid or partial instruction
$1F8B brk
$1F8C .byte $37            ; Invalid or partial instruction
$1F8D dec f92,x
$1F8F and f81C1,y
$1F92 .byte $3c            ; Invalid or partial instruction
$1F93 .byte $c3            ; Invalid or partial instruction
$1F94 sta f8000
$1F97 bmi b1F99
b1F99:
$1F99 bmi b1F9B            ; x-ref: $1f97
b1F9B:
$1F9B sta (f0030,x)        ; x-ref: $1f99
$1F9D sta (a32),y
$1F9F bcc b1FD6
$1FA1 brk
$1FA2 .byte $37            ; Invalid or partial instruction
$1FA3 brk
$1FA4 .byte $32            ; Invalid or partial instruction
$1FA5 dec f92,x
$1FA7 .byte $34            ; Invalid or partial instruction
$1FA8 cmp (f0080,x)
$1FAA and p00,x
$1FAC .byte $32            ; Invalid or partial instruction
$1FAD dec f93,x
$1FAF .byte $34            ; Invalid or partial instruction
$1FB0 .byte $c3            ; Invalid or partial instruction
$1FB1 .byte $82            ; Invalid or partial instruction
$1FB2 brk
$1FB3 cmp (f0080,x)
$1FB5 bmi b1FB7
b1FB7:
$1FB7 .byte $32            ; x-ref: $1fb5; Invalid or partial instruction
$1FB8 dec f92,x
$1FBA .byte $34            ; Invalid or partial instruction
$1FBB .byte $80            ; Invalid or partial instruction
$1FBC and p00,x
$1FBE .byte $32            ; Invalid or partial instruction
$1FBF dec f94,x
$1FC1 .byte $34            ; Invalid or partial instruction
$1FC2 sta (p35),y
$1FC4 cmp (a32,x)
$1FC6 brk
$1FC7 .byte $c3            ; Invalid or partial instruction
$1FC8 .byte $8f            ; Invalid or partial instruction
$1FC9 brk
$1FCA sta (p00,x)
$1FCC .byte $80            ; Invalid or partial instruction
$1FCD bmi b1FCF
b1FCF:
$1FCF bmi b1FD1            ; x-ref: $1fcd
b1FD1:
$1FD1 sta (f0030,x)        ; x-ref: $1fcf
$1FD3 sta (a32),y
$1FD5 sta (p35),y
$1FD7 .byte $80            ; Invalid or partial instruction
$1FD8 .byte $37            ; Invalid or partial instruction
$1FD9 brk
$1FDA .byte $37            ; Invalid or partial instruction
$1FDB dec f92,x
$1FDD and f8FC3,y
$1FE0 brk
$1FE1 cmp (f0080,x)
$1FE3 and f3900,y
$1FE6 brk
$1FE7 sta (f39,x)
$1FE9 sta (a3A),y
$1FEB sta (p3C),y
$1FED .byte $80            ; Invalid or partial instruction
$1FEE and f3500,y
$1FF1 dec f92,x
$1FF3 .byte $37            ; Invalid or partial instruction
$1FF4 cmp (f0081,x)
$1FF6 and fC3,x
$1FF8 .byte $89            ; Invalid or partial instruction
$1FF9 brk
$1FFA .byte $80            ; Invalid or partial instruction
$1FFB rol f92D6,x
$1FFE rti
$1FFF sta (a3E),y
* = $2000
$2001 brk
$2002 .byte $3c            ; Invalid or partial instruction
$2003 dec f91,x
$2005 rol f3C91,x
$2008 .byte $c3            ; Invalid or partial instruction
$2009 stx a007E
$200B dey
$200C brk
$200D .byte $80            ; Invalid or partial instruction
$200E bmi b2010
b2010:
$2010 sta (f39,x)          ; x-ref: $200e
$2012 .byte $c3            ; Invalid or partial instruction
$2013 ror f3A91,x
$2016 brk
$2017 .byte $3c            ; Invalid or partial instruction
$2018 .byte $80            ; Invalid or partial instruction
$2019 .byte $37            ; Invalid or partial instruction
$201A dec a90,x
$201C and f93C1,y
f201F:
$201F and fC3,x            ; x-ref: $16da
$2021 sty a007E
$2023 .byte $8f            ; Invalid or partial instruction
$2024 brk
$2025 txa
$2026 brk
$2027 .byte $7f            ; Invalid or partial instruction
$2028 .byte $d3            ; Invalid or partial instruction
$2029 ldy a4180
$202C .byte $82            ; Invalid or partial instruction
$202D brk
$202E .byte $80            ; Invalid or partial instruction
$202F ror f7E00,x
$2032 .byte $82            ; Invalid or partial instruction
$2033 brk
$2034 .byte $80            ; Invalid or partial instruction
$2035 ror @w f0082,x
$2038 .byte $80            ; Invalid or partial instruction
$2039 ror @w f0082,x
$203C .byte $80            ; Invalid or partial instruction
$203D ror f7E00,x
$2040 brk
$2041 ror @w f0082,x
$2044 .byte $80            ; Invalid or partial instruction
$2045 ror @w f0082,x
$2048 .byte $80            ; Invalid or partial instruction
$2049 ror f7F00,x
$204C .byte $80            ; Invalid or partial instruction
$204D ror @w f0082,x
$2050 .byte $80            ; Invalid or partial instruction
$2051 ror f7E00,x
$2054 .byte $82            ; Invalid or partial instruction
$2055 brk
$2056 .byte $80            ; Invalid or partial instruction
$2057 ror @w f0082,x
$205A .byte $80            ; Invalid or partial instruction
$205B ror @w f0082,x
$205E .byte $80            ; Invalid or partial instruction
$205F ror f7E00,x
$2062 brk
$2063 ror @w f0082,x
$2066 .byte $80            ; Invalid or partial instruction
$2067 ror @w f0082,x
$206A .byte $80            ; Invalid or partial instruction
$206B ror f7F00,x
$206E .byte $ab            ; Invalid or partial instruction
$206F sta (p29,x)
$2071 .byte $c2            ; Invalid or partial instruction
$2072 ror f8329,x
$2075 and p29,x
$2077 sta (p29,x)
$2079 .byte $c2            ; Invalid or partial instruction
$207A .byte $87            ; Invalid or partial instruction
$207B ror fADCB,x
$207E .byte $3a            ; Invalid or partial instruction
$207F .byte $7f            ; Invalid or partial instruction
$2080 .byte $80            ; Invalid or partial instruction
$2081 ror @w f0082,x
$2084 .byte $80            ; Invalid or partial instruction
$2085 ror f7E00,x
$2088 .byte $82            ; Invalid or partial instruction
$2089 brk
$208A .byte $80            ; Invalid or partial instruction
$208B ror @w f0082,x
$208E .byte $80            ; Invalid or partial instruction
$208F ror @w f0088,x
$2092 .byte $d4            ; Invalid or partial instruction
$2093 ldx a3786
$2096 .byte $80            ; Invalid or partial instruction
$2097 brk
$2098 .byte $7f            ; Invalid or partial instruction
$2099 .byte $8f            ; Invalid or partial instruction
$209A brk
$209B .byte $87            ; Invalid or partial instruction
$209C brk
$209D cmp aAF,x
$209F .byte $80            ; Invalid or partial instruction
$20A0 .byte $3c            ; Invalid or partial instruction
$20A1 .byte $3c            ; Invalid or partial instruction
$20A2 .byte $3c            ; Invalid or partial instruction
$20A3 .byte $3c            ; Invalid or partial instruction
$20A4 .byte $3c            ; Invalid or partial instruction
$20A5 .byte $3c            ; Invalid or partial instruction
$20A6 .byte $3c            ; Invalid or partial instruction
$20A7 .byte $3c            ; Invalid or partial instruction
$20A8 .byte $7f            ; Invalid or partial instruction
$20A9 cpy aB1
$20AB sta (f39,x)
$20AD and fC439,y
$20B0 lda #$39
$20B2 cpy aB1
$20B4 .byte $83            ; Invalid or partial instruction
$20B5 and f3980,y
$20B8 brk
$20B9 .byte $83            ; Invalid or partial instruction
$20BA and f81C5,y
$20BD .byte $3a            ; Invalid or partial instruction
$20BE cmp aA9
$20C0 .byte $3a            ; Invalid or partial instruction
$20C1 cpy aB1
$20C3 sta f39
$20C5 cpy aA9
$20C7 sta (f39,x)
$20C9 and fC67F,y
$20CC lda (f0081),y
$20CE and p35,x
$20D0 and fC6,x
$20D2 lda #$35
$20D4 dec aB1
$20D6 .byte $83            ; Invalid or partial instruction
$20D7 and f0080,x
$20D9 and p00,x
$20DB .byte $c7            ; Invalid or partial instruction
$20DC .byte $83            ; Invalid or partial instruction
$20DD .byte $37            ; Invalid or partial instruction
$20DE .byte $80            ; Invalid or partial instruction
$20DF .byte $37            ; Invalid or partial instruction
$20E0 brk
$20E1 .byte $c7            ; Invalid or partial instruction
$20E2 lda #$37
$20E4 brk
$20E5 dec aB1
$20E7 stx p35
$20E9 .byte $80            ; Invalid or partial instruction
$20EA brk
$20EB iny
$20EC .byte $32            ; Invalid or partial instruction
$20ED brk
$20EE cmp #$81
$20F0 .byte $34            ; Invalid or partial instruction
$20F1 .byte $34            ; Invalid or partial instruction
$20F2 .byte $34            ; Invalid or partial instruction
$20F3 cmp #$a9
$20F5 .byte $80            ; Invalid or partial instruction
$20F6 .byte $34            ; Invalid or partial instruction
$20F7 brk
$20F8 cmp #$b1
$20FA .byte $83            ; Invalid or partial instruction
$20FB .byte $34            ; Invalid or partial instruction
$20FC .byte $80            ; Invalid or partial instruction
$20FD .byte $34            ; Invalid or partial instruction
$20FE brk
$20FF dex
$2100 .byte $83            ; Invalid or partial instruction
$2101 and f0081,x
$2103 and fCA,x
$2105 lda #$80
$2107 and p00,x
$2109 cmp #$b1
$210B .byte $83            ; Invalid or partial instruction
$210C .byte $34            ; Invalid or partial instruction
$210D .byte $80            ; Invalid or partial instruction
$210E .byte $34            ; Invalid or partial instruction
$210F brk
$2110 dec a83
$2112 bmi b2144
$2114 cpy f0080
$2116 .byte $32            ; Invalid or partial instruction
$2117 brk
$2118 sta a32
$211A cpy aA9
$211C sta (a32,x)
$211E bne b2152
$2120 .byte $32            ; Invalid or partial instruction
s2121:
$2121 bne b2155            ; x-ref: $1a5d
$2123 bne b2157
$2125 .byte $32            ; Invalid or partial instruction
$2126 bne b215A
$2128 bne b215C
$212A .byte $32            ; Invalid or partial instruction
$212B bne b215F
$212D .byte $7f            ; Invalid or partial instruction
$212E dec aA9
$2130 sta (p35,x)
$2132 dec aB1
$2134 .byte $80            ; Invalid or partial instruction
$2135 and p00,x
$2137 and p00,x
$2139 .byte $83            ; Invalid or partial instruction
$213A and f0080,x
$213C and p00,x
$213E dec aA9
$2140 sta (p35,x)
$2142 dec aB1
b2144:
$2144 .byte $80            ; x-ref: $2112, $217e; Invalid or partial instruction
$2145 and p00,x
$2147 .byte $c7            ; Invalid or partial instruction
$2148 .byte $83            ; Invalid or partial instruction
$2149 .byte $37            ; Invalid or partial instruction
$214A sta (f37,x)
$214C .byte $c7            ; Invalid or partial instruction
$214D lda #$37
$214F dec aB1
$2151 stx p35
$2153 .byte $80            ; Invalid or partial instruction
$2154 brk
b2155:
$2155 cmp #$34             ; x-ref: $2121
b2157:
$2157 brk                  ; x-ref: $2123
$2158 .byte $34            ; Invalid or partial instruction
$2159 brk
b215A:
$215A .byte $83            ; x-ref: $2126; Invalid or partial instruction
$215B .byte $34            ; Invalid or partial instruction
b215C:
$215C sta (p34,x)          ; x-ref: $2128
$215E cmp #$a9
$2160 .byte $34            ; Invalid or partial instruction
$2161 cmp #$b1
$2163 .byte $80            ; Invalid or partial instruction
$2164 .byte $34            ; Invalid or partial instruction
$2165 brk
$2166 dex
$2167 .byte $83            ; Invalid or partial instruction
$2168 and f0081,x
$216A and fCA,x
$216C lda #$35
$216E cmp #$b1
$2170 .byte $83            ; Invalid or partial instruction
$2171 .byte $34            ; Invalid or partial instruction
$2172 .byte $80            ; Invalid or partial instruction
$2173 .byte $34            ; Invalid or partial instruction
$2174 brk
$2175 dec f0081
$2177 bmi b213F
$2179 lda #$30
$217B dec aB1
$217D .byte $83            ; Invalid or partial instruction
$217E bmi b2144
$2180 .byte $80            ; Invalid or partial instruction
$2181 .byte $32            ; Invalid or partial instruction
$2182 brk
$2183 sta a32
$2185 cpy aA9
$2187 sta (a32,x)
$2189 bne b21BD
$218B .byte $32            ; Invalid or partial instruction
$218C bne b21C0
$218E bne b21C2
$2190 .byte $32            ; Invalid or partial instruction
$2191 bne b21C5
$2193 bne b21C7
$2195 .byte $32            ; Invalid or partial instruction
$2196 bne b21CA
$2198 .byte $7f            ; Invalid or partial instruction
$2199 lda (a83,x)
$219B ora (pA6),y
$219D sta (p3C,x)
$219F .byte $a7            ; Invalid or partial instruction
$21A0 eor aA2
$21A2 clc
$21A3 .byte $a7            ; Invalid or partial instruction
$21A4 pha
$21A5 ldy f0080
$21A7 ora (p00),y
$21A9 lda (a83,x)
$21AB ora (f0081),y
$21AD brk
$21AE ldx p3C
$21B0 .byte $a7            ; Invalid or partial instruction
$21B1 .byte $43            ; Invalid or partial instruction
$21B2 ldx #$18
$21B4 .byte $a7            ; Invalid or partial instruction
$21B5 pha
$21B6 ldy a83
$21B8 clc
$21B9 .byte $7f            ; Invalid or partial instruction
$21BA lda (a83,x)
$21BC ora (pA6),y
$21BE sta (p3C,x)
b21C0:
$21C0 .byte $a7            ; x-ref: $218c; Invalid or partial instruction
$21C1 eor (aA2,x)
$21C3 clc
$21C4 .byte $a7            ; Invalid or partial instruction
b21C5:
$21C5 pha                  ; x-ref: $2191
$21C6 ldy f0080
$21C8 ora (p00),y
b21CA:
$21CA lda (a83,x)          ; x-ref: $2196
$21CC ora (f0081),y
$21CE brk
$21CF ldx p3C
$21D1 .byte $a7            ; Invalid or partial instruction
$21D2 .byte $43            ; Invalid or partial instruction
$21D3 ldx #$18
$21D5 .byte $a7            ; Invalid or partial instruction
$21D6 pha
$21D7 ldy a83
$21D9 clc
$21DA .byte $7f            ; Invalid or partial instruction
$21DB lda (a83,x)
$21DD .byte $1c            ; Invalid or partial instruction
$21DE ldx f0081
$21E0 .byte $43            ; Invalid or partial instruction
$21E1 .byte $a7            ; Invalid or partial instruction
$21E2 pha
$21E3 ldx #$18
$21E5 ldy a10
$21E7 .byte $a3            ; Invalid or partial instruction
$21E8 .byte $80            ; Invalid or partial instruction
$21E9 clc
$21EA brk
$21EB lda (a83,x)
$21ED ora (f0080),y
$21EF ora fA600,x
$21F2 sta (p43,x)
$21F4 .byte $a7            ; Invalid or partial instruction
$21F5 eor aA2
$21F7 clc
$21F8 lda (p15,x)
$21FA ldy a1D
$21FC sta (a1B),y
$21FE lda (a83,x)
s2200:
$2200 .byte $1a            ; x-ref: $192d; Invalid or partial instruction
$2201 ldx f0081
$2203 eor (fA1,x)
$2205 ora f83A2,x
$2208 asl a80A4
$220B asl p00,x
$220D lda (f0081,x)
$220F .byte $1b            ; Invalid or partial instruction
$2210 sta (p16),y
$2212 .byte $83            ; Invalid or partial instruction
$2213 .byte $0f            ; Invalid or partial instruction
$2214 ldx f0081
$2216 .byte $43            ; Invalid or partial instruction
$2217 ldx #$18
$2219 lda (a1F,x)
$221B ldy a1B
$221D sta (p1A),y
$221F lda (a83,x)
$2221 ora f81A6,y
$2224 rti
$2225 lda (p15,x)
$2227 ldx #$18
$2229 ldy a10
b222B:
$222B sta f0E,x            ; x-ref: $22a9
$222D sta (p1A,x)
$222F ldx f40
$2231 .byte $a7            ; Invalid or partial instruction
$2232 eor (aA2,x)
$2234 clc
$2235 lda (p15,x)
$2237 .byte $a3            ; Invalid or partial instruction
$2238 bit fA1
$223A .byte $80            ; Invalid or partial instruction
$223B ora p00,x
$223D .byte $83            ; Invalid or partial instruction
$223E .byte $17            ; Invalid or partial instruction
b223F:
$223F ldx f0081            ; x-ref: $22bd
$2241 rol f43A7,x
$2244 ldx #$83
$2246 clc
$2247 ldy f0080
$2249 ora (p00),y
$224B lda (a85,x)
$224D .byte $13            ; Invalid or partial instruction
$224E ldx f0081
$2250 .byte $3b            ; Invalid or partial instruction
$2251 .byte $a7            ; Invalid or partial instruction
$2252 eor (aA2,x)
$2254 clc
$2255 lda (f0080,x)
$2257 ora (p00),y
$2259 ldy f0081
$225B .byte $13            ; Invalid or partial instruction
$225C sta (p15),y
$225E lda (a83,x)
$2260 asl pA6,x
$2262 sta (a3A,x)
$2264 .byte $a7            ; Invalid or partial instruction
$2265 rol f18A2,x
$2268 .byte $a7            ; Invalid or partial instruction
$2269 eor aA4
$226B .byte $80            ; Invalid or partial instruction
$226C ora (p00),y
$226E lda (a85,x)
$2270 asl a
$2271 .byte $a7            ; Invalid or partial instruction
$2272 sta (a3A,x)
$2274 ldx a3E
$2276 ldx #$18
$2278 ldx p43
$227A .byte $a3            ; Invalid or partial instruction
$227B .byte $83            ; Invalid or partial instruction
$227C bit fA1
$227E clc
$227F ldx f0081
$2281 .byte $3c            ; Invalid or partial instruction
$2282 .byte $a7            ; Invalid or partial instruction
$2283 rti
$2284 ldx #$18
$2286 .byte $a7            ; Invalid or partial instruction
$2287 eor aA4
$2289 .byte $80            ; Invalid or partial instruction
$228A .byte $13            ; Invalid or partial instruction
$228B brk
$228C lda (a85,x)
$228E .byte $0c            ; Invalid or partial instruction
$228F ldx f0081
$2291 .byte $37            ; Invalid or partial instruction
$2292 .byte $a7            ; Invalid or partial instruction
$2293 .byte $3c            ; Invalid or partial instruction
$2294 ldx #$18
$2296 lda (f0089,x)
$2298 .byte $0c            ; Invalid or partial instruction
$2299 .byte $83            ; Invalid or partial instruction
$229A brk
$229B cmp aAF,x
$229D .byte $80            ; Invalid or partial instruction
$229E .byte $3c            ; Invalid or partial instruction
$229F .byte $3c            ; Invalid or partial instruction
$22A0 .byte $3c            ; Invalid or partial instruction
b22A1:
$22A1 .byte $3c            ; x-ref: $231c; Invalid or partial instruction
$22A2 .byte $3c            ; Invalid or partial instruction
$22A3 .byte $3c            ; Invalid or partial instruction
$22A4 .byte $3c            ; Invalid or partial instruction
$22A5 .byte $3c            ; Invalid or partial instruction
$22A6 .byte $7f            ; Invalid or partial instruction
$22A7 .byte $83            ; Invalid or partial instruction
$22A8 brk
$22A9 bcs b222B
$22AB .byte $3c            ; Invalid or partial instruction
$22AC brk
$22AD .byte $3c            ; Invalid or partial instruction
$22AE brk
$22AF sta (p3C,x)
$22B1 sta (a3E),y
$22B3 sta (f41),y
$22B5 .byte $80            ; Invalid or partial instruction
$22B6 .byte $43            ; Invalid or partial instruction
$22B7 brk
$22B8 .byte $7f            ; Invalid or partial instruction
$22B9 .byte $8f            ; Invalid or partial instruction
$22BA brk
$22BB .byte $83            ; Invalid or partial instruction
$22BC brk
$22BD bcs b223F
$22BF .byte $3c            ; Invalid or partial instruction
$22C0 brk
$22C1 .byte $3c            ; Invalid or partial instruction
$22C2 brk
$22C3 sta (p3C,x)
$22C5 sta (a3D),y
$22C7 sta (f41),y
$22C9 .byte $80            ; Invalid or partial instruction
$22CA pha
$22CB brk
$22CC .byte $7f            ; Invalid or partial instruction
$22CD .byte $cb            ; Invalid or partial instruction
$22CE lda #$81
$22D0 and #$cb
$22D2 ldy #$80
$22D4 and #$00
$22D6 .byte $83            ; Invalid or partial instruction
$22D7 and #$80
$22D9 and #$00
$22DB .byte $cb            ; Invalid or partial instruction
$22DC lda #$81
$22DE and #$cb
$22E0 ldy #$83
$22E2 and #$80
$22E4 and #$00
$22E6 .byte $cb            ; Invalid or partial instruction
$22E7 lda #$81
$22E9 and #$c8
$22EB ldy #$80
$22ED .byte $2b            ; Invalid or partial instruction
$22EE brk
$22EF cmp a2D85
$22F2 cmp a81A9
$22F5 and aCB2D
$22F8 ldy #$80
$22FA .byte $2b            ; Invalid or partial instruction
$22FB brk
$22FC .byte $2b            ; Invalid or partial instruction
$22FD brk
$22FE .byte $83            ; Invalid or partial instruction
$22FF .byte $2b            ; Invalid or partial instruction
$2300 .byte $80            ; Invalid or partial instruction
$2301 .byte $2b            ; Invalid or partial instruction
$2302 brk
$2303 .byte $cb            ; Invalid or partial instruction
$2304 lda #$2b
$2306 brk
$2307 .byte $cb            ; Invalid or partial instruction
$2308 ldy #$2b
$230A brk
$230B .byte $83            ; Invalid or partial instruction
$230C .byte $2b            ; Invalid or partial instruction
a230D:
$230D iny                  ; x-ref: $1ac7
$230E sta (p2D,x)
$2310 iny
$2311 lda #$2d
$2313 dec a2EA0
$2316 dec a2EA9
$2319 .byte $d7            ; Invalid or partial instruction
$231A ldy #$89
$231C bmi b22A1
$231E brk
$231F sta (f0030,x)
$2321 brk
$2322 bmi b2324
b2324:
$2324 .byte $7f            ; x-ref: $2322; Invalid or partial instruction
$2325 cpy aA0
$2327 .byte $80            ; Invalid or partial instruction
$2328 .byte $34            ; Invalid or partial instruction
$2329 .byte $82            ; Invalid or partial instruction
$232A brk
$232B cpy aA9
$232D sta (p34,x)
$232F cpy aA0
$2331 .byte $80            ; Invalid or partial instruction
$2332 .byte $34            ; Invalid or partial instruction
$2333 .byte $82            ; Invalid or partial instruction
$2334 brk
$2335 cpy aA9
$2337 sta (p34,x)
$2339 cpy aA0
$233B .byte $80            ; Invalid or partial instruction
$233C .byte $34            ; Invalid or partial instruction
$233D .byte $82            ; Invalid or partial instruction
$233E brk
$233F cpy aA9
$2341 sta (p34,x)
$2343 cpy aA0
$2345 .byte $80            ; Invalid or partial instruction
$2346 .byte $34            ; Invalid or partial instruction
$2347 .byte $82            ; Invalid or partial instruction
$2348 brk
$2349 cpy aA9
$234B .byte $80            ; Invalid or partial instruction
$234C .byte $34            ; Invalid or partial instruction
$234D brk
$234E cpy aA0
$2350 .byte $34            ; Invalid or partial instruction
$2351 .byte $82            ; Invalid or partial instruction
$2352 brk
$2353 cpy aA9
$2355 .byte $80            ; Invalid or partial instruction
$2356 .byte $34            ; Invalid or partial instruction
$2357 brk
$2358 .byte $34            ; Invalid or partial instruction
$2359 brk
$235A cld
$235B ldy #$35
$235D .byte $82            ; Invalid or partial instruction
$235E brk
$235F cld
$2360 lda #$81
$2362 and fD8,x
$2364 ldy #$80
$2366 and f0082,x
$2368 brk
$2369 cld
$236A lda #$81
$236C and fD8,x
$236E ldy #$80
$2370 and f0082,x
$2372 brk
$2373 cld
$2374 lda #$81
$2376 and fD8,x
$2378 ldy #$80
$237A and f0082,x
$237C brk
$237D cld
$237E lda #$81
$2380 and fD8,x
$2382 ldy #$80
$2384 and f0082,x
$2386 brk
$2387 sta (p35,x)
$2389 cld
$238A lda #$35
$238C cmp a80A0,y
$238F .byte $32            ; Invalid or partial instruction
$2390 .byte $82            ; Invalid or partial instruction
$2391 brk
$2392 cmp a81A9,y
$2395 .byte $32            ; Invalid or partial instruction
$2396 cmp a80A0,y
$2399 .byte $32            ; Invalid or partial instruction
$239A .byte $82            ; Invalid or partial instruction
$239B brk
$239C cmp a81A9,y
$239F .byte $32            ; Invalid or partial instruction
$23A0 cmp a80A0,y
$23A3 .byte $32            ; Invalid or partial instruction
$23A4 .byte $82            ; Invalid or partial instruction
$23A5 brk
$23A6 cmp a81A9,y
$23A9 .byte $32            ; Invalid or partial instruction
$23AA cmp a80A0,y
$23AD .byte $32            ; Invalid or partial instruction
$23AE .byte $82            ; Invalid or partial instruction
$23AF brk
$23B0 cmp a81A9,y
$23B3 .byte $32            ; Invalid or partial instruction
$23B4 cmp a80A0,y
$23B7 .byte $32            ; Invalid or partial instruction
$23B8 .byte $82            ; Invalid or partial instruction
$23B9 brk
$23BA cmp a81A9,y
$23BD .byte $32            ; Invalid or partial instruction
$23BE .byte $32            ; Invalid or partial instruction
$23BF cld
$23C0 ldy #$80
$23C2 .byte $32            ; Invalid or partial instruction
$23C3 .byte $82            ; Invalid or partial instruction
$23C4 brk
$23C5 cld
$23C6 lda #$81
$23C8 .byte $32            ; Invalid or partial instruction
$23C9 cld
$23CA ldy #$80
$23CC .byte $32            ; Invalid or partial instruction
$23CD .byte $82            ; Invalid or partial instruction
$23CE brk
$23CF cld
$23D0 lda #$81
$23D2 .byte $32            ; Invalid or partial instruction
$23D3 cld
$23D4 ldy #$80
$23D6 .byte $32            ; Invalid or partial instruction
$23D7 .byte $82            ; Invalid or partial instruction
$23D8 brk
$23D9 cld
$23DA lda #$81
$23DC .byte $32            ; Invalid or partial instruction
$23DD cld
$23DE ldy #$80
$23E0 .byte $32            ; Invalid or partial instruction
$23E1 .byte $82            ; Invalid or partial instruction
$23E2 brk
$23E3 cld
$23E4 lda #$81
$23E6 .byte $32            ; Invalid or partial instruction
$23E7 cld
$23E8 ldy #$80
$23EA .byte $32            ; Invalid or partial instruction
$23EB .byte $82            ; Invalid or partial instruction
$23EC brk
$23ED sta (p35,x)
$23EF cld
$23F0 lda #$35
$23F2 .byte $7f            ; Invalid or partial instruction
$23F3 lda (a83,x)
$23F5 clc
$23F6 ldx f0081
$23F8 .byte $43            ; Invalid or partial instruction
$23F9 .byte $a7            ; Invalid or partial instruction
$23FA pha
$23FB ldx #$83
$23FD clc
$23FE ldy f0080
$2400 clc
$2401 brk
$2402 lda (a83,x)
$2404 ora (f0080),y
$2406 ora fA600,x
$2409 sta (p43,x)
$240B .byte $a7            ; Invalid or partial instruction
$240C eor aA2
$240E clc
$240F lda (p15,x)
$2411 ldy a18
$2413 sta (f17),y
$2415 lda (a83,x)
$2417 asl pA6,x
$2419 sta (f41,x)
$241B .byte $a7            ; Invalid or partial instruction
$241C lsr aA2
$241E .byte $83            ; Invalid or partial instruction
$241F clc
$2420 ldy f0080
$2422 asl p00,x
$2424 lda (f0081,x)
$2426 .byte $1b            ; Invalid or partial instruction
$2427 sta (p16),y
$2429 .byte $0f            ; Invalid or partial instruction
$242A .byte $a7            ; Invalid or partial instruction
$242B eor (pA6,x)
$242D .byte $43            ; Invalid or partial instruction
$242E ldx #$18
$2430 lda (a1F,x)
$2432 ldy a1B
$2434 sta (p1A),y
$2436 lda (a83,x)
$2438 ora f81A6,y
$243B rti
$243C lda (p15,x)
$243E ldx #$18
$2440 ldy a10
$2442 sta f0E,x
$2444 sta (p1A,x)
$2446 ldx f40
$2448 .byte $a7            ; Invalid or partial instruction
$2449 eor (aA2,x)
$244B clc
$244C lda (p15,x)
$244E .byte $a3            ; Invalid or partial instruction
$244F bit fA1
$2451 .byte $80            ; Invalid or partial instruction
$2452 ora p00,x
$2454 .byte $83            ; Invalid or partial instruction
$2455 .byte $17            ; Invalid or partial instruction
$2456 ldx f0081
$2458 rol f43A7,x
$245B ldx #$83
$245D clc
$245E ldy f0080
$2460 ora (p00),y
$2462 lda (a85,x)
$2464 .byte $13            ; Invalid or partial instruction
$2465 ldx f0081
$2467 .byte $3b            ; Invalid or partial instruction
$2468 .byte $a7            ; Invalid or partial instruction
$2469 eor (aA2,x)
$246B clc
$246C lda (f0080,x)
$246E ora (p00),y
$2470 ldy f0081
$2472 .byte $13            ; Invalid or partial instruction
$2473 sta (p15),y
$2475 lda (a83,x)
$2477 asl pA6,x
$2479 sta (a3A,x)
$247B .byte $a7            ; Invalid or partial instruction
$247C rol f18A2,x
$247F .byte $a7            ; Invalid or partial instruction
f2480:
$2480 eor aA4              ; x-ref: $25f8
$2482 .byte $80            ; Invalid or partial instruction
$2483 ora (p00),y
$2485 lda (a85,x)
$2487 asl a
$2488 .byte $a7            ; Invalid or partial instruction
$2489 sta (a3A,x)
$248B ldx a3E
$248D ldx #$18
$248F ldx p43
b2491:
$2491 .byte $a3            ; x-ref: $24cf; Invalid or partial instruction
$2492 .byte $83            ; Invalid or partial instruction
$2493 bit fA1
$2495 clc
$2496 ldx f0081
$2498 .byte $3c            ; Invalid or partial instruction
$2499 .byte $a7            ; Invalid or partial instruction
$249A rti
$249B ldx #$18
$249D .byte $a7            ; Invalid or partial instruction
$249E eor aA4
$24A0 .byte $80            ; Invalid or partial instruction
$24A1 .byte $13            ; Invalid or partial instruction
$24A2 brk
$24A3 lda (a85,x)
$24A5 .byte $0c            ; Invalid or partial instruction
$24A6 ldx f0081
$24A8 .byte $37            ; Invalid or partial instruction
b24A9:
$24A9 .byte $a7            ; x-ref: $2524; Invalid or partial instruction
$24AA .byte $3c            ; Invalid or partial instruction
$24AB ldx #$18
$24AD lda (a85,x)
$24AF .byte $0c            ; Invalid or partial instruction
$24B0 .byte $7f            ; Invalid or partial instruction
$24B1 .byte $c3            ; Invalid or partial instruction
$24B2 sty a007E
$24B4 .byte $82            ; Invalid or partial instruction
$24B5 brk
$24B6 tay
$24B7 .byte $80            ; Invalid or partial instruction
$24B8 and f92C0,y
$24BB .byte $3a            ; Invalid or partial instruction
$24BC .byte $93            ; Invalid or partial instruction
$24BD and f7EC3,y
$24C0 brk
$24C1 .byte $80            ; Invalid or partial instruction
$24C2 and fC0,x
$24C4 .byte $92            ; Invalid or partial instruction
$24C5 .byte $37            ; Invalid or partial instruction
$24C6 .byte $93            ; Invalid or partial instruction
$24C7 and fC3,x
$24C9 sta (a007E,x)
$24CB .byte $33            ; Invalid or partial instruction
$24CC .byte $32            ; Invalid or partial instruction
$24CD brk
$24CE .byte $80            ; Invalid or partial instruction
$24CF bmi b2491
$24D1 bcc b2505
$24D3 cmp (f0081,x)
$24D5 and f93,x
$24D7 rol a84C3
$24DA ror @w f0080,x
$24DD sta (a26,x)
$24DF cpy #$91
$24E1 .byte $27            ; Invalid or partial instruction
$24E2 cmp (p2B,x)
$24E4 sta (p2E),y
$24E6 sta (a32),y
$24E8 .byte $93            ; Invalid or partial instruction
$24E9 and (fC0),y
$24EB sta (a32),y
$24ED cmp (f0080,x)
$24EF .byte $34            ; Invalid or partial instruction
$24F0 .byte $82            ; Invalid or partial instruction
$24F1 brk
$24F2 sta (f39,x)
$24F4 .byte $80            ; Invalid or partial instruction
$24F5 .byte $34            ; Invalid or partial instruction
$24F6 .byte $92            ; Invalid or partial instruction
$24F7 and f0081,x
$24F9 .byte $34            ; Invalid or partial instruction
$24FA .byte $32            ; Invalid or partial instruction
$24FB brk
$24FC .byte $80            ; Invalid or partial instruction
$24FD and a3700
$2500 cpy #$90
$2502 and f91C1,y
b2505:
$2505 .byte $3c            ; x-ref: $24d1; Invalid or partial instruction
$2506 .byte $80            ; Invalid or partial instruction
$2507 and f92C0,y
$250A .byte $3b            ; Invalid or partial instruction
$250B bcc b2547
$250D cmp (a90,x)
$250F and f3791,y
$2512 .byte $c3            ; Invalid or partial instruction
$2513 .byte $83            ; Invalid or partial instruction
$2514 ror @w a85,x
$2517 tay
$2518 .byte $80            ; Invalid or partial instruction
$2519 .byte $32            ; Invalid or partial instruction
$251A brk
$251B .byte $34            ; Invalid or partial instruction
$251C cpy #$92
$251E and f91,x
$2520 .byte $34            ; Invalid or partial instruction
$2521 cmp (a32,x)
$2523 brk
$2524 bmi b24A9
$2526 .byte $32            ; Invalid or partial instruction
$2527 .byte $c3            ; Invalid or partial instruction
$2528 .byte $87            ; Invalid or partial instruction
$2529 ror @w a83,x
$252C .byte $80            ; Invalid or partial instruction
$252D .byte $32            ; Invalid or partial instruction
$252E brk
$252F .byte $34            ; Invalid or partial instruction
$2530 brk
$2531 .byte $34            ; Invalid or partial instruction
$2532 cpy #$92
$2534 and f91,x
$2536 .byte $34            ; Invalid or partial instruction
$2537 cmp (f0080,x)
$2539 .byte $32            ; Invalid or partial instruction
$253A .byte $82            ; Invalid or partial instruction
$253B brk
$253C sta (f0030,x)
$253E .byte $80            ; Invalid or partial instruction
$253F bmi b2501
$2541 .byte $92            ; Invalid or partial instruction
$2542 .byte $32            ; Invalid or partial instruction
$2543 .byte $c3            ; Invalid or partial instruction
$2544 .byte $87            ; Invalid or partial instruction
$2545 ror @w f0081,x
$2548 .byte $80            ; Invalid or partial instruction
$2549 and a3200
$254C brk
$254D .byte $34            ; Invalid or partial instruction
$254E brk
$254F .byte $34            ; Invalid or partial instruction
$2550 cpy #$92
$2552 and f0081,x
$2554 .byte $34            ; Invalid or partial instruction
$2555 cmp (f0080,x)
$2557 .byte $32            ; Invalid or partial instruction
$2558 .byte $82            ; Invalid or partial instruction
$2559 brk
$255A .byte $80            ; Invalid or partial instruction
$255B bmi b255D
b255D:
$255D bmi b251F            ; x-ref: $255b
$255F .byte $92            ; Invalid or partial instruction
$2560 .byte $32            ; Invalid or partial instruction
$2561 .byte $7f            ; Invalid or partial instruction
$2562 .byte $cb            ; Invalid or partial instruction
$2563 lda #$81
$2565 and #$cb
$2567 ldy #$80
$2569 and #$00
$256B .byte $83            ; Invalid or partial instruction
$256C and #$80
$256E and #$00
$2570 .byte $cb            ; Invalid or partial instruction
$2571 lda #$81
$2573 and #$cb
$2575 ldy #$83
$2577 and #$80
$2579 and #$00
$257B .byte $cb            ; Invalid or partial instruction
$257C lda #$81
$257E and #$c8
$2580 ldy #$80
$2582 .byte $2b            ; Invalid or partial instruction
$2583 brk
$2584 cmp a2D85
$2587 cmp a81A9
$258A and aCB2D
$258D ldy #$80
$258F .byte $2b            ; Invalid or partial instruction
$2590 brk
$2591 .byte $2b            ; Invalid or partial instruction
$2592 brk
$2593 .byte $83            ; Invalid or partial instruction
$2594 .byte $2b            ; Invalid or partial instruction
$2595 .byte $80            ; Invalid or partial instruction
$2596 .byte $2b            ; Invalid or partial instruction
$2597 brk
$2598 .byte $cb            ; Invalid or partial instruction
$2599 lda #$2b
$259B brk
$259C .byte $cb            ; Invalid or partial instruction
$259D ldy #$2b
$259F brk
$25A0 .byte $83            ; Invalid or partial instruction
$25A1 .byte $2b            ; Invalid or partial instruction
$25A2 iny
$25A3 sta (p2D,x)
$25A5 iny
b25A6:
$25A6 lda #$2d             ; x-ref: $25c5
$25A8 .byte $cb            ; Invalid or partial instruction
$25A9 ldy #$89
$25AB .byte $2b            ; Invalid or partial instruction
$25AC .byte $7f            ; Invalid or partial instruction
$25AD .byte $da            ; Invalid or partial instruction
$25AE ldy #$8f
$25B0 and #$83
$25B2 ror @w f008F,x
$25B5 brk
$25B6 .byte $8b            ; Invalid or partial instruction
$25B7 brk
$25B8 .byte $7f            ; Invalid or partial instruction
$25B9 lda (f008F,x)
$25BB asl @w a007E
$25BE brk
$25BF .byte $7f            ; Invalid or partial instruction
$25C0 .byte $c3            ; Invalid or partial instruction
$25C1 .byte $89            ; Invalid or partial instruction
$25C2 ror f90E0,x
$25C5 bmi b25A6
$25C7 bcc b25F6
$25C9 bcc b25F7
$25CB bcc b25F8
f25CD:
$25CD bcc b25F8            ; x-ref: $1a3c
$25CF bcc b25F7
$25D1 bcc b25F7
$25D3 bcc b25F6
$25D5 bcc b25F7
$25D7 bcc b25F8
$25D9 bcc b25F8
$25DB .byte $9f            ; Invalid or partial instruction
$25DC .byte $1a            ; Invalid or partial instruction
$25DD ror f7E8A,x
$25E0 .byte $7f            ; Invalid or partial instruction
$25E1 .byte $8f            ; Invalid or partial instruction
$25E2 brk
$25E3 brk
$25E4 brk
$25E5 brk
$25E6 brk
$25E7 brk
$25E8 brk
b25E9:
$25E9 .byte $87            ; x-ref: $2657; Invalid or partial instruction
$25EA brk
$25EB .byte $b2            ; Invalid or partial instruction
$25EC sta a22
$25EE .byte $db            ; Invalid or partial instruction
$25EF sta fC324,x
$25F2 .byte $8b            ; Invalid or partial instruction
$25F3 ror @w a83,x
b25F6:
$25F6 sta (p21,x)          ; x-ref: $25c7, $25d3
b25F8:
$25F8 ora f2480,x          ; x-ref: $25cb, $25cd, $25d7, $25d9
$25FB cmp f269A,x
$25FE .byte $93            ; Invalid or partial instruction
$25FF and #$c3
$2601 .byte $87            ; Invalid or partial instruction
$2602 ror f97DD,x
$2605 and a2B97
$2608 .byte $c3            ; Invalid or partial instruction
$2609 ror @w a85,x
$260C .byte $80            ; Invalid or partial instruction
$260D rol p00
$260F sta (p29,x)
$2611 sta (p2B),y
$2613 sta (f0030),y
$2615 .byte $80            ; Invalid or partial instruction
$2616 and #$dd
$2618 .byte $92            ; Invalid or partial instruction
$2619 .byte $2b            ; Invalid or partial instruction
$261A sta p29,x
$261C .byte $c3            ; Invalid or partial instruction
$261D .byte $89            ; Invalid or partial instruction
$261E ror @w a83,x
$2621 .byte $80            ; Invalid or partial instruction
$2622 rol p00
$2624 sta (p29,x)
$2626 sta (p2B),y
$2628 sta (p35),y
$262A .byte $b2            ; Invalid or partial instruction
$262B .byte $80            ; Invalid or partial instruction
$262C .byte $32            ; Invalid or partial instruction
$262D cmp f3490,x
$2630 .byte $7f            ; Invalid or partial instruction
$2631 sta (a007E,x)
$2633 cpy #$95
$2635 bmi b25FA
$2637 .byte $87            ; Invalid or partial instruction
$2638 ror f3580,x
$263B cpy #$92
$263D .byte $37            ; Invalid or partial instruction
$263E .byte $97            ; Invalid or partial instruction
$263F .byte $34            ; Invalid or partial instruction
$2640 cmp (f0080,x)
$2642 and f90DC,y
$2645 .byte $3b            ; Invalid or partial instruction
$2646 cmp (f91,x)
$2648 .byte $3c            ; Invalid or partial instruction
$2649 cmp (f91,x)
$264B and f3780,y
$264E brk
$264F .byte $32            ; Invalid or partial instruction
$2650 cpy #$90
$2652 .byte $34            ; Invalid or partial instruction
$2653 sta (a32),y
$2655 cmp (f91,x)
$2657 bmi b25E9
$2659 and a2B90
$265C .byte $c3            ; Invalid or partial instruction
$265D .byte $97            ; Invalid or partial instruction
$265E and #$81
$2660 brk
$2661 rol a2D91
$2664 sta (f0030),y
$2666 .byte $b2            ; Invalid or partial instruction
$2667 and #$c0
$2669 sta p2B,x
$266B cmp (f0080,x)
$266D and @w a0084
$2670 .byte $80            ; Invalid or partial instruction
$2671 and #$c0
$2673 bcc b26A0
$2675 .byte $c3            ; Invalid or partial instruction
$2676 .byte $83            ; Invalid or partial instruction
$2677 ror a2D80,x
$267A .byte $82            ; Invalid or partial instruction
$267B brk
$267C .byte $80            ; Invalid or partial instruction
$267D bit aDE
$267F brk
$2680 sta (p2B,x)
$2682 .byte $c2            ; Invalid or partial instruction
$2683 .byte $83            ; Invalid or partial instruction
$2684 ror a2D80,x
$2687 .byte $82            ; Invalid or partial instruction
$2688 brk
$2689 .byte $80            ; Invalid or partial instruction
$268A .byte $22            ; Invalid or partial instruction
$268B dec a8100,x
$268E .byte $2b            ; Invalid or partial instruction
$268F bcc b26BD
$2691 bcc b26BE
$2693 sta (p29),y
$2695 .byte $80            ; Invalid or partial instruction
$2696 and a3000
$2699 dec f1D00,x
$269C dec a8100,x
$269F .byte $2b            ; Invalid or partial instruction
b26A0:
$26A0 .byte $c3            ; x-ref: $2673; Invalid or partial instruction
$26A1 .byte $83            ; Invalid or partial instruction
$26A2 ror f3080,x
$26A5 brk
$26A6 .byte $32            ; Invalid or partial instruction
$26A7 dec f2600,x
$26AA dec f8500,x
$26AD and aA17F
$26B0 .byte $83            ; Invalid or partial instruction
$26B1 ora (pA6),y
$26B3 sta (p3C,x)
$26B5 .byte $a7            ; Invalid or partial instruction
$26B6 eor aB3
$26B8 clc
$26B9 .byte $a7            ; Invalid or partial instruction
$26BA pha
$26BB ldy f0080
b26BD:
$26BD ora (p00),y          ; x-ref: $268f
$26BF lda (a83,x)
$26C1 ora (f0081),y
$26C3 brk
$26C4 ldx p3C
$26C6 .byte $a7            ; Invalid or partial instruction
$26C7 .byte $43            ; Invalid or partial instruction
$26C8 .byte $b3            ; Invalid or partial instruction
$26C9 clc
$26CA .byte $a7            ; Invalid or partial instruction
$26CB pha
$26CC ldy a83
$26CE ora fA1,x
$26D0 .byte $1a            ; Invalid or partial instruction
$26D1 ldx f0081
$26D3 and f41A7,y
$26D6 .byte $b3            ; Invalid or partial instruction
$26D7 clc
$26D8 .byte $a7            ; Invalid or partial instruction
$26D9 pha
$26DA ldy f0080
$26DC .byte $1a            ; Invalid or partial instruction
$26DD brk
$26DE lda (a83,x)
$26E0 .byte $1a            ; Invalid or partial instruction
$26E1 sta (p00,x)
$26E3 ldx f39
$26E5 .byte $a7            ; Invalid or partial instruction
$26E6 rol f18B3,x
$26E9 .byte $a7            ; Invalid or partial instruction
$26EA pha
$26EB ldy a1F
$26ED bcc b2702
$26EF brk
$26F0 lda (a83,x)
$26F2 ora pA6,x
$26F4 sta (p3C,x)
$26F6 .byte $a7            ; Invalid or partial instruction
$26F7 rti
$26F8 .byte $b3            ; Invalid or partial instruction
$26F9 clc
$26FA .byte $a7            ; Invalid or partial instruction
$26FB pha
$26FC ldy f0080
$26FE ora p00,x
$2700 lda (a83,x)
b2702:
$2702 ora f0081,x          ; x-ref: $26ed
$2704 brk
$2705 ldx p34
$2707 .byte $a7            ; Invalid or partial instruction
$2708 .byte $3c            ; Invalid or partial instruction
$2709 .byte $b3            ; Invalid or partial instruction
$270A clc
$270B .byte $a7            ; Invalid or partial instruction
$270C eor aA3
$270E bit fA1
$2710 ora a83,x
$2712 asl pA6,x
$2714 sta (a3A,x)
f2716:
$2716 .byte $a7            ; x-ref: $1700; Invalid or partial instruction
$2717 eor (aB3,x)
$2719 clc
$271A .byte $a7            ; Invalid or partial instruction
$271B lsr a
$271C ldy p16
$271E lda (a83,x)
$2720 asl a
$2721 sta (p00,x)
$2723 ldx p35
$2725 .byte $a7            ; Invalid or partial instruction
$2726 rol f18B3,x
$2729 .byte $a7            ; Invalid or partial instruction
$272A lsr aA4
$272C clc
$272D sta (p1A),y
$272F .byte $7f            ; Invalid or partial instruction
$2730 .byte $80            ; Invalid or partial instruction
$2731 .byte $34            ; Invalid or partial instruction
$2732 brk
$2733 and aDE,x
$2735 brk
$2736 and #$de
$2738 brk
$2739 sta (f0030,x)
$273B .byte $c2            ; Invalid or partial instruction
$273C .byte $83            ; Invalid or partial instruction
b273D:
$273D ror f3780,x          ; x-ref: $27a8
$2740 bcc b277B
$2742 .byte $3c            ; Invalid or partial instruction
$2743 dec f2D00,x
$2746 dec a8100,x
$2749 .byte $34            ; Invalid or partial instruction
$274A .byte $c2            ; Invalid or partial instruction
$274B .byte $83            ; Invalid or partial instruction
$274C ror f3E80,x
$274F brk
$2750 and @w aDE,y
$2753 .byte $43            ; Invalid or partial instruction
$2754 dec fB200,x
$2757 .byte $3b            ; Invalid or partial instruction
$2758 .byte $dc            ; Invalid or partial instruction
$2759 sta (p3C),y
$275B .byte $c3            ; Invalid or partial instruction
$275C .byte $82            ; Invalid or partial instruction
$275D ror f3A81,x
$2760 cpy #$91
$2762 and f91C1,y
$2765 .byte $37            ; Invalid or partial instruction
$2766 .byte $dc            ; Invalid or partial instruction
$2767 sta (p35),y
$2769 sta (f37),y
$276B cmp (f39,x)
$276D .byte $80            ; Invalid or partial instruction
$276E and f90C0,y
$2771 .byte $3a            ; Invalid or partial instruction
$2772 sta (f39),y
$2774 cmp (f91,x)
$2776 .byte $32            ; Invalid or partial instruction
$2777 sta (f39),y
$2779 sta (p35),y
b277B:
$277B sta (p2E),y          ; x-ref: $2740
$277D sta (f37),y
$277F .byte $80            ; Invalid or partial instruction
$2780 .byte $32            ; Invalid or partial instruction
$2781 cpy #$92
$2783 .byte $34            ; Invalid or partial instruction
$2784 .byte $c3            ; Invalid or partial instruction
$2785 sta (a007E,x)
$2787 bcc e27BC
$2789 bcc e27BD
$278B sta (f0030),y
$278D .byte $c3            ; Invalid or partial instruction
$278E .byte $83            ; Invalid or partial instruction
$278F ror f8000,x
$2792 .byte $32            ; Invalid or partial instruction
$2793 cpy #$90
$2795 .byte $34            ; Invalid or partial instruction
$2796 sta (a32),y
$2798 cmp (f0030,x)
$279A .byte $80            ; Invalid or partial instruction
$279B .byte $37            ; Invalid or partial instruction
$279C brk
$279D .byte $34            ; Invalid or partial instruction
$279E cpy #$90
$27A0 and f91,x
$27A2 .byte $34            ; Invalid or partial instruction
$27A3 cpy #$95
$27A5 .byte $32            ; Invalid or partial instruction
$27A6 cpy #$91
$27A8 bmi b273D
$27AA .byte $32            ; Invalid or partial instruction
$27AB .byte $c3            ; Invalid or partial instruction
$27AC .byte $87            ; Invalid or partial instruction
$27AD ror @w a85,x
$27B0 tay
$27B1 .byte $80            ; Invalid or partial instruction
$27B2 rol a3000
$27B5 cpy #$92
$27B7 .byte $32            ; Invalid or partial instruction
$27B8 .byte $93            ; Invalid or partial instruction
$27B9 bmi e283A
