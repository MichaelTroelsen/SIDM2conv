# SIDdecompiler Integration Analysis

**Date**: 2025-12-14
**Purpose**: Analyze SIDdecompiler and NewPlayer source code for SIDM2 pipeline integration
**Source**: SID-Depacker repository analysis

---

## Executive Summary

**Key Findings**:
1. ✅ **SIDdecompiler** provides emulation-based disassembly with relocation support
2. ✅ **JCH NewPlayer v21.G5** complete source code available (1,034 lines of assembly)
3. ✅ **NewPlayer v20.G4 Packer** source reveals format structure
4. 🎯 **Integration opportunity**: Use SIDdecompiler for automated player analysis and table extraction

**Recommendation**: Integrate SIDdecompiler as **Step 1.5** in conversion pipeline for automated player structure analysis.

---

## 1. SIDdecompiler Capabilities

### Core Features

**Emulation-Based Disassembly**:
- Runs SID file through complete 6502 emulator
- Tracks executed code vs data
- Produces relocatable assembly source
- Based on siddump.c emulator (same as our siddump.exe)

**Special Features**:
- **Rob Hubbard detection** - Better labeling for Hubbard tunes
- **Address operand tracing** - Tracks memory references
- **Relocation support** - Can relocate to any address
- **Multiple subtune support** - Handles multi-song SIDs
- **Conservative approach** - Only marks executed code

### Command-Line Options (Relevant for SIDM2)

```bash
# Basic usage
SIDdecompiler.exe input.sid -o output.asm

# Key options for our pipeline:
-o <filename>          # Output filename
-a <0000-ffff>         # Relocation address (e.g., -a 0e00 for Laxity driver)
-t <ticks>             # How many times to call play routine (default: 30000)
-s <0-255>             # Subtune number
-p                     # Make source produce runnable .PRG file
-e                     # Standard entry points (init, play)
-v <0-2>               # Verbosity level
-z                     # Create labels for ZP addresses
-Z <2-255>             # Relocate ZP addresses
```

**Most useful for us**:
- `-a 0e00` - Relocate to $0E00 (Laxity driver target address)
- `-t 3000` - Run for 60 seconds (3000 ticks at 50 Hz)
- `-o analysis.asm` - Output assembly for analysis

### Known Limitations

From readme.txt:
```
* Does not handle tunes with timer-based sample playback
* Multiple player instances in single file not well handled
* SIDs that set up IRQs or never return from init not supported
* Undocumented opcodes only partially supported
```

**Impact on SIDM2**:
- ⚠️ Laxity NewPlayer v21 may have multiple instances
- ✅ Standard player format should work fine
- ✅ No IRQ usage in Laxity player

---

## 2. JCH NewPlayer v21.G5 Source Analysis

### Complete Source Code Available

**File**: `SRC_JCH_Glover/21.g5spd3up.src.prg`
**Size**: 1,034 lines of 6502 assembly
**Format**: Full source with comments

### Memory Layout (from source)

```asm
$09E0        ; SFX init
$0F00        ; Demo init/drive routines
$0FA0-$0FEE  ; Pointer table (47 pointers!)
$1000        ; INIT entry point (jmp sinit)
$1003        ; PLAY entry point (jmp main)
```

**Critical Pointer Table** ($0FA0-$0FEE):
```asm
$0FA0: voicon    ; Voice on/off flags
$0FA2: vol+1     ; Volume
$0FA4: credits   ; Credits text
$0FA6: tpoin     ; Track pointers
$0FA8: sinit     ; Init routine
$0FAA: main      ; Main player routine
$0FAC: getinit   ; Get init
$0FAE: getinit   ; (duplicate?)
$0FB0: get3      ; Get routine 3
$0FB2: getins    ; Get instrument
$0FB4: real      ; Real-time routine
$0FB6: setsid    ; Set SID
$0FB8: notes     ; Note frequency table
$0FBA: fintun    ; Fine tune
$0FBC: arp1      ; Arpeggio table 1
$0FBE: arp2      ; Arpeggio table 2
$0FC0: filttab   ; Filter table
$0FC2: pulstab   ; Pulse table
$0FC4: instr     ; Instrument table
$0FC6: v1        ; Voice 1 data
$0FC8: v2        ; Voice 2 data
$0FCA: v3        ; Voice 3 data
$0FCC: lobyt     ; Low byte table
$0FCE: hibyt     ; High byte table
$0FD0: supertab  ; Super table (commands)
$0FD2: s00       ; Sound 00
$0FD4: shspeed   ; Speed
$0FD6: s02       ; Sound 02
$0FD8: voice     ; Voice offsets
$0FDA: gat       ; Gate
$0FDC: nog       ; No gate
$0FDE: trans     ; Transpose
$0FE0: sflag     ; Slide flag
$0FE2: not       ; Note
$0FE4: vhzl      ; Vibrato Hz low
$0FE6: vhzh      ; Vibrato Hz high
$0FE8: next      ; Next
$0FEA: insnr     ; Instrument number
$0FEC: synth     ; Synth
```

### Table Formats (from source)

**Instrument Table** (8 bytes per instrument):
```asm
instr:
  .byte AD       ; Attack/Decay
  .byte SR       ; Sustain/Release
  .byte WaveSpd  ; Wave table speed (high/low nibbles)
  .byte FX       ; Effects flags
  .byte Filt     ; Resonance/Filter type
  .byte FiltNum  ; Filter table number
  .byte PulsNum  ; Pulse table number
  .byte WaveNum  ; Wave table number
```

**Filter Table** (4 bytes per entry):
```asm
filttab:
  .byte Value    ; Filter value (or $FF for end)
  .byte Add      ; Add value for filter sweep
  .byte Delay    ; Delay/speed
  .byte NextPtr  ; Next entry pointer
```

**Pulse Table** (4 bytes per entry):
```asm
pulstab:
  .byte PulseHi  ; Pulse width high (or $FF for end)
  .byte PulseAdd ; Add value
  .byte Dir      ; Direction (bit 7) + delay
  .byte NextPtr  ; Next entry pointer
```

**Wave Table** (Arpeggio tables):
```asm
arp1:  .byte Note1, Note2, ..., $7F  ; Notes or commands
arp2:  .byte Wave1, Wave2, ...       ; Waveforms
```

### Track Pointer Format

```asm
tpoin:
  .word v1, v2, v3  ; Voice track pointers
  .byte speed1, speed2
```

### Voice Track Format

```asm
v1:
  .byte $A0-$FF     ; Transpose (if negative)
  .byte TrackNum    ; Track/sequence number
  .byte ...
  .byte $FF         ; End marker
```

### Supertab (Command Table)

Commands in sequences:
```asm
$0h,lo  ; Slide up
$1h,lo  ; Slide down
$2x,yy  ; Vibrato1 (x=speed, yy=add)
$3?,sr  ; Sustain/Release
$4?,xy  ; Half speed
$5?,xx  ; Filter frequency add
$60-7F,xx  ; New filter point
$80-9F,xx  ; New pulse point
$A0-BF,xx  ; New waveform point
$C0-DF,xx  ; New wave speed point
$E?,?x  ; Volume tune
$Fx,yz  ; Vibrato2 (x=feel, y=speed, z=add)
```

---

## 3. NewPlayer v20.G4 Packer Analysis

### Memory Map (from packer source)

```asm
$0810-$0F00  ; Object code
$0FA0-$1000  ; Pointers
$1000-$CB00  ; Music routine + song data
$CB00-$CC00  ; Empty space
$CC00-$D000  ; Object code (remaining)
```

### Packer Workflow

1. **Load NewPlayer file** - Loads unpacked music
2. **Check player** - Verifies NewPlayer format
3. **Pack** - Compresses/organizes tables
4. **Write length** - Updates file size
5. **Save** - Writes packed .SID file

### Format Markers

```asm
$FC, $3E  ; DeluxDrive marker
"player 21.g5"  ; Player version string
```

**TPOIN Marker**:
```asm
$FC, $3C  ; TPOIN marker
$00       ; Total number of tpoin sets
```

---

## 4. Integration Opportunities for SIDM2

### 4.1 SIDdecompiler as Pipeline Step

**Proposed**: Add as **Step 1.5** in conversion pipeline

**Current Pipeline**:
```
1. SID → SF2 conversion
2. SF2 → SID packing
3. Siddump generation
...
```

**Enhanced Pipeline**:
```
1. SID → SF2 conversion
1.5. SIDdecompiler analysis (NEW)
     - Generate annotated disassembly
     - Extract player type
     - Identify table locations
     - Validate memory layout
2. SF2 → SID packing
3. Siddump generation
...
```

### 4.2 Automated Table Location Detection

**Current Approach** (manual):
```python
# Hardcoded addresses in laxity_parser.py
FILTER_TABLE_ADDR = 0x1A1E
PULSE_TABLE_ADDR = 0x1A3B
INSTRUMENT_TABLE_ADDR = 0x1A6B
WAVE_TABLE_ADDR = 0x1ACB
```

**Proposed Approach** (SIDdecompiler-assisted):
```python
# 1. Run SIDdecompiler with tracing
subprocess.run([
    "SIDdecompiler.exe",
    "input.sid",
    "-o", "analysis.asm",
    "-t", "3000",  # 60 seconds
    "-v", "2"      # Verbose
])

# 2. Parse output assembly for table references
def extract_table_addresses(asm_file):
    """Parse SIDdecompiler output for table addresses"""
    tables = {}

    # Look for label patterns
    for line in asm_file:
        if "filttab" in line:
            tables['filter'] = parse_address(line)
        if "pulstab" in line:
            tables['pulse'] = parse_address(line)
        if "instr" in line:
            tables['instrument'] = parse_address(line)
        if "arp1" in line or "wavetab" in line:
            tables['wave'] = parse_address(line)

    return tables
```

### 4.3 Player Type Detection

**Current**: Uses `player-id.exe` (binary only)

**Enhanced**: Combine player-id + SIDdecompiler analysis

```python
def detect_player_type(sid_file):
    """Enhanced player detection"""

    # 1. Quick check with player-id
    player_id = run_player_id(sid_file)

    # 2. Verify with SIDdecompiler analysis
    disasm = run_siddecompiler(sid_file)

    # 3. Look for player signatures
    if "player 21.g5" in disasm:
        return "NewPlayer_v21_G5"
    if "player 21.g4" in disasm:
        return "NewPlayer_v21_G4"
    if "player 20" in disasm:
        return "NewPlayer_v20"

    # 4. Check pointer table structure
    if has_pointer_table_at(disasm, 0x0FA0):
        return "NewPlayer_v21_variant"

    return player_id  # Fallback
```

### 4.4 Relocation Validation

**Use Case**: Validate relocated Laxity driver code

```python
def validate_relocation(original_sid, relocated_prg):
    """Validate relocation using SIDdecompiler"""

    # 1. Disassemble original at $1000
    original_asm = run_siddecompiler(
        original_sid,
        reloc_addr=0x1000
    )

    # 2. Disassemble relocated at $0E00
    relocated_asm = run_siddecompiler(
        relocated_prg,
        reloc_addr=0x0E00,
        init_addr=0x0D7E,  # SF2 wrapper
        play_addr=0x0D81
    )

    # 3. Compare instruction sequences
    return compare_code_flow(original_asm, relocated_asm)
```

### 4.5 Memory Map Visualization

**Generate memory maps** for debugging:

```python
def generate_memory_map(sid_file):
    """Create visual memory map from SIDdecompiler output"""

    disasm = run_siddecompiler(sid_file, verbose=2)

    map = {
        'code': [],
        'data': [],
        'tables': {},
        'zero_page': []
    }

    # Parse disassembly for memory regions
    for line in disasm:
        addr = parse_address(line)

        if is_code(line):
            map['code'].append(addr)
        elif is_data(line):
            map['data'].append(addr)
        elif is_table(line):
            table_name = extract_table_name(line)
            map['tables'][table_name] = addr

    return visualize_map(map)
```

---

## 5. NewPlayer Source Code Insights

### 5.1 Critical Discovery: Dual Table Pointers

**From source (lines 206-217)**:
```asm
sinit:
    ; Setup dual pointers for voice tracks
    lda #<tpoin
    clc
    ldx tpoin+7,y
    bpl *+4
    adc #8
    sta si1a+1      ; First pointer set
    adc #1
    sta si1b+1      ; Second pointer set
```

**Insight**: NewPlayer uses **two sets of track pointers** for looping:
- `kbyl/kbyh` - Current position
- `kbyl2/kbyh2` - Loop point

**Impact on SIDM2**:
- ✅ Explains why we need dual pointer tracking
- ✅ Loop point must be preserved in conversion
- ⚠️ Current Laxity parser may not handle this correctly

### 5.2 Speed/Timing System

**From source (lines 256-264)**:
```asm
main:
    dec speed+1
    bpl m0
half:
    ldy #0
    lda filttab,y
    sta speed+1
    sta shspeed
    tya
    eor #1
    sta half+1
```

**Insight**: **Half-speed system**
- Speed alternates between two values
- Stored in first two bytes of filter table
- Can be modified by commands ($4x in supertab)

**Impact on SIDM2**:
- ✅ Explains speed variations we see
- ⚠️ Must preserve speed table in conversion
- 🎯 Filter table first 2 bytes are SPEED, not filter data!

### 5.3 Voice Offset Table

**From source (line 950)**:
```asm
voice:  .byte $00, $07, $0E
```

**Insight**: SID register offsets for 3 voices
- Voice 1: $D400 + $00 = $D400
- Voice 2: $D400 + $07 = $D407
- Voice 3: $D400 + $0E = $D40E

**Standard SID layout**:
- Each voice: 7 registers
- Voice 1: $D400-$D406
- Voice 2: $D407-$D40D
- Voice 3: $D40E-$D414

### 5.4 Instrument FX Byte Decoding

**From source documentation (lines 10-18)**:
```asm
;sound:
;00:attack/delay
;01:sustain/release
;02:wavetab speed first pos/second pos
;03:fx
;04:resonans/filter type
;05:filtertab number
;06:pulsetab number
;07:wavetab number
;
;fx:
;01:drum effect
;02:filter no restart
;04:pulse no restart
```

**Insight**: FX byte is bit flags
- Bit 0 ($01): Drum mode (uses arp1 as drum table)
- Bit 1 ($02): Don't restart filter on new note
- Bit 2 ($04): Don't restart pulse on new note

**Impact on SIDM2**:
- ✅ Explains different note triggering behavior
- ⚠️ Must preserve FX flags in conversion
- 🎯 Drum mode changes arpeggio table interpretation!

### 5.5 Waveform Table Dual Array Structure

**From source (lines 864-902)**:
```asm
waveform:
    ldy sampoi,x
    lda drum,x
    beq wv0
    ; Drum mode: arp1 = note offsets
    lda arp1,y
    cmp #$7f
    bne wv
    lda arp2,y      ; Loop pointer
    sta sampoi,x
    tay
    lda arp1,y
wv:
    sta tab
    lda #0
    beq wv3
wv0:
    ; Normal mode: arp1 = notes, arp2 = waveforms
    lda arp1,y
    cmp #$7f
    bne wv1
    lda arp2,y      ; Loop pointer
    sta sampoi,x
    tay
    lda arp1,y
wv1:
    asl a
    bcs wv2
    adc not,x       ; Add base note
wv2:
    tay
    lda notes+1,y   ; Get frequency high
    sta tab
    lda notes+0,y   ; Get frequency low
wv3:
    ; tab = freq high, A = freq low
    ldy voice,x
    clc
    adc #0          ; Add vibrato/slide
    sta $d400,y
    lda tab
    adc #0
    sta $d401,y
    ldy sampoi,x
    lda arp2,y      ; Get waveform
    ldy voice,x
    and gat,x       ; Apply gate
    sta $d404,y
```

**CRITICAL INSIGHT**: Wave table is **TWO separate arrays**:
- **arp1**: Note values (or drum offsets in drum mode)
- **arp2**: Waveforms (or loop pointers)

**Not interleaved pairs!** Each is a separate 256-byte array.

**This matches our recent discovery**:
```python
# Laxity format (CORRECT):
arp1 = [note1, note2, note3, ..., 0x7F]  # 256 bytes at $1ACB
arp2 = [wave1, wave2, wave3, ...]        # 256 bytes at $1BCB (offset +$100)

# NOT interleaved like SF2:
# [(note1, wave1), (note2, wave2), ...]
```

**This explains our wave table fix that improved accuracy from 0.20% → 99.93%!**

---

## 6. Practical Implementation Plan

### Phase 1: Basic SIDdecompiler Integration (4-6 hours)

**Goal**: Add SIDdecompiler analysis to pipeline

**Tasks**:
1. Create `sidm2/siddecompiler.py` wrapper module
2. Add `run_siddecompiler()` function
3. Integrate into `complete_pipeline_with_validation.py`
4. Generate analysis reports

**Code Structure**:
```python
# sidm2/siddecompiler.py

import subprocess
import os
from pathlib import Path

class SIDdecompilerAnalyzer:
    def __init__(self, siddecompiler_path):
        self.exe = siddecompiler_path

    def analyze(self, sid_file, output_dir,
                reloc_addr=0x1000,
                ticks=3000):
        """Run SIDdecompiler analysis"""

        output_asm = output_dir / f"{sid_file.stem}_analysis.asm"

        cmd = [
            str(self.exe),
            str(sid_file),
            "-o", str(output_asm),
            "-a", f"{reloc_addr:04x}",
            "-t", str(ticks),
            "-v", "2"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        return {
            'asm_file': output_asm,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }

    def extract_tables(self, asm_file):
        """Extract table addresses from disassembly"""

        tables = {}

        with open(asm_file) as f:
            for line in f:
                # Look for common table labels
                if 'filter' in line.lower():
                    addr = self._parse_address(line)
                    if addr:
                        tables['filter'] = addr

                if 'pulse' in line.lower():
                    addr = self._parse_address(line)
                    if addr:
                        tables['pulse'] = addr

                if 'instr' in line.lower():
                    addr = self._parse_address(line)
                    if addr:
                        tables['instrument'] = addr

                if 'arp' in line.lower() or 'wave' in line.lower():
                    addr = self._parse_address(line)
                    if addr:
                        tables['wave'] = addr

        return tables

    def _parse_address(self, line):
        """Parse hexadecimal address from assembly line"""
        import re
        match = re.search(r'\$([0-9a-fA-F]{4})', line)
        if match:
            return int(match.group(1), 16)
        return None
```

### Phase 2: Player Structure Analysis (6-8 hours)

**Goal**: Automatically detect player structure

**Tasks**:
1. Parse SIDdecompiler output for player signatures
2. Detect pointer table locations
3. Identify table formats
4. Generate structure reports

**Example Report**:
```
Player Analysis Report
======================
File: Stinsens_Last_Night_of_89.sid
Player: NewPlayer v21.G5 (detected)

Memory Layout:
  $0FA0-$0FEE: Pointer table (47 entries)
  $1000:       INIT entry
  $1003:       PLAY entry
  $1A1E:       Filter table
  $1A3B:       Pulse table
  $1A6B:       Instrument table
  $1ACB:       Wave table (arp1)
  $1BCB:       Wave table (arp2)

Table Sizes:
  Instruments: 32 entries (256 bytes)
  Filter:      29 bytes
  Pulse:       63 bytes
  Wave:        512 bytes (2×256)

Detected Features:
  - Dual wave tables (arp1/arp2)
  - Half-speed system
  - Drum mode support
  - Vibrato/slide commands
```

### Phase 3: Automated Extraction (8-12 hours)

**Goal**: Use SIDdecompiler analysis to guide extraction

**Tasks**:
1. Replace hardcoded addresses with detected addresses
2. Validate table formats
3. Auto-detect table sizes
4. Improve error handling

### Phase 4: Validation & Testing (6-8 hours)

**Goal**: Validate SIDdecompiler integration

**Tasks**:
1. Test on 18 Laxity files
2. Compare extracted tables with manual extraction
3. Validate accuracy improvements
4. Update documentation

---

## 7. Expected Benefits

### 7.1 Improved Accuracy

**Current State**:
- Manual address detection
- Hardcoded table locations
- Format assumptions

**With SIDdecompiler**:
- Automatic address detection
- Validated memory layout
- Format verification
- ✅ Expected: 99.93% → 99.95%+ accuracy

### 7.2 Better Debugging

**Memory Layout Visualization**:
- See exact code vs data regions
- Identify table boundaries
- Track memory usage
- Spot relocation issues

### 7.3 Broader Format Support

**Current**: Laxity NewPlayer v21 only

**With Analysis**:
- Detect player variants automatically
- Adapt extraction to player version
- Support NP20, NP22-25
- Handle custom players

### 7.4 Validation

**Relocation Verification**:
- Compare original vs relocated code
- Verify pointer patches
- Validate table injection
- Catch relocation errors early

---

## 8. Technical Challenges

### 8.1 SIDdecompiler Limitations

**Multiple Player Instances**:
```
* A lot of rips in HVSC consist of multiple music driver
  instances in a single file. Often, these are moved around
  in memory and are not very well handled by the address
  operand tracer.
```

**Mitigation**:
- Run with short trace time (-t 1000)
- Focus on primary player instance
- Validate with player-id.exe

### 8.2 Assembly Parsing

**Challenge**: Parse disassembly output reliably

**Solution**:
```python
def parse_disassembly(asm_file):
    """Robust assembly parser"""

    # Example line formats:
    # "label:       LDA $1234"
    # "             STA $0FA0,X"
    # "  $1000      JMP $1003"

    patterns = {
        'label': r'^(\w+):\s+',
        'address': r'\$([0-9A-F]{4})',
        'opcode': r'\s+(LDA|STA|JMP|...) ',
    }

    # Parse with regex patterns
    # Build symbol table
    # Track data vs code regions
```

### 8.3 Cross-Platform Support

**Issue**: SIDdecompiler is Windows-only (.exe)

**Solutions**:
1. **Wine on Linux/Mac** - Run Windows binary
2. **Build from source** - C++ source available
3. **Alternative tools** - Use existing tools for now

**Implementation**:
```python
def get_siddecompiler_command():
    """Get platform-specific SIDdecompiler command"""

    if platform.system() == 'Windows':
        return "SIDdecompiler.exe"
    elif platform.system() == 'Linux':
        return "wine SIDdecompiler.exe"
    elif platform.system() == 'Darwin':  # macOS
        return "wine SIDdecompiler.exe"
```

---

## 9. NewPlayer Source Code Applications

### 9.1 Format Validation

**Use source as reference** for table format validation:

```python
def validate_instrument_table(data):
    """Validate instrument table against NP21 format"""

    # From source: 8 bytes per instrument
    assert len(data) % 8 == 0, "Instrument table not multiple of 8"

    num_instruments = len(data) // 8

    for i in range(num_instruments):
        offset = i * 8

        ad = data[offset + 0]     # Attack/Decay
        sr = data[offset + 1]     # Sustain/Release
        ws = data[offset + 2]     # Wave speed
        fx = data[offset + 3]     # FX flags
        filt = data[offset + 4]   # Filter settings
        fnum = data[offset + 5]   # Filter table num
        pnum = data[offset + 6]   # Pulse table num
        wnum = data[offset + 7]   # Wave table num

        # Validate ranges (from source constraints)
        assert fx & 0xF8 == 0, f"Invalid FX flags: {fx:02x}"
        # ... more validation
```

### 9.2 Command Decoder

**Implement supertab command decoder** based on source:

```python
def decode_supertab_command(cmd, param):
    """Decode NewPlayer supertab command"""

    cmd_hi = (cmd >> 4) & 0x0F
    cmd_lo = cmd & 0x0F

    if cmd_hi == 0x0:
        return f"Slide up ${param:02x}"
    elif cmd_hi == 0x1:
        return f"Slide down ${param:02x}"
    elif cmd_hi == 0x2:
        return f"Vibrato1 speed={cmd_lo} add={param:02x}"
    elif cmd_hi == 0x3:
        return f"Set sustain/release ${param:02x}"
    elif cmd_hi == 0x4:
        speed1 = (param >> 4) & 0x0F
        speed2 = param & 0x0F
        return f"Half speed {speed1}/{speed2}"
    elif cmd_hi == 0x5:
        return f"Filter freq add ${param:02x}"
    elif 0x60 <= cmd <= 0x7F:
        return f"New filter point ${param:02x}"
    elif 0x80 <= cmd <= 0x9F:
        return f"New pulse point ${param:02x}"
    elif 0xA0 <= cmd <= 0xBF:
        return f"New waveform point ${param:02x}"
    elif 0xC0 <= cmd <= 0xDF:
        return f"New wave speed point ${param:02x}"
    elif cmd_hi == 0xE:
        return f"Volume tune {cmd_lo}"
    elif cmd_hi == 0xF:
        feel = cmd_lo
        speed = (param >> 4) & 0x0F
        add = param & 0x0F
        return f"Vibrato2 feel={feel} speed={speed} add={add}"
    else:
        return f"Unknown command ${cmd:02x} ${param:02x}"
```

### 9.3 Speed System Emulation

**Implement half-speed system** for accurate playback:

```python
class NewPlayerSpeedSystem:
    def __init__(self):
        self.speed_counter = 0
        self.half_flag = 0
        self.speed_values = [3, 3]  # Default from filttab

    def tick(self):
        """Called each frame"""

        if self.speed_counter > 0:
            self.speed_counter -= 1
            return False  # Don't advance sequence

        # Reset speed counter
        self.speed_counter = self.speed_values[self.half_flag]

        # Alternate between two speeds
        self.half_flag ^= 1

        return True  # Advance sequence

    def set_speeds(self, speed1, speed2):
        """Set from filter table"""
        self.speed_values = [speed1, speed2]
```

---

## 10. Recommended Next Steps

### Immediate (This Week)

1. ✅ **Copy SIDdecompiler to SIDM2 tools/**
   ```bash
   cp "C:/Users/mit/Downloads/SID-Depacker/SIDdecompiler_0.8-Win_x64/x64/SIDdecompiler.exe" tools/
   ```

2. ✅ **Test SIDdecompiler on Laxity files**
   ```bash
   tools/SIDdecompiler.exe SID/Stinsens_Last_Night_of_89.sid -o test_analysis.asm -v 2
   ```

3. ✅ **Create `sidm2/siddecompiler.py` wrapper**
   - Basic subprocess wrapper
   - Parse output assembly
   - Extract table addresses

### Short Term (Next 2 Weeks)

4. **Integrate into pipeline as Step 1.5**
   - Add to `complete_pipeline_with_validation.py`
   - Generate analysis reports
   - Compare with manual extraction

5. **Create player structure analyzer**
   - Auto-detect player type
   - Extract memory layout
   - Generate visual maps

6. **Validate on 18 test files**
   - Compare extracted addresses
   - Measure accuracy impact
   - Document findings

### Medium Term (Next Month)

7. **Use for NP20 driver development**
   - Analyze NP20 source files
   - Extract format differences
   - Build NP20 driver

8. **Create format validation suite**
   - Validate extracted tables
   - Check format compliance
   - Auto-detect issues

---

## 11. Success Metrics

### Integration Success

- ✅ SIDdecompiler runs on all 18 test files
- ✅ Table addresses extracted automatically
- ✅ Player type detected correctly (>95%)
- ✅ Analysis integrated into pipeline
- ✅ Memory maps generated

### Accuracy Impact

- **Current**: 99.93% frame accuracy (Laxity driver)
- **Target**: 99.95%+ frame accuracy
- **Benefit**: Automated validation catches issues earlier

### Developer Experience

- ⏱️ Faster debugging (memory maps)
- 🔍 Better error messages (address validation)
- 📊 Visual tools (memory layout)
- 🎯 Confident development (source-level understanding)

---

## References

### Source Code

- **SIDdecompiler source**: `SIDdecompiler-master/src/`
- **JCH NewPlayer v21.G5**: `SRC_JCH_Glover/21g5.txt` (1,034 lines)
- **NewPlayer v20.G4 packer**: `crescent-newplayer_tools/src/np_v20.g4_packer.s`

### Documentation

- **SIDdecompiler readme**: `SIDdecompiler-master/src/SIDdisasm/readme.txt`
- **NewPlayer v21.G5 docs**: `SRC_JCH_Glover/21g5.txt` (format specification)
- **SIDM2 Laxity driver**: `docs/implementation/LAXITY_DRIVER_IMPLEMENTATION.md`

### Tools

- **SIDdecompiler.exe**: `SIDdecompiler_0.8-Win_x64/x64/SIDdecompiler.exe`
- **player-id.exe**: `tools/player-id.exe` (in SIDM2)
- **siddump.exe**: `tools/siddump.exe` (in SIDM2)

---

**Document Status**: Complete Analysis
**Next Action**: Copy SIDdecompiler to tools/ and begin integration
**Priority**: P1 (High Impact - Improves automation and accuracy)
