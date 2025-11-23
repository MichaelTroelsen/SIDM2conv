# Siddump Tool Analysis

*Documentation of the siddump source code for SID register capture*

## Overview

Siddump is a command-line tool that emulates a 6502 CPU to run SID files and capture SID register writes frame-by-frame. This is critical for validating our extraction by comparing expected vs actual SID output.

**Source Files:**
- `tools/cpu.h` - CPU emulator header
- `tools/cpu.c` - Complete 6502 CPU emulator (~1200 lines)
- `tools/siddump.c` - Main program (~520 lines)

---

## Architecture

### Components

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SID File   │ ──> │ 6502 CPU    │ ──> │ SID Regs    │
│  (PSID)     │     │ Emulator    │     │ $D400-D418  │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    ┌─────┴─────┐
                    │ 64KB RAM  │
                    │ mem[0x10000] │
                    └───────────┘
```

### Memory Model

```c
unsigned char mem[0x10000];  // 64KB C64 memory
unsigned short pc;           // Program counter
unsigned char a, x, y;       // Registers
unsigned char flags;         // Status flags
unsigned char sp;            // Stack pointer
unsigned int cpucycles;      // Cycle counter
```

---

## CPU Emulator (cpu.c)

### Status Flags

```c
#define FN 0x80    // Negative
#define FV 0x40    // Overflow
#define FB 0x10    // Break
#define FD 0x08    // Decimal
#define FI 0x04    // Interrupt disable
#define FZ 0x02    // Zero
#define FC 0x01    // Carry
```

### Addressing Modes

```c
#define IMMEDIATE()   (LO())
#define ABSOLUTE()    (LO() | (HI() << 8))
#define ABSOLUTEX()   (((LO() | (HI() << 8)) + x) & 0xffff)
#define ABSOLUTEY()   (((LO() | (HI() << 8)) + y) & 0xffff)
#define ZEROPAGE()    (LO() & 0xff)
#define ZEROPAGEX()   ((LO() + x) & 0xff)
#define ZEROPAGEY()   ((LO() + y) & 0xff)
#define INDIRECTX()   (MEM((LO() + x) & 0xff) | (MEM((LO() + x + 1) & 0xff) << 8))
#define INDIRECTY()   (((MEM(LO()) | (MEM((LO() + 1) & 0xff) << 8)) + y) & 0xffff)
```

### Key Operations

**Arithmetic:**
- `ADC` - Add with carry (includes decimal mode)
- `SBC` - Subtract with carry
- `CMP`, `CPX`, `CPY` - Compare

**Logical:**
- `AND`, `ORA`, `EOR` - Bitwise operations
- `ASL`, `LSR`, `ROL`, `ROR` - Shifts and rotates

**Memory:**
- `LDA`, `LDX`, `LDY` - Load
- `STA`, `STX`, `STY` - Store
- `INC`, `DEC` - Increment/decrement

**Control:**
- `JMP`, `JSR`, `RTS`, `RTI` - Jump/call/return
- `BCC`, `BCS`, `BEQ`, `BNE`, `BMI`, `BPL`, `BVC`, `BVS` - Branches

### Cycle Counting

```c
static const int cpucycles_table[] = {
  7,  6,  0,  8,  3,  3,  5,  5,  3,  2,  2,  2,  4,  4,  6,  6,
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7,
  // ... 256 entries for each opcode
};
```

Used for profiling and rastertime calculation.

### Illegal Opcodes

Limited support for some illegal opcodes:
- `$A7`, `$B7`, `$AF`, `$A3`, `$B3` - LAX variants
- NOPs: `$1A`, `$3A`, `$5A`, `$7A`, `$DA`, `$FA`
- SKB (skip byte): `$80`, `$82`, `$89`, `$C2`, `$E2`, etc.
- SKW (skip word): `$0C`, `$1C`, `$3C`, `$5C`, `$7C`, `$DC`, `$FC`

---

## Siddump Main Program (siddump.c)

### Data Structures

```c
typedef struct {
  unsigned short freq;   // Frequency value ($D400/$D401)
  unsigned short pulse;  // Pulse width ($D402/$D403)
  unsigned short adsr;   // ADSR ($D405/$D406)
  unsigned char wave;    // Waveform ($D404)
  int note;              // Detected note (0-95)
} CHANNEL;

typedef struct {
  unsigned short cutoff; // Filter cutoff ($D415/$D416)
  unsigned char ctrl;    // Resonance/routing ($D417)
  unsigned char type;    // Filter type/volume ($D418)
} FILTER;

CHANNEL chn[3];          // Current frame
CHANNEL prevchn[3];      // Previous frame
CHANNEL prevchn2[3];     // Frame before that
FILTER filt;
FILTER prevfilt;
```

### Frequency Tables

PAL frequency values for notes C-0 to B-7:

```c
unsigned char freqtbllo[] = {
  0x17,0x27,0x39,0x4b,0x5f,0x74,0x8a,0xa1,0xba,0xd4,0xf0,0x0e,  // C-0 to B-0
  0x2d,0x4e,0x71,0x96,0xbe,0xe8,0x14,0x43,0x74,0xa9,0xe1,0x1c,  // C-1 to B-1
  0x5a,0x9c,0xe2,0x2d,0x7c,0xcf,0x28,0x85,0xe8,0x52,0xc1,0x37,  // C-2 to B-2
  0xb4,0x39,0xc5,0x5a,0xf7,0x9e,0x4f,0x0a,0xd1,0xa3,0x82,0x6e,  // C-3 to B-3
  0x68,0x71,0x8a,0xb3,0xee,0x3c,0x9e,0x15,0xa2,0x46,0x04,0xdc,  // C-4 to B-4
  0xd0,0xe2,0x14,0x67,0xdd,0x79,0x3c,0x29,0x44,0x8d,0x08,0xb8,  // C-5 to B-5
  0xa1,0xc5,0x28,0xcd,0xba,0xf1,0x78,0x53,0x87,0x1a,0x10,0x71,  // C-6 to B-6
  0x42,0x89,0x4f,0x9b,0x74,0xe2,0xf0,0xa6,0x0e,0x33,0x20,0xff   // C-7 to B-7
};

unsigned char freqtblhi[] = {
  0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x02,  // Octave 0
  0x02,0x02,0x02,0x02,0x02,0x02,0x03,0x03,0x03,0x03,0x03,0x04,  // Octave 1
  // ... continues to octave 7
};
```

### Execution Flow

```c
int main(int argc, char **argv) {
    // 1. Parse command line arguments
    // 2. Open and read SID file header
    // 3. Load C64 data into mem[]

    // 4. Run init routine
    mem[0x01] = 0x37;  // Set memory configuration
    initcpu(initaddress, subtune, 0, 0);
    while (runcpu()) {
        // Handle raster counter for timing loops
        ++mem[0xd012];
        if (instr > MAX_INSTR) break;
    }

    // 5. Main playback loop (50 frames/second)
    while (frames < seconds * 50) {
        // Run play routine
        initcpu(playaddress, 0, 0, 0);
        while (runcpu()) {
            if (instr > MAX_INSTR) break;
            // Check for Kernal exit
            if (pc == 0xea31 || pc == 0xea81) break;
        }

        // 6. Capture SID registers
        for (c = 0; c < 3; c++) {
            chn[c].freq = mem[0xd400 + 7*c] | (mem[0xd401 + 7*c] << 8);
            chn[c].pulse = mem[0xd402 + 7*c] | (mem[0xd403 + 7*c] << 8);
            chn[c].wave = mem[0xd404 + 7*c];
            chn[c].adsr = mem[0xd406 + 7*c] | (mem[0xd405 + 7*c] << 8);
        }
        filt.cutoff = (mem[0xd415] << 5) | (mem[0xd416] << 8);
        filt.ctrl = mem[0xd417];
        filt.type = mem[0xd418];

        // 7. Convert frequency to note
        // 8. Format and print output

        frames++;
    }
}
```

### Note Detection Algorithm

```c
// Find closest matching note
for (d = 0; d < 96; d++) {
    int cmpfreq = freqtbllo[d] | (freqtblhi[d] << 8);
    int freq = chn[c].freq;

    if (abs(freq - cmpfreq) < dist) {
        dist = abs(freq - cmpfreq);
        // Favor the old note (helps with vibrato)
        if (d == prevchn[c].note) dist /= oldnotefactor;
        chn[c].note = d;
    }
}
```

---

## Output Format

### Header Line

```
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
```

### Column Descriptions

**Per Voice (×3):**

| Column | Width | Description |
|--------|-------|-------------|
| Freq | 4 hex | 16-bit frequency value |
| Note | 3 char | Note name (C-0 to B-7) |
| Abs | 2 hex | Absolute note value ($80-$DF) |
| WF | 2 hex | Waveform byte |
| ADSR | 4 hex | Attack/Decay + Sustain/Release |
| Pul | 3 hex | Pulse width (12-bit) |

**Filter:**

| Column | Width | Description |
|--------|-------|-------------|
| FCut | 4 hex | Filter cutoff |
| RC | 2 hex | Resonance/routing |
| Typ | 3 char | Filter type (Off/Low/Bnd/Hi/etc) |
| V | 1 hex | Master volume |

### Example Output

```
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
+-------+---------------------------+---------------------------+---------------------------+---------------+
|     0 | 0000  ... ..  00 0000 000 | 0000  ... ..  00 0000 000 | 0000  ... ..  00 0000 000 | 0000 00 Off 0 |
|     1 | 1CD6  C-4 B0  41 09F0 800 | 0000  ... ..  00 0000 000 | 0E6B  C-3 A4  21 08A0 000 | 0400 8F Low F |
|     2 | 1CD6  ... ..  41 .... ... | 0000  ... ..  .. .... ... | 0E6B  ... ..  21 .... ... | .... .. ... . |
|     3 | 1CD6  ... ..  41 .... ... | 08A0  A-2 99  41 09F0 800 | 0E6B  ... ..  21 .... ... | .... .. ... . |
```

**Legend:**
- `....` = Same as previous frame
- `...` = No note/data

### Special Notations

```
 C-4 B0   = New note triggered (note name + absolute value)
(C-4 B0)  = Note changed without gate trigger
(+ 0008)  = Frequency increased (slide up)
(- 0010)  = Frequency decreased (slide down)
 ... ..   = No change / rest
```

---

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-a<n>` | Subtune number | 0 |
| `-t<n>` | Playback seconds | 60 |
| `-f<n>` | First frame to display | 0 |
| `-n<n>` | Note spacing (rows between notes) | 0 |
| `-p<n>` | Pattern spacing | 0 |
| `-l` | Low-resolution mode | Off |
| `-c<hex>` | Frequency calibration | PAL |
| `-d<hex>` | Calibration note | $B0 (C-4) |
| `-o<n>` | Old note factor (vibrato) | 1 |
| `-s` | Time in MM:SS.FF format | Frames |
| `-z` | Show CPU cycles/rastertime | Off |

### Usage Examples

```bash
# Basic dump
siddump Angular.sid

# First 30 seconds, subtune 1
siddump Angular.sid -a1 -t30

# With note spacing
siddump Angular.sid -n4 -p16

# Show timing info
siddump Angular.sid -z -s
```

---

## Using Siddump for Validation

### Validating ADSR Extraction

Compare extracted instrument ADSR with siddump output:

1. Note when instrument triggers in siddump (gate on)
2. Check ADSR column value
3. Compare with extracted instrument table

```python
# Example validation
def validate_adsr(siddump_adsr, extracted_instrument):
    expected_ad = extracted_instrument[0]
    expected_sr = extracted_instrument[1]
    expected = (expected_ad << 8) | expected_sr
    return siddump_adsr == expected
```

### Validating Waveform Sequences

Track waveform changes to validate wave table:

```
Frame  WF
  1    09    ; Oscillator reset
  2    41    ; Pulse + gate
  3    41    ; Still pulse
  4    21    ; Changed to saw
```

Compare with wave table entry sequence.

### Validating Note Timing

Check that notes occur at expected frames based on speed:

```python
# If speed = 4, notes should occur every 4 frames
speed = 4
expected_frames = [0, 4, 8, 12, ...]  # etc
```

### Frequency Slide Detection

Siddump shows slides as frequency deltas:

```
|  10 | 1CD6  C-4 B0  41 09F0 800 |  ; Note start
|  11 | 1CE0 (+ 000A) 41 .... ... |  ; Sliding up
|  12 | 1CEA (+ 000A) 41 .... ... |  ; Still sliding
```

This validates slide command extraction.

---

## Integration with Converter

### Python Parsing

```python
def parse_siddump_line(line):
    """Parse a single siddump output line."""
    if not line.startswith('|'):
        return None

    parts = line.split('|')
    if len(parts) < 6:
        return None

    frame = int(parts[1].strip())
    voices = []

    for i in range(3):
        voice_str = parts[2 + i].strip()
        # Parse: "FREQ Note Ab WF ADSR Pul"
        tokens = voice_str.split()
        if len(tokens) >= 6:
            voices.append({
                'freq': int(tokens[0], 16),
                'note': tokens[1],
                'waveform': int(tokens[3], 16),
                'adsr': int(tokens[4], 16),
                'pulse': int(tokens[5], 16)
            })

    filter_str = parts[5].strip().split()
    filter_info = {
        'cutoff': int(filter_str[0], 16),
        'control': int(filter_str[1], 16),
        'type': filter_str[2],
        'volume': int(filter_str[3], 16)
    }

    return {
        'frame': frame,
        'voices': voices,
        'filter': filter_info
    }
```

### Validation Workflow

1. **Run siddump** on original SID file
2. **Extract tables** using converter
3. **Compare** extracted ADSR/wave/pulse with siddump
4. **Report discrepancies** for debugging

---

## Limitations

### CPU Emulation

- Limited illegal opcode support
- No CIA/VIC timing (only basic $D012 raster)
- No interrupts (init/play called directly)

### SID Emulation

- Register capture only (no audio synthesis)
- No read-back of SID registers
- Voice3 OSC/ENV not emulated

### Accuracy

- Note detection uses simple nearest-frequency
- Vibrato may cause note flicker
- Multi-speed tunes may not capture all writes

---

## Building from Source

```bash
# Compile
gcc -o siddump siddump.c cpu.c -lm

# Or with optimization
gcc -O2 -o siddump siddump.c cpu.c -lm
```

---

## References

- [SID Registers](sid-registers.md)
- [Laxity Player Analysis](LAXITY_PLAYER_ANALYSIS.md)
- [Format Specification](format-specification.md)
