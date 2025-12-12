# Stinsens Last Night of '89 - SF2 Conversion TODO

## Completed ✓

1. **Wave Table** - Fixed column order (waveforms first, notes second) - VERIFIED
2. **Wave Table Address** - Fixed to start at $18DA (skip 2-byte header at $18D8) - VERIFIED
3. **Pulse Table** - Fixed extraction from SF2-packed SID (3 consecutive columns at $09BC) - VERIFIED
   - Extracted 3 columns of 25 bytes each from SF2-packed SID
   - Converted to Driver 11 4-column format (value, delta, duration, next)
   - Script: `fix_pulse_table_correct.py`
4. **Filter Table** - Verified 4-column format (cutoff, count, duration, next) - VERIFIED
5. **Instruments Table** - Verified 6-column format (AD, SR, Flags, Filter, Pulse, Wave) - VERIFIED
6. **Commands Table** - Verified 3-column format (cmd, param1, param2) - VERIFIED

7. **Tempo Table** - Verified format (speed values + wrap markers) - VERIFIED
8. **HR Table** - Verified format (2 columns: AD, SR) - VERIFIED
9. **Init Table** - Verified format (2 columns: tempo ptr, volume) - VERIFIED
10. **Arp Table** - Verified format (arpeggio patterns) - VERIFIED
11. **Sequence/Orderlist Data** - Verified structure for all 3 tracks - VERIFIED

## Pending

12. **Final Playback Test** - Test in SID Factory II and verify music plays correctly
13. **Binary Comparison** - Compare with manually-created SF2 file (if available)

## Notes

- Load address: $0D7E (Driver 11 standard) ✓
- File size: 8,436 bytes
- Driver: Driver 11.00 - The Standard
- All tables verified as PASS (Wave, Pulse, Filter, Instruments, Commands, Tempo, HR, Init, Arp)
- Sequences/orderlists verified as structurally correct (3 tracks, 1 sequence extracted)

**Pulse Table Discovery:**
- SF2-packed SID format stores pulse table as 3 consecutive columns (not 4 columns like Driver 11)
- Location: $09BC-$0A06 (75 bytes total: 3 columns × 25 bytes each)
- Column 0: bytes 0-24 at $09BC (Value)
- Column 1: bytes 25-49 at $09D5 (Delta)
- Column 2: bytes 50-74 at $09EE (Duration)
- Conversion adds 4th column (Next) filled with zeros
- Note: `PULSE_TABLE_ANALYSIS.md` contains incorrect analysis (stated pulse should be empty)

## Current Status

**11/13 tasks complete (85%)**

Verification Summary:
- ✓ All 9 SF2 Driver 11 tables verified and passing
- ✓ Sequence/orderlist structure verified for all 3 tracks
- ⚠ Note: Only 1 sequence extracted by Laxity parser (parser limitation, not format issue)

Next steps:
1. Test playback in SID Factory II
2. Compare with manually-created reference file if available
