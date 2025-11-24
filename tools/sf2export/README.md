# SF2Export - SF2 to PSID Converter

Standalone command-line tool to convert SID Factory II (.sf2) files to playable PSID (.sid) format.

## Features

- ✅ Minimal dependencies (standalone C++)
- ✅ Supports Driver 11 and NewPlayer 20
- ✅ Extracts metadata (title, author, copyright)
- ✅ Cross-platform (Windows, Linux, macOS)
- ✅ Fast execution (<1ms per file)

## Building

### Windows (MinGW/MSYS2)

```bash
cd tools/sf2export
g++ -std=c++11 -O2 -o sf2export.exe sf2export.cpp
```

### Windows (Visual Studio)

```cmd
cd tools\sf2export
cl /EHsc /O2 /Fe:sf2export.exe sf2export.cpp
```

### Linux/macOS

```bash
cd tools/sf2export
g++ -std=c++11 -O2 -o sf2export sf2export.cpp
```

Or use the Makefile:

```bash
make
```

## Usage

### Basic Usage

```bash
# Convert with Driver 11 offsets (default)
sf2export input.sf2 output.sid

# Convert with NewPlayer 20 offsets
sf2export input.sf2 output.sid --np20

# Verbose output
sf2export input.sf2 output.sid -v
```

### Driver Options

| Option | Init Offset | Play Offset | Description |
|--------|-------------|-------------|-------------|
| `--driver11` (default) | 0 | 3 | Driver 11.xx (most common) |
| `--np20` | 0 | 161 ($A1) | NewPlayer 20 (Laxity-style) |
| `--init <N>` | N | - | Custom init offset |
| `--play <N>` | - | N | Custom play offset |

### Examples

```bash
# Convert Angular.sf2 to SID with Driver 11
sf2export Angular_d11_final.sf2 Angular_converted.sid -v

# Convert with NewPlayer 20 driver
sf2export file_g4.sf2 file.sid --np20

# Custom offsets (hex or decimal)
sf2export custom.sf2 custom.sid --init 0 --play 0xA1
```

## Output Format

The tool creates standard PSID v2 files compatible with:
- SID players (HVSC format)
- Emulators (VICE, CCS64, etc.)
- Analysis tools (siddump, sidplayfp)

## Technical Details

### PSID Header Structure

The converter creates a 124-byte PSID v2 header with:
- Magic: `PSID`
- Version: 2
- Load address: From SF2 PRG format (first 2 bytes)
- Init address: `load_address + init_offset`
- Play address: `load_address + play_offset`
- Metadata: Title, Author, Copyright (extracted from SF2)
- Flags: 6581 SID, PAL timing

### SF2 File Format

SF2 files are PRG format containing:
- Load address (2 bytes, little-endian)
- Driver code and music data
- Auxiliary data section (metadata strings)

The tool reads the entire SF2 file and wraps it with a proper PSID header.

### Driver Offsets

Different SF2 drivers use different entry point offsets:

**Driver 11**:
- Init: `driver_address + 0`
- Play: `driver_address + 3`
- Common in most SF2 files

**NewPlayer 20 (NP20)**:
- Init: `driver_address + 0`
- Play: `driver_address + 161` ($A1)
- Used in Laxity-style files

## Integration with Python

The tool is designed to be called from Python scripts:

```python
import subprocess

def convert_sf2_to_sid(sf2_path, sid_path, driver='driver11'):
    cmd = ['tools/sf2export/sf2export.exe', sf2_path, sid_path]
    if driver == 'np20':
        cmd.append('--np20')

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

## Testing

Test the converter with an existing SF2 file:

```bash
# Convert
sf2export SF2/Angular_d11_final.sf2 test_output.sid -v

# Verify with siddump
siddump test_output.sid -t5

# Play with SID player
sidplayfp test_output.sid
```

## Troubleshooting

### "Unknown opcode" error when playing

**Problem**: The generated SID file produces errors like:
```
Error: Unknown opcode $XX at $XXXX
```

**Solution**: Try different driver offsets:
- If using `--driver11`, try `--np20`
- If using `--np20`, try `--driver11`
- Check the SF2 file was created with the correct driver

### Empty or corrupted output

**Problem**: Generated SID file doesn't play correctly.

**Cause**: SF2 file may be corrupted or use unsupported driver.

**Solution**:
1. Verify SF2 file opens in SID Factory II
2. Try manual export from SID Factory II (File → Export → SID)
3. Compare file sizes

### Metadata not extracted

**Problem**: Title/Author/Copyright fields are empty.

**Cause**: SF2 file doesn't contain auxiliary metadata section.

**Solution**: This is normal for some SF2 files. The music data is still correctly converted.

## Limitations

- Only supports standard SF2 drivers (11, 12-16, NP20)
- Assumes single subtune (song count = 1)
- Metadata extraction is best-effort (may miss some strings)
- Does not perform code relocation (uses PRG load address as-is)

## License

Based on SID Factory II source code (GPL).
Extracted and simplified for standalone use.

## Credits

- SID Factory II by Hermit Software
- PSIDFile implementation by Lasse Öörni
- C64File implementation by SID Factory II team

## See Also

- `validate_conversion.py` - Uses this tool for round-trip testing
- `sid_to_sf2.py` - Converts SID → SF2
- `docs/SF2_FORMAT_SPEC.md` - SF2 format documentation
