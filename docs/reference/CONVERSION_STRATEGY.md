# Laxity to SF2 Conversion Strategy

This document describes the strategy for converting Laxity NewPlayer v21 SID files to SID Factory II (.sf2) format.

## Overview

### The Challenge

Converting SID files to SF2 format is fundamentally **reverse engineering compiled data**:

1. SID files contain machine code + encoded data (not source)
2. The original editable structure is lost during compilation
3. Player-specific encoding varies significantly
4. SF2 format is tightly coupled to specific driver versions

### Target Format

We convert to **SID Factory II Driver 11** because:
- It's the default "luxury" driver with full features
- Has separate tables for wave, pulse, filter, arp
- Supports 12-bit pulse and filter control
- Most similar feature set to Laxity NewPlayer

### SF2 Editor Converter Architecture

From the SF2 source code, the editor uses a converter framework:

```cpp
class ConverterBase {
    virtual void Convert(
        const vector<unsigned char>& sourceData,
        SF2::Interface* sf2Interface
    ) = 0;
}
```

Available converters:
- `ConverterMod` - MOD files (4→3 channel)
- `ConverterGT` - GoatTracker .sng files
- `ConverterJCH` - CheeseCutter .ct files

Our converter follows similar patterns but works externally.

## Source Format: Laxity NewPlayer v21

### Memory Layout

```
$1000-$10FF  Player init code
$1100-$17FF  Player play code
$1800-$1FFF  Music data tables
$2000+       Sequence data
```

### Instrument Format (8 bytes)

*From JCH NewPlayer v21.g5 Final documentation*

| Byte | Description | Notes |
|------|-------------|-------|
| 0 | AD (Attack/Decay) | Direct SID register |
| 1 | SR (Sustain/Release) | Direct SID register |
| 2 | Restart options / Wave speed | See restart flags below |
| 3 | Filter setting | Lo nibble: pass band, Hi nibble: resonance |
| 4 | Filter table pointer | 0 = use filter setting directly, else pointer |
| 5 | Pulse table pointer | **Y*4 indexed** (entry 6 = $18) |
| 6 | Pulse property | Bit 0: pulse only on instrument, Bit 1: filter only on instrument |
| 7 | Wave table pointer | Index to wave table |

#### Restart Options (Byte 2)

| Value | Description |
|-------|-------------|
| Low nibble | Wave count speed |
| $8x | Hard restart (fixed) |
| $4x | Soft restart (gate off only, no silence) |
| $Ax/$Bx | Laxity hard restart (requires bit 7 set) - AD not touched during HR |
| $1x | Wave generator reset enable |
| $00 | Gate off 3 frames before next note, silent gate on on 3rd frame |

**Note**: $8x & $1x can be combined. $4x cannot be combined with other settings.

#### Pulse Property (Byte 6)

| Bit | Description |
|-----|-------------|
| 0 | Pulse table only reset on instrument set, not on note events |
| 1 | Filter table only reset on instrument set, not on note events |

### Key Data Structures

**Wave Table** (2 bytes/entry):
- Byte 0: Note offset ($80+ = absolute, $7F = jump, $7E = stop)
- Byte 1: Waveform

**Pulse Table** (4 bytes/entry, Y*4 indexed):
- Byte 0: Initial pulse value
- Byte 1: Add/subtract delta
- Byte 2: Duration + direction bit
- Byte 3: Next entry (Y*4 index)

**Filter Table** (4 bytes/entry):
- Byte 0: Filter value ($FF = keep current)
- Byte 1: Count value
- Byte 2: Duration
- Byte 3: Next entry (absolute index)

**Note**: First entry (4 bytes) is used for alternative speed (break speeds).

### Super Commands (Complete Reference)

*From JCH NewPlayer v21.g5 Final - (D) = Direct command, lasts until next note*

| Command | Parameters | Description |
|---------|------------|-------------|
| $0x yy | (D) | Slide up speed $xyy |
| $1? ?? | | Free |
| $2x yy | (D) | Slide down speed $xyy |
| $3? ?? | | Free |
| $4x yy | | Invoke instrument x with alternative wave table pointer yy |
| $60 xy | (D) | Vibrato, x=frequency, y=amplitude |
| $7? ?? | | Free |
| $8x xx | | Portamento, speed $xxx |
| $9x yy | | Set D=x and SR=yy (persistent until instrument change) |
| $ax yy | (D) | Set D=x and SR=yy directly (until next note) |
| $b? ?? | | Free |
| $c0 xx | (D) | Set channel wave pointer directly to xx |
| $dx yy | (D) | x=0: filter ptr=yy, x=1: filter value=yy, x=2: pulse ptr=yy |
| $e0 xx | | Set speed to xx |
| $f0 xx | | Set master volume |

### Speed System

Speeds below $02 use alternative speed lookup in filter table's first entry (break speeds).

- Speed lookup table: max 4 entries, wraps automatically
- Write $00 as wrap mark for shorter tables (e.g., `$06 $04 $00`)
- Speeds of $01 in table are clamped to $02 to prevent crashes

### Vibrato and Slide Special Cases

**Important**: Vibrato and slides only apply to wave table entries with note offset = $00.

The special value $80 in wave table:
- Recalculates base note + transpose
- Does NOT overwrite internally stored frequency
- Enables "Hubbard slide" effect

Example Hubbard slide:
```
00 - $00 $21  ; Note offset 0, saw
01 - $80 $21  ; Recalc base, saw
02 - $7f $00  ; Loop
```
Apply a slide command to get the classic Hubbard slide effect.

---

## Target Format: SF2 Driver 11

### Instrument Format (6 bytes, column-major)

| Column | Description |
|--------|-------------|
| 0 | AD |
| 1 | SR |
| 2 | Flags ($80=HR, $40=filter, etc.) |
| 3 | Filter table index |
| 4 | Pulse table index |
| 5 | Wave table index |

### Table Formats

**Wave Table**: (waveform, note) - swapped from Laxity!
**Pulse Table**: Direct indices (not Y*4)
**Filter Table**: Direct indices

---

## Mapping Strategy

### 1. ADSR Mapping

**Direct copy** - Both formats use standard SID ADSR values.

```python
sf2_ad = laxity_ad  # Column 0
sf2_sr = laxity_sr  # Column 1
```

### 2. Flags Conversion

Convert Laxity restart options to SF2 flags:

| Laxity Byte 2 | SF2 Flags | Description |
|---------------|-----------|-------------|
| $8x | $80 | Hard restart (fixed) |
| $4x | $00 | Soft restart |
| $Ax/$Bx | $80 | Laxity HR (requires bit 7) |
| $1x | $10 | Oscillator reset |

```python
sf2_flags = 0
if laxity_restart & 0x80:
    sf2_flags |= 0x80  # Hard restart
if laxity_restart & 0x10:
    sf2_flags |= 0x10  # Osc reset
# Add filter flags based on filter_ptr != 0
if laxity_filter_ptr:
    sf2_flags |= 0x40  # Filter on
```

### 3. Wave Table Mapping

**Critical**: Byte order is swapped!

| Laxity | SF2 | Notes |
|--------|-----|-------|
| (note, waveform) | (waveform, note) | Swap bytes |
| $7F in byte 0 | $7F in byte 0 | Jump command (same position) |
| $7E in byte 0 | N/A | Convert to $7F jump |

```python
def convert_wave_entry(laxity_note, laxity_waveform):
    if laxity_note == 0x7F:
        # Jump command - target is in waveform byte
        return (0x7F, laxity_waveform)
    else:
        # Normal entry - swap order
        return (laxity_waveform, laxity_note)
```

### 4. Pulse Table Index Mapping

**Critical**: Laxity uses Y*4 indices, SF2 uses direct indices.

```python
def convert_pulse_index(laxity_index):
    return laxity_index // 4
```

Apply to:
- Instrument pulse_ptr field
- Pulse table "next entry" field (byte 3)

### 5. Filter Table Mapping

Direct index copy (no Y*4 conversion needed).

### 6. Sequence Mapping

#### Note Encoding

| Laxity | SF2 | Description |
|--------|-----|-------------|
| $00-$5F | $00-$5D | Note values |
| Rest values | $7E | Gate on (+++) |
| End marker | $7F | Sequence end |

#### Gate System Translation

Laxity uses implicit gate handling; SF2 uses explicit `+++` and `---`:

```python
def add_gate_events(sequence):
    """Insert +++ to sustain notes, --- for release."""
    result = []
    for event in sequence:
        result.append(event)
        if is_note(event):
            # Add sustain frames based on duration
            for _ in range(event.duration - 1):
                result.append(GateOnEvent())
    return result
```

#### Instrument/Command Encoding

```python
sf2_instrument = 0x80 if no_change else (laxity_instr + 0xA0)
sf2_command = 0x80 if no_change else (laxity_cmd + 0xC0)
```

### 7. Order List Mapping

Format is similar: transpose + sequence number.

| Laxity | SF2 | Description |
|--------|-----|-------------|
| $A0 YY | $A0 YY | No transpose |
| $94 YY | $94 YY | -12 semitones |
| $AC YY | $AC YY | +12 semitones |

---

## Conversion Pipeline

### Step 1: Parse SID Header

```python
parser = SIDParser(sid_data)
header = parser.parse_header()
c64_memory = parser.load_c64_data()
```

### Step 2: Identify Player

```python
player_id = identify_player(c64_memory)
if player_id != "Laxity NewPlayer v21":
    raise UnsupportedPlayerError()
```

### Step 3: Locate Tables

Search for known patterns to find table addresses:

```python
instr_addr = find_instrument_table(c64_memory)
wave_addr = find_wave_table(c64_memory)
pulse_addr = find_pulse_table(c64_memory)
filter_addr = find_filter_table(c64_memory)
seq_addrs = find_sequences(c64_memory)
```

### Bytecode Patterns for Table Discovery

From the Laxity player disassembly (`docs/LAXITY_PLAYER_ANALYSIS.md`), these 6502 patterns help find tables:

**Instrument Table Access Pattern:**
```assembly
; Pattern: LDA table,Y followed by STA state,X
lda  W1A6B,y        ; $B9 $6B $1A - LDA absolute,Y
sta  W193A,x        ; $9D $3A $19 - STA absolute,X
```
Search for: `$B9` followed by `$9D` with state array addresses in $19xx range.

**Sequence Pointer Pattern:**
```assembly
; Pattern: LDA from pointer table, store to state
lda  W199F,y        ; Pointer table
sta  W1901,x        ; Current position lo
```

**Wave Table Loop Check:**
```assembly
; Pattern: CMP #$7E or CMP #$7F
cmp  #$7E           ; $C9 $7E - Loop marker check
cmp  #$7F           ; $C9 $7F - Jump marker check
```

**Filter Register Write:**
```assembly
; Pattern: STA to SID filter registers
sta  $D416          ; $8D $16 $D4 - Filter cutoff hi
sta  $D417          ; $8D $17 $D4 - Filter routing
sta  $D418          ; $8D $18 $D4 - Volume/mode
```

These patterns help validate that extracted addresses are correct by checking the player code references them.

### Step 4: Extract and Convert Tables

```python
instruments = extract_instruments(c64_memory, instr_addr)
sf2_instruments = [convert_instrument(i) for i in instruments]

wave_table = extract_wave_table(c64_memory, wave_addr)
sf2_wave = [convert_wave_entry(w) for w in wave_table]

# ... similar for pulse, filter
```

### Step 5: Extract Sequences

```python
sequences = []
for addr in seq_addrs:
    seq = extract_sequence(c64_memory, addr)
    sf2_seq = convert_sequence(seq)
    sequences.append(sf2_seq)
```

### Step 6: Build SF2 File

```python
writer = SF2Writer(driver="driver11")
writer.set_instruments(sf2_instruments)
writer.set_wave_table(sf2_wave)
writer.set_pulse_table(sf2_pulse)
writer.set_filter_table(sf2_filter)
writer.set_sequences(sequences)
writer.write(output_path)
```

---

## Known Limitations

### 1. Tables Using Defaults

Some tables can't be reliably extracted:

| Table | Status | Fallback |
|-------|--------|----------|
| Init | Not in Laxity | Use defaults (tempo 0, vol $0F) |
| Arp | Embedded in wave | Default patterns |
| HR | Often hardcoded | Default $0F 00 |

### 2. Information Loss

Laxity compilation discards:
- Instrument names
- Sequence descriptions
- Bookmarks
- Song metadata (partially recoverable from SID header)

### 3. Command Mapping

Not all Laxity super commands map cleanly to SF2:

| Laxity | SF2 Support |
|--------|-------------|
| Slide up/down | Full |
| Vibrato | Full |
| Portamento | Full |
| Alt wave ptr ($4x) | Partial |
| Direct filter ($Dx) | Limited |

### 4. Multi-Speed Tunes

Songs with multiple play calls per frame require special handling - tempo detection may not be accurate.

---

## Validation Checklist

After conversion, verify:

### Structural Integrity

- [ ] All instruments have valid table pointers
- [ ] Wave table entries have valid jumps (no orphans)
- [ ] Pulse table "next" indices are within bounds
- [ ] Filter table entries form valid chains
- [ ] All sequences terminate with $7F

### Cross-Reference Validation

- [ ] Every instrument's wave_ptr points to valid wave entry
- [ ] Every instrument's pulse_ptr points to valid pulse entry
- [ ] Every sequence instrument number exists in instrument table
- [ ] Every sequence command number exists in command table

### Playback Comparison

- [ ] Compare siddump output: original vs converted
- [ ] Verify ADSR values match at note triggers
- [ ] Check waveform changes occur at correct times
- [ ] Validate pulse width modulation patterns

---

## Common Issues and Solutions

### Issue: Wave Table Points to Wrong Entry

**Symptom**: Wrong sounds, or no sound
**Cause**: Incorrect wave table pointer conversion
**Solution**: Verify byte swap (waveform, note) order

### Issue: Pulse Not Modulating

**Symptom**: Static pulse width
**Cause**: Pulse indices not divided by 4
**Solution**: Convert Y*4 indices to direct indices

### Issue: Notes Cut Off Early

**Symptom**: Staccato when should sustain
**Cause**: Missing +++ gate events
**Solution**: Add proper gate sustain events

### Issue: Instruments Sound Different

**Symptom**: Tone quality doesn't match
**Cause**: Incorrect flags conversion
**Solution**: Verify hard restart and filter flags

### Issue: Song Plays at Wrong Speed

**Symptom**: Too fast or slow
**Cause**: Incorrect tempo extraction
**Solution**: Extract speed from player data or siddump timing

---

## Future Improvements

### Enhanced Extraction

1. **Better table scoring** - Improve heuristics for finding correct tables
2. **Command parameter extraction** - Extract slide/vibrato values
3. **Tempo detection** - Analyze frame timing from siddump

### Additional Player Support

1. **JCH NewPlayer** - Similar to Laxity
2. **GoatTracker** - Different sequence format
3. **DMC** - Demo Music Creator player

### Output Quality

1. **Instrument naming** - Heuristics based on ADSR/waveform
2. **Sequence optimization** - Remove redundant events
3. **Loop detection** - Identify and mark loop points

---

## SF2 Editor Conversion Insights

### MOD Converter Approach

From the SF2 source code (`converter_mod.cpp`):

1. **Channel reduction**: 4 MOD channels → 3 SID voices with user selection
2. **Tempo extraction**: First tempo command sets SF2 tempo value
3. **Default instruments**: Triangle waveform with standard ADSR
4. **Effect mapping**: MOD effects map to SF2 commands where possible

### Sequence Packing

The SF2 editor uses persistence encoding:

```cpp
// If instrument/command same as previous, write 0x80 instead
// This saves space in sequences

lastInstr = 0x80
for each event:
    if event.instrument == lastInstr:
        write(0x80)  // "no change" marker
    else:
        write(event.instrument)
        lastInstr = event.instrument
```

### Table Layout Considerations

SF2 Driver 11 uses **column-major** storage for instruments:
- All AD values first, then all SR values, etc.
- This differs from Laxity's row-major format
- Conversion must transpose the data

```cpp
// Laxity: row-major (instrument 0 bytes 0-7, then instrument 1, etc.)
// SF2: column-major (all byte 0s, then all byte 1s, etc.)

for col in range(6):
    for row in range(32):
        sf2_data[col * 32 + row] = laxity_data[row * 8 + col]
```

---

## References

- [SF2 Format Specification](SF2_FORMAT_SPEC.md)
- [Source Code Analysis](SF2_SOURCE_ANALYSIS.md)
- [SID Registers Reference](sid-registers.md)
- [Format Specifications](format-specification.md)
- [SID Factory II User Manual](https://sidfactory2.com/)
