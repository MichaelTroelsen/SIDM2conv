# Tools Reference

Complete reference for all external tools used in the SIDM2 project.

## Quick Reference

| Tool | Purpose | Status |
|------|---------|--------|
| siddump.exe | SID register dump (6502 emulation) | ✅ Working |
| player-id.exe | Player type identification | ✅ Working |
| SID2WAV.EXE | SID to WAV audio rendering | ✅ Working |
| SIDwinder.exe | SID processor (disassembly, trace, player, relocate) | ⚠️ Disassembly works, trace needs rebuild |
| sf2pack | C++ SF2 to SID packer (reference) | ✅ Working |
| RetroDebugger | Real-time C64/SID debugger | ⚠️ Not integrated |

## Siddump

**Location**: `tools/siddump.exe`
**Purpose**: Emulates 6502 CPU to run SID files and capture register writes frame-by-frame
**Source**: `tools/siddump.c`

### Usage

```bash
# Basic usage - dump to stdout
tools/siddump.exe SID/file.sid > output/file.dump

# With timing info (30 seconds)
tools/siddump.exe SID/file.sid -z -t30

# Specific subtune
tools/siddump.exe SID/file.sid -a2 -t30
```

### Options

- `-a<n>` - Select subtune number (default: 0)
- `-t<n>` - Duration in seconds (default: 120)
- `-z` - Include cycle timing information
- `-v` - Verbose output with frame information

### Output Format

Pipe-delimited table format with frame-by-frame SID register writes:
```
Frame|Voice|Freq|Pulse|Waveform|ADSR|Filter
0|1|1234|2048|17|249|0
1|1|1234|2048|16|249|0
...
```

### Integration

- Used by `complete_pipeline_with_validation.py` (Step 3) to generate `.dump` files
- Used by `validate_sid_accuracy.py` for frame-by-frame comparison
- Used by `sidm2/siddump_extractor.py` (v1.3) for runtime sequence extraction

### See Also

- `docs/SIDDUMP_ANALYSIS.md` - Complete source code analysis
- `docs/SIDDUMP_DEEP_DIVE.md` - Deep dive into internals

---

## Player-ID

**Location**: `tools/player-id.exe`
**Purpose**: Identifies SID player type from binary patterns
**Status**: ✅ Working

### Usage

```bash
tools/player-id.exe SID/file.sid
```

### Output

Returns player type string (e.g., "Laxity NewPlayer v21", "JCH", "GoatTracker", etc.)

### Integration

- Used by `scripts/sid_to_sf2.py` to determine conversion method
- Supports detection of 50+ player types

---

## SID2WAV

**Location**: `tools/SID2WAV.EXE`
**Purpose**: Converts SID files to WAV audio for listening and comparison
**Status**: ✅ Working

### Usage

```bash
# Basic conversion (30 seconds, 16-bit)
tools/SID2WAV.EXE -t30 -16 SID/file.sid output/file.wav

# Specific subtune
tools/SID2WAV.EXE -t30 -16 -a2 SID/file.sid output/file.wav

# Full quality (44.1kHz, 16-bit)
tools/SID2WAV.EXE -t60 -16 -o44100 SID/file.sid output/file.wav
```

### Options

- `-t<n>` - Duration in seconds
- `-16` - 16-bit output (default: 8-bit)
- `-a<n>` - Subtune number
- `-o<freq>` - Sample rate (22050, 44100, 48000)

### Integration

- Used by `complete_pipeline_with_validation.py` (Step 4) to render both original and exported SIDs
- Enables audio quality comparison during validation

---

## SIDwinder

**Location**: `tools/SIDwinder.exe`
**Version**: v0.2.6
**Purpose**: Comprehensive C64 SID file processor
**Source**: `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src`

### Capabilities

SIDwinder provides four main functions:

1. **Disassembly** - ✅ Working
2. **Trace** - ⚠️ Broken (fix available, needs rebuild)
3. **Player Generation** - ⚠️ Not integrated
4. **Relocation** - ⚠️ Not integrated

### 1. Disassembly (WORKING)

Converts SID files to KickAssembler-compatible 6502 assembly code.

```bash
# Disassemble to .asm file
tools/SIDwinder.exe -disassemble SID/file.sid output/file.asm
```

**Features**:
- KickAssembler-compatible syntax
- Metadata comments (title, author, copyright)
- Labeled data blocks and code sections
- Full 6502 instruction set support

**Integration**: Integrated in `complete_pipeline_with_validation.py` (Step 9)

**Known Limitation**: Exported SID files from `sf2_packer.py` fail disassembly with "Execution at $0000" error due to pointer relocation bug in packer. Original SID files disassemble correctly.

### 2. Trace (BROKEN - Fix Available)

Captures SID register writes frame-by-frame during playback.

```bash
# Trace SID register writes (currently broken)
tools/SIDwinder.exe -trace=output.txt SID/file.sid
```

**Status**: ⚠️ Currently produces empty output due to three bugs

**Bugs (FIXED in source code on 2024-12-06)**:
1. **TraceLogger.cpp** - Missing public `logWrite()` method (lines 51-61) ✅ FIXED
2. **SIDEmulator.cpp** - SID write callback not calling trace logger (lines 52-55) ✅ FIXED
3. **SIDEmulator.cpp** - Callback not enabled for trace-only commands (line 129) ✅ FIXED

**Patch File**: `tools/sidwinder_trace_fix.patch`

**To Rebuild and Activate**:
```bash
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6

# All source files already patched, just rebuild:
build.bat

# Copy new executable to tools
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

**After Rebuild Benefits**:
- ✅ Step 6 trace generation will produce working output
- ✅ Frame-by-frame SID register comparison (original vs exported)
- ✅ Debug data for "Execution at $0000" packer issues
- ✅ Complete validation system for SF2→SID conversion

**Output Format** (after rebuild):
```
FRAME 0: D400:$00,D401:$08,D404:$11,...
FRAME 1: D400:$10,D401:$0E,D404:$21,...
...
```

**Integration**: Added to `complete_pipeline_with_validation.py` (Step 6), currently generates empty files with "[WARN - needs rebuilt SIDwinder]" message.

### 3. Player Generation (Not Integrated)

Creates standalone .prg files with visualization players.

```bash
# Create player with visualization
tools/SIDwinder.exe -player=RaistlinBars music.sid music.prg
```

**Available Visualizations**:
- RaistlinBars - Classic bar visualization
- Other visualization types (see SIDwinder docs)

**Status**: Available but not integrated into pipeline

### 4. Relocation (Not Integrated)

Moves SID files to different memory addresses with pointer updates.

```bash
# Relocate SID to different address
tools/SIDwinder.exe -relocate=$2000 input.sid output.sid
```

**Potential Use**: Could help debug pointer relocation issues in `sf2_packer.py`

### Additional Features

- **Pattern Recognition**: SIDPatternFinder for improved table extraction
- **Memory Analysis**: Detailed memory maps and usage tracking
- **Verification Mode**: Validate pointer relocations

### Documentation

- `tools/SIDWINDER_ANALYSIS.md` - Complete 600+ line source code analysis
- `tools/SIDWINDER_QUICK_REFERENCE.md` - Quick command reference

---

## sf2pack (C++ Reference Implementation)

**Location**: `tools/sf2pack/`
**Purpose**: Reference implementation of SF2 to SID packing
**Status**: ✅ Working (used as reference, Python version is primary)

### Files

- `sf2pack.exe` - Main packer executable
- `packer_simple.cpp` - Core relocation logic (343 abs + 114 ZP relocations)
- `opcodes.cpp` - Complete 256-opcode 6502 lookup table
- `c64memory.cpp` - 64KB memory management
- `psidfile.cpp` - PSID v2 file export

### Usage

```bash
# Build (requires MinGW)
cd tools/sf2pack
mingw32-make

# Pack SF2 to SID
tools/sf2pack/sf2pack.exe SF2/file.sf2 output.sid --title "Title" --author "Author"

# Verbose mode with stats
tools/sf2pack/sf2pack.exe SF2/file.sf2 output.sid -v
```

### Options

- `--title "text"` - Set SID title metadata
- `--author "text"` - Set author metadata
- `--copyright "text"` - Set copyright metadata
- `-v` - Verbose output with relocation statistics

### Note

The Python implementation in `sidm2/sf2_packer.py` (v0.6.0) is now the primary packer. The C++ version serves as a reference for correctness validation.

---

## RetroDebugger

**Location**: `C:\Users\mit\Downloads\RetroDebugger-master\RetroDebugger-master\`
**Version**: v0.64.68
**Purpose**: Real-time C64/Atari/NES debugger with advanced SID debugging
**Status**: ⚠️ Available but not integrated

### Architecture

- Embeds VICE v3.1 emulator with reSID library
- SDL2 + ImGui GUI for real-time visualization
- HTTP/JSON REST API for remote debugging
- Multi-platform support (Windows, Linux, macOS)

### Key SID Features

#### 1. Real-Time SID Register Access
- Read/write all 32 SID registers ($D400-$D41F)
- Multi-SID support (mono/stereo/triple)
- Burst-write mode to avoid side effects
- Per-channel muting and control

#### 2. Waveform Visualization
- Real-time oscilloscope display per voice
- Mixed output waveform
- Historical state tracking
- Step backward/forward through emulation

#### 3. Remote Debugging API (HTTP/JSON)

```python
import requests

# Read SID registers
response = requests.post(
    'http://localhost:6502/c64/sid/read',
    json={'num': 0, 'registers': [0, 1, 2, 3, 4, 5, 6]}
)

# Write SID registers
response = requests.post(
    'http://localhost:6502/c64/sid/write',
    json={'sids': [{'num': 0, 'registers': {'0': '0x10', '1': '0x20'}}]}
)

# Load SID file
response = requests.post(
    'http://localhost:6502/c64/load',
    json={'path': '/path/to/file.sid', 'run': True}
)
```

#### 4. Full C64 Emulation
- Complete memory inspection ($0000-$FFFF)
- CPU state tracking with breakpoints
- VIC-II and CIA register access
- PSID/RSID file loading

#### 5. reSID Integration
- 6581/8580 chip emulation
- Multiple sampling methods (Fast, Interpolating, Resampling)
- Filter emulation with configurable passband
- Accurate audio rendering

### Integration Opportunities

| Use Case | Value | Complexity |
|----------|-------|------------|
| Remote API Validation | HIGH | Medium |
| Waveform Comparison | MEDIUM | High |
| Interactive Debugging | MEDIUM | Low |
| Batch Testing | LOW | High |

### Example Integration

```python
class RetroDebuggerValidator:
    def __init__(self, host='localhost', port=6502):
        self.base_url = f'http://{host}:{port}'

    def load_sid(self, sid_path):
        response = requests.post(
            f'{self.base_url}/c64/load',
            json={'path': sid_path, 'run': True}
        )
        return response.status_code == 200

    def read_sid_registers(self, sid_num=0):
        response = requests.post(
            f'{self.base_url}/c64/sid/read',
            json={'num': sid_num, 'registers': list(range(0x20))}
        )
        return response.json()['registers']

    def compare_sids(self, original_sid, converted_sid):
        """Compare register states between original and converted SID files"""
        self.load_sid(original_sid)
        time.sleep(2)  # Let it play
        original_regs = self.read_sid_registers()

        self.load_sid(converted_sid)
        time.sleep(2)
        converted_regs = self.read_sid_registers()

        # Calculate differences
        differences = []
        for reg_num, (orig, conv) in enumerate(zip(original_regs, converted_regs)):
            if orig != conv:
                differences.append({
                    'register': f'${reg_num:02X}',
                    'original': f'${orig:02X}',
                    'converted': f'${conv:02X}'
                })

        return differences
```

### Comparison with Existing Tools

| Feature | RetroDebugger | SIDwinder | siddump |
|---------|--------------|-----------|---------|
| Real-time debugging | ✅ Full GUI | ❌ No | ❌ No |
| SID register access | ✅ Read/Write | ⚠️ Read-only | ✅ Write trace |
| Waveform visualization | ✅ Real-time | ❌ No | ❌ No |
| Remote API | ✅ HTTP/JSON | ❌ No | ❌ No |
| Disassembly | ✅ Interactive | ✅ Best quality | ❌ No |
| Batch processing | ⚠️ Limited | ✅ Excellent | ✅ Excellent |

### When to Use

**Use RetroDebugger for**:
- Interactive debugging of conversion issues
- Visual inspection of SID register states
- Remote validation via API
- Waveform analysis and comparison
- Manual testing of specific music sections

**Use SIDwinder/siddump for**:
- Batch processing of multiple files
- Automated pipeline integration
- High-quality disassembly output
- Command-line only workflows

### Documentation

- `tools/RETRODEBUGGER_ANALYSIS.md` - Complete 70KB+ documentation
- Full architecture, API specifications, and integration examples
- Python code samples for SIDM2 integration
- Implementation roadmap with 4 phases

### Potential Future Integration

1. **Phase 1** - Manual testing workflow (immediate use)
2. **Phase 2** - Remote API validation script
3. **Phase 3** - Waveform comparison integration
4. **Phase 4** - Automated regression testing

---

## Tool Comparison Matrix

| Feature | siddump | SIDwinder | SID2WAV | RetroDebugger |
|---------|---------|-----------|---------|---------------|
| **Register Capture** | ✅ Frame-by-frame | ⚠️ Needs rebuild | ❌ | ✅ Real-time |
| **Audio Output** | ❌ | ❌ | ✅ WAV | ✅ Real-time |
| **Disassembly** | ❌ | ✅ Best | ❌ | ✅ Interactive |
| **Visualization** | ❌ | ❌ | ❌ | ✅ Oscilloscope |
| **Batch Processing** | ✅ Excellent | ✅ Good | ✅ Good | ⚠️ Limited |
| **API Integration** | ❌ | ❌ | ❌ | ✅ HTTP/JSON |
| **C64 Emulation** | ✅ Basic | ✅ Basic | ✅ Basic | ✅ Full |
| **Pipeline Integration** | ✅ Steps 3,1.5 | ⚠️ Steps 6,9 | ✅ Step 4 | ❌ Not yet |

---

## See Also

- `CLAUDE.md` - Quick reference and usage
- `docs/COMPONENTS_REFERENCE.md` - Python module documentation
- `docs/ARCHITECTURE.md` - System architecture details
- `docs/VALIDATION_SYSTEM.md` - Validation architecture
