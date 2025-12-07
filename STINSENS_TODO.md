# Stinsens Last Night of '89 - SF2 Conversion TODO

## Completed ✓

1. **Wave Table** - Fixed column order (waveforms first, notes second) - VERIFIED
2. **Wave Table Address** - Fixed to start at $18DA (skip 2-byte header at $18D8) - VERIFIED
3. **Pulse Table** - Verified 4-column format (value, delta, duration, next) - VERIFIED
4. **Filter Table** - Verified 4-column format (cutoff, count, duration, next) - VERIFIED
5. **Instruments Table** - Verified 6-column format (AD, SR, Flags, Filter, Pulse, Wave) - VERIFIED
6. **Commands Table** - Verified 3-column format (cmd, param1, param2) - VERIFIED

## In Progress 🔄

7. **Tempo Table** - Verify format (speed values + wrap markers)
8. **HR Table** - Verify format (2 columns: AD, SR)
9. **Init Table** - Verify format (2 columns: tempo ptr, volume)
10. **Arp Table** - Verify format (arpeggio patterns)

## Pending

11. **Sequence Data** - Verify Track 1, Track 2, Track 3 sequences match original
12. **Orderlist Data** - Verify orderlists are correct
13. **Final Playback Test** - Test in SID Factory II and verify music plays correctly
14. **Binary Comparison** - Compare with manually-created SF2 file

## Notes

- Load address: $0D7E (Driver 11 standard) ✓
- File size: 8,436 bytes
- Driver: Driver 11.00 - The Standard
- All major tables verified as PASS

## Current Status

**5/14 tasks complete (36%)**

Next steps:
1. Verify remaining tables (Tempo, HR, Init, Arp)
2. Verify sequence/orderlist data
3. Test playback in SID Factory II
