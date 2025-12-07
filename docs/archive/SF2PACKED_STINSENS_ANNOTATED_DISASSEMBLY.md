# Complete Annotated Disassembly: Stinsen 89 SF2 packed

**Author:** MIT

**Player Type:** SID Factory II SF2-Packed Format

---

## File Information

- **Format:** PSID v2
- **Load Address:** $1000
- **Init Address:** $1000
- **Play Address:** $1006
- **Data Size:** 6,075 bytes
- **End Address:** $27BA

## Memory Map

| Address Range | Description |
|---------------|-------------|
| $1000-$1048 | Jump table and header |
| $1000-1006 | Init routine |
| $1006-$1900 | Play routine and player code |
| $1914-$1954 | Wave table |
| $1A1E-$1A4E | Filter table |
| $1A3B-$1A7B | Pulse table |
| $1A6B-$1AAB | Instrument table |
| $1A8B-$1ACB | Arpeggio table |
| $1ADB-$1B9B | Command table |
| $1C00-$27BA | Music data |

## Key Player Variables (Zero Page & RAM)

| Address | Size | Description |
|---------|------|-------------|
| $FC-$FD | 2    | Temporary pointer for table/sequence access |
| $FE-$FF | 2    | Secondary pointer for data structures |
| $1780   | 1    | Tempo counter (frames per row) |
| $1781   | 1    | Player state flags |
| $1782   | 1    | Current subtune number |
| $1783   | 1    | Frame counter / timing |
| $178F+X | 3    | Per-voice: Note duration counter |
| $1792+X | 3    | Per-voice: Sequence position |
| $1795+X | 3    | Per-voice: Active flag |
| $1798+X | 3    | Per-voice: Wave table position |
| $179B+X | 3    | Per-voice: Current instrument |
| $17B0+X | 3    | Per-voice: Transpose value |
| $17F8+X | 3    | Per-voice: Speed/timing flags |

## Annotated Disassembly

### Init Routine ($1000-$1005)

```asm
;===============================================================================
; Init Routine - Called once to initialize the player
; Entry: A = subtune number (0-based)
;===============================================================================

Init:
$1000  4C 92 16      JMP     $1692       
$1003  4C 9B 16      JMP     $169B       
```

### Play Routine ($1006 and beyond)

The play routine is called 50 times per second (PAL) to update the music.

```asm
;===============================================================================
; Main Play Loop - Processes each voice and updates SID registers
;===============================================================================

Play:

;---------------------------------------------------------------
; Play Routine Entry Point
;---------------------------------------------------------------
$1006  A9 00         LDA     #$00        
$1008  2C 81 17      BIT     $1781       
$100B  30 44         BMI     L_1051        ; Jump forward 68 bytes
$100D  70 38         BVS     L_1047        ; Jump forward 56 bytes
$100F  A2 75         LDX     #$75        

L_1011:
$1011  9D 82 17      STA     $1782,X     
$1014  CA            DEX                 
$1015  D0 FA         BNE     L_1011        ; Jump back 6 bytes
$1017  AE 82 17      LDX     $1782       
$101A  BD FB 17      LDA     $17FB,X     
$101D  8D 80 17      STA     $1780       
$1020  8D 84 17      STA     $1784       
$1023  BD FC 17      LDA     $17FC,X     
$1026  29 0F         AND     #$0F        
$1028  8D 85 17      STA     $1785       
$102B  BD FC 17      LDA     $17FC,X     
$102E  29 70         AND     #$70        
$1030  8D 86 17      STA     $1786       
$1033  A9 02         LDA     #$02        
$1035  8D 83 17      STA     $1783       
$1038  8D F8 17      STA     $17F8       
$103B  8D F9 17      STA     $17F9       
$103E  8D FA 17      STA     $17FA       
$1041  A9 80         LDA     #$80        
$1043  8D 81 17      STA     $1781       
$1046  60            RTS                 

L_1047:
$1047  8D 04 D4      STA     $D404         ; Voice 1 Control Register
$104A  8D 0B D4      STA     $D40B         ; Voice 2 Control Register
$104D  8D 12 D4      STA     $D412         ; Voice 3 Control Register
$1050  60            RTS                 

L_1051:
$1051  CE 83 17      DEC     $1783       
$1054  10 17         BPL     L_106D        ; Jump forward 23 bytes
$1056  AE 84 17      LDX     $1784       
$1059  BD 19 1A      LDA     $1A19,X     
$105C  8D 83 17      STA     $1783       
$105F  E8            INX                 
$1060  BD 19 1A      LDA     $1A19,X     
$1063  C9 7F         CMP     #$7F          ; Check for end marker
$1065  D0 03         BNE     L_106A        ; Jump forward 3 bytes
$1067  AE 80 17      LDX     $1780       

L_106A:
$106A  8E 84 17      STX     $1784       

L_106D:
$106D  A2 02         LDX     #$02        
$106F  BD F8 17      LDA     $17F8,X     
$1072  C9 01         CMP     #$01          ; Check if == 1
$1074  D0 39         BNE     L_10AF        ; Jump forward 57 bytes
$1076  BD 95 17      LDA     $1795,X     
$1079  D0 34         BNE     L_10AF        ; Jump forward 52 bytes
$107B  FE 95 17      INC     $1795,X     
$107E  BD 1C 1A      LDA     $1A1C,X     
$1081  85 FC         STA     $FC           ; Pointer low/high byte
$1083  BD 1F 1A      LDA     $1A1F,X     
$1086  85 FD         STA     $FD           ; Pointer low/high byte
$1088  BC 92 17      LDY     $1792,X     
$108B  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$108D  10 09         BPL     L_1098        ; Jump forward 9 bytes
$108F  38            SEC                 
$1090  E9 A0         SBC     #$A0        
$1092  9D B0 17      STA     $17B0,X     
$1095  C8            INY                 
$1096  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte

L_1098:
$1098  9D 9B 17      STA     $179B,X     
$109B  C8            INY                 
$109C  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$109E  C9 FF         CMP     #$FF          ; Check for loop marker
$10A0  D0 04         BNE     L_10A6        ; Jump forward 4 bytes
$10A2  C8            INY                 
$10A3  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$10A5  A8            TAY                 

L_10A6:
$10A6  98            TYA                 
$10A7  9D 92 17      STA     $1792,X     
$10AA  A9 00         LDA     #$00        
$10AC  9D 98 17      STA     $1798,X     

L_10AF:
$10AF  AD 83 17      LDA     $1783       
$10B2  D0 6D         BNE     L_1121        ; Jump forward 109 bytes
$10B4  DE 8F 17      DEC     $178F,X     
$10B7  10 68         BPL     L_1121        ; Jump forward 104 bytes
$10B9  BC 9B 17      LDY     $179B,X     
$10BC  B9 22 1A      LDA     $1A22,Y     
$10BF  85 FC         STA     $FC           ; Pointer low/high byte
$10C1  B9 49 1A      LDA     $1A49,Y     
$10C4  85 FD         STA     $FD           ; Pointer low/high byte
$10C6  BC 98 17      LDY     $1798,X     
$10C9  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$10CB  10 27         BPL     L_10F4        ; Jump forward 39 bytes
$10CD  C9 C0         CMP     #$C0        
$10CF  90 08         BCC     L_10D9        ; Jump forward 8 bytes
$10D1  9D AA 17      STA     $17AA,X     
$10D4  C8            INY                 
$10D5  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$10D7  10 1B         BPL     L_10F4        ; Jump forward 27 bytes

L_10D9:
$10D9  C9 A0         CMP     #$A0        
$10DB  90 08         BCC     L_10E5        ; Jump forward 8 bytes
$10DD  9D A7 17      STA     $17A7,X     
$10E0  C8            INY                 
$10E1  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$10E3  10 0F         BPL     L_10F4        ; Jump forward 15 bytes

L_10E5:
$10E5  C9 90         CMP     #$90        
$10E7  90 03         BCC     L_10EC        ; Jump forward 3 bytes
$10E9  FE A1 17      INC     $17A1,X     

L_10EC:
$10EC  29 0F         AND     #$0F        
$10EE  9D 9E 17      STA     $179E,X     
$10F1  C8            INY                 
$10F2  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte

L_10F4:
$10F4  9D A4 17      STA     $17A4,X     
$10F7  F0 04         BEQ     L_10FD        ; Jump forward 4 bytes
$10F9  C9 7E         CMP     #$7E        
$10FB  D0 05         BNE     L_1102        ; Jump forward 5 bytes

L_10FD:
$10FD  FE A1 17      INC     $17A1,X     
$1100  D0 06         BNE     L_1108        ; Jump forward 6 bytes

L_1102:
$1102  BD B0 17      LDA     $17B0,X     
$1105  9D B3 17      STA     $17B3,X     

L_1108:
$1108  C8            INY                 
$1109  98            TYA                 
$110A  9D 98 17      STA     $1798,X     
$110D  BD 9E 17      LDA     $179E,X     
$1110  9D 8F 17      STA     $178F,X     
$1113  A9 02         LDA     #$02        
$1115  9D F8 17      STA     $17F8,X     
$1118  B1 FC         LDA     ($FC),Y       ; Pointer low/high byte
$111A  C9 7F         CMP     #$7F          ; Check for end marker
$111C  D0 03         BNE     L_1121        ; Jump forward 3 bytes
$111E  DE 95 17      DEC     $1795,X     

L_1121:
$1121  BC F8 17      LDY     $17F8,X     
$1124  30 36         BMI     L_115C        ; Jump forward 54 bytes
$1126  BD A1 17      LDA     $17A1,X     
$1129  D0 31         BNE     L_115C        ; Jump forward 49 bytes
$112B  C0 01         CPY     #$01        
$112D  F0 23         BEQ     L_1152        ; Jump forward 35 bytes
$112F  C0 00         CPY     #$00        
$1131  F0 2C         BEQ     L_115F        ; Jump forward 44 bytes
$1133  BD A7 17      LDA     $17A7,X     
$1136  29 1F         AND     #$1F        
$1138  A8            TAY                 
$1139  B9 25 18      LDA     $1825,Y     
$113C  10 0F         BPL     L_114D        ; Jump forward 15 bytes
$113E  29 0F         AND     #$0F        
$1140  A8            TAY                 
$1141  B9 D8 18      LDA     $18D8,Y     
$1144  9D EF 17      STA     $17EF,X     
$1147  B9 D9 18      LDA     $18D9,Y     
$114A  9D F2 17      STA     $17F2,X     

L_114D:
$114D  A9 FE         LDA     #$FE        
$114F  9D F5 17      STA     $17F5,X     

L_1152:
$1152  BD BC 17      LDA     $17BC,X     
$1155  C9 04         CMP     #$04        
$1157  B0 03         BCS     L_115C        ; Jump forward 3 bytes
$1159  4C 40 15      JMP     $1540       

L_115C:
$115C  4C 79 13      JMP     $1379       

L_115F:
$115F  A9 FF         LDA     #$FF        
$1161  9D F5 17      STA     $17F5,X     
$1164  BD A7 17      LDA     $17A7,X     
$1167  10 36         BPL     L_119F        ; Jump forward 54 bytes
$1169  29 1F         AND     #$1F        
$116B  9D AD 17      STA     $17AD,X     
$116E  9D A7 17      STA     $17A7,X     
$1171  A8            TAY                 
$1172  B9 FD 17      LDA     $17FD,Y     
$1175  9D D4 17      STA     $17D4,X     
$1178  9D EF 17      STA     $17EF,X     
$117B  B9 11 18      LDA     $1811,Y     
$117E  9D D7 17      STA     $17D7,X     
$1181  9D F2 17      STA     $17F2,X     
$1184  B9 25 18      LDA     $1825,Y     
$1187  29 20         AND     #$20        
$1189  F0 08         BEQ     L_1193        ; Jump forward 8 bytes
$118B  AD 8B 17      LDA     $178B       
$118E  1D 7A 17      ORA     $177A,X     
$1191  D0 06         BNE     L_1199        ; Jump forward 6 bytes

L_1193:
$1193  AD 8B 17      LDA     $178B       
$1196  3D 7D 17      AND     $177D,X     

L_1199:
$1199  8D 8B 17      STA     $178B       
$119C  4C C8 11      JMP     $11C8       

L_119F:
$119F  BC AD 17      LDY     $17AD,X     
$11A2  BD D4 17      LDA     $17D4,X     
$11A5  9D EF 17      STA     $17EF,X     
$11A8  BD D7 17      LDA     $17D7,X     
$11AB  9D F2 17      STA     $17F2,X     
$11AE  BD BC 17      LDA     $17BC,X     
$11B1  C9 03         CMP     #$03        
$11B3  F0 18         BEQ     L_11CD        ; Jump forward 24 bytes
$11B5  C9 04         CMP     #$04        
$11B7  D0 0F         BNE     L_11C8        ; Jump forward 15 bytes
$11B9  BD CE 17      LDA     $17CE,X     
$11BC  9D D1 17      STA     $17D1,X     
$11BF  BD CB 17      LDA     $17CB,X     
$11C2  9D C8 17      STA     $17C8,X     
$11C5  4C CD 11      JMP     $11CD       

L_11C8:
$11C8  A9 00         LDA     #$00        
$11CA  9D BC 17      STA     $17BC,X     

L_11CD:
$11CD  B9 25 18      LDA     $1825,Y     
$11D0  29 10         AND     #$10        
$11D2  4A            LSR     A           
$11D3  09 01         ORA     #$01        
$11D5  9D EC 17      STA     $17EC,X     
$11D8  B9 25 18      LDA     $1825,Y     
$11DB  29 40         AND     #$40        
$11DD  F0 12         BEQ     L_11F1        ; Jump forward 18 bytes
$11DF  0A            ASL     A           
$11E0  8D 8C 17      STA     $178C       
$11E3  B9 39 18      LDA     $1839,Y     
$11E6  8D 8E 17      STA     $178E       
$11E9  CE 8E 17      DEC     $178E       
$11EC  A9 00         LDA     #$00        
$11EE  8D 8D 17      STA     $178D       

L_11F1:
$11F1  B9 61 18      LDA     $1861,Y     
$11F4  9D BF 17      STA     $17BF,X     
$11F7  B9 4D 18      LDA     $184D,Y     
$11FA  9D C2 17      STA     $17C2,X     
$11FD  A9 00         LDA     #$00        
$11FF  9D C5 17      STA     $17C5,X     
$1202  BD AA 17      LDA     $17AA,X     
$1205  30 03         BMI     L_120A        ; Jump forward 3 bytes
$1207  4C 1F 13      JMP     $131F       

L_120A:
$120A  29 3F         AND     #$3F        
$120C  9D AA 17      STA     $17AA,X     
$120F  A8            TAY                 
$1210  B9 75 18      LDA     $1875,Y     
$1213  29 0F         AND     #$0F        
$1215  A8            TAY                 
$1216  B9 61 17      LDA     $1761,Y     
$1219  8D 88 12      STA     $1288       
$121C  BC AA 17      LDY     $17AA,X     
$121F  4C 86 12      JMP     $1286       

L_1222:
$1222  B9 96 18      LDA     $1896,Y     
$1225  9D CB 17      STA     $17CB,X     
$1228  B9 B7 18      LDA     $18B7,Y     
$122B  9D C8 17      STA     $17C8,X     
$122E  A9 01         LDA     #$01        
$1230  4C 1C 13      JMP     $131C       
$1233  B9 96 18      LDA     $1896,Y     
$1236  9D CB 17      STA     $17CB,X     
$1239  B9 B7 18      LDA     $18B7,Y     
$123C  9D C8 17      STA     $17C8,X     
$123F  A9 03         LDA     #$03        
$1241  4C 1C 13      JMP     $131C       
$1244  B9 96 18      LDA     $1896,Y     
$1247  30 2F         BMI     L_1278        ; Jump forward 47 bytes
$1249  9D CB 17      STA     $17CB,X     
$124C  9D C8 17      STA     $17C8,X     
$124F  B9 B7 18      LDA     $18B7,Y     
$1252  9D CE 17      STA     $17CE,X     
$1255  9D D1 17      STA     $17D1,X     
$1258  A9 04         LDA     #$04        
$125A  4C 1C 13      JMP     $131C       
$125D  B9 96 18      LDA     $1896,Y     
$1260  9D CB 17      STA     $17CB,X     
$1263  29 7F         AND     #$7F        
$1265  9D C8 17      STA     $17C8,X     
$1268  B9 B7 18      LDA     $18B7,Y     
$126B  9D D1 17      STA     $17D1,X     
$126E  A9 00         LDA     #$00        
$1270  9D CE 17      STA     $17CE,X     
$1273  A9 05         LDA     #$05        
$1275  4C 1C 13      JMP     $131C       

L_1278:
$1278  4C 1A 13      JMP     $131A       
$127B  B9 B7 18      LDA     $18B7,Y     
$127E  29 0F         AND     #$0F        
$1280  8D 85 17      STA     $1785       
$1283  4C 1F 13      JMP     $131F       
$1286  38            SEC                 
$1287  B0 99         BCS     L_1222        ; Jump back 103 bytes
$1289  B9 B7 18      LDA     $18B7,Y     
$128C  29 0F         AND     #$0F        
$128E  9D C8 17      STA     $17C8,X     
$1291  B9 96 18      LDA     $1896,Y     
$1294  18            CLC                 
$1295  69 01         ADC     #$01        
$1297  9D CB 17      STA     $17CB,X     
$129A  4A            LSR     A           
$129B  90 02         BCC     L_129F        ; Jump forward 2 bytes
$129D  09 80         ORA     #$80        

L_129F:
$129F  9D CE 17      STA     $17CE,X     
$12A2  A9 02         LDA     #$02        
$12A4  9D D1 17      STA     $17D1,X     
$12A7  4C 1C 13      JMP     $131C       
$12AA  B9 96 18      LDA     $1896,Y     
$12AD  9D EF 17      STA     $17EF,X     
$12B0  B9 B7 18      LDA     $18B7,Y     
$12B3  9D F2 17      STA     $17F2,X     
$12B6  4C 1F 13      JMP     $131F       
$12B9  B9 96 18      LDA     $1896,Y     
$12BC  9D D4 17      STA     $17D4,X     
$12BF  9D EF 17      STA     $17EF,X     
$12C2  B9 B7 18      LDA     $18B7,Y     
$12C5  9D D7 17      STA     $17D7,X     
$12C8  9D F2 17      STA     $17F2,X     
$12CB  4C 1F 13      JMP     $131F       
$12CE  B9 B7 18      LDA     $18B7,Y     
$12D1  9D BF 17      STA     $17BF,X     
$12D4  4C 1F 13      JMP     $131F       
$12D7  A9 80         LDA     #$80        
$12D9  8D 8C 17      STA     $178C       
$12DC  B9 B7 18      LDA     $18B7,Y     
$12DF  8D 8E 17      STA     $178E       
$12E2  CE 8E 17      DEC     $178E       
$12E5  A9 00         LDA     #$00        
$12E7  8D 8D 17      STA     $178D       
$12EA  4C 1F 13      JMP     $131F       
$12ED  B9 B7 18      LDA     $18B7,Y     
$12F0  9D C2 17      STA     $17C2,X     
$12F3  A9 00         LDA     #$00        
$12F5  9D C5 17      STA     $17C5,X     
$12F8  4C 1F 13      JMP     $131F       
$12FB  B9 B7 18      LDA     $18B7,Y     
$12FE  8D 80 17      STA     $1780       
$1301  8D 84 17      STA     $1784       
$1304  A8            TAY                 
$1305  B9 1A 1A      LDA     $1A1A,Y     
$1308  C9 7F         CMP     #$7F          ; Check for end marker
$130A  F0 03         BEQ     L_130F        ; Jump forward 3 bytes
$130C  EE 84 17      INC     $1784       

L_130F:
$130F  B9 19 1A      LDA     $1A19,Y     
$1312  A8            TAY                 
$1313  88            DEY                 
$1314  8C 83 17      STY     $1783       
$1317  4C 1F 13      JMP     $131F       
$131A  A9 00         LDA     #$00        
$131C  9D BC 17      STA     $17BC,X     
$131F  BD A1 17      LDA     $17A1,X     
$1322  D0 06         BNE     L_132A        ; Jump forward 6 bytes
$1324  BD A4 17      LDA     $17A4,X     
$1327  4C 3E 13      JMP     $133E       

L_132A:
$132A  BD A4 17      LDA     $17A4,X     
$132D  F0 39         BEQ     L_1368        ; Jump forward 57 bytes
$132F  C9 7E         CMP     #$7E        
$1331  F0 39         BEQ     L_136C        ; Jump forward 57 bytes
$1333  A8            TAY                 
$1334  18            CLC                 
$1335  7D B3 17      ADC     $17B3,X     
$1338  DD B9 17      CMP     $17B9,X     
$133B  F0 34         BEQ     L_1371        ; Jump forward 52 bytes
$133D  98            TYA                 
$133E  9D B6 17      STA     $17B6,X     
$1341  18            CLC                 
$1342  7D B3 17      ADC     $17B3,X     
$1345  9D B9 17      STA     $17B9,X     
$1348  A8            TAY                 
$1349  BD BC 17      LDA     $17BC,X     
$134C  C9 03         CMP     #$03        
$134E  F0 10         BEQ     L_1360        ; Jump forward 16 bytes
$1350  C9 04         CMP     #$04        
$1352  F0 0C         BEQ     L_1360        ; Jump forward 12 bytes
$1354  B9 01 17      LDA     $1701,Y     
$1357  9D DA 17      STA     $17DA,X     
$135A  B9 A1 16      LDA     $16A1,Y     
$135D  9D DD 17      STA     $17DD,X     

L_1360:
$1360  BD A1 17      LDA     $17A1,X     
$1363  D0 07         BNE     L_136C        ; Jump forward 7 bytes
$1365  4C 82 15      JMP     $1582       

L_1368:
$1368  A9 FE         LDA     #$FE        
$136A  D0 02         BNE     L_136E        ; Jump forward 2 bytes

L_136C:
$136C  A9 FF         LDA     #$FF        

L_136E:
$136E  9D F5 17      STA     $17F5,X     

L_1371:
$1371  A9 00         LDA     #$00        
$1373  9D A1 17      STA     $17A1,X     
$1376  4C E1 15      JMP     $15E1       
$1379  BD BC 17      LDA     $17BC,X     
$137C  A8            TAY                 
$137D  B9 71 17      LDA     $1771,Y     
$1380  8D 85 13      STA     $1385       
$1383  38            SEC                 
$1384  B0 0C         BCS     L_1392        ; Jump forward 12 bytes
$1386  4C F2 14      JMP     $14F2       
$1389  4C 14 14      JMP     $1414       
$138C  4C 82 14      JMP     $1482       
$138F  4C BC 14      JMP     $14BC       

L_1392:
$1392  BD DA 17      LDA     $17DA,X     
$1395  18            CLC                 
$1396  7D C8 17      ADC     $17C8,X     
$1399  9D DA 17      STA     $17DA,X     
$139C  BD DD 17      LDA     $17DD,X     
$139F  7D CB 17      ADC     $17CB,X     
$13A2  9D DD 17      STA     $17DD,X     
$13A5  4C F2 14      JMP     $14F2       
$13A8  BC B9 17      LDY     $17B9,X     
$13AB  B9 02 17      LDA     $1702,Y     
$13AE  F9 01 17      SBC     $1701,Y     
$13B1  85 FC         STA     $FC           ; Pointer low/high byte
$13B3  B9 A2 16      LDA     $16A2,Y     
$13B6  F9 A1 16      SBC     $16A1,Y     
$13B9  85 FD         STA     $FD           ; Pointer low/high byte
$13BB  BD CE 17      LDA     $17CE,X     
$13BE  C9 80         CMP     #$80        
$13C0  29 00         AND     #$00        
$13C2  7D C8 17      ADC     $17C8,X     
$13C5  A8            TAY                 
$13C6  88            DEY                 
$13C7  30 07         BMI     L_13D0        ; Jump forward 7 bytes
$13C9  46 FD         LSR     $FD         
$13CB  66 FC         ROR     $FC         
$13CD  4C C6 13      JMP     $13C6       

L_13D0:
$13D0  BD D1 17      LDA     $17D1,X     
$13D3  29 01         AND     #$01        
$13D5  D0 14         BNE     L_13EB        ; Jump forward 20 bytes
$13D7  BD DA 17      LDA     $17DA,X     
$13DA  18            CLC                 
$13DB  65 FC         ADC     $FC         
$13DD  9D DA 17      STA     $17DA,X     
$13E0  BD DD 17      LDA     $17DD,X     
$13E3  65 FD         ADC     $FD         
$13E5  9D DD 17      STA     $17DD,X     
$13E8  4C FC 13      JMP     $13FC       

L_13EB:
$13EB  BD DA 17      LDA     $17DA,X     
$13EE  38            SEC                 
$13EF  E5 FC         SBC     $FC         
$13F1  9D DA 17      STA     $17DA,X     
$13F4  BD DD 17      LDA     $17DD,X     
$13F7  E5 FD         SBC     $FD         
$13F9  9D DD 17      STA     $17DD,X     
$13FC  BD CE 17      LDA     $17CE,X     
$13FF  29 7F         AND     #$7F        
$1401  18            CLC                 
$1402  69 01         ADC     #$01        
$1404  DD CB 17      CMP     $17CB,X     
$1407  90 05         BCC     L_140E        ; Jump forward 5 bytes
$1409  FE D1 17      INC     $17D1,X     
$140C  A9 00         LDA     #$00        

L_140E:
$140E  9D CE 17      STA     $17CE,X     
$1411  4C F2 14      JMP     $14F2       
$1414  BC B9 17      LDY     $17B9,X     
$1417  B9 01 17      LDA     $1701,Y     
$141A  85 FC         STA     $FC           ; Pointer low/high byte
$141C  B9 A1 16      LDA     $16A1,Y     
$141F  85 FD         STA     $FD           ; Pointer low/high byte
$1421  BD DA 17      LDA     $17DA,X     
$1424  38            SEC                 
$1425  E5 FC         SBC     $FC         
$1427  9D DA 17      STA     $17DA,X     
$142A  BD DD 17      LDA     $17DD,X     
$142D  E5 FD         SBC     $FD         
$142F  9D DD 17      STA     $17DD,X     
$1432  30 18         BMI     L_144C        ; Jump forward 24 bytes
$1434  BD DA 17      LDA     $17DA,X     
$1437  38            SEC                 
$1438  FD C8 17      SBC     $17C8,X     
$143B  9D DA 17      STA     $17DA,X     
$143E  BD DD 17      LDA     $17DD,X     
$1441  FD CB 17      SBC     $17CB,X     
$1444  9D DD 17      STA     $17DD,X     
$1447  10 25         BPL     L_146E        ; Jump forward 37 bytes
$1449  4C 61 14      JMP     $1461       

L_144C:
$144C  BD DA 17      LDA     $17DA,X     
$144F  18            CLC                 
$1450  7D C8 17      ADC     $17C8,X     
$1453  9D DA 17      STA     $17DA,X     
$1456  BD DD 17      LDA     $17DD,X     
$1459  7D CB 17      ADC     $17CB,X     
$145C  9D DD 17      STA     $17DD,X     
$145F  30 0D         BMI     L_146E        ; Jump forward 13 bytes
$1461  A5 FC         LDA     $FC           ; Pointer low/high byte
$1463  9D DA 17      STA     $17DA,X     
$1466  A5 FD         LDA     $FD           ; Pointer low/high byte
$1468  9D DD 17      STA     $17DD,X     
$146B  4C 7F 14      JMP     $147F       

L_146E:
$146E  BD DA 17      LDA     $17DA,X     
$1471  18            CLC                 
$1472  65 FC         ADC     $FC         
$1474  9D DA 17      STA     $17DA,X     
$1477  BD DD 17      LDA     $17DD,X     
$147A  65 FD         ADC     $FD         
$147C  9D DD 17      STA     $17DD,X     
$147F  4C F2 14      JMP     $14F2       
$1482  BC D1 17      LDY     $17D1,X     
$1485  DE C8 17      DEC     $17C8,X     
$1488  10 1B         BPL     L_14A5        ; Jump forward 27 bytes
$148A  C8            INY                 
$148B  B9 D7 19      LDA     $19D7,Y     
$148E  30 0B         BMI     L_149B        ; Jump forward 11 bytes
$1490  C9 70         CMP     #$70        
$1492  30 07         BMI     L_149B        ; Jump forward 7 bytes
$1494  29 0F         AND     #$0F        
$1496  18            CLC                 
$1497  7D CE 17      ADC     $17CE,X     
$149A  A8            TAY                 

L_149B:
$149B  98            TYA                 
$149C  9D D1 17      STA     $17D1,X     
$149F  BD CB 17      LDA     $17CB,X     
$14A2  9D C8 17      STA     $17C8,X     

L_14A5:
$14A5  B9 D7 19      LDA     $19D7,Y     
$14A8  18            CLC                 
$14A9  7D B9 17      ADC     $17B9,X     
$14AC  A8            TAY                 
$14AD  B9 01 17      LDA     $1701,Y     
$14B0  9D DA 17      STA     $17DA,X     
$14B3  B9 A1 16      LDA     $16A1,Y     
$14B6  9D DD 17      STA     $17DD,X     
$14B9  4C F2 14      JMP     $14F2       
$14BC  DE C8 17      DEC     $17C8,X     
$14BF  10 31         BPL     L_14F2        ; Jump forward 49 bytes
$14C1  BD CB 17      LDA     $17CB,X     
$14C4  30 06         BMI     L_14CC        ; Jump forward 6 bytes
$14C6  FE CE 17      INC     $17CE,X     
$14C9  4C D1 14      JMP     $14D1       

L_14CC:
$14CC  DE CE 17      DEC     $17CE,X     
$14CF  29 7F         AND     #$7F        
$14D1  9D C8 17      STA     $17C8,X     
$14D4  DE D1 17      DEC     $17D1,X     
$14D7  D0 05         BNE     L_14DE        ; Jump forward 5 bytes
$14D9  A9 00         LDA     #$00        
$14DB  9D BC 17      STA     $17BC,X     

L_14DE:
$14DE  BD B9 17      LDA     $17B9,X     
$14E1  18            CLC                 
$14E2  7D CE 17      ADC     $17CE,X     
$14E5  A8            TAY                 
$14E6  B9 01 17      LDA     $1701,Y     
$14E9  9D DA 17      STA     $17DA,X     
$14EC  B9 A1 16      LDA     $16A1,Y     
$14EF  9D DD 17      STA     $17DD,X     

L_14F2:
$14F2  BC C2 17      LDY     $17C2,X     
$14F5  B9 3E 19      LDA     $193E,Y     
$14F8  C9 7F         CMP     #$7F          ; Check for end marker
$14FA  D0 0C         BNE     L_1508        ; Jump forward 12 bytes
$14FC  B9 70 19      LDA     $1970,Y     
$14FF  DD C2 17      CMP     $17C2,X     
$1502  F0 3C         BEQ     L_1540        ; Jump forward 60 bytes
$1504  9D C2 17      STA     $17C2,X     
$1507  A8            TAY                 

L_1508:
$1508  B9 3E 19      LDA     $193E,Y     
$150B  10 0C         BPL     L_1519        ; Jump forward 12 bytes
$150D  9D E9 17      STA     $17E9,X     
$1510  B9 57 19      LDA     $1957,Y     
$1513  9D E6 17      STA     $17E6,X     
$1516  4C 2D 15      JMP     $152D       

L_1519:
$1519  85 FC         STA     $FC           ; Pointer low/high byte
$151B  BD E6 17      LDA     $17E6,X     
$151E  18            CLC                 
$151F  79 57 19      ADC     $1957,Y     
$1522  9D E6 17      STA     $17E6,X     
$1525  BD E9 17      LDA     $17E9,X     
$1528  65 FC         ADC     $FC         
$152A  9D E9 17      STA     $17E9,X     
$152D  FE C5 17      INC     $17C5,X     
$1530  BD C5 17      LDA     $17C5,X     
$1533  D9 70 19      CMP     $1970,Y     
$1536  90 08         BCC     L_1540        ; Jump forward 8 bytes
$1538  FE C2 17      INC     $17C2,X     
$153B  A9 00         LDA     #$00        
$153D  9D C5 17      STA     $17C5,X     

L_1540:
$1540  BC BF 17      LDY     $17BF,X     
$1543  B9 DA 18      LDA     $18DA,Y     
$1546  C9 7F         CMP     #$7F          ; Check for end marker
$1548  D0 0A         BNE     L_1554        ; Jump forward 10 bytes
$154A  B9 0C 19      LDA     $190C,Y     
$154D  9D BF 17      STA     $17BF,X     
$1550  A8            TAY                 
$1551  B9 DA 18      LDA     $18DA,Y     

L_1554:
$1554  9D EC 17      STA     $17EC,X     
$1557  B9 0C 19      LDA     $190C,Y     
$155A  F0 17         BEQ     L_1573        ; Jump forward 23 bytes
$155C  C9 81         CMP     #$81        
$155E  B0 04         BCS     L_1564        ; Jump forward 4 bytes
$1560  18            CLC                 
$1561  7D B9 17      ADC     $17B9,X     

L_1564:
$1564  29 7F         AND     #$7F        
$1566  A8            TAY                 
$1567  B9 01 17      LDA     $1701,Y     
$156A  9D E0 17      STA     $17E0,X     
$156D  B9 A1 16      LDA     $16A1,Y     
$1570  4C 7C 15      JMP     $157C       

L_1573:
$1573  BD DA 17      LDA     $17DA,X     
$1576  9D E0 17      STA     $17E0,X     
$1579  BD DD 17      LDA     $17DD,X     
$157C  9D E3 17      STA     $17E3,X     
$157F  FE BF 17      INC     $17BF,X     
$1582  BC 77 17      LDY     $1777,X     
$1585  BD E0 17      LDA     $17E0,X     
$1588  99 00 D4      STA     $D400,Y       ; Voice 1 Frequency Lo
$158B  BD E3 17      LDA     $17E3,X     
$158E  99 01 D4      STA     $D401,Y       ; Voice 1 Frequency Hi
$1591  BD F2 17      LDA     $17F2,X     
$1594  99 06 D4      STA     $D406,Y       ; Voice 1 Sustain/Release
$1597  BD EF 17      LDA     $17EF,X     
$159A  99 05 D4      STA     $D405,Y       ; Voice 1 Attack/Decay
$159D  BD E6 17      LDA     $17E6,X     
$15A0  99 02 D4      STA     $D402,Y       ; Voice 1 Pulse Width Lo
$15A3  BD E9 17      LDA     $17E9,X     
$15A6  99 03 D4      STA     $D403,Y       ; Voice 1 Pulse Width Hi
$15A9  BD EC 17      LDA     $17EC,X     
$15AC  3D F5 17      AND     $17F5,X     
$15AF  99 04 D4      STA     $D404,Y       ; Voice 1 Control Register
$15B2  BD F8 17      LDA     $17F8,X     
$15B5  D0 2A         BNE     L_15E1        ; Jump forward 42 bytes
$15B7  BD A1 17      LDA     $17A1,X     
$15BA  F0 25         BEQ     L_15E1        ; Jump forward 37 bytes
$15BC  BD BC 17      LDA     $17BC,X     
$15BF  C9 03         CMP     #$03        
$15C1  F0 1B         BEQ     L_15DE        ; Jump forward 27 bytes
$15C3  C9 04         CMP     #$04        
$15C5  F0 17         BEQ     L_15DE        ; Jump forward 23 bytes
$15C7  BD A4 17      LDA     $17A4,X     
$15CA  F0 12         BEQ     L_15DE        ; Jump forward 18 bytes
$15CC  C9 7E         CMP     #$7E        
$15CE  F0 0E         BEQ     L_15DE        ; Jump forward 14 bytes
$15D0  18            CLC                 
$15D1  7D B3 17      ADC     $17B3,X     
$15D4  DD B9 17      CMP     $17B9,X     
$15D7  F0 05         BEQ     L_15DE        ; Jump forward 5 bytes
$15D9  A9 00         LDA     #$00        
$15DB  9D BC 17      STA     $17BC,X     

L_15DE:
$15DE  4C 02 12      JMP     $1202       

L_15E1:
$15E1  BD F8 17      LDA     $17F8,X     
$15E4  30 03         BMI     L_15E9        ; Jump forward 3 bytes
$15E6  DE F8 17      DEC     $17F8,X     

L_15E9:
$15E9  CA            DEX                 
$15EA  30 03         BMI     L_15EF        ; Jump forward 3 bytes
$15EC  4C 6F 10      JMP     $106F       

L_15EF:
$15EF  AD 8C 17      LDA     $178C       
$15F2  30 61         BMI     L_1655        ; Jump forward 97 bytes
$15F4  F0 64         BEQ     L_165A        ; Jump forward 100 bytes
$15F6  AC 8E 17      LDY     $178E       
$15F9  CE 8D 17      DEC     $178D       
$15FC  10 41         BPL     L_163F        ; Jump forward 65 bytes
$15FE  C8            INY                 
$15FF  B9 89 19      LDA     $1989,Y     
$1602  C9 7F         CMP     #$7F          ; Check for end marker
$1604  D0 12         BNE     L_1618        ; Jump forward 18 bytes
$1606  98            TYA                 
$1607  D9 BD 19      CMP     $19BD,Y     
$160A  D0 08         BNE     L_1614        ; Jump forward 8 bytes
$160C  A9 00         LDA     #$00        
$160E  8D 8C 17      STA     $178C       
$1611  4C 5A 16      JMP     $165A       

L_1614:
$1614  B9 BD 19      LDA     $19BD,Y     
$1617  A8            TAY                 

L_1618:
$1618  B9 89 19      LDA     $1989,Y     
$161B  10 1C         BPL     L_1639        ; Jump forward 28 bytes
$161D  29 70         AND     #$70        
$161F  8D 86 17      STA     $1786       
$1622  B9 89 19      LDA     $1989,Y     
$1625  29 0F         AND     #$0F        
$1627  8D 8A 17      STA     $178A       
$162A  B9 A3 19      LDA     $19A3,Y     
$162D  8D 89 17      STA     $1789       
$1630  B9 BD 19      LDA     $19BD,Y     
$1633  8D 87 17      STA     $1787       
$1636  4C 52 16      JMP     $1652       

L_1639:
$1639  B9 BD 19      LDA     $19BD,Y     
$163C  8D 8D 17      STA     $178D       

L_163F:
$163F  AD 89 17      LDA     $1789       
$1642  18            CLC                 
$1643  79 A3 19      ADC     $19A3,Y     
$1646  8D 89 17      STA     $1789       
$1649  AD 8A 17      LDA     $178A       
$164C  79 89 19      ADC     $1989,Y     
$164F  8D 8A 17      STA     $178A       
$1652  8C 8E 17      STY     $178E       

L_1655:
$1655  A9 40         LDA     #$40        
$1657  8D 8C 17      STA     $178C       

L_165A:
$165A  AD 8A 17      LDA     $178A       
$165D  85 FC         STA     $FC           ; Pointer low/high byte
$165F  AD 89 17      LDA     $1789       
$1662  46 FC         LSR     $FC         
$1664  6A            ROR     A           
$1665  AA            TAX                 
$1666  46 FC         LSR     $FC         
$1668  6A            ROR     A           
$1669  46 FC         LSR     $FC         
$166B  6A            ROR     A           
$166C  46 FC         LSR     $FC         
$166E  6A            ROR     A           
$166F  A8            TAY                 
$1670  AD 87 17      LDA     $1787       
$1673  0D 88 17      ORA     $1788       
$1676  8D 17 D4      STA     $D417         ; Filter Resonance/Routing
$1679  8C 16 D4      STY     $D416         ; Filter Cutoff Hi
$167C  8A            TXA                 
$167D  29 07         AND     #$07        
$167F  8D 15 D4      STA     $D415         ; Filter Cutoff Lo
$1682  AD 85 17      LDA     $1785       
$1685  0D 86 17      ORA     $1786       
$1688  8D 18 D4      STA     $D418         ; Filter Mode/Volume
$168B  AD 8B 17      LDA     $178B       
$168E  8D 88 17      STA     $1788       
$1691  60            RTS                 
$1692  8D 82 17      STA     $1782       
$1695  A9 00         LDA     #$00        
$1697  8D 81 17      STA     $1781       
$169A  60            RTS                 
$169B  A9 40         LDA     #$40        
$169D  8D 81 17      STA     $1781       
$16A0  60            RTS                 
```

### Instrument Table Format

Location: **$1A6B-$1AAA** (64 bytes, 8 instruments × 8 bytes)

```asm
;===============================================================================
; Instrument Table Format
;===============================================================================
; Offset 0: Attack/Decay (ADSR)
; Offset 1: Sustain/Release (ADSR)
; Offset 2: Wave table pointer
; Offset 3: Pulse table pointer
; Offset 4: Filter table pointer
; Offset 5: Arpeggio table pointer
; Offset 6: Flags/Options
; Offset 7: Vibrato/Other settings
```

#### Hex Dump (from Stinsen 89 SF2 packed)

```
Address: $1A6B-$1AAA  Size: 64 bytes  Count: 8 instruments × 8 bytes
================================================================================
00: 25 25 26 26 27 a0 0e 0f 0f 0f 0f 11 01 05 01 04
10: ac 02 03 a0 13 14 13 15 0e 11 01 05 01 04 ac 02
20: 1b a0 13 14 13 15 1c 1c 1c 1c ac 02 1f 20 ff 00
30: a0 00 12 06 06 06 07 25 25 16 17 06 06 18 25 25
```

#### Decoded Instruments

| Inst | AD   | SR   | Wave | Pulse | Filter | Arp  | Flags | Vib  |
|------|------|------|------|-------|--------|------|-------|------|
| 0    | $25  | $25  | $26  | $26   | $27    | $A0  | $0E   | $0F  |
| 1    | $0F  | $0F  | $0F  | $11   | $01    | $05  | $01   | $04  |
| 2    | $AC  | $02  | $03  | $A0   | $13    | $14  | $13   | $15  |
| 3    | $0E  | $11  | $01  | $05   | $01    | $04  | $AC   | $02  |
| 4    | $1B  | $A0  | $13  | $14   | $13    | $15  | $1C   | $1C  |
| 5    | $1C  | $1C  | $AC  | $02   | $1F    | $20  | $FF   | $00  |
| 6    | $A0  | $00  | $12  | $06   | $06    | $06  | $07   | $25  |
| 7    | $25  | $16  | $17  | $06   | $06    | $18  | $25   | $25  |

### Wave Table Format

Location: **$1914-$1953** (64 bytes, 32 notes + 32 waveforms)

```asm
;===============================================================================
; Wave Table Format
;===============================================================================
; $0914-$0933: Note offsets (32 entries)
;   Each byte is a note offset (0-95) or special marker:
;   $7F = Loop marker
;   $7E = Gate on (sustain)
;   $80 = Note offset special (recalculate frequency)
;
; $0934-$0953: Waveforms (32 entries)
;   Bits 0-3: Waveform type
;     $01 = Triangle
;     $02 = Sawtooth
;     $04 = Pulse
;     $08 = Noise
;   Bit 4: Gate bit
;   Bits 5-7: Additional control flags
```

#### Hex Dump (from Stinsen 89 SF2 packed)

```
Address: $1914-$1953  Size: 64 bytes  Count: 32 notes + 32 waveforms
================================================================================
00: 07 c4 ac c0 bc 0c c0 00 0f c0 00 76 74 14 b4 12
10: 00 18 00 00 1b 00 1d c5 00 20 00 22 c0 00 25 00
20: 27 00 29 c7 ae a5 c0 2e 00 30 88 00 81 00 00 0f
30: 7f 88 7f 88 0f 0f 00 7f 88 00 0f 00 7f 86 00 0f
```

### Pulse Table Format

Location: **$1A3B-$1A7A** (64 bytes, 16 entries × 4 bytes)

```asm
;===============================================================================
; Pulse Table Format
;===============================================================================
; Byte 0: Initial pulse width value (bits 0-7 of 12-bit value)
; Byte 1: Delta (change per frame)
; Byte 2: Duration (frames to run)
; Byte 3: Next entry index (or $7F for loop)
;
; Each entry creates a pulse width sweep program.
; Multiple entries can be chained together for complex modulation.
```

#### Hex Dump (from Stinsen 89 SF2 packed)

```
Address: $1A3B-$1A7A  Size: 64 bytes  Count: 16 entries × 4 bytes
================================================================================
00: a7 b9 cd 25 f3 b1 62 ad b9 c0 e1 31 af 30 1a 1a
10: 1a 1b 1b 1c 1c 1d 1d 1e 1f 1f 1f 1f 20 20 20 20
20: 20 20 20 21 21 21 21 22 22 22 23 23 24 25 25 25
30: 25 25 26 26 27 a0 0e 0f 0f 0f 0f 11 01 05 01 04
```

### Filter Table Format

Location: **$1A1E-$1A4D** (48 bytes, 16 entries × 3 bytes)

```asm
;===============================================================================
; Filter Table Format
;===============================================================================
; Byte 0: Initial cutoff frequency (0-255)
; Byte 1: Delta (change per frame)
; Byte 2: Duration (frames to run)
;
; Each entry creates a filter sweep program.
; Filter type and resonance are set separately in init routine.
```

#### Hex Dump (from Stinsen 89 SF2 packed)

```
Address: $1A1E-$1A4D  Size: 48 bytes  Count: 16 entries × 3 bytes
================================================================================
00: b3 1a 1a 1a d1 d5 f7 97 ec 57 ba 3b fc ae 30 47
10: 5e 75 28 4c 6e 80 99 a9 cb 2e 99 ba db a7 b9 cd
20: 25 f3 b1 62 ad b9 c0 e1 31 af 30 1a 1a 1a 1b 1b
```

### Arpeggio Table Format

Location: **$1A8B-$1ACA** (64 bytes, 16 entries × 4 bytes)

```asm
;===============================================================================
; Arpeggio Table Format
;===============================================================================
; Byte 0-3: Note offsets (semitones)
;   Each byte is added to the base note to create chord notes.
;   Cycles through all 4 bytes to create arpeggio effect.
;   Common patterns:
;     00 04 07 00 = Major chord (root, major 3rd, 5th)
;     00 03 07 00 = Minor chord (root, minor 3rd, 5th)
;     00 0C 00 0C = Octave jump
```

#### Hex Dump (from Stinsen 89 SF2 packed)

```
Address: $1A8B-$1ACA  Size: 64 bytes  Count: 16 entries × 4 bytes
================================================================================
00: 1b a0 13 14 13 15 1c 1c 1c 1c ac 02 1f 20 ff 00
10: a0 00 12 06 06 06 07 25 25 16 17 06 06 18 25 25
20: 06 06 06 06 1d 21 ff 00 a0 0a 0a 0b 0c a2 0a a0
30: 10 08 09 19 ac 0d a0 0b 10 08 09 1a ac 0d 23 24
```

### Command Table Format

Location: **$1ADB-$1B9A** (192 bytes, 64 commands × 3 bytes)

```asm
;===============================================================================
; Command Table Format
;===============================================================================
; Byte 0: Command type
;   $00 = Slide
;   $01 = Vibrato
;   $02 = Portamento
;   $03 = Arpeggio
;   $04 = Fret
;   $08 = ADSR (note-based)
;   $09 = ADSR (persistent)
;   $0A = Index Filter
;   $0B = Index Wave
;   $0C = Index Pulse
;   $0D = Tempo
;   $0E = Volume
;   $0F = Demo flag
;
; Byte 1: Parameter 1 (command-specific)
; Byte 2: Parameter 2 (command-specific)
```

#### Hex Dump (from Stinsen 89 SF2 packed)

```
Address: $1ADB-$1B9A  Size: 192 bytes  Count: 64 commands × 3 bytes
================================================================================
00: c4 a9 39 c4 a0 83 39 80 39 00 83 39 c5 81 3a c5
10: a9 3a c4 a0 85 39 c4 a9 81 39 39 7f ca a0 81 30
20: 30 80 30 00 ca a9 81 30 ca a0 83 30 cb 80 2b 00
30: c4 85 2d c4 a9 81 2d d0 2d 2d c4 a0 80 2d 00 81
40: 2d c4 a9 2d ca a0 2e 2e 80 2e 00 ca a9 81 2e ca
50: a0 83 2e cb 80 29 00 c4 85 2b c4 a9 81 2b d0 2b
60: 2b c4 a0 80 2b 00 81 2b c4 a9 2b ca a0 2d 2d 80
70: 2d 00 ca a9 81 2d ca a0 83 2d cb 80 28 00 c6 85
80: 29 80 29 00 c6 a9 81 29 c6 a0 80 29 00 81 29 c6
90: a9 29 29 ca a0 2b 2b 80 2b 00 ca a9 81 2b ca a0
a0: 83 2b cb 80 26 00 cc 85 29 cc a9 81 29 d0 29 29
b0: cc a0 80 29 00 29 00 cc a9 81 29 7f cb a9 81 29
```

## Player Execution Flow

### Initialization Sequence

1. **Entry**: Init routine called with subtune number in A register
2. **State Clear**: Zero out player state variables ($1782-$17F7)
3. **Configuration**: Load tempo, filter, and resonance settings
4. **Voice Setup**: Initialize speed and position for all 3 voices
5. **Flag Set**: Mark player as initialized ($1781 = $80)

### Play Loop (50Hz PAL)

1. **Tempo Check**: Decrement tempo counter, reload if zero
2. **Voice Processing** (for each of 3 voices):
   - Check if voice needs new note
   - Read sequence data (note, instrument, command)
   - Process transpose values
   - Load instrument parameters
   - Execute wave table programs
3. **SID Updates**:
   - Set frequency (from note + transpose)
   - Set waveform and gate control
   - Apply ADSR envelope
   - Update pulse width (if used)
   - Update filter (if enabled)
4. **Return**: Exit until next frame

## Key Data Structures

### Sequence Pointers ($199F-$19A5)

```
$199F-$19A0: Voice 1 sequence pointer (16-bit)
$19A1-$19A2: Voice 2 sequence pointer (16-bit)
$19A3-$19A4: Voice 3 sequence pointer (16-bit)
```

### Tempo Table

Speed values in frames per row, terminated by $7F wrap marker.

```
Format: [speed1] [speed2] ... [speedN] $7F [wrap_position]
Example: 02 02 02 02 7F 00 = constant speed of 2 frames/row
```

### Per-Voice State

Each voice (0-2) maintains separate state in parallel arrays:

```
$178F+X: Note duration counter (counts down to 0)
$1792+X: Current position in sequence data
$1795+X: Sequence active flag (0=inactive, 1=active)
$1798+X: Current position in wave table program
$179B+X: Current instrument number (0-7)
$17B0+X: Transpose value (semitones ± 12)
$17F8+X: Voice speed flag (timing divisor)
```

## Notes on This Implementation

This SF2-packed player uses several optimization techniques:

1. **Table-Driven Design**: All sound parameters stored in compact tables
2. **Programmatic Control**: Wave, pulse, and filter tables contain mini-programs
3. **Per-Voice State**: Each voice independently tracks position and timing
4. **Tempo Flexibility**: Variable speed system with loop markers
5. **Transpose System**: In-sequence transpose adjustments (values $A0+)
6. **Gate Control**: Explicit gate on/off for envelope precision
7. **Command System**: Effects like slides, vibrato, arpeggios via command table
8. **Hard Restart**: Prevents ADSR bugs with 2-frame gate-off before notes

## Memory Usage

- **Player code**: ~1,697 bytes ($1000-$16A0)
- **Data tables**: ~648 bytes ($1914-$1B9B)
- **Music data**: ~3,003 bytes ($1C00-$27BA)
- **Total**: ~6,075 bytes

---

*This disassembly documents the SF2-packed format as used in "Stinsen 89 SF2 packed"*
