# SIDM2 File Inventory
Generated: 2025-12-07 14:07:50

## Purpose
This inventory categorizes all project files with their purpose and recommendations for cleanup.
Files are marked as:
- 🟢 **Active** - Core functionality, recently updated (Nov 2025)
- 🟡 **Old** - Not recently updated, review for cleanup

**Note**: This file is auto-generated. Run `python update_inventory.py` to refresh.

---

## Main Entry Point

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| complete_pipeline_with_validation.py | 26,248 | 2025-12-07 | 🟢 Active |

## Scripts (scripts/)

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| scripts/convert_all.py - Batch converter (v0.6.3) | 44,663 | 2025-12-07 | 🟢 Active |
| scripts/sid_to_sf2.py - Main SID to SF2 converter (v0.6.3) | 18,351 | 2025-12-07 | 🟢 Active |
| scripts/update_inventory.py - Auto-generates FILE_INVENTORY.md | 7,032 | 2025-12-07 | 🟢 Active |
| scripts/__init__.py | 908 | 2025-12-07 | 🟢 Active |
| scripts/extract_sf2_properly.py | 4,997 | 2025-12-06 | 🟢 Active |
| scripts/sf2_to_sid.py - SF2 to SID packer (v1.0.0) | 11,243 | 2025-12-04 | 🟢 Active |
| scripts/disassemble_sid.py | 9,428 | 2025-12-02 | 🟢 Active |
| scripts/extract_addresses.py | 8,336 | 2025-12-02 | 🟢 Active |
| scripts/format_tables.py | 15,340 | 2025-12-02 | 🟢 Active |
| scripts/generate_info.py | 14,310 | 2025-12-02 | 🟢 Active |
| scripts/batch_validate_sidsf2player.py | 8,797 | 2025-11-30 | 🟢 Active |
| scripts/comprehensive_validate.py | 19,027 | 2025-11-30 | 🟢 Active |
| scripts/validate_structure.py | 10,512 | 2025-11-30 | 🟢 Active |
| scripts/convert_all_sidsf2player.py | 3,386 | 2025-11-29 | 🟢 Active |
| scripts/laxity_parser.py | 22,179 | 2025-11-29 | 🟢 Active |
| scripts/generate_validation_report.py | 18,327 | 2025-11-27 | 🟢 Active |
| scripts/validate_conversion.py - Conversion validation | 17,569 | 2025-11-27 | 🟢 Active |
| scripts/validate_psid.py - PSID header validator | 13,315 | 2025-11-27 | 🟢 Active |
| scripts/validate_sid_accuracy.py - Frame-by-frame accuracy checker | 33,839 | 2025-11-27 | 🟢 Active |
| scripts/ci_local.py | 12,287 | 2025-11-22 | 🟢 Active |

## Core Package (sidm2/)

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| sidm2/__init__.py | 3,183 | 2025-12-07 | 🟢 Active |
| sidm2/sf2_packer.py | 26,550 | 2025-12-06 | 🟢 Active |
| sidm2/instrument_extraction.py | 7,770 | 2025-12-04 | 🟢 Active |
| sidm2/sf2_writer.py | 55,677 | 2025-12-04 | 🟢 Active |
| sidm2/sf2_packed_reader.py | 11,817 | 2025-12-02 | 🟢 Active |
| sidm2/laxity_analyzer.py | 26,397 | 2025-12-01 | 🟢 Active |
| sidm2/table_extraction.py | 55,267 | 2025-12-01 | 🟢 Active |
| sidm2/laxity_parser.py | 12,395 | 2025-11-30 | 🟢 Active |
| sidm2/sequence_translator.py | 18,907 | 2025-11-30 | 🟢 Active |
| sidm2/sf2_player_parser.py | 22,393 | 2025-11-30 | 🟢 Active |
| sidm2/sf2_reader.py | 8,310 | 2025-11-30 | 🟢 Active |
| sidm2/sid_structure_analyzer.py | 18,483 | 2025-11-30 | 🟢 Active |
| sidm2/sid_structure_extractor.py | 22,670 | 2025-11-30 | 🟢 Active |
| sidm2/wav_comparison.py | 10,706 | 2025-11-30 | 🟢 Active |
| sidm2/config.py | 7,000 | 2025-11-29 | 🟢 Active |
| sidm2/sequence_extraction.py | 17,161 | 2025-11-29 | 🟢 Active |
| sidm2/cpu6502_emulator.py | 41,080 | 2025-11-28 | 🟢 Active |
| sidm2/sid_player.py | 19,184 | 2025-11-28 | 🟢 Active |
| sidm2/confidence.py | 26,766 | 2025-11-27 | 🟢 Active |
| sidm2/cpu6502.py | 12,422 | 2025-11-27 | 🟢 Active |
| sidm2/models.py | 4,221 | 2025-11-27 | 🟢 Active |
| sidm2/note_utils.py | 11,248 | 2025-11-27 | 🟢 Active |
| sidm2/player_base.py | 9,826 | 2025-11-27 | 🟢 Active |
| sidm2/siddump.py | 4,862 | 2025-11-27 | 🟢 Active |
| sidm2/validation.py | 13,302 | 2025-11-27 | 🟢 Active |
| sidm2/players/laxity.py | 3,359 | 2025-11-27 | 🟢 Active |
| sidm2/players/__init__.py | 293 | 2025-11-27 | 🟢 Active |
| sidm2/constants.py | 3,148 | 2025-11-22 | 🟢 Active |
| sidm2/exceptions.py | 658 | 2025-11-22 | 🟢 Active |
| sidm2/logging_config.py | 1,253 | 2025-11-22 | 🟢 Active |
| sidm2/sid_parser.py | 3,474 | 2025-11-22 | 🟢 Active |

## Tests

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| scripts/test_converter.py | 63,604 | 2025-12-07 | 🟢 Active |
| scripts/test_complete_pipeline.py | 14,014 | 2025-12-03 | 🟢 Active |
| scripts/test_config.py | 8,943 | 2025-11-29 | 🟢 Active |
| scripts/test_sf2_player_parser.py | 5,693 | 2025-11-29 | 🟢 Active |
| scripts/test_roundtrip.py | 26,692 | 2025-11-28 | 🟢 Active |
| scripts/test_sf2_editor.py | 16,160 | 2025-11-23 | 🟢 Active |
| scripts/test_sf2_format.py | 9,632 | 2025-11-22 | 🟢 Active |

## Documentation

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| CLAUDE.md | 33,547 | 2025-12-07 | 🟢 Active |
| FILE_INVENTORY.md | 21,232 | 2025-12-07 | 🟢 Active |
| README.md | 65,023 | 2025-12-07 | 🟢 Active |
| TODO.md | 27,843 | 2025-12-07 | 🟢 Active |
| docs/INDEX.md | 4,592 | 2025-12-07 | 🟢 Active |
| docs/analysis/TECHNICAL_ANALYSIS.md | 14,166 | 2025-12-07 | 🟢 Active |
| docs/guides/SIDWINDER_GUIDE.md | 7,060 | 2025-12-07 | 🟢 Active |
| docs/INDEX_OLD.md | 14,120 | 2025-12-06 | 🟢 Active |
| docs/archive/2025-12-06/PIPELINE_EXECUTION_REPORT.md | 12,153 | 2025-12-06 | 🟢 Active |
| docs/archive/2025-12-06/PIPELINE_RESULTS_2025-12-06.md | 3,613 | 2025-12-06 | 🟢 Active |
| docs/archive/2025-12-06/PIPELINE_RESULTS_SUMMARY.md | 6,521 | 2025-12-06 | 🟢 Active |
| docs/archive/2025-12-06/PIPELINE_TIMING.md | 1,458 | 2025-12-06 | 🟢 Active |
| docs/reference/WAVE_TABLE_PACKING.md | 6,897 | 2025-12-04 | 🟢 Active |
| docs/archive/ANNOTATED_DISASSEMBLY_INTEGRATION.md | 12,612 | 2025-12-03 | 🟢 Active |
| docs/archive/SF2PACKED_STINSENS_ANNOTATED_DISASSEMBLY.md | 45,673 | 2025-12-03 | 🟢 Active |
| docs/archive/SF2PACKED_STINSENS_COMPLETE_DISASSEMBLY.md | 178,898 | 2025-12-03 | 🟢 Active |
| docs/reference/STINSENS_PLAYER_DISASSEMBLY.md | 23,492 | 2025-12-03 | 🟢 Active |
| docs/FILE_INVENTORY.md | 16,764 | 2025-12-02 | 🟢 Active |
| docs/archive/SIDSF2PLAYER_VALIDATION_REPORT.md | 9,919 | 2025-11-30 | 🟢 Active |
| docs/analysis/ACCURACY_ROADMAP.md | 11,655 | 2025-11-27 | 🟢 Active |
| docs/analysis/PACK_STATUS.md | 5,555 | 2025-11-27 | 🟢 Active |
| docs/archive/PHASE1_COMPLETION_REPORT.md | 12,673 | 2025-11-27 | 🟢 Active |
| docs/archive/ROUNDTRIP_VALIDATION_FINDINGS.md | 6,325 | 2025-11-27 | 🟢 Active |
| docs/guides/VALIDATION_GUIDE.md | 23,744 | 2025-11-27 | 🟢 Active |
| docs/reference/SF2_TO_SID_LIMITATIONS.md | 7,185 | 2025-11-27 | 🟢 Active |
| docs/reference/CONVERSION_STRATEGY.md | 15,397 | 2025-11-23 | 🟢 Active |
| docs/reference/DRIVER_REFERENCE.md | 9,725 | 2025-11-23 | 🟢 Active |
| docs/reference/format-specification.md | 10,858 | 2025-11-23 | 🟢 Active |
| docs/reference/SF2_CLASSES.md | 8,564 | 2025-11-23 | 🟢 Active |
| docs/reference/SF2_FORMAT_SPEC.md | 14,208 | 2025-11-23 | 🟢 Active |
| docs/reference/sid-registers.md | 5,809 | 2025-11-22 | 🟢 Active |
| CONTRIBUTING.md | 6,626 | 2025-11-21 | 🟢 Active |

## Tools

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| tools/= | 58 | 2025-12-06 | 🟢 Active |
| tools/angular_test.asm | 108,218 | 2025-12-06 | 🟢 Active |
| tools/mit.log | 283 | 2025-12-06 | 🟢 Active |
| tools/mit.txt | 540,009 | 2025-12-06 | 🟢 Active |
| tools/SIDwinder.cfg | 1,574 | 2025-12-06 | 🟢 Active |
| tools/SIDwinder.exe | 1,889,280 | 2025-12-06 | 🟢 Active |
| tools/SIDwinder.log | 217 | 2025-12-06 | 🟢 Active |
| tools/SIDWINDER_FIXES_APPLIED.md | 1,560 | 2025-12-06 | 🟢 Active |
| tools/SIDWINDER_QUICK_REFERENCE.md | 9,822 | 2025-12-06 | 🟢 Active |
| tools/sidwinder_trace_fix.patch | 2,308 | 2025-12-06 | 🟢 Active |
| tools/trace.bin | 240,008 | 2025-12-06 | 🟢 Active |
| tools/mit | 58 | 2025-12-05 | 🟢 Active |
| tools/mit.asm | 115,912 | 2025-12-05 | 🟢 Active |
| tools/README.md | 352 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/Default/Default.asm | 1,479 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/INC/FreqTable.asm | 5,121 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/INC/MemoryPreservation.asm | 3,214 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/INC/NMIFix.asm | 231 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/INC/StableRasterSetup.asm | 2,937 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinBars/CharSet.map | 1,792 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinBars/RaistlinBars.asm | 29,705 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinBars/WaterSprites.map | 512 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinBarsWithLogo/CharSet.map | 1,792 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinBarsWithLogo/RaistlinBarsWithLogo.asm | 28,985 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinBarsWithLogo/WaterSprites.map | 512 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinMirrorBars/CharSet.map | 1,792 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinMirrorBars/RaistlinMirrorBars.asm | 25,008 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinMirrorBarsWithLogo/CharSet.map | 1,792 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinMirrorBarsWithLogo/RaistlinMirrorBarsWithLogo.asm | 25,373 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinMirrorBarsWithLogo/SoundbarSine.bin | 128 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/RaistlinMirrorBarsWithLogo/WaterSprites.map | 512 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/SimpleBitmap/SimpleBitmap.asm | 9,736 | 2025-12-05 | 🟢 Active |
| tools/SIDPlayers/SimpleRaster/SimpleRaster.asm | 6,595 | 2025-12-05 | 🟢 Active |
| tools/prg2sid/Makefile | 1,783 | 2025-11-27 | 🟢 Active |
| tools/prg2sid/p2s.c | 117,179 | 2025-11-27 | 🟢 Active |
| tools/prg2sid/p2s.txt | 14,272 | 2025-11-27 | 🟢 Active |
| tools/prg2sid/Release/p2s.exe | 84,992 | 2025-11-27 | 🟢 Active |
| tools/sf2export/Makefile | 808 | 2025-11-27 | 🟢 Active |
| tools/sf2export/README.md | 5,077 | 2025-11-27 | 🟢 Active |
| tools/sf2export/sf2export.cpp | 9,897 | 2025-11-27 | 🟢 Active |
| tools/sf2export/sf2export.exe | 2,468,196 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/c64memory.cpp | 2,884 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/c64memory.h | 1,443 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/c64memory.o | 4,997 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/Makefile | 953 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/opcodes.cpp | 4,980 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/opcodes.h | 1,136 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/opcodes.o | 3,420 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/packer_simple.cpp | 5,814 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/packer_simple.h | 1,381 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/packer_simple.o | 6,700 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/psidfile.cpp | 3,473 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/psidfile.h | 2,305 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/psidfile.o | 8,506 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/README.md | 6,624 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/sf2pack.cpp | 7,912 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/sf2pack.exe | 2,480,208 | 2025-11-27 | 🟢 Active |
| tools/sf2pack/sf2pack.o | 21,663 | 2025-11-27 | 🟢 Active |
| tools/cpu.c | 27,991 | 2025-11-22 | 🟢 Active |
| tools/cpu.h | 204 | 2025-11-22 | 🟢 Active |
| tools/player-id.exe | 470,544 | 2025-11-22 | 🟢 Active |
| tools/readme.txt | 6,227 | 2025-11-22 | 🟢 Active |
| tools/SID2WAV.EXE | 196,608 | 2025-11-22 | 🟢 Active |
| tools/siddump.c | 16,214 | 2025-11-22 | 🟢 Active |
| tools/siddump.exe | 50,702 | 2025-11-22 | 🟢 Active |
| tools/sidid.cfg | 76,622 | 2025-11-22 | 🟢 Active |
| tools/sidid.nfo | 44,879 | 2025-11-22 | 🟢 Active |
| tools/Signature_File_Format.txt | 6,956 | 2025-11-22 | 🟢 Active |
| tools/Stinsens_Last_Night_of_89.sid | 6,201 | 2025-11-22 | 🟢 Active |
| tools/tedid.cfg | 878 | 2025-11-22 | 🟢 Active |

## Templates (G5/)

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| G5/desktop.ini | 80 | 2025-11-22 | 🟢 Active |
| G5/NewPlayer v21.G5 Final/21.g5 clean.prg | 8,353 | 2025-11-22 | 🟢 Active |
| G5/NewPlayer v21.G5 Final/desktop.ini | 68 | 2025-11-22 | 🟢 Active |
| G5/siddump108/cpu.c | 27,991 | 2025-11-22 | 🟢 Active |
| G5/siddump108/cpu.h | 204 | 2025-11-22 | 🟢 Active |
| G5/siddump108/Makefile | 114 | 2025-11-22 | 🟢 Active |
| G5/siddump108/readme.txt | 2,006 | 2025-11-22 | 🟢 Active |
| G5/siddump108/siddump.c | 16,214 | 2025-11-22 | 🟢 Active |
| G5/siddump108/siddump.exe | 50,702 | 2025-11-22 | 🟢 Active |
| G5/21g5.txt | 20,569 | 2024-11-10 | 🟡 Old |
| G5/21.g5_Final.d64 | 174,848 | 2024-11-08 | 🟡 Old |
| G5/21.g5_Final.txt | 11,072 | 2024-11-08 | 🟡 Old |
| G5/NewPlayer v21.G5 Final/21.g5_Demos_Final.d64 | 174,848 | 2024-11-08 | 🟡 Old |
| G5/NewPlayer v21.G5 Final/21.g5_Final.d64 | 174,848 | 2024-11-08 | 🟡 Old |
| G5/NewPlayer v21.G5 Final/21.g5_Final.txt | 11,072 | 2024-11-08 | 🟡 Old |
| G5/NewPlayer v21.G5 Final/NP-PACK5.5.d64 | 174,848 | 2024-11-08 | 🟡 Old |
| G5/drivers/sf2driver11_00.prg | 6,577 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver11_01.prg | 6,665 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver11_02.prg | 6,721 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver11_03.prg | 6,768 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver11_04.prg | 6,799 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver11_04_01.prg | 6,817 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver11_05.prg | 6,726 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver12_00.prg | 3,273 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver12_00_01.prg | 3,291 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver13_00.prg | 3,577 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver13_00_01.prg | 3,595 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver14_00.prg | 5,696 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver14_00_01.prg | 5,714 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver15_00.prg | 3,585 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver15_01.prg | 3,585 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver15_02.prg | 3,618 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver16_00.prg | 3,334 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver16_01.prg | 3,334 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver16_01_01.prg | 3,350 | 2024-08-20 | 🟡 Old |
| G5/drivers/sf2driver_np20_00.prg | 5,345 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 11 Test - Arpeggio.sf2 | 7,656 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 11 Test - Filter.sf2 | 7,866 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 11 Test - Polyphonic.sf2 | 8,649 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 11 Test - Tie Notes.sf2 | 8,464 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 12 Test - The Barber.sf2 | 4,829 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 13 Test - Hubbard.sf2 | 5,904 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 14 Test - Heavy.sf2 | 10,434 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 14 Test - Long Sequence.sf2 | 7,266 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 14 Test - Medieval.sf2 | 8,018 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 15 Test - Mood.sf2 | 9,289 | 2024-08-20 | 🟡 Old |
| G5/examples/Driver 16 Test - Busy.sf2 | 5,315 | 2024-08-20 | 🟡 Old |
| G5/siddump108.zip | 27,858 | 2024-08-15 | 🟡 Old |

## Example Files (SID/)

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| SID/Stinsens_Last_Night_of_89.sid | 6,201 | 2025-12-02 | 🟢 Active |
| SID/Balance.sid | 4,087 | 2025-11-27 | 🟢 Active |
| SID/Beast.sid | 3,880 | 2025-11-27 | 🟢 Active |
| SID/Blue.sid | 4,442 | 2025-11-27 | 🟢 Active |
| SID/Cascade.sid | 3,880 | 2025-11-27 | 🟢 Active |
| SID/Chaser.sid | 4,508 | 2025-11-27 | 🟢 Active |
| SID/Colorama.sid | 4,187 | 2025-11-27 | 🟢 Active |
| SID/Cycles.sid | 4,869 | 2025-11-27 | 🟢 Active |
| SID/Delicate.sid | 4,331 | 2025-11-27 | 🟢 Active |
| SID/Dreams.sid | 3,965 | 2025-11-27 | 🟢 Active |
| SID/Dreamy.sid | 3,793 | 2025-11-27 | 🟢 Active |
| SID/Angular.sid | 3,907 | 2025-11-21 | 🟢 Active |
| SID/Clarencio_extended.sid | 8,162 | 2025-11-21 | 🟢 Active |
| SID/Ocean_Reloaded.sid | 6,680 | 2025-11-21 | 🟢 Active |
| SID/Omniphunk.sid | 4,484 | 2025-11-21 | 🟢 Active |
| SID/Phoenix_Code_End_Tune.sid | 4,514 | 2025-11-21 | 🟢 Active |
| SID/Unboxed_Ending_8580.sid | 4,638 | 2025-11-21 | 🟢 Active |

## Player Files (SIDSF2player/)

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| SIDSF2player/SF2packed_new1_Stiensens_last_night_of_89.sid | 6,201 | 2025-12-04 | 🟢 Active |
| SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid | 6,201 | 2025-12-02 | 🟢 Active |
| SIDSF2player/debug_packer.py | 639 | 2025-11-30 | 🟢 Active |
| SIDSF2player/parse_sf2_blocks.py | 1,411 | 2025-11-30 | 🟢 Active |
| SIDSF2player/polyphonic_cpp.sid | 8,706 | 2025-11-30 | 🟢 Active |
| SIDSF2player/polyphonic_test.sid | 8,771 | 2025-11-30 | 🟢 Active |
| SIDSF2player/test_broware_packed_only.sid | 6,965 | 2025-11-30 | 🟢 Active |
| SIDSF2player/test_sidsf2player_batch.py | 3,971 | 2025-11-30 | 🟢 Active |
| SIDSF2player/Aint_Somebody.sid | 5,162 | 2025-11-29 | 🟢 Active |
| SIDSF2player/batch_convert_sidsf2player.py | 2,416 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Broware.sid | 6,732 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Cocktail_to_Go_tune_3.sid | 4,544 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Driver 11 Test - Arpeggio.sid | 7,104 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Driver 11 Test - Filter.sid | 7,315 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Driver 11 Test - Polyphonic.sid | 8,064 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Driver 11 Test - Tie Notes.sid | 7,954 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Expand_Side_1.sid | 6,823 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Halloweed_4_tune_3.sid | 5,698 | 2025-11-29 | 🟢 Active |
| SIDSF2player/I_Have_Extended_Intros.sid | 3,809 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Staying_Alive.sid | 5,092 | 2025-11-29 | 🟢 Active |
| SIDSF2player/tie_notes_test.sid | 8,586 | 2025-11-29 | 🟢 Active |
| SIDSF2player/Stinsens_Last_Night_of_89.sid | 6,201 | 2025-11-22 | 🟢 Active |

## Configuration

| File | Size (bytes) | Last Modified | Status |
|------|--------------|---------------|--------|
| SIDwinder.cfg | 1,574 | 2025-12-07 | 🟢 Active |
| .gitignore | 1,077 | 2025-11-30 | 🟢 Active |
| sidm2_config.example.json | 699 | 2025-11-29 | 🟢 Active |
| .github/workflows/ci.yml | 6,514 | 2025-11-27 | 🟢 Active |
| .github/workflows/test.yml | 1,055 | 2025-11-27 | 🟢 Active |
| pytest.ini | 475 | 2025-11-23 | 🟢 Active |
| learnings/desktop.ini | 80 | 2025-11-23 | 🟢 Active |

---

## Cleanup Recommendations

### Safe to Remove (if confirmed unused)
1. **output/** directory contents - Can be regenerated
2. **roundtrip_output/** directory contents - Can be regenerated

### Keep Everything Else
- All sidm2/ package files are core functionality
- All test files are part of the test suite
- All documentation provides valuable reference
- All G5/ templates are required for conversion
- All SID/ example files are test references

---

## Usage

To update this inventory, run:
```bash
python scripts/update_inventory.py
```

---

Last updated: 2025-12-07 14:07:50