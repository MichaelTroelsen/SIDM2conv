# Enhanced SIDM2 Video - Setup Guide

Your video has been upgraded with:
- ✨ **Cool animations** - Particles, gradients, glows, dynamic effects
- 🎨 **Better colors** - Gradients, cyan/green theme, visual depth
- 📸 **Tool screenshots** - SF2 Viewer, Conversion Cockpit, SF2 Editor
- 🎵 **Background music** - SID music or royalty-free track
- 🎬 **New Tools Demo scene** - Shows your actual software

**New Duration**: 65 seconds (was 55 seconds)

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Capture Screenshots
```bash
# Launch each tool and take screenshots

# SF2 Viewer
sf2-viewer.bat
# Press Win+Shift+S, capture window
# Save as: public/assets/screenshots/sf2-viewer.png

# Conversion Cockpit
conversion-cockpit.bat
# Capture and save as: public/assets/screenshots/conversion-cockpit.png

# Tools menu
tools.bat
# Capture and save as: public/assets/screenshots/tools-bat.png
```

**SF2 Editor**: Find a screenshot online or use your own SID Factory II
Save as: `public/assets/screenshots/sf2-editor.png`

### Step 2: Add Background Music
**Option A - Use SID Music** (Recommended!):
```bash
# Convert a nice SID file to audio
tools/SID2WAV.EXE "test_collections/Laxity/YourFavorite.sid" temp.wav

# Convert WAV to MP3 using online tool:
# https://cloudconvert.com/wav-to-mp3

# Save as: public/assets/audio/background-music.mp3
```

**Option B - Download Royalty-Free**:
- Visit: https://studio.youtube.com/ (YouTube Audio Library)
- Filter: Instrumental, Tech/Electronic, 60+ seconds
- Download and save as: `public/assets/audio/background-music.mp3`

### Step 3: Preview & Render
```bash
cd video-demo/sidm2-demo
npm start
# Open http://localhost:3000 - preview the enhanced video!

# When happy, render:
npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4
```

---

## 🎨 What's New

### 1. Enhanced Title Scene
- Radial gradient background
- Animated particles exploding outward
- Pulsing glow effect
- Gradient text with cyan/green colors
- Badge for "99.93% Accuracy"

### 2. New Tools Demo Scene (10 seconds)
Shows 3 tool screenshots side-by-side:
- SF2 Viewer
- Conversion Cockpit
- SID Factory II Editor

With animated particles, glassmorphism effects, and staggered entrances.

### 3. Background Music
- Plays throughout entire video
- Volume: 30% (doesn't overpower narration)
- Fades naturally with video

### 4. Updated Timeline
| Scene          | Start | Duration | New Features                     |
|----------------|-------|----------|----------------------------------|
| Title          | 0s    | 5s       | Particles, gradients, glow       |
| Problem        | 5s    | 8s       | Enhanced animations              |
| Features       | 13s   | 12s      | Better card animations           |
| **Tools Demo** | 25s   | **10s**  | **NEW SCENE** - Screenshots      |
| Workflow       | 35s   | 10s      | Icon animations                  |
| Tech Stack     | 45s   | 8s       | Improved layout                  |
| Results        | 53s   | 7s       | Dynamic stats                    |
| Closing        | 60s   | 5s       | Polished finish                  |

**Total**: 65 seconds (10 seconds longer)

---

## 📁 Required Files

### Screenshots (Required)
All should be 1920x1080 or 1280x720 PNG files:

```
public/assets/screenshots/
├── sf2-viewer.png        ✅ SF2 Viewer GUI
├── conversion-cockpit.png ✅ Conversion Cockpit GUI
├── sf2-editor.png        ✅ SID Factory II editor
└── tools-bat.png         ✅ Tools.bat menu (optional)
```

### Audio (Required)
```
public/assets/audio/
└── background-music.mp3  ✅ 60-70 seconds, instrumental
```

---

## 🎵 Background Music Tips

### Finding Great SID Music
```bash
# Browse your Laxity collection
ls test_collections/Laxity/

# Good candidates (melodic, upbeat):
# - Files with "music", "song", "melody" in name
# - Medium tempo (not too fast/slow)
# - Clear melody (not just bass/drums)
```

### Testing Music
```bash
# Convert and listen first
tools/SID2WAV.EXE input.sid test.wav
# Play test.wav - does it sound good?

# If yes, convert to MP3 and use it!
```

### Music Volume
Default: 30% volume (in `SIDM2Demo.jsx`)
```jsx
<Audio
  src={staticFile('assets/audio/background-music.mp3')}
  volume={0.3}  // Adjust 0.0-1.0
  startFrom={0}
/>
```

---

## 📸 Screenshot Capture Guide

### Windows Built-in Tools
1. **Snipping Tool** - Win + Shift + S
2. **Snip & Sketch** - Win + Shift + S (Windows 10/11)
3. **Print Screen** - Capture full screen, paste in Paint

### Recommended: ShareX (Free)
- Download: https://getsharex.com/
- Auto-save screenshots
- Built-in editor
- Hotkey customization

### Best Practices
✅ Use highest resolution (1920x1080)
✅ Clean up desktop/taskbar before capturing
✅ Ensure text is readable
✅ Show typical use case (file loaded, data visible)
✅ Good lighting/contrast
✅ Crop to just the application window

❌ Don't include sensitive data
❌ Don't use low resolution
❌ Don't capture empty windows

---

## 🎬 Preview Before Rendering

```bash
cd video-demo/sidm2-demo
npm start
```

Open http://localhost:3000 and:
1. ✅ Check all screenshots load correctly
2. ✅ Verify background music plays
3. ✅ Watch full video (65 seconds)
4. ✅ Look for any placeholder text/missing images
5. ✅ Check timing and transitions

If everything looks good → Render!

---

## 🚀 Rendering Options

### Standard Quality (Default)
```bash
npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4
```

### High Quality (Best for sharing)
```bash
npx remotion render SIDM2Demo out/sidm2-demo-hq.mp4 --quality=100
```

### Quick Preview (Fast render for testing)
```bash
npx remotion render SIDM2Demo out/preview.mp4 --quality=50 --frames=0-300
```

### Different Format
```bash
npx remotion render SIDM2Demo out/sidm2-demo.webm --codec=vp9
```

---

## ⚠️ Troubleshooting

### "Cannot find module 'assets/...'"
→ Make sure files are in correct folders:
  - `public/assets/screenshots/`
  - `public/assets/audio/`

### Screenshots don't appear
→ Check file names exactly match:
  - `sf2-viewer.png` (not `SF2-Viewer.PNG`)
  - Case sensitive on some systems

### Background music doesn't play
→ Ensure:
  - File is named `background-music.mp3`
  - File is in `public/assets/audio/`
  - File is MP3 format (not WAV, OGG, etc.)

### Placeholder emojis instead of screenshots
→ Screenshot files missing or wrong names
→ Check browser console for errors (F12)

### Video too large
→ Reduce quality: `--quality=80`
→ Or use WebM: `--codec=vp9`

---

## 💡 Optional Enhancements

### Add More Screenshots
Edit `src/scenes/ToolsDemoScene.jsx`:
```jsx
const tools = [
  { name: 'SF2 Viewer', ... },
  { name: 'Conversion Cockpit', ... },
  { name: 'SID Factory II', ... },
  { name: 'Your New Tool', desc: 'Description', image: 'screenshots/new-tool.png', delay: 220 },
];
```

### Adjust Music Volume
Edit `src/SIDM2Demo.jsx`:
```jsx
<Audio
  src={staticFile('assets/audio/background-music.mp3')}
  volume={0.5}  // Louder (was 0.3)
  startFrom={0}
/>
```

### Change Color Scheme
Current: Cyan (#00ddff) + Green (#00ff88)

To change globally, search and replace in all scene files:
- `#00ff88` → Your primary color
- `#00ddff` → Your secondary color
- `#0f0f1e` → Your background color

---

## 📚 Documentation

- **Capture Guide**: `MEDIA-CAPTURE-GUIDE.md` - Detailed instructions
- **Quick Start**: `QUICK-START.md` - Basic commands
- **Full README**: `README.md` - Complete guide

---

## ✅ Checklist

Before rendering final video:

- [ ] All 4 screenshots captured and saved
- [ ] Background music file added (60+ seconds)
- [ ] Previewed in Remotion Studio (npm start)
- [ ] All scenes look correct
- [ ] Music volume is good (not too loud/quiet)
- [ ] No placeholder emojis visible
- [ ] Total duration is 65 seconds
- [ ] Ready to render!

---

**Once setup**: The video will look professional with cool animations, your actual tool screenshots, and authentic SID music! 🎬✨

**Estimated setup time**: 15-30 minutes (mostly screenshot capture)
