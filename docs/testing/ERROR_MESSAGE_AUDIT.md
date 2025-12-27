# Error Message Audit Report

**Date**: 1766826690.072384
**Files Audited**: 47
**Total Issues Found**: 449

## Issues by Category

| Category | Count |
|----------|-------|
| Bare Logger Errors | 216 |
| Missing Doc Links | 156 |
| Missing Alternatives | 52 |
| Generic Exceptions | 24 |
| Technical Jargon | 1 |

## Issues by Severity

| Severity | Count |
|----------|-------|
| Low | 425 |
| Medium | 24 |

## Detailed Findings

### Bare Logger Errors (216 issues)

#### scripts\convert_all.py

**Line 170** (low)
```python
logger.warning(f"siddump timed out for {sid_path}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 173** (low)
```python
logger.warning(f"siddump failed with code {e.returncode}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 298** (low)
```python
logger.warning(f"Failed to extract table data: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 306** (low)
```python
logger.warning(f"File I/O error during extraction: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 1154** (low)
```python
logger.error(f"Unexpected error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### scripts\sf2_to_sid.py

**Line 245** (low)
```python
logger.warning(f"  Failed to parse SF2 header blocks: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 429** (low)
```python
logger.error("Conversion failed")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 436** (low)
```python
logger.error(f"Unexpected error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### scripts\sid_to_sf2.py

**Line 186** (low)
```python
logger.warning(f"Player type detection failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 342** (low)
```python
logger.error(f"Failed to analyze SID file: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 372** (low)
```python
logger.error(f"Laxity conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 456** (low)
```python
logger.warning("File does not appear to be Martin Galway format based on header analysis")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 457** (low)
```python
logger.warning("Attempting conversion anyway...")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 468** (low)
```python
logger.error(f"SF2 Driver 11 template not found at {driver11_template_path}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 504** (low)
```python
logger.error("Galway conversion produced no output")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 508** (low)
```python
logger.error(f"Galway conversion failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 514** (low)
```python
logger.error(f"Galway conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 659** (low)
```python
logger.error(f"Failed to analyze SID file: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

*... and 31 more issues in this file*

#### scripts\test_logging_system.py

**Line 336** (low)
```python
logger.error("Error message")
```
**Suggestion**: Add actionable suggestion or documentation link

#### scripts\test_midi_comparison.py

**Line 81** (low)
```python
logger.error("SIDtool not found")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 117** (low)
```python
logger.error("  SIDtool did not create MIDI file")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 121** (low)
```python
logger.error("  SIDtool timed out (>60s)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 124** (low)
```python
logger.error(f"  SIDtool failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 126** (low)
```python
logger.error(f"  Error: {e.stderr}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 139** (low)
```python
logger.error("  Python emulator failed")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 142** (low)
```python
logger.error(f"  Python emulator error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 188** (low)
```python
logger.error(f"Failed to analyze {midi_path}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 435** (low)
```python
logger.error(f"No SID files found in {args.sid_dir}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\accuracy.py

**Line 113** (low)
```python
logger.error(f"SID file does not exist: {self.sid_path}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 144** (low)
```python
logger.error(f"Siddump exe not found: {siddump_exe}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 159** (low)
```python
logger.error(f"Siddump exe failed with return code: {result.returncode}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 165** (low)
```python
logger.error(f"Siddump exe exception: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 475** (low)
```python
logger.error(f"Failed to capture registers from original SID: {original_sid}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 480** (low)
```python
logger.error(f"Failed to capture registers from exported SID: {exported_sid}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 487** (low)
```python
logger.error(f"Accuracy calculation exception: {e}", exc_info=True)
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\accuracy_integration.py

**Line 76** (low)
```python
logger.warning(f"Accuracy calculation failed - no result returned")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 79** (low)
```python
logger.error(f"Accuracy calculation error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 105** (low)
```python
logger.error(f"Accuracy validation failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\audio_comparison.py

**Line 239** (low)
```python
logger.warning(f"WAV format mismatch: "
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 292** (low)
```python
logger.warning(f"  Audio comparison failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 295** (low)
```python
logger.error(f"  Audio comparison error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\audio_export_wrapper.py

**Line 139** (low)
```python
logger.warning("SID2WAV.EXE not available (tools/SID2WAV.EXE not found)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 150** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 215** (low)
```python
logger.error(f"Audio export failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 225** (low)
```python
logger.error(error_msg)
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 235** (low)
```python
logger.error(f"Audio export failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\config.py

**Line 180** (low)
```python
logger.error(f"Failed to save configuration: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 193** (low)
```python
logger.warning(f"Configuration file not found: {path}, using defaults")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 196** (low)
```python
logger.error(f"Failed to load configuration: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\disasm_table_finder.py

**Line 36** (low)
```python
logger.error(f"Failed to disassemble {sid_path}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 37** (low)
```python
logger.error(f"Output: {e.output}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 40** (low)
```python
logger.error(f"Failed to disassemble {sid_path}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 146** (low)
```python
logger.warning("Failed to generate disassembly")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 153** (low)
```python
logger.warning("No table references found in disassembly")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\disasm_wrapper.py

**Line 132** (low)
```python
logger.warning("Disassembler not available (disasm6502.py not found)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 137** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 200** (low)
```python
logger.error(f"Disassembly failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\galway_format_converter.py

**Line 118** (low)
```python
logger.error(f"Instrument conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 172** (low)
```python
logger.error(f"Sequence conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 232** (low)
```python
logger.error(f"Wave table conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 278** (low)
```python
logger.error(f"Pulse table conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 323** (low)
```python
logger.error(f"Filter table conversion error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\galway_table_extractor.py

**Line 132** (low)
```python
logger.error(f"Extraction error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\galway_table_injector.py

**Line 79** (low)
```python
logger.warning(f"Unknown driver: {driver}, using Driver11 offsets")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 96** (low)
```python
logger.warning(f"Unknown table type: {table_type}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 108** (low)
```python
logger.error(f"Table {table_type} too large for driver")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 120** (low)
```python
logger.error(f"Injection error for {table_type}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 219** (low)
```python
logger.warning("No tables extracted, using Driver 11 defaults")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 281** (low)
```python
logger.error(f"Integration error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\instrument_extraction.py

**Line 30** (low)
```python
logger.warning(f"Data too small for instrument extraction: {len(data) if data else 0} bytes, returning empty list")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\laxity_analyzer.py

**Line 677** (low)
```python
logger.warning(f"Validation warnings: {len(extracted.validation_errors)}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 679** (low)
```python
logger.warning(f"  - {err}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\laxity_parser.py

**Line 95** (low)
```python
logger.warning(f"Sequence pointer table at ${seq_ptr_addr:04X} is outside loaded data range")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 112** (low)
```python
logger.warning(f"Voice {voice}: pointer offset {ptr_offset} out of range")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 132** (low)
```python
logger.warning(f"Voice {voice}: invalid sequence address ${seq_addr:04X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 194** (low)
```python
logger.warning(f"Could not locate sequence at ${address:04X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 246** (low)
```python
logger.warning(f"Instrument table at ${instr_addr:04X} is outside loaded data range")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 257** (low)
```python
logger.warning("Not enough data for full instrument table")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 290** (low)
```python
logger.warning(f"Command table at ${cmd_addr:04X} is outside loaded data range")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\logging_config.py

**Line 174** (low)
```python
self.logger.error(
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\memmap_analyzer.py

**Line 227** (low)
```python
logger.error(f"Memory map analysis failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 311** (low)
```python
logger.error(f"Failed to generate report: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\midi_sequence_extractor.py

**Line 76** (low)
```python
self.logger.error("mido library not found - cannot extract from MIDI")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 82** (low)
```python
self.logger.error(f"Failed to load MIDI file {midi_path}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\output_organizer.py

**Line 186** (low)
```python
logger.warning(f"Target exists, skipping: {target_path.name}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 199** (low)
```python
logger.error(f"Failed to move {file_path.name}: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 288** (low)
```python
logger.error(f"Failed to create index: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 382** (low)
```python
logger.error(f"Failed to create README: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 419** (low)
```python
logger.warning("No files found to organize")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 472** (low)
```python
logger.error(f"Organization failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\pattern_recognizer.py

**Line 231** (low)
```python
logger.error(f"Pattern analysis failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 315** (low)
```python
logger.error(f"Failed to generate report: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\report_generator.py

**Line 176** (low)
```python
logger.warning("No analysis files found to consolidate")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 302** (low)
```python
logger.error(f"Report generation failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sequence_translator.py

**Line 94** (low)
```python
logger.warning(f"Frequency table at offset ${offset:04X} extends beyond data (len={len(c64_data)})")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 154** (low)
```python
logger.warning(f"Unexpected control byte as note: ${lax_note:02X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 159** (low)
```python
logger.warning(f"Note index ${lax_note:02X} exceeds table size {len(self.frequencies)}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 251** (low)
```python
logger.warning(f"Command index ${byte:02X} (idx={cmd_idx}) not in command table (len={len(self.command_table)})")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 276** (low)
```python
logger.warning(f"Unexpected byte ${byte:02X} at offset ${pos:04X}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sf2_packer.py

**Line 340** (low)
```python
logger.warning("  SF2 format detected: using hybrid extraction (SF2Reader for data, traditional for code)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 346** (low)
```python
logger.warning(f"  SF2Reader parsing failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 347** (low)
```python
logger.warning("  Falling back to traditional fixed-address extraction")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 669** (low)
```python
logger.warning(f"Init address at ${init_dc:04X} appears invalid (all zeros or same bytes)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 676** (low)
```python
logger.warning(f"Using standard PSID init address: ${init_address:04X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 685** (low)
```python
logger.warning(f"Play address at ${play_dc:04X} appears invalid (all zeros or same bytes)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 692** (low)
```python
logger.warning(f"Using standard PSID play address: ${play_address:04X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 947** (low)
```python
logger.error(f"Validation failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 959** (low)
```python
logger.error(f"Pack error: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sf2_player_parser.py

**Line 349** (low)
```python
logger.warning(f"Ran out of data at sequence {file_position} (index {sparse_idx})")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 377** (low)
```python
logger.warning(f"Empty sequence at position {file_position} (index {sparse_idx})")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 429** (low)
```python
logger.warning(f"Failed to extract sequences from SF2 reference: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 482** (low)
```python
logger.warning(f"Failed to extract from embedded SF2: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 485** (low)
```python
logger.warning("No SF2 marker found - file may not be SF2-exported")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sf2_reader.py

**Line 53** (low)
```python
logger.warning("SF2 data too short for header")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 62** (low)
```python
logger.warning(f"Invalid SF2 file ID: ${file_id:04X} (expected $1337)")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 94** (low)
```python
logger.warning("No music data block found")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 141** (low)
```python
logger.warning("No instrument block found")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 168** (low)
```python
logger.warning("No driver tables block found")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 182** (low)
```python
logger.warning("No wave table end marker found")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 211** (low)
```python
logger.warning("No pulse table end marker found")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sf2_writer.py

**Line 107** (low)
```python
logger.warning("No template or driver found, creating minimal structure")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 190** (low)
```python
logger.warning(f" File ID {file_id:04X} != expected {self.SF2_FILE_ID:04X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 335** (low)
```python
logger.warning(" Could not parse SF2 header, using fallback")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 376** (low)
```python
logger.warning(f"     Invalid sequence start offset {seq_start}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 491** (low)
```python
logger.warning(f"     Invalid orderlist start offset {ol_start}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 1377** (low)
```python
logger.error("  Output file too small to contain load address")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 1472** (low)
```python
logger.warning(f"    Patch mismatch at ${file_offset:04X}: expected {old_lo:02X} {old_hi:02X}, found {current_lo:02X} {current_hi:02X}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 1869** (low)
```python
logger.error("  ERR Could not read file for validation")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 1874** (low)
```python
logger.error(f"  ERR File too small: {len(data)} bytes")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 1883** (low)
```python
logger.error(f"  ERR Invalid magic number: 0x{magic:04X} (expected 0x1337)")
```
**Suggestion**: Add actionable suggestion or documentation link

*... and 9 more issues in this file*

#### sidm2\sid_structure_analyzer.py

**Line 58** (low)
```python
logger.error("Failed to get siddump output")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 96** (low)
```python
logger.error(f"siddump failed: {result.stderr}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 100** (low)
```python
logger.error(f"siddump timed out after {duration + 30} seconds")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 103** (low)
```python
logger.error(f"siddump execution failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sid_structure_extractor.py

**Line 149** (low)
```python
logger.error(f"Emulation failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sid_to_midi_emulator.py

**Line 156** (low)
```python
logger.error(f"Emulation failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 173** (low)
```python
logger.warning("No frame states to convert")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 337** (low)
```python
logger.warning("No MIDI events to export")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 459** (low)
```python
logger.error(f"\n[ERROR] Conversion failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 483** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\siddecompiler.py

**Line 110** (low)
```python
logger.warning(f"Python SIDdecompiler not available: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 163** (low)
```python
logger.warning(f"Python SIDdecompiler failed: {e}, falling back to .exe")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\siddump.py

**Line 39** (low)
```python
logger.warning("Python siddump failed, falling back to .exe")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 182** (low)
```python
logger.warning(f"Python siddump returned non-zero: {result}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 208** (low)
```python
logger.warning(f"siddump.exe not found at {siddump_exe}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 220** (low)
```python
logger.error(f"siddump.exe failed for {sid_path}: return code {result.returncode}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 222** (low)
```python
logger.error(f"siddump.exe stderr: {result.stderr}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 228** (low)
```python
logger.warning(f"siddump.exe timed out after {playback_time}s for {sid_path}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 231** (low)
```python
logger.error(f"File not found during siddump.exe for {sid_path}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 234** (low)
```python
logger.error(f"siddump.exe failed for {sid_path}: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\siddump_integration.py

**Line 73** (low)
```python
logger.warning(f"Siddump extraction failed for {sid_file.name}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 121** (low)
```python
logger.error(f"Siddump generation failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\sidwinder_wrapper.py

**Line 73** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 121** (low)
```python
logger.error(f"SIDwinder trace failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\subroutine_tracer.py

**Line 256** (low)
```python
logger.error(f"Subroutine trace failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 396** (low)
```python
logger.error(f"Failed to generate report: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\table_extraction.py

**Line 209** (low)
```python
logger.warning(f"Data too small for instrument table search: {len(data) if data else 0} bytes")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 580** (low)
```python
logger.warning(f"Wave table only has {len(entries)} entries (expected 32+) - may be incomplete")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\vsid_wrapper.py

**Line 125** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 167** (low)
```python
logger.error(f"VSID export failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 177** (low)
```python
logger.error("Output file is empty")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 223** (low)
```python
logger.error(error_msg)
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 232** (low)
```python
logger.error(f"VSID export failed: {error_msg}")
```
**Suggestion**: Add actionable suggestion or documentation link

#### sidm2\wav_comparison.py

**Line 56** (low)
```python
logger.error(f"SID2WAV failed: {result.stderr}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 60** (low)
```python
logger.error(f"SID2WAV timed out after {duration + 30} seconds")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 63** (low)
```python
logger.error(f"WAV generation failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 99** (low)
```python
logger.warning(f"WAV file sizes differ: {len(data1)} vs {len(data2)} bytes")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 127** (low)
```python
logger.warning("Could not extract audio data, using byte comparison only")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 133** (low)
```python
logger.error(f"WAV comparison failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 153** (low)
```python
logger.warning("Could not find 'data' chunk in WAV file")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 167** (low)
```python
logger.error(f"Failed to extract audio data: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 201** (low)
```python
logger.error(f"RMS calculation failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

**Line 246** (low)
```python
logger.error(f"SID-to-WAV comparison failed: {e}")
```
**Suggestion**: Add actionable suggestion or documentation link

*... and 3 more issues in this file*

---

### Missing Doc Links (156 issues)

#### scripts\convert_all.py

**Line 1154** (low)
```python
logger.error(f"Unexpected error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### scripts\sf2_to_sid.py

**Line 429** (low)
```python
logger.error("Conversion failed")
```
**Suggestion**: Add documentation link for user reference

**Line 436** (low)
```python
logger.error(f"Unexpected error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### scripts\sid_to_sf2.py

**Line 342** (low)
```python
logger.error(f"Failed to analyze SID file: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 372** (low)
```python
logger.error(f"Laxity conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 468** (low)
```python
logger.error(f"SF2 Driver 11 template not found at {driver11_template_path}")
```
**Suggestion**: Add documentation link for user reference

**Line 504** (low)
```python
logger.error("Galway conversion produced no output")
```
**Suggestion**: Add documentation link for user reference

**Line 508** (low)
```python
logger.error(f"Galway conversion failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 514** (low)
```python
logger.error(f"Galway conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 659** (low)
```python
logger.error(f"Failed to analyze SID file: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 801** (low)
```python
logger.error(f"FAILED: SF2 format validation failed ({validation_result.errors} errors)")
```
**Suggestion**: Add documentation link for user reference

**Line 805** (low)
```python
logger.error(f"  - {check.name}: {check.message}")
```
**Suggestion**: Add documentation link for user reference

**Line 876** (low)
```python
logger.error(f"Unexpected error during conversion: {e}")
```
**Suggestion**: Add documentation link for user reference

*... and 4 more issues in this file*

#### sidm2\accuracy.py

**Line 113** (low)
```python
logger.error(f"SID file does not exist: {self.sid_path}")
```
**Suggestion**: Add documentation link for user reference

**Line 144** (low)
```python
logger.error(f"Siddump exe not found: {siddump_exe}")
```
**Suggestion**: Add documentation link for user reference

**Line 159** (low)
```python
logger.error(f"Siddump exe failed with return code: {result.returncode}")
```
**Suggestion**: Add documentation link for user reference

**Line 165** (low)
```python
logger.error(f"Siddump exe exception: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 475** (low)
```python
logger.error(f"Failed to capture registers from original SID: {original_sid}")
```
**Suggestion**: Add documentation link for user reference

**Line 480** (low)
```python
logger.error(f"Failed to capture registers from exported SID: {exported_sid}")
```
**Suggestion**: Add documentation link for user reference

**Line 487** (low)
```python
logger.error(f"Accuracy calculation exception: {e}", exc_info=True)
```
**Suggestion**: Add documentation link for user reference

#### sidm2\accuracy_integration.py

**Line 79** (low)
```python
logger.error(f"Accuracy calculation error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 105** (low)
```python
logger.error(f"Accuracy validation failed: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\audio_comparison.py

**Line 41** (low)
```python
raise WAVComparisonError("File too small to be a valid WAV")
```
**Suggestion**: Add documentation link for user reference

**Line 45** (low)
```python
raise WAVComparisonError("Not a WAV file (missing RIFF header)")
```
**Suggestion**: Add documentation link for user reference

**Line 49** (low)
```python
raise WAVComparisonError("Not a WAV file (missing WAVE format)")
```
**Suggestion**: Add documentation link for user reference

**Line 53** (low)
```python
raise WAVComparisonError("Missing fmt chunk")
```
**Suggestion**: Add documentation link for user reference

**Line 74** (low)
```python
raise WAVComparisonError("Missing data chunk")
```
**Suggestion**: Add documentation link for user reference

**Line 103** (low)
```python
raise WAVComparisonError(f"Cannot read file {filepath}: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 136** (low)
```python
raise WAVComparisonError(f"Unsupported bit depth: {bits}")
```
**Suggestion**: Add documentation link for user reference

**Line 230** (low)
```python
raise WAVComparisonError(f"Failed to read WAV files: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 295** (low)
```python
logger.error(f"  Audio comparison error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\audio_export_wrapper.py

**Line 150** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add documentation link for user reference

**Line 215** (low)
```python
logger.error(f"Audio export failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 225** (low)
```python
logger.error(error_msg)
```
**Suggestion**: Add documentation link for user reference

**Line 235** (low)
```python
logger.error(f"Audio export failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\config.py

**Line 33** (low)
```python
raise ValueError(f"Invalid default driver: {self.default_driver}. "
```
**Suggestion**: Add documentation link for user reference

**Line 81** (low)
```python
raise ValueError(f"Invalid validation level: {self.validation_level}")
```
**Suggestion**: Add documentation link for user reference

**Line 84** (low)
```python
raise ValueError(f"Siddump duration must be 1-300 seconds")
```
**Suggestion**: Add documentation link for user reference

**Line 103** (low)
```python
raise ValueError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")
```
**Suggestion**: Add documentation link for user reference

**Line 180** (low)
```python
logger.error(f"Failed to save configuration: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 196** (low)
```python
logger.error(f"Failed to load configuration: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\cpu6502.py

**Line 399** (low)
```python
raise KeyError(f"Unknown opcode ${opcode:02X} at ${address:04X}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\disasm_table_finder.py

**Line 36** (low)
```python
logger.error(f"Failed to disassemble {sid_path}: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 37** (low)
```python
logger.error(f"Output: {e.output}")
```
**Suggestion**: Add documentation link for user reference

**Line 40** (low)
```python
logger.error(f"Failed to disassemble {sid_path}: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\disasm_wrapper.py

**Line 56** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Add documentation link for user reference

**Line 61** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Add documentation link for user reference

**Line 137** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add documentation link for user reference

**Line 200** (low)
```python
logger.error(f"Disassembly failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\errors.py

**Line 15** (low)
```python
raise FileNotFoundError(
```
**Suggestion**: Add documentation link for user reference

#### sidm2\galway_format_converter.py

**Line 118** (low)
```python
logger.error(f"Instrument conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 172** (low)
```python
logger.error(f"Sequence conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 232** (low)
```python
logger.error(f"Wave table conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 278** (low)
```python
logger.error(f"Pulse table conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 323** (low)
```python
logger.error(f"Filter table conversion error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\galway_table_extractor.py

**Line 132** (low)
```python
logger.error(f"Extraction error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\galway_table_injector.py

**Line 108** (low)
```python
logger.error(f"Table {table_type} too large for driver")
```
**Suggestion**: Add documentation link for user reference

**Line 120** (low)
```python
logger.error(f"Injection error for {table_type}: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 281** (low)
```python
logger.error(f"Integration error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\instrument_extraction.py

**Line 63** (low)
```python
raise TableExtractionError(f"Invalid instrument table offset: {instr_offset}")
```
**Suggestion**: Add documentation link for user reference

**Line 74** (low)
```python
raise TableExtractionError(f"Insufficient data for instrument {i} at offset {off}")
```
**Suggestion**: Add documentation link for user reference

**Line 163** (low)
```python
raise TableExtractionError(f"Index error while extracting instruments: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 202** (low)
```python
raise TableExtractionError(f"Data too small for wave table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\laxity_converter.py

**Line 99** (low)
```python
raise FileNotFoundError(f"Driver not found: {self.DRIVER_PATH}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\logging_config.py

**Line 174** (low)
```python
self.logger.error(
```
**Suggestion**: Add documentation link for user reference

#### sidm2\memmap_analyzer.py

**Line 80** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Add documentation link for user reference

**Line 84** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Add documentation link for user reference

**Line 227** (low)
```python
logger.error(f"Memory map analysis failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 311** (low)
```python
logger.error(f"Failed to generate report: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\midi_sequence_extractor.py

**Line 76** (low)
```python
self.logger.error("mido library not found - cannot extract from MIDI")
```
**Suggestion**: Add documentation link for user reference

**Line 82** (low)
```python
self.logger.error(f"Failed to load MIDI file {midi_path}: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\output_organizer.py

**Line 199** (low)
```python
logger.error(f"Failed to move {file_path.name}: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 288** (low)
```python
logger.error(f"Failed to create index: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 472** (low)
```python
logger.error(f"Organization failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\pattern_recognizer.py

**Line 73** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Add documentation link for user reference

**Line 77** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Add documentation link for user reference

**Line 231** (low)
```python
logger.error(f"Pattern analysis failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 315** (low)
```python
logger.error(f"Failed to generate report: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\player_base.py

**Line 265** (low)
```python
raise ValueError("No analyzer available and no default set")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\report_generator.py

**Line 302** (low)
```python
logger.error(f"Report generation failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sf2_compatibility.py

**Line 206** (low)
```python
raise ValueError(f"Unknown driver: {target_driver}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sf2_editor_automation.py

**Line 159** (low)
```python
raise SF2EditorNotFoundError(error_msg)
```
**Suggestion**: Add documentation link for user reference

**Line 218** (low)
```python
raise SF2EditorTimeoutError(error_msg)
```
**Suggestion**: Add documentation link for user reference

**Line 259** (low)
```python
raise SF2EditorNotFoundError(f"Editor not found: {self.editor_path}")
```
**Suggestion**: Add documentation link for user reference

**Line 1563** (low)
```python
raise SF2EditorAutomationError("Failed to launch editor")
```
**Suggestion**: Add documentation link for user reference

**Line 1566** (low)
```python
raise SF2EditorAutomationError("Failed to load SF2 file")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sf2_packer.py

**Line 947** (low)
```python
logger.error(f"Validation failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 948** (low)
```python
logger.error("SID file not written (use validate=False to override)")
```
**Suggestion**: Add documentation link for user reference

**Line 959** (low)
```python
logger.error(f"Pack error: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sf2_player_parser.py

**Line 175** (low)
```python
raise ValueError("SF2 reference file required for this method")
```
**Suggestion**: Add documentation link for user reference

**Line 517** (low)
```python
raise ValueError("SF2 marker not found in data")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sf2_writer.py

**Line 1377** (low)
```python
logger.error("  Output file too small to contain load address")
```
**Suggestion**: Add documentation link for user reference

**Line 1869** (low)
```python
logger.error("  ERR Could not read file for validation")
```
**Suggestion**: Add documentation link for user reference

**Line 1874** (low)
```python
logger.error(f"  ERR File too small: {len(data)} bytes")
```
**Suggestion**: Add documentation link for user reference

**Line 1883** (low)
```python
logger.error(f"  ERR Invalid magic number: 0x{magic:04X} (expected 0x1337)")
```
**Suggestion**: Add documentation link for user reference

**Line 1904** (low)
```python
logger.error(f"  ERR File truncated at block {block_id}")
```
**Suggestion**: Add documentation link for user reference

**Line 1911** (low)
```python
logger.error(f"  ERR Block {block_id} extends beyond file (declares {block_size} bytes)")
```
**Suggestion**: Add documentation link for user reference

**Line 1944** (low)
```python
logger.error("  ERR Too many blocks (possible corruption)")
```
**Suggestion**: Add documentation link for user reference

**Line 1965** (low)
```python
logger.error("    ERR Instruments table (0x80) MISSING - file will be rejected!")
```
**Suggestion**: Add documentation link for user reference

**Line 1970** (low)
```python
logger.error("    ERR Commands table (0x81) MISSING - file will be rejected!")
```
**Suggestion**: Add documentation link for user reference

**Line 1972** (low)
```python
logger.error("  ERR Block 3 (Driver Tables) missing")
```
**Suggestion**: Add documentation link for user reference

*... and 1 more issues in this file*

#### sidm2\sid_player.py

**Line 140** (low)
```python
raise ValueError(f"Invalid SID file magic: {magic}")
```
**Suggestion**: Add documentation link for user reference

**Line 238** (low)
```python
raise RuntimeError("No SID file loaded")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sid_structure_analyzer.py

**Line 39** (low)
```python
raise FileNotFoundError(f"siddump not found at {siddump_path}")
```
**Suggestion**: Add documentation link for user reference

**Line 58** (low)
```python
logger.error("Failed to get siddump output")
```
**Suggestion**: Add documentation link for user reference

**Line 96** (low)
```python
logger.error(f"siddump failed: {result.stderr}")
```
**Suggestion**: Add documentation link for user reference

**Line 100** (low)
```python
logger.error(f"siddump timed out after {duration + 30} seconds")
```
**Suggestion**: Add documentation link for user reference

**Line 103** (low)
```python
logger.error(f"siddump execution failed: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sid_structure_extractor.py

**Line 149** (low)
```python
logger.error(f"Emulation failed: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sid_to_midi_emulator.py

**Line 65** (low)
```python
raise ImportError("mido library required. Install with: pip install mido")
```
**Suggestion**: Add documentation link for user reference

**Line 156** (low)
```python
logger.error(f"Emulation failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 459** (low)
```python
logger.error(f"\n[ERROR] Conversion failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 483** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\siddecompiler.py

**Line 115** (low)
```python
raise FileNotFoundError(
```
**Suggestion**: Add documentation link for user reference

#### sidm2\siddump.py

**Line 220** (low)
```python
logger.error(f"siddump.exe failed for {sid_path}: return code {result.returncode}")
```
**Suggestion**: Add documentation link for user reference

**Line 222** (low)
```python
logger.error(f"siddump.exe stderr: {result.stderr}")
```
**Suggestion**: Add documentation link for user reference

**Line 231** (low)
```python
logger.error(f"File not found during siddump.exe for {sid_path}: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 234** (low)
```python
logger.error(f"siddump.exe failed for {sid_path}: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\siddump_integration.py

**Line 101** (low)
```python
logger.error(f"Failed to run Python siddump: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 121** (low)
```python
logger.error(f"Siddump generation failed: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\sidwinder_wrapper.py

**Line 73** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add documentation link for user reference

**Line 121** (low)
```python
logger.error(f"SIDwinder trace failed: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\subroutine_tracer.py

**Line 76** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Add documentation link for user reference

**Line 80** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Add documentation link for user reference

**Line 256** (low)
```python
logger.error(f"Subroutine trace failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 396** (low)
```python
logger.error(f"Failed to generate report: {e}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\table_extraction.py

**Line 85** (low)
```python
raise TableExtractionError(f"Data too small for table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Add documentation link for user reference

**Line 113** (low)
```python
raise TableExtractionError(f"Index error while searching for SID register tables: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 133** (low)
```python
raise TableExtractionError(f"Data too small for player code analysis: {len(data) if data else 0} bytes")
```
**Suggestion**: Add documentation link for user reference

**Line 173** (low)
```python
raise TableExtractionError(f"Index error while analyzing player code: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 186** (low)
```python
raise TableExtractionError(f"Error selecting table candidates: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 346** (low)
```python
raise TableExtractionError(f"Index error while searching for instrument table: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 515** (low)
```python
raise TableExtractionError(f"Data too small for wave table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Add documentation link for user reference

**Line 667** (low)
```python
raise TableExtractionError(f"Index error while extracting wave table: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 703** (low)
```python
raise TableExtractionError(f"Data too small for pulse table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Add documentation link for user reference

**Line 894** (low)
```python
raise TableExtractionError(f"Data too small for filter table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\vsid_wrapper.py

**Line 125** (low)
```python
logger.error(f"SID file not found: {sid_file}")
```
**Suggestion**: Add documentation link for user reference

**Line 167** (low)
```python
logger.error(f"VSID export failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

**Line 177** (low)
```python
logger.error("Output file is empty")
```
**Suggestion**: Add documentation link for user reference

**Line 223** (low)
```python
logger.error(error_msg)
```
**Suggestion**: Add documentation link for user reference

**Line 232** (low)
```python
logger.error(f"VSID export failed: {error_msg}")
```
**Suggestion**: Add documentation link for user reference

#### sidm2\wav_comparison.py

**Line 25** (low)
```python
raise FileNotFoundError(f"SID2WAV.EXE not found at {sid2wav_path}")
```
**Suggestion**: Add documentation link for user reference

**Line 56** (low)
```python
logger.error(f"SID2WAV failed: {result.stderr}")
```
**Suggestion**: Add documentation link for user reference

**Line 60** (low)
```python
logger.error(f"SID2WAV timed out after {duration + 30} seconds")
```
**Suggestion**: Add documentation link for user reference

**Line 63** (low)
```python
logger.error(f"WAV generation failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 133** (low)
```python
logger.error(f"WAV comparison failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 167** (low)
```python
logger.error(f"Failed to extract audio data: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 201** (low)
```python
logger.error(f"RMS calculation failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 246** (low)
```python
logger.error(f"SID-to-WAV comparison failed: {e}")
```
**Suggestion**: Add documentation link for user reference

**Line 284** (low)
```python
logger.error(f"WAV comparison failed: {results.get('error', 'Unknown error')}")
```
**Suggestion**: Add documentation link for user reference

**Line 288** (low)
```python
logger.error(f"Quick WAV compare failed: {e}")
```
**Suggestion**: Add documentation link for user reference

---

### Missing Alternatives (52 issues)

#### sidm2\audio_comparison.py

**Line 41** (low)
```python
raise WAVComparisonError("File too small to be a valid WAV")
```
**Suggestion**: Consider providing alternative approach

**Line 45** (low)
```python
raise WAVComparisonError("Not a WAV file (missing RIFF header)")
```
**Suggestion**: Consider providing alternative approach

**Line 49** (low)
```python
raise WAVComparisonError("Not a WAV file (missing WAVE format)")
```
**Suggestion**: Consider providing alternative approach

**Line 53** (low)
```python
raise WAVComparisonError("Missing fmt chunk")
```
**Suggestion**: Consider providing alternative approach

**Line 74** (low)
```python
raise WAVComparisonError("Missing data chunk")
```
**Suggestion**: Consider providing alternative approach

**Line 103** (low)
```python
raise WAVComparisonError(f"Cannot read file {filepath}: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 136** (low)
```python
raise WAVComparisonError(f"Unsupported bit depth: {bits}")
```
**Suggestion**: Consider providing alternative approach

**Line 230** (low)
```python
raise WAVComparisonError(f"Failed to read WAV files: {e}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\config.py

**Line 33** (low)
```python
raise ValueError(f"Invalid default driver: {self.default_driver}. "
```
**Suggestion**: Consider providing alternative approach

**Line 81** (low)
```python
raise ValueError(f"Invalid validation level: {self.validation_level}")
```
**Suggestion**: Consider providing alternative approach

**Line 84** (low)
```python
raise ValueError(f"Siddump duration must be 1-300 seconds")
```
**Suggestion**: Consider providing alternative approach

**Line 103** (low)
```python
raise ValueError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\cpu6502.py

**Line 399** (low)
```python
raise KeyError(f"Unknown opcode ${opcode:02X} at ${address:04X}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\disasm_wrapper.py

**Line 56** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Consider providing alternative approach

**Line 61** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\errors.py

**Line 15** (low)
```python
raise FileNotFoundError(
```
**Suggestion**: Consider providing alternative approach

#### sidm2\instrument_extraction.py

**Line 63** (low)
```python
raise TableExtractionError(f"Invalid instrument table offset: {instr_offset}")
```
**Suggestion**: Consider providing alternative approach

**Line 74** (low)
```python
raise TableExtractionError(f"Insufficient data for instrument {i} at offset {off}")
```
**Suggestion**: Consider providing alternative approach

**Line 163** (low)
```python
raise TableExtractionError(f"Index error while extracting instruments: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 202** (low)
```python
raise TableExtractionError(f"Data too small for wave table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\laxity_converter.py

**Line 99** (low)
```python
raise FileNotFoundError(f"Driver not found: {self.DRIVER_PATH}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\memmap_analyzer.py

**Line 80** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Consider providing alternative approach

**Line 84** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\pattern_recognizer.py

**Line 73** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Consider providing alternative approach

**Line 77** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\player_base.py

**Line 265** (low)
```python
raise ValueError("No analyzer available and no default set")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\sf2_compatibility.py

**Line 206** (low)
```python
raise ValueError(f"Unknown driver: {target_driver}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\sf2_editor_automation.py

**Line 159** (low)
```python
raise SF2EditorNotFoundError(error_msg)
```
**Suggestion**: Consider providing alternative approach

**Line 218** (low)
```python
raise SF2EditorTimeoutError(error_msg)
```
**Suggestion**: Consider providing alternative approach

**Line 259** (low)
```python
raise SF2EditorNotFoundError(f"Editor not found: {self.editor_path}")
```
**Suggestion**: Consider providing alternative approach

**Line 1563** (low)
```python
raise SF2EditorAutomationError("Failed to launch editor")
```
**Suggestion**: Consider providing alternative approach

**Line 1566** (low)
```python
raise SF2EditorAutomationError("Failed to load SF2 file")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\sf2_player_parser.py

**Line 175** (low)
```python
raise ValueError("SF2 reference file required for this method")
```
**Suggestion**: Consider providing alternative approach

**Line 517** (low)
```python
raise ValueError("SF2 marker not found in data")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\sid_player.py

**Line 140** (low)
```python
raise ValueError(f"Invalid SID file magic: {magic}")
```
**Suggestion**: Consider providing alternative approach

**Line 238** (low)
```python
raise RuntimeError("No SID file loaded")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\sid_structure_analyzer.py

**Line 39** (low)
```python
raise FileNotFoundError(f"siddump not found at {siddump_path}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\sid_to_midi_emulator.py

**Line 65** (low)
```python
raise ImportError("mido library required. Install with: pip install mido")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\siddecompiler.py

**Line 115** (low)
```python
raise FileNotFoundError(
```
**Suggestion**: Consider providing alternative approach

#### sidm2\subroutine_tracer.py

**Line 76** (low)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Consider providing alternative approach

**Line 80** (low)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\table_extraction.py

**Line 85** (low)
```python
raise TableExtractionError(f"Data too small for table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Consider providing alternative approach

**Line 113** (low)
```python
raise TableExtractionError(f"Index error while searching for SID register tables: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 133** (low)
```python
raise TableExtractionError(f"Data too small for player code analysis: {len(data) if data else 0} bytes")
```
**Suggestion**: Consider providing alternative approach

**Line 173** (low)
```python
raise TableExtractionError(f"Index error while analyzing player code: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 186** (low)
```python
raise TableExtractionError(f"Error selecting table candidates: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 346** (low)
```python
raise TableExtractionError(f"Index error while searching for instrument table: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 515** (low)
```python
raise TableExtractionError(f"Data too small for wave table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Consider providing alternative approach

**Line 667** (low)
```python
raise TableExtractionError(f"Index error while extracting wave table: {e}")
```
**Suggestion**: Consider providing alternative approach

**Line 703** (low)
```python
raise TableExtractionError(f"Data too small for pulse table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Consider providing alternative approach

**Line 894** (low)
```python
raise TableExtractionError(f"Data too small for filter table extraction: {len(data) if data else 0} bytes")
```
**Suggestion**: Consider providing alternative approach

#### sidm2\wav_comparison.py

**Line 25** (low)
```python
raise FileNotFoundError(f"SID2WAV.EXE not found at {sid2wav_path}")
```
**Suggestion**: Consider providing alternative approach

---

### Generic Exceptions (24 issues)

#### scripts\sid_to_sf2.py

**Line 1022** (medium)
```python
raise IOError("Failed to generate any SF2 files")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### scripts\test_logging_system.py

**Line 248** (medium)
```python
raise ValueError("Test error")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\config.py

**Line 33** (medium)
```python
raise ValueError(f"Invalid default driver: {self.default_driver}. "
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 81** (medium)
```python
raise ValueError(f"Invalid validation level: {self.validation_level}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 84** (medium)
```python
raise ValueError(f"Siddump duration must be 1-300 seconds")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 103** (medium)
```python
raise ValueError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\disasm_wrapper.py

**Line 56** (medium)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 61** (medium)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\laxity_converter.py

**Line 99** (medium)
```python
raise FileNotFoundError(f"Driver not found: {self.DRIVER_PATH}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\memmap_analyzer.py

**Line 80** (medium)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 84** (medium)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\pattern_recognizer.py

**Line 73** (medium)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 77** (medium)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\player_base.py

**Line 265** (medium)
```python
raise ValueError("No analyzer available and no default set")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\sf2_compatibility.py

**Line 206** (medium)
```python
raise ValueError(f"Unknown driver: {target_driver}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\sf2_player_parser.py

**Line 175** (medium)
```python
raise ValueError("SF2 reference file required for this method")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 517** (medium)
```python
raise ValueError("SF2 marker not found in data")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\sid_player.py

**Line 140** (medium)
```python
raise ValueError(f"Invalid SID file magic: {magic}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 238** (medium)
```python
raise RuntimeError("No SID file loaded")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\sid_structure_analyzer.py

**Line 39** (medium)
```python
raise FileNotFoundError(f"siddump not found at {siddump_path}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\siddecompiler.py

**Line 115** (medium)
```python
raise FileNotFoundError(
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\subroutine_tracer.py

**Line 76** (medium)
```python
raise ValueError("SID file too small")
```
**Suggestion**: Replace with rich error class from sidm2.errors

**Line 80** (medium)
```python
raise ValueError(f"Invalid SID magic: {magic}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

#### sidm2\wav_comparison.py

**Line 25** (medium)
```python
raise FileNotFoundError(f"SID2WAV.EXE not found at {sid2wav_path}")
```
**Suggestion**: Replace with rich error class from sidm2.errors

---

### Technical Jargon (1 issues)

#### sidm2\galway_format_converter.py

**Line 172** (low)
```python
logger.error(f"Sequence conversion error: {e}")
```
**Suggestion**: Explain technical term "sequence"

---

## Recommendations

### High Priority

1. **Replace Generic Exceptions**
   - Use `sidm2.errors` rich error classes
   - Provide context, suggestions, and documentation links
   - Example: Replace `ValueError` with `InvalidInputError`

2. **Enhance Logger Errors**
   - Add actionable suggestions to all error logs
   - Include troubleshooting steps
   - Link to relevant documentation

### Medium Priority

3. **Add Documentation Links**
   - Link errors to TROUBLESHOOTING.md sections
   - Provide direct links to relevant guides

4. **Explain Technical Jargon**
   - Define technical terms in error messages
   - Provide context for domain-specific concepts

### Low Priority

5. **Add Alternative Approaches**
   - Suggest fallback options
   - Provide workarounds when available
