# SF2 to SID Conversion - Technical Limitations

## Summary

After exploring the SID Factory II source code and attempting to create a Python-based SF2 → PSID converter, I discovered that **direct conversion is not feasible** without replicating the complex driver relocation logic from SID Factory II.

## The Problem

### SF2 File Format
- SF2 files are **data containers**, not executable programs
- They contain:
  - Driver code (6502 assembly)
  - Music data (sequences, instruments, wave/pulse/filter tables)
  - Metadata (title, author, copyright)
- Load address (e.g., $0D7E) points to the **data section**, not executable code

### What's Needed for SID Export
1. **Driver Relocation**: Driver code must be relocated to a specific memory location
2. **Address Patching**: All internal pointers must be updated
3. **Init/Play Entry Points**: Must be determined from driver-specific offsets
4. **Memory Layout**: Different drivers have different memory layouts

## Attempted Solution

Created `sf2_to_sid.py` which:
- ✅ Reads SF2 files correctly
- ✅ Extracts metadata (title, author, copyright)
- ✅ Creates valid PSID headers
- ❌ **Cannot create playable SID files** due to:
  - Driver code starts at different offsets depending on driver version
  - Relocation requires understanding of driver internals
  - The PRG load address ($0D7E) is not an executable entry point

### Test Results

```bash
$ python sf2_to_sid.py SF2/Angular_d11_final.sf2 output.sid
# Creates file, but:
$ tools/siddump.exe output.sid
Load address: $0D7E Init address: $0D7E Play address: $0D81
Error: Unknown opcode $37 at $0D7E
```

**Why it fails**: $0D7E contains data (0x37 = table data), not executable 6502 code.

## Why SID Factory II Can Do It

From analyzing `SIDFactoryII/source/utils/psidfile.cpp`:

```cpp
unsigned short driver_address = read_load_address_from_prg(inPRGData);
m_Header.m_InitAddress = endian_convert(driver_address + inInitOffset);
m_Header.m_UpdateAddress = endian_convert(driver_address + inUpdateOffset);
```

SID Factory II knows:
- Exact driver structure for each driver version
- Where executable code actually starts (not just PRG load address)
- How to relocate code and patch addresses
- Init/play offsets for each driver type

This knowledge is embedded in:
- `runtime/editor/driver/driver_info.cpp` (~500 lines)
- `runtime/editor/driver/driver_architecture_sidfactory2.cpp` (~800 lines)
- Complex C++ class hierarchies with Qt dependencies

## Alternative Approaches Considered

### 1. Extract and Recompile SF2 Source Components ❌
**Effort**: Very High
- Requires C++ compilation with Qt framework
- Complex dependencies (SDL2, emulation layer, etc.)
- Would need to extract 10+ source files
- Platform-specific (Windows/Linux/Mac)

### 2. Reverse Engineer Driver Relocation ❌
**Effort**: High
- Would need to disassemble all driver versions
- Understand relocation logic for each
- Implement 6502 code patching
- Fragile (breaks with new driver versions)

### 3. Use SIDFactoryII.exe Command Line ❌
**Not Available**: SIDFactoryII.exe is GUI-only, no CLI for export

### 4. GUI Automation (AutoHotkey, etc.) ⚠️
**Effort**: Medium, **Reliability**: Low
- Could script SIDFactoryII GUI interactions
- Fragile (breaks if UI changes)
- Platform-specific (Windows only)
- Difficult to debug

## Current Solution: Validation Without Round-Trip

Instead of SF2 → SID → WAV, use:

### Approach 1: Direct Data Comparison ✅
```
Original SID → Siddump → ADSR/Waveform data
             ↘
               → SF2 Converter → Extract same data
                              ↓
                         Compare results
```

**Implemented in** `validate_conversion.py`:
- Extracts actual ADSR values from SID playback via siddump
- Extracts ADSR values from our converter
- Compares: instruments, waveforms, pulse/filter data
- Generates HTML reports

### Approach 2: Audio Reference Comparison ✅
```
Original SID → SID2WAV → Reference WAV file
```

**Implemented in** `validate_conversion.py`:
- Creates reference WAV from original SID
- User manually plays SF2 in SID Factory II
- Compares by ear (subjective but effective)

### Approach 3: Manual SF2 Export (Documented) ✅
**Workflow**:
1. Open SF2 file in SID Factory II
2. File → Export → SID file
3. Use exported SID for comparison

**Advantage**: Uses official exporter with correct relocation
**Disadvantage**: Manual step required

## What We Achieved

### 1. Automated Validation Tool ✅
`validate_conversion.py` provides:
- Siddump analysis (actual runtime behavior)
- ADSR/waveform comparison
- Reference WAV generation
- Detailed HTML reports
- Command-line interface

### 2. SF2 Format Understanding ✅
Documented SF2 structure:
- Driver architecture
- Table layouts (wave, pulse, filter, etc.)
- Sequence format
- Auxiliary data (metadata)

### 3. Conversion Quality Improvements ✅
Through validation, we fixed:
- Phase 1: Duration bytes and command parameters
- Phase 2: Instrument ADSR extraction
- Phase 3: Tempo extraction from break speeds

## Recommendations

### For Current Project
1. **Use `validate_conversion.py`** for automated testing
2. **Manual SF2 → SID export** via SID Factory II GUI when needed
3. **Compare WAV files** for audio quality verification

### For Future Enhancement
If SF2 → SID export is critical:

**Option A: Minimal C++ Wrapper** (Recommended if needed)
- Extract just the PSIDFile class + dependencies
- Create minimal C++ CLI tool (~500 lines)
- Python can call this tool via subprocess
- **Effort**: 1-2 days
- **Maintenance**: Low (stable API)

**Option B: Wait for Official CLI**
- Request feature from SID Factory II developers
- Official solution would be most reliable

**Option C: Accept Limitation**
- Current validation approach is sufficient for development
- Manual export for final testing

## Conclusion

**SF2 → SID conversion requires driver-specific knowledge that's impractical to replicate in Python.**

However, our current validation tools provide excellent coverage:
- ✅ Data extraction accuracy (ADSR, waveforms, tables)
- ✅ Reference audio generation (WAV files)
- ✅ Detailed comparison reports
- ✅ Easy-to-use CLI interface

For full round-trip testing, use the manual workflow with SID Factory II's built-in export feature.

## Files Created

| File | Purpose | Status |
|------|---------|--------|
| `validate_conversion.py` | Automated validation tool | ✅ Working |
| `sf2_to_sid.py` | Attempted SF2→SID converter | ⚠️ Incomplete (architectural limitation) |
| `docs/VALIDATION_TOOL.md` | Validation tool documentation | ✅ Complete |
| `docs/SF2_TO_SID_LIMITATIONS.md` | This document | ✅ Complete |

## References

- `SIDFactoryII/source/utils/psidfile.cpp` - Official PSID export implementation
- `SIDFactoryII/source/runtime/editor/driver/driver_info.cpp` - Driver metadata
- `SIDFactoryII/source/runtime/editor/converters/utils/sf2_interface.h` - SF2 interface
