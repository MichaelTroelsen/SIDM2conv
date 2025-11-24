# SID to SF2 Validation Tool

## Overview

The `validate_conversion.py` script provides automated quality validation for SID to SF2 conversions. It analyzes the original SID file, performs the conversion, and generates detailed reports comparing the extracted data against the actual runtime behavior.

## Features

1. **Siddump Analysis** - Extracts actual ADSR values and waveforms used during playback
2. **Automated Conversion** - Converts SID to SF2 using the main converter
3. **WAV Rendering** - Creates reference WAV file from original SID
4. **Data Comparison** - Compares extracted vs. actual instrument data
5. **HTML Reports** - Generates detailed validation reports with statistics

## Usage

### Basic Usage

```bash
python validate_conversion.py SID/Angular.sid
```

### With Options

```bash
python validate_conversion.py SID/Angular.sid --duration 30 --verbose
python validate_conversion.py SID/Angular.sid -o custom_output -t 60
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `sid_file` | Input SID file to validate | (required) |
| `--output-dir`, `-o` | Output directory for generated files | `validation_output` |
| `--duration`, `-t` | Playback duration in seconds | `30` |
| `--verbose`, `-v` | Enable verbose/debug output | `false` |

## Output Files

The validation script generates the following files in the output directory:

| File | Description |
|------|-------------|
| `{name}_validated.sf2` | Generated SF2 file (can be opened in SID Factory II) |
| `{name}_reference.wav` | Reference WAV file from original SID (16-bit stereo, 44.1kHz) |
| `{name}_validation_report.html` | Detailed HTML report with statistics and comparisons |

## Validation Process

The script follows a 7-step validation process:

### Step 1: Siddump Analysis

Uses `tools/siddump.exe` to analyze the original SID file during playback:
- Extracts unique ADSR values actually used
- Identifies waveforms used (triangle, pulse, sawtooth, noise)
- Determines pulse width range
- Records runtime behavior

### Step 2: SID File Parsing

Parses the SID file structure:
- Reads PSID/RSID header
- Extracts C64 memory data
- Identifies load address and data size

### Step 3: Music Data Extraction

Extracts music data using Laxity analyzer:
- Sequences (note patterns)
- Instruments (ADSR, table pointers)
- Wave/Pulse/Filter tables
- Tempo and tempo
- Orderlists

### Step 4: SF2 Generation

Generates the SF2 file using Driver 11 format:
- Injects extracted sequences
- Converts instruments from Laxity to SF2 format
- Writes wave, pulse, filter tables
- Configures tempo and other settings

### Step 5: WAV Rendering

Renders the original SID file to WAV using `tools/SID2WAV.EXE`:
- 16-bit stereo
- 44.1kHz sample rate
- Specified duration (default 30 seconds)

### Step 6: Data Comparison

Compares extracted data against siddump analysis:
- **ADSR Matching** - Checks if extracted instruments match runtime ADSR values
- **Waveform Matching** - Verifies waveforms are correctly extracted
- **Tempo Validation** - Confirms tempo value is correct

### Step 7: Report Generation

Creates an HTML report with:
- SID file information
- Extracted data summary
- Siddump analysis results (actual runtime behavior)
- Comparison statistics
- Extracted instruments table
- Issues and warnings

## HTML Report

The generated HTML report includes:

### SID File Information
- Format (PSID/RSID version)
- Title, Author, Copyright
- Load address and size

### Extracted Data Summary
- Number of sequences, instruments, tables
- Tempo value
- Total data extracted

### Siddump Analysis
- **ADSR Values Table** - Shows all unique ADSR combinations found during playback
- **Waveforms Table** - Lists waveforms used with binary representation and descriptions
- **Pulse Width Range** - Min/max pulse values observed

### Extraction Quality
- **ADSR Matching** - How many extracted ADSR values match actual runtime
- **Waveform Matching** - How many waveforms match
- **Issues List** - Missing or extra values

### Extracted Instruments Table
Shows the instrument table structure:
- Index (0-15)
- AD (Attack/Decay)
- SR (Sustain/Release)
- Restart flags
- Filter, Pulse, Wave pointers

### Testing Instructions
Step-by-step guide for manual validation in SID Factory II

## Example Output

```
============================================================
SID to SF2 Conversion Validation
============================================================
Original SID: SID/Angular.sid

Step 1: Analyzing original SID with siddump...
  Found 9 unique ADSR values
  Found 13 unique waveforms
  Pulse width range: $340 - $910

Step 2: Parsing SID file structure...
  Format: PSID v2
  Name: Angular
  Author: Thomas Mogensen (DRAX)
  Load: $1000, Size: 3781 bytes

Step 3: Extracting music data from SID...
  Sequences: 14
  Instruments: 4
  Wave entries: 58
  Pulse entries: 64
  Filter entries: 52
  Tempo: 3

Step 4: Generating SF2 file...
  Created: validation_output\Angular_validated.sf2 (39,960 bytes)

Step 5: Rendering original SID to WAV...
  Created: validation_output\Angular_reference.wav (1,764,044 bytes)

Step 6: Comparing extracted vs. actual data...
  ADSR: 0/9 matching
  Waveforms: 3/13 matching
  Tempo: 3 frames/row

Step 7: Generating HTML report...
  Report: validation_output\Angular_validation_report.html

============================================================
Validation complete!
============================================================
```

## Interpreting Results

### ADSR Matching

- **High match rate (80%+)**: Instruments are correctly extracted
- **Medium match rate (40-80%)**: Some instruments may need manual adjustment
- **Low match rate (<40%)**: Instrument extraction has significant issues

**Why mismatches occur:**
- Laxity instrument format differs from siddump observations
- Hard restart instruments use different ADSR during init
- Not all instruments may be used during playback

### Waveform Matching

- **High match rate (80%+)**: Wave table correctly extracted
- **Missing waveforms**: Some waveforms in SID not extracted to wave table
- **Extra waveforms**: Extracted more waveforms than actually used

### Tempo

Should always match exactly. If tempo is incorrect, it indicates a bug in tempo extraction.

## Limitations

1. **No SF2 Playback Validation** - Script doesn't automatically play SF2 and compare audio
2. **Manual Testing Required** - Final validation requires loading SF2 in SID Factory II
3. **No Round-Trip Testing** - Doesn't convert SF2 back to SID for comparison
4. **Laxity Format Only** - Only works with Laxity NewPlayer v21 SID files

## Future Enhancements

Potential improvements discussed but not yet implemented:

1. **SF2 to SID Export** - Automate SIDFactoryII to export SF2 back to SID
2. **Full Round-Trip Testing** - Compare original SID → SF2 → SID → WAV
3. **Register-Level Comparison** - Compare SID register writes between original and converted
4. **Audio Waveform Analysis** - Numerical comparison of WAV files
5. **Batch Validation** - Test multiple SID files and generate summary report

## Tools Used

- **siddump.exe** (`tools/`) - 6502 CPU emulator for SID playback analysis
- **SID2WAV.EXE** (`tools/`) - SID to WAV renderer
- **sidm2 package** - Python modules for SID parsing and SF2 generation

## Example Workflow

```bash
# 1. Validate conversion of Angular.sid
python validate_conversion.py SID/Angular.sid -t 30

# 2. Open validation_output/Angular_validation_report.html in browser
# 3. Review ADSR and waveform matching statistics
# 4. Open validation_output/Angular_validated.sf2 in SID Factory II
# 5. Play the song and compare to validation_output/Angular_reference.wav
# 6. If issues found, investigate using the HTML report

# 7. Validate all SID files
for file in SID/*.sid; do
    python validate_conversion.py "$file" -t 30
done
```

## Related Documentation

- [SF2_FORMAT_SPEC.md](SF2_FORMAT_SPEC.md) - Complete SF2 format specification
- [CONVERSION_STRATEGY.md](CONVERSION_STRATEGY.md) - Laxity to SF2 mapping strategy
- [AUDIO_QUALITY_ANALYSIS.md](AUDIO_QUALITY_ANALYSIS.md) - Audio quality issues analysis
- [SIDDUMP_ANALYSIS.md](SIDDUMP_ANALYSIS.md) - Siddump tool source code analysis
