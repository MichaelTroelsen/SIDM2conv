# Complete Disassembly: Stinsen 89 SF2 packed

**Author:** MIT

**Disassembled:** 2025-12-03

---

## Table of Contents

1. [File Information](#file-information)
2. [Memory Map](#memory-map)
3. [Complete Disassembly](#complete-disassembly)
4. [Data Tables](#data-tables)
5. [Music Data](#music-data)

---

## File Information

- **Format:** PSID v2
- **Load Address:** $1000
- **Init Address:** $1000
- **Play Address:** $1006
- **Songs:** 1
- **Start Song:** 1
- **Data Size:** 6,075 bytes
- **End Address:** $27BA
- **Memory Range:** $1000-$27BA

## Memory Map

| Address Range | Size | Description |
|--------------|------|-------------|
| $1000-$1048 |   49 | Jump table and player header |
| $1049-$1900 | 2232 | Player code (init + play routines) |
| $1914-$1954 |   64 | Wave table (note offsets + waveforms) |
| $1A1E-$1A4E |   48 | Filter table (16 entries × 3 bytes) |
| $1A3B-$1A7B |   64 | Pulse table (16 entries × 4 bytes) |
| $1A6B-$1AAB |   64 | Instrument table (8 instruments × 8 bytes) |
| $1A8B-$1ACB |   64 | Arpeggio table (16 entries × 4 bytes) |
| $1ADB-$1B9B |  192 | Command table (64 commands × 3 bytes) |
| $1C00-$27BA | 3003 | Music data (patterns, sequences, orders) |

## Complete Disassembly

Full 6502/6510 assembly disassembly of the player code and music data.

```asm
; Stinsen 89 SF2 packed
; MIT
; 
;
; Load: $1000
; Init: $1000
; Play: $1006

$1000  00            BRK                  
$1001  10 4C         BPL    $104f         
$1003  92            DCB    $92           ; Unknown opcode
$1004  16 4C         ASL    $4c,X         
$1006  9B            DCB    $9b           ; Unknown opcode
$1007  16 A9         ASL    $a9,X         
$1009  00            BRK                  
$100A  2C 81 17      BIT    $1781         
$100D  30 44         BMI    $1053         
$100F  70 38         BVS    $1049         
$1011  A2 75         LDX    #$75          
$1013  9D 82 17      STA    $1782,X       
$1016  CA            DEX                  
$1017  D0 FA         BNE    $1013         
$1019  AE 82 17      LDX    $1782         
$101C  BD FB 17      LDA    $17fb,X       
$101F  8D 80 17      STA    $1780         
$1022  8D 84 17      STA    $1784         
$1025  BD FC 17      LDA    $17fc,X       
$1028  29 0F         AND    #$0f          
$102A  8D 85 17      STA    $1785         
$102D  BD FC 17      LDA    $17fc,X       
$1030  29 70         AND    #$70          
$1032  8D 86 17      STA    $1786         
$1035  A9 02         LDA    #$02          
$1037  8D 83 17      STA    $1783         
$103A  8D F8 17      STA    $17f8         
$103D  8D F9 17      STA    $17f9         
$1040  8D FA 17      STA    $17fa         
$1043  A9 80         LDA    #$80          
$1045  8D 81 17      STA    $1781         
$1048  60            RTS                  
$1049  8D 04 D4      STA    $d404         
$104C  8D 0B D4      STA    $d40b         
$104F  8D 12 D4      STA    $d412         
$1052  60            RTS                  
$1053  CE 83 17      DEC    $1783         
$1056  10 17         BPL    $106f         
$1058  AE 84 17      LDX    $1784         
$105B  BD 19 1A      LDA    $1a19,X       
$105E  8D 83 17      STA    $1783         
$1061  E8            INX                  
$1062  BD 19 1A      LDA    $1a19,X       
$1065  C9 7F         CMP    #$7f          
$1067  D0 03         BNE    $106c         
$1069  AE 80 17      LDX    $1780         
$106C  8E 84 17      STX    $1784         
$106F  A2 02         LDX    #$02          
$1071  BD F8 17      LDA    $17f8,X       
$1074  C9 01         CMP    #$01          
$1076  D0 39         BNE    $10b1         
$1078  BD 95 17      LDA    $1795,X       
$107B  D0 34         BNE    $10b1         
$107D  FE 95 17      INC    $1795,X       
$1080  BD 1C 1A      LDA    $1a1c,X       
$1083  85 FC         STA    $fc           
$1085  BD 1F 1A      LDA    $1a1f,X       
$1088  85 FD         STA    $fd           
$108A  BC 92 17      LDY    $1792,X       
$108D  B1 FC         LDA    ($fc),Y       
$108F  10 09         BPL    $109a         
$1091  38            SEC                  
$1092  E9 A0         SBC    #$a0          
$1094  9D B0 17      STA    $17b0,X       
$1097  C8            INY                  
$1098  B1 FC         LDA    ($fc),Y       
$109A  9D 9B 17      STA    $179b,X       
$109D  C8            INY                  
$109E  B1 FC         LDA    ($fc),Y       
$10A0  C9 FF         CMP    #$ff          
$10A2  D0 04         BNE    $10a8         
$10A4  C8            INY                  
$10A5  B1 FC         LDA    ($fc),Y       
$10A7  A8            TAY                  
$10A8  98            TYA                  
$10A9  9D 92 17      STA    $1792,X       
$10AC  A9 00         LDA    #$00          
$10AE  9D 98 17      STA    $1798,X       
$10B1  AD 83 17      LDA    $1783         
$10B4  D0 6D         BNE    $1123         
$10B6  DE 8F 17      DEC    $178f,X       
$10B9  10 68         BPL    $1123         
$10BB  BC 9B 17      LDY    $179b,X       
$10BE  B9 22 1A      LDA    $1a22,Y       
$10C1  85 FC         STA    $fc           
$10C3  B9 49 1A      LDA    $1a49,Y       
$10C6  85 FD         STA    $fd           
$10C8  BC 98 17      LDY    $1798,X       
$10CB  B1 FC         LDA    ($fc),Y       
$10CD  10 27         BPL    $10f6         
$10CF  C9 C0         CMP    #$c0          
$10D1  90 08         BCC    $10db         
$10D3  9D AA 17      STA    $17aa,X       
$10D6  C8            INY                  
$10D7  B1 FC         LDA    ($fc),Y       
$10D9  10 1B         BPL    $10f6         
$10DB  C9 A0         CMP    #$a0          
$10DD  90 08         BCC    $10e7         
$10DF  9D A7 17      STA    $17a7,X       
$10E2  C8            INY                  
$10E3  B1 FC         LDA    ($fc),Y       
$10E5  10 0F         BPL    $10f6         
$10E7  C9 90         CMP    #$90          
$10E9  90 03         BCC    $10ee         
$10EB  FE A1 17      INC    $17a1,X       
$10EE  29 0F         AND    #$0f          
$10F0  9D 9E 17      STA    $179e,X       
$10F3  C8            INY                  
$10F4  B1 FC         LDA    ($fc),Y       
$10F6  9D A4 17      STA    $17a4,X       
$10F9  F0 04         BEQ    $10ff         
$10FB  C9 7E         CMP    #$7e          
$10FD  D0 05         BNE    $1104         
$10FF  FE A1 17      INC    $17a1,X       
$1102  D0 06         BNE    $110a         
$1104  BD B0 17      LDA    $17b0,X       
$1107  9D B3 17      STA    $17b3,X       
$110A  C8            INY                  
$110B  98            TYA                  
$110C  9D 98 17      STA    $1798,X       
$110F  BD 9E 17      LDA    $179e,X       
$1112  9D 8F 17      STA    $178f,X       
$1115  A9 02         LDA    #$02          
$1117  9D F8 17      STA    $17f8,X       
$111A  B1 FC         LDA    ($fc),Y       
$111C  C9 7F         CMP    #$7f          
$111E  D0 03         BNE    $1123         
$1120  DE 95 17      DEC    $1795,X       
$1123  BC F8 17      LDY    $17f8,X       
$1126  30 36         BMI    $115e         
$1128  BD A1 17      LDA    $17a1,X       
$112B  D0 31         BNE    $115e         
$112D  C0 01         CPY    #$01          
$112F  F0 23         BEQ    $1154         
$1131  C0 00         CPY    #$00          
$1133  F0 2C         BEQ    $1161         
$1135  BD A7 17      LDA    $17a7,X       
$1138  29 1F         AND    #$1f          
$113A  A8            TAY                  
$113B  B9 25 18      LDA    $1825,Y       
$113E  10 0F         BPL    $114f         
$1140  29 0F         AND    #$0f          
$1142  A8            TAY                  
$1143  B9 D8 18      LDA    $18d8,Y       
$1146  9D EF 17      STA    $17ef,X       
$1149  B9 D9 18      LDA    $18d9,Y       
$114C  9D F2 17      STA    $17f2,X       
$114F  A9 FE         LDA    #$fe          
$1151  9D F5 17      STA    $17f5,X       
$1154  BD BC 17      LDA    $17bc,X       
$1157  C9 04         CMP    #$04          
$1159  B0 03         BCS    $115e         
$115B  4C 40 15      JMP    $1540         
$115E  4C 79 13      JMP    $1379         
$1161  A9 FF         LDA    #$ff          
$1163  9D F5 17      STA    $17f5,X       
$1166  BD A7 17      LDA    $17a7,X       
$1169  10 36         BPL    $11a1         
$116B  29 1F         AND    #$1f          
$116D  9D AD 17      STA    $17ad,X       
$1170  9D A7 17      STA    $17a7,X       
$1173  A8            TAY                  
$1174  B9 FD 17      LDA    $17fd,Y       
$1177  9D D4 17      STA    $17d4,X       
$117A  9D EF 17      STA    $17ef,X       
$117D  B9 11 18      LDA    $1811,Y       
$1180  9D D7 17      STA    $17d7,X       
$1183  9D F2 17      STA    $17f2,X       
$1186  B9 25 18      LDA    $1825,Y       
$1189  29 20         AND    #$20          
$118B  F0 08         BEQ    $1195         
$118D  AD 8B 17      LDA    $178b         
$1190  1D 7A 17      ORA    $177a,X       
$1193  D0 06         BNE    $119b         
$1195  AD 8B 17      LDA    $178b         
$1198  3D 7D 17      AND    $177d,X       
$119B  8D 8B 17      STA    $178b         
$119E  4C C8 11      JMP    $11c8         
$11A1  BC AD 17      LDY    $17ad,X       
$11A4  BD D4 17      LDA    $17d4,X       
$11A7  9D EF 17      STA    $17ef,X       
$11AA  BD D7 17      LDA    $17d7,X       
$11AD  9D F2 17      STA    $17f2,X       
$11B0  BD BC 17      LDA    $17bc,X       
$11B3  C9 03         CMP    #$03          
$11B5  F0 18         BEQ    $11cf         
$11B7  C9 04         CMP    #$04          
$11B9  D0 0F         BNE    $11ca         
$11BB  BD CE 17      LDA    $17ce,X       
$11BE  9D D1 17      STA    $17d1,X       
$11C1  BD CB 17      LDA    $17cb,X       
$11C4  9D C8 17      STA    $17c8,X       
$11C7  4C CD 11      JMP    $11cd         
$11CA  A9 00         LDA    #$00          
$11CC  9D BC 17      STA    $17bc,X       
$11CF  B9 25 18      LDA    $1825,Y       
$11D2  29 10         AND    #$10          
$11D4  4A            LSR    A             
$11D5  09 01         ORA    #$01          
$11D7  9D EC 17      STA    $17ec,X       
$11DA  B9 25 18      LDA    $1825,Y       
$11DD  29 40         AND    #$40          
$11DF  F0 12         BEQ    $11f3         
$11E1  0A            ASL    A             
$11E2  8D 8C 17      STA    $178c         
$11E5  B9 39 18      LDA    $1839,Y       
$11E8  8D 8E 17      STA    $178e         
$11EB  CE 8E 17      DEC    $178e         
$11EE  A9 00         LDA    #$00          
$11F0  8D 8D 17      STA    $178d         
$11F3  B9 61 18      LDA    $1861,Y       
$11F6  9D BF 17      STA    $17bf,X       
$11F9  B9 4D 18      LDA    $184d,Y       
$11FC  9D C2 17      STA    $17c2,X       
$11FF  A9 00         LDA    #$00          
$1201  9D C5 17      STA    $17c5,X       
$1204  BD AA 17      LDA    $17aa,X       
$1207  30 03         BMI    $120c         
$1209  4C 1F 13      JMP    $131f         
$120C  29 3F         AND    #$3f          
$120E  9D AA 17      STA    $17aa,X       
$1211  A8            TAY                  
$1212  B9 75 18      LDA    $1875,Y       
$1215  29 0F         AND    #$0f          
$1217  A8            TAY                  
$1218  B9 61 17      LDA    $1761,Y       
$121B  8D 88 12      STA    $1288         
$121E  BC AA 17      LDY    $17aa,X       
$1221  4C 86 12      JMP    $1286         
$1224  B9 96 18      LDA    $1896,Y       
$1227  9D CB 17      STA    $17cb,X       
$122A  B9 B7 18      LDA    $18b7,Y       
$122D  9D C8 17      STA    $17c8,X       
$1230  A9 01         LDA    #$01          
$1232  4C 1C 13      JMP    $131c         
$1235  B9 96 18      LDA    $1896,Y       
$1238  9D CB 17      STA    $17cb,X       
$123B  B9 B7 18      LDA    $18b7,Y       
$123E  9D C8 17      STA    $17c8,X       
$1241  A9 03         LDA    #$03          
$1243  4C 1C 13      JMP    $131c         
$1246  B9 96 18      LDA    $1896,Y       
$1249  30 2F         BMI    $127a         
$124B  9D CB 17      STA    $17cb,X       
$124E  9D C8 17      STA    $17c8,X       
$1251  B9 B7 18      LDA    $18b7,Y       
$1254  9D CE 17      STA    $17ce,X       
$1257  9D D1 17      STA    $17d1,X       
$125A  A9 04         LDA    #$04          
$125C  4C 1C 13      JMP    $131c         
$125F  B9 96 18      LDA    $1896,Y       
$1262  9D CB 17      STA    $17cb,X       
$1265  29 7F         AND    #$7f          
$1267  9D C8 17      STA    $17c8,X       
$126A  B9 B7 18      LDA    $18b7,Y       
$126D  9D D1 17      STA    $17d1,X       
$1270  A9 00         LDA    #$00          
$1272  9D CE 17      STA    $17ce,X       
$1275  A9 05         LDA    #$05          
$1277  4C 1C 13      JMP    $131c         
$127A  4C 1A 13      JMP    $131a         
$127D  B9 B7 18      LDA    $18b7,Y       
$1280  29 0F         AND    #$0f          
$1282  8D 85 17      STA    $1785         
$1285  4C 1F 13      JMP    $131f         
$1288  38            SEC                  
$1289  B0 99         BCS    $1224         
$128B  B9 B7 18      LDA    $18b7,Y       
$128E  29 0F         AND    #$0f          
$1290  9D C8 17      STA    $17c8,X       
$1293  B9 96 18      LDA    $1896,Y       
$1296  18            CLC                  
$1297  69 01         ADC    #$01          
$1299  9D CB 17      STA    $17cb,X       
$129C  4A            LSR    A             
$129D  90 02         BCC    $12a1         
$129F  09 80         ORA    #$80          
$12A1  9D CE 17      STA    $17ce,X       
$12A4  A9 02         LDA    #$02          
$12A6  9D D1 17      STA    $17d1,X       
$12A9  4C 1C 13      JMP    $131c         
$12AC  B9 96 18      LDA    $1896,Y       
$12AF  9D EF 17      STA    $17ef,X       
$12B2  B9 B7 18      LDA    $18b7,Y       
$12B5  9D F2 17      STA    $17f2,X       
$12B8  4C 1F 13      JMP    $131f         
$12BB  B9 96 18      LDA    $1896,Y       
$12BE  9D D4 17      STA    $17d4,X       
$12C1  9D EF 17      STA    $17ef,X       
$12C4  B9 B7 18      LDA    $18b7,Y       
$12C7  9D D7 17      STA    $17d7,X       
$12CA  9D F2 17      STA    $17f2,X       
$12CD  4C 1F 13      JMP    $131f         
$12D0  B9 B7 18      LDA    $18b7,Y       
$12D3  9D BF 17      STA    $17bf,X       
$12D6  4C 1F 13      JMP    $131f         
$12D9  A9 80         LDA    #$80          
$12DB  8D 8C 17      STA    $178c         
$12DE  B9 B7 18      LDA    $18b7,Y       
$12E1  8D 8E 17      STA    $178e         
$12E4  CE 8E 17      DEC    $178e         
$12E7  A9 00         LDA    #$00          
$12E9  8D 8D 17      STA    $178d         
$12EC  4C 1F 13      JMP    $131f         
$12EF  B9 B7 18      LDA    $18b7,Y       
$12F2  9D C2 17      STA    $17c2,X       
$12F5  A9 00         LDA    #$00          
$12F7  9D C5 17      STA    $17c5,X       
$12FA  4C 1F 13      JMP    $131f         
$12FD  B9 B7 18      LDA    $18b7,Y       
$1300  8D 80 17      STA    $1780         
$1303  8D 84 17      STA    $1784         
$1306  A8            TAY                  
$1307  B9 1A 1A      LDA    $1a1a,Y       
$130A  C9 7F         CMP    #$7f          
$130C  F0 03         BEQ    $1311         
$130E  EE 84 17      INC    $1784         
$1311  B9 19 1A      LDA    $1a19,Y       
$1314  A8            TAY                  
$1315  88            DEY                  
$1316  8C 83 17      STY    $1783         
$1319  4C 1F 13      JMP    $131f         
$131C  A9 00         LDA    #$00          
$131E  9D BC 17      STA    $17bc,X       
$1321  BD A1 17      LDA    $17a1,X       
$1324  D0 06         BNE    $132c         
$1326  BD A4 17      LDA    $17a4,X       
$1329  4C 3E 13      JMP    $133e         
$132C  BD A4 17      LDA    $17a4,X       
$132F  F0 39         BEQ    $136a         
$1331  C9 7E         CMP    #$7e          
$1333  F0 39         BEQ    $136e         
$1335  A8            TAY                  
$1336  18            CLC                  
$1337  7D B3 17      ADC    $17b3,X       
$133A  DD B9 17      CMP    $17b9,X       
$133D  F0 34         BEQ    $1373         
$133F  98            TYA                  
$1340  9D B6 17      STA    $17b6,X       
$1343  18            CLC                  
$1344  7D B3 17      ADC    $17b3,X       
$1347  9D B9 17      STA    $17b9,X       
$134A  A8            TAY                  
$134B  BD BC 17      LDA    $17bc,X       
$134E  C9 03         CMP    #$03          
$1350  F0 10         BEQ    $1362         
$1352  C9 04         CMP    #$04          
$1354  F0 0C         BEQ    $1362         
$1356  B9 01 17      LDA    $1701,Y       
$1359  9D DA 17      STA    $17da,X       
$135C  B9 A1 16      LDA    $16a1,Y       
$135F  9D DD 17      STA    $17dd,X       
$1362  BD A1 17      LDA    $17a1,X       
$1365  D0 07         BNE    $136e         
$1367  4C 82 15      JMP    $1582         
$136A  A9 FE         LDA    #$fe          
$136C  D0 02         BNE    $1370         
$136E  A9 FF         LDA    #$ff          
$1370  9D F5 17      STA    $17f5,X       
$1373  A9 00         LDA    #$00          
$1375  9D A1 17      STA    $17a1,X       
$1378  4C E1 15      JMP    $15e1         
$137B  BD BC 17      LDA    $17bc,X       
$137E  A8            TAY                  
$137F  B9 71 17      LDA    $1771,Y       
$1382  8D 85 13      STA    $1385         
$1385  38            SEC                  
$1386  B0 0C         BCS    $1394         
$1388  4C F2 14      JMP    $14f2         
$138B  4C 14 14      JMP    $1414         
$138E  4C 82 14      JMP    $1482         
$1391  4C BC 14      JMP    $14bc         
$1394  BD DA 17      LDA    $17da,X       
$1397  18            CLC                  
$1398  7D C8 17      ADC    $17c8,X       
$139B  9D DA 17      STA    $17da,X       
$139E  BD DD 17      LDA    $17dd,X       
$13A1  7D CB 17      ADC    $17cb,X       
$13A4  9D DD 17      STA    $17dd,X       
$13A7  4C F2 14      JMP    $14f2         
$13AA  BC B9 17      LDY    $17b9,X       
$13AD  B9 02 17      LDA    $1702,Y       
$13B0  F9 01 17      SBC    $1701,Y       
$13B3  85 FC         STA    $fc           
$13B5  B9 A2 16      LDA    $16a2,Y       
$13B8  F9 A1 16      SBC    $16a1,Y       
$13BB  85 FD         STA    $fd           
$13BD  BD CE 17      LDA    $17ce,X       
$13C0  C9 80         CMP    #$80          
$13C2  29 00         AND    #$00          
$13C4  7D C8 17      ADC    $17c8,X       
$13C7  A8            TAY                  
$13C8  88            DEY                  
$13C9  30 07         BMI    $13d2         
$13CB  46 FD         LSR    $fd           
$13CD  66 FC         ROR    $fc           
$13CF  4C C6 13      JMP    $13c6         
$13D2  BD D1 17      LDA    $17d1,X       
$13D5  29 01         AND    #$01          
$13D7  D0 14         BNE    $13ed         
$13D9  BD DA 17      LDA    $17da,X       
$13DC  18            CLC                  
$13DD  65 FC         ADC    $fc           
$13DF  9D DA 17      STA    $17da,X       
$13E2  BD DD 17      LDA    $17dd,X       
$13E5  65 FD         ADC    $fd           
$13E7  9D DD 17      STA    $17dd,X       
$13EA  4C FC 13      JMP    $13fc         
$13ED  BD DA 17      LDA    $17da,X       
$13F0  38            SEC                  
$13F1  E5 FC         SBC    $fc           
$13F3  9D DA 17      STA    $17da,X       
$13F6  BD DD 17      LDA    $17dd,X       
$13F9  E5 FD         SBC    $fd           
$13FB  9D DD 17      STA    $17dd,X       
$13FE  BD CE 17      LDA    $17ce,X       
$1401  29 7F         AND    #$7f          
$1403  18            CLC                  
$1404  69 01         ADC    #$01          
$1406  DD CB 17      CMP    $17cb,X       
$1409  90 05         BCC    $1410         
$140B  FE D1 17      INC    $17d1,X       
$140E  A9 00         LDA    #$00          
$1410  9D CE 17      STA    $17ce,X       
$1413  4C F2 14      JMP    $14f2         
$1416  BC B9 17      LDY    $17b9,X       
$1419  B9 01 17      LDA    $1701,Y       
$141C  85 FC         STA    $fc           
$141E  B9 A1 16      LDA    $16a1,Y       
$1421  85 FD         STA    $fd           
$1423  BD DA 17      LDA    $17da,X       
$1426  38            SEC                  
$1427  E5 FC         SBC    $fc           
$1429  9D DA 17      STA    $17da,X       
$142C  BD DD 17      LDA    $17dd,X       
$142F  E5 FD         SBC    $fd           
$1431  9D DD 17      STA    $17dd,X       
$1434  30 18         BMI    $144e         
$1436  BD DA 17      LDA    $17da,X       
$1439  38            SEC                  
$143A  FD C8 17      SBC    $17c8,X       
$143D  9D DA 17      STA    $17da,X       
$1440  BD DD 17      LDA    $17dd,X       
$1443  FD CB 17      SBC    $17cb,X       
$1446  9D DD 17      STA    $17dd,X       
$1449  10 25         BPL    $1470         
$144B  4C 61 14      JMP    $1461         
$144E  BD DA 17      LDA    $17da,X       
$1451  18            CLC                  
$1452  7D C8 17      ADC    $17c8,X       
$1455  9D DA 17      STA    $17da,X       
$1458  BD DD 17      LDA    $17dd,X       
$145B  7D CB 17      ADC    $17cb,X       
$145E  9D DD 17      STA    $17dd,X       
$1461  30 0D         BMI    $1470         
$1463  A5 FC         LDA    $fc           
$1465  9D DA 17      STA    $17da,X       
$1468  A5 FD         LDA    $fd           
$146A  9D DD 17      STA    $17dd,X       
$146D  4C 7F 14      JMP    $147f         
$1470  BD DA 17      LDA    $17da,X       
$1473  18            CLC                  
$1474  65 FC         ADC    $fc           
$1476  9D DA 17      STA    $17da,X       
$1479  BD DD 17      LDA    $17dd,X       
$147C  65 FD         ADC    $fd           
$147E  9D DD 17      STA    $17dd,X       
$1481  4C F2 14      JMP    $14f2         
$1484  BC D1 17      LDY    $17d1,X       
$1487  DE C8 17      DEC    $17c8,X       
$148A  10 1B         BPL    $14a7         
$148C  C8            INY                  
$148D  B9 D7 19      LDA    $19d7,Y       
$1490  30 0B         BMI    $149d         
$1492  C9 70         CMP    #$70          
$1494  30 07         BMI    $149d         
$1496  29 0F         AND    #$0f          
$1498  18            CLC                  
$1499  7D CE 17      ADC    $17ce,X       
$149C  A8            TAY                  
$149D  98            TYA                  
$149E  9D D1 17      STA    $17d1,X       
$14A1  BD CB 17      LDA    $17cb,X       
$14A4  9D C8 17      STA    $17c8,X       
$14A7  B9 D7 19      LDA    $19d7,Y       
$14AA  18            CLC                  
$14AB  7D B9 17      ADC    $17b9,X       
$14AE  A8            TAY                  
$14AF  B9 01 17      LDA    $1701,Y       
$14B2  9D DA 17      STA    $17da,X       
$14B5  B9 A1 16      LDA    $16a1,Y       
$14B8  9D DD 17      STA    $17dd,X       
$14BB  4C F2 14      JMP    $14f2         
$14BE  DE C8 17      DEC    $17c8,X       
$14C1  10 31         BPL    $14f4         
$14C3  BD CB 17      LDA    $17cb,X       
$14C6  30 06         BMI    $14ce         
$14C8  FE CE 17      INC    $17ce,X       
$14CB  4C D1 14      JMP    $14d1         
$14CE  DE CE 17      DEC    $17ce,X       
$14D1  29 7F         AND    #$7f          
$14D3  9D C8 17      STA    $17c8,X       
$14D6  DE D1 17      DEC    $17d1,X       
$14D9  D0 05         BNE    $14e0         
$14DB  A9 00         LDA    #$00          
$14DD  9D BC 17      STA    $17bc,X       
$14E0  BD B9 17      LDA    $17b9,X       
$14E3  18            CLC                  
$14E4  7D CE 17      ADC    $17ce,X       
$14E7  A8            TAY                  
$14E8  B9 01 17      LDA    $1701,Y       
$14EB  9D DA 17      STA    $17da,X       
$14EE  B9 A1 16      LDA    $16a1,Y       
$14F1  9D DD 17      STA    $17dd,X       
$14F4  BC C2 17      LDY    $17c2,X       
$14F7  B9 3E 19      LDA    $193e,Y       
$14FA  C9 7F         CMP    #$7f          
$14FC  D0 0C         BNE    $150a         
$14FE  B9 70 19      LDA    $1970,Y       
$1501  DD C2 17      CMP    $17c2,X       
$1504  F0 3C         BEQ    $1542         
$1506  9D C2 17      STA    $17c2,X       
$1509  A8            TAY                  
$150A  B9 3E 19      LDA    $193e,Y       
$150D  10 0C         BPL    $151b         
$150F  9D E9 17      STA    $17e9,X       
$1512  B9 57 19      LDA    $1957,Y       
$1515  9D E6 17      STA    $17e6,X       
$1518  4C 2D 15      JMP    $152d         
$151B  85 FC         STA    $fc           
$151D  BD E6 17      LDA    $17e6,X       
$1520  18            CLC                  
$1521  79 57 19      ADC    $1957,Y       
$1524  9D E6 17      STA    $17e6,X       
$1527  BD E9 17      LDA    $17e9,X       
$152A  65 FC         ADC    $fc           
$152C  9D E9 17      STA    $17e9,X       
$152F  FE C5 17      INC    $17c5,X       
$1532  BD C5 17      LDA    $17c5,X       
$1535  D9 70 19      CMP    $1970,Y       
$1538  90 08         BCC    $1542         
$153A  FE C2 17      INC    $17c2,X       
$153D  A9 00         LDA    #$00          
$153F  9D C5 17      STA    $17c5,X       
$1542  BC BF 17      LDY    $17bf,X       
$1545  B9 DA 18      LDA    $18da,Y       
$1548  C9 7F         CMP    #$7f          
$154A  D0 0A         BNE    $1556         
$154C  B9 0C 19      LDA    $190c,Y       
$154F  9D BF 17      STA    $17bf,X       
$1552  A8            TAY                  
$1553  B9 DA 18      LDA    $18da,Y       
$1556  9D EC 17      STA    $17ec,X       
$1559  B9 0C 19      LDA    $190c,Y       
$155C  F0 17         BEQ    $1575         
$155E  C9 81         CMP    #$81          
$1560  B0 04         BCS    $1566         
$1562  18            CLC                  
$1563  7D B9 17      ADC    $17b9,X       
$1566  29 7F         AND    #$7f          
$1568  A8            TAY                  
$1569  B9 01 17      LDA    $1701,Y       
$156C  9D E0 17      STA    $17e0,X       
$156F  B9 A1 16      LDA    $16a1,Y       
$1572  4C 7C 15      JMP    $157c         
$1575  BD DA 17      LDA    $17da,X       
$1578  9D E0 17      STA    $17e0,X       
$157B  BD DD 17      LDA    $17dd,X       
$157E  9D E3 17      STA    $17e3,X       
$1581  FE BF 17      INC    $17bf,X       
$1584  BC 77 17      LDY    $1777,X       
$1587  BD E0 17      LDA    $17e0,X       
$158A  99 00 D4      STA    $d400,Y       
$158D  BD E3 17      LDA    $17e3,X       
$1590  99 01 D4      STA    $d401,Y       
$1593  BD F2 17      LDA    $17f2,X       
$1596  99 06 D4      STA    $d406,Y       
$1599  BD EF 17      LDA    $17ef,X       
$159C  99 05 D4      STA    $d405,Y       
$159F  BD E6 17      LDA    $17e6,X       
$15A2  99 02 D4      STA    $d402,Y       
$15A5  BD E9 17      LDA    $17e9,X       
$15A8  99 03 D4      STA    $d403,Y       
$15AB  BD EC 17      LDA    $17ec,X       
$15AE  3D F5 17      AND    $17f5,X       
$15B1  99 04 D4      STA    $d404,Y       
$15B4  BD F8 17      LDA    $17f8,X       
$15B7  D0 2A         BNE    $15e3         
$15B9  BD A1 17      LDA    $17a1,X       
$15BC  F0 25         BEQ    $15e3         
$15BE  BD BC 17      LDA    $17bc,X       
$15C1  C9 03         CMP    #$03          
$15C3  F0 1B         BEQ    $15e0         
$15C5  C9 04         CMP    #$04          
$15C7  F0 17         BEQ    $15e0         
$15C9  BD A4 17      LDA    $17a4,X       
$15CC  F0 12         BEQ    $15e0         
$15CE  C9 7E         CMP    #$7e          
$15D0  F0 0E         BEQ    $15e0         
$15D2  18            CLC                  
$15D3  7D B3 17      ADC    $17b3,X       
$15D6  DD B9 17      CMP    $17b9,X       
$15D9  F0 05         BEQ    $15e0         
$15DB  A9 00         LDA    #$00          
$15DD  9D BC 17      STA    $17bc,X       
$15E0  4C 02 12      JMP    $1202         
$15E3  BD F8 17      LDA    $17f8,X       
$15E6  30 03         BMI    $15eb         
$15E8  DE F8 17      DEC    $17f8,X       
$15EB  CA            DEX                  
$15EC  30 03         BMI    $15f1         
$15EE  4C 6F 10      JMP    $106f         
$15F1  AD 8C 17      LDA    $178c         
$15F4  30 61         BMI    $1657         
$15F6  F0 64         BEQ    $165c         
$15F8  AC 8E 17      LDY    $178e         
$15FB  CE 8D 17      DEC    $178d         
$15FE  10 41         BPL    $1641         
$1600  C8            INY                  
$1601  B9 89 19      LDA    $1989,Y       
$1604  C9 7F         CMP    #$7f          
$1606  D0 12         BNE    $161a         
$1608  98            TYA                  
$1609  D9 BD 19      CMP    $19bd,Y       
$160C  D0 08         BNE    $1616         
$160E  A9 00         LDA    #$00          
$1610  8D 8C 17      STA    $178c         
$1613  4C 5A 16      JMP    $165a         
$1616  B9 BD 19      LDA    $19bd,Y       
$1619  A8            TAY                  
$161A  B9 89 19      LDA    $1989,Y       
$161D  10 1C         BPL    $163b         
$161F  29 70         AND    #$70          
$1621  8D 86 17      STA    $1786         
$1624  B9 89 19      LDA    $1989,Y       
$1627  29 0F         AND    #$0f          
$1629  8D 8A 17      STA    $178a         
$162C  B9 A3 19      LDA    $19a3,Y       
$162F  8D 89 17      STA    $1789         
$1632  B9 BD 19      LDA    $19bd,Y       
$1635  8D 87 17      STA    $1787         
$1638  4C 52 16      JMP    $1652         
$163B  B9 BD 19      LDA    $19bd,Y       
$163E  8D 8D 17      STA    $178d         
$1641  AD 89 17      LDA    $1789         
$1644  18            CLC                  
$1645  79 A3 19      ADC    $19a3,Y       
$1648  8D 89 17      STA    $1789         
$164B  AD 8A 17      LDA    $178a         
$164E  79 89 19      ADC    $1989,Y       
$1651  8D 8A 17      STA    $178a         
$1654  8C 8E 17      STY    $178e         
$1657  A9 40         LDA    #$40          
$1659  8D 8C 17      STA    $178c         
$165C  AD 8A 17      LDA    $178a         
$165F  85 FC         STA    $fc           
$1661  AD 89 17      LDA    $1789         
$1664  46 FC         LSR    $fc           
$1666  6A            ROR    A             
$1667  AA            TAX                  
$1668  46 FC         LSR    $fc           
$166A  6A            ROR    A             
$166B  46 FC         LSR    $fc           
$166D  6A            ROR    A             
$166E  46 FC         LSR    $fc           
$1670  6A            ROR    A             
$1671  A8            TAY                  
$1672  AD 87 17      LDA    $1787         
$1675  0D 88 17      ORA    $1788         
$1678  8D 17 D4      STA    $d417         
$167B  8C 16 D4      STY    $d416         
$167E  8A            TXA                  
$167F  29 07         AND    #$07          
$1681  8D 15 D4      STA    $d415         
$1684  AD 85 17      LDA    $1785         
$1687  0D 86 17      ORA    $1786         
$168A  8D 18 D4      STA    $d418         
$168D  AD 8B 17      LDA    $178b         
$1690  8D 88 17      STA    $1788         
$1693  60            RTS                  
$1694  8D 82 17      STA    $1782         
$1697  A9 00         LDA    #$00          
$1699  8D 81 17      STA    $1781         
$169C  60            RTS                  
$169D  A9 40         LDA    #$40          
$169F  8D 81 17      STA    $1781         
$16A2  60            RTS                  
$16A3  01 01         ORA    ($01,X)       
$16A5  01 01         ORA    ($01,X)       
$16A7  01 01         ORA    ($01,X)       
$16A9  01 01         ORA    ($01,X)       
$16AB  01 01         ORA    ($01,X)       
$16AD  01 02         ORA    ($02,X)       
$16AF  02            DCB    $02           ; Unknown opcode
$16B0  02            DCB    $02           ; Unknown opcode
$16B1  02            DCB    $02           ; Unknown opcode
$16B2  02            DCB    $02           ; Unknown opcode
$16B3  02            DCB    $02           ; Unknown opcode
$16B4  02            DCB    $02           ; Unknown opcode
$16B5  03            DCB    $03           ; Unknown opcode
$16B6  03            DCB    $03           ; Unknown opcode
$16B7  03            DCB    $03           ; Unknown opcode
$16B8  03            DCB    $03           ; Unknown opcode
$16B9  03            DCB    $03           ; Unknown opcode
$16BA  04            DCB    $04           ; Unknown opcode
$16BB  04            DCB    $04           ; Unknown opcode
$16BC  04            DCB    $04           ; Unknown opcode
$16BD  04            DCB    $04           ; Unknown opcode
$16BE  05 05         ORA    $05           
$16C0  05 06         ORA    $06           
$16C2  06 06         ASL    $06           
$16C4  07            DCB    $07           ; Unknown opcode
$16C5  07            DCB    $07           ; Unknown opcode
$16C6  08            PHP                  
$16C7  08            PHP                  
$16C8  09 09         ORA    #$09          
$16CA  0A            ASL    A             
$16CB  0A            ASL    A             
$16CC  0B            DCB    $0b           ; Unknown opcode
$16CD  0C            DCB    $0c           ; Unknown opcode
$16CE  0D 0D 0E      ORA    $0e0d         
$16D1  0F            DCB    $0f           ; Unknown opcode
$16D2  10 11         BPL    $16e5         
$16D4  12            DCB    $12           ; Unknown opcode
$16D5  13            DCB    $13           ; Unknown opcode
$16D6  14            DCB    $14           ; Unknown opcode
$16D7  15 17         ORA    $17,X         
$16D9  18            CLC                  
$16DA  1A            DCB    $1a           ; Unknown opcode
$16DB  1B            DCB    $1b           ; Unknown opcode
$16DC  1D 1F 20      ORA    $201f,X       
$16DF  22            DCB    $22           ; Unknown opcode
$16E0  24 27         BIT    $27           
$16E2  29 2B         AND    #$2b          
$16E4  2E 31 34      ROL    $3431         
$16E7  37            DCB    $37           ; Unknown opcode
$16E8  3A            DCB    $3a           ; Unknown opcode
$16E9  3E 41 45      ROL    $4541,X       
$16EC  49 4E         EOR    #$4e          
$16EE  52            DCB    $52           ; Unknown opcode
$16EF  57            DCB    $57           ; Unknown opcode
$16F0  5C            DCB    $5c           ; Unknown opcode
$16F1  62            DCB    $62           ; Unknown opcode
$16F2  68            PLA                  
$16F3  6E 75 7C      ROR    $7c75         
$16F6  83            DCB    $83           ; Unknown opcode
$16F7  8B            DCB    $8b           ; Unknown opcode
$16F8  93            DCB    $93           ; Unknown opcode
$16F9  9C            DCB    $9c           ; Unknown opcode
$16FA  A5 AF         LDA    $af           
$16FC  B9 C4 D0      LDA    $d0c4,Y       
$16FF  DD EA F8      CMP    $f8ea,X       
$1702  FD 16 27      SBC    $2716,X       
$1705  38            SEC                  
$1706  4B            DCB    $4b           ; Unknown opcode
$1707  5F            DCB    $5f           ; Unknown opcode
$1708  73            DCB    $73           ; Unknown opcode
$1709  8A            TXA                  
$170A  A1 BA         LDA    ($ba,X)       
$170C  D4            DCB    $d4           ; Unknown opcode
$170D  F0 0E         BEQ    $171d         
$170F  2D 4E 71      AND    $714e         
$1712  96 BD         STX    $bd,Y         
$1714  E7            DCB    $e7           ; Unknown opcode
$1715  13            DCB    $13           ; Unknown opcode
$1716  42            DCB    $42           ; Unknown opcode
$1717  74            DCB    $74           ; Unknown opcode
$1718  A9 E0         LDA    #$e0          
$171A  1B            DCB    $1b           ; Unknown opcode
$171B  5A            DCB    $5a           ; Unknown opcode
$171C  9B            DCB    $9b           ; Unknown opcode
$171D  E2            DCB    $e2           ; Unknown opcode
$171E  2C 7B CE      BIT    $ce7b         
$1721  27            DCB    $27           ; Unknown opcode
$1722  85 E8         STA    $e8           
$1724  51 C1         EOR    ($c1),Y       
$1726  37            DCB    $37           ; Unknown opcode
$1727  B4 37         LDY    $37,X         
$1729  C4 57         CPY    $57           
$172B  F5 9C         SBC    $9c,X         
$172D  4E 09 D0      LSR    $d009         
$1730  A3            DCB    $a3           ; Unknown opcode
$1731  82            DCB    $82           ; Unknown opcode
$1732  6E 68 6E      ROR    $6e68         
$1735  88            DEY                  
$1736  AF            DCB    $af           ; Unknown opcode
$1737  EB            DCB    $eb           ; Unknown opcode
$1738  39 9C 13      AND    $139c,Y       
$173B  A1 46         LDA    ($46,X)       
$173D  04            DCB    $04           ; Unknown opcode
$173E  DC            DCB    $dc           ; Unknown opcode
$173F  D0 DC         BNE    $171d         
$1741  10 5E         BPL    $17a1         
$1743  D6 72         DEC    $72,X         
$1745  38            SEC                  
$1746  26 42         ROL    $42           
$1748  8C 08 B8      STY    $b808         
$174B  A0 B8         LDY    #$b8          
$174D  20 BC AC      JSR    $acbc         
$1750  E4 70         CPX    $70           
$1752  4C 84 18      JMP    $1884         
$1755  10 70         BPL    $17c7         
$1757  40            RTI                  
$1758  70 40         BVS    $179a         
$175A  78            SEI                  
$175B  58            CLI                  
$175C  C8            INY                  
$175D  E0 98         CPX    #$98          
$175F  08            PHP                  
$1760  30 20         BMI    $1782         
$1762  2E 99 00      ROL    $0099         
$1765  AA            TAX                  
$1766  BB            DCB    $bb           ; Unknown opcode
$1767  D4            DCB    $d4           ; Unknown opcode
$1768  2D 2D 2D      AND    $2d2d         
$176B  21 30         AND    ($30,X)       
$176D  4E 45 64      LSR    $6445         
$1770  72            DCB    $72           ; Unknown opcode
$1771  F2            DCB    $f2           ; Unknown opcode
$1772  2D 00 0C      AND    $0c00         
$1775  22            DCB    $22           ; Unknown opcode
$1776  03            DCB    $03           ; Unknown opcode
$1777  06 09         ASL    $09           
$1779  00            BRK                  
$177A  07            DCB    $07           ; Unknown opcode
$177B  0E 01 02      ASL    $0201         
$177E  04            DCB    $04           ; Unknown opcode
$177F  FE FD FB      INC    $fbfd,X       
$1782  00            BRK                  
$1783  40            RTI                  
$1784  00            BRK                  
$1785  04            DCB    $04           ; Unknown opcode
$1786  00            BRK                  
$1787  0F            DCB    $0f           ; Unknown opcode
$1788  00            BRK                  
$1789  00            BRK                  
$178A  00            BRK                  
$178B  00            BRK                  
$178C  00            BRK                  
$178D  00            BRK                  
$178E  00            BRK                  
$178F  00            BRK                  
$1790  00            BRK                  
$1791  00            BRK                  
$1792  00            BRK                  
$1793  00            BRK                  
$1794  03            DCB    $03           ; Unknown opcode
$1795  03            DCB    $03           ; Unknown opcode
$1796  03            DCB    $03           ; Unknown opcode
$1797  01 01         ORA    ($01,X)       
$1799  01 00         ORA    ($00,X)       
$179B  00            BRK                  
$179C  00            BRK                  
$179D  0F            DCB    $0f           ; Unknown opcode
$179E  12            DCB    $12           ; Unknown opcode
$179F  0A            ASL    A             
$17A0  00            BRK                  
$17A1  0F            DCB    $0f           ; Unknown opcode
$17A2  01 01         ORA    ($01,X)       
$17A4  00            BRK                  
$17A5  00            BRK                  
$17A6  00            BRK                  
$17A7  00            BRK                  
$17A8  27            DCB    $27           ; Unknown opcode
$17A9  0C            DCB    $0c           ; Unknown opcode
$17AA  00            BRK                  
$17AB  0B            DCB    $0b           ; Unknown opcode
$17AC  13            DCB    $13           ; Unknown opcode
$17AD  00            BRK                  
$17AE  12            DCB    $12           ; Unknown opcode
$17AF  0C            DCB    $0c           ; Unknown opcode
$17B0  00            BRK                  
$17B1  0B            DCB    $0b           ; Unknown opcode
$17B2  00            BRK                  
$17B3  00            BRK                  
$17B4  00            BRK                  
$17B5  00            BRK                  
$17B6  00            BRK                  
$17B7  00            BRK                  
$17B8  41 00         EOR    ($00,X)       
$17BA  27            DCB    $27           ; Unknown opcode
$17BB  41 00         EOR    ($00,X)       
$17BD  27            DCB    $27           ; Unknown opcode
$17BE  01 00         ORA    ($00,X)       
$17C0  00            BRK                  
$17C1  31 03         AND    ($03),Y       
$17C3  21 04         AND    ($04,X)       
$17C5  04            DCB    $04           ; Unknown opcode
$17C6  03            DCB    $03           ; Unknown opcode
$17C7  03            DCB    $03           ; Unknown opcode
$17C8  06 00         ASL    $00           
$17CA  F4            DCB    $f4           ; Unknown opcode
$17CB  00            BRK                  
$17CC  F0 FF         BEQ    $17cd         
$17CE  00            BRK                  
$17CF  FF            DCB    $ff           ; Unknown opcode
$17D0  00            BRK                  
$17D1  00            BRK                  
$17D2  00            BRK                  
$17D3  00            BRK                  
$17D4  00            BRK                  
$17D5  04            DCB    $04           ; Unknown opcode
$17D6  A0 00         LDY    #$00          
$17D8  20 25 00      JSR    $0025         
$17DB  3A            DCB    $3a           ; Unknown opcode
$17DC  FA            DCB    $fa           ; Unknown opcode
$17DD  00            BRK                  
$17DE  57            DCB    $57           ; Unknown opcode
$17DF  27            DCB    $27           ; Unknown opcode
$17E0  00            BRK                  
$17E1  0A            ASL    A             
$17E2  FA            DCB    $fa           ; Unknown opcode
$17E3  00            BRK                  
$17E4  57            DCB    $57           ; Unknown opcode
$17E5  27            DCB    $27           ; Unknown opcode
$17E6  00            BRK                  
$17E7  0A            ASL    A             
$17E8  A0 D0         LDY    #$d0          
$17EA  70 82         BVS    $176e         
$17EC  82            DCB    $82           ; Unknown opcode
$17ED  81 13         STA    ($13,X)       
$17EF  41 40         EOR    ($40,X)       
$17F1  A0 0F         LDY    #$0f          
$17F3  20 25 00      JSR    $0025         
$17F6  3A            DCB    $3a           ; Unknown opcode
$17F7  FF            DCB    $ff           ; Unknown opcode
$17F8  FE FF 00      INC    $00ff,X       
$17FB  FF            DCB    $ff           ; Unknown opcode
$17FC  FF            DCB    $ff           ; Unknown opcode
$17FD  00            BRK                  
$17FE  0F            DCB    $0f           ; Unknown opcode
$17FF  05 00         ORA    $00           
$1801  00            BRK                  
$1802  02            DCB    $02           ; Unknown opcode
$1803  02            DCB    $02           ; Unknown opcode
$1804  00            BRK                  
$1805  02            DCB    $02           ; Unknown opcode
$1806  00            BRK                  
$1807  00            BRK                  
$1808  00            BRK                  
$1809  10 20         BPL    $182b         
$180B  A0 E0         LDY    #$e0          
$180D  D0 00         BNE    $180f         
$180F  00            BRK                  
$1810  05 00         ORA    $00           
$1812  00            BRK                  
$1813  3A            DCB    $3a           ; Unknown opcode
$1814  F7            DCB    $f7           ; Unknown opcode
$1815  F6 07         INC    $07,X         
$1817  F7            DCB    $f7           ; Unknown opcode
$1818  67            DCB    $67           ; Unknown opcode
$1819  88            DEY                  
$181A  88            DEY                  
$181B  A8            TAY                  
$181C  48            PHA                  
$181D  24 3A         BIT    $3a           
$181F  25 03         AND    $03           
$1821  03            DCB    $03           ; Unknown opcode
$1822  12            DCB    $12           ; Unknown opcode
$1823  8A            TXA                  
$1824  66 78         ROR    $78           
$1826  F7            DCB    $f7           ; Unknown opcode
$1827  80            DCB    $80           ; Unknown opcode
$1828  C0 C0         CPY    #$c0          
$182A  C0 C0         CPY    #$c0          
$182C  00            BRK                  
$182D  C0 C0         CPY    #$c0          
$182F  80            DCB    $80           ; Unknown opcode
$1830  00            BRK                  
$1831  80            DCB    $80           ; Unknown opcode
$1832  80            DCB    $80           ; Unknown opcode
$1833  00            BRK                  
$1834  80            DCB    $80           ; Unknown opcode
$1835  80            DCB    $80           ; Unknown opcode
$1836  A0 80         LDY    #$80          
$1838  80            DCB    $80           ; Unknown opcode
$1839  80            DCB    $80           ; Unknown opcode
$183A  C0 00         CPY    #$00          
$183C  00            BRK                  
$183D  06 0B         ASL    $0b           
$183F  0D 00 0F      ORA    $0f00         
$1842  10 00         BPL    $1844         
$1844  00            BRK                  
$1845  00            BRK                  
$1846  00            BRK                  
$1847  00            BRK                  
$1848  00            BRK                  
$1849  00            BRK                  
$184A  0B            DCB    $0b           ; Unknown opcode
$184B  00            BRK                  
$184C  00            BRK                  
$184D  00            BRK                  
$184E  16 09         ASL    $09,X         
$1850  00            BRK                  
$1851  07            DCB    $07           ; Unknown opcode
$1852  00            BRK                  
$1853  00            BRK                  
$1854  00            BRK                  
$1855  00            BRK                  
$1856  00            BRK                  
$1857  00            BRK                  
$1858  00            BRK                  
$1859  00            BRK                  
$185A  00            BRK                  
$185B  00            BRK                  
$185C  00            BRK                  
$185D  00            BRK                  
$185E  00            BRK                  
$185F  00            BRK                  
$1860  0E 13 07      ASL    $0713         
$1863  00            BRK                  
$1864  04            DCB    $04           ; Unknown opcode
$1865  09 0E         ORA    #$0e          
$1867  04            DCB    $04           ; Unknown opcode
$1868  00            BRK                  
$1869  11 16         ORA    ($16),Y       
$186B  18            CLC                  
$186C  1A            DCB    $1a           ; Unknown opcode
$186D  1D 1F 30      ORA    $301f,X       
$1870  1B            DCB    $1b           ; Unknown opcode
$1871  22            DCB    $22           ; Unknown opcode
$1872  24 27         BIT    $27           
$1874  00            BRK                  
$1875  02            DCB    $02           ; Unknown opcode
$1876  2B            DCB    $2b           ; Unknown opcode
$1877  02            DCB    $02           ; Unknown opcode
$1878  02            DCB    $02           ; Unknown opcode
$1879  01 01         ORA    ($01,X)       
$187B  03            DCB    $03           ; Unknown opcode
$187C  03            DCB    $03           ; Unknown opcode
$187D  03            DCB    $03           ; Unknown opcode
$187E  03            DCB    $03           ; Unknown opcode
$187F  03            DCB    $03           ; Unknown opcode
$1880  03            DCB    $03           ; Unknown opcode
$1881  03            DCB    $03           ; Unknown opcode
$1882  03            DCB    $03           ; Unknown opcode
$1883  03            DCB    $03           ; Unknown opcode
$1884  03            DCB    $03           ; Unknown opcode
$1885  03            DCB    $03           ; Unknown opcode
$1886  03            DCB    $03           ; Unknown opcode
$1887  08            PHP                  
$1888  08            PHP                  
$1889  00            BRK                  
$188A  00            BRK                  
$188B  00            BRK                  
$188C  0A            ASL    A             
$188D  02            DCB    $02           ; Unknown opcode
$188E  03            DCB    $03           ; Unknown opcode
$188F  03            DCB    $03           ; Unknown opcode
$1890  03            DCB    $03           ; Unknown opcode
$1891  03            DCB    $03           ; Unknown opcode
$1892  02            DCB    $02           ; Unknown opcode
$1893  02            DCB    $02           ; Unknown opcode
$1894  02            DCB    $02           ; Unknown opcode
$1895  08            PHP                  
$1896  0B            DCB    $0b           ; Unknown opcode
$1897  08            PHP                  
$1898  01 80         ORA    ($80,X)       
$189A  03            DCB    $03           ; Unknown opcode
$189B  04            DCB    $04           ; Unknown opcode
$189C  01 01         ORA    ($01,X)       
$189E  01 01         ORA    ($01,X)       
$18A0  01 01         ORA    ($01,X)       
$18A2  01 01         ORA    ($01,X)       
$18A4  01 01         ORA    ($01,X)       
$18A6  01 01         ORA    ($01,X)       
$18A8  00            BRK                  
$18A9  00            BRK                  
$18AA  FF            DCB    $ff           ; Unknown opcode
$18AB  FF            DCB    $ff           ; Unknown opcode
$18AC  FF            DCB    $ff           ; Unknown opcode
$18AD  00            BRK                  
$18AE  01 01         ORA    ($01,X)       
$18B0  01 01         ORA    ($01,X)       
$18B2  01 00         ORA    ($00,X)       
$18B4  02            DCB    $02           ; Unknown opcode
$18B5  00            BRK                  
$18B6  00            BRK                  
$18B7  00            BRK                  
$18B8  00            BRK                  
$18B9  00            BRK                  
$18BA  00            BRK                  
$18BB  03            DCB    $03           ; Unknown opcode
$18BC  03            DCB    $03           ; Unknown opcode
$18BD  00            BRK                  
$18BE  04            DCB    $04           ; Unknown opcode
$18BF  08            PHP                  
$18C0  0C            DCB    $0c           ; Unknown opcode
$18C1  10 14         BPL    $18d7         
$18C3  18            CLC                  
$18C4  1C            DCB    $1c           ; Unknown opcode
$18C5  20 24 28      JSR    $2824         
$18C8  2C 28 14      BIT    $1428         
$18CB  F0 F4         BEQ    $18c1         
$18CD  80            DCB    $80           ; Unknown opcode
$18CE  13            DCB    $13           ; Unknown opcode
$18CF  C0 30         CPY    #$30          
$18D1  35 39         AND    $39,X         
$18D3  3D 30 00      AND    $0030,X       
$18D6  A0 00         LDY    #$00          
$18D8  29 AB         AND    #$ab          
$18DA  0F            DCB    $0f           ; Unknown opcode
$18DB  00            BRK                  
$18DC  21 21         AND    ($21,X)       
$18DE  41 7F         EOR    ($7f,X)       
$18E0  81 41         STA    ($41,X)       
$18E2  41 41         EOR    ($41,X)       
$18E4  7F            DCB    $7f           ; Unknown opcode
$18E5  81 41         STA    ($41,X)       
$18E7  80            DCB    $80           ; Unknown opcode
$18E8  80            DCB    $80           ; Unknown opcode
$18E9  7F            DCB    $7f           ; Unknown opcode
$18EA  81 01         STA    ($01,X)       
$18EC  7F            DCB    $7f           ; Unknown opcode
$18ED  81 15         STA    ($15,X)       
$18EF  11 11         ORA    ($11),Y       
$18F1  7F            DCB    $7f           ; Unknown opcode
$18F2  81 7F         STA    ($7f,X)       
$18F4  21 7F         AND    ($7f,X)       
$18F6  21 11         AND    ($11,X)       
$18F8  7F            DCB    $7f           ; Unknown opcode
$18F9  51 7F         EOR    ($7f),Y       
$18FB  15 40         ORA    $40,X         
$18FD  7F            DCB    $7f           ; Unknown opcode
$18FE  53            DCB    $53           ; Unknown opcode
$18FF  7F            DCB    $7f           ; Unknown opcode
$1900  81 01         STA    ($01,X)       
$1902  7F            DCB    $7f           ; Unknown opcode
$1903  41 7F         EOR    ($7f,X)       
$1905  20 7F 81      JSR    $817f         
$1908  41 40         EOR    ($40,X)       
$190A  80            DCB    $80           ; Unknown opcode
$190B  7F            DCB    $7f           ; Unknown opcode
$190C  13            DCB    $13           ; Unknown opcode
$190D  7F            DCB    $7f           ; Unknown opcode
$190E  80            DCB    $80           ; Unknown opcode
$190F  80            DCB    $80           ; Unknown opcode
$1910  00            BRK                  
$1911  02            DCB    $02           ; Unknown opcode
$1912  C0 A1         CPY    #$a1          
$1914  9A            TXS                  
$1915  00            BRK                  
$1916  07            DCB    $07           ; Unknown opcode
$1917  C4 AC         CPY    $ac           
$1919  C0 BC         CPY    #$bc          
$191B  0C            DCB    $0c           ; Unknown opcode
$191C  C0 00         CPY    #$00          
$191E  0F            DCB    $0f           ; Unknown opcode
$191F  C0 00         CPY    #$00          
$1921  76 74         ROR    $74,X         
$1923  14            DCB    $14           ; Unknown opcode
$1924  B4 12         LDY    $12,X         
$1926  00            BRK                  
$1927  18            CLC                  
$1928  00            BRK                  
$1929  00            BRK                  
$192A  1B            DCB    $1b           ; Unknown opcode
$192B  00            BRK                  
$192C  1D C5 00      ORA    $00c5,X       
$192F  20 00 22      JSR    $2200         
$1932  C0 00         CPY    #$00          
$1934  25 00         AND    $00           
$1936  27            DCB    $27           ; Unknown opcode
$1937  00            BRK                  
$1938  29 C7         AND    #$c7          
$193A  AE A5 C0      LDX    $c0a5         
$193D  2E 00 30      ROL    $3000         
$1940  88            DEY                  
$1941  00            BRK                  
$1942  81 00         STA    ($00,X)       
$1944  00            BRK                  
$1945  0F            DCB    $0f           ; Unknown opcode
$1946  7F            DCB    $7f           ; Unknown opcode
$1947  88            DEY                  
$1948  7F            DCB    $7f           ; Unknown opcode
$1949  88            DEY                  
$194A  0F            DCB    $0f           ; Unknown opcode
$194B  0F            DCB    $0f           ; Unknown opcode
$194C  00            BRK                  
$194D  7F            DCB    $7f           ; Unknown opcode
$194E  88            DEY                  
$194F  00            BRK                  
$1950  0F            DCB    $0f           ; Unknown opcode
$1951  00            BRK                  
$1952  7F            DCB    $7f           ; Unknown opcode
$1953  86 00         STX    $00           
$1955  0F            DCB    $0f           ; Unknown opcode
$1956  00            BRK                  
$1957  0F            DCB    $0f           ; Unknown opcode
$1958  7F            DCB    $7f           ; Unknown opcode
$1959  00            BRK                  
$195A  00            BRK                  
$195B  70 40         BVS    $199d         
$195D  10 F0         BPL    $194f         
$195F  00            BRK                  
$1960  00            BRK                  
$1961  00            BRK                  
$1962  00            BRK                  
$1963  A0 F0         LDY    #$f0          
$1965  10 00         BPL    $1967         
$1967  00            BRK                  
$1968  80            DCB    $80           ; Unknown opcode
$1969  F0 10         BEQ    $197b         
$196B  00            BRK                  
$196C  00            BRK                  
$196D  80            DCB    $80           ; Unknown opcode
$196E  80            DCB    $80           ; Unknown opcode
$196F  30 D0         BMI    $1941         
$1971  00            BRK                  
$1972  00            BRK                  
$1973  01 00         ORA    ($00,X)       
$1975  04            DCB    $04           ; Unknown opcode
$1976  20 20 04      JSR    $0420         
$1979  00            BRK                  
$197A  07            DCB    $07           ; Unknown opcode
$197B  00            BRK                  
$197C  05 20         ORA    $20           
$197E  20 0A 00      JSR    $000a         
$1981  0F            DCB    $0f           ; Unknown opcode
$1982  30 30         BMI    $19b4         
$1984  10 00         BPL    $1986         
$1986  10 10         BPL    $1998         
$1988  30 30         BMI    $19ba         
$198A  16 9F         ASL    $9f,X         
$198C  90 90         BCC    $191e         
$198E  90 0F         BCC    $199f         
$1990  7F            DCB    $7f           ; Unknown opcode
$1991  A4 90         LDY    $90           
$1993  C1 A5         CMP    ($a5,X)       
$1995  7F            DCB    $7f           ; Unknown opcode
$1996  A9 7F         LDA    #$7f          
$1998  A9 7F         LDA    #$7f          
$199A  A9 97         LDA    #$97          
$199C  0E 7F A9      ASL    $a97f         
$199F  0F            DCB    $0f           ; Unknown opcode
$19A0  7F            DCB    $7f           ; Unknown opcode
$19A1  9F            DCB    $9f           ; Unknown opcode
$19A2  00            BRK                  
$19A3  E2            DCB    $e2           ; Unknown opcode
$19A4  7F            DCB    $7f           ; Unknown opcode
$19A5  00            BRK                  
$19A6  2C 24 3A      BIT    $3a24         
$19A9  FF            DCB    $ff           ; Unknown opcode
$19AA  00            BRK                  
$19AB  30 4F         BMI    $19fc         
$19AD  70 70         BVS    $1a1f         
$19AF  00            BRK                  
$19B0  00            BRK                  
$19B1  00            BRK                  
$19B2  00            BRK                  
$19B3  00            BRK                  
$19B4  00            BRK                  
$19B5  00            BRK                  
$19B6  10 00         BPL    $19b8         
$19B8  00            BRK                  
$19B9  A6 00         LDX    $00           
$19BB  00            BRK                  
$19BC  00            BRK                  
$19BD  00            BRK                  
$19BE  00            BRK                  
$19BF  F2            DCB    $f2           ; Unknown opcode
$19C0  F2            DCB    $f2           ; Unknown opcode
$19C1  F2            DCB    $f2           ; Unknown opcode
$19C2  F2            DCB    $f2           ; Unknown opcode
$19C3  10 05         BPL    $19ca         
$19C5  F2            DCB    $f2           ; Unknown opcode
$19C6  02            DCB    $02           ; Unknown opcode
$19C7  F2            DCB    $f2           ; Unknown opcode
$19C8  F2            DCB    $f2           ; Unknown opcode
$19C9  0A            ASL    A             
$19CA  F2            DCB    $f2           ; Unknown opcode
$19CB  0B            DCB    $0b           ; Unknown opcode
$19CC  F2            DCB    $f2           ; Unknown opcode
$19CD  01 F2         ORA    ($f2,X)       
$19CF  F2            DCB    $f2           ; Unknown opcode
$19D0  02            DCB    $02           ; Unknown opcode
$19D1  12            DCB    $12           ; Unknown opcode
$19D2  F2            DCB    $f2           ; Unknown opcode
$19D3  18            CLC                  
$19D4  15 F2         ORA    $f2,X         
$19D6  01 F2         ORA    ($f2,X)       
$19D8  18            CLC                  
$19D9  00            BRK                  
$19DA  FC            DCB    $fc           ; Unknown opcode
$19DB  F7            DCB    $f7           ; Unknown opcode
$19DC  70 00         BVS    $19de         
$19DE  FB            DCB    $fb           ; Unknown opcode
$19DF  F6 70         INC    $70,X         
$19E1  00            BRK                  
$19E2  FD F8 70      SBC    $70f8,X       
$19E5  00            BRK                  
$19E6  FB            DCB    $fb           ; Unknown opcode
$19E7  F6 70         INC    $70,X         
$19E9  00            BRK                  
$19EA  FB            DCB    $fb           ; Unknown opcode
$19EB  F7            DCB    $f7           ; Unknown opcode
$19EC  70 00         BVS    $19ee         
$19EE  FC            DCB    $fc           ; Unknown opcode
$19EF  F9 70 00      SBC    $0070,Y       
$19F2  FB            DCB    $fb           ; Unknown opcode
$19F3  F8            SED                  
$19F4  70 00         BVS    $19f6         
$19F6  FD F9 70      SBC    $70f9,X       
$19F9  00            BRK                  
$19FA  FD FA 70      SBC    $70fa,X       
$19FD  00            BRK                  
$19FE  F9 F5 70      SBC    $70f5,Y       
$1A01  00            BRK                  
$1A02  FA            DCB    $fa           ; Unknown opcode
$1A03  F6 70         INC    $70,X         
$1A05  00            BRK                  
$1A06  FE F8 70      INC    $70f8,X       
$1A09  00            BRK                  
$1A0A  FE F9 F5      INC    $f5f9,X       
$1A0D  70 00         BVS    $1a0f         
$1A0F  FB            DCB    $fb           ; Unknown opcode
$1A10  F9 70 00      SBC    $0070,Y       
$1A13  FE F9 70      INC    $70f9,X       
$1A16  00            BRK                  
$1A17  FF            DCB    $ff           ; Unknown opcode
$1A18  FD F8 70      SBC    $70f8,X       
$1A1B  03            DCB    $03           ; Unknown opcode
$1A1C  04            DCB    $04           ; Unknown opcode
$1A1D  7F            DCB    $7f           ; Unknown opcode
$1A1E  70 9B         BVS    $19bb         
$1A20  B3            DCB    $b3           ; Unknown opcode
$1A21  1A            DCB    $1a           ; Unknown opcode
$1A22  1A            DCB    $1a           ; Unknown opcode
$1A23  1A            DCB    $1a           ; Unknown opcode
$1A24  D1 D5         CMP    ($d5),Y       
$1A26  F7            DCB    $f7           ; Unknown opcode
$1A27  97            DCB    $97           ; Unknown opcode
$1A28  EC 57 BA      CPX    $ba57         
$1A2B  3B            DCB    $3b           ; Unknown opcode
$1A2C  FC            DCB    $fc           ; Unknown opcode
$1A2D  AE 30 47      LDX    $4730         
$1A30  5E 75 28      LSR    $2875,X       
$1A33  4C 6E 80      JMP    $806e         
$1A36  99 A9 CB      STA    $cba9,Y       
$1A39  2E 99 BA      ROL    $ba99         
$1A3C  DB            DCB    $db           ; Unknown opcode
$1A3D  A7            DCB    $a7           ; Unknown opcode
$1A3E  B9 CD 25      LDA    $25cd,Y       
$1A41  F3            DCB    $f3           ; Unknown opcode
$1A42  B1 62         LDA    ($62),Y       
$1A44  AD B9 C0      LDA    $c0b9         
$1A47  E1 31         SBC    ($31,X)       
$1A49  AF            DCB    $af           ; Unknown opcode
$1A4A  30 1A         BMI    $1a66         
$1A4C  1A            DCB    $1a           ; Unknown opcode
$1A4D  1A            DCB    $1a           ; Unknown opcode
$1A4E  1B            DCB    $1b           ; Unknown opcode
$1A4F  1B            DCB    $1b           ; Unknown opcode
$1A50  1C            DCB    $1c           ; Unknown opcode
$1A51  1C            DCB    $1c           ; Unknown opcode
$1A52  1D 1D 1E      ORA    $1e1d,X       
$1A55  1F            DCB    $1f           ; Unknown opcode
$1A56  1F            DCB    $1f           ; Unknown opcode
$1A57  1F            DCB    $1f           ; Unknown opcode
$1A58  1F            DCB    $1f           ; Unknown opcode
$1A59  20 20 20      JSR    $2020         
$1A5C  20 20 20      JSR    $2020         
$1A5F  20 21 21      JSR    $2121         
$1A62  21 21         AND    ($21,X)       
$1A64  22            DCB    $22           ; Unknown opcode
$1A65  22            DCB    $22           ; Unknown opcode
$1A66  22            DCB    $22           ; Unknown opcode
$1A67  23            DCB    $23           ; Unknown opcode
$1A68  23            DCB    $23           ; Unknown opcode
$1A69  24 25         BIT    $25           
$1A6B  25 25         AND    $25           
$1A6D  25 25         AND    $25           
$1A6F  26 26         ROL    $26           
$1A71  27            DCB    $27           ; Unknown opcode
$1A72  A0 0E         LDY    #$0e          
$1A74  0F            DCB    $0f           ; Unknown opcode
$1A75  0F            DCB    $0f           ; Unknown opcode
$1A76  0F            DCB    $0f           ; Unknown opcode
$1A77  0F            DCB    $0f           ; Unknown opcode
$1A78  11 01         ORA    ($01),Y       
$1A7A  05 01         ORA    $01           
$1A7C  04            DCB    $04           ; Unknown opcode
$1A7D  AC 02 03      LDY    $0302         
$1A80  A0 13         LDY    #$13          
$1A82  14            DCB    $14           ; Unknown opcode
$1A83  13            DCB    $13           ; Unknown opcode
$1A84  15 0E         ORA    $0e,X         
$1A86  11 01         ORA    ($01),Y       
$1A88  05 01         ORA    $01           
$1A8A  04            DCB    $04           ; Unknown opcode
$1A8B  AC 02 1B      LDY    $1b02         
$1A8E  A0 13         LDY    #$13          
$1A90  14            DCB    $14           ; Unknown opcode
$1A91  13            DCB    $13           ; Unknown opcode
$1A92  15 1C         ORA    $1c,X         
$1A94  1C            DCB    $1c           ; Unknown opcode
$1A95  1C            DCB    $1c           ; Unknown opcode
$1A96  1C            DCB    $1c           ; Unknown opcode
$1A97  AC 02 1F      LDY    $1f02         
$1A9A  20 FF 00      JSR    $00ff         
$1A9D  A0 00         LDY    #$00          
$1A9F  12            DCB    $12           ; Unknown opcode
$1AA0  06 06         ASL    $06           
$1AA2  06 07         ASL    $07           
$1AA4  25 25         AND    $25           
$1AA6  16 17         ASL    $17,X         
$1AA8  06 06         ASL    $06           
$1AAA  18            CLC                  
$1AAB  25 25         AND    $25           
$1AAD  06 06         ASL    $06           
$1AAF  06 06         ASL    $06           
$1AB1  1D 21 FF      ORA    $ff21,X       
$1AB4  00            BRK                  
$1AB5  A0 0A         LDY    #$0a          
$1AB7  0A            ASL    A             
$1AB8  0B            DCB    $0b           ; Unknown opcode
$1AB9  0C            DCB    $0c           ; Unknown opcode
$1ABA  A2 0A         LDX    #$0a          
$1ABC  A0 10         LDY    #$10          
$1ABE  08            PHP                  
$1ABF  09 19         ORA    #$19          
$1AC1  AC 0D A0      LDY    $a00d         
$1AC4  0B            DCB    $0b           ; Unknown opcode
$1AC5  10 08         BPL    $1acf         
$1AC7  09 1A         ORA    #$1a          
$1AC9  AC 0D 23      LDY    $230d         
$1ACC  24 26         BIT    $26           
$1ACE  A0 1E         LDY    #$1e          
$1AD0  22            DCB    $22           ; Unknown opcode
$1AD1  FF            DCB    $ff           ; Unknown opcode
$1AD2  00            BRK                  
$1AD3  8F            DCB    $8f           ; Unknown opcode
$1AD4  00            BRK                  
$1AD5  00            BRK                  
$1AD6  7F            DCB    $7f           ; Unknown opcode
$1AD7  C4 A0         CPY    $a0           
$1AD9  81 39         STA    ($39,X)       
$1ADB  39 39 C4      AND    $c439,Y       
$1ADE  A9 39         LDA    #$39          
$1AE0  C4 A0         CPY    $a0           
$1AE2  83            DCB    $83           ; Unknown opcode
$1AE3  39 80 39      AND    $3980,Y       
$1AE6  00            BRK                  
$1AE7  83            DCB    $83           ; Unknown opcode
$1AE8  39 C5 81      AND    $81c5,Y       
$1AEB  3A            DCB    $3a           ; Unknown opcode
$1AEC  C5 A9         CMP    $a9           
$1AEE  3A            DCB    $3a           ; Unknown opcode
$1AEF  C4 A0         CPY    $a0           
$1AF1  85 39         STA    $39           
$1AF3  C4 A9         CPY    $a9           
$1AF5  81 39         STA    ($39,X)       
$1AF7  39 7F CA      AND    $ca7f,Y       
$1AFA  A0 81         LDY    #$81          
$1AFC  30 30         BMI    $1b2e         
$1AFE  80            DCB    $80           ; Unknown opcode
$1AFF  30 00         BMI    $1b01         
$1B01  CA            DEX                  
$1B02  A9 81         LDA    #$81          
$1B04  30 CA         BMI    $1ad0         
$1B06  A0 83         LDY    #$83          
$1B08  30 CB         BMI    $1ad5         
$1B0A  80            DCB    $80           ; Unknown opcode
$1B0B  2B            DCB    $2b           ; Unknown opcode
$1B0C  00            BRK                  
$1B0D  C4 85         CPY    $85           
$1B0F  2D C4 A9      AND    $a9c4         
$1B12  81 2D         STA    ($2d,X)       
$1B14  D0 2D         BNE    $1b43         
$1B16  2D C4 A0      AND    $a0c4         
$1B19  80            DCB    $80           ; Unknown opcode
$1B1A  2D 00 81      AND    $8100         
$1B1D  2D C4 A9      AND    $a9c4         
$1B20  2D CA A0      AND    $a0ca         
$1B23  2E 2E 80      ROL    $802e         
$1B26  2E 00 CA      ROL    $ca00         
$1B29  A9 81         LDA    #$81          
$1B2B  2E CA A0      ROL    $a0ca         
$1B2E  83            DCB    $83           ; Unknown opcode
$1B2F  2E CB 80      ROL    $80cb         
$1B32  29 00         AND    #$00          
$1B34  C4 85         CPY    $85           
$1B36  2B            DCB    $2b           ; Unknown opcode
$1B37  C4 A9         CPY    $a9           
$1B39  81 2B         STA    ($2b,X)       
$1B3B  D0 2B         BNE    $1b68         
$1B3D  2B            DCB    $2b           ; Unknown opcode
$1B3E  C4 A0         CPY    $a0           
$1B40  80            DCB    $80           ; Unknown opcode
$1B41  2B            DCB    $2b           ; Unknown opcode
$1B42  00            BRK                  
$1B43  81 2B         STA    ($2b,X)       
$1B45  C4 A9         CPY    $a9           
$1B47  2B            DCB    $2b           ; Unknown opcode
$1B48  CA            DEX                  
$1B49  A0 2D         LDY    #$2d          
$1B4B  2D 80 2D      AND    $2d80         
$1B4E  00            BRK                  
$1B4F  CA            DEX                  
$1B50  A9 81         LDA    #$81          
$1B52  2D CA A0      AND    $a0ca         
$1B55  83            DCB    $83           ; Unknown opcode
$1B56  2D CB 80      AND    $80cb         
$1B59  28            PLP                  
$1B5A  00            BRK                  
$1B5B  C6 85         DEC    $85           
$1B5D  29 80         AND    #$80          
$1B5F  29 00         AND    #$00          
$1B61  C6 A9         DEC    $a9           
$1B63  81 29         STA    ($29,X)       
$1B65  C6 A0         DEC    $a0           
$1B67  80            DCB    $80           ; Unknown opcode
$1B68  29 00         AND    #$00          
$1B6A  81 29         STA    ($29,X)       
$1B6C  C6 A9         DEC    $a9           
$1B6E  29 29         AND    #$29          
$1B70  CA            DEX                  
$1B71  A0 2B         LDY    #$2b          
$1B73  2B            DCB    $2b           ; Unknown opcode
$1B74  80            DCB    $80           ; Unknown opcode
$1B75  2B            DCB    $2b           ; Unknown opcode
$1B76  00            BRK                  
$1B77  CA            DEX                  
$1B78  A9 81         LDA    #$81          
$1B7A  2B            DCB    $2b           ; Unknown opcode
$1B7B  CA            DEX                  
$1B7C  A0 83         LDY    #$83          
$1B7E  2B            DCB    $2b           ; Unknown opcode
$1B7F  CB            DCB    $cb           ; Unknown opcode
$1B80  80            DCB    $80           ; Unknown opcode
$1B81  26 00         ROL    $00           
$1B83  CC 85 29      CPY    $2985         
$1B86  CC A9 81      CPY    $81a9         
$1B89  29 D0         AND    #$d0          
$1B8B  29 29         AND    #$29          
$1B8D  CC A0 80      CPY    $80a0         
$1B90  29 00         AND    #$00          
$1B92  29 00         AND    #$00          
$1B94  CC A9 81      CPY    $81a9         
$1B97  29 7F         AND    #$7f          
$1B99  CB            DCB    $cb           ; Unknown opcode
$1B9A  A9 81         LDA    #$81          
$1B9C  29 CB         AND    #$cb          
$1B9E  A0 80         LDY    #$80          
$1BA0  29 00         AND    #$00          
$1BA2  83            DCB    $83           ; Unknown opcode
$1BA3  29 80         AND    #$80          
$1BA5  29 00         AND    #$00          
$1BA7  CB            DCB    $cb           ; Unknown opcode
$1BA8  A9 81         LDA    #$81          
$1BAA  29 CB         AND    #$cb          
$1BAC  A0 83         LDY    #$83          
$1BAE  29 80         AND    #$80          
$1BB0  29 00         AND    #$00          
$1BB2  CB            DCB    $cb           ; Unknown opcode
$1BB3  A9 81         LDA    #$81          
$1BB5  29 C8         AND    #$c8          
$1BB7  A0 80         LDY    #$80          
$1BB9  2B            DCB    $2b           ; Unknown opcode
$1BBA  00            BRK                  
$1BBB  CD 85 2D      CMP    $2d85         
$1BBE  CD A9 81      CMP    $81a9         
$1BC1  2D 2D CB      AND    $cb2d         
$1BC4  A0 80         LDY    #$80          
$1BC6  2B            DCB    $2b           ; Unknown opcode
$1BC7  00            BRK                  
$1BC8  2B            DCB    $2b           ; Unknown opcode
$1BC9  00            BRK                  
$1BCA  83            DCB    $83           ; Unknown opcode
$1BCB  2B            DCB    $2b           ; Unknown opcode
$1BCC  80            DCB    $80           ; Unknown opcode
$1BCD  2B            DCB    $2b           ; Unknown opcode
$1BCE  00            BRK                  
$1BCF  CB            DCB    $cb           ; Unknown opcode
$1BD0  A9 2B         LDA    #$2b          
$1BD2  00            BRK                  
$1BD3  CB            DCB    $cb           ; Unknown opcode
$1BD4  A0 2B         LDY    #$2b          
$1BD6  00            BRK                  
$1BD7  83            DCB    $83           ; Unknown opcode
$1BD8  2B            DCB    $2b           ; Unknown opcode
$1BD9  C8            INY                  
$1BDA  81 2D         STA    ($2d,X)       
$1BDC  C8            INY                  
$1BDD  A9 2D         LDA    #$2d          
$1BDF  CE A0 2E      DEC    $2ea0         
$1BE2  CE A9 2E      DEC    $2ea9         
$1BE5  CF            DCB    $cf           ; Unknown opcode
$1BE6  A0 83         LDY    #$83          
$1BE8  30 CF         BMI    $1bb9         
$1BEA  A9 81         LDA    #$81          
$1BEC  30 7F         BMI    $1c6d         
$1BEE  C6 A9         DEC    $a9           
$1BF0  81 35         STA    ($35,X)       
$1BF2  C6 A0         DEC    $a0           
$1BF4  80            DCB    $80           ; Unknown opcode
$1BF5  35 00         AND    $00,X         
$1BF7  35 00         AND    $00,X         
$1BF9  83            DCB    $83           ; Unknown opcode
$1BFA  35 80         AND    $80,X         
$1BFC  35 00         AND    $00,X         
$1BFE  C6 A9         DEC    $a9           
$1C00  81 35         STA    ($35,X)       
$1C02  C6 A0         DEC    $a0           
$1C04  80            DCB    $80           ; Unknown opcode
$1C05  35 00         AND    $00,X         
$1C07  C7            DCB    $c7           ; Unknown opcode
$1C08  83            DCB    $83           ; Unknown opcode
$1C09  37            DCB    $37           ; Unknown opcode
$1C0A  81 37         STA    ($37,X)       
$1C0C  C7            DCB    $c7           ; Unknown opcode
$1C0D  A9 37         LDA    #$37          
$1C0F  C6 A0         DEC    $a0           
$1C11  86 35         STX    $35           
$1C13  80            DCB    $80           ; Unknown opcode
$1C14  00            BRK                  
$1C15  C9 34         CMP    #$34          
$1C17  00            BRK                  
$1C18  34            DCB    $34           ; Unknown opcode
$1C19  00            BRK                  
$1C1A  83            DCB    $83           ; Unknown opcode
$1C1B  34            DCB    $34           ; Unknown opcode
$1C1C  81 34         STA    ($34,X)       
$1C1E  C9 A9         CMP    #$a9          
$1C20  34            DCB    $34           ; Unknown opcode
$1C21  C9 A0         CMP    #$a0          
$1C23  80            DCB    $80           ; Unknown opcode
$1C24  34            DCB    $34           ; Unknown opcode
$1C25  00            BRK                  
$1C26  CA            DEX                  
$1C27  83            DCB    $83           ; Unknown opcode
$1C28  35 81         AND    $81,X         
$1C2A  35 CA         AND    $ca,X         
$1C2C  A9 35         LDA    #$35          
$1C2E  C9 A0         CMP    #$a0          
$1C30  83            DCB    $83           ; Unknown opcode
$1C31  34            DCB    $34           ; Unknown opcode
$1C32  80            DCB    $80           ; Unknown opcode
$1C33  34            DCB    $34           ; Unknown opcode
$1C34  00            BRK                  
$1C35  C6 81         DEC    $81           
$1C37  30 C6         BMI    $1bff         
$1C39  A9 30         LDA    #$30          
$1C3B  C6 A0         DEC    $a0           
$1C3D  83            DCB    $83           ; Unknown opcode
$1C3E  30 C4         BMI    $1c04         
$1C40  80            DCB    $80           ; Unknown opcode
$1C41  32            DCB    $32           ; Unknown opcode
$1C42  00            BRK                  
$1C43  85 32         STA    $32           
$1C45  C4 A9         CPY    $a9           
$1C47  81 32         STA    ($32,X)       
$1C49  D0 32         BNE    $1c7d         
$1C4B  32            DCB    $32           ; Unknown opcode
$1C4C  D0 32         BNE    $1c80         
$1C4E  D0 32         BNE    $1c82         
$1C50  32            DCB    $32           ; Unknown opcode
$1C51  D0 32         BNE    $1c85         
$1C53  D0 32         BNE    $1c87         
$1C55  32            DCB    $32           ; Unknown opcode
$1C56  D0 32         BNE    $1c8a         
$1C58  7F            DCB    $7f           ; Unknown opcode
$1C59  C6 A0         DEC    $a0           
$1C5B  81 35         STA    ($35,X)       
$1C5D  35 35         AND    $35,X         
$1C5F  C6 A9         DEC    $a9           
$1C61  35 C6         AND    $c6,X         
$1C63  A0 83         LDY    #$83          
$1C65  35 80         AND    $80,X         
$1C67  35 00         AND    $00,X         
$1C69  C7            DCB    $c7           ; Unknown opcode
$1C6A  83            DCB    $83           ; Unknown opcode
$1C6B  37            DCB    $37           ; Unknown opcode
$1C6C  80            DCB    $80           ; Unknown opcode
$1C6D  37            DCB    $37           ; Unknown opcode
$1C6E  00            BRK                  
$1C6F  C7            DCB    $c7           ; Unknown opcode
$1C70  A9 37         LDA    #$37          
$1C72  00            BRK                  
$1C73  C6 A0         DEC    $a0           
$1C75  86 35         STX    $35           
$1C77  80            DCB    $80           ; Unknown opcode
$1C78  00            BRK                  
$1C79  C8            INY                  
$1C7A  32            DCB    $32           ; Unknown opcode
$1C7B  00            BRK                  
$1C7C  C9 81         CMP    #$81          
$1C7E  34            DCB    $34           ; Unknown opcode
$1C7F  34            DCB    $34           ; Unknown opcode
$1C80  34            DCB    $34           ; Unknown opcode
$1C81  C9 A9         CMP    #$a9          
$1C83  80            DCB    $80           ; Unknown opcode
$1C84  34            DCB    $34           ; Unknown opcode
$1C85  00            BRK                  
$1C86  C9 A0         CMP    #$a0          
$1C88  83            DCB    $83           ; Unknown opcode
$1C89  34            DCB    $34           ; Unknown opcode
$1C8A  80            DCB    $80           ; Unknown opcode
$1C8B  34            DCB    $34           ; Unknown opcode
$1C8C  00            BRK                  
$1C8D  CA            DEX                  
$1C8E  83            DCB    $83           ; Unknown opcode
$1C8F  35 81         AND    $81,X         
$1C91  35 CA         AND    $ca,X         
$1C93  A9 80         LDA    #$80          
$1C95  35 00         AND    $00,X         
$1C97  C9 A0         CMP    #$a0          
$1C99  83            DCB    $83           ; Unknown opcode
$1C9A  34            DCB    $34           ; Unknown opcode
$1C9B  80            DCB    $80           ; Unknown opcode
$1C9C  34            DCB    $34           ; Unknown opcode
$1C9D  00            BRK                  
$1C9E  C6 83         DEC    $83           
$1CA0  30 30         BMI    $1cd2         
$1CA2  C4 80         CPY    $80           
$1CA4  32            DCB    $32           ; Unknown opcode
$1CA5  00            BRK                  
$1CA6  85 32         STA    $32           
$1CA8  C4 A9         CPY    $a9           
$1CAA  81 32         STA    ($32,X)       
$1CAC  D0 32         BNE    $1ce0         
$1CAE  32            DCB    $32           ; Unknown opcode
$1CAF  D0 32         BNE    $1ce3         
$1CB1  D0 32         BNE    $1ce5         
$1CB3  32            DCB    $32           ; Unknown opcode
$1CB4  D0 32         BNE    $1ce8         
$1CB6  D0 32         BNE    $1cea         
$1CB8  32            DCB    $32           ; Unknown opcode
$1CB9  D0 32         BNE    $1ced         
$1CBB  7F            DCB    $7f           ; Unknown opcode
$1CBC  A1 83         LDA    ($83,X)       
$1CBE  11 A6         ORA    ($a6),Y       
$1CC0  81 3C         STA    ($3c,X)       
$1CC2  A7            DCB    $a7           ; Unknown opcode
$1CC3  45 A2         EOR    $a2           
$1CC5  18            CLC                  
$1CC6  A7            DCB    $a7           ; Unknown opcode
$1CC7  48            PHA                  
$1CC8  A4 80         LDY    $80           
$1CCA  11 00         ORA    ($00),Y       
$1CCC  A1 83         LDA    ($83,X)       
$1CCE  11 81         ORA    ($81),Y       
$1CD0  00            BRK                  
$1CD1  A6 3C         LDX    $3c           
$1CD3  A7            DCB    $a7           ; Unknown opcode
$1CD4  43            DCB    $43           ; Unknown opcode
$1CD5  A2 18         LDX    #$18          
$1CD7  A7            DCB    $a7           ; Unknown opcode
$1CD8  48            PHA                  
$1CD9  A4 83         LDY    $83           
$1CDB  15 A1         ORA    $a1,X         
$1CDD  1A            DCB    $1a           ; Unknown opcode
$1CDE  A6 81         LDX    $81           
$1CE0  39 A7 41      AND    $41a7,Y       
$1CE3  A2 18         LDX    #$18          
$1CE5  A7            DCB    $a7           ; Unknown opcode
$1CE6  48            PHA                  
$1CE7  A4 80         LDY    $80           
$1CE9  1A            DCB    $1a           ; Unknown opcode
$1CEA  00            BRK                  
$1CEB  A1 83         LDA    ($83,X)       
$1CED  1A            DCB    $1a           ; Unknown opcode
$1CEE  81 00         STA    ($00,X)       
$1CF0  A6 39         LDX    $39           
$1CF2  A7            DCB    $a7           ; Unknown opcode
$1CF3  3E A2 18      ROL    $18a2,X       
$1CF6  A7            DCB    $a7           ; Unknown opcode
$1CF7  48            PHA                  
$1CF8  A4 1F         LDY    $1f           
$1CFA  90 13         BCC    $1d0f         
$1CFC  00            BRK                  
$1CFD  A1 83         LDA    ($83,X)       
$1CFF  15 A6         ORA    $a6,X         
$1D01  81 3C         STA    ($3c,X)       
$1D03  A7            DCB    $a7           ; Unknown opcode
$1D04  40            RTI                  
$1D05  A2 18         LDX    #$18          
$1D07  A7            DCB    $a7           ; Unknown opcode
$1D08  48            PHA                  
$1D09  A4 80         LDY    $80           
$1D0B  15 00         ORA    $00,X         
$1D0D  A1 83         LDA    ($83,X)       
$1D0F  15 81         ORA    $81,X         
$1D11  00            BRK                  
$1D12  A6 34         LDX    $34           
$1D14  A7            DCB    $a7           ; Unknown opcode
$1D15  3C            DCB    $3c           ; Unknown opcode
$1D16  A2 18         LDX    #$18          
$1D18  A7            DCB    $a7           ; Unknown opcode
$1D19  45 A3         EOR    $a3           
$1D1B  24 A1         BIT    $a1           
$1D1D  15 83         ORA    $83,X         
$1D1F  16 A6         ASL    $a6,X         
$1D21  81 3A         STA    ($3a,X)       
$1D23  A7            DCB    $a7           ; Unknown opcode
$1D24  41 A2         EOR    ($a2,X)       
$1D26  18            CLC                  
$1D27  A7            DCB    $a7           ; Unknown opcode
$1D28  4A            LSR    A             
$1D29  A4 16         LDY    $16           
$1D2B  A1 83         LDA    ($83,X)       
$1D2D  0A            ASL    A             
$1D2E  81 00         STA    ($00,X)       
$1D30  A6 35         LDX    $35           
$1D32  A7            DCB    $a7           ; Unknown opcode
$1D33  3E A2 18      ROL    $18a2,X       
$1D36  A7            DCB    $a7           ; Unknown opcode
$1D37  46 A4         LSR    $a4           
$1D39  18            CLC                  
$1D3A  91 1A         STA    ($1a),Y       
$1D3C  7F            DCB    $7f           ; Unknown opcode
$1D3D  A1 83         LDA    ($83,X)       
$1D3F  18            CLC                  
$1D40  A6 81         LDX    $81           
$1D42  43            DCB    $43           ; Unknown opcode
$1D43  A7            DCB    $a7           ; Unknown opcode
$1D44  48            PHA                  
$1D45  A2 83         LDX    #$83          
$1D47  18            CLC                  
$1D48  A4 80         LDY    $80           
$1D4A  18            CLC                  
$1D4B  00            BRK                  
$1D4C  A1 83         LDA    ($83,X)       
$1D4E  11 80         ORA    ($80),Y       
$1D50  1D 00 A6      ORA    $a600,X       
$1D53  81 43         STA    ($43,X)       
$1D55  A7            DCB    $a7           ; Unknown opcode
$1D56  45 A2         EOR    $a2           
$1D58  18            CLC                  
$1D59  A1 15         LDA    ($15,X)       
$1D5B  A4 18         LDY    $18           
$1D5D  91 17         STA    ($17),Y       
$1D5F  A1 83         LDA    ($83,X)       
$1D61  16 A6         ASL    $a6,X         
$1D63  81 41         STA    ($41,X)       
$1D65  A7            DCB    $a7           ; Unknown opcode
$1D66  46 A2         LSR    $a2           
$1D68  83            DCB    $83           ; Unknown opcode
$1D69  18            CLC                  
$1D6A  A4 80         LDY    $80           
$1D6C  16 00         ASL    $00,X         
$1D6E  A1 81         LDA    ($81,X)       
$1D70  1B            DCB    $1b           ; Unknown opcode
$1D71  91 16         STA    ($16),Y       
$1D73  0F            DCB    $0f           ; Unknown opcode
$1D74  A7            DCB    $a7           ; Unknown opcode
$1D75  41 A6         EOR    ($a6,X)       
$1D77  43            DCB    $43           ; Unknown opcode
$1D78  A2 18         LDX    #$18          
$1D7A  A1 1F         LDA    ($1f,X)       
$1D7C  A4 1B         LDY    $1b           
$1D7E  91 1A         STA    ($1a),Y       
$1D80  A1 83         LDA    ($83,X)       
$1D82  19 A6 81      ORA    $81a6,Y       
$1D85  40            RTI                  
$1D86  A1 15         LDA    ($15,X)       
$1D88  A2 18         LDX    #$18          
$1D8A  A4 10         LDY    $10           
$1D8C  95 0E         STA    $0e,X         
$1D8E  81 1A         STA    ($1a,X)       
$1D90  A6 40         LDX    $40           
$1D92  A7            DCB    $a7           ; Unknown opcode
$1D93  41 A2         EOR    ($a2,X)       
$1D95  18            CLC                  
$1D96  A1 15         LDA    ($15,X)       
$1D98  A3            DCB    $a3           ; Unknown opcode
$1D99  24 A1         BIT    $a1           
$1D9B  80            DCB    $80           ; Unknown opcode
$1D9C  15 00         ORA    $00,X         
$1D9E  83            DCB    $83           ; Unknown opcode
$1D9F  17            DCB    $17           ; Unknown opcode
$1DA0  A6 81         LDX    $81           
$1DA2  3E A7 43      ROL    $43a7,X       
$1DA5  A2 83         LDX    #$83          
$1DA7  18            CLC                  
$1DA8  A4 80         LDY    $80           
$1DAA  11 00         ORA    ($00),Y       
$1DAC  A1 85         LDA    ($85,X)       
$1DAE  13            DCB    $13           ; Unknown opcode
$1DAF  A6 81         LDX    $81           
$1DB1  3B            DCB    $3b           ; Unknown opcode
$1DB2  A7            DCB    $a7           ; Unknown opcode
$1DB3  41 A2         EOR    ($a2,X)       
$1DB5  18            CLC                  
$1DB6  A1 80         LDA    ($80,X)       
$1DB8  11 00         ORA    ($00),Y       
$1DBA  A4 81         LDY    $81           
$1DBC  13            DCB    $13           ; Unknown opcode
$1DBD  91 15         STA    ($15),Y       
$1DBF  A1 83         LDA    ($83,X)       
$1DC1  16 A6         ASL    $a6,X         
$1DC3  81 3A         STA    ($3a,X)       
$1DC5  A7            DCB    $a7           ; Unknown opcode
$1DC6  3E A2 18      ROL    $18a2,X       
$1DC9  A7            DCB    $a7           ; Unknown opcode
$1DCA  45 A4         EOR    $a4           
$1DCC  80            DCB    $80           ; Unknown opcode
$1DCD  11 00         ORA    ($00),Y       
$1DCF  A1 85         LDA    ($85,X)       
$1DD1  0A            ASL    A             
$1DD2  A7            DCB    $a7           ; Unknown opcode
$1DD3  81 3A         STA    ($3a,X)       
$1DD5  A6 3E         LDX    $3e           
$1DD7  A2 18         LDX    #$18          
$1DD9  A6 43         LDX    $43           
$1DDB  A3            DCB    $a3           ; Unknown opcode
$1DDC  83            DCB    $83           ; Unknown opcode
$1DDD  24 A1         BIT    $a1           
$1DDF  18            CLC                  
$1DE0  A6 81         LDX    $81           
$1DE2  3C            DCB    $3c           ; Unknown opcode
$1DE3  A7            DCB    $a7           ; Unknown opcode
$1DE4  40            RTI                  
$1DE5  A2 18         LDX    #$18          
$1DE7  A7            DCB    $a7           ; Unknown opcode
$1DE8  45 A4         EOR    $a4           
$1DEA  80            DCB    $80           ; Unknown opcode
$1DEB  13            DCB    $13           ; Unknown opcode
$1DEC  00            BRK                  
$1DED  A1 85         LDA    ($85,X)       
$1DEF  0C            DCB    $0c           ; Unknown opcode
$1DF0  A6 81         LDX    $81           
$1DF2  37            DCB    $37           ; Unknown opcode
$1DF3  A7            DCB    $a7           ; Unknown opcode
$1DF4  3C            DCB    $3c           ; Unknown opcode
$1DF5  B3            DCB    $b3           ; Unknown opcode
$1DF6  18            CLC                  
$1DF7  A7            DCB    $a7           ; Unknown opcode
$1DF8  83            DCB    $83           ; Unknown opcode
$1DF9  43            DCB    $43           ; Unknown opcode
$1DFA  B3            DCB    $b3           ; Unknown opcode
$1DFB  81 18         STA    ($18,X)       
$1DFD  7F            DCB    $7f           ; Unknown opcode
$1DFE  87            DCB    $87           ; Unknown opcode
$1DFF  00            BRK                  
$1E00  A8            TAY                  
$1E01  80            DCB    $80           ; Unknown opcode
$1E02  37            DCB    $37           ; Unknown opcode
$1E03  C0 92         CPY    #$92          
$1E05  39 C3 81      AND    $81c3,Y       
$1E08  7E 00 83      ROR    $8300,X       
$1E0B  37            DCB    $37           ; Unknown opcode
$1E0C  00            BRK                  
$1E0D  35 C3         AND    $c3,X         
$1E0F  81 7E         STA    ($7e,X)       
$1E11  00            BRK                  
$1E12  83            DCB    $83           ; Unknown opcode
$1E13  34            DCB    $34           ; Unknown opcode
$1E14  C0 93         CPY    #$93          
$1E16  35 00         AND    $00,X         
$1E18  C1 37         CMP    ($37,X)       
$1E1A  00            BRK                  
$1E1B  80            DCB    $80           ; Unknown opcode
$1E1C  32            DCB    $32           ; Unknown opcode
$1E1D  C0 94         CPY    #$94          
$1E1F  34            DCB    $34           ; Unknown opcode
$1E20  81 00         STA    ($00,X)       
$1E22  C1 83         CMP    ($83,X)       
$1E24  30 C3         BMI    $1de9         
$1E26  7E 89 00      ROR    $0089,X       
$1E29  80            DCB    $80           ; Unknown opcode
$1E2A  2D 00 83      AND    $8300         
$1E2D  30 C0         BMI    $1def         
$1E2F  93            DCB    $93           ; Unknown opcode
$1E30  32            DCB    $32           ; Unknown opcode
$1E31  C1 34         CMP    ($34,X)       
$1E33  C0 91         CPY    #$91          
$1E35  35 C3         AND    $c3,X         
$1E37  85 7E         STA    $7e           
$1E39  C1 81         CMP    ($81,X)       
$1E3B  32            DCB    $32           ; Unknown opcode
$1E3C  83            DCB    $83           ; Unknown opcode
$1E3D  00            BRK                  
$1E3E  AA            TAX                  
$1E3F  81 3C         STA    ($3c,X)       
$1E41  90 3E         BCC    $1e81         
$1E43  00            BRK                  
$1E44  43            DCB    $43           ; Unknown opcode
$1E45  00            BRK                  
$1E46  D1 35         CMP    ($35),Y       
$1E48  00            BRK                  
$1E49  81 41         STA    ($41,X)       
$1E4B  D1 80         CMP    ($80),Y       
$1E4D  3A            DCB    $3a           ; Unknown opcode
$1E4E  00            BRK                  
$1E4F  3E 00 81      ROL    $8100,X       
$1E52  3C            DCB    $3c           ; Unknown opcode
$1E53  91 3E         STA    ($3e),Y       
$1E55  91 3C         STA    ($3c),Y       
$1E57  D1 80         CMP    ($80),Y       
$1E59  35 88         AND    $88,X         
$1E5B  00            BRK                  
$1E5C  A8            TAY                  
$1E5D  80            DCB    $80           ; Unknown opcode
$1E5E  37            DCB    $37           ; Unknown opcode
$1E5F  C0 92         CPY    #$92          
$1E61  39 C3 81      AND    $81c3,Y       
$1E64  7E 00 83      ROR    $8300,X       
$1E67  3C            DCB    $3c           ; Unknown opcode
$1E68  00            BRK                  
$1E69  35 C3         AND    $c3,X         
$1E6B  81 7E         STA    ($7e,X)       
$1E6D  00            BRK                  
$1E6E  83            DCB    $83           ; Unknown opcode
$1E6F  34            DCB    $34           ; Unknown opcode
$1E70  C0 93         CPY    #$93          
$1E72  35 00         AND    $00,X         
$1E74  C1 37         CMP    ($37,X)       
$1E76  00            BRK                  
$1E77  39 00 80      AND    $8000,Y       
$1E7A  36 C0         ROL    $c0,X         
$1E7C  94 37         STY    $37,X         
$1E7E  C3            DCB    $c3           ; Unknown opcode
$1E7F  81 7E         STA    ($7e,X)       
$1E81  89            DCB    $89           ; Unknown opcode
$1E82  00            BRK                  
$1E83  80            DCB    $80           ; Unknown opcode
$1E84  30 00         BMI    $1e86         
$1E86  35 C0         AND    $c0,X         
$1E88  92            DCB    $92           ; Unknown opcode
$1E89  37            DCB    $37           ; Unknown opcode
$1E8A  93            DCB    $93           ; Unknown opcode
$1E8B  39 C1 34      AND    $34c1,Y       
$1E8E  35 C3         AND    $c3,X         
$1E90  7E 81 3E      ROR    $3e81,X       
$1E93  83            DCB    $83           ; Unknown opcode
$1E94  00            BRK                  
$1E95  AA            TAX                  
$1E96  81 3C         STA    ($3c,X)       
$1E98  90 3E         BCC    $1ed8         
$1E9A  00            BRK                  
$1E9B  45 00         EOR    $00           
$1E9D  D1 3A         CMP    ($3a),Y       
$1E9F  00            BRK                  
$1EA0  81 41         STA    ($41,X)       
$1EA2  90 3E         BCC    $1ee2         
$1EA4  00            BRK                  
$1EA5  D1 35         CMP    ($35),Y       
$1EA7  00            BRK                  
$1EA8  A8            TAY                  
$1EA9  3C            DCB    $3c           ; Unknown opcode
$1EAA  C0 92         CPY    #$92          
$1EAC  3E 93 3C      ROL    $3c93,X       
$1EAF  7F            DCB    $7f           ; Unknown opcode
$1EB0  C3            DCB    $c3           ; Unknown opcode
$1EB1  84 7E         STY    $7e           
$1EB3  82            DCB    $82           ; Unknown opcode
$1EB4  00            BRK                  
$1EB5  A8            TAY                  
$1EB6  80            DCB    $80           ; Unknown opcode
$1EB7  39 C0 92      AND    $92c0,Y       
$1EBA  3A            DCB    $3a           ; Unknown opcode
$1EBB  93            DCB    $93           ; Unknown opcode
$1EBC  39 C3 7E      AND    $7ec3,Y       
$1EBF  00            BRK                  
$1EC0  80            DCB    $80           ; Unknown opcode
$1EC1  35 C0         AND    $c0,X         
$1EC3  92            DCB    $92           ; Unknown opcode
$1EC4  37            DCB    $37           ; Unknown opcode
$1EC5  93            DCB    $93           ; Unknown opcode
$1EC6  35 C3         AND    $c3,X         
$1EC8  7E 00 80      ROR    $8000,X       
$1ECB  30 C0         BMI    $1e8d         
$1ECD  92            DCB    $92           ; Unknown opcode
$1ECE  32            DCB    $32           ; Unknown opcode
$1ECF  93            DCB    $93           ; Unknown opcode
$1ED0  2E C3 84      ROL    $84c3         
$1ED3  7E 88 00      ROR    $0088,X       
$1ED6  80            DCB    $80           ; Unknown opcode
$1ED7  2D 00 83      AND    $8300         
$1EDA  31 C0         AND    ($c0),Y       
$1EDC  91 32         STA    ($32),Y       
$1EDE  C1 80         CMP    ($80,X)       
$1EE0  34            DCB    $34           ; Unknown opcode
$1EE1  82            DCB    $82           ; Unknown opcode
$1EE2  00            BRK                  
$1EE3  81 37         STA    ($37,X)       
$1EE5  83            DCB    $83           ; Unknown opcode
$1EE6  35 C3         AND    $c3,X         
$1EE8  7E 81 32      ROR    $3281,X       
$1EEB  80            DCB    $80           ; Unknown opcode
$1EEC  2D 00 37      AND    $3700         
$1EEF  C0 92         CPY    #$92          
$1EF1  39 97 37      AND    $3797,Y       
$1EF4  C3            DCB    $c3           ; Unknown opcode
$1EF5  83            DCB    $83           ; Unknown opcode
$1EF6  7E 85 00      ROR    $0085,X       
$1EF9  80            DCB    $80           ; Unknown opcode
$1EFA  32            DCB    $32           ; Unknown opcode
$1EFB  00            BRK                  
$1EFC  34            DCB    $34           ; Unknown opcode
$1EFD  C0 92         CPY    #$92          
$1EFF  35 91         AND    $91,X         
$1F01  34            DCB    $34           ; Unknown opcode
$1F02  C1 32         CMP    ($32,X)       
$1F04  00            BRK                  
$1F05  30 83         BMI    $1e8a         
$1F07  32            DCB    $32           ; Unknown opcode
$1F08  C3            DCB    $c3           ; Unknown opcode
$1F09  87            DCB    $87           ; Unknown opcode
$1F0A  7E 83 00      ROR    $0083,X       
$1F0D  80            DCB    $80           ; Unknown opcode
$1F0E  32            DCB    $32           ; Unknown opcode
$1F0F  00            BRK                  
$1F10  34            DCB    $34           ; Unknown opcode
$1F11  00            BRK                  
$1F12  34            DCB    $34           ; Unknown opcode
$1F13  C0 92         CPY    #$92          
$1F15  35 91         AND    $91,X         
$1F17  34            DCB    $34           ; Unknown opcode
$1F18  C1 80         CMP    ($80,X)       
$1F1A  32            DCB    $32           ; Unknown opcode
$1F1B  82            DCB    $82           ; Unknown opcode
$1F1C  00            BRK                  
$1F1D  81 30         STA    ($30,X)       
$1F1F  80            DCB    $80           ; Unknown opcode
$1F20  32            DCB    $32           ; Unknown opcode
$1F21  C0 92         CPY    #$92          
$1F23  34            DCB    $34           ; Unknown opcode
$1F24  C3            DCB    $c3           ; Unknown opcode
$1F25  83            DCB    $83           ; Unknown opcode
$1F26  7E 91 32      ROR    $3291,X       
$1F29  90 33         BCC    $1f5e         
$1F2B  90 32         BCC    $1f5f         
$1F2D  93            DCB    $93           ; Unknown opcode
$1F2E  30 C3         BMI    $1ef3         
$1F30  7E 7F AB      ROR    $ab7f,X       
$1F33  81 29         STA    ($29,X)       
$1F35  C2            DCB    $c2           ; Unknown opcode
$1F36  7E 29 83      ROR    $8329,X       
$1F39  35 29         AND    $29,X         
$1F3B  81 29         STA    ($29,X)       
$1F3D  C2            DCB    $c2           ; Unknown opcode
$1F3E  7E 29 29      ROR    $2929,X       
$1F41  35 D2         AND    $d2,X         
$1F43  7E 83 29      ROR    $2983,X       
$1F46  81 27         STA    ($27,X)       
$1F48  7F            DCB    $7f           ; Unknown opcode
$1F49  AB            DCB    $ab           ; Unknown opcode
$1F4A  81 29         STA    ($29,X)       
$1F4C  C2            DCB    $c2           ; Unknown opcode
$1F4D  7E 29 83      ROR    $8329,X       
$1F50  35 29         AND    $29,X         
$1F52  81 29         STA    ($29,X)       
$1F54  C2            DCB    $c2           ; Unknown opcode
$1F55  7E 29 29      ROR    $2929,X       
$1F58  35 D2         AND    $d2,X         
$1F5A  7E 83 29      ROR    $2983,X       
$1F5D  81 28         STA    ($28,X)       
$1F5F  7F            DCB    $7f           ; Unknown opcode
$1F60  AB            DCB    $ab           ; Unknown opcode
$1F61  81 29         STA    ($29,X)       
$1F63  C2            DCB    $c2           ; Unknown opcode
$1F64  7E 29 83      ROR    $8329,X       
$1F67  35 29         AND    $29,X         
$1F69  81 29         STA    ($29,X)       
$1F6B  C2            DCB    $c2           ; Unknown opcode
$1F6C  7E 29 29      ROR    $2929,X       
$1F6F  35 D2         AND    $d2,X         
$1F71  7E 83 29      ROR    $2983,X       
$1F74  81 2D         STA    ($2d,X)       
$1F76  7F            DCB    $7f           ; Unknown opcode
$1F77  B0 80         BCS    $1ef9         
$1F79  37            DCB    $37           ; Unknown opcode
$1F7A  D6 92         DEC    $92,X         
$1F7C  39 C3 8F      AND    $8fc3,Y       
$1F7F  00            BRK                  
$1F80  80            DCB    $80           ; Unknown opcode
$1F81  30 00         BMI    $1f83         
$1F83  30 00         BMI    $1f85         
$1F85  81 30         STA    ($30,X)       
$1F87  91 32         STA    ($32),Y       
$1F89  91 35         STA    ($35),Y       
$1F8B  80            DCB    $80           ; Unknown opcode
$1F8C  37            DCB    $37           ; Unknown opcode
$1F8D  00            BRK                  
$1F8E  37            DCB    $37           ; Unknown opcode
$1F8F  D6 92         DEC    $92,X         
$1F91  39 C1 81      AND    $81c1,Y       
$1F94  3C            DCB    $3c           ; Unknown opcode
$1F95  C3            DCB    $c3           ; Unknown opcode
$1F96  8D 00 80      STA    $8000         
$1F99  30 00         BMI    $1f9b         
$1F9B  30 00         BMI    $1f9d         
$1F9D  81 30         STA    ($30,X)       
$1F9F  91 32         STA    ($32),Y       
$1FA1  90 35         BCC    $1fd8         
$1FA3  00            BRK                  
$1FA4  37            DCB    $37           ; Unknown opcode
$1FA5  00            BRK                  
$1FA6  32            DCB    $32           ; Unknown opcode
$1FA7  D6 92         DEC    $92,X         
$1FA9  34            DCB    $34           ; Unknown opcode
$1FAA  C1 80         CMP    ($80,X)       
$1FAC  35 00         AND    $00,X         
$1FAE  32            DCB    $32           ; Unknown opcode
$1FAF  D6 93         DEC    $93,X         
$1FB1  34            DCB    $34           ; Unknown opcode
$1FB2  C3            DCB    $c3           ; Unknown opcode
$1FB3  82            DCB    $82           ; Unknown opcode
$1FB4  00            BRK                  
$1FB5  C1 80         CMP    ($80,X)       
$1FB7  30 00         BMI    $1fb9         
$1FB9  32            DCB    $32           ; Unknown opcode
$1FBA  D6 92         DEC    $92,X         
$1FBC  34            DCB    $34           ; Unknown opcode
$1FBD  80            DCB    $80           ; Unknown opcode
$1FBE  35 00         AND    $00,X         
$1FC0  32            DCB    $32           ; Unknown opcode
$1FC1  D6 94         DEC    $94,X         
$1FC3  34            DCB    $34           ; Unknown opcode
$1FC4  91 35         STA    ($35),Y       
$1FC6  C1 32         CMP    ($32,X)       
$1FC8  00            BRK                  
$1FC9  C3            DCB    $c3           ; Unknown opcode
$1FCA  8F            DCB    $8f           ; Unknown opcode
$1FCB  00            BRK                  
$1FCC  81 00         STA    ($00,X)       
$1FCE  80            DCB    $80           ; Unknown opcode
$1FCF  30 00         BMI    $1fd1         
$1FD1  30 00         BMI    $1fd3         
$1FD3  81 30         STA    ($30,X)       
$1FD5  91 32         STA    ($32),Y       
$1FD7  91 35         STA    ($35),Y       
$1FD9  80            DCB    $80           ; Unknown opcode
$1FDA  37            DCB    $37           ; Unknown opcode
$1FDB  00            BRK                  
$1FDC  37            DCB    $37           ; Unknown opcode
$1FDD  D6 92         DEC    $92,X         
$1FDF  39 C3 8F      AND    $8fc3,Y       
$1FE2  00            BRK                  
$1FE3  C1 80         CMP    ($80,X)       
$1FE5  39 00 39      AND    $3900,Y       
$1FE8  00            BRK                  
$1FE9  81 39         STA    ($39,X)       
$1FEB  91 3A         STA    ($3a),Y       
$1FED  91 3C         STA    ($3c),Y       
$1FEF  80            DCB    $80           ; Unknown opcode
$1FF0  39 00 35      AND    $3500,Y       
$1FF3  D6 92         DEC    $92,X         
$1FF5  37            DCB    $37           ; Unknown opcode
$1FF6  C1 81         CMP    ($81,X)       
$1FF8  35 C3         AND    $c3,X         
$1FFA  89            DCB    $89           ; Unknown opcode
$1FFB  00            BRK                  
$1FFC  80            DCB    $80           ; Unknown opcode
$1FFD  3E D6 92      ROL    $92d6,X       
$2000  40            RTI                  
$2001  91 3E         STA    ($3e),Y       
$2003  00            BRK                  
$2004  3C            DCB    $3c           ; Unknown opcode
$2005  D6 91         DEC    $91,X         
$2007  3E 91 3C      ROL    $3c91,X       
$200A  C3            DCB    $c3           ; Unknown opcode
$200B  86 7E         STX    $7e           
$200D  88            DEY                  
$200E  00            BRK                  
$200F  80            DCB    $80           ; Unknown opcode
$2010  30 00         BMI    $2012         
$2012  81 39         STA    ($39,X)       
$2014  C3            DCB    $c3           ; Unknown opcode
$2015  7E 91 3A      ROR    $3a91,X       
$2018  00            BRK                  
$2019  3C            DCB    $3c           ; Unknown opcode
$201A  80            DCB    $80           ; Unknown opcode
$201B  37            DCB    $37           ; Unknown opcode
$201C  D6 90         DEC    $90,X         
$201E  39 C1 93      AND    $93c1,Y       
$2021  35 C3         AND    $c3,X         
$2023  84 7E         STY    $7e           
$2025  8F            DCB    $8f           ; Unknown opcode
$2026  00            BRK                  
$2027  8A            TXA                  
$2028  00            BRK                  
$2029  7F            DCB    $7f           ; Unknown opcode
$202A  D3            DCB    $d3           ; Unknown opcode
$202B  AC 80 41      LDY    $4180         
$202E  82            DCB    $82           ; Unknown opcode
$202F  00            BRK                  
$2030  80            DCB    $80           ; Unknown opcode
$2031  7E 00 7E      ROR    $7e00,X       
$2034  82            DCB    $82           ; Unknown opcode
$2035  00            BRK                  
$2036  80            DCB    $80           ; Unknown opcode
$2037  7E 82 00      ROR    $0082,X       
$203A  80            DCB    $80           ; Unknown opcode
$203B  7E 82 00      ROR    $0082,X       
$203E  80            DCB    $80           ; Unknown opcode
$203F  7E 00 7E      ROR    $7e00,X       
$2042  00            BRK                  
$2043  7E 82 00      ROR    $0082,X       
$2046  80            DCB    $80           ; Unknown opcode
$2047  7E 82 00      ROR    $0082,X       
$204A  80            DCB    $80           ; Unknown opcode
$204B  7E 00 7F      ROR    $7f00,X       
$204E  80            DCB    $80           ; Unknown opcode
$204F  7E 82 00      ROR    $0082,X       
$2052  80            DCB    $80           ; Unknown opcode
$2053  7E 00 7E      ROR    $7e00,X       
$2056  82            DCB    $82           ; Unknown opcode
$2057  00            BRK                  
$2058  80            DCB    $80           ; Unknown opcode
$2059  7E 82 00      ROR    $0082,X       
$205C  80            DCB    $80           ; Unknown opcode
$205D  7E 82 00      ROR    $0082,X       
$2060  80            DCB    $80           ; Unknown opcode
$2061  7E 00 7E      ROR    $7e00,X       
$2064  00            BRK                  
$2065  7E 82 00      ROR    $0082,X       
$2068  80            DCB    $80           ; Unknown opcode
$2069  7E 82 00      ROR    $0082,X       
$206C  80            DCB    $80           ; Unknown opcode
$206D  7E 00 7F      ROR    $7f00,X       
$2070  AB            DCB    $ab           ; Unknown opcode
$2071  81 29         STA    ($29,X)       
$2073  C2            DCB    $c2           ; Unknown opcode
$2074  7E 29 83      ROR    $8329,X       
$2077  35 29         AND    $29,X         
$2079  81 29         STA    ($29,X)       
$207B  C2            DCB    $c2           ; Unknown opcode
$207C  87            DCB    $87           ; Unknown opcode
$207D  7E CB AD      ROR    $adcb,X       
$2080  3A            DCB    $3a           ; Unknown opcode
$2081  7F            DCB    $7f           ; Unknown opcode
$2082  80            DCB    $80           ; Unknown opcode
$2083  7E 82 00      ROR    $0082,X       
$2086  80            DCB    $80           ; Unknown opcode
$2087  7E 00 7E      ROR    $7e00,X       
$208A  82            DCB    $82           ; Unknown opcode
$208B  00            BRK                  
$208C  80            DCB    $80           ; Unknown opcode
$208D  7E 82 00      ROR    $0082,X       
$2090  80            DCB    $80           ; Unknown opcode
$2091  7E 88 00      ROR    $0088,X       
$2094  D4            DCB    $d4           ; Unknown opcode
$2095  AE 86 37      LDX    $3786         
$2098  80            DCB    $80           ; Unknown opcode
$2099  00            BRK                  
$209A  7F            DCB    $7f           ; Unknown opcode
$209B  8F            DCB    $8f           ; Unknown opcode
$209C  00            BRK                  
$209D  87            DCB    $87           ; Unknown opcode
$209E  00            BRK                  
$209F  D5 AF         CMP    $af,X         
$20A1  80            DCB    $80           ; Unknown opcode
$20A2  3C            DCB    $3c           ; Unknown opcode
$20A3  3C            DCB    $3c           ; Unknown opcode
$20A4  3C            DCB    $3c           ; Unknown opcode
$20A5  3C            DCB    $3c           ; Unknown opcode
$20A6  3C            DCB    $3c           ; Unknown opcode
$20A7  3C            DCB    $3c           ; Unknown opcode
$20A8  3C            DCB    $3c           ; Unknown opcode
$20A9  3C            DCB    $3c           ; Unknown opcode
$20AA  7F            DCB    $7f           ; Unknown opcode
$20AB  C4 B1         CPY    $b1           
$20AD  81 39         STA    ($39,X)       
$20AF  39 39 C4      AND    $c439,Y       
$20B2  A9 39         LDA    #$39          
$20B4  C4 B1         CPY    $b1           
$20B6  83            DCB    $83           ; Unknown opcode
$20B7  39 80 39      AND    $3980,Y       
$20BA  00            BRK                  
$20BB  83            DCB    $83           ; Unknown opcode
$20BC  39 C5 81      AND    $81c5,Y       
$20BF  3A            DCB    $3a           ; Unknown opcode
$20C0  C5 A9         CMP    $a9           
$20C2  3A            DCB    $3a           ; Unknown opcode
$20C3  C4 B1         CPY    $b1           
$20C5  85 39         STA    $39           
$20C7  C4 A9         CPY    $a9           
$20C9  81 39         STA    ($39,X)       
$20CB  39 7F C6      AND    $c67f,Y       
$20CE  B1 81         LDA    ($81),Y       
$20D0  35 35         AND    $35,X         
$20D2  35 C6         AND    $c6,X         
$20D4  A9 35         LDA    #$35          
$20D6  C6 B1         DEC    $b1           
$20D8  83            DCB    $83           ; Unknown opcode
$20D9  35 80         AND    $80,X         
$20DB  35 00         AND    $00,X         
$20DD  C7            DCB    $c7           ; Unknown opcode
$20DE  83            DCB    $83           ; Unknown opcode
$20DF  37            DCB    $37           ; Unknown opcode
$20E0  80            DCB    $80           ; Unknown opcode
$20E1  37            DCB    $37           ; Unknown opcode
$20E2  00            BRK                  
$20E3  C7            DCB    $c7           ; Unknown opcode
$20E4  A9 37         LDA    #$37          
$20E6  00            BRK                  
$20E7  C6 B1         DEC    $b1           
$20E9  86 35         STX    $35           
$20EB  80            DCB    $80           ; Unknown opcode
$20EC  00            BRK                  
$20ED  C8            INY                  
$20EE  32            DCB    $32           ; Unknown opcode
$20EF  00            BRK                  
$20F0  C9 81         CMP    #$81          
$20F2  34            DCB    $34           ; Unknown opcode
$20F3  34            DCB    $34           ; Unknown opcode
$20F4  34            DCB    $34           ; Unknown opcode
$20F5  C9 A9         CMP    #$a9          
$20F7  80            DCB    $80           ; Unknown opcode
$20F8  34            DCB    $34           ; Unknown opcode
$20F9  00            BRK                  
$20FA  C9 B1         CMP    #$b1          
$20FC  83            DCB    $83           ; Unknown opcode
$20FD  34            DCB    $34           ; Unknown opcode
$20FE  80            DCB    $80           ; Unknown opcode
$20FF  34            DCB    $34           ; Unknown opcode
$2100  00            BRK                  
$2101  CA            DEX                  
$2102  83            DCB    $83           ; Unknown opcode
$2103  35 81         AND    $81,X         
$2105  35 CA         AND    $ca,X         
$2107  A9 80         LDA    #$80          
$2109  35 00         AND    $00,X         
$210B  C9 B1         CMP    #$b1          
$210D  83            DCB    $83           ; Unknown opcode
$210E  34            DCB    $34           ; Unknown opcode
$210F  80            DCB    $80           ; Unknown opcode
$2110  34            DCB    $34           ; Unknown opcode
$2111  00            BRK                  
$2112  C6 83         DEC    $83           
$2114  30 30         BMI    $2146         
$2116  C4 80         CPY    $80           
$2118  32            DCB    $32           ; Unknown opcode
$2119  00            BRK                  
$211A  85 32         STA    $32           
$211C  C4 A9         CPY    $a9           
$211E  81 32         STA    ($32,X)       
$2120  D0 32         BNE    $2154         
$2122  32            DCB    $32           ; Unknown opcode
$2123  D0 32         BNE    $2157         
$2125  D0 32         BNE    $2159         
$2127  32            DCB    $32           ; Unknown opcode
$2128  D0 32         BNE    $215c         
$212A  D0 32         BNE    $215e         
$212C  32            DCB    $32           ; Unknown opcode
$212D  D0 32         BNE    $2161         
$212F  7F            DCB    $7f           ; Unknown opcode
$2130  C6 A9         DEC    $a9           
$2132  81 35         STA    ($35,X)       
$2134  C6 B1         DEC    $b1           
$2136  80            DCB    $80           ; Unknown opcode
$2137  35 00         AND    $00,X         
$2139  35 00         AND    $00,X         
$213B  83            DCB    $83           ; Unknown opcode
$213C  35 80         AND    $80,X         
$213E  35 00         AND    $00,X         
$2140  C6 A9         DEC    $a9           
$2142  81 35         STA    ($35,X)       
$2144  C6 B1         DEC    $b1           
$2146  80            DCB    $80           ; Unknown opcode
$2147  35 00         AND    $00,X         
$2149  C7            DCB    $c7           ; Unknown opcode
$214A  83            DCB    $83           ; Unknown opcode
$214B  37            DCB    $37           ; Unknown opcode
$214C  81 37         STA    ($37,X)       
$214E  C7            DCB    $c7           ; Unknown opcode
$214F  A9 37         LDA    #$37          
$2151  C6 B1         DEC    $b1           
$2153  86 35         STX    $35           
$2155  80            DCB    $80           ; Unknown opcode
$2156  00            BRK                  
$2157  C9 34         CMP    #$34          
$2159  00            BRK                  
$215A  34            DCB    $34           ; Unknown opcode
$215B  00            BRK                  
$215C  83            DCB    $83           ; Unknown opcode
$215D  34            DCB    $34           ; Unknown opcode
$215E  81 34         STA    ($34,X)       
$2160  C9 A9         CMP    #$a9          
$2162  34            DCB    $34           ; Unknown opcode
$2163  C9 B1         CMP    #$b1          
$2165  80            DCB    $80           ; Unknown opcode
$2166  34            DCB    $34           ; Unknown opcode
$2167  00            BRK                  
$2168  CA            DEX                  
$2169  83            DCB    $83           ; Unknown opcode
$216A  35 81         AND    $81,X         
$216C  35 CA         AND    $ca,X         
$216E  A9 35         LDA    #$35          
$2170  C9 B1         CMP    #$b1          
$2172  83            DCB    $83           ; Unknown opcode
$2173  34            DCB    $34           ; Unknown opcode
$2174  80            DCB    $80           ; Unknown opcode
$2175  34            DCB    $34           ; Unknown opcode
$2176  00            BRK                  
$2177  C6 81         DEC    $81           
$2179  30 C6         BMI    $2141         
$217B  A9 30         LDA    #$30          
$217D  C6 B1         DEC    $b1           
$217F  83            DCB    $83           ; Unknown opcode
$2180  30 C4         BMI    $2146         
$2182  80            DCB    $80           ; Unknown opcode
$2183  32            DCB    $32           ; Unknown opcode
$2184  00            BRK                  
$2185  85 32         STA    $32           
$2187  C4 A9         CPY    $a9           
$2189  81 32         STA    ($32,X)       
$218B  D0 32         BNE    $21bf         
$218D  32            DCB    $32           ; Unknown opcode
$218E  D0 32         BNE    $21c2         
$2190  D0 32         BNE    $21c4         
$2192  32            DCB    $32           ; Unknown opcode
$2193  D0 32         BNE    $21c7         
$2195  D0 32         BNE    $21c9         
$2197  32            DCB    $32           ; Unknown opcode
$2198  D0 32         BNE    $21cc         
$219A  7F            DCB    $7f           ; Unknown opcode
$219B  A1 83         LDA    ($83,X)       
$219D  11 A6         ORA    ($a6),Y       
$219F  81 3C         STA    ($3c,X)       
$21A1  A7            DCB    $a7           ; Unknown opcode
$21A2  45 A2         EOR    $a2           
$21A4  18            CLC                  
$21A5  A7            DCB    $a7           ; Unknown opcode
$21A6  48            PHA                  
$21A7  A4 80         LDY    $80           
$21A9  11 00         ORA    ($00),Y       
$21AB  A1 83         LDA    ($83,X)       
$21AD  11 81         ORA    ($81),Y       
$21AF  00            BRK                  
$21B0  A6 3C         LDX    $3c           
$21B2  A7            DCB    $a7           ; Unknown opcode
$21B3  43            DCB    $43           ; Unknown opcode
$21B4  A2 18         LDX    #$18          
$21B6  A7            DCB    $a7           ; Unknown opcode
$21B7  48            PHA                  
$21B8  A4 83         LDY    $83           
$21BA  18            CLC                  
$21BB  7F            DCB    $7f           ; Unknown opcode
$21BC  A1 83         LDA    ($83,X)       
$21BE  11 A6         ORA    ($a6),Y       
$21C0  81 3C         STA    ($3c,X)       
$21C2  A7            DCB    $a7           ; Unknown opcode
$21C3  41 A2         EOR    ($a2,X)       
$21C5  18            CLC                  
$21C6  A7            DCB    $a7           ; Unknown opcode
$21C7  48            PHA                  
$21C8  A4 80         LDY    $80           
$21CA  11 00         ORA    ($00),Y       
$21CC  A1 83         LDA    ($83,X)       
$21CE  11 81         ORA    ($81),Y       
$21D0  00            BRK                  
$21D1  A6 3C         LDX    $3c           
$21D3  A7            DCB    $a7           ; Unknown opcode
$21D4  43            DCB    $43           ; Unknown opcode
$21D5  A2 18         LDX    #$18          
$21D7  A7            DCB    $a7           ; Unknown opcode
$21D8  48            PHA                  
$21D9  A4 83         LDY    $83           
$21DB  18            CLC                  
$21DC  7F            DCB    $7f           ; Unknown opcode
$21DD  A1 83         LDA    ($83,X)       
$21DF  1C            DCB    $1c           ; Unknown opcode
$21E0  A6 81         LDX    $81           
$21E2  43            DCB    $43           ; Unknown opcode
$21E3  A7            DCB    $a7           ; Unknown opcode
$21E4  48            PHA                  
$21E5  A2 18         LDX    #$18          
$21E7  A4 10         LDY    $10           
$21E9  A3            DCB    $a3           ; Unknown opcode
$21EA  80            DCB    $80           ; Unknown opcode
$21EB  18            CLC                  
$21EC  00            BRK                  
$21ED  A1 83         LDA    ($83,X)       
$21EF  11 80         ORA    ($80),Y       
$21F1  1D 00 A6      ORA    $a600,X       
$21F4  81 43         STA    ($43,X)       
$21F6  A7            DCB    $a7           ; Unknown opcode
$21F7  45 A2         EOR    $a2           
$21F9  18            CLC                  
$21FA  A1 15         LDA    ($15,X)       
$21FC  A4 1D         LDY    $1d           
$21FE  91 1B         STA    ($1b),Y       
$2200  A1 83         LDA    ($83,X)       
$2202  1A            DCB    $1a           ; Unknown opcode
$2203  A6 81         LDX    $81           
$2205  41 A1         EOR    ($a1,X)       
$2207  1D A2 83      ORA    $83a2,X       
$220A  0E A4 80      ASL    $80a4         
$220D  16 00         ASL    $00,X         
$220F  A1 81         LDA    ($81,X)       
$2211  1B            DCB    $1b           ; Unknown opcode
$2212  91 16         STA    ($16),Y       
$2214  83            DCB    $83           ; Unknown opcode
$2215  0F            DCB    $0f           ; Unknown opcode
$2216  A6 81         LDX    $81           
$2218  43            DCB    $43           ; Unknown opcode
$2219  A2 18         LDX    #$18          
$221B  A1 1F         LDA    ($1f,X)       
$221D  A4 1B         LDY    $1b           
$221F  91 1A         STA    ($1a),Y       
$2221  A1 83         LDA    ($83,X)       
$2223  19 A6 81      ORA    $81a6,Y       
$2226  40            RTI                  
$2227  A1 15         LDA    ($15,X)       
$2229  A2 18         LDX    #$18          
$222B  A4 10         LDY    $10           
$222D  95 0E         STA    $0e,X         
$222F  81 1A         STA    ($1a,X)       
$2231  A6 40         LDX    $40           
$2233  A7            DCB    $a7           ; Unknown opcode
$2234  41 A2         EOR    ($a2,X)       
$2236  18            CLC                  
$2237  A1 15         LDA    ($15,X)       
$2239  A3            DCB    $a3           ; Unknown opcode
$223A  24 A1         BIT    $a1           
$223C  80            DCB    $80           ; Unknown opcode
$223D  15 00         ORA    $00,X         
$223F  83            DCB    $83           ; Unknown opcode
$2240  17            DCB    $17           ; Unknown opcode
$2241  A6 81         LDX    $81           
$2243  3E A7 43      ROL    $43a7,X       
$2246  A2 83         LDX    #$83          
$2248  18            CLC                  
$2249  A4 80         LDY    $80           
$224B  11 00         ORA    ($00),Y       
$224D  A1 85         LDA    ($85,X)       
$224F  13            DCB    $13           ; Unknown opcode
$2250  A6 81         LDX    $81           
$2252  3B            DCB    $3b           ; Unknown opcode
$2253  A7            DCB    $a7           ; Unknown opcode
$2254  41 A2         EOR    ($a2,X)       
$2256  18            CLC                  
$2257  A1 80         LDA    ($80,X)       
$2259  11 00         ORA    ($00),Y       
$225B  A4 81         LDY    $81           
$225D  13            DCB    $13           ; Unknown opcode
$225E  91 15         STA    ($15),Y       
$2260  A1 83         LDA    ($83,X)       
$2262  16 A6         ASL    $a6,X         
$2264  81 3A         STA    ($3a,X)       
$2266  A7            DCB    $a7           ; Unknown opcode
$2267  3E A2 18      ROL    $18a2,X       
$226A  A7            DCB    $a7           ; Unknown opcode
$226B  45 A4         EOR    $a4           
$226D  80            DCB    $80           ; Unknown opcode
$226E  11 00         ORA    ($00),Y       
$2270  A1 85         LDA    ($85,X)       
$2272  0A            ASL    A             
$2273  A7            DCB    $a7           ; Unknown opcode
$2274  81 3A         STA    ($3a,X)       
$2276  A6 3E         LDX    $3e           
$2278  A2 18         LDX    #$18          
$227A  A6 43         LDX    $43           
$227C  A3            DCB    $a3           ; Unknown opcode
$227D  83            DCB    $83           ; Unknown opcode
$227E  24 A1         BIT    $a1           
$2280  18            CLC                  
$2281  A6 81         LDX    $81           
$2283  3C            DCB    $3c           ; Unknown opcode
$2284  A7            DCB    $a7           ; Unknown opcode
$2285  40            RTI                  
$2286  A2 18         LDX    #$18          
$2288  A7            DCB    $a7           ; Unknown opcode
$2289  45 A4         EOR    $a4           
$228B  80            DCB    $80           ; Unknown opcode
$228C  13            DCB    $13           ; Unknown opcode
$228D  00            BRK                  
$228E  A1 85         LDA    ($85,X)       
$2290  0C            DCB    $0c           ; Unknown opcode
$2291  A6 81         LDX    $81           
$2293  37            DCB    $37           ; Unknown opcode
$2294  A7            DCB    $a7           ; Unknown opcode
$2295  3C            DCB    $3c           ; Unknown opcode
$2296  A2 18         LDX    #$18          
$2298  A1 89         LDA    ($89,X)       
$229A  0C            DCB    $0c           ; Unknown opcode
$229B  83            DCB    $83           ; Unknown opcode
$229C  00            BRK                  
$229D  D5 AF         CMP    $af,X         
$229F  80            DCB    $80           ; Unknown opcode
$22A0  3C            DCB    $3c           ; Unknown opcode
$22A1  3C            DCB    $3c           ; Unknown opcode
$22A2  3C            DCB    $3c           ; Unknown opcode
$22A3  3C            DCB    $3c           ; Unknown opcode
$22A4  3C            DCB    $3c           ; Unknown opcode
$22A5  3C            DCB    $3c           ; Unknown opcode
$22A6  3C            DCB    $3c           ; Unknown opcode
$22A7  3C            DCB    $3c           ; Unknown opcode
$22A8  7F            DCB    $7f           ; Unknown opcode
$22A9  83            DCB    $83           ; Unknown opcode
$22AA  00            BRK                  
$22AB  B0 80         BCS    $222d         
$22AD  3C            DCB    $3c           ; Unknown opcode
$22AE  00            BRK                  
$22AF  3C            DCB    $3c           ; Unknown opcode
$22B0  00            BRK                  
$22B1  81 3C         STA    ($3c,X)       
$22B3  91 3E         STA    ($3e),Y       
$22B5  91 41         STA    ($41),Y       
$22B7  80            DCB    $80           ; Unknown opcode
$22B8  43            DCB    $43           ; Unknown opcode
$22B9  00            BRK                  
$22BA  7F            DCB    $7f           ; Unknown opcode
$22BB  8F            DCB    $8f           ; Unknown opcode
$22BC  00            BRK                  
$22BD  83            DCB    $83           ; Unknown opcode
$22BE  00            BRK                  
$22BF  B0 80         BCS    $2241         
$22C1  3C            DCB    $3c           ; Unknown opcode
$22C2  00            BRK                  
$22C3  3C            DCB    $3c           ; Unknown opcode
$22C4  00            BRK                  
$22C5  81 3C         STA    ($3c,X)       
$22C7  91 3D         STA    ($3d),Y       
$22C9  91 41         STA    ($41),Y       
$22CB  80            DCB    $80           ; Unknown opcode
$22CC  48            PHA                  
$22CD  00            BRK                  
$22CE  7F            DCB    $7f           ; Unknown opcode
$22CF  CB            DCB    $cb           ; Unknown opcode
$22D0  A9 81         LDA    #$81          
$22D2  29 CB         AND    #$cb          
$22D4  A0 80         LDY    #$80          
$22D6  29 00         AND    #$00          
$22D8  83            DCB    $83           ; Unknown opcode
$22D9  29 80         AND    #$80          
$22DB  29 00         AND    #$00          
$22DD  CB            DCB    $cb           ; Unknown opcode
$22DE  A9 81         LDA    #$81          
$22E0  29 CB         AND    #$cb          
$22E2  A0 83         LDY    #$83          
$22E4  29 80         AND    #$80          
$22E6  29 00         AND    #$00          
$22E8  CB            DCB    $cb           ; Unknown opcode
$22E9  A9 81         LDA    #$81          
$22EB  29 C8         AND    #$c8          
$22ED  A0 80         LDY    #$80          
$22EF  2B            DCB    $2b           ; Unknown opcode
$22F0  00            BRK                  
$22F1  CD 85 2D      CMP    $2d85         
$22F4  CD A9 81      CMP    $81a9         
$22F7  2D 2D CB      AND    $cb2d         
$22FA  A0 80         LDY    #$80          
$22FC  2B            DCB    $2b           ; Unknown opcode
$22FD  00            BRK                  
$22FE  2B            DCB    $2b           ; Unknown opcode
$22FF  00            BRK                  
$2300  83            DCB    $83           ; Unknown opcode
$2301  2B            DCB    $2b           ; Unknown opcode
$2302  80            DCB    $80           ; Unknown opcode
$2303  2B            DCB    $2b           ; Unknown opcode
$2304  00            BRK                  
$2305  CB            DCB    $cb           ; Unknown opcode
$2306  A9 2B         LDA    #$2b          
$2308  00            BRK                  
$2309  CB            DCB    $cb           ; Unknown opcode
$230A  A0 2B         LDY    #$2b          
$230C  00            BRK                  
$230D  83            DCB    $83           ; Unknown opcode
$230E  2B            DCB    $2b           ; Unknown opcode
$230F  C8            INY                  
$2310  81 2D         STA    ($2d,X)       
$2312  C8            INY                  
$2313  A9 2D         LDA    #$2d          
$2315  CE A0 2E      DEC    $2ea0         
$2318  CE A9 2E      DEC    $2ea9         
$231B  D7            DCB    $d7           ; Unknown opcode
$231C  A0 89         LDY    #$89          
$231E  30 83         BMI    $22a3         
$2320  00            BRK                  
$2321  81 30         STA    ($30,X)       
$2323  00            BRK                  
$2324  30 00         BMI    $2326         
$2326  7F            DCB    $7f           ; Unknown opcode
$2327  C4 A0         CPY    $a0           
$2329  80            DCB    $80           ; Unknown opcode
$232A  34            DCB    $34           ; Unknown opcode
$232B  82            DCB    $82           ; Unknown opcode
$232C  00            BRK                  
$232D  C4 A9         CPY    $a9           
$232F  81 34         STA    ($34,X)       
$2331  C4 A0         CPY    $a0           
$2333  80            DCB    $80           ; Unknown opcode
$2334  34            DCB    $34           ; Unknown opcode
$2335  82            DCB    $82           ; Unknown opcode
$2336  00            BRK                  
$2337  C4 A9         CPY    $a9           
$2339  81 34         STA    ($34,X)       
$233B  C4 A0         CPY    $a0           
$233D  80            DCB    $80           ; Unknown opcode
$233E  34            DCB    $34           ; Unknown opcode
$233F  82            DCB    $82           ; Unknown opcode
$2340  00            BRK                  
$2341  C4 A9         CPY    $a9           
$2343  81 34         STA    ($34,X)       
$2345  C4 A0         CPY    $a0           
$2347  80            DCB    $80           ; Unknown opcode
$2348  34            DCB    $34           ; Unknown opcode
$2349  82            DCB    $82           ; Unknown opcode
$234A  00            BRK                  
$234B  C4 A9         CPY    $a9           
$234D  80            DCB    $80           ; Unknown opcode
$234E  34            DCB    $34           ; Unknown opcode
$234F  00            BRK                  
$2350  C4 A0         CPY    $a0           
$2352  34            DCB    $34           ; Unknown opcode
$2353  82            DCB    $82           ; Unknown opcode
$2354  00            BRK                  
$2355  C4 A9         CPY    $a9           
$2357  80            DCB    $80           ; Unknown opcode
$2358  34            DCB    $34           ; Unknown opcode
$2359  00            BRK                  
$235A  34            DCB    $34           ; Unknown opcode
$235B  00            BRK                  
$235C  D8            CLD                  
$235D  A0 35         LDY    #$35          
$235F  82            DCB    $82           ; Unknown opcode
$2360  00            BRK                  
$2361  D8            CLD                  
$2362  A9 81         LDA    #$81          
$2364  35 D8         AND    $d8,X         
$2366  A0 80         LDY    #$80          
$2368  35 82         AND    $82,X         
$236A  00            BRK                  
$236B  D8            CLD                  
$236C  A9 81         LDA    #$81          
$236E  35 D8         AND    $d8,X         
$2370  A0 80         LDY    #$80          
$2372  35 82         AND    $82,X         
$2374  00            BRK                  
$2375  D8            CLD                  
$2376  A9 81         LDA    #$81          
$2378  35 D8         AND    $d8,X         
$237A  A0 80         LDY    #$80          
$237C  35 82         AND    $82,X         
$237E  00            BRK                  
$237F  D8            CLD                  
$2380  A9 81         LDA    #$81          
$2382  35 D8         AND    $d8,X         
$2384  A0 80         LDY    #$80          
$2386  35 82         AND    $82,X         
$2388  00            BRK                  
$2389  81 35         STA    ($35,X)       
$238B  D8            CLD                  
$238C  A9 35         LDA    #$35          
$238E  D9 A0 80      CMP    $80a0,Y       
$2391  32            DCB    $32           ; Unknown opcode
$2392  82            DCB    $82           ; Unknown opcode
$2393  00            BRK                  
$2394  D9 A9 81      CMP    $81a9,Y       
$2397  32            DCB    $32           ; Unknown opcode
$2398  D9 A0 80      CMP    $80a0,Y       
$239B  32            DCB    $32           ; Unknown opcode
$239C  82            DCB    $82           ; Unknown opcode
$239D  00            BRK                  
$239E  D9 A9 81      CMP    $81a9,Y       
$23A1  32            DCB    $32           ; Unknown opcode
$23A2  D9 A0 80      CMP    $80a0,Y       
$23A5  32            DCB    $32           ; Unknown opcode
$23A6  82            DCB    $82           ; Unknown opcode
$23A7  00            BRK                  
$23A8  D9 A9 81      CMP    $81a9,Y       
$23AB  32            DCB    $32           ; Unknown opcode
$23AC  D9 A0 80      CMP    $80a0,Y       
$23AF  32            DCB    $32           ; Unknown opcode
$23B0  82            DCB    $82           ; Unknown opcode
$23B1  00            BRK                  
$23B2  D9 A9 81      CMP    $81a9,Y       
$23B5  32            DCB    $32           ; Unknown opcode
$23B6  D9 A0 80      CMP    $80a0,Y       
$23B9  32            DCB    $32           ; Unknown opcode
$23BA  82            DCB    $82           ; Unknown opcode
$23BB  00            BRK                  
$23BC  D9 A9 81      CMP    $81a9,Y       
$23BF  32            DCB    $32           ; Unknown opcode
$23C0  32            DCB    $32           ; Unknown opcode
$23C1  D8            CLD                  
$23C2  A0 80         LDY    #$80          
$23C4  32            DCB    $32           ; Unknown opcode
$23C5  82            DCB    $82           ; Unknown opcode
$23C6  00            BRK                  
$23C7  D8            CLD                  
$23C8  A9 81         LDA    #$81          
$23CA  32            DCB    $32           ; Unknown opcode
$23CB  D8            CLD                  
$23CC  A0 80         LDY    #$80          
$23CE  32            DCB    $32           ; Unknown opcode
$23CF  82            DCB    $82           ; Unknown opcode
$23D0  00            BRK                  
$23D1  D8            CLD                  
$23D2  A9 81         LDA    #$81          
$23D4  32            DCB    $32           ; Unknown opcode
$23D5  D8            CLD                  
$23D6  A0 80         LDY    #$80          
$23D8  32            DCB    $32           ; Unknown opcode
$23D9  82            DCB    $82           ; Unknown opcode
$23DA  00            BRK                  
$23DB  D8            CLD                  
$23DC  A9 81         LDA    #$81          
$23DE  32            DCB    $32           ; Unknown opcode
$23DF  D8            CLD                  
$23E0  A0 80         LDY    #$80          
$23E2  32            DCB    $32           ; Unknown opcode
$23E3  82            DCB    $82           ; Unknown opcode
$23E4  00            BRK                  
$23E5  D8            CLD                  
$23E6  A9 81         LDA    #$81          
$23E8  32            DCB    $32           ; Unknown opcode
$23E9  D8            CLD                  
$23EA  A0 80         LDY    #$80          
$23EC  32            DCB    $32           ; Unknown opcode
$23ED  82            DCB    $82           ; Unknown opcode
$23EE  00            BRK                  
$23EF  81 35         STA    ($35,X)       
$23F1  D8            CLD                  
$23F2  A9 35         LDA    #$35          
$23F4  7F            DCB    $7f           ; Unknown opcode
$23F5  A1 83         LDA    ($83,X)       
$23F7  18            CLC                  
$23F8  A6 81         LDX    $81           
$23FA  43            DCB    $43           ; Unknown opcode
$23FB  A7            DCB    $a7           ; Unknown opcode
$23FC  48            PHA                  
$23FD  A2 83         LDX    #$83          
$23FF  18            CLC                  
$2400  A4 80         LDY    $80           
$2402  18            CLC                  
$2403  00            BRK                  
$2404  A1 83         LDA    ($83,X)       
$2406  11 80         ORA    ($80),Y       
$2408  1D 00 A6      ORA    $a600,X       
$240B  81 43         STA    ($43,X)       
$240D  A7            DCB    $a7           ; Unknown opcode
$240E  45 A2         EOR    $a2           
$2410  18            CLC                  
$2411  A1 15         LDA    ($15,X)       
$2413  A4 18         LDY    $18           
$2415  91 17         STA    ($17),Y       
$2417  A1 83         LDA    ($83,X)       
$2419  16 A6         ASL    $a6,X         
$241B  81 41         STA    ($41,X)       
$241D  A7            DCB    $a7           ; Unknown opcode
$241E  46 A2         LSR    $a2           
$2420  83            DCB    $83           ; Unknown opcode
$2421  18            CLC                  
$2422  A4 80         LDY    $80           
$2424  16 00         ASL    $00,X         
$2426  A1 81         LDA    ($81,X)       
$2428  1B            DCB    $1b           ; Unknown opcode
$2429  91 16         STA    ($16),Y       
$242B  0F            DCB    $0f           ; Unknown opcode
$242C  A7            DCB    $a7           ; Unknown opcode
$242D  41 A6         EOR    ($a6,X)       
$242F  43            DCB    $43           ; Unknown opcode
$2430  A2 18         LDX    #$18          
$2432  A1 1F         LDA    ($1f,X)       
$2434  A4 1B         LDY    $1b           
$2436  91 1A         STA    ($1a),Y       
$2438  A1 83         LDA    ($83,X)       
$243A  19 A6 81      ORA    $81a6,Y       
$243D  40            RTI                  
$243E  A1 15         LDA    ($15,X)       
$2440  A2 18         LDX    #$18          
$2442  A4 10         LDY    $10           
$2444  95 0E         STA    $0e,X         
$2446  81 1A         STA    ($1a,X)       
$2448  A6 40         LDX    $40           
$244A  A7            DCB    $a7           ; Unknown opcode
$244B  41 A2         EOR    ($a2,X)       
$244D  18            CLC                  
$244E  A1 15         LDA    ($15,X)       
$2450  A3            DCB    $a3           ; Unknown opcode
$2451  24 A1         BIT    $a1           
$2453  80            DCB    $80           ; Unknown opcode
$2454  15 00         ORA    $00,X         
$2456  83            DCB    $83           ; Unknown opcode
$2457  17            DCB    $17           ; Unknown opcode
$2458  A6 81         LDX    $81           
$245A  3E A7 43      ROL    $43a7,X       
$245D  A2 83         LDX    #$83          
$245F  18            CLC                  
$2460  A4 80         LDY    $80           
$2462  11 00         ORA    ($00),Y       
$2464  A1 85         LDA    ($85,X)       
$2466  13            DCB    $13           ; Unknown opcode
$2467  A6 81         LDX    $81           
$2469  3B            DCB    $3b           ; Unknown opcode
$246A  A7            DCB    $a7           ; Unknown opcode
$246B  41 A2         EOR    ($a2,X)       
$246D  18            CLC                  
$246E  A1 80         LDA    ($80,X)       
$2470  11 00         ORA    ($00),Y       
$2472  A4 81         LDY    $81           
$2474  13            DCB    $13           ; Unknown opcode
$2475  91 15         STA    ($15),Y       
$2477  A1 83         LDA    ($83,X)       
$2479  16 A6         ASL    $a6,X         
$247B  81 3A         STA    ($3a,X)       
$247D  A7            DCB    $a7           ; Unknown opcode
$247E  3E A2 18      ROL    $18a2,X       
$2481  A7            DCB    $a7           ; Unknown opcode
$2482  45 A4         EOR    $a4           
$2484  80            DCB    $80           ; Unknown opcode
$2485  11 00         ORA    ($00),Y       
$2487  A1 85         LDA    ($85,X)       
$2489  0A            ASL    A             
$248A  A7            DCB    $a7           ; Unknown opcode
$248B  81 3A         STA    ($3a,X)       
$248D  A6 3E         LDX    $3e           
$248F  A2 18         LDX    #$18          
$2491  A6 43         LDX    $43           
$2493  A3            DCB    $a3           ; Unknown opcode
$2494  83            DCB    $83           ; Unknown opcode
$2495  24 A1         BIT    $a1           
$2497  18            CLC                  
$2498  A6 81         LDX    $81           
$249A  3C            DCB    $3c           ; Unknown opcode
$249B  A7            DCB    $a7           ; Unknown opcode
$249C  40            RTI                  
$249D  A2 18         LDX    #$18          
$249F  A7            DCB    $a7           ; Unknown opcode
$24A0  45 A4         EOR    $a4           
$24A2  80            DCB    $80           ; Unknown opcode
$24A3  13            DCB    $13           ; Unknown opcode
$24A4  00            BRK                  
$24A5  A1 85         LDA    ($85,X)       
$24A7  0C            DCB    $0c           ; Unknown opcode
$24A8  A6 81         LDX    $81           
$24AA  37            DCB    $37           ; Unknown opcode
$24AB  A7            DCB    $a7           ; Unknown opcode
$24AC  3C            DCB    $3c           ; Unknown opcode
$24AD  A2 18         LDX    #$18          
$24AF  A1 85         LDA    ($85,X)       
$24B1  0C            DCB    $0c           ; Unknown opcode
$24B2  7F            DCB    $7f           ; Unknown opcode
$24B3  C3            DCB    $c3           ; Unknown opcode
$24B4  84 7E         STY    $7e           
$24B6  82            DCB    $82           ; Unknown opcode
$24B7  00            BRK                  
$24B8  A8            TAY                  
$24B9  80            DCB    $80           ; Unknown opcode
$24BA  39 C0 92      AND    $92c0,Y       
$24BD  3A            DCB    $3a           ; Unknown opcode
$24BE  93            DCB    $93           ; Unknown opcode
$24BF  39 C3 7E      AND    $7ec3,Y       
$24C2  00            BRK                  
$24C3  80            DCB    $80           ; Unknown opcode
$24C4  35 C0         AND    $c0,X         
$24C6  92            DCB    $92           ; Unknown opcode
$24C7  37            DCB    $37           ; Unknown opcode
$24C8  93            DCB    $93           ; Unknown opcode
$24C9  35 C3         AND    $c3,X         
$24CB  81 7E         STA    ($7e,X)       
$24CD  33            DCB    $33           ; Unknown opcode
$24CE  32            DCB    $32           ; Unknown opcode
$24CF  00            BRK                  
$24D0  80            DCB    $80           ; Unknown opcode
$24D1  30 C0         BMI    $2493         
$24D3  90 32         BCC    $2507         
$24D5  C1 81         CMP    ($81,X)       
$24D7  35 93         AND    $93,X         
$24D9  2E C3 84      ROL    $84c3         
$24DC  7E 80 00      ROR    $0080,X       
$24DF  81 26         STA    ($26,X)       
$24E1  C0 91         CPY    #$91          
$24E3  27            DCB    $27           ; Unknown opcode
$24E4  C1 2B         CMP    ($2b,X)       
$24E6  91 2E         STA    ($2e),Y       
$24E8  91 32         STA    ($32),Y       
$24EA  93            DCB    $93           ; Unknown opcode
$24EB  31 C0         AND    ($c0),Y       
$24ED  91 32         STA    ($32),Y       
$24EF  C1 80         CMP    ($80,X)       
$24F1  34            DCB    $34           ; Unknown opcode
$24F2  82            DCB    $82           ; Unknown opcode
$24F3  00            BRK                  
$24F4  81 39         STA    ($39,X)       
$24F6  80            DCB    $80           ; Unknown opcode
$24F7  34            DCB    $34           ; Unknown opcode
$24F8  92            DCB    $92           ; Unknown opcode
$24F9  35 81         AND    $81,X         
$24FB  34            DCB    $34           ; Unknown opcode
$24FC  32            DCB    $32           ; Unknown opcode
$24FD  00            BRK                  
$24FE  80            DCB    $80           ; Unknown opcode
$24FF  2D 00 37      AND    $3700         
$2502  C0 90         CPY    #$90          
$2504  39 C1 91      AND    $91c1,Y       
$2507  3C            DCB    $3c           ; Unknown opcode
$2508  80            DCB    $80           ; Unknown opcode
$2509  39 C0 92      AND    $92c0,Y       
$250C  3B            DCB    $3b           ; Unknown opcode
$250D  90 3A         BCC    $2549         
$250F  C1 90         CMP    ($90,X)       
$2511  39 91 37      AND    $3791,Y       
$2514  C3            DCB    $c3           ; Unknown opcode
$2515  83            DCB    $83           ; Unknown opcode
$2516  7E 85 00      ROR    $0085,X       
$2519  A8            TAY                  
$251A  80            DCB    $80           ; Unknown opcode
$251B  32            DCB    $32           ; Unknown opcode
$251C  00            BRK                  
$251D  34            DCB    $34           ; Unknown opcode
$251E  C0 92         CPY    #$92          
$2520  35 91         AND    $91,X         
$2522  34            DCB    $34           ; Unknown opcode
$2523  C1 32         CMP    ($32,X)       
$2525  00            BRK                  
$2526  30 83         BMI    $24ab         
$2528  32            DCB    $32           ; Unknown opcode
$2529  C3            DCB    $c3           ; Unknown opcode
$252A  87            DCB    $87           ; Unknown opcode
$252B  7E 83 00      ROR    $0083,X       
$252E  80            DCB    $80           ; Unknown opcode
$252F  32            DCB    $32           ; Unknown opcode
$2530  00            BRK                  
$2531  34            DCB    $34           ; Unknown opcode
$2532  00            BRK                  
$2533  34            DCB    $34           ; Unknown opcode
$2534  C0 92         CPY    #$92          
$2536  35 91         AND    $91,X         
$2538  34            DCB    $34           ; Unknown opcode
$2539  C1 80         CMP    ($80,X)       
$253B  32            DCB    $32           ; Unknown opcode
$253C  82            DCB    $82           ; Unknown opcode
$253D  00            BRK                  
$253E  81 30         STA    ($30,X)       
$2540  80            DCB    $80           ; Unknown opcode
$2541  30 C0         BMI    $2503         
$2543  92            DCB    $92           ; Unknown opcode
$2544  32            DCB    $32           ; Unknown opcode
$2545  C3            DCB    $c3           ; Unknown opcode
$2546  87            DCB    $87           ; Unknown opcode
$2547  7E 81 00      ROR    $0081,X       
$254A  80            DCB    $80           ; Unknown opcode
$254B  2D 00 32      AND    $3200         
$254E  00            BRK                  
$254F  34            DCB    $34           ; Unknown opcode
$2550  00            BRK                  
$2551  34            DCB    $34           ; Unknown opcode
$2552  C0 92         CPY    #$92          
$2554  35 81         AND    $81,X         
$2556  34            DCB    $34           ; Unknown opcode
$2557  C1 80         CMP    ($80,X)       
$2559  32            DCB    $32           ; Unknown opcode
$255A  82            DCB    $82           ; Unknown opcode
$255B  00            BRK                  
$255C  80            DCB    $80           ; Unknown opcode
$255D  30 00         BMI    $255f         
$255F  30 C0         BMI    $2521         
$2561  92            DCB    $92           ; Unknown opcode
$2562  32            DCB    $32           ; Unknown opcode
$2563  7F            DCB    $7f           ; Unknown opcode
$2564  CB            DCB    $cb           ; Unknown opcode
$2565  A9 81         LDA    #$81          
$2567  29 CB         AND    #$cb          
$2569  A0 80         LDY    #$80          
$256B  29 00         AND    #$00          
$256D  83            DCB    $83           ; Unknown opcode
$256E  29 80         AND    #$80          
$2570  29 00         AND    #$00          
$2572  CB            DCB    $cb           ; Unknown opcode
$2573  A9 81         LDA    #$81          
$2575  29 CB         AND    #$cb          
$2577  A0 83         LDY    #$83          
$2579  29 80         AND    #$80          
$257B  29 00         AND    #$00          
$257D  CB            DCB    $cb           ; Unknown opcode
$257E  A9 81         LDA    #$81          
$2580  29 C8         AND    #$c8          
$2582  A0 80         LDY    #$80          
$2584  2B            DCB    $2b           ; Unknown opcode
$2585  00            BRK                  
$2586  CD 85 2D      CMP    $2d85         
$2589  CD A9 81      CMP    $81a9         
$258C  2D 2D CB      AND    $cb2d         
$258F  A0 80         LDY    #$80          
$2591  2B            DCB    $2b           ; Unknown opcode
$2592  00            BRK                  
$2593  2B            DCB    $2b           ; Unknown opcode
$2594  00            BRK                  
$2595  83            DCB    $83           ; Unknown opcode
$2596  2B            DCB    $2b           ; Unknown opcode
$2597  80            DCB    $80           ; Unknown opcode
$2598  2B            DCB    $2b           ; Unknown opcode
$2599  00            BRK                  
$259A  CB            DCB    $cb           ; Unknown opcode
$259B  A9 2B         LDA    #$2b          
$259D  00            BRK                  
$259E  CB            DCB    $cb           ; Unknown opcode
$259F  A0 2B         LDY    #$2b          
$25A1  00            BRK                  
$25A2  83            DCB    $83           ; Unknown opcode
$25A3  2B            DCB    $2b           ; Unknown opcode
$25A4  C8            INY                  
$25A5  81 2D         STA    ($2d,X)       
$25A7  C8            INY                  
$25A8  A9 2D         LDA    #$2d          
$25AA  CB            DCB    $cb           ; Unknown opcode
$25AB  A0 89         LDY    #$89          
$25AD  2B            DCB    $2b           ; Unknown opcode
$25AE  7F            DCB    $7f           ; Unknown opcode
$25AF  DA            DCB    $da           ; Unknown opcode
$25B0  A0 8F         LDY    #$8f          
$25B2  29 83         AND    #$83          
$25B4  7E 8F 00      ROR    $008f,X       
$25B7  00            BRK                  
$25B8  8B            DCB    $8b           ; Unknown opcode
$25B9  00            BRK                  
$25BA  7F            DCB    $7f           ; Unknown opcode
$25BB  A1 8F         LDA    ($8f,X)       
$25BD  0E 7E 00      ASL    $007e         
$25C0  00            BRK                  
$25C1  7F            DCB    $7f           ; Unknown opcode
$25C2  C3            DCB    $c3           ; Unknown opcode
$25C3  89            DCB    $89           ; Unknown opcode
$25C4  7E E0 90      ROR    $90e0,X       
$25C7  30 DF         BMI    $25a8         
$25C9  90 2D         BCC    $25f8         
$25CB  90 2C         BCC    $25f9         
$25CD  90 2B         BCC    $25fa         
$25CF  90 29         BCC    $25fa         
$25D1  90 26         BCC    $25f9         
$25D3  90 24         BCC    $25f9         
$25D5  90 21         BCC    $25f8         
$25D7  90 20         BCC    $25f9         
$25D9  90 1F         BCC    $25fa         
$25DB  90 1D         BCC    $25fa         
$25DD  9F            DCB    $9f           ; Unknown opcode
$25DE  1A            DCB    $1a           ; Unknown opcode
$25DF  7E 8A 7E      ROR    $7e8a,X       
$25E2  7F            DCB    $7f           ; Unknown opcode
$25E3  8F            DCB    $8f           ; Unknown opcode
$25E4  00            BRK                  
$25E5  00            BRK                  
$25E6  00            BRK                  
$25E7  00            BRK                  
$25E8  00            BRK                  
$25E9  00            BRK                  
$25EA  00            BRK                  
$25EB  87            DCB    $87           ; Unknown opcode
$25EC  00            BRK                  
$25ED  B2            DCB    $b2           ; Unknown opcode
$25EE  85 22         STA    $22           
$25F0  DB            DCB    $db           ; Unknown opcode
$25F1  9D 24 C3      STA    $c324,X       
$25F4  8B            DCB    $8b           ; Unknown opcode
$25F5  7E 83 00      ROR    $0083,X       
$25F8  81 21         STA    ($21,X)       
$25FA  1D 80 24      ORA    $2480,X       
$25FD  DD 9A 26      CMP    $269a,X       
$2600  93            DCB    $93           ; Unknown opcode
$2601  29 C3         AND    #$c3          
$2603  87            DCB    $87           ; Unknown opcode
$2604  7E DD 97      ROR    $97dd,X       
$2607  2D 97 2B      AND    $2b97         
$260A  C3            DCB    $c3           ; Unknown opcode
$260B  7E 85 00      ROR    $0085,X       
$260E  80            DCB    $80           ; Unknown opcode
$260F  26 00         ROL    $00           
$2611  81 29         STA    ($29,X)       
$2613  91 2B         STA    ($2b),Y       
$2615  91 30         STA    ($30),Y       
$2617  80            DCB    $80           ; Unknown opcode
$2618  29 DD         AND    #$dd          
$261A  92            DCB    $92           ; Unknown opcode
$261B  2B            DCB    $2b           ; Unknown opcode
$261C  95 29         STA    $29,X         
$261E  C3            DCB    $c3           ; Unknown opcode
$261F  89            DCB    $89           ; Unknown opcode
$2620  7E 83 00      ROR    $0083,X       
$2623  80            DCB    $80           ; Unknown opcode
$2624  26 00         ROL    $00           
$2626  81 29         STA    ($29,X)       
$2628  91 2B         STA    ($2b),Y       
$262A  91 35         STA    ($35),Y       
$262C  B2            DCB    $b2           ; Unknown opcode
$262D  80            DCB    $80           ; Unknown opcode
$262E  32            DCB    $32           ; Unknown opcode
$262F  DD 90 34      CMP    $3490,X       
$2632  7F            DCB    $7f           ; Unknown opcode
$2633  81 7E         STA    ($7e,X)       
$2635  C0 95         CPY    #$95          
$2637  30 C3         BMI    $25fc         
$2639  87            DCB    $87           ; Unknown opcode
$263A  7E 80 35      ROR    $3580,X       
$263D  C0 92         CPY    #$92          
$263F  37            DCB    $37           ; Unknown opcode
$2640  97            DCB    $97           ; Unknown opcode
$2641  34            DCB    $34           ; Unknown opcode
$2642  C1 80         CMP    ($80,X)       
$2644  39 DC 90      AND    $90dc,Y       
$2647  3B            DCB    $3b           ; Unknown opcode
$2648  C1 91         CMP    ($91,X)       
$264A  3C            DCB    $3c           ; Unknown opcode
$264B  C1 91         CMP    ($91,X)       
$264D  39 80 37      AND    $3780,Y       
$2650  00            BRK                  
$2651  32            DCB    $32           ; Unknown opcode
$2652  C0 90         CPY    #$90          
$2654  34            DCB    $34           ; Unknown opcode
$2655  91 32         STA    ($32),Y       
$2657  C1 91         CMP    ($91,X)       
$2659  30 90         BMI    $25eb         
$265B  2D 90 2B      AND    $2b90         
$265E  C3            DCB    $c3           ; Unknown opcode
$265F  97            DCB    $97           ; Unknown opcode
$2660  29 81         AND    #$81          
$2662  00            BRK                  
$2663  2E 91 2D      ROL    $2d91         
$2666  91 30         STA    ($30),Y       
$2668  B2            DCB    $b2           ; Unknown opcode
$2669  29 C0         AND    #$c0          
$266B  95 2B         STA    $2b,X         
$266D  C1 80         CMP    ($80,X)       
$266F  2D 84 00      AND    $0084         
$2672  80            DCB    $80           ; Unknown opcode
$2673  29 C0         AND    #$c0          
$2675  90 2B         BCC    $26a2         
$2677  C3            DCB    $c3           ; Unknown opcode
$2678  83            DCB    $83           ; Unknown opcode
$2679  7E 80 2D      ROR    $2d80,X       
$267C  82            DCB    $82           ; Unknown opcode
$267D  00            BRK                  
$267E  80            DCB    $80           ; Unknown opcode
$267F  24 DE         BIT    $de           
$2681  00            BRK                  
$2682  81 2B         STA    ($2b,X)       
$2684  C2            DCB    $c2           ; Unknown opcode
$2685  83            DCB    $83           ; Unknown opcode
$2686  7E 80 2D      ROR    $2d80,X       
$2689  82            DCB    $82           ; Unknown opcode
$268A  00            BRK                  
$268B  80            DCB    $80           ; Unknown opcode
$268C  22            DCB    $22           ; Unknown opcode
$268D  DE 00 81      DEC    $8100,X       
$2690  2B            DCB    $2b           ; Unknown opcode
$2691  90 2C         BCC    $26bf         
$2693  90 2B         BCC    $26c0         
$2695  91 29         STA    ($29),Y       
$2697  80            DCB    $80           ; Unknown opcode
$2698  2D 00 30      AND    $3000         
$269B  DE 00 1D      DEC    $1d00,X       
$269E  DE 00 81      DEC    $8100,X       
$26A1  2B            DCB    $2b           ; Unknown opcode
$26A2  C3            DCB    $c3           ; Unknown opcode
$26A3  83            DCB    $83           ; Unknown opcode
$26A4  7E 80 30      ROR    $3080,X       
$26A7  00            BRK                  
$26A8  32            DCB    $32           ; Unknown opcode
$26A9  DE 00 26      DEC    $2600,X       
$26AC  DE 00 85      DEC    $8500,X       
$26AF  2D 7F A1      AND    $a17f         
$26B2  83            DCB    $83           ; Unknown opcode
$26B3  11 A6         ORA    ($a6),Y       
$26B5  81 3C         STA    ($3c,X)       
$26B7  A7            DCB    $a7           ; Unknown opcode
$26B8  45 B3         EOR    $b3           
$26BA  18            CLC                  
$26BB  A7            DCB    $a7           ; Unknown opcode
$26BC  48            PHA                  
$26BD  A4 80         LDY    $80           
$26BF  11 00         ORA    ($00),Y       
$26C1  A1 83         LDA    ($83,X)       
$26C3  11 81         ORA    ($81),Y       
$26C5  00            BRK                  
$26C6  A6 3C         LDX    $3c           
$26C8  A7            DCB    $a7           ; Unknown opcode
$26C9  43            DCB    $43           ; Unknown opcode
$26CA  B3            DCB    $b3           ; Unknown opcode
$26CB  18            CLC                  
$26CC  A7            DCB    $a7           ; Unknown opcode
$26CD  48            PHA                  
$26CE  A4 83         LDY    $83           
$26D0  15 A1         ORA    $a1,X         
$26D2  1A            DCB    $1a           ; Unknown opcode
$26D3  A6 81         LDX    $81           
$26D5  39 A7 41      AND    $41a7,Y       
$26D8  B3            DCB    $b3           ; Unknown opcode
$26D9  18            CLC                  
$26DA  A7            DCB    $a7           ; Unknown opcode
$26DB  48            PHA                  
$26DC  A4 80         LDY    $80           
$26DE  1A            DCB    $1a           ; Unknown opcode
$26DF  00            BRK                  
$26E0  A1 83         LDA    ($83,X)       
$26E2  1A            DCB    $1a           ; Unknown opcode
$26E3  81 00         STA    ($00,X)       
$26E5  A6 39         LDX    $39           
$26E7  A7            DCB    $a7           ; Unknown opcode
$26E8  3E B3 18      ROL    $18b3,X       
$26EB  A7            DCB    $a7           ; Unknown opcode
$26EC  48            PHA                  
$26ED  A4 1F         LDY    $1f           
$26EF  90 13         BCC    $2704         
$26F1  00            BRK                  
$26F2  A1 83         LDA    ($83,X)       
$26F4  15 A6         ORA    $a6,X         
$26F6  81 3C         STA    ($3c,X)       
$26F8  A7            DCB    $a7           ; Unknown opcode
$26F9  40            RTI                  
$26FA  B3            DCB    $b3           ; Unknown opcode
$26FB  18            CLC                  
$26FC  A7            DCB    $a7           ; Unknown opcode
$26FD  48            PHA                  
$26FE  A4 80         LDY    $80           
$2700  15 00         ORA    $00,X         
$2702  A1 83         LDA    ($83,X)       
$2704  15 81         ORA    $81,X         
$2706  00            BRK                  
$2707  A6 34         LDX    $34           
$2709  A7            DCB    $a7           ; Unknown opcode
$270A  3C            DCB    $3c           ; Unknown opcode
$270B  B3            DCB    $b3           ; Unknown opcode
$270C  18            CLC                  
$270D  A7            DCB    $a7           ; Unknown opcode
$270E  45 A3         EOR    $a3           
$2710  24 A1         BIT    $a1           
$2712  15 83         ORA    $83,X         
$2714  16 A6         ASL    $a6,X         
$2716  81 3A         STA    ($3a,X)       
$2718  A7            DCB    $a7           ; Unknown opcode
$2719  41 B3         EOR    ($b3,X)       
$271B  18            CLC                  
$271C  A7            DCB    $a7           ; Unknown opcode
$271D  4A            LSR    A             
$271E  A4 16         LDY    $16           
$2720  A1 83         LDA    ($83,X)       
$2722  0A            ASL    A             
$2723  81 00         STA    ($00,X)       
$2725  A6 35         LDX    $35           
$2727  A7            DCB    $a7           ; Unknown opcode
$2728  3E B3 18      ROL    $18b3,X       
$272B  A7            DCB    $a7           ; Unknown opcode
$272C  46 A4         LSR    $a4           
$272E  18            CLC                  
$272F  91 1A         STA    ($1a),Y       
$2731  7F            DCB    $7f           ; Unknown opcode
$2732  80            DCB    $80           ; Unknown opcode
$2733  34            DCB    $34           ; Unknown opcode
$2734  00            BRK                  
$2735  35 DE         AND    $de,X         
$2737  00            BRK                  
$2738  29 DE         AND    #$de          
$273A  00            BRK                  
$273B  81 30         STA    ($30,X)       
$273D  C2            DCB    $c2           ; Unknown opcode
$273E  83            DCB    $83           ; Unknown opcode
$273F  7E 80 37      ROR    $3780,X       
$2742  90 39         BCC    $277d         
$2744  3C            DCB    $3c           ; Unknown opcode
$2745  DE 00 2D      DEC    $2d00,X       
$2748  DE 00 81      DEC    $8100,X       
$274B  34            DCB    $34           ; Unknown opcode
$274C  C2            DCB    $c2           ; Unknown opcode
$274D  83            DCB    $83           ; Unknown opcode
$274E  7E 80 3E      ROR    $3e80,X       
$2751  00            BRK                  
$2752  39 DE 00      AND    $00de,Y       
$2755  43            DCB    $43           ; Unknown opcode
$2756  DE 00 B2      DEC    $b200,X       
$2759  3B            DCB    $3b           ; Unknown opcode
$275A  DC            DCB    $dc           ; Unknown opcode
$275B  91 3C         STA    ($3c),Y       
$275D  C3            DCB    $c3           ; Unknown opcode
$275E  82            DCB    $82           ; Unknown opcode
$275F  7E 81 3A      ROR    $3a81,X       
$2762  C0 91         CPY    #$91          
$2764  39 C1 91      AND    $91c1,Y       
$2767  37            DCB    $37           ; Unknown opcode
$2768  DC            DCB    $dc           ; Unknown opcode
$2769  91 35         STA    ($35),Y       
$276B  91 37         STA    ($37),Y       
$276D  C1 39         CMP    ($39,X)       
$276F  80            DCB    $80           ; Unknown opcode
$2770  39 C0 90      AND    $90c0,Y       
$2773  3A            DCB    $3a           ; Unknown opcode
$2774  91 39         STA    ($39),Y       
$2776  C1 91         CMP    ($91,X)       
$2778  32            DCB    $32           ; Unknown opcode
$2779  91 39         STA    ($39),Y       
$277B  91 35         STA    ($35),Y       
$277D  91 2E         STA    ($2e),Y       
$277F  91 37         STA    ($37),Y       
$2781  80            DCB    $80           ; Unknown opcode
$2782  32            DCB    $32           ; Unknown opcode
$2783  C0 92         CPY    #$92          
$2785  34            DCB    $34           ; Unknown opcode
$2786  C3            DCB    $c3           ; Unknown opcode
$2787  81 7E         STA    ($7e,X)       
$2789  90 33         BCC    $27be         
$278B  90 32         BCC    $27bf         
$278D  91 30         STA    ($30),Y       
$278F  C3            DCB    $c3           ; Unknown opcode
$2790  83            DCB    $83           ; Unknown opcode
$2791  7E 00 80      ROR    $8000,X       
$2794  32            DCB    $32           ; Unknown opcode
$2795  C0 90         CPY    #$90          
$2797  34            DCB    $34           ; Unknown opcode
$2798  91 32         STA    ($32),Y       
$279A  C1 30         CMP    ($30,X)       
$279C  80            DCB    $80           ; Unknown opcode
$279D  37            DCB    $37           ; Unknown opcode
$279E  00            BRK                  
$279F  34            DCB    $34           ; Unknown opcode
$27A0  C0 90         CPY    #$90          
$27A2  35 91         AND    $91,X         
$27A4  34            DCB    $34           ; Unknown opcode
$27A5  C0 95         CPY    #$95          
$27A7  32            DCB    $32           ; Unknown opcode
$27A8  C0 91         CPY    #$91          
$27AA  30 93         BMI    $273f         
$27AC  32            DCB    $32           ; Unknown opcode
$27AD  C3            DCB    $c3           ; Unknown opcode
$27AE  87            DCB    $87           ; Unknown opcode
$27AF  7E 85 00      ROR    $0085,X       
$27B2  A8            TAY                  
$27B3  80            DCB    $80           ; Unknown opcode
$27B4  2E 00 30      ROL    $3000         
$27B7  C0 92         CPY    #$92          
$27B9  32            DCB    $32           ; Unknown opcode
$27BA  93            DCB    $93           ; Unknown opcode
$27BB  30 7F         BMI    $283c         
```

## Data Tables

Hex dumps of the music data tables embedded in the SID file.

### Wave Table

**Location:** $1914-$1954 (65 bytes)

Note offsets and waveform selections

```
$1914: 07 C4 AC C0 BC 0C C0 00  0F C0 00 76 74 14 B4 12  ...........vt...
$1924: 00 18 00 00 1B 00 1D C5  00 20 00 22 C0 00 25 00  ......... ."..%.
$1934: 27 00 29 C7 AE A5 C0 2E  00 30 88 00 81 00 00 0F  '.)......0......
$1944: 7F 88 7F 88 0F 0F 00 7F  88 00 0F 00 7F 86 00 0F  ................
$1954: 00                                                .               
```

### Filter Table

**Location:** $1A1E-$1A4E (49 bytes)

Filter cutoff and resonance programs

```
$1A1E: B3 1A 1A 1A D1 D5 F7 97  EC 57 BA 3B FC AE 30 47  .........W.;..0G
$1A2E: 5E 75 28 4C 6E 80 99 A9  CB 2E 99 BA DB A7 B9 CD  ^u(Ln...........
$1A3E: 25 F3 B1 62 AD B9 C0 E1  31 AF 30 1A 1A 1A 1B 1B  %..b....1.0.....
$1A4E: 1C                                                .               
```

### Pulse Table

**Location:** $1A3B-$1A7B (65 bytes)

Pulse width modulation programs

```
$1A3B: A7 B9 CD 25 F3 B1 62 AD  B9 C0 E1 31 AF 30 1A 1A  ...%..b....1.0..
$1A4B: 1A 1B 1B 1C 1C 1D 1D 1E  1F 1F 1F 1F 20 20 20 20  ............    
$1A5B: 20 20 20 21 21 21 21 22  22 22 23 23 24 25 25 25     !!!!"""##$%%%
$1A6B: 25 25 26 26 27 A0 0E 0F  0F 0F 0F 11 01 05 01 04  %%&&'...........
$1A7B: AC                                                .               
```

### Instrument Table

**Location:** $1A6B-$1AAB (65 bytes)

Instrument definitions (ADSR, table pointers, flags)

```
$1A6B: 25 25 26 26 27 A0 0E 0F  0F 0F 0F 11 01 05 01 04  %%&&'...........
$1A7B: AC 02 03 A0 13 14 13 15  0E 11 01 05 01 04 AC 02  ................
$1A8B: 1B A0 13 14 13 15 1C 1C  1C 1C AC 02 1F 20 FF 00  ............. ..
$1A9B: A0 00 12 06 06 06 07 25  25 16 17 06 06 18 25 25  .......%%.....%%
$1AAB: 06                                                .               
```

### Arpeggio Table

**Location:** $1A8B-$1ACB (65 bytes)

Arpeggio note offset patterns

```
$1A8B: 1B A0 13 14 13 15 1C 1C  1C 1C AC 02 1F 20 FF 00  ............. ..
$1A9B: A0 00 12 06 06 06 07 25  25 16 17 06 06 18 25 25  .......%%.....%%
$1AAB: 06 06 06 06 1D 21 FF 00  A0 0A 0A 0B 0C A2 0A A0  .....!..........
$1ABB: 10 08 09 19 AC 0D A0 0B  10 08 09 1A AC 0D 23 24  ..............#$
$1ACB: 26                                                &               
```

### Command Table

**Location:** $1ADB-$1B9B (193 bytes)

Effect commands (slide, vibrato, etc.)

```
$1ADB: C4 A9 39 C4 A0 83 39 80  39 00 83 39 C5 81 3A C5  ..9...9.9..9..:.
$1AEB: A9 3A C4 A0 85 39 C4 A9  81 39 39 7F CA A0 81 30  .:...9...99....0
$1AFB: 30 80 30 00 CA A9 81 30  CA A0 83 30 CB 80 2B 00  0.0....0...0..+.
$1B0B: C4 85 2D C4 A9 81 2D D0  2D 2D C4 A0 80 2D 00 81  ..-...-.--...-..
$1B1B: 2D C4 A9 2D CA A0 2E 2E  80 2E 00 CA A9 81 2E CA  -..-............
$1B2B: A0 83 2E CB 80 29 00 C4  85 2B C4 A9 81 2B D0 2B  .....)...+...+.+
$1B3B: 2B C4 A0 80 2B 00 81 2B  C4 A9 2B CA A0 2D 2D 80  +...+..+..+..--.
$1B4B: 2D 00 CA A9 81 2D CA A0  83 2D CB 80 28 00 C6 85  -....-...-..(...
$1B5B: 29 80 29 00 C6 A9 81 29  C6 A0 80 29 00 81 29 C6  ).)....)...)..).
$1B6B: A9 29 29 CA A0 2B 2B 80  2B 00 CA A9 81 2B CA A0  .))..++.+....+..
$1B7B: 83 2B CB 80 26 00 CC 85  29 CC A9 81 29 D0 29 29  .+..&...)...).))
$1B8B: CC A0 80 29 00 29 00 CC  A9 81 29 7F CB A9 81 29  ...).)....)....)
$1B9B: CB                                                .               
```

## Music Data

**Location:** $1C00-$27BA

Pattern and sequence data for the music composition.

```
$1C00: C6 A0 80 35 00 C7 83 37  81 37 C7 A9 37 C6 A0 86  ...5...7.7..7...
$1C10: 35 80 00 C9 34 00 34 00  83 34 81 34 C9 A9 34 C9  5...4.4..4.4..4.
$1C20: A0 80 34 00 CA 83 35 81  35 CA A9 35 C9 A0 83 34  ..4...5.5..5...4
$1C30: 80 34 00 C6 81 30 C6 A9  30 C6 A0 83 30 C4 80 32  .4...0..0...0..2
$1C40: 00 85 32 C4 A9 81 32 D0  32 32 D0 32 D0 32 32 D0  ..2...2.22.2.22.
$1C50: 32 D0 32 32 D0 32 7F C6  A0 81 35 35 35 C6 A9 35  2.22.2....555..5
$1C60: C6 A0 83 35 80 35 00 C7  83 37 80 37 00 C7 A9 37  ...5.5...7.7...7
$1C70: 00 C6 A0 86 35 80 00 C8  32 00 C9 81 34 34 34 C9  ....5...2...444.
$1C80: A9 80 34 00 C9 A0 83 34  80 34 00 CA 83 35 81 35  ..4....4.4...5.5
$1C90: CA A9 80 35 00 C9 A0 83  34 80 34 00 C6 83 30 30  ...5....4.4...00
$1CA0: C4 80 32 00 85 32 C4 A9  81 32 D0 32 32 D0 32 D0  ..2..2...2.22.2.
$1CB0: 32 32 D0 32 D0 32 32 D0  32 7F A1 83 11 A6 81 3C  22.2.22.2......<
$1CC0: A7 45 A2 18 A7 48 A4 80  11 00 A1 83 11 81 00 A6  .E...H..........
$1CD0: 3C A7 43 A2 18 A7 48 A4  83 15 A1 1A A6 81 39 A7  <.C...H.......9.
$1CE0: 41 A2 18 A7 48 A4 80 1A  00 A1 83 1A 81 00 A6 39  A...H..........9
$1CF0: A7 3E A2 18 A7 48 A4 1F  90 13 00 A1 83 15 A6 81  .>...H..........
$1D00: 3C A7 40 A2 18 A7 48 A4  80 15 00 A1 83 15 81 00  <.@...H.........
$1D10: A6 34 A7 3C A2 18 A7 45  A3 24 A1 15 83 16 A6 81  .4.<...E.$......
$1D20: 3A A7 41 A2 18 A7 4A A4  16 A1 83 0A 81 00 A6 35  :.A...J........5
$1D30: A7 3E A2 18 A7 46 A4 18  91 1A 7F A1 83 18 A6 81  .>...F..........
$1D40: 43 A7 48 A2 83 18 A4 80  18 00 A1 83 11 80 1D 00  C.H.............
$1D50: A6 81 43 A7 45 A2 18 A1  15 A4 18 91 17 A1 83 16  ..C.E...........
$1D60: A6 81 41 A7 46 A2 83 18  A4 80 16 00 A1 81 1B 91  ..A.F...........
$1D70: 16 0F A7 41 A6 43 A2 18  A1 1F A4 1B 91 1A A1 83  ...A.C..........
$1D80: 19 A6 81 40 A1 15 A2 18  A4 10 95 0E 81 1A A6 40  ...@...........@
$1D90: A7 41 A2 18 A1 15 A3 24  A1 80 15 00 83 17 A6 81  .A.....$........
$1DA0: 3E A7 43 A2 83 18 A4 80  11 00 A1 85 13 A6 81 3B  >.C............;
$1DB0: A7 41 A2 18 A1 80 11 00  A4 81 13 91 15 A1 83 16  .A..............
$1DC0: A6 81 3A A7 3E A2 18 A7  45 A4 80 11 00 A1 85 0A  ..:.>...E.......
$1DD0: A7 81 3A A6 3E A2 18 A6  43 A3 83 24 A1 18 A6 81  ..:.>...C..$....
$1DE0: 3C A7 40 A2 18 A7 45 A4  80 13 00 A1 85 0C A6 81  <.@...E.........
$1DF0: 37 A7 3C B3 18 A7 83 43  B3 81 18 7F 87 00 A8 80  7.<....C........

; ... 2491 more bytes ($1E00-$27BA) ...
```

---

*Generated by SIDM2 Complete Disassembly Tool*
*Source: SF2packed_Stinsens_Last_Night_of_89.sid*
