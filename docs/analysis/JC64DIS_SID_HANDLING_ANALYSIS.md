# JC64dis SID File Handling - Complete Technical Analysis

**Document Version**: 1.0.0
**Date**: 2025-12-24
**Status**: Comprehensive Analysis Complete
**Repository**: https://github.com/ice00/jc64
**Purpose**: Integration guidance for SIDM2 conversion pipeline

---

## Executive Summary

This document provides a complete technical analysis of **JC64dis SID file handling capabilities** based on comprehensive source code exploration of the JC64 repository. JC64 is a Java-based Commodore 64 emulator and disassembler with sophisticated SID music file analysis features.

**Key Findings**:
- ✅ Comprehensive PSID/RSID/MUS format support with full header parsing
- ✅ Advanced player detection (SIDId V1.09 algorithm with 80+ signatures)
- ✅ Sophisticated frequency table recognition (12 format variants)
- ✅ Full SID chip emulation (6581/8580) with ADSR and filter
- ✅ Code vs data separation with block-based memory management
- ✅ 8 assembler output formats (ACME, KickAssembler, CA65, etc.)

**Integration Value for SIDM2**: HIGH
- Player auto-detection can identify Laxity and other formats
- Frequency table validation for SF2 output verification
- Memory usage analysis for better driver understanding
- Cross-platform Java implementation (no Wine needed)
- Independent validation reference for conversion accuracy

---

## Table of Contents

1. [SID File Format Handling](#1-sid-file-format-handling)
2. [Disassembly Capabilities](#2-disassembly-capabilities)
3. [SID Register Analysis & Emulation](#3-sid-register-analysis--emulation)
4. [Output Formats & Assemblers](#4-output-formats--assemblers)
5. [Configuration & Customization](#5-configuration--customization)
6. [Integration Points & API](#6-integration-points--api)
7. [SIDM2 Integration Strategies](#7-sidm2-integration-strategies)
8. [Code Examples & Python Ports](#8-code-examples--python-ports)
9. [Recommendations & Next Steps](#9-recommendations--next-steps)

---

## 1. SID File Format Handling

### 1.1 File Format Detection

**Primary Class**: `sw_emulator.software.FileDasm`
**Location**: `src/sw_emulator/software/FileDasm.java`

#### PSID/RSID Detection Method

```java
boolean isPSID()
```

**Detection Logic**:
1. **Magic Bytes Validation** (bytes 0-3):
   - Checks for "PSID" or "RSID" signature
   - ASCII comparison without case sensitivity

2. **Version Validation** (bytes 4-5):
   - Supports versions 1 and 2
   - Rejects unknown versions

3. **Data Offset Verification**:
   - Version 1: Expects 0x76 bytes header
   - Version 2: Expects 0x7C bytes header
   - Validates header size matches version

4. **Little-Endian Parsing**:
   - All multi-byte values use little-endian format
   - Conversion: `value = lowByte + (highByte * 256)`

#### Metadata Extraction

**Addresses** (16-bit little-endian):
```java
// Bytes 8-9: Load address
psidLAddr = Unsigned.done(inB[9]) + Unsigned.done(inB[8]) * 256

// Bytes 10-11: Init routine address
psidIAddr = (inB[11] << 8) | inB[10]

// Bytes 12-13: Play routine address
psidPAddr = (inB[13] << 8) | inB[12]
```

**Song Information**:
```java
// Bytes 14-15: Number of songs
songCount = (inB[14] << 8) | inB[15]

// Bytes 16-17: Starting song number (1-based)
startSong = (inB[16] << 8) | inB[17]
```

**Text Metadata** (null-terminated ASCII):
```java
// Bytes 0x16-0x35: Title (32 bytes)
title = extractNullTerminatedString(inB, 0x16, 32)

// Bytes 0x36-0x55: Author (32 bytes)
author = extractNullTerminatedString(inB, 0x36, 32)

// Bytes 0x56-0x75: Copyright/Released (32 bytes)
copyright = extractNullTerminatedString(inB, 0x56, 32)
```

### 1.2 Enhanced PSID Parsing

**Advanced Class**: `sw_emulator.software.sidid.PSID`
**Location**: `src/sw_emulator/software/sidid/PSID.java`

#### Extended Format Support

**PSID Versions**:
- **v1** (0x01): Original format, $76 bytes header
- **v2** (0x02): Extended format, $7C bytes header
- **v3** (0x03): Enhanced metadata
- **v4** (0x04): Advanced features
- **WebSID** (0x4E): Multi-SID support (up to 4 chips)

**Multi-SID Capabilities**:
```java
// WebSID format header extension
if (version == 0x4E) {  // 'N' character
    int sidCount = readByte(0x7E);  // Number of SID chips (1-4)

    for (int i = 0; i < sidCount; i++) {
        int sidAddress = readWord(0x7E + 2 + i*2);
        // SID chip base addresses: 0xD400, 0xD500, 0xDE00, 0xDF00
    }
}
```

#### Additional Metadata Fields

**SID Model Specifications** (byte 0x77):
```java
int modelFormatStandard = inB[0x77];

// Bit 0-1: SID model for voice 1-3
// 0 = Unknown, 1 = 6581, 2 = 8580, 3 = Both
int sidModel = (modelFormatStandard >> 4) & 0x03;

// Bit 2: Video standard (0=PAL, 1=NTSC)
boolean isNTSC = (modelFormatStandard & 0x04) != 0;

// Bit 3: PSID specific (reserved)
// Bit 4-5: SID model
// Bit 6-7: Reserved
```

**Real SID Mode** (RSID vs PSID):
```java
boolean isRSID = magic.equals("RSID");

// RSID implications:
// - Requires C64 reset initialization
// - Cannot use BASIC or KERNAL ROM
// - Must honor interrupt timing
// - Player uses actual hardware initialization
```

**DigiMode Flag**:
```java
boolean hasDigi = (modelFormatStandard & 0x02) != 0;
// Indicates use of 4-bit samples via volume register
```

### 1.3 MUS/STR Format Detection

**Method**: `boolean isMUS()`

**Detection Strategy** (no magic bytes):

1. **Structural Validation**:
   ```java
   // Extract voice lengths from first 8 bytes
   int v1Length = readWord(0) + 1;
   int v2Length = readWord(2) + 1;
   int v3Length = readWord(4) + 1;

   // Calculate voice positions
   int v1Start = 8;
   int v2Start = v1Start + v1Length;
   int v3Start = v2Start + v2Length;
   ```

2. **Terminator Pattern Validation**:
   ```java
   // Each voice must end with [0x01, 0x4F]
   boolean v1Valid = (inB[v1Start + v1Length - 2] == 0x01) &&
                     (inB[v1Start + v1Length - 1] == 0x4F);

   boolean v2Valid = (inB[v2Start + v2Length - 2] == 0x01) &&
                     (inB[v2Start + v2Length - 1] == 0x4F);

   boolean v3Valid = (inB[v3Start + v3Length - 2] == 0x01) &&
                     (inB[v3Start + v3Length - 1] == 0x4F);

   return v1Valid && v2Valid && v3Valid;
   ```

3. **Length-Based Offset Calculation**:
   - Dynamically determines voice boundaries
   - Validates total file size consistency
   - Ensures no overlap between voice sections

### 1.4 PRG Format (Default Fallback)

**Detection**: If not PSID/RSID and not MUS, treat as PRG

**Processing**:
```java
// First 2 bytes: Load address (little-endian)
int loadAddress = inB[0] | (inB[1] << 8);

// Remaining bytes: Machine code
byte[] machineCode = Arrays.copyOfRange(inB, 2, inB.length);
```

**Assumptions**:
- Raw 6502 machine code
- No header metadata
- User must specify entry points manually

---

## 2. Disassembly Capabilities

### 2.1 Code vs Data Separation

**Core Class**: `sw_emulator.software.Disassembly`
**Memory Tracking**: `sw_emulator.software.MemoryDasm`

#### Block-Based Memory Management

**Block Object Structure**:
```java
class Block {
    int startAddress;           // Block start ($0000-$FFFF)
    int endAddress;             // Block end (inclusive)
    boolean isCode;             // True if executable code
    boolean isData;             // True if data
    String label;               // User-defined label
    String comment;             // Block description
}
```

**Memory Marking System**:
```java
void markInside(int start, int end) {
    for (int i = start; i <= end; i++) {
        memory[i].isInside = true;  // Processed flag
    }
}
```

**Block Merging** (option: `mergeBlocks`):
```java
// Combines adjacent or overlapping blocks
Block merged = mergeAdjacentBlocks(block1, block2);

// Example:
// Block1: $1000-$10FF (code)
// Block2: $1100-$11FF (code)
// Merged: $1000-$11FF (code)
```

**Relocate Blocks**:
```java
// External Relocate objects define additional code sections
class Relocate {
    int sourceAddress;
    int targetAddress;
    int length;
}

// Applied during disassembly to track relocated code
```

#### Memory Classification System

**MemoryDasm Structure** (per address $0000-$FFFF):
```java
class MemoryDasm {
    byte copy;                      // Actual byte value

    // Classification flags
    boolean isCode;                 // Executable instruction
    boolean isData;                 // Data byte
    boolean isGarbage;              // Unused/filler
    boolean isInside;               // Processing flag

    // Annotation system (dual-layer)
    String comment;                 // Auto-generated comment
    String userComment;             // User override

    // Cross-reference tracking
    ArrayList<Integer> related;     // Referenced addresses

    // Type system
    DataType dataType;              // Byte/Word/Text/Sprite/etc.
    BasicType basicType;            // BASIC token type

    // Methods
    MemoryDasm clone();             // State snapshot
    boolean equals(Object o);       // Comparison
    int hashCode();                 // Hashing
}
```

**DataType Enumeration**:
```java
enum DataType {
    BYTE,           // Single byte
    WORD,           // 16-bit word
    TRIBYTE,        // 24-bit value
    TEXT,           // ASCII text
    PETSCII,        // PETSCII text
    SCREENCODE,     // Screen codes
    SPRITE,         // Sprite data
    CHARSET,        // Character set
    BITMAP,         // Bitmap graphics
    MUSIC           // Music data
}
```

### 2.2 Player Pattern Recognition

**Algorithm Class**: `sw_emulator.software.SidId`
**Version**: SIDId V1.09 by Cadaver (C) 2012

#### Pattern Matching Algorithm

**Pattern Token System**:
```java
static final int END = -1;      // Pattern completion marker
static final int ANY = -2;      // Wildcard (matches any byte)
static final int AND = -3;      // Logical AND (non-contiguous)
static final int NAME = -4;     // Player name identifier

// Hex values 0x00-0xFF: Exact byte matches
```

**Signature Data Structure**:
```java
class SidIdRecord {
    String name;                    // Player/engine name
    ArrayList<int[]> list;          // Multiple patterns per player

    // Example:
    // name = "Laxity NewPlayer v21"
    // list[0] = [0x78, 0xA9, 0x00, ANY, 0x8D, END]
    // list[1] = [0xA2, 0x00, ANY, ANY, 0x9D, AND, 0x4C, END]
}

// Main storage
ArrayList<SidIdRecord> sidIdList;   // All registered players
String lastPlayers;                 // Cached identification
```

#### Matching Process with Backtracking

**Algorithm Flow**:
```java
boolean matchPattern(byte[] buffer, int[] pattern) {
    int bufPos = 0;
    int patPos = 0;
    int lastBuf = 0;
    int lastPat = 0;

    while (patPos < pattern.length) {
        int token = pattern[patPos];

        if (token == END) {
            return true;                // Pattern matched
        }
        else if (token == AND) {
            // Non-contiguous: reset to last position
            bufPos = lastBuf;
            patPos++;
        }
        else if (token == ANY) {
            // Wildcard: match any byte
            bufPos++;
            patPos++;
        }
        else if (token >= 0x00 && token <= 0xFF) {
            // Exact match required
            if (bufPos >= buffer.length || buffer[bufPos] != token) {
                return false;           // Mismatch
            }
            bufPos++;
            patPos++;
        }

        // Save backtrack position
        lastBuf = bufPos;
        lastPat = patPos;
    }

    return false;
}
```

**Configuration Loading**:
```java
void readConfig(String configFile) {
    // Parse space-separated tokens from file
    // Example config line:
    // "Laxity 78 A9 00 8D ANY ANY 8D 01 D4 END"

    String[] tokens = line.split("\\s+");
    String playerName = null;
    ArrayList<Integer> pattern = new ArrayList<>();

    for (String token : tokens) {
        if (token.equals("END")) {
            // Store pattern
            if (playerName != null) {
                addPattern(playerName, pattern);
            }
            pattern.clear();
        }
        else if (token.equals("ANY")) {
            pattern.add(ANY);
        }
        else if (token.equals("AND")) {
            pattern.add(AND);
        }
        else if (token.matches("[0-9A-Fa-f]{2}")) {
            // Hex byte
            pattern.add(Integer.parseInt(token, 16));
        }
        else {
            // Player name
            playerName = token;
        }
    }
}
```

**Known Players** (80+ signatures):
- Laxity NewPlayer v21
- JCH NewPlayer
- Maniacs of Noise
- Galway Music System
- DMC sound system
- Future Composer
- SoundMonitor
- And many more...

### 2.3 Music Data Extraction

**MUS File Disassembly**:
```java
void disassemblyMUS() {
    // Extract voice data pointers from header
    int v1Length = readWord(0) + 1;
    int v2Length = readWord(2) + 1;
    int v3Length = readWord(4) + 1;

    int ind1 = 8;                       // Voice 1 start
    int ind2 = ind1 + v1Length;         // Voice 2 start
    int ind3 = ind2 + v2Length;         // Voice 3 start

    // Use C64MusDasm to disassemble each voice
    C64MusDasm.disassemble(buffer, ind1, v1Length, "VOICE1");
    C64MusDasm.disassemble(buffer, ind2, v2Length, "VOICE2");
    C64MusDasm.disassemble(buffer, ind3, v3Length, "VOICE3");

    // Generate labeled sections in output:
    // "VOICE 1 MUSIC DATA"
    // "VOICE 2 MUSIC DATA"
    // "VOICE 3 MUSIC DATA"
}
```

**Data Structure Recognition**:
- Frequency tables (detected by SidFreq)
- Instrument definitions
- Pattern sequences
- Note data
- Effect parameters

---

## 3. SID Register Analysis & Emulation

### 3.1 Hardware SID Interface (Stub Only)

**Class**: `sw_emulator.hardware.chip.Sid`
**Location**: `src/sw_emulator/hardware/chip/Sid.java`

**Status**: ⚠️ **Skeleton implementation only**

```java
public class Sid implements powered, signaller, readableBus, writeableBus {

    @Override
    public void write(int addr, byte value) {
        switch(addr) {
            // Empty - no actual register handling
            default:
                break;
        }
    }

    // No voice/oscillator structure
    // No ADSR implementation
    // No filter implementation
}
```

**Conclusion**: The hardware SID chip class is an interface stub without functional emulation.

### 3.2 Full SID Emulation (sidid Package)

**Functional Class**: `sw_emulator.software.sidid.SID`
**Location**: `src/sw_emulator/software/sidid/SID.java`

This is the **complete working SID emulator** used for actual playback.

#### Voice and Oscillator Structure

**Three Independent Voices**:
```java
class Voice {
    // Oscillator state
    int phase;                  // 24-bit phase accumulator
    int frequency;              // 16-bit frequency register

    // Waveform selection
    boolean noiseWave;          // Noise waveform
    boolean pulseWave;          // Pulse waveform
    boolean sawtoothWave;       // Sawtooth waveform
    boolean triangleWave;       // Triangle waveform

    // Pulse width
    int pulseWidth;             // 12-bit pulse width (0-4095)

    // Modulation
    boolean ringModulation;     // Ring mod with previous voice
    boolean oscillatorSync;     // Hard sync with previous voice

    // ADSR envelope
    EnvelopeGenerator envelope;

    // Output control
    boolean gateOn;             // Gate bit
    boolean testBit;            // Test bit (freezes oscillator)
    int output;                 // Final output sample
    boolean muted;              // Mute flag
}

Voice voice1, voice2, voice3;
```

**Combined Waveforms**:
```java
int getWaveformOutput() {
    int output = 0;

    // Single waveforms
    if (noiseWave && !pulseWave && !sawtoothWave && !triangleWave) {
        output = getNoiseOutput();
    }
    else if (pulseWave && !noiseWave && !sawtoothWave && !triangleWave) {
        output = getPulseOutput();
    }
    else if (sawtoothWave && !noiseWave && !pulseWave && !triangleWave) {
        output = getSawtoothOutput();
    }
    else if (triangleWave && !noiseWave && !pulseWave && !sawtoothWave) {
        output = getTriangleOutput();
    }
    // Combined waveforms (pulse+saw+tri combinations)
    else if (pulseWave && sawtoothWave) {
        output = (getPulseOutput() & getSawtoothOutput());
    }
    else if (pulseWave && triangleWave) {
        output = (getPulseOutput() & getTriangleOutput());
    }
    // ... additional combinations

    return output;
}
```

#### ADSR Envelope Generator

**Lookup Tables** (model-specific):
```java
// 6581 chip
static final int[] ADSRprescalePeriods_6581 = {
    9, 32, 63, 95, 149, 220, 267, 313,
    392, 977, 1954, 3126, 3906, 11720, 19532, 31251
};

static final int[] ADSRexponentPeriods_6581 = {
    1, 30, 30, 30, 30, 30, 16, 16,
    16, 8, 8, 8, 4, 4, 2, 1
};

// 8580 chip
static final int[] ADSRprescalePeriods_8580 = {
    9, 32, 63, 95, 149, 220, 267, 313,
    392, 977, 1954, 3126, 3907, 11720, 19532, 31251
};

static final int[] ADSRexponentPeriods_8580 = {
    1, 30, 30, 30, 30, 30, 16, 16,
    16, 8, 8, 8, 4, 4, 2, 1
};
```

**Envelope State Machine**:
```java
enum EnvelopePhase {
    ATTACK,
    DECAY_SUSTAIN,
    RELEASE
}

void updateEnvelope() {
    switch (phase) {
        case ATTACK:
            envelopeLevel += attackIncrement;
            if (envelopeLevel >= 0xFF) {
                envelopeLevel = 0xFF;
                phase = DECAY_SUSTAIN;
            }
            break;

        case DECAY_SUSTAIN:
            if (envelopeLevel > sustainLevel) {
                envelopeLevel -= decayDecrement;
            }
            break;

        case RELEASE:
            envelopeLevel -= releaseDecrement;
            if (envelopeLevel < 0) {
                envelopeLevel = 0;
            }
            break;
    }
}
```

#### Filter Implementation

**State-Variable Filter**:
```java
class Filter {
    // Filter type selection
    boolean lowPass;            // Low-pass filter
    boolean bandPass;           // Band-pass filter
    boolean highPass;           // High-pass filter

    // Filter parameters
    int cutoffFrequency;        // 11-bit cutoff (0-2047)
    int resonance;              // 4-bit resonance (0-15)

    // Voice routing
    boolean filterVoice1;       // Route voice 1 to filter
    boolean filterVoice2;       // Route voice 2 to filter
    boolean filterVoice3;       // Route voice 3 to filter
    boolean filterExtIn;        // Route external input to filter

    // Internal state
    int bandPassOutput;         // Band-pass integrator
    int lowPassOutput;          // Low-pass integrator
}
```

**Cutoff Frequency Tables** (44100Hz sample rate):
```java
// 8580 chip cutoff multipliers
static final double[] CutoffMul8580_44100Hz = {
    // 2048 values, frequency-dependent
    0.0, 0.0012, 0.0024, 0.0036, ..., 1.0
};

// 6581 chip cutoff multipliers
static final double[] CutoffMul6581_44100Hz = {
    // 2048 values, frequency-dependent
    0.0, 0.0015, 0.0030, 0.0045, ..., 1.0
};
```

**Resonance Tables**:
```java
// 6581 resonance values (0-15)
static final double[] Resonances6581 = {
    0.5, 0.65, 0.75, 0.82, 0.87, 0.91, 0.94, 0.96,
    0.97, 0.98, 0.985, 0.99, 0.993, 0.995, 0.997, 1.0
};

// 8580 resonance values (0-15)
static final double[] Resonances8580 = {
    0.5, 0.60, 0.70, 0.78, 0.84, 0.88, 0.91, 0.93,
    0.95, 0.96, 0.97, 0.98, 0.985, 0.99, 0.995, 1.0
};
```

**6581 Special: MOSFET-VCR Control Voltage**:
```java
// MOSFET voltage-controlled resistor for filter distortion
double getControlVoltage(int cutoff, int resonance) {
    // Simulates non-linear MOSFET behavior in 6581 filter
    double vcr = Math.pow(2.0, (cutoff / 2048.0) * 11.0);
    vcr *= (1.0 + (resonance / 15.0) * 0.5);
    return vcr;
}
```

#### Register Mapping

**SID Base Addresses**:
```java
// Standard addresses
int SID1_BASE = 0xD400;         // Primary SID chip
int SID2_BASE = 0xD500;         // Secondary SID (if present)
int SID3_BASE = 0xDE00;         // Tertiary SID (if present)
int SID4_BASE = 0xDF00;         // Quaternary SID (if present)

// Address range: 0xD400-0xD7FF or 0xDE00-0xDFE0
// Collision avoidance: Prevents Color-RAM conflicts
```

**Register Map** (per SID chip):
```java
// Voice 1 (0xD400-0xD406)
0xD400-0xD401: Frequency (16-bit)
0xD402-0xD403: Pulse width (12-bit)
0xD404:        Control register
0xD405:        Attack/Decay
0xD406:        Sustain/Release

// Voice 2 (0xD407-0xD40D) - same structure
// Voice 3 (0xD40E-0xD414) - same structure

// Filter (0xD415-0xD417)
0xD415:        Filter cutoff low (bits 0-2)
0xD416:        Filter cutoff high (bits 3-10)
0xD417:        Resonance + voice routing

// Volume and filter (0xD418)
0xD418:        Volume (0-15) + filter type selection
```

### 3.3 SID Register Write Tracking

**System Emulation Class**: `sw_emulator.software.sidid.C64`
**Location**: `src/sw_emulator/software/sidid/C64.java`

#### Memory Banking System

**Memory Banks**:
```java
byte[] ramBank = new byte[0x10100];         // RAM: $0000-$FFFF
byte[] ioBankWR = new byte[0x10100];        // I/O write: $D000-$DFFF
byte[] ioBankRD = new byte[0x10100];        // I/O read: $D000-$DFFF
byte[][] romBanks = new byte[8][0x10100];   // ROM banks

// Bank selection via CPU port register ($0001)
```

**Write Tracking Mechanism**:
```java
void writeMemC64(int address, byte value) {
    // CPU port controls bank selection
    int bankBits = ramBank[0x0001] & 0x07;

    if (address < 0xD000) {
        // RAM area
        ramBank[address] = value;
    }
    else if (address >= 0xD000 && address < 0xE000) {
        // I/O or ROM area (depends on bank bits)
        if ((bankBits & 0x04) != 0) {
            // I/O visible
            if (address >= 0xD400 && address < 0xD800) {
                // SID registers (write-only tracking)
                ioBankWR[address] = value;
                sid.write(address - 0xD400, value);
            }
            else if (address >= 0xDE00 && address < 0xE000) {
                // Secondary SID or expansion
                ioBankWR[address] = value;
            }
        }
        else {
            // Character ROM visible
            romBanks[bankBits][address] = value;
        }
    }
    else {
        // KERNAL/BASIC ROM or RAM
        ramBank[address] = value;
    }
}
```

**Playback Architecture** (cycle-based):
```java
void generateSamples(int sampleCount) {
    for (int i = 0; i < sampleCount; i++) {
        // Accumulate CPU cycles per sample
        int cyclesPerSample = cpuClock / sampleRate;

        for (int c = 0; c < cyclesPerSample; c++) {
            // Execute one CPU instruction
            cpu.executeInstruction();

            // Update SID envelope every cycle
            sid.updateADSR();

            // Handle interrupts (CIA timers, VIC raster)
            if (cia1.hasIRQ() || vic.hasIRQ()) {
                cpu.handleIRQ();
            }
        }

        // Generate SID output sample
        samples[i] = sid.generateSample();
    }
}
```

**Frame Synchronization** (for PSID files):
```java
void playPSIDFrame() {
    // Call INIT routine once (if first frame)
    if (frameCount == 0) {
        cpu.setPC(psid.initAddress);
        cpu.setAccumulator(psid.startSong);
        cpu.executeUntilRTS();
    }

    // Call PLAY routine every frame (50Hz PAL or 60Hz NTSC)
    cpu.setPC(psid.playAddress);
    cpu.executeUntilRTS();

    // Generate audio samples for this frame
    int samplesPerFrame = sampleRate / frameRate;
    generateSamples(samplesPerFrame);

    frameCount++;
}
```

### 3.4 SID Frequency Analysis

**Analysis Class**: `sw_emulator.software.SidFreq`
**Location**: `src/sw_emulator/software/SidFreq.java`

#### Frequency Calculation

**SID Register to Hz Conversion**:
```java
// Formula: freq_hz = sid_value * clock_speed / 16777216
// Simplified multipliers for PAL and NTSC:

int freqNTSC = (int) Math.round(sidValue * 0.0609592795372);
int freqPAL  = (int) Math.round(sidValue * 0.0587253570557);

// SID value from 16-bit register (high + low bytes)
int sidValue = (highByte << 8) | lowByte;
```

**Example Calculation**:
```java
// A4 note (440 Hz) on PAL system
int a4_sid = 7489;  // Common A4 SID value

int a4_pal_hz = (int) Math.round(7489 * 0.0587253570557);
// Result: 440 Hz

int a4_ntsc_hz = (int) Math.round(7489 * 0.0609592795372);
// Result: 456 Hz
```

#### Note and Frequency Conversion

**Chromatic Scale Detection**:
```java
boolean isFrequencyTable(byte[] buffer, int offset) {
    // Check for "1, 1, 1" pattern (very low notes)
    if (!(buffer[offset] == 1 &&
          buffer[offset+2] == 1 &&
          buffer[offset+4] == 1)) {
        return false;
    }

    // Validate sequential increasing values
    int prevFreq = 0;
    for (int i = 0; i < 12*7; i += 2) {  // Check 7 octaves
        int freq = getWord(buffer, offset + i);
        if (freq <= prevFreq) {
            return false;
        }
        prevFreq = freq;
    }

    return true;
}
```

**Semitone Validation** (equal temperament):
```java
boolean validateSemitoneRatios(byte[] buffer, int offset) {
    final double SEMITONE_RATIO = Math.pow(2.0, 1.0/12.0);  // ≈ 1.0594631
    final double ERROR_THRESHOLD = 6.0;

    for (int i = 0; i < 12; i++) {
        int freq1 = getWord(buffer, offset + i*2);
        int freq2 = getWord(buffer, offset + (i+1)*2);

        double ratio = (double)freq2 / (double)freq1;
        double error = Math.abs(ratio - SEMITONE_RATIO);

        if (error > ERROR_THRESHOLD) {
            return false;  // Not a valid chromatic scale
        }
    }

    return true;
}
```

**Octave Scanning**:
```java
int detectOctaveCount(byte[] buffer, int offset) {
    int octaves = 0;

    for (int oct = 0; oct < 10; oct++) {  // Max 10 octaves
        int baseNote = getWord(buffer, offset + oct*12*2);
        int topNote = getWord(buffer, offset + (oct*12 + 11)*2);

        // Check for 2:1 octave ratio
        double ratio = (double)topNote / (double)baseNote;
        if (ratio >= 1.8 && ratio <= 2.2) {
            octaves++;
        }
        else {
            break;  // No more valid octaves
        }
    }

    return octaves;
}
```

**Reference Tuning** (A4 calibration):
```java
final int A4_INDEX = 57;  // A4 note at index 57

int calculateA4Frequency(byte[] buffer, int offset) {
    int a4_sid = getWord(buffer, offset + A4_INDEX * 2);

    int a4_ntsc_hz = (int) Math.round(a4_sid * 0.0609592795372);
    int a4_pal_hz  = (int) Math.round(a4_sid * 0.0587253570557);

    return a4_pal_hz;  // Default to PAL
}
```

#### Frequency Table Recognition

**Supported Table Types**:
```java
enum FrequencyTableType {
    LINEAR,                 // Standard linear table (90 notes)
    LINEAR_OCT_NOTE,        // Octave + note format
    SCALE,                  // Note-only (C,D,E,F,G,A,B per octave)
    SCALE_OCT_NOTE,         // Octave + note scale
    INVERSE,                // Inverted frequency values
    INVERSE_OCT_NOTE,       // Inverted octave + note
    COMBINED,               // Combined high/low tables
    COMBINED_OCT_NOTE,      // Combined octave + note
    COMBINED_INVERSE,       // Combined inverted
    COMBINED_INVERSE_OCT_NOTE,  // Combined inverted octave + note
    SHORT,                  // Shortened table (72 notes)
    SHORT2                  // Alternative short (65 notes)
}
```

**Known Formats**:
1. **Mastercomposer Format**:
   ```
   90 notes, linear layout
   Low bytes: $0000-$0059
   High bytes: $005A-$00B3
   ```

2. **Soundtracker Format**:
   ```
   Octave/note separation
   12 notes × 7 octaves = 84 entries
   Octave table separate from note table
   ```

3. **Short Tables**:
   ```
   72 notes: 6 octaves (C0-B5)
   65 notes: 5 octaves + extras
   ```

**Table Detection Algorithm**:
```java
FrequencyTableType detectTableType(byte[] buffer, int offset) {
    int tableSize = measureTableSize(buffer, offset);
    boolean hasOctaveTable = checkForOctaveTable(buffer, offset);
    boolean isInverted = checkIfInverted(buffer, offset);
    boolean isCombined = checkIfCombined(buffer, offset);

    if (tableSize == 90) {
        if (!hasOctaveTable && !isInverted && !isCombined) {
            return FrequencyTableType.LINEAR;
        }
        else if (hasOctaveTable) {
            return FrequencyTableType.LINEAR_OCT_NOTE;
        }
        // ... additional combinations
    }
    else if (tableSize == 72) {
        return FrequencyTableType.SHORT;
    }
    else if (tableSize == 65) {
        return FrequencyTableType.SHORT2;
    }

    return null;  // Unknown format
}
```

#### Memory Annotation

**Automatic Labeling**:
```java
void annotateFrequencyTable(int offset, FrequencyTableType type, int a4_hz) {
    // Mark memory as data
    for (int i = 0; i < tableSize; i++) {
        memory[offset + i].isData = true;
        memory[offset + i].isCode = false;
        memory[offset + i].dataType = DataType.WORD;
    }

    // Generate labels
    String loLabel = "SIDFREQLO";
    String hiLabel = "SIDFREQHI";

    memory[offset].label = loLabel;
    memory[offset + tableSize/2].label = hiLabel;

    // Add comments with calculated frequencies
    memory[offset].comment = String.format(
        "Frequency table (A4 = %d Hz %s)",
        a4_hz,
        (a4_hz >= 440 && a4_hz <= 450) ? "PAL" : "NTSC"
    );
}
```

**Usage in Disassembly**:
- Prevents frequency data from being disassembled as code
- Generates readable labels in assembly output
- Provides frequency information in comments
- Validates music data structure

---

## 4. Output Formats & Assemblers

### 4.1 Supported Assembler Formats

**Assembler Class**: `sw_emulator.software.Assembler`
**Location**: `src/sw_emulator/software/Assembler.java`

#### 8 Assembler Syntaxes

**Enumeration**:
```java
enum AssemblerName {
    DASM,               // Classic 6502 assembler
    TMPx,               // Commodore assembler variant
    CA65,               // cc65 cross-compiler assembler
    ACME,               // ACME Crossassembler
    KickAssembler,      // Modern 6502 assembler (popular for C64)
    Tass64,             // 64Tass multi-processor assembler
    Glass,              // 8-bit systems assembler
    AS                  // Macro Assembler (MOS6502/Intel8048 variants)
}
```

#### Syntax Variations by Assembler

**1. DASM (Classic)**:
```assembly
; Labels and comments
INIT:           ; Entry point
    LDA #$00    ; Load accumulator
    STA $D400   ; Store to SID

; Data declarations
FREQLO: .byte $00, $01, $02, $03
FREQHI: .byte $10, $11, $12, $13
NOTES:  .word $1234, $5678
TEXT:   .byte "MUSIC", $00
```

**2. ACME (Modern)**:
```assembly
; Labels and comments
!zone init
.init           ; Entry point
    lda #$00    ; Load accumulator
    sta $d400   ; Store to SID

; Data declarations
.freqlo !byte $00, $01, $02, $03
.freqhi !byte $10, $11, $12, $13
.notes  !word $1234, $5678
.text   !text "MUSIC", $00
```

**3. KickAssembler (Advanced)**:
```assembly
// Labels and comments
.label INIT = $1000
.label SID = $d400

INIT: {
    lda #$00    // Load accumulator
    sta SID     // Store to SID
}

// Data declarations
.var freqlo = List().add($00, $01, $02, $03)
.var freqhi = List().add($10, $11, $12, $13)

freqlo_data: .fill freqlo.size(), freqlo.get(i)
notes_data:  .word $1234, $5678
text_data:   .text "MUSIC"
```

**4. CA65 (cc65 Suite)**:
```assembly
; Labels and comments
.proc init
    lda #$00    ; Load accumulator
    sta $D400   ; Store to SID
    rts
.endproc

; Data declarations
.segment "RODATA"
freqlo: .byte $00, $01, $02, $03
freqhi: .byte $10, $11, $12, $13
notes:  .word $1234, $5678
text:   .asciiz "MUSIC"
```

**5. 64Tass**:
```assembly
; Labels and comments
init    .proc
        lda #$00    ; Load accumulator
        sta $d400   ; Store to SID
        rts
        .pend

; Data declarations
freqlo  .byte $00, $01, $02, $03
freqhi  .byte $10, $11, $12, $13
notes   .word $1234, $5678
text    .text "MUSIC", $00
```

**6. AS (Macro Assembler)**:
```assembly
; Labels and comments (Intel-style)
init:
        ld      a, #00h     ; Load accumulator
        st      a, (0d400h) ; Store to SID
        ret

; Data declarations
freqlo: db      00h, 01h, 02h, 03h
freqhi: db      10h, 11h, 12h, 13h
notes:  dw      1234h, 5678h
text:   db      "MUSIC", 00h
```

**7. TMPx (Commodore)**:
```assembly
; Labels and comments (Commodore-style)
*=$1000
INIT    LDA #$00    ;Load accumulator
        STA $D400   ;Store to SID
        RTS

; Data declarations
FREQLO  .BYTE $00,$01,$02,$03
FREQHI  .BYTE $10,$11,$12,$13
NOTES   .WORD $1234,$5678
TEXT    .TEXT "MUSIC",$00
```

**8. Glass**:
```assembly
; Labels and comments
.ORG $1000
INIT:
        LDA #$00    ; Load accumulator
        STA $D400   ; Store to SID
        RTS

; Data declarations
FREQLO: DB $00, $01, $02, $03
FREQHI: DB $10, $11, $12, $13
NOTES:  DW $1234, $5678
TEXT:   DB "MUSIC", $00
```

### 4.2 Data Declaration Types

**Byte Declarations**:
```java
void putByte(int value) {
    switch (assembler) {
        case DASM:
        case CA65:
        case TMPx:
            output.append(String.format(".byte $%02X", value));
            break;
        case ACME:
            output.append(String.format("!byte $%02X", value));
            break;
        case KickAssembler:
            output.append(String.format(".byte $%02X", value));
            break;
        case Tass64:
            output.append(String.format(".byte $%02X", value));
            break;
        case AS:
            output.append(String.format("db $%02X", value));
            break;
        case Glass:
            output.append(String.format("DB $%02X", value));
            break;
    }
}
```

**Word Declarations** (16-bit):
```java
void putWord(int value) {
    int lowByte = value & 0xFF;
    int highByte = (value >> 8) & 0xFF;

    switch (assembler) {
        case DASM:
        case CA65:
            output.append(String.format(".word $%04X", value));
            break;
        case ACME:
            output.append(String.format("!word $%04X", value));
            break;
        case KickAssembler:
            output.append(String.format(".word $%04X", value));
            break;
        case AS:
            output.append(String.format("dw $%04X", value));
            break;
    }
}
```

**Swapped Word Declarations**:
```java
void putWordSwapped(int value) {
    int lowByte = value & 0xFF;
    int highByte = (value >> 8) & 0xFF;

    // Some assemblers store words as high byte first
    output.append(String.format(".byte $%02X, $%02X", highByte, lowByte));
}
```

**Tribyte Declarations** (24-bit):
```java
void putTribyte(int value) {
    int byte1 = value & 0xFF;
    int byte2 = (value >> 8) & 0xFF;
    int byte3 = (value >> 16) & 0xFF;

    output.append(String.format(".byte $%02X, $%02X, $%02X",
                                byte1, byte2, byte3));
}
```

**Text/String Declarations**:
```java
void putText(String text) {
    switch (assembler) {
        case DASM:
            output.append(String.format(".byte \"%s\"", text));
            break;
        case ACME:
            output.append(String.format("!text \"%s\"", text));
            break;
        case KickAssembler:
            output.append(String.format(".text \"%s\"", text));
            break;
        case CA65:
            output.append(String.format(".asciiz \"%s\"", text));
            break;
    }
}
```

### 4.3 Output Features

**Label Generation**:
```java
String generateLabel(int address, LabelType type) {
    switch (type) {
        case CODE:
            return String.format("SUB_%04X", address);
        case DATA:
            return String.format("DATA_%04X", address);
        case JUMP_TARGET:
            return String.format("LOC_%04X", address);
        case FREQUENCY_TABLE:
            return "FREQTABLE";
        case MUSIC_DATA:
            return String.format("MUSIC_%04X", address);
    }
}
```

**Relative Address Calculations**:
```java
String formatRelativeBranch(int pc, byte offset) {
    int target = pc + 2 + (byte)offset;
    String label = getLabel(target);

    if (label != null) {
        return label;  // Use label if exists
    }
    else {
        return String.format("$%04X", target);  // Use absolute address
    }
}
```

**Memory Reference Handling**:
```java
String formatMemoryReference(int address) {
    String label = getLabel(address);

    if (label != null) {
        return label;
    }

    // Check for known hardware addresses
    if (address >= 0xD400 && address < 0xD420) {
        return getSIDRegisterName(address);
    }
    else if (address >= 0xD000 && address < 0xD400) {
        return getVICRegisterName(address);
    }
    else if (address >= 0xDC00 && address < 0xDD00) {
        return getCIARegisterName(address);
    }

    return String.format("$%04X", address);
}
```

**Sprite/Graphics Data Macros**:
```java
void outputSpriteData(byte[] data, int offset) {
    output.append("; Sprite data\n");

    for (int row = 0; row < 21; row++) {
        // 3 bytes per row
        int byte1 = data[offset + row*3];
        int byte2 = data[offset + row*3 + 1];
        int byte3 = data[offset + row*3 + 2];

        // Visual representation
        String visual = byteToDots(byte1) + byteToDots(byte2) + byteToDots(byte3);

        output.append(String.format(".byte $%02X, $%02X, $%02X  ; %s\n",
                                    byte1, byte2, byte3, visual));
    }
}

String byteToDots(int b) {
    StringBuilder dots = new StringBuilder();
    for (int bit = 7; bit >= 0; bit--) {
        dots.append(((b >> bit) & 1) == 1 ? "*" : ".");
    }
    return dots.toString();
}
```

**Character Set Visualization**:
```java
void outputCharset(byte[] data, int offset) {
    output.append("; Character set\n");

    for (int charIdx = 0; charIdx < 256; charIdx++) {
        output.append(String.format("; Character $%02X\n", charIdx));

        for (int row = 0; row < 8; row++) {
            int byteValue = data[offset + charIdx*8 + row];
            String visual = byteToDots(byteValue);

            output.append(String.format(".byte $%02X  ; %s\n",
                                       byteValue, visual));
        }
    }
}
```

### 4.4 6502 Disassembly Output

**Disassembler Class**: `sw_emulator.software.cpu.M6510Dasm`
**Location**: `src/sw_emulator/software/cpu/M6510Dasm.java`

#### Instruction Set Coverage

**80 Instruction Types**:
```java
// Legal opcodes (0-55)
enum LegalOpcodes {
    ADC, AND, ASL, BCC, BCS, BEQ, BIT, BMI,
    BNE, BPL, BRK, BVC, BVS, CLC, CLD, CLI,
    CLV, CMP, CPX, CPY, DEC, DEX, DEY, EOR,
    INC, INX, INY, JMP, JSR, LDA, LDX, LDY,
    LSR, NOP, ORA, PHA, PHP, PLA, PLP, ROL,
    ROR, RTI, RTS, SBC, SEC, SED, SEI, STA,
    STX, STY, TAX, TAY, TSX, TXA, TXS, TYA
}

// Undocumented opcodes (56-79)
enum UndocumentedOpcodes {
    SLO, RLA, SRE, RRA, SAX, LAX, DCP, ISC,
    ANC, ALR, ARR, XAA, AHX, TAS, SHY, SHX,
    LAS, AXS, SBC2, NOP2, LAX2, // ... etc
}
```

**Mnemonic Mode Selection**:
```java
enum MnemonicMode {
    MODE1,  // Standard mnemonics (SLO, RLA, etc.)
    MODE2,  // Alternative mnemonics (ASO, RLN, etc.)
    MODE3   // Descriptive mnemonics (LSE, RLN, etc.)
}
```

**Lookup Tables**:
```java
// Instruction type per opcode (256 entries)
static final int[] tableMnemonics = {
    BRK, ORA, /*02*/ KIL, SLO, NOP, ORA, ASL, SLO,
    PHP, ORA, ASL, ANC, NOP, ORA, ASL, SLO,
    BPL, ORA, /*12*/ KIL, SLO, NOP, ORA, ASL, SLO,
    // ... 256 total entries
};

// Addressing mode per opcode
static final int[] tableModes = {
    IMP, IZX, IMP, IZX, ZPG, ZPG, ZPG, ZPG,
    IMP, IMM, ACC, IMM, ABS, ABS, ABS, ABS,
    REL, IZY, IMP, IZY, ZPX, ZPX, ZPX, ZPX,
    // ... 256 total entries
};

// Instruction size in bytes (1-3)
static final int[] tableSize = {
    1, 2, 1, 2, 2, 2, 2, 2,
    1, 2, 1, 2, 3, 3, 3, 3,
    2, 2, 1, 2, 2, 2, 2, 2,
    // ... 256 total entries
};
```

#### Addressing Modes (7 types)

**Addressing Mode Enumeration**:
```java
enum AddressingMode {
    IMP,    // Implied (no operand)
    ACC,    // Accumulator
    IMM,    // Immediate (#$xx)
    ZPG,    // Zero-page ($xx)
    ZPX,    // Zero-page,X ($xx,X)
    ZPY,    // Zero-page,Y ($xx,Y)
    ABS,    // Absolute ($xxxx)
    ABX,    // Absolute,X ($xxxx,X)
    ABY,    // Absolute,Y ($xxxx,Y)
    IND,    // Indirect ($xxxx)
    IZX,    // Indexed indirect (($xx,X))
    IZY,    // Indirect indexed (($xx),Y)
    REL     // Relative (branch target)
}
```

**Formatting Examples**:
```java
String formatOperand(int mode, int operand) {
    switch (mode) {
        case IMP:
            return "";
        case ACC:
            return "A";
        case IMM:
            return String.format("#$%02X", operand);
        case ZPG:
            return String.format("$%02X", operand);
        case ZPX:
            return String.format("$%02X,X", operand);
        case ZPY:
            return String.format("$%02X,Y", operand);
        case ABS:
            return String.format("$%04X", operand);
        case ABX:
            return String.format("$%04X,X", operand);
        case ABY:
            return String.format("$%04X,Y", operand);
        case IND:
            return String.format("($%04X)", operand);
        case IZX:
            return String.format("($%02X,X)", operand);
        case IZY:
            return String.format("($%02X),Y", operand);
        case REL:
            int target = pc + 2 + (byte)operand;
            return String.format("$%04X", target);
    }
}
```

#### Output Methods

**1. cdasm() - Disassemble with Comments**:
```java
String cdasm(int address, byte[] memory) {
    // Format: "ADDRESS  BYTES       MNEMONIC OPERAND  ; Comment"
    // Example: "$1000   78          SEI                ; Disable interrupts"

    int opcode = memory[address];
    int mnemonic = tableMnemonics[opcode];
    int mode = tableModes[opcode];
    int size = tableSize[opcode];

    // Build bytecode representation
    String bytes = String.format("%02X", opcode);
    if (size >= 2) bytes += String.format(" %02X", memory[address+1]);
    if (size == 3) bytes += String.format(" %02X", memory[address+2]);

    // Pad bytes to fixed width
    while (bytes.length() < 12) bytes += " ";

    // Build instruction
    String instruction = getMnemonic(mnemonic) + " " +
                        formatOperand(mode, getOperand(memory, address+1, size-1));

    // Pad instruction to fixed width
    while (instruction.length() < 20) instruction += " ";

    // Add comment
    String comment = getComment(address, opcode, mode);

    return String.format("$%04X   %s  %s; %s\n",
                        address, bytes, instruction, comment);
}
```

**2. csdasm() - Source Code Style**:
```java
String csdasm(int address, byte[] memory) {
    // Format: "LABEL:    MNEMONIC OPERAND"
    // Example: "INIT:     LDA #$00"

    String output = "";

    // Add label if exists
    String label = getLabel(address);
    if (label != null) {
        output += label + ":\n";
    }

    // Indent instruction
    output += "    ";

    // Add mnemonic and operand
    int opcode = memory[address];
    int mnemonic = tableMnemonics[opcode];
    int mode = tableModes[opcode];
    int size = tableSize[opcode];

    output += getMnemonic(mnemonic);
    String operand = formatOperand(mode, getOperand(memory, address+1, size-1));
    if (!operand.isEmpty()) {
        output += " " + operand;
    }

    output += "\n";
    return output;
}
```

**3. dcom() - Undocumented Instruction Annotations**:
```java
String getUndocumentedComment(int opcode) {
    if (opcode >= 56 && opcode <= 79) {
        return "Undocumented instruction";
    }

    // Specific warnings for unstable opcodes
    switch (opcode) {
        case 0x8B:  // XAA
            return "Unstable instruction - results may vary";
        case 0x9F:  // AHX
        case 0x9E:  // SHX
        case 0x9C:  // SHY
            return "Unstable instruction - affected by temperature";
        case 0x93:  // AHX
        case 0x9B:  // TAS
            return "Unusual operation - use with caution";
        default:
            return "Illegal instruction";
    }
}
```

#### Code vs Data Handling

**Decision Logic**:
```java
String disassembleLocation(int address, byte[] memory, MemoryDasm[] memState) {
    if (memState[address].isCode) {
        // Disassemble as instruction
        return csdasm(address, memory);
    }
    else if (memState[address].isGarbage || !option.useAsCode) {
        // Output as data bytes
        int value = memory[address] & 0xFF;

        if (memState[address].dataType == DataType.WORD) {
            int word = value | ((memory[address+1] & 0xFF) << 8);
            return assembler.putWord(word);
        }
        else {
            return assembler.putByte(value);
        }
    }
    else {
        // Undocumented instruction handling
        if (option.noUndocumented) {
            // Mark as data instead of illegal instruction
            return assembler.putByte(memory[address] & 0xFF);
        }
        else {
            // Disassemble with warning comment
            return cdasm(address, memory) + dcom(memory[address]);
        }
    }
}
```

#### Address Tracking

**Program Counter Management**:
```java
int pc;     // Program counter (logical address in 6502 memory space)
int pos;    // Buffer position (physical offset in input byte array)

// Sequential disassembly
while (pc < endAddress) {
    int opcode = buffer[pos];
    int size = tableSize[opcode];

    // Disassemble instruction
    output += disassemble(pc, buffer, pos);

    // Advance both counters
    pc += size;
    pos += size;
}
```

**Relative Addressing Calculation**:
```java
int calculateBranchTarget(int pc, byte offset) {
    // Relative offset is signed (-128 to +127)
    int signedOffset = (byte)offset;

    // Target = PC + 2 (instruction size) + offset
    int target = pc + 2 + signedOffset;

    // Wrap around at 64K boundary
    target = target & 0xFFFF;

    return target;
}
```

**Label References**:
```java
void setLabel(int address, String name) {
    memoryDasm[address].label = name;
}

void setLabelPlus(int address, String prefix) {
    String label = prefix + String.format("_%04X", address);
    memoryDasm[address].label = label;
}

String getLabel(int address) {
    return memoryDasm[address].label;
}
```

---

## 5. Configuration & Customization

### 5.1 SID-Specific Configuration Options

**Configuration Class**: `sw_emulator.swing.main.Option`
**Location**: `src/sw_emulator/swing/main/Option.java`

#### Frequency Analysis Configuration

**Master Control**:
```java
boolean useSidFreq = false;             // Enable SID frequency analysis
```

**Memory Marking Options**:
```java
boolean sidFreqMarkMem = false;         // Mark detected tables in memory
boolean sidFreqCreateLabel = false;     // Generate labels for tables
boolean sidFreqCreateComment = false;   // Add frequency comments
```

**Label Customization**:
```java
String sidFreqLoLabel = "SIDFREQLO";    // Low byte table label
String sidFreqHiLabel = "SIDFREQHI";    // High byte table label
```

**Table Type Recognition** (12 boolean flags):
```java
// Linear tables
boolean sidFreqTableLinear = true;
boolean sidFreqTableLinearOctNote = true;

// Scale tables (C,D,E,F,G,A,B only)
boolean sidFreqTableScale = true;
boolean sidFreqTableScaleOctNote = true;

// Inverse tables (high byte first)
boolean sidFreqTableInverse = true;
boolean sidFreqTableInverseOctNote = true;

// Combined tables (hi/lo separated)
boolean sidFreqTableCombined = true;
boolean sidFreqTableCombinedOctNote = true;
boolean sidFreqTableCombinedInverse = true;
boolean sidFreqTableCombinedInverseOctNote = true;

// Short tables
boolean sidFreqTableShort = true;       // 72 notes (6 octaves)
boolean sidFreqTableShort2 = true;      // 65 notes (custom)
```

#### PSID Header Configuration

**Header Generation**:
```java
boolean createPSID = true;              // Generate PSID header in output
boolean notMarkPSID = false;            // Skip marking PSID metadata
```

**Routine Labeling**:
```java
String psidInitSongsLabel = "PSIDINIT"; // Init routine label
String psidPlaySoundsLabel = "PSIDPLAY";// Play routine label
```

**Example Output**:
```assembly
; PSID header metadata
; Title: Music Title
; Author: Composer Name
; Released: 2023

PSIDINIT:           ; Init routine at $1000
    lda #$00        ; Subtune number in A
    jsr INIT
    rts

PSIDPLAY:           ; Play routine at $10A1
    jsr PLAY
    rts
```

#### Assembler Selection

**Syntax Customization**:
```java
enum AssemblerName {
    DASM,
    TMPx,
    CA65,
    ACME,
    KickAssembler,
    Tass64,
    Glass,
    AS
}

AssemblerName selectedAssembler = AssemblerName.ACME;
```

**Per-Assembler Settings**:
```java
class AssemblerSettings {
    String labelSuffix;         // ":", "", etc.
    String commentPrefix;       // ";", "//", etc.
    String byteDirective;       // ".byte", "!byte", "db", etc.
    String wordDirective;       // ".word", "!word", "dw", etc.
    String textDirective;       // ".text", "!text", etc.
    boolean caseSensitive;      // Label case sensitivity
    boolean upperCaseOpcodes;   // LDA vs lda
}
```

### 5.2 Output Formatting Options

#### Spacing and Alignment

**Indentation**:
```java
int numInstrSpaces = 6;         // Instruction indentation (default)
int numInstrTabs = 0;           // Tab-based alternative (0 = use spaces)

// Example with 6 spaces:
//       LDA #$00
// ^^^^^^ (6 spaces)
```

**Comment Alignment**:
```java
int numInstrCSpaces = 34;       // Comment column (default)
int numInstrCTabs = 0;          // Tab-based alternative

// Example with 34 spaces:
// LDA #$00                          ; Load zero
//         ^^^^^^^^^^^^^^^^^^^^^^^^^ (padding to column 34)
```

**Opcode-Operand Separation**:
```java
int numSpacesOp = 1;            // Spaces between opcode and operand
int numTabsOp = 0;              // Tab-based alternative

// Example with 1 space:
// LDA #$00
//    ^ (1 space)
```

#### Header Management

**Header Modes**:
```java
enum HeaderMode {
    STANDARD,       // Include standard file header
    NONE,           // No header
    CUSTOM          // User-defined header
}

HeaderMode headerMode = HeaderMode.STANDARD;
```

**Standard Header Template**:
```java
String getStandardHeader() {
    return ";\n" +
           "; JC64dis Disassembly\n" +
           "; File: " + inputFileName + "\n" +
           "; Date: " + currentDate + "\n" +
           "; Assembler: " + assemblerName + "\n" +
           ";\n";
}
```

**PSID/SAP Specific Headers**:
```java
boolean createPSIDHeader = true;        // Add PSID metadata as comments
boolean createSAPHeader = true;         // Add SAP metadata as comments
```

#### Opcode Handling

**Illegal Opcode Mode**:
```java
enum IllegalOpcodeMode {
    DISASSEMBLE,    // Show illegal opcodes with warning
    AS_DATA,        // Output as data bytes
    OMIT            // Skip entirely
}

IllegalOpcodeMode illegalOpcodeMode = IllegalOpcodeMode.DISASSEMBLE;
```

**Case Sensitivity**:
```java
boolean opcodeUpperCasePreview = false; // Preview window: LDA vs lda
boolean opcodeUpperCaseSource = false;  // Source output: LDA vs lda
```

**Undocumented Instructions**:
```java
boolean noUndocumented = false;         // Exclude undocumented opcodes
```

**Example**:
```assembly
; With noUndocumented = false:
$1000   0B 00       ANC #$00            ; Undocumented instruction

; With noUndocumented = true:
$1000   0B          .byte $0B           ; Marked as data
$1001   00          .byte $00
```

#### Memory Representation

**Value Display Format**:
```java
enum MemoryValueFormat {
    HEXADECIMAL,    // $00
    DECIMAL,        // 0
    BINARY,         // %00000000
    CHARACTER       // 'A'
}

MemoryValueFormat memoryValue = MemoryValueFormat.HEXADECIMAL;
```

**Byte Aggregation**:
```java
int maxByteAggregate = 8;       // Bytes per line in data blocks

// Example with maxByteAggregate = 8:
.byte $00, $01, $02, $03, $04, $05, $06, $07
.byte $08, $09, $0A, $0B, $0C, $0D, $0E, $0F
```

**Word Aggregation**:
```java
int maxWordAggregate = 4;       // Words per line in data blocks

// Example with maxWordAggregate = 4:
.word $0000, $0001, $0002, $0003
.word $0004, $0005, $0006, $0007
```

**Dots Representation** (for comments):
```java
enum DotsType {
    ASCII,          // Standard ASCII dots (.)
    UTF16           // Unicode characters (•○●)
}

DotsType dotsType = DotsType.ASCII;

// Used in sprite/character visualization:
// .byte $FF  ; ********
// .byte $81  ; *......*
```

#### Machine-Specific Comments

**Platform-Specific Documentation**:
```java
// Commodore 64 chip registers
boolean commentC64_SID = true;          // SID chip ($D400-$D7FF)
boolean commentC64_VIC = true;          // VIC-II chip ($D000-$D3FF)
boolean commentC64_CIA1 = true;         // CIA#1 chip ($DC00-$DCFF)
boolean commentC64_CIA2 = true;         // CIA#2 chip ($DD00-$DDFF)

// Commodore 128 memory areas
boolean commentC128_MMU = true;         // Memory management
boolean commentC128_VDC = true;         // Video display controller

// Disk drive hardware
boolean comment1541_VIA1 = true;        // VIA chip #1
boolean comment1541_VIA2 = true;        // VIA chip #2

// Other platforms
boolean commentPlus4 = true;            // Commodore Plus/4
boolean commentVIC20 = true;            // VIC-20
boolean commentAtari = true;            // Atari 8-bit
```

**Example with Comments Enabled**:
```assembly
LDA $D400       ; SID: Voice 1 frequency low byte
STA $D401       ; SID: Voice 1 frequency high byte
LDA $D012       ; VIC: Raster line register
STA $DC00       ; CIA#1: Data port A
```

### 5.3 Player Detection Configuration

**Pattern Configuration** (from `SidId.java`):

**Configuration File Format** (inferred):
```
# SIDId configuration file
# Format: PLAYER_NAME <hex_bytes | ANY | AND | END>

# Laxity NewPlayer v21
Laxity 78 A9 00 8D 00 D4 ANY ANY 8D 01 D4 END
Laxity A2 00 BD ANY ANY 9D 00 D4 E8 E0 19 D0 F6 END

# JCH NewPlayer
JCH 4C ANY ANY 4C ANY ANY AD ANY ANY 8D 18 D4 END

# Maniacs of Noise
MoN A9 00 AA 9D 00 D4 CA 10 FB 8D 18 D4 END

# Future Composer
FC 78 A2 00 A9 00 9D 00 D4 CA D0 FA END
```

**Loading Configuration**:
```java
SidId sidId = SidId.instance;
sidId.readConfig("sidid_patterns.cfg");

// Check loaded patterns
int playerCount = sidId.getNumberOfPlayers();
int patternCount = sidId.getNumberOfPatterns();

System.out.println("Loaded " + playerCount + " players");
System.out.println("Total " + patternCount + " patterns");
```

**Identification Usage**:
```java
byte[] buffer = loadSIDFile("music.sid");

// Identify players
String players = sidId.identifyBuffer(buffer, buffer.length);

if (players != null && !players.isEmpty()) {
    System.out.println("Detected player: " + players);
}
else {
    System.out.println("Unknown player");
}

// Access cached result
String lastDetected = sidId.lastPlayers;
```

### 5.4 Batch Processing Capabilities

**Command-Line Entry Points**:

**1. FileDasm (Legacy CLI)**:
```bash
# English output
java -cp jc64.jar sw_emulator.software.FileDasm -en input.sid output.asm

# Italian output
java -cp jc64.jar sw_emulator.software.FileDasm -it input.sid output.asm
```

**Parameters**:
- `-en` / `-it`: Language selection (English/Italian)
- `input_file`: Path to PRG/SID/MUS file
- `output_file`: Path for assembly source output

**Single-File Processing**:
```java
public static void main(String[] args) {
    String language = "en";
    String inputFile = "";
    String outputFile = "";

    // Parse arguments
    for (String arg : args) {
        if (arg.equals("-en")) language = "en";
        else if (arg.equals("-it")) language = "it";
        else if (inputFile.isEmpty()) inputFile = arg;
        else if (outputFile.isEmpty()) outputFile = arg;
    }

    // Process single file
    FileDasm dasm = new FileDasm();
    dasm.disassemble(inputFile, outputFile, language);
}
```

**2. JC64dis (Modern GUI)**:
```bash
java -cp jc64.jar sw_emulator.swing.main.JC64dis
```

**Features**:
- Three-panel iterative interface
- Project-based workflow (`Project.java`)
- Recent items tracking (`RecentItems.java`)
- Undo/redo support (`UndoManager.java`)
- Cross-reference tooltips (`XRefToolTipManager.java`)

**No Documented Batch Mode**, but supports:
- Project files for saving/loading state
- Recent items for quick access
- Scripting could potentially be added

**Memory State System** (`MemoryFlags`):
```java
// Analyzes execution vs data regions
MemoryDasm[] memoryDasm = new MemoryDasm[0x10000];  // 64K address space

// Each address classified based on execution trace
for (int i = 0; i < 0x10000; i++) {
    memoryDasm[i] = new MemoryDasm();
    memoryDasm[i].copy = (byte)0;
    memoryDasm[i].isCode = false;
    memoryDasm[i].isData = false;
    memoryDasm[i].isGarbage = false;
    memoryDasm[i].isInside = false;
}
```

**Delegated Disassemblers** (mentioned but not found in searches):
```java
// Format-specific disassembly handlers
C64SidDasm    // PSID/RSID specific disassembly
C64MusDasm    // MUS file specific disassembly
C64Dasm       // Generic C64 PRG disassembly
```

---

## 6. Integration Points & API

### 6.1 Entry Points

#### Entry Point 1: FileDasm (CLI)

**Class**: `sw_emulator.software.FileDasm`

**Invocation**:
```bash
java -cp jc64.jar sw_emulator.software.FileDasm [-en|-it] <input> <output>
```

**Processing Flow**:
```
1. File detection (isPSID() or isMUS())
2. Header parsing and metadata extraction
3. Memory state analysis (MemoryFlags)
4. Disassembly with format-specific handler
5. Assembly source generation (via Assembler class)
6. Output file writing
```

**Code Example**:
```java
public class FileDasm {
    public void disassemble(String inputPath, String outputPath, String lang) {
        // 1. Read input file
        byte[] buffer = readFile(inputPath);

        // 2. Detect format
        if (isPSID(buffer)) {
            disassemblePSID(buffer, outputPath);
        }
        else if (isMUS(buffer)) {
            disassemblyMUS(buffer, outputPath);
        }
        else {
            disassemblePRG(buffer, outputPath);
        }
    }
}
```

#### Entry Point 2: JC64Dis (GUI)

**Class**: `sw_emulator.swing.main.JC64dis`

**Invocation**:
```bash
java -cp jc64.jar sw_emulator.swing.main.JC64dis
```

**Features**:
- **Three-panel iterative disassembly interface**
- **Project-based file management** (`Project.java`)
- **Recent items tracking** (`RecentItems.java`)
- **Undo/redo support** (`UndoManager.java`)
- **Cross-reference tooltips** (`XRefToolTipManager.java`)

**GUI-Specific Enhancements** (from GitHub issue #7):
- **ALT+Click navigation** to jump/branch targets
- **Dual-window view** (code + data)
- **Manual load address override**
- **Comment management** (user annotations)
- **Commodore font rendering** for hex/text/char view

**Programmatic Usage**:
```java
JC64dis gui = new JC64dis();
gui.setVisible(true);

// Load SID file programmatically
gui.loadFile(new File("music.sid"));

// Access disassembly result
String asmSource = gui.getDisassemblyText();
```

### 6.2 Input File Handling

**Supported Input Formats**:

| Format | Magic Bytes | Detection Method | Handler |
|--------|-------------|------------------|---------|
| PSID v1 | "PSID" + version 0x01 | `isPSID()` | FileDasm/C64SidDasm |
| PSID v2 | "PSID" + version 0x02 | `isPSID()` | FileDasm/C64SidDasm |
| RSID | "RSID" | `isPSID()` | FileDasm/C64SidDasm |
| MUS/STR | Structural (0x01 0x4F pattern) | `isMUS()` | FileDasm/C64MusDasm |
| PRG | None (default) | Fallback | FileDasm/C64Dasm |

**File Size Limits**:
```java
int MIN_FILE_SIZE = 0x80;           // 128 bytes minimum
int MAX_FILE_SIZE = 0x66000;        // 417,792 bytes (~408 KB) maximum

void validateFileSize(byte[] buffer) throws IOException {
    if (buffer.length < MIN_FILE_SIZE) {
        throw new IOException("File too small (min " + MIN_FILE_SIZE + " bytes)");
    }
    if (buffer.length > MAX_FILE_SIZE) {
        throw new IOException("File too large (max " + MAX_FILE_SIZE + " bytes)");
    }
}
```

**File Reading**:
```java
byte[] readFile(String path) throws IOException {
    File file = new File(path);

    // Security check
    if (!file.exists()) {
        throw new FileNotFoundException("File not found: " + path);
    }
    if (!file.canRead()) {
        throw new SecurityException("Cannot read file: " + path);
    }

    // Read entire file
    FileInputStream fis = new FileInputStream(file);
    BufferedInputStream bis = new BufferedInputStream(fis);

    byte[] buffer = new byte[(int)file.length()];
    bis.read(buffer);
    bis.close();

    return buffer;
}
```

### 6.3 Output File Handling

**Supported Output Formats**:
- Assembly source (8 assembler syntax variants)
- Text export with comments
- Label/symbol tables
- Character/sprite visualizations

**File Writing**:
```java
void writeOutput(String path, String content) throws IOException {
    File file = new File(path);

    // Create parent directories if needed
    File parent = file.getParentFile();
    if (parent != null && !parent.exists()) {
        parent.mkdirs();
    }

    // Write character-by-character
    FileOutputStream fos = new FileOutputStream(file);
    BufferedOutputStream bos = new BufferedOutputStream(fos);

    for (char c : content.toCharArray()) {
        bos.write((byte)c);
    }

    bos.flush();
    bos.close();
}
```

### 6.4 Error Handling and Validation

**File Validation**:
```java
boolean validatePSID(byte[] buffer) {
    // Magic bytes check
    String magic = new String(buffer, 0, 4, StandardCharsets.US_ASCII);
    if (!magic.equals("PSID") && !magic.equals("RSID")) {
        return false;
    }

    // Version check
    int version = (buffer[4] << 8) | buffer[5];
    if (version != 1 && version != 2) {
        return false;
    }

    // Data offset check
    int dataOffset = (buffer[6] << 8) | buffer[7];
    if (version == 1 && dataOffset != 0x76) {
        return false;
    }
    if (version == 2 && dataOffset != 0x7C) {
        return false;
    }

    return true;
}

boolean validateMUS(byte[] buffer) {
    // Extract voice lengths
    int v1Length = getWord(buffer, 0) + 1;
    int v2Length = getWord(buffer, 2) + 1;
    int v3Length = getWord(buffer, 4) + 1;

    // Calculate positions
    int v1End = 8 + v1Length;
    int v2End = v1End + v2Length;
    int v3End = v2End + v3Length;

    // Check terminators [0x01, 0x4F]
    if (buffer[v1End - 2] != 0x01 || buffer[v1End - 1] != 0x4F) {
        return false;
    }
    if (buffer[v2End - 2] != 0x01 || buffer[v2End - 1] != 0x4F) {
        return false;
    }
    if (buffer[v3End - 2] != 0x01 || buffer[v3End - 1] != 0x4F) {
        return false;
    }

    return true;
}
```

**Exception Handling**:
```java
try {
    byte[] buffer = readFile(inputPath);
    disassemble(buffer, outputPath);
}
catch (FileNotFoundException e) {
    System.err.println("Error: Input file not found - " + e.getMessage());
}
catch (SecurityException e) {
    System.err.println("Error: Permission denied - " + e.getMessage());
}
catch (IOException e) {
    System.err.println("Error: I/O error - " + e.getMessage());
}
catch (Exception e) {
    System.err.println("Error: Unexpected error - " + e.getMessage());
    e.printStackTrace();
}
```

### 6.5 Programmatic Integration

**Memory-Based Disassembly API**:
```java
public class MemoryDasm {
    byte copy;                      // Byte value
    boolean isCode;                 // Code flag
    boolean isData;                 // Data flag
    boolean isGarbage;              // Garbage flag
    boolean isInside;               // Processing flag

    String comment;                 // Auto-generated comment
    String userComment;             // User override

    ArrayList<Integer> related;     // Cross-references

    DataType dataType;              // Classification
    BasicType basicType;            // BASIC type

    // Methods
    public MemoryDasm clone();      // State snapshot
    public boolean equals(Object o); // Comparison
    public int hashCode();          // Hashing
}

// Usage
MemoryDasm[] memory = new MemoryDasm[0x10000];
for (int i = 0; i < 0x10000; i++) {
    memory[i] = new MemoryDasm();
}

// Mark code regions
memory[0x1000].isCode = true;
memory[0x1000].comment = "Init routine";

// Mark data regions
memory[0x2000].isData = true;
memory[0x2000].dataType = DataType.WORD;
memory[0x2000].comment = "Frequency table";
```

**Player Identification API**:
```java
// Singleton instance
SidId sidId = SidId.instance;

// Configuration
sidId.readConfig("sidid_patterns.cfg");

// Identification
byte[] buffer = loadSIDFile("music.sid");
String players = sidId.identifyBuffer(buffer, buffer.length);

// Statistics
int playerCount = sidId.getNumberOfPlayers();
int patternCount = sidId.getNumberOfPatterns();

// Results
String lastPlayers = sidId.lastPlayers;
System.out.println("Detected: " + lastPlayers);
```

**SID Playback API**:
```java
// Create player
CRSID player = new CRSID();

// Initialize (44100 Hz sample rate)
player.init(44100);

// Load SID file
PSID psid = new PSID();
psid.load("music.sid");
player.initSIDtune(psid, 0);  // Subtune 0

// Playback control
player.playSIDfile("music.sid", 0);
player.pausePlaying();
player.stopPlaying();
player.fPlay();  // Toggle 1x/4x speed

// Voice control
player.setVoiceMute(1, true);   // Mute voice 1
player.setVoiceMute(2, false);  // Unmute voice 2

// Audio generation
byte[] audioBuffer = new byte[4096];
player.generateSound(audioBuffer);

// Status
long elapsedMs = player.time();
System.out.println("Playback time: " + elapsedMs + " ms");
```

---

## 7. SIDM2 Integration Strategies

### 7.1 Integration Architecture

```
┌─────────────────────────────────────────────────┐
│ SIDM2 Python Pipeline (Enhanced)               │
├─────────────────────────────────────────────────┤
│                                                 │
│  Input SID File                                 │
│       ↓                                         │
│  ┌────────────────────────────────────────┐    │
│  │ JC64 Analysis Layer (NEW)             │    │
│  │  - Player detection (SIDId)           │    │
│  │  - Frequency table recognition        │    │
│  │  - Code vs data separation            │    │
│  │  - Memory usage analysis              │    │
│  └────────────┬───────────────────────────┘    │
│               │                                 │
│               ↓                                 │
│  ┌────────────────────────────────────────┐    │
│  │ Enhanced Laxity Parser                │    │
│  │  - Auto-detect player type            │    │
│  │  - Validate frequency tables          │    │
│  │  - Improved data extraction           │    │
│  └────────────┬───────────────────────────┘    │
│               │                                 │
│               ↓                                 │
│  ┌────────────────────────────────────────┐    │
│  │ Laxity Converter (99.93% accurate)    │    │
│  └────────────┬───────────────────────────┘    │
│               │                                 │
│               ↓                                 │
│  Output SF2 File                                │
│       ↓                                         │
│  ┌────────────────────────────────────────┐    │
│  │ JC64 Validation Layer (NEW)           │    │
│  │  - Disassemble output SID             │    │
│  │  - Compare memory usage               │    │
│  │  - Verify frequency tables            │    │
│  │  - Cross-check player structure       │    │
│  └────────────────────────────────────────┘    │
│                                                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ JC64 Java Components (via Bridge)              │
├─────────────────────────────────────────────────┤
│  - FileDasm (file format detection)            │
│  - SidId (player detection)                    │
│  - SidFreq (frequency analysis)                │
│  - Disassembly (code/data separation)          │
│  - CRSID (SID playback for validation)         │
└─────────────────────────────────────────────────┘
```

### 7.2 Integration Methods

**Method 1: Subprocess Wrapper (Recommended for MVP)**

**Advantages**:
- ✅ Simple to implement
- ✅ No Java/Python interop complexity
- ✅ Fault isolation (Java crashes don't affect Python)

**Disadvantages**:
- ⚠️ Performance overhead (process spawning)
- ⚠️ Limited data interchange (files or stdout only)

**Implementation**:
```python
# sidm2/jc64_wrapper.py

import subprocess
import tempfile
from pathlib import Path

class JC64Wrapper:
    """Python wrapper for JC64 Java components."""

    def __init__(self, jc64_jar_path: str):
        self.jar_path = Path(jc64_jar_path)
        if not self.jar_path.exists():
            raise FileNotFoundError(f"JC64 JAR not found: {jc64_jar_path}")

    def disassemble_sid(self, sid_file: Path, output_file: Path = None) -> str:
        """Disassemble SID file using FileDasm."""
        if output_file is None:
            output_file = Path(tempfile.mktemp(suffix=".asm"))

        cmd = [
            "java",
            "-cp", str(self.jar_path),
            "sw_emulator.software.FileDasm",
            "-en",
            str(sid_file),
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"JC64 disassembly failed: {result.stderr}")

        return output_file.read_text()

    def identify_player(self, sid_file: Path) -> str:
        """Identify SID player using SIDId."""
        # Call custom Java wrapper that uses SidId class
        cmd = [
            "java",
            "-cp", str(self.jar_path),
            "sidm2.JC64PlayerIdentifier",  # Custom wrapper class
            str(sid_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Player identification failed: {result.stderr}")

        return result.stdout.strip()

    def detect_frequency_tables(self, sid_file: Path) -> dict:
        """Detect frequency tables using SidFreq."""
        cmd = [
            "java",
            "-cp", str(self.jar_path),
            "sidm2.JC64FrequencyDetector",  # Custom wrapper class
            str(sid_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Frequency detection failed: {result.stderr}")

        # Parse JSON output
        import json
        return json.loads(result.stdout)
```

**Usage in SIDM2**:
```python
from sidm2.jc64_wrapper import JC64Wrapper

# Initialize wrapper
jc64 = JC64Wrapper("path/to/jc64.jar")

# Identify player
player = jc64.identify_player("music.sid")
print(f"Detected player: {player}")

# Detect frequency tables
tables = jc64.detect_frequency_tables("music.sid")
print(f"Found {len(tables)} frequency tables")

# Disassemble for analysis
asm_code = jc64.disassemble_sid("music.sid")
```

**Method 2: JPype Bridge (Advanced)**

**Advantages**:
- ✅ Direct Java object access
- ✅ No subprocess overhead
- ✅ Rich data interchange

**Disadvantages**:
- ⚠️ Complex setup
- ⚠️ Potential version conflicts
- ⚠️ Shared JVM state

**Implementation**:
```python
# sidm2/jc64_jpype_wrapper.py

import jpype
import jpype.imports
from pathlib import Path

class JC64JPypeWrapper:
    """JPype-based wrapper for JC64 components."""

    def __init__(self, jc64_jar_path: str):
        if not jpype.isJVMStarted():
            jpype.startJVM(classpath=[jc64_jar_path])

        # Import Java classes
        from sw_emulator.software import FileDasm, SidId, SidFreq
        from sw_emulator.software.sidid import PSID

        self.FileDasm = FileDasm
        self.SidId = SidId
        self.SidFreq = SidFreq
        self.PSID = PSID

    def parse_psid_header(self, sid_file: Path) -> dict:
        """Parse PSID header directly."""
        psid = self.PSID()
        psid.load(str(sid_file))

        return {
            'magic': psid.getMagic(),
            'version': psid.getVersion(),
            'load_addr': psid.getLoadAddress(),
            'init_addr': psid.getInitAddress(),
            'play_addr': psid.getPlayAddress(),
            'song_count': psid.getSongCount(),
            'start_song': psid.getStartSong(),
            'title': psid.getTitle(),
            'author': psid.getAuthor(),
            'copyright': psid.getCopyright()
        }

    def identify_player(self, sid_file: Path) -> str:
        """Identify player using SIDId."""
        sidId = self.SidId.instance

        # Read file
        with open(sid_file, 'rb') as f:
            buffer = list(f.read())

        # Identify
        players = sidId.identifyBuffer(buffer, len(buffer))
        return players if players else "Unknown"

    def detect_frequency_tables(self, sid_file: Path) -> list:
        """Detect frequency tables using SidFreq."""
        sidFreq = self.SidFreq()

        # Read file
        with open(sid_file, 'rb') as f:
            buffer = list(f.read())

        # Analyze
        tables = sidFreq.analyzeBuffer(buffer)

        results = []
        for table in tables:
            results.append({
                'offset': table.getOffset(),
                'type': str(table.getType()),
                'a4_hz_pal': table.getA4FrequencyPAL(),
                'a4_hz_ntsc': table.getA4FrequencyNTSC(),
                'notes': list(table.getNotes())
            })

        return results
```

**Usage**:
```python
from sidm2.jc64_jpype_wrapper import JC64JPypeWrapper

jc64 = JC64JPypeWrapper("path/to/jc64.jar")

# Parse PSID header
header = jc64.parse_psid_header("music.sid")
print(f"Title: {header['title']}")
print(f"Author: {header['author']}")

# Identify player
player = jc64.identify_player("music.sid")
print(f"Player: {player}")

# Detect tables
tables = jc64.detect_frequency_tables("music.sid")
for table in tables:
    print(f"Table at ${table['offset']:04X}: {table['type']}")
```

**Method 3: Python Port (Long-term)**

**Advantages**:
- ✅ Pure Python (no external dependencies)
- ✅ Maximum performance
- ✅ Full customization

**Disadvantages**:
- ⚠️ Significant development effort
- ⚠️ Ongoing maintenance

**Priority Order**:
1. Port SIDId algorithm (player detection)
2. Port SidFreq (frequency table recognition)
3. Port PSID header parser (file format handling)

**Already Ported** (from earlier analysis):
- PSID header parser (Example 1 in Appendix B)
- SidPlayerDetector (Example 2 in Appendix B)
- SidFrequencyAnalyzer (Example 3 in Appendix B)

### 7.3 Integration Use Cases

**Use Case 1: Player Auto-Detection**

**Current SIDM2 Workflow**:
```python
# Manual player detection in laxity_parser.py
def is_laxity_player(sid_data: bytes) -> bool:
    # Hardcoded checks for Laxity signatures
    if sid_data[0x100:0x104] == b'\\x78\\xA9\\x00\\x8D':
        return True
    # ... more hardcoded checks
    return False
```

**Enhanced with JC64**:
```python
from sidm2.jc64_wrapper import JC64Wrapper

def detect_player_type(sid_file: Path) -> str:
    jc64 = JC64Wrapper("jc64.jar")
    player = jc64.identify_player(sid_file)

    if "Laxity" in player:
        return "laxity"
    elif "JCH" in player:
        return "jch"
    elif "Galway" in player:
        return "galway"
    else:
        return "unknown"

# Use in conversion pipeline
player_type = detect_player_type("music.sid")

if player_type == "laxity":
    result = convert_laxity_to_sf2(sid_file)
elif player_type == "jch":
    result = convert_jch_to_sf2(sid_file)
else:
    raise ValueError(f"Unsupported player: {player_type}")
```

**Use Case 2: Frequency Table Validation**

**Current SIDM2 Workflow**:
```python
# Manual frequency table extraction in laxity_converter.py
def extract_wave_table(sid_data: bytes) -> bytes:
    # Hardcoded offset
    WAVE_TABLE_OFFSET = 0x1ACB
    return sid_data[WAVE_TABLE_OFFSET:WAVE_TABLE_OFFSET+100]
```

**Enhanced with JC64**:
```python
from sidm2.jc64_wrapper import JC64Wrapper

def validate_frequency_tables(sid_file: Path, extracted_tables: dict) -> bool:
    jc64 = JC64Wrapper("jc64.jar")
    detected_tables = jc64.detect_frequency_tables(sid_file)

    # Cross-validate
    for detected in detected_tables:
        offset = detected['offset']
        a4_hz = detected['a4_hz_pal']

        # Check if we extracted this table
        if offset in extracted_tables:
            our_a4 = extracted_tables[offset]['a4_hz']

            # Verify match
            if abs(our_a4 - a4_hz) > 5:  # 5 Hz tolerance
                print(f"WARNING: Frequency mismatch at ${offset:04X}")
                print(f"  JC64: {a4_hz} Hz")
                print(f"  SIDM2: {our_a4} Hz")
                return False

    return True
```

**Use Case 3: Code vs Data Separation**

**Current SIDM2 Workflow**:
```python
# Manual memory layout in laxity_parser.py
PLAYER_CODE_START = 0x1000
PLAYER_CODE_END = 0x19FF
MUSIC_DATA_START = 0x1900
```

**Enhanced with JC64**:
```python
from sidm2.jc64_wrapper import JC64Wrapper

def analyze_memory_layout(sid_file: Path) -> dict:
    jc64 = JC64Wrapper("jc64.jar")
    asm_code = jc64.disassemble_sid(sid_file)

    # Parse disassembly to identify memory regions
    code_regions = []
    data_regions = []

    for line in asm_code.splitlines():
        if line.startswith("SUB_"):
            # Code subroutine
            addr = int(line[4:8], 16)
            code_regions.append(addr)
        elif line.startswith("DATA_"):
            # Data block
            addr = int(line[5:9], 16)
            data_regions.append(addr)

    return {
        'code_regions': code_regions,
        'data_regions': data_regions
    }

# Use to improve extraction accuracy
layout = analyze_memory_layout("music.sid")
print(f"Code regions: {layout['code_regions']}")
print(f"Data regions: {layout['data_regions']}")
```

**Use Case 4: Output SID Validation**

**Current SIDM2 Workflow**:
```python
# Manual validation in validate_sid_accuracy.py
def validate_conversion(original_sid: Path, converted_sf2: Path):
    # Compare SIDwinder traces
    original_trace = trace_sid(original_sid)
    exported_sid = export_sf2_to_sid(converted_sf2)
    exported_trace = trace_sid(exported_sid)

    accuracy = compare_traces(original_trace, exported_trace)
    return accuracy
```

**Enhanced with JC64**:
```python
from sidm2.jc64_wrapper import JC64Wrapper

def validate_with_jc64(original_sid: Path, exported_sid: Path) -> dict:
    jc64 = JC64Wrapper("jc64.jar")

    # Disassemble both
    original_asm = jc64.disassemble_sid(original_sid)
    exported_asm = jc64.disassemble_sid(exported_sid)

    # Compare player structures
    original_player = jc64.identify_player(original_sid)
    exported_player = jc64.identify_player(exported_sid)

    # Compare frequency tables
    original_tables = jc64.detect_frequency_tables(original_sid)
    exported_tables = jc64.detect_frequency_tables(exported_sid)

    return {
        'player_match': original_player == exported_player,
        'table_count_match': len(original_tables) == len(exported_tables),
        'disassembly_similarity': calculate_similarity(original_asm, exported_asm),
        'original_player': original_player,
        'exported_player': exported_player
    }
```

### 7.4 Recommended Implementation Phases

**Phase 1: Proof of Concept (1-2 days)**

1. **Setup JC64 Build**:
   ```bash
   git clone https://github.com/ice00/jc64.git
   cd jc64
   ant build
   ```

2. **Create Subprocess Wrapper**:
   - Implement `JC64Wrapper` class (subprocess-based)
   - Add `disassemble_sid()` method
   - Test with 3-5 Laxity SID files

3. **Validate Output**:
   - Compare JC64 disassembly with manual analysis
   - Verify accuracy of player code identification

**Phase 2: Player Detection (3-5 days)**

1. **Extract SIDId Patterns**:
   - Search JC64 source for pattern configuration
   - Create `sidid_patterns.cfg` file
   - Port Laxity NewPlayer v21 signatures

2. **Implement Player ID Wrapper**:
   - Add `identify_player()` to `JC64Wrapper`
   - Create custom Java wrapper class if needed
   - Test on 10+ known Laxity files

3. **Integrate with SIDM2**:
   - Modify `laxity_parser.py` to use JC64 detection
   - Add fallback to manual detection
   - Update validation tests

**Phase 3: Frequency Analysis (5-7 days)**

1. **Study SidFreq Algorithm**:
   - Analyze Java source code
   - Understand 12 table format variants
   - Document detection logic

2. **Implement Frequency Detection Wrapper**:
   - Add `detect_frequency_tables()` to `JC64Wrapper`
   - Parse JC64 output (JSON or structured text)
   - Extract A4 frequencies and table types

3. **Validate Extracted Tables**:
   - Cross-check with SIDM2's extracted tables
   - Identify discrepancies
   - Improve extraction accuracy

**Phase 4: Validation Integration (3-5 days)**

1. **Output SID Disassembly**:
   - Disassemble original SID with JC64
   - Disassemble exported SID with JC64
   - Compare memory layouts and structures

2. **Automated Validation**:
   - Add JC64 validation to `validate_sid_accuracy.py`
   - Generate comparison reports
   - Identify conversion anomalies

3. **Dashboard Integration**:
   - Add JC64 analysis to validation dashboard
   - Display player detection results
   - Show frequency table comparisons

**Phase 5: Python Port (Long-term, 2-3 weeks)**

1. **Port SIDId Algorithm**:
   - Translate Java pattern matching to Python
   - Create pattern database
   - Test accuracy against JC64 results

2. **Port SidFreq Algorithm**:
   - Translate frequency detection to Python
   - Implement semitone validation
   - Support all 12 table formats

3. **Optimize Performance**:
   - Profile Python implementation
   - Optimize hot paths
   - Compare speed with Java version

**Phase 6: Documentation & Maintenance (Ongoing)**

1. **User Documentation**:
   - Create JC64 integration guide
   - Document configuration options
   - Provide usage examples

2. **Developer Documentation**:
   - API reference for wrapper classes
   - Architecture diagrams
   - Integration patterns

3. **Testing & Validation**:
   - Unit tests for wrapper classes
   - Integration tests for SIDM2 pipeline
   - Regression testing for accuracy

---

## 8. Code Examples & Python Ports

See **Appendix B** for complete Python port examples:
- PSID Header Parser
- Player Detection Pattern Matcher
- Frequency Table Analyzer

---

## 9. Recommendations & Next Steps

### 9.1 Immediate Actions

**1. Build and Test JC64**:
```bash
# Clone repository
git clone https://github.com/ice00/jc64.git
cd jc64

# Build with Ant
ant build

# Test FileDasm
java -cp dist/jc64.jar sw_emulator.software.FileDasm \
     G5/Laxity/Stinsens_Last_Night_of_89.sid \
     output/stinsens_jc64.asm

# Verify output
cat output/stinsens_jc64.asm
```

**2. Create Initial Wrapper**:
```python
# sidm2/jc64_wrapper.py
import subprocess
from pathlib import Path

class JC64Wrapper:
    def __init__(self, jar_path: str):
        self.jar = Path(jar_path)

    def disassemble(self, sid_file: Path) -> str:
        output = Path(f"{sid_file}.asm")
        subprocess.run([
            "java", "-cp", str(self.jar),
            "sw_emulator.software.FileDasm",
            "-en", str(sid_file), str(output)
        ])
        return output.read_text()
```

**3. Test Integration**:
```python
# test_jc64_integration.py
from sidm2.jc64_wrapper import JC64Wrapper

jc64 = JC64Wrapper("path/to/jc64.jar")

# Test with known Laxity file
asm = jc64.disassemble("G5/Laxity/Broware.sid")

# Verify player code detected
assert "LDA #$00" in asm
assert "STA $D400" in asm
print("JC64 integration test: PASSED")
```

### 9.2 Medium-term Goals

**1. Player Auto-Detection**:
- Extract SIDId pattern database from JC64
- Integrate player detection into SIDM2 pipeline
- Auto-select converter based on detected player

**2. Frequency Table Validation**:
- Use JC64's SidFreq for cross-validation
- Improve SIDM2's table extraction accuracy
- Detect and warn about non-standard tables

**3. Memory Layout Analysis**:
- Leverage JC64's code/data separation
- Better understanding of driver structures
- Improve SF2 driver pointer patching

### 9.3 Long-term Vision

**1. Multi-Format Support**:
- Use JC64 to identify non-Laxity players
- Implement converters for JCH, Galway, MoN
- Universal SID to SF2 conversion system

**2. Cross-Platform Independence**:
- Pure Python + Java (no .exe dependencies)
- Run SIDM2 on Mac/Linux without Wine
- 100% cross-platform pipeline

**3. Advanced Analysis Tools**:
- Player code pattern library
- Data structure recognition
- Automated conversion optimization

### 9.4 Success Metrics

**Integration Success Criteria**:
- ✅ JC64 correctly identifies Laxity player in 100% of test files
- ✅ Frequency table detection matches SIDM2's extraction in 95%+ of cases
- ✅ Disassembly output provides useful validation information
- ✅ Integration adds <5% overhead to conversion time

**Validation Improvements**:
- ✅ Detect 90%+ of conversion errors automatically
- ✅ Identify frequency table mismatches
- ✅ Verify player structure preservation
- ✅ Cross-validate with independent tool

**Developer Experience**:
- ✅ Clear API documentation
- ✅ Easy-to-use wrapper classes
- ✅ Comprehensive error handling
- ✅ Debugging support

---

## Conclusion

JC64dis provides a **comprehensive, battle-tested SID file handling framework** with strong capabilities in:

✅ **PSID/RSID/MUS Format Support** - Complete header parsing and metadata extraction
✅ **Player Detection** - SIDId V1.09 algorithm with 80+ signatures
✅ **Frequency Analysis** - 12 table format variants with PAL/NTSC support
✅ **Code/Data Separation** - Block-based memory management
✅ **SID Emulation** - Full 6581/8580 chip emulation with ADSR and filter
✅ **Multi-Format Output** - 8 assembler syntaxes
✅ **Cross-Platform** - Java-based, runs on Windows/Mac/Linux

**Integration Value for SIDM2**: **HIGH**

**Recommended Approach**:
1. **Short-term**: Subprocess wrapper for quick integration
2. **Medium-term**: Player detection and frequency validation
3. **Long-term**: Python port of key algorithms

**Key Benefits**:
- Auto-detect Laxity and other players
- Validate frequency table extraction
- Improve conversion accuracy
- Independent validation reference
- Cross-platform compatibility

**Next Steps**:
1. Build JC64 from source
2. Create subprocess wrapper
3. Test with Laxity SID files
4. Integrate player detection
5. Add frequency validation
6. Document integration

This integration will significantly enhance SIDM2's capabilities, providing intelligent player detection, robust validation, and a foundation for supporting additional SID music formats beyond Laxity NewPlayer v21.

---

**Document End**
