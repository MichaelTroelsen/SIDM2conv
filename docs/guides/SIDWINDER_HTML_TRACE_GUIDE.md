# SIDwinder HTML Trace - User Guide

**Version**: 1.0.0
**Created**: 2026-01-01

Interactive HTML visualization for SID register traces with frame-by-frame analysis.

---

## 🚀 Quick Start

### Generate Trace HTML

```bash
# Basic usage (300 frames default) - Windows
trace-viewer.bat input.sid

# Specify output file - Windows
trace-viewer.bat input.sid -o trace.html

# Custom frame count - Windows
trace-viewer.bat input.sid -f 1000

# Complete example - Windows
trace-viewer.bat SID/Beast.sid -o beast_trace.html -f 500

# Direct Python (cross-platform)
python pyscript/sidwinder_html_exporter.py input.sid
python pyscript/sidwinder_html_exporter.py input.sid -o trace.html -f 500
```

### From Python

```python
from pyscript.sidwinder_html_exporter import export_trace_to_html
from pyscript.sidtracer import SIDTracer

# Create tracer
tracer = SIDTracer("input.sid", verbose=0)

# Generate trace data
trace_data = tracer.trace(frames=300)

# Export to HTML
export_trace_to_html(
    trace_data=trace_data,
    output_path="trace.html",
    sid_name=tracer.header.name
)
```

---

## 📊 Trace Sections

### 1. **Overview**
- SID file information (name, author)
- Total frames traced
- Total CPU cycles executed
- Quick navigation sidebar

### 2. **Statistics**
Six metric cards:
- **Total Writes**: All register writes (init + frames)
- **Init Writes**: Initialization writes
- **Avg/Frame**: Average writes per frame
- **Max/Frame**: Maximum writes in any single frame
- **Min/Frame**: Minimum writes in any single frame
- **Total Cycles**: Total CPU cycles executed

### 3. **Frame Timeline**
Interactive timeline with two components:

**Slider**:
- Drag to navigate frames
- Shows current frame number
- Instant update

**Activity Bars**:
- Visual representation of write activity
- Height = number of register writes
- Click bar to jump to that frame
- Hover for frame number and write count

### 4. **Frame Viewer**
Current frame's register writes:
- Color-coded by register group
- Shows register address ($D4XX)
- Shows register value ($XX)
- Hover for register name

### 5. **Register States**
Live SID register values organized by group:
- **Voice 1**: 7 registers ($D400-$D406)
- **Voice 2**: 7 registers ($D407-$D40D)
- **Voice 3**: 7 registers ($D40E-$D414)
- **Filter**: 4 registers ($D415-$D418)

Registers highlight (yellow flash) when changed.

---

## 🎮 Interactive Features

### Timeline Navigation

**Slider**:
1. Click and drag slider thumb
2. Current frame updates in real-time
3. Frame writes display updates
4. Register states update

**Timeline Bars**:
1. Click any bar
2. Jumps to that frame instantly
3. Useful for finding active frames

**Keyboard**:
- Arrow keys: Navigate slider (if focused)
- Tab: Move focus
- Enter: Activate focused element

### Register Highlighting

When frame changes:
1. Register values update
2. Changed registers flash yellow
3. Fade back to normal after 0.5s
4. Visual feedback for changes

### Hover Information

**Timeline Bars**:
- Shows: "Frame X: Y writes"
- Helps identify busy frames

**Register Writes**:
- Shows full register name
- Example: "Voice 1: Frequency Lo"

---

## 🎨 Color Coding

### Register Groups

**Voice 1** (Red border):
- Frequency Lo/Hi
- Pulse Width Lo/Hi
- Control Register
- Attack/Decay
- Sustain/Release

**Voice 2** (Blue border):
- Same as Voice 1, different voice

**Voice 3** (Green border):
- Same as Voice 1, different voice

**Filter** (Orange border):
- Cutoff Frequency Lo/Hi
- Resonance/Routing
- Mode/Volume

**Other** (Gray border):
- Paddle inputs
- Oscillator/Envelope outputs

### Write Items

In Frame Viewer, writes have colored left border:
- **Red**: Voice 1 writes
- **Blue**: Voice 2 writes
- **Green**: Voice 3 writes
- **Orange**: Filter writes
- **Gray**: Other writes

---

## 📖 Understanding SID Registers

### Voice Registers (×3)

Each voice has 7 registers:

**$D4X0/$D4X1 - Frequency**:
- 16-bit frequency value
- Lo byte ($D4X0), Hi byte ($D4X1)
- Controls pitch

**$D4X2/$D4X3 - Pulse Width**:
- 12-bit pulse width value
- Used for pulse waveform
- Lo byte ($D4X2), Hi byte ($D4X3)

**$D4X4 - Control Register**:
- Bit 0: Gate (on/off)
- Bit 1: Sync
- Bit 2: Ring modulation
- Bit 3: Test
- Bit 4-7: Waveform select

**$D4X5 - Attack/Decay**:
- High nibble: Attack rate
- Low nibble: Decay rate

**$D4X6 - Sustain/Release**:
- High nibble: Sustain level
- Low nibble: Release rate

### Filter Registers

**$D415/$D416 - Cutoff Frequency**:
- 11-bit cutoff frequency
- Controls filter cutoff point

**$D417 - Resonance/Routing**:
- Bit 0-2: Voice routing to filter
- Bit 4-7: Resonance

**$D418 - Mode/Volume**:
- Bit 0-3: Master volume
- Bit 4-6: Filter mode (LP/BP/HP)
- Bit 7: Voice 3 off

---

## 💡 Use Cases

### 1. **Debug Music Player Code**

```
Goal: Understand why music sounds wrong
Steps:
1. Generate trace with 300 frames
2. Navigate to problematic frame
3. Check register writes:
   - Are frequencies correct?
   - Is gate triggered properly?
   - Are waveforms set correctly?
4. Compare with expected values
5. Identify bug in player code
```

### 2. **Analyze Music Pattern**

```
Goal: Understand how music is structured
Steps:
1. Generate trace with 1000 frames
2. Navigate through timeline
3. Observe register write patterns:
   - When does melody start?
   - How often do notes change?
   - Which voices are used?
4. Document music structure
```

### 3. **Compare Player Implementations**

```
Goal: Compare original vs converted player
Steps:
1. Trace original SID (300 frames)
2. Trace converted SF2 (300 frames)
3. Open both HTML files
4. Navigate to same frame in both
5. Compare register writes
6. Identify differences
7. Fix conversion code
```

### 4. **Performance Analysis**

```
Goal: Optimize player code
Steps:
1. Generate trace
2. Look at timeline bars
3. Find frames with many writes
4. Check if writes are necessary
5. Optimize code to reduce writes
```

### 5. **Learn SID Programming**

```
Goal: Understand SID chip programming
Steps:
1. Trace simple test SID
2. Navigate frame by frame
3. Observe how registers change:
   - Gate on → Note starts
   - Frequency sets pitch
   - Waveform shapes sound
   - ADSR envelope controls volume
4. Experiment with own code
```

---

## 🔍 Analysis Techniques

### Finding Gate Events

Gate on/off events control note starts:

1. Navigate through frames
2. Watch for $D404, $D40B, $D412 (control registers)
3. Value with bit 0 set = gate on (note start)
4. Value with bit 0 clear = gate off (note end)

Example:
```
Frame 10: $D404 = $21  (gate on, triangle wave)
Frame 50: $D404 = $20  (gate off, note ends)
```

### Tracking Pitch Changes

Monitor frequency registers:

1. Watch $D400/$D401 (Voice 1 frequency)
2. Note frequency changes
3. Calculate pitch from frequency value
4. Map to musical notes

Formula:
```
Frequency = (FCLK / 16777216) × Register_Value
Note = 12 × log2(Frequency / 440Hz) + 69
```

### Identifying Waveforms

Control register bits 4-7 select waveform:

- **$10**: Triangle
- **$20**: Sawtooth
- **$40**: Pulse
- **$80**: Noise
- **$11**: Triangle + Noise (combined)

Watch control registers to see waveform changes.

### Analyzing Envelopes

Attack/Decay and Sustain/Release shape volume:

1. Find note start (gate on)
2. Check $D405 (Attack/Decay)
3. Check $D406 (Sustain/Release)
4. Observe how sound evolves

---

## 🛠️ Advanced Usage

### Exporting Frame Data

While HTML is interactive, you can extract data:

```javascript
// Open browser DevTools console
// Get all writes for frame 50
const frame50 = frameData[50];
console.table(frame50.map(w => ({
    register: '$D4' + w.reg.toString(16).toUpperCase().padStart(2, '0'),
    value: '$' + w.value.toString(16).toUpperCase().padStart(2, '0')
})));

// Export to CSV
const csv = frame50.map(w =>
    `D4${w.reg.toString(16).toUpperCase().padStart(2, '0')},` +
    `${w.value.toString(16).toUpperCase().padStart(2, '0')}`
).join('\n');
console.log(csv);
```

### Comparing Frames

Compare two frames manually:

1. Navigate to frame A
2. Note register values
3. Navigate to frame B
4. Compare register values
5. Identify differences

Or use browser DevTools:
```javascript
function compareFrames(frameA, frameB) {
    const diff = [];
    // Compare register writes
    // (Implementation left as exercise)
    return diff;
}
```

### Animation Playback

For automatic frame-by-frame playback:

```javascript
// Open DevTools console
let currentFrame = 0;
const interval = setInterval(() => {
    document.getElementById('frameSlider').value = currentFrame;
    document.getElementById('frameSlider').dispatchEvent(new Event('input'));
    currentFrame++;
    if (currentFrame >= frameData.length) clearInterval(interval);
}, 100);  // 100ms per frame = 10 FPS
```

---

## 📊 Example Analysis

### Case Study: Beast.sid

```bash
# Generate trace
python pyscript/sidwinder_html_exporter.py SID/Beast.sid -f 300 -o beast.html

# Open in browser
```

**Observations**:
1. **Frame 0-10**: Initialization
   - Heavy register writes
   - Sets up all 3 voices
   - Configures filter

2. **Frame 11+**: Music starts
   - Regular pattern every 4 frames
   - Voice 1: Melody (frequent frequency changes)
   - Voice 2: Bass (lower frequencies)
   - Voice 3: Arpeggio (rapid frequency changes)

3. **Timeline bars**: Even distribution
   - Consistent write activity
   - ~10-15 writes per frame
   - No gaps (continuous music)

4. **Register patterns**:
   - Voice 1: Triangle wave ($10)
   - Voice 2: Pulse wave ($40)
   - Voice 3: Sawtooth wave ($20)
   - Filter: Low-pass mode

---

## 🐛 Troubleshooting

### Timeline Not Interactive

**Cause**: JavaScript disabled

**Solution**: Enable JavaScript in browser

### Registers Not Updating

**Cause**: Browser compatibility issue

**Solution**: Use modern browser (Chrome, Firefox, Edge)

### Slow Performance

**Cause**: Too many frames (>1000)

**Solution**:
- Reduce frame count
- Timeline auto-scales to ~500 bars
- Use fewer frames for analysis

### Missing Register Names

**Cause**: Hover tooltip not working

**Solution**:
- Check browser supports hover
- Try clicking instead of hovering
- Check browser console for errors

---

## 🎯 Best Practices

### 1. **Start Small**
- Begin with 100-300 frames
- Increase if needed
- Avoid >1000 frames for interactive use

### 2. **Use Timeline Effectively**
- Scan activity bars first
- Jump to busy frames
- Focus analysis where activity changes

### 3. **Document Findings**
- Screenshot interesting frames
- Note register patterns
- Document frame numbers

### 4. **Compare Systematically**
- Use same frame count for comparisons
- Compare same frame numbers
- Document differences

### 5. **Learn Incrementally**
- Start with single voice
- Add complexity gradually
- Test understanding with own SIDs

---

## 📚 See Also

- **SIDwinder Guide**: `docs/implementation/SIDWINDER_PYTHON_DESIGN.md` - Technical design
- **Siddump Guide**: `docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md` - Frame dump tool
- **SID Format**: `docs/reference/SID_FORMAT.md` - SID file format specification
- **6502 Emulator**: `sidm2/cpu6502_emulator.py` - Emulation details

---

## 🎵 SID Programming Resources

### Online Resources

- **SID Chip Datasheet**: Complete register documentation
- **HVSC**: High Voltage SID Collection (test files)
- **CSDb**: C64 Scene Database (SID files and info)

### Recommended Test Files

Start with these well-structured SIDs:
1. Simple test tunes (single voice)
2. NP20 player files (structured)
3. Laxity NewPlayer files (complex)

---

## 💡 Tips & Tricks

1. **Quick Navigation**: Click timeline bars to jump frames
2. **Find Changes**: Look for yellow flashes in register table
3. **Pattern Recognition**: Regular timeline bars = consistent music
4. **Debugging**: Compare frame N with frame N-1 for changes
5. **Learning**: Trace simple SIDs first, then complex ones
6. **Performance**: Use 300 frames for interactive analysis
7. **Archiving**: HTML files work offline, perfect for documentation
8. **Sharing**: Send single file to collaborators
9. **Screenshots**: Capture frames for tutorials
10. **Browser Zoom**: Adjust text size for readability

---

## 🆕 Future Enhancements

Potential future features:
- Waveform visualization
- Audio playback synchronized with frames
- Frame comparison diff view
- Export to various formats
- Filter by register type
- Register change history
- Automated pattern detection

---

**End of Guide** - Master SID register analysis! 🎮
