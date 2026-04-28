# SIDM2 Video Creation Guide

**Complete Guide to Creating Demonstration Videos for SIDM2**

**Version**: 1.0 | **Created**: 2025-12-26 | **Status**: Production Ready

---

## Overview

This guide documents the complete automated pipeline for creating demonstration videos for the SIDM2 project using Remotion (React-based video creation framework).

**Output**: Professional 65-second Full HD (1920x1080) demo video with:
- Animated title sequences
- Feature demonstrations
- Tool screenshots
- Background music (authentic C64 SID music)
- Closing scene with project information

**Result**: `video-demo/sidm2-demo/out/sidm2-demo-enhanced.mp4` (6.2 MB)

---

## Quick Start

### Prerequisites

- Node.js 24.11.1+ and npm 11.6.2+
- Python 3.14+
- Windows OS (for current implementation)

### One-Command Setup

```bash
# 1. Install ffmpeg and set up all assets
setup-video-assets.bat

# 2. Render video
cd video-demo/sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4
```

**Total time**: ~5 minutes (including download)
**Output**: `video-demo/sidm2-demo/out/sidm2-demo-enhanced.mp4`

---

## Architecture

### Complete Pipeline

```
SID File (Laxity .sid)
    ↓
SID2WAV.EXE (70 seconds)
    ↓
WAV File (3.0 MB)
    ↓
ffmpeg (high quality MP3 encoding)
    ↓
MP3 File (1.1 MB)
    ↓
Remotion (React components + assets)
    ↓
Final MP4 Video (6.2 MB, 1920x1080)
```

### Key Components

1. **Asset Pipeline** (`pyscript/setup_video_assets.py`)
   - Automated SID → WAV → MP3 conversion
   - Screenshot capture automation
   - Asset verification

2. **Video Framework** (Remotion 4.0)
   - React-based scene composition
   - Programmatic animations
   - Audio/video synchronization

3. **Scene Components** (`video-demo/sidm2-demo/src/scenes/`)
   - TitleScene: Animated title with particles
   - ProblemScene: Problem statement
   - FeaturesScene: Key features
   - ToolsDemoScene: Tool screenshots
   - WorkflowScene: Conversion workflow
   - TechStackScene: Technical details
   - ResultsScene: Performance metrics
   - ClosingScene: Project information

---

## Installation

### 1. Install ffmpeg (Automated)

```bash
# Run the automated installer
install-ffmpeg.bat

# Or manually:
python pyscript/install_ffmpeg.py
```

**What it does**:
- Downloads ffmpeg Windows build (198 MB)
- Extracts to `tools/ffmpeg/`
- Verifies installation
- Updates pipeline to use local ffmpeg

**Location**: `tools/ffmpeg/bin/ffmpeg.exe` (184 MB)

### 2. Install Remotion Project

```bash
cd video-demo/sidm2-demo
npm install
```

**Dependencies** (from package.json):
- `remotion`: ^4.0.395
- `react`: ^19.2.3
- `react-dom`: ^19.2.3
- `@remotion/cli`: ^4.0.395

---

## Asset Creation Pipeline

### Automated Asset Generation

The `setup_video_assets.py` script automates the entire asset creation process:

```bash
# Run the complete pipeline
setup-video-assets.bat

# Or directly:
python pyscript/setup_video_assets.py
```

### Pipeline Steps

**Step 1: Find SID File**
- Searches for Stinsens_Last_Night_of_89.sid
- Locations checked: `Laxity/`, `learnings/`, `SID/`, `tools/`

**Step 2: Convert SID → WAV**
- Tool: `vsid.exe` (VICE SID Player from C:\winvice\bin or tools/vice/bin)
- Duration: 240 seconds / 4 minutes (stopped via timeout)
- Output: `video-demo/sidm2-demo/temp/background-music.wav` (~23 MB)
- Format: 48kHz 16-bit PCM WAV
- Note: VSID runs indefinitely; script uses timeout to stop it after 240 seconds

**Step 3: Convert WAV → MP3**
- Tool: `tools/ffmpeg/bin/ffmpeg.exe`
- Script: `pyscript/wav_to_mp3.py`
- Quality: 192 kbps (high quality)
- Output: `video-demo/sidm2-demo/public/assets/audio/background-music.mp3` (1.1 MB)

**Step 4: Capture Screenshots**
- Script: `pyscript/capture_screenshots.py`
- Automation: Uses pyautogui + PIL
- Outputs:
  - `sf2-viewer.png` (230 KB) - SF2 Viewer GUI
  - `conversion-cockpit.png` (478 KB) - Conversion Cockpit GUI
  - `sf2-editor.png` (35 KB) - Placeholder for SID Factory II

**Step 5: Verify Assets**
- Checks all required files exist
- Verifies file sizes
- Reports missing assets

### Manual Asset Creation (Optional)

If automation fails, assets can be created manually:

**Screenshots**:
1. Press `Win + Shift + S` (Windows Snipping Tool)
2. Capture window area
3. Save to `video-demo/sidm2-demo/public/assets/screenshots/`

**Audio Conversion**:
- Online: https://cloudconvert.com/wav-to-mp3
- VLC: Media → Convert/Save → Choose MP3 codec

---

## Video Rendering

### Development Preview

```bash
cd video-demo/sidm2-demo
npm start
```

Opens preview server at: http://localhost:3000

**Features**:
- Live reload on code changes
- Frame-by-frame scrubbing
- Timeline controls
- Scene inspection

### Production Render

```bash
cd video-demo/sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4
```

**Render Settings**:
- Composition: SIDM2Demo
- Duration: 1950 frames (65 seconds at 30 fps)
- Resolution: 1920x1080 (Full HD)
- Codec: H.264
- Concurrency: 6x parallel rendering

**Render Time**: ~30 seconds (on modern hardware)

**Output**: `video-demo/sidm2-demo/out/sidm2-demo-enhanced.mp4` (6.2 MB)

---

## Video Structure

### Scene Timeline (65 seconds total)

| Scene | Frames | Duration | Description |
|-------|--------|----------|-------------|
| Title | 0-150 | 5s | Animated title with particles |
| Problem | 150-300 | 5s | Problem statement |
| Features | 300-450 | 5s | Key features (3 highlights) |
| Workflow | 450-750 | 10s | Conversion workflow diagram |
| Tools Demo | 750-1050 | 10s | Tool screenshots showcase |
| Tech Stack | 1050-1350 | 10s | Technical details |
| Results | 1350-1650 | 10s | Performance metrics |
| Closing | 1650-1950 | 10s | Project info & links |

### Animation Techniques

**Title Scene**:
- Particle explosion (30 particles)
- Radial gradient background
- Gradient text effect
- Pulsing glow animation

**Tools Demo Scene**:
- Glassmorphism UI effects
- Staggered entrance animations
- Floating background particles
- Screenshot showcase with labels

**Other Scenes**:
- Slide-in animations
- Fade transitions
- Color gradients
- Dynamic text effects

---

## File Structure

```
SIDM2/
├── video-demo/
│   └── sidm2-demo/
│       ├── src/
│       │   ├── Root.jsx              # Composition registration
│       │   ├── SIDM2Demo.jsx         # Main timeline
│       │   └── scenes/               # Individual scene components
│       │       ├── TitleScene.jsx
│       │       ├── ToolsDemoScene.jsx
│       │       ├── ProblemScene.jsx
│       │       ├── FeaturesScene.jsx
│       │       ├── WorkflowScene.jsx
│       │       ├── TechStackScene.jsx
│       │       ├── ResultsScene.jsx
│       │       └── ClosingScene.jsx
│       ├── public/
│       │   └── assets/
│       │       ├── audio/
│       │       │   └── background-music.mp3  # 1.1 MB, 70s
│       │       └── screenshots/
│       │           ├── sf2-viewer.png        # 230 KB
│       │           ├── conversion-cockpit.png # 478 KB
│       │           └── sf2-editor.png        # 35 KB (placeholder)
│       ├── temp/
│       │   └── background-music.wav          # 3.0 MB (intermediate)
│       ├── out/
│       │   └── sidm2-demo-enhanced.mp4       # 6.2 MB (final output)
│       ├── package.json              # Remotion dependencies
│       └── remotion.config.ts        # Remotion configuration
├── pyscript/
│   ├── setup_video_assets.py        # Master pipeline script
│   ├── wav_to_mp3.py                 # WAV → MP3 converter
│   ├── capture_screenshots.py        # Screenshot automation
│   └── install_ffmpeg.py             # ffmpeg installer
├── tools/
│   ├── ffmpeg/
│   │   └── bin/
│   │       └── ffmpeg.exe            # 184 MB
│   └── SID2WAV.EXE                   # SID → WAV converter
├── install-ffmpeg.bat                # ffmpeg installer launcher
└── setup-video-assets.bat            # Asset pipeline launcher
```

---

## Customization

### Modify Video Content

**Edit Scene Duration**:
```javascript
// In SIDM2Demo.jsx
<Sequence from={0} durationInFrames={150}>  // 5 seconds
  <TitleScene />
</Sequence>
```

**Change Video Length**:
```javascript
// In Root.jsx
<Composition
  id="SIDM2Demo"
  component={SIDM2Demo}
  durationInFrames={1950}  // 65 seconds at 30fps
  fps={30}
  width={1920}
  height={1080}
/>
```

**Modify Animations**:
```javascript
// In any scene component
const opacity = interpolate(
  frame,
  [0, 30],      // Frame range
  [0, 1],       // Value range
  { extrapolateRight: 'clamp' }
);
```

### Replace Assets

**Background Music**:
1. Convert new SID file: `python scripts/sid_to_sf2.py newsong.sid`
2. Convert to WAV: `tools/SID2WAV.EXE newsong.sid output.wav -t70`
3. Convert to MP3: `python pyscript/wav_to_mp3.py output.wav assets/audio/background-music.mp3`

**Screenshots**:
1. Capture new screenshot
2. Save to `public/assets/screenshots/`
3. Update filename in `ToolsDemoScene.jsx`

---

## Troubleshooting

### Issue: Video Render Fails

**Symptoms**: Error during `npx remotion render`

**Solutions**:
1. Check all assets exist: `ls public/assets/audio/` and `ls public/assets/screenshots/`
2. Verify Node.js version: `node --version` (should be 24.11.1+)
3. Reinstall dependencies: `cd video-demo/sidm2-demo && npm install`
4. Check console for specific error messages

### Issue: Audio Not Playing

**Symptoms**: Video renders but no sound

**Solutions**:
1. Verify MP3 exists: `ls public/assets/audio/background-music.mp3`
2. Check MP3 size: Should be ~1.1 MB
3. Test MP3 playback in media player
4. Verify Audio component in SIDM2Demo.jsx

### Issue: Screenshots Missing

**Symptoms**: Placeholder images or errors

**Solutions**:
1. Run screenshot capture: `python pyscript/capture_screenshots.py`
2. Manually capture with Win+Shift+S
3. Check file permissions
4. Verify file paths in ToolsDemoScene.jsx

### Issue: ffmpeg Not Found

**Symptoms**: WAV to MP3 conversion fails

**Solutions**:
1. Run: `install-ffmpeg.bat`
2. Verify: `tools/ffmpeg/bin/ffmpeg.exe --version`
3. Check `wav_to_mp3.py` finds local ffmpeg
4. Manually download from: https://github.com/BtbN/FFmpeg-Builds/releases

---

## Performance

### Asset Pipeline Performance

| Step | Duration | Output Size |
|------|----------|-------------|
| SID → WAV (VSID) | ~240-250s (4 min) | ~23 MB |
| WAV → MP3 | ~3-5s | ~3.7 MB |
| Screenshot Capture | ~15s | 743 KB total |
| **Total Pipeline** | **~260s (4.3 min)** | **~4.5 MB assets** |

**Note**: VSID conversion takes the full 240 seconds of playback time (real-time audio capture)

### Video Render Performance

| Hardware | Render Time | Frame Rate |
|----------|-------------|------------|
| Modern (6-core) | ~30s | 65 fps |
| Average (4-core) | ~45s | 43 fps |
| Older (2-core) | ~90s | 22 fps |

**Note**: Remotion uses parallel rendering (6x concurrency by default)

---

## Advanced Topics

### Custom Codecs

```bash
# Render with different codec
npx remotion render SIDM2Demo out/video.mp4 --codec h265

# Adjust quality
npx remotion render SIDM2Demo out/video.mp4 --crf 18
```

### Different Resolutions

```javascript
// In Root.jsx
<Composition
  width={3840}   // 4K
  height={2160}
/>
```

### Export Individual Scenes

```bash
# Render only frames 750-1050 (Tools Demo scene)
npx remotion render SIDM2Demo out/tools-demo.mp4 --frames=750-1050
```

### Add New Scenes

1. Create new scene component in `src/scenes/NewScene.jsx`
2. Import in `SIDM2Demo.jsx`
3. Add Sequence with frame range
4. Update total duration in `Root.jsx`

---

## Dependencies

### Python Packages

- **Required**: None (uses standard library)
- **Optional**:
  - `pillow`: Screenshot creation (auto-installed)
  - `pyautogui`: Screenshot automation (auto-installed)

### External Tools

- **ffmpeg**: Audio conversion (auto-installed to `tools/ffmpeg/`)
- **VSID (VICE)**: SID to WAV conversion (from C:\winvice\bin or auto-installed to `tools/vice/`)
  - Install: `python pyscript/install_vice.py` or use existing installation

### Node.js Packages

See `video-demo/sidm2-demo/package.json`:
- `remotion`: ^4.0.395
- `react`: ^19.2.3
- `react-dom`: ^19.2.3
- `@remotion/cli`: ^4.0.395

---

## Version History

### v1.0 (2025-12-26)

**Initial Release**:
- Complete automated asset pipeline
- ffmpeg integration
- 8 scene compositions
- 65-second Full HD output
- Background music support
- Tool screenshot integration
- Professional animations

**Features**:
- One-command setup (`setup-video-assets.bat`)
- Automated ffmpeg installation
- Screenshot capture automation
- Complete documentation

---

## References

- **Remotion Documentation**: https://www.remotion.dev/docs
- **ffmpeg Documentation**: https://ffmpeg.org/documentation.html
- **React Documentation**: https://react.dev/

---

## Support

**Issues**: See `docs/guides/TROUBLESHOOTING.md`

**Questions**: Check documentation in `video-demo/sidm2-demo/`:
- `README.md` - Complete project documentation
- `QUICK-START.md` - Quick reference
- `SETUP-ENHANCED-VIDEO.md` - Setup guide

---

**End of Video Creation Guide**
