# SF2 File Format Deep-Dive Analysis

**Source Analysis**: SID Factory II Editor v2023-09-30
**Analyzed Files**: `sf2_interface.cpp/h`, `driver_info.cpp/h`, `datasource_sequence.cpp/h`, `datasource_orderlist.h`, `driver_utils.cpp/h`, `screen_edit_utils.cpp/h`, `c64file.cpp/h`
**Date**: 2025-12-10

---

## Table of Contents

1. [SF2 File Structure](#1-sf2-file-structure)
2. [Sequence Format](#2-sequence-format)
3. [Orderlist Format](#3-orderlist-format)
4. [Critical Constraints](#4-critical-constraints)
5. [Loading and Validation](#5-loading-and-validation)
6. [Memory Layout](#6-memory-layout)
7. [Common Crash Causes](#7-common-crash-causes)

---

## 1. SF2 File Structure

### File Identification

SF2 files are identified by a **magic number** at the top address:

```cpp
static const unsigned short ExpectedFileIDNumber = 0x1337;
static const unsigned short AuxilaryDataPointerAddress = 0x0ffb;

// Parse() in driver_info.cpp line 33:
unsigned short top_address = inFile.GetTopAddress();
if (inFile.GetWord(top_address) == ExpectedFileIDNumber)
{
    m_TopAddress = top_address;
    // File is valid
}
```

**Critical**: The first two bytes at the PRG load address MUST be `0x37 0x13` (little-endian `0x1337`).

### Header Block System

SF2 files use a **block-based header system**. After the magic number (`0x1337`), blocks follow this format:

```
Offset  Size  Description
------  ----  -----------
0x00    1     Block ID (see HeaderBlockID enum)
0x01    1     Block size (N bytes)
0x02    N     Block data
```

Block parsing continues until **Block ID `0xFF`** (end marker) is found.

#### Required Header Blocks

From `driver_info.cpp` line 152-162:

```cpp
bool HasParsedRequiredBlocks() const
{
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_Descriptor))       return false;  // Block 1
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_DriverCommon))     return false;  // Block 2
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_DriverTables))     return false;  // Block 3
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_DriverInstrumentDescriptor)) return false; // Block 4
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_MusicData))        return false;  // Block 5
    return true;
}
```

**Note**: Blocks 6-9 (TableColorRules, TableInsertDeleteRules, TableActionRules, DriverInstrumentDataDescriptor) are **optional**.

### Block 1: Descriptor (ID_Descriptor = 1)

Parsed in `driver_info.cpp` line 296-318:

```cpp
struct Descriptor
{
    unsigned char m_DriverType;           // Driver type identifier
    unsigned short m_DriverSize;          // Total driver size
    std::string m_DriverName;             // Null-terminated driver name
    unsigned short m_DriverCodeTop;       // Start of driver code
    unsigned short m_DriverCodeSize;      // Driver code size
    unsigned char m_DriverVersionMajor;   // Major version (e.g., 11)
    unsigned char m_DriverVersionMinor;   // Minor version (e.g., 02)
    unsigned char m_DriverVersionRevision;// Revision (optional, 0 if not present)
};
```

### Block 2: DriverCommon (ID_DriverCommon = 2)

Parsed in `driver_info.cpp` line 321-344:

```cpp
struct DriverCommon
{
    unsigned short m_InitAddress;                         // Init routine entry point
    unsigned short m_StopAddress;                         // Stop routine entry point
    unsigned short m_UpdateAddress;                       // Play/update routine entry point
    unsigned short m_SIDChannelOffsetAddress;             // SID channel offset table
    unsigned short m_DriverStateAddress;                  // Driver state byte
    unsigned short m_TickCounterAddress;                  // Tick counter
    unsigned short m_OrderListIndexAddress;               // Current orderlist index (per track)
    unsigned short m_SequenceIndexAddress;                // Current sequence position (per track)
    unsigned short m_SequenceInUseAddress;                // Sequence in use flag
    unsigned short m_CurrentSequenceAddress;              // Current sequence number
    unsigned short m_CurrentTransposeAddress;             // Current transpose value
    unsigned short m_CurrentSequenceEventDurationAddress; // Current event duration
    unsigned short m_NextInstrumentAddress;               // Next instrument to apply
    unsigned short m_NextCommandAddress;                  // Next command to apply
    unsigned short m_NextNoteAddress;                     // Next note to play
    unsigned short m_NextNoteIsTiedAddress;               // Tie note flag
    unsigned short m_TempoCounterAddress;                 // Tempo counter
    unsigned short m_TriggerSyncAddress;                  // Trigger sync byte
    unsigned char m_NoteEventTriggerSyncValue;            // Sync value for note events
    unsigned char m_ReservedByte;                         // Reserved
    unsigned short m_ReservedWord;                        // Reserved
};
```

### Block 3: DriverTables (ID_DriverTables = 3)

Parsed in `driver_info.cpp` line 347-387:

```cpp
struct TableDefinition
{
    unsigned char m_Type;                  // 0x00=Generic, 0x80=Instruments, 0x81=Commands
    unsigned char m_ID;                    // Table identifier
    unsigned char m_TextFieldSize;         // Description field size
    std::string m_Name;                    // Table name (null-terminated)

    enum DataLayout : unsigned char {
        RowMajor = 0,                      // Data organized by rows
        ColumnMajor = 1                    // Data organized by columns
    } m_DataLayout;

    bool m_PropertyEnabledInsertDelete;    // Allow insert/delete operations
    bool m_PropertyLayoutVertically;       // Layout vertically in editor
    bool m_PropertyIndexAsContinuousMemory;// Index as continuous memory block

    unsigned char m_InsertDeleteRuleID;    // Insert/delete rule ID
    unsigned char m_EnterActionRuleID;     // Action rule on Enter key
    unsigned char m_ColorRuleID;           // Color rule ID

    unsigned short m_Address;              // Memory address of table data
    unsigned short m_ColumnCount;          // Number of columns
    unsigned short m_RowCount;             // Number of rows

    unsigned char m_VisibleRowCount;       // Visible rows in editor
};
```

**Important**: Table definitions continue until **byte `0xFF`** is found.

### Block 4: DriverInstrumentDescriptor (ID_DriverInstrumentDescriptor = 4)

Parsed in `driver_info.cpp` line 390-399:

```cpp
struct InstrumentDescriptor
{
    std::vector<std::string> m_CellDescription;  // Description for each cell in instrument table
};
```

Format:
- 1 byte: descriptor count (N)
- N null-terminated strings

### Block 5: MusicData (ID_MusicData = 5) - **CRITICAL**

Parsed in `driver_info.cpp` line 402-422:

```cpp
struct MusicData
{
    unsigned char m_TrackCount;                       // Number of tracks (usually 3)
    unsigned short m_TrackOrderListPointersLowAddress;  // Low byte pointers to orderlists
    unsigned short m_TrackOrderListPointersHighAddress; // High byte pointers to orderlists

    unsigned char m_SequenceCount;                    // Total sequence slots (usually 128)
    unsigned short m_SequencePointersLowAddress;      // Low byte pointers to sequences
    unsigned short m_SequencePointersHighAddress;     // High byte pointers to sequences

    unsigned short m_OrderListSize;                   // Size of each orderlist (usually 256)
    unsigned short m_OrderListTrack1Address;          // Address of first orderlist

    unsigned short m_SequenceSize;                    // Size of each sequence (usually 256)
    unsigned short m_Sequence00Address;               // Address of sequence 0
};
```

**This block defines the entire music data memory layout!**

---

## 2. Sequence Format

### Sequence Entry Format (Packed Format)

From `datasource_sequence.cpp` line 184-195:

```
Byte Value     Meaning
----------     -------
0x00           Note off (gate off)
0x01 - 0x6F    Notes (0x01 = lowest note, 0x6F = highest)
0x70 - 0x7D    Reserved
0x7E           Note on (gate on) - sustain marker in unpacked view
0x7F           End of sequence marker
0x80 - 0x8F    Duration (bits 0-3 = duration value)
0x90 - 0x9F    Duration + Tie note flag (bit 4 = tie, bits 0-3 = duration)
0xA0 - 0xBF    Set instrument (bits 0-4 = instrument index 0-31)
0xC0 - 0xFF    Set command (bits 0-5 = command index 0-63)
```

### Packed Sequence Format

Sequences are stored in packed format. Each event consists of:

```
[Command byte?] [Instrument byte?] [Duration byte?] [Note byte]
```

**Rules**:
1. Command byte (`0xC0-0xFF`) is **optional** - only included when command changes
2. Instrument byte (`0xA0-0xBF`) is **optional** - only included when instrument changes
3. Duration byte (`0x80-0x9F`) is **optional** - omitted if duration unchanged from previous event
4. Note byte (`0x00-0x7E`, or `0x7F` for end) is **always present**

**Example packed sequence**:

```
A0 C1 81 3C    ; Set instrument 0, command 1, duration 1, note C-4 (0x3C)
3D             ; Note C#4 (0x3D) - reuses instrument, command, duration
3E             ; Note D-4 (0x3E) - reuses all
C2 3F          ; Set command 2, note D#4 (0x3F) - reuses instrument and duration
7F             ; End marker
```

### Unpacked Sequence Format (Editor View)

From `datasource_sequence.cpp` line 23-42:

```cpp
struct Event
{
    unsigned char m_Instrument;  // 0x80 = no change, 0x90 = tie note, 0xA0-0xBF = set instrument
    unsigned char m_Command;     // 0x80 = no change, 0xC0-0xFF = set command
    unsigned char m_Note;        // 0x00 = gate off, 0x01-0x6F = note, 0x7E = gate on/sustain
};
```

**Special Values**:
- `m_Instrument = 0x80`: No instrument change
- `m_Instrument = 0x90`: Tie note (no gate retrigger)
- `m_Instrument = 0xA0-0xBF`: Set instrument (bits 0-4 = instrument index)
- `m_Command = 0x80`: No command change
- `m_Command = 0xC0-0xFF`: Set command (bits 0-5 = command index)
- `m_Note = 0x00`: Gate off
- `m_Note = 0x01-0x6F`: Note value
- `m_Note = 0x7E`: Gate on (shown as `+++` in editor)

### Unpacking Algorithm

From `datasource_sequence.cpp` line 197-267:

```cpp
void Unpack()
{
    ClearEvents();

    int event_index = 0;
    int duration = 0;
    bool tie_note = false;

    for (int i = 0; i < 0x100;)
    {
        unsigned char value = m_Data[i++];

        if (value == 0x7f)  // End marker
        {
            m_PackedSize = i;
            break;
        }

        // Check for command byte (0xC0-0xFF)
        if (value >= 0xc0)
        {
            m_Events[event_index].m_Command = value;
            m_LastCommandSet = value & 0x3f;
            value = m_Data[i++];
        }
        else
            m_Events[event_index].m_Command = 0x80;  // No change

        // Check for instrument byte (0xA0-0xBF)
        if (value >= 0xa0)
        {
            m_Events[event_index].m_Instrument = value;
            m_LastInstrumentSet = value & 0x1f;
            value = m_Data[i++];
        }
        else
            m_Events[event_index].m_Instrument = 0x80;  // No change

        // Check for duration byte (0x80-0x9F)
        if (value >= 0x80)
        {
            duration = value & 0x0f;            // Bits 0-3 = duration
            tie_note = (value & 0x10) != 0;     // Bit 4 = tie flag

            if (tie_note)
                m_Events[event_index].m_Instrument = 0x90;  // Mark as tie

            value = m_Data[i++];
        }

        // Now value is the note byte (0x00-0x7E)
        m_Events[event_index++].m_Note = value;

        // Fill in sustain events for duration
        for (int j = 0; j < duration; ++j)
        {
            m_Events[event_index].m_Command = 0x80;
            m_Events[event_index].m_Instrument = 0x80;
            m_Events[event_index].m_Note = value != 0x00 ? 0x7e : 0x00;  // Gate on or off
            event_index++;
        }
    }

    m_Length = event_index;
}
```

### Packing Algorithm

From `datasource_sequence.cpp` line 282-364:

```cpp
PackResult Pack()
{
    m_LastCommandSet = 0xff;
    m_LastInstrumentSet = 0xff;

    int packIndex = 0;
    int lastDuration = -1;

    for (unsigned int i = 0; i < m_Length; ++i)
    {
        unsigned char instrument = m_Events[i].m_Instrument;
        unsigned char command = m_Events[i].m_Command;
        unsigned char note = m_Events[i].m_Note;

        // Look ahead to calculate duration
        int duration = 0;
        for (unsigned int j = i + 1; j < m_Length; ++j)
        {
            if (m_Events[j].m_Instrument != 0x80 || m_Events[j].m_Command != 0x80)
                break;  // Next event has changes

            if (note == 0)
            {
                if (m_Events[j].m_Note != 0)
                    break;  // Gate off ends
            }
            else
            {
                if (m_Events[j].m_Note != 0x7e)
                    break;  // Not sustain
            }

            duration++;
            if (duration >= 0x0f)
                break;  // Max duration is 15
        }

        bool bTieNote = (instrument == 0x90);

        // Write command byte if changed
        if (command != 0x80)
        {
            m_InternalBuffer[packIndex++] = command;
            m_LastCommandSet = command & 0x3f;
        }

        // Write instrument byte if >= 0xA0
        if (instrument >= 0xa0)
        {
            m_InternalBuffer[packIndex++] = instrument;
            m_LastInstrumentSet = instrument & 0x1f;
        }

        // Write duration byte if changed or tie note
        if (lastDuration != duration || bTieNote)
        {
            m_InternalBuffer[packIndex++] = (duration | 0x80) | (bTieNote ? 0x10 : 0x00);
            lastDuration = duration;
        }

        // Always write note byte
        m_InternalBuffer[packIndex++] = note;

        i += duration;  // Skip sustained events
    }

    // Error check
    m_PackingErrorState = !(packIndex > 0 && packIndex < 0xff);

    if (!m_PackingErrorState)
    {
        // Insert end marker
        m_InternalBuffer[packIndex++] = 0x7f;

        // Copy to final buffer
        unsigned char* packed_data = new unsigned char[packIndex];
        for (int i = 0; i < packIndex; i++)
            packed_data[i] = m_InternalBuffer[i];

        return PackResult(packed_data, packIndex);
    }

    return PackResult();  // Error
}
```

### Sequence Constraints

From `datasource_sequence.h` line 21 and `datasource_sequence.cpp` line 10:

```cpp
static const unsigned int MaxEventCount = 1024;  // Max unpacked events
```

From `sf2_interface.cpp` line 461 and line 516:

```cpp
if (sequence_length < DataSourceSequence::MaxEventCount) {
    // OK to add
}

if (packed_result.m_DataLength >= 0x100 || packed_result.m_Data == nullptr)
    return false;  // Sequence too large or packing failed
```

**Critical Constraints**:
1. **Unpacked**: Maximum 1024 events per sequence
2. **Packed**: Maximum 255 bytes per sequence (including `0x7F` end marker)
3. Sequences are stored in fixed-size blocks (usually 256 bytes from `MusicData.m_SequenceSize`)

---

## 3. Orderlist Format

### Orderlist Entry Format (Packed)

From `datasource_orderlist.h` line 21-24:

```cpp
struct Entry
{
    unsigned char m_Transposition;  // Transpose value (0xA0 = no transpose, 0xFF = end marker)
    unsigned char m_SequenceIndex;  // Sequence number (0-127), or loop index if preceded by 0xFF
};
```

### Packed Orderlist Format

```
[Transpose] [Sequence] [Transpose] [Sequence] ... 0xFF [LoopIndex]
```

**Special Values**:
- `Transpose = 0xA0`: No transposition (default)
- `Transpose = 0xFF`: End of orderlist marker
- `Transpose = 0xFE`: Alternative end marker (no loop)
- Byte after `0xFF`: Loop index (which orderlist entry to loop back to)

**Example**:

```
A0 00    ; Play sequence 0, no transpose
A0 01    ; Play sequence 1, no transpose
A3 02    ; Play sequence 2, transpose +3 semitones
FF 01    ; End, loop back to index 1
```

### Orderlist Constraints

From `datasource_orderlist.h` line 18:

```cpp
const int MaxEntryCount = 256;
```

From `sf2_interface.cpp` line 492-493:

```cpp
if (packed_result.m_DataLength >= 0x100)
    return false;  // Orderlist too large
```

**Critical Constraints**:
1. Maximum 256 entries per orderlist (including end marker + loop index)
2. Stored in fixed-size blocks (usually 256 bytes from `MusicData.m_OrderListSize`)

---

## 4. Critical Constraints

### Space Allocation for Sequences

From `driver_utils.cpp` line 329-338:

```cpp
unsigned short GetEndOfMusicDataAddress(const Editor::DriverInfo& inDriverInfo,
                                        const Emulation::IMemoryRandomReadAccess& InMemoryReader)
{
    FOUNDATION_ASSERT(inDriverInfo.IsValid());

    const unsigned char highest_sequence_index = GetHighestSequenceIndexUsed(inDriverInfo, InMemoryReader);

    // Get Music data descriptor
    const unsigned short sequence_data_address = inDriverInfo.GetMusicData().m_Sequence00Address +
                                                 (inDriverInfo.GetMusicData().m_SequenceSize * (highest_sequence_index + 1));

    return sequence_data_address;
}
```

**Key Insight**: The end of music data is calculated as:

```
EndAddress = Sequence00Address + (SequenceSize × (HighestUsedSequenceIndex + 1))
```

This means:
- Only sequences **0 through highest_used_index** are included in the file
- Unused sequences **beyond** the highest used index are **NOT saved**
- File size automatically shrinks when high-numbered sequences are unused

### What Happens When You Overwrite Sequence Data

From `sf2_interface.cpp` line 217-248:

```cpp
void InitData()
{
    // ...

    // Replace first transpose byte 0xa0 with 0xff to solidify this is a true virgin state
    // NOTE: This is only in effect during converting; it is restored when pushing data if it still persists.
    for (int i = 0; i < m_DriverDetails.m_TrackCount; i++)
    {
        std::shared_ptr<DataSourceOrderList>& orderlist_track = m_OrderListDataSources[i];
        (*orderlist_track)[0] = { 0xff, 0x00 };
    }

    // Set all sequence sizes to 0 (the small one event sequences are obstructing the conversions)
    // NOTE: This is only for appending during converting; the sequence sizes are restored when pushing data.
    for (int i = 0; i < m_DriverDetails.m_SequenceCount; i++)
    {
        const std::shared_ptr<DataSourceSequence>& sequence_source = m_SequenceDataSources[i];
        sequence_source->SetLength(0);
    }
}
```

**Important**: During conversion, the SF2 interface:
1. Marks orderlists as "virgin" with `0xFF 0x00` (restored to `0xA0 0x00` on save)
2. Sets all sequence lengths to 0 temporarily
3. This allows appending without interference from template data

### Pointer Tables Required

From `screen_edit_utils.cpp` line 42-62:

```cpp
void PrepareSequencePointers(const Editor::DriverInfo& inDriverInfo, Emulation::CPUMemory& inCPUMemory)
{
    FOUNDATION_ASSERT(inCPUMemory.IsLocked());

    if (inDriverInfo.IsValid())
    {
        // Get Music data descriptor
        const DriverInfo::MusicData& music_data = inDriverInfo.GetMusicData();

        for (int i = 0; i < music_data.m_SequenceCount; ++i)
        {
            const unsigned short sequence_address = music_data.m_Sequence00Address + i * music_data.m_SequenceSize;

            const unsigned char sequence_address_low = static_cast<unsigned char>(sequence_address & 0xff);
            const unsigned char sequence_address_high = static_cast<unsigned char>(sequence_address >> 8);

            inCPUMemory[music_data.m_SequencePointersLowAddress + i] = sequence_address_low;
            inCPUMemory[music_data.m_SequencePointersHighAddress + i] = sequence_address_high;
        }
    }
}
```

**Critical**: When sequences are at fixed offsets, pointer tables MUST be updated:

```
For each sequence i (0 to SequenceCount-1):
    SequenceAddress = Sequence00Address + (i × SequenceSize)
    SequencePointersLowAddress[i] = SequenceAddress & 0xFF
    SequencePointersHighAddress[i] = SequenceAddress >> 8
```

**Same applies to orderlists**, though orderlists are typically at fixed offsets per track.

### Block Size Limitations

From `MusicData` block:

```cpp
unsigned short m_OrderListSize;   // Usually 256 (0x100) bytes
unsigned short m_SequenceSize;    // Usually 256 (0x100) bytes
```

**Fixed allocations**:
- Each orderlist occupies exactly `OrderListSize` bytes in memory
- Each sequence occupies exactly `SequenceSize` bytes in memory
- Overflowing these limits will corrupt adjacent data

### Memory Layout Constraints

From `driver_info.cpp` line 233-293:

The SF2 file is **NOT** a simple binary blob. It has a **structured header + data layout**:

```
[Magic: 0x1337]
[Header Blocks...]
[0xFF End Marker]
[Driver Code]
[Music Data: Orderlists]
[Music Data: Sequences]
[Tables: Instruments, Commands, Wave, Pulse, Filter, etc.]
[IRQ Code - appended on export]
[Auxiliary Data - appended on export]
```

**The header blocks define WHERE everything is in memory, NOT in the file!**

---

## 5. Loading and Validation

### File Load Process

From `sf2_interface.cpp` line 87-131:

```cpp
bool LoadFile(const std::string& inPathAndFilename)
{
    void* data = nullptr;
    long data_size = 0;

    std::shared_ptr<DriverInfo> driver_info = std::make_shared<DriverInfo>();

    if (Utility::ReadFile(inPathAndFilename, 65536, &data, data_size))
    {
        if (data_size > 2)
        {
            // 1. Create C64File from PRG data (reads load address from first 2 bytes)
            std::shared_ptr<Utility::C64File> c64_file = Utility::C64File::CreateFromPRGData(data, data_size);

            // 2. Parse driver info header blocks
            driver_info->Parse(*c64_file);

            if (driver_info->IsValid())
            {
                m_DriverInfo = driver_info;
                m_DriverInfo->GetAuxilaryDataCollection().Reset();

                // 3. Load auxiliary data if present
                const unsigned short auxilary_data_vector = m_DriverInfo->GetDriverCommon().m_InitAddress - 5;
                const unsigned short auxilary_data_address = c64_file->GetWord(auxilary_data_vector);

                if (auxilary_data_address != 0)
                {
                    Utility::C64FileReader reader = Utility::C64FileReader(*c64_file, auxilary_data_address);
                    m_DriverInfo->GetAuxilaryDataCollection().Load(reader);
                }

                // 4. Parse driver-specific details
                ParseDriverDetails();

                // 5. Copy data to emulated C64 memory
                m_CPUMemory->Lock();
                m_CPUMemory->Clear();
                m_CPUMemory->SetData(c64_file->GetTopAddress(), c64_file->GetData(), c64_file->GetDataSize());
                m_CPUMemory->Unlock();

                // 6. Initialize data sources (orderlists, sequences)
                InitData();
            }
        }

        delete[] static_cast<char*>(data);
    }

    return driver_info->IsValid();
}
```

### Validation Checks

#### Required Header Blocks

From `driver_info.cpp` line 151-173:

```cpp
bool HasParsedRequiredBlocks() const
{
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_Descriptor))       return false;
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_DriverCommon))     return false;
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_DriverTables))     return false;
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_DriverInstrumentDescriptor)) return false;
    if (!HasParsedHeaderBlock(HeaderBlockID::ID_MusicData))        return false;
    return true;
}
```

#### Required Tables

From `driver_info.cpp` line 382-386:

```cpp
if (table_definition.m_Type == TableType::Instruments)
    m_FoundRequiredTableInstruments = true;
if (table_definition.m_Type == TableType::Commands)
    m_FoundRequiredTableCommands = true;
```

From `driver_info.cpp` line 46:

```cpp
m_IsValid = m_FoundRequiredTableInstruments && m_FoundRequiredTableCommands && HasParsedRequiredBlocks();
```

**An SF2 file MUST have Instruments (0x80) and Commands (0x81) tables, or it's invalid.**

#### Magic Number Check

From `driver_info.cpp` line 41:

```cpp
if (inFile.GetWord(top_address) == ExpectedFileIDNumber)  // 0x1337
{
    m_TopAddress = top_address;
    // Continue parsing
}
```

### Common Load Crash Patterns

#### 1. Missing Magic Number

**Symptom**: File rejected immediately
**Cause**: First two bytes not `0x37 0x13`
**Fix**: Ensure PRG load address is followed by `0x1337`

#### 2. Malformed Header Blocks

**Symptom**: Parser stops mid-header
**Cause**: Block size mismatch or missing end marker (`0xFF`)
**Fix**: Verify each block has correct size byte and data length

#### 3. Missing Required Tables

**Symptom**: `IsValid()` returns false
**Cause**: No Instruments (0x80) or Commands (0x81) table in Block 3
**Fix**: Include both table types in DriverTables block

#### 4. Invalid Music Data Block

**Symptom**: Crash on InitData() or empty sequences
**Cause**:
- `SequenceCount` exceeds available memory
- `Sequence00Address` points outside file range
- `OrderListTrack1Address` invalid

**Fix**: Ensure all addresses in MusicData block are valid and within file bounds

#### 5. Sequence Pointer Corruption

**Symptom**: Random crashes during playback
**Cause**: Sequence pointer tables not initialized correctly
**Fix**: Call `PrepareSequencePointers()` after loading (handled automatically by `InitData()`)

---

## 6. Memory Layout

### C64 Memory Model

From `sf2_interface.cpp` line 48-49:

```cpp
m_EntireBlock = new unsigned char[0x10000];  // Full 64KB memory space
m_CPUMemory = new CPUMemory(0x10000, m_Platform);
```

SF2 files operate on a **full 64KB C64 memory model**.

### Typical Driver 11 Layout

Based on analysis of header blocks:

```
Address Range    Component
-------------    ---------
$0800 - $0900    Driver code start (varies by driver)
$0900 - $09FF    Driver code / init routines
$0A00 - $0AFF    Sequence pointer tables
$0B00 - $0BFF    Orderlist data (Track 1, 2, 3...)
$0C00 - $13FF    Sequence data (128 × 256 bytes = 32KB typical)
$1400 - $14FF    Instrument table (column-major, 32 rows × 6 cols)
$1500 - $15FF    Command table (3 bytes per row)
$1600 - $16FF    Wave table
$1700 - $17FF    Pulse table
$1800 - $18FF    Filter table
$1900 - $19FF    HR table (Hard Restart ADSR)
$1A00 - $1AFF    Arpeggio table
$1B00 - $1BFF    Tempo table
$1C00 - $1CFF    Init table
[End of music data]
[IRQ code - optional]
[Auxiliary data - optional]
```

**Note**: Actual addresses vary by driver version and configuration.

### How End of File is Calculated

From `sf2_interface.cpp` line 144-151:

```cpp
unsigned short top_of_file_address = m_DriverInfo->GetTopAddress();
unsigned short end_of_file_address = DriverUtils::GetEndOfMusicDataAddress(*m_DriverInfo,
                                        reinterpret_cast<const Emulation::IMemoryRandomReadAccess&>(*m_CPUMemory));
unsigned short data_size = end_of_file_address - top_of_file_address;

unsigned char* data = new unsigned char[data_size];
m_CPUMemory->GetData(top_of_file_address, data, data_size);
```

**Process**:
1. Find highest used sequence index by scanning all orderlists
2. Calculate: `EndAddress = Sequence00Address + (SequenceSize × (HighestIndex + 1))`
3. Extract memory from `TopAddress` to `EndAddress`
4. Append IRQ code and auxiliary data
5. Write to PRG file

---

## 7. Common Crash Causes

### Why Injecting Sequence Data Might Crash

Based on source analysis, crashes occur when:

#### 1. Sequence Pointer Tables Not Updated

**Problem**: Sequences are at fixed addresses, but pointer tables still point to old locations.

**Fix**:
```cpp
PrepareSequencePointers(*m_DriverInfo, *m_CPUMemory);
```

This recalculates all sequence pointers after any address changes.

#### 2. Overwriting Driver Code

**Problem**: Sequence data overlaps with driver code region.

**Check**:
```cpp
if (sequence_address < m_DriverInfo->GetDescriptor().m_DriverCodeTop +
                       m_DriverInfo->GetDescriptor().m_DriverCodeSize)
{
    // ERROR: Sequence would overwrite driver code!
}
```

#### 3. Exceeding Sequence Size Limit

**Problem**: Packed sequence exceeds 255 bytes (including `0x7F` end marker).

**Validation**:
```cpp
PackResult result = sequence->Pack();
if (result.m_DataLength >= 0x100 || result.m_Data == nullptr)
{
    // ERROR: Sequence too large or packing failed
}
```

#### 4. Invalid Sequence Index in Orderlist

**Problem**: Orderlist references sequence index >= SequenceCount.

**Validation**:
```cpp
if (sequence_index >= m_DriverInfo->GetMusicData().m_SequenceCount)
{
    // ERROR: Invalid sequence index
}
```

#### 5. Missing End Marker

**Problem**: Sequence data missing `0x7F` end marker.

**Symptom**: Player reads beyond sequence bounds, crashes or plays garbage.

**Fix**: Always ensure packed sequences end with `0x7F`.

#### 6. Corrupted Header Blocks

**Problem**: Block size mismatch or missing `0xFF` end marker.

**Symptom**: Parser reads garbage, corrupts DriverInfo data structures.

**Validation**:
```cpp
// During block parsing:
unsigned short block_size = reader.ReadByte();
unsigned short expected_end = reader.GetReadAddress() + block_size;

// After block parsing:
if (!reader.IsAtEndAddress())
{
    // ERROR: Block size mismatch
}
```

#### 7. Memory Overlap Between Sequences and Tables

**Problem**: Tables and sequences use same memory addresses.

**Check**: Ensure no overlap:
```cpp
// Calculate all address ranges:
unsigned short seq_start = m_MusicData.m_Sequence00Address;
unsigned short seq_end = seq_start + (m_MusicData.m_SequenceCount * m_MusicData.m_SequenceSize);

for (auto& table : m_TableDefinitions)
{
    unsigned short table_start = table.m_Address;
    unsigned short table_end = table_start + (table.m_RowCount * table.m_ColumnCount);

    if (!(seq_end <= table_start || seq_start >= table_end))
    {
        // ERROR: Sequence and table memory overlap!
    }
}
```

---

## Summary of Critical Points

### For Safe SF2 File Generation:

1. **Always include magic number** `0x1337` at top address
2. **Include all 5 required header blocks** (Descriptor, DriverCommon, DriverTables, DriverInstrumentDescriptor, MusicData)
3. **End header with** `0xFF` marker
4. **Include Instruments (0x80) and Commands (0x81) tables** in DriverTables block
5. **Ensure sequences end with** `0x7F` marker
6. **Keep packed sequences under 256 bytes** (including end marker)
7. **Update sequence pointer tables** after any address changes
8. **Verify no memory overlaps** between driver code, sequences, orderlists, and tables
9. **Use GetEndOfMusicDataAddress()** to calculate file size correctly
10. **Validate all addresses** are within 64KB memory space and within file bounds

### For Safe Sequence Injection:

1. **Call `PrepareSequencePointers()`** after modifying sequences
2. **Call `PushAllDataToMemory()`** to pack and validate before saving
3. **Check packed size** `< 0x100` bytes
4. **Verify sequence index** `< SequenceCount`
5. **Ensure end marker** `0x7F` is present
6. **Don't exceed** `MaxEventCount = 1024` unpacked events
7. **Update orderlist** to reference new sequences
8. **Verify no overlap** with driver code or tables

---

**End of Deep-Dive Analysis**
