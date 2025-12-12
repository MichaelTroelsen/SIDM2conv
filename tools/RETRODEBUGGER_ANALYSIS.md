# RetroDebugger v0.64.68 - Source Code Analysis

**Analysis Date:** December 11, 2025
**Source Location:** `C:\Users\mit\Downloads\RetroDebugger-master\RetroDebugger-master`

---

## Executive Summary

RetroDebugger is a real-time code and memory debugger for Commodore 64, Atari XL/XE, and NES. It provides advanced debugging capabilities including full C64 emulation, comprehensive SID debugging, and remote debugging APIs. The tool embeds VICE v3.1 emulator with reSID for accurate SID emulation.

**Key Finding for SIDM2:** RetroDebugger offers powerful remote debugging APIs that could enhance SIDM2's validation pipeline with real-time SID register inspection, waveform comparison, and automated testing capabilities.

---

## Architecture Overview

### Core Components

```
RetroDebugger/
├── src/
│   ├── DebugInterface/C64/          # C64-specific debugging
│   │   ├── CDebugInterfaceC64.h/cpp # Abstract C64 interface
│   │   └── ...                      # Adapters, disk handling
│   ├── Emulators/vice/              # VICE emulator integration
│   │   ├── ViceInterface/           # VICE-specific implementation
│   │   │   ├── CDebugInterfaceVice  # Full C64 debug interface
│   │   │   ├── CDebuggerApiVice     # API for scripts/plugins
│   │   │   ├── CDebuggerServerApiVice # Remote debugging API
│   │   │   └── ViceWrapper          # VICE C interface wrapper
│   │   ├── resid/                   # reSID SID emulation library
│   │   ├── sid/                     # SID chip implementation
│   │   └── c64/psid.h/c             # PSID/RSID file handling
│   ├── Views/C64/                   # UI components
│   │   ├── CViewC64StateSID         # SID state visualization
│   │   ├── CViewC64StateCPU         # CPU state view
│   │   └── CViewC64StateVIC         # VIC state view
│   ├── Remote/                      # Remote debugging
│   │   ├── Pipe/                    # Named pipe communication
│   │   └── WebSockets/              # WebSocket server
│   └── Plugins/GoatTracker/         # GoatTracker integration
```

### Technology Stack

- **Emulator:** VICE v3.1 (Versatile Commodore Emulator)
- **SID Emulation:** reSID library (accurate 6581/8580 simulation)
- **UI Framework:** SDL2 + ImGui
- **Remote API:** HTTP/JSON RESTful endpoints
- **Communication:** Named pipes, WebSockets
- **Build System:** CMake, platform-specific projects (Xcode, VS2019, Linux)

---

## SID Debugging Capabilities

### 1. Register Access (`CDebugInterfaceVice.h` lines 303-318)

**Full SID Register Control:**
```cpp
// Read single SID register
u8 GetSidRegister(uint8 sidId, uint8 registerNum);

// Write single SID register
void SetSidRegister(uint8 sidId, uint8 registerNum, uint8 value);

// Batch write all registers (avoids side effects)
void SetSid(CSidData *sidData);
```

**CSidData Structure:**
```cpp
class CSidData {
    u8 sidRegs[SOUND_SIDS_MAX][C64_NUM_SID_REGISTERS];  // All registers
    bool shouldSetSidReg[SOUND_SIDS_MAX][C64_NUM_SID_REGISTERS]; // Write mask

    bool SaveRegs(const char *fileName);   // Export to file
    bool LoadRegs(const char *fileName);   // Import from file
    void Serialize(CByteBuffer *byteBuffer); // Network/IPC
};
```

**Key Features:**
- Access to all 32 SID registers ($D400-$D41F)
- Support for up to 3 SIDs (mono/stereo/triple)
- Selective register writing to avoid unwanted side effects
- Serialization for snapshots and remote debugging

### 2. Configuration (`CDebugInterfaceVice.h` lines 154-173)

**SID Type Selection:**
```cpp
void SetSidType(int sidType);        // 6581 vs 8580
void GetSidTypes(vector<CSlrString*> *sidTypes);
```

**SID Parameters:**
```cpp
void SetSidSamplingMethod(int samplingMethod);  // Fast/Interpolating/Resampling
void SetSidEmulateFilters(int emulateFilters);  // Enable/disable filter emulation
void SetSidPassBand(int passband);              // 0-90
void SetSidFilterBias(int filterBias);          // -500 to 500
```

**Multi-SID Support:**
```cpp
void SetSidStereo(int stereoMode);              // 0=none, 1=stereo, 2=triple
void SetSidStereoAddress(uint16 sidAddress);    // Second SID address
void SetSidTripleAddress(uint16 sidAddress);    // Third SID address
int GetNumSids();                                // Current SID count
```

### 3. Waveform Visualization (`CViewC64StateSID.h` lines 58-62)

**Real-time Waveform Display:**
```cpp
// Per-channel waveforms for each SID
CViewWaveform *viewChannelWaveform[C64_MAX_NUM_SIDS][3];

// Mixed output waveform for each SID
CViewWaveform *viewMixWaveform[C64_MAX_NUM_SIDS];
```

**Waveform Data Collection:**
```cpp
// Called every audio sample
void AddWaveformData(int sidNumber, int voice1, int voice2, int voice3, short mix);
void UpdateWaveforms();
```

**Features:**
- Real-time oscilloscope-style display
- Individual voice waveforms (Voice 1, 2, 3)
- Mixed output waveform
- Multi-SID support
- Can mute individual channels for debugging

### 4. Historical State Tracking (`CDebugInterfaceVice.h` lines 330-336)

**SID Data History:**
```cpp
list<CSidData*> sidDataHistory;          // Historical states
int sidDataHistorySteps;                 // Number of steps to keep
int sidDataHistoryCurrentStep;           // Current position
void UpdateSidDataHistory();             // Update history
void SetSidDataHistorySteps(int numSteps); // Configure depth
```

**Use Cases:**
- Step backward/forward through SID states
- Compare SID behavior over time
- Analyze envelope and filter changes
- Debug timing-dependent issues

### 5. Channel Control (`CDebugInterfaceVice.h` lines 316-317)

**Per-Channel Muting:**
```cpp
void SetSIDMuteChannels(int sidNumber, bool mute1, bool mute2, bool mute3, bool muteExt);
void SetSIDReceiveChannelsData(int sidNumber, bool isReceiving);
```

**Applications:**
- Isolate individual voices for analysis
- Test voice interactions
- Debug polyphony issues
- Analyze channel crosstalk

---

## Remote Debugging API

### HTTP/JSON Endpoints (`CDebuggerServerApiVice.cpp`)

#### SID Write Endpoint (lines 236-282)

```http
POST /c64/sid/write
Content-Type: application/json

{
  "sids": {
    "0": {
      "num": 0,
      "registers": {
        "0": "0x00",     // Frequency low (Voice 1)
        "1": "0x08",     // Frequency high (Voice 1)
        "4": "0x11",     // Control register (Voice 1)
        ...
      }
    }
  }
}
```

**Features:**
- Burst-write capability (all registers updated atomically)
- Prevents side effects from sequential writes
- Multi-SID support
- Hex or decimal values
- HTTP 200 OK on success, 406 Not Acceptable on error

#### SID Read Endpoint (lines 284-300)

```http
POST /c64/sid/read
Content-Type: application/json

{
  "num": 0,
  "registers": [0, 1, 2, 3, 4, 5, 6, 7]
}

Response:
{
  "registers": {
    "0": 128,
    "1": 15,
    "2": 0,
    ...
  }
}
```

**Features:**
- Read multiple registers in one call
- Specify SID number (0, 1, 2)
- Returns current register values
- Supports both write-only and read-only registers

#### VIC and CIA Endpoints

Similar patterns for VIC and CIA chip access:
- `/c64/vic/write`, `/c64/vic/read` (lines 58-110)
- `/c64/cia/write`, `/c64/cia/read` (lines 144-234)
- `/c64/vic/breakpoint/add`, `/c64/vic/breakpoint/remove` (lines 112-142)

### API Architecture

**Thread-Safe Access:**
```cpp
debugInterfaceVice->LockMutex();
// ... perform operations ...
debugInterfaceVice->UnlockMutex();
```

**Error Handling:**
- Validates register numbers and SID IDs
- Returns HTTP status codes
- Thread-safe with mutex protection
- Synchronizes with emulation thread

---

## SID File Support (`CDebuggerApiVice.h` lines 130-131)

### LoadSID() Function

```cpp
bool LoadSID(const char *filePath,
             u16 *fromAddr,   // Load address
             u16 *toAddr,     // End address
             u16 *initAddr,   // Init routine
             u16 *playAddr);  // Play routine
```

**PSID/RSID Format Support:**
- Parses PSID v2 headers
- Extracts metadata (title, author, copyright)
- Loads SID code into C64 memory
- Sets up init and play addresses
- Supports multiple subtunes

**Integration with VICE:**
```cpp
// VICE PSID handler (c64/psid.c, c64/psid.h)
extern "C" {
    #include "psid.h"
}
```

---

## API Classes

### CDebuggerApiVice (`CDebuggerApiVice.h`)

**High-Level API for Scripts/Plugins:**

```cpp
class CDebuggerApiVice : public CDebuggerApi {
public:
    // SID control
    void SetSid(CSidData *sidData);
    void SetSidRegister(uint8 sidId, uint8 registerNum, uint8 value);
    u8 GetSidRegister(uint8 sidId, uint8 registerNum);

    // Memory access
    void SetByteToRamC64(int addr, u8 v);
    u8 GetByteFromRamC64(int addr);

    // CPU control
    void MakeJmp(int addr);

    // File operations
    bool LoadSID(const char *filePath, u16 *fromAddr, u16 *toAddr,
                 u16 *initAddr, u16 *playAddr);
    bool LoadPRG(const char *filePath, u16 *fromAddr, u16 *toAddr);
    bool SavePRG(u16 fromAddr, u16 toAddr, const char *fileName);

    // Assembly
    int Assemble(int addr, char *assembleText);

    // Breakpoints
    u64 AddBreakpointRasterLine(int rasterLine);
    u64 RemoveBreakpointRasterLine(int rasterLine);

    // JSON API
    nlohmann::json GetCpuStatusJson();
};
```

### CDebuggerServerApiVice (`CDebuggerServerApiVice.h`)

**Remote Debugging Server:**

```cpp
class CDebuggerServerApiVice : public CDebuggerServerApi {
public:
    void RegisterEndpoints(CDebuggerServer *server);

    // Endpoints registered:
    // - /c64/savePrg
    // - /c64/vic/write, /c64/vic/read
    // - /c64/vic/breakpoint/add, /c64/vic/breakpoint/remove
    // - /c64/cia/write, /c64/cia/read
    // - /c64/sid/write, /c64/sid/read

    CSidData *sidData;  // Shared SID data buffer
};
```

---

## reSID Integration

### Accurate SID Emulation (`src/Emulators/vice/resid/`)

**Components:**
- `resid-sid.cpp/h` - Main SID chip emulation
- `resid-voice.cpp/h` - Voice implementation
- `resid-envelope.cpp/h` - ADSR envelope generator
- `resid-wave.cpp/h` - Waveform generation
- `resid-filter.cpp/h` - Filter implementation
- `resid-extfilt.cpp/h` - External filter
- `resid-dac.cpp/h` - DAC emulation

**Sampling Methods:**
- **Fast** (0): Basic interpolation
- **Interpolating** (1): Better quality
- **Resampling** (2): High quality with resampling
- **Fast Resampling** (3): Balance between speed and quality

**Filter Accuracy:**
- Emulates 6581 vs 8580 filter differences
- Configurable passband (0-90)
- Filter bias adjustment (-500 to 500)
- External filter emulation

---

## Potential Integration with SIDM2

### 1. Real-Time Validation

**Use RetroDebugger API to validate SID conversions:**

```python
# Example integration
import requests
import json

class RetroDebuggerValidator:
    def __init__(self, host='localhost', port=8080):
        self.base_url = f'http://{host}:{port}/c64'

    def load_sid(self, sid_path):
        """Load SID file into RetroDebugger"""
        # Use LoadSID() API endpoint (would need to be implemented)
        pass

    def read_sid_registers(self, sid_num=0):
        """Read all SID registers"""
        response = requests.post(
            f'{self.base_url}/sid/read',
            json={
                'num': sid_num,
                'registers': list(range(0x20))  # All 32 registers
            }
        )
        return response.json()['registers']

    def write_sid_registers(self, registers, sid_num=0):
        """Write SID registers"""
        response = requests.post(
            f'{self.base_url}/sid/write',
            json={
                'sids': {
                    '0': {
                        'num': sid_num,
                        'registers': registers
                    }
                }
            }
        )
        return response.status_code == 200

    def compare_sids(self, original_sid, converted_sid):
        """Compare original vs converted SID files"""
        # 1. Load original SID
        self.load_sid(original_sid)
        original_regs = self.read_sid_registers()

        # 2. Load converted SID
        self.load_sid(converted_sid)
        converted_regs = self.read_sid_registers()

        # 3. Compare register states
        differences = {}
        for reg in range(0x20):
            if original_regs[reg] != converted_regs[reg]:
                differences[reg] = {
                    'original': original_regs[reg],
                    'converted': converted_regs[reg]
                }

        return differences
```

### 2. Waveform Comparison

**Capture and compare audio waveforms:**

```python
class WaveformValidator:
    def capture_waveform(self, sid_file, duration_seconds=30):
        """Capture SID waveform data"""
        # 1. Load SID in RetroDebugger
        # 2. Run emulation for duration
        # 3. Export waveform data (would need API endpoint)
        # 4. Return waveform array
        pass

    def compare_waveforms(self, waveform1, waveform2, threshold=0.95):
        """Compare two waveforms for similarity"""
        import numpy as np

        # Normalize waveforms
        w1 = np.array(waveform1, dtype=float)
        w2 = np.array(waveform2, dtype=float)

        # Calculate correlation coefficient
        correlation = np.corrcoef(w1, w2)[0, 1]

        return {
            'similarity': correlation,
            'passed': correlation >= threshold
        }
```

### 3. Automated Testing

**Integration into SIDM2 pipeline:**

```python
# In complete_pipeline_with_validation.py

def validate_with_retrodebugger(original_sid, exported_sid):
    """Step 11: RetroDebugger validation (optional)"""

    if not RETRODEBUGGER_ENABLED:
        return None

    validator = RetroDebuggerValidator()

    # Compare register states
    reg_diff = validator.compare_sids(original_sid, exported_sid)

    # Capture and compare waveforms
    wf_validator = WaveformValidator()
    wf_orig = wf_validator.capture_waveform(original_sid, 10)
    wf_conv = wf_validator.capture_waveform(exported_sid, 10)
    wf_similarity = wf_validator.compare_waveforms(wf_orig, wf_conv)

    return {
        'register_differences': reg_diff,
        'waveform_similarity': wf_similarity,
        'passed': len(reg_diff) == 0 and wf_similarity['passed']
    }
```

### 4. Interactive Debugging

**Manual inspection during development:**

1. **Load SID in RetroDebugger GUI**
   - Full C64 environment
   - Real-time register inspection
   - Waveform visualization

2. **Step through execution**
   - Set breakpoints on init/play routines
   - Monitor SID register writes
   - Analyze timing and patterns

3. **Compare original vs converted**
   - Side-by-side waveform comparison
   - Register value differences
   - Audio output comparison

---

## Integration Opportunities

### ✅ Recommended Integrations

1. **Remote API for Validation** (HIGH VALUE)
   - Add HTTP endpoint integration to `complete_pipeline_with_validation.py`
   - Use `/c64/sid/read` to capture register states
   - Compare original vs exported SID register values
   - Provides real-time validation beyond siddump

2. **Waveform Comparison** (MEDIUM VALUE)
   - Complement audio WAV comparison
   - Provides visual feedback on accuracy
   - Can detect subtle timing issues
   - Requires API endpoint for waveform export

3. **Interactive Debugging Tool** (MEDIUM VALUE)
   - Launch RetroDebugger GUI for manual inspection
   - Useful when automated validation finds issues
   - Side-by-side comparison mode
   - Real-time register monitoring

### ⚠️ Requires Implementation

4. **Batch Testing Mode** (LOW PRIORITY)
   - Would need headless mode
   - Automated SID loading via API
   - Waveform export API endpoint
   - Currently requires GUI

### ❌ Not Recommended

5. **Embedding RetroDebugger** (NOT RECOMMENDED)
   - Large codebase (VICE + SDL2 + ImGui)
   - Licensing complexities
   - Better as external validation tool
   - HTTP API sufficient for integration

---

## Technical Requirements

### For SIDM2 Integration

**Prerequisites:**
- RetroDebugger running with HTTP server enabled
- Python requests library: `pip install requests`
- Optional: numpy for waveform analysis

**Configuration:**
```python
# Add to SIDM2 settings
RETRODEBUGGER_ENABLED = True
RETRODEBUGGER_HOST = 'localhost'
RETRODEBUGGER_PORT = 8080
```

**API Availability:**
- Check if RetroDebugger exposes HTTP server
- May need to enable in RetroDebugger settings
- WebSocket support also available

---

## Comparison with Existing Tools

| Feature | RetroDebugger | SIDwinder | siddump |
|---------|--------------|-----------|---------|
| **Real-time debugging** | ✅ Full GUI | ❌ No | ❌ No |
| **SID register access** | ✅ Read/Write | ⚠️ Read-only trace | ✅ Write trace |
| **Waveform visualization** | ✅ Real-time | ❌ No | ❌ No |
| **Remote API** | ✅ HTTP/JSON | ❌ No | ❌ No |
| **Disassembly** | ✅ Interactive | ✅ Best quality | ❌ No |
| **Trace logging** | ✅ Yes | ⚠️ Needs rebuild | ✅ Best |
| **SID file loading** | ✅ Full support | ✅ Yes | ✅ Yes |
| **Batch processing** | ⚠️ Limited | ✅ Excellent | ✅ Excellent |
| **Integration effort** | Medium (HTTP) | Low (CLI) | Low (CLI) |

**Recommendation:**
- **SIDwinder:** Best for batch disassembly and trace (after rebuild)
- **siddump:** Best for frame-by-frame register validation
- **RetroDebugger:** Best for interactive debugging and waveform analysis
- **SIDM2 Usage:** Complement existing tools with RetroDebugger's HTTP API for real-time validation

---

## Example Use Cases

### Use Case 1: Validate SF2→SID Packer

```python
def test_packer_with_retrodebugger(sf2_file):
    """Test SF2 packer using RetroDebugger validation"""

    # 1. Pack SF2 to SID
    from sidm2.sf2_packer import SF2Packer
    packer = SF2Packer(sf2_file)
    exported_sid = packer.pack()

    # 2. Load in RetroDebugger
    rd = RetroDebuggerValidator()
    rd.load_sid(exported_sid)

    # 3. Execute init routine
    rd.api.make_jmp(packer.init_addr)

    # 4. Capture initial SID state
    init_regs = rd.read_sid_registers()

    # 5. Execute play routine (50 frames)
    for frame in range(50):
        rd.api.make_jmp(packer.play_addr)
        frame_regs = rd.read_sid_registers()

        # Validate expected register writes
        assert frame_regs[0x04] & 0x01  # Voice 1 gate on

    return True
```

### Use Case 2: Debug Pointer Relocation Bug

```python
def debug_relocation_bug(sid_file):
    """Use RetroDebugger to find pointer relocation issues"""

    rd = RetroDebuggerValidator()
    rd.load_sid(sid_file)

    # Set breakpoint on potential bad jump
    rd.api.add_breakpoint_address(0x0000)  # Execution at $0000

    # Run until breakpoint
    rd.api.run_until_breakpoint()

    # Get CPU state
    cpu_state = rd.api.get_cpu_status_json()

    print(f"PC: ${cpu_state['pc']:04X}")
    print(f"Last instruction: {cpu_state['last_instruction']}")
    print(f"Stack trace: {cpu_state['stack_trace']}")

    # Analyze recent jumps
    for addr in cpu_state['recent_jumps']:
        print(f"Jump to: ${addr:04X}")
```

### Use Case 3: Waveform-Based Accuracy Grading

```python
def grade_conversion_accuracy(original_sid, converted_sid):
    """Grade SF2→SID conversion using waveform similarity"""

    wf_validator = WaveformValidator()

    # Capture 30-second waveforms
    wf_orig = wf_validator.capture_waveform(original_sid, 30)
    wf_conv = wf_validator.capture_waveform(converted_sid, 30)

    # Compare
    result = wf_validator.compare_waveforms(wf_orig, wf_conv)

    # Grade based on similarity
    similarity = result['similarity']
    if similarity >= 0.99:
        grade = 'EXCELLENT'
    elif similarity >= 0.95:
        grade = 'GOOD'
    elif similarity >= 0.90:
        grade = 'FAIR'
    else:
        grade = 'POOR'

    return {
        'grade': grade,
        'similarity': similarity,
        'recommendation': 'PASS' if grade in ['EXCELLENT', 'GOOD'] else 'REVIEW'
    }
```

---

## Implementation Roadmap

### Phase 1: Research (CURRENT)
- ✅ Source code analysis complete
- ✅ API capabilities documented
- ⏳ Verify HTTP server availability
- ⏳ Test remote API endpoints

### Phase 2: Basic Integration
- Create `retrodebugger_client.py` wrapper
- Add HTTP endpoint validation
- Test SID register read/write
- Document API usage in CLAUDE.md

### Phase 3: Validation Integration
- Add optional RetroDebugger validation step to pipeline
- Implement register state comparison
- Generate validation reports
- Update `complete_pipeline_with_validation.py`

### Phase 4: Advanced Features (Future)
- Waveform capture and comparison
- Interactive debugging mode
- Batch testing automation
- CI/CD integration

---

## Limitations and Considerations

### RetroDebugger Limitations

1. **GUI Dependency**
   - Requires graphical interface
   - No official headless mode
   - May not work on servers without X11

2. **API Availability**
   - HTTP server may need manual enabling
   - Port configuration required
   - Network security considerations

3. **Resource Usage**
   - Full emulator is resource-intensive
   - May slow down batch processing
   - Best used for selected validation cases

### Integration Challenges

1. **Process Lifecycle**
   - Need to start/stop RetroDebugger
   - Handle crashes gracefully
   - Manage multiple instances

2. **State Synchronization**
   - Ensure clean state between tests
   - Reset emulator properly
   - Handle timing issues

3. **Error Handling**
   - Network timeouts
   - API errors
   - Validation failures

---

## Conclusion

RetroDebugger is a powerful C64 debugging tool with excellent SID debugging capabilities. Its remote HTTP/JSON API provides opportunities for integration with SIDM2's validation pipeline, complementing existing tools like SIDwinder and siddump.

**Recommended Next Steps:**

1. ✅ **Immediate:** Test RetroDebugger HTTP API availability
2. **Short-term:** Create Python wrapper for `/c64/sid/` endpoints
3. **Medium-term:** Add optional RetroDebugger validation to pipeline
4. **Long-term:** Develop waveform comparison capabilities

**Value Proposition:**

- **Unique Capability:** Real-time register inspection and waveform visualization
- **Complementary:** Works alongside SIDwinder and siddump
- **Development Aid:** Interactive debugging for tough issues
- **Validation:** Additional accuracy metric beyond binary comparison

**Integration Effort:** Medium (HTTP API integration is straightforward, but requires RetroDebugger setup and testing)

---

## References

- **GitHub Repository:** https://github.com/slajerek/RetroDebugger
- **VICE Emulator:** https://sourceforge.net/projects/vice-emu/
- **reSID Library:** Part of VICE distribution
- **License:** FSF-compatible free software license
- **Author:** Marcin Skoczylas (C) 2016-2024

---

**For detailed source code:** See `C:\Users\mit\Downloads\RetroDebugger-master\RetroDebugger-master\src`

**Key files analyzed:**
- `src/DebugInterface/C64/CDebugInterfaceC64.h` (369 lines)
- `src/Emulators/vice/ViceInterface/CDebugInterfaceVice.h` (409 lines)
- `src/Emulators/vice/ViceInterface/CDebuggerApiVice.h` (164 lines)
- `src/Emulators/vice/ViceInterface/CDebuggerServerApiVice.cpp` (600+ lines)
- `src/Views/C64/CViewC64StateSID.h` (116 lines)
- `README.md` (173 lines)
