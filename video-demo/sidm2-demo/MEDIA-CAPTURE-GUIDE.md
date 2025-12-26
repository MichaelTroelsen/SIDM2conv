# Media Capture Guide for SIDM2 Video

This guide explains how to capture screenshots, videos, and audio for the enhanced SIDM2 demo video.

## 📁 File Organization

All media files go in: `public/assets/`

```
public/
└── assets/
    ├── screenshots/
    │   ├── sf2-viewer.png
    │   ├── sf2-editor.png
    │   ├── conversion-cockpit.png
    │   └── tools-bat.png
    ├── videos/
    │   ├── sf2-viewer-demo.mp4
    │   └── conversion-demo.mp4
    └── audio/
        └── background-music.mp3
```

---

## 🎥 1. Capture Tool Screenshots

### SF2 Viewer
```bash
# Launch SF2 Viewer
sf2-viewer.bat

# Or with a specific file
sf2-viewer.bat "path/to/file.sf2"
```

**What to capture**:
- Main window showing file loaded
- Table data visible
- Clear, readable interface
- Suggested size: 1920x1080 or 1280x720

**Save as**: `public/assets/screenshots/sf2-viewer.png`

### Conversion Cockpit GUI
```bash
# Launch Conversion Cockpit
conversion-cockpit.bat
```

**What to capture**:
- Main window with controls
- File browser visible
- Progress indicators (if possible)
- Clean interface view

**Save as**: `public/assets/screenshots/conversion-cockpit.png`

### Tools.bat Menu
```bash
# Launch Tools menu
tools.bat
```

**What to capture**:
- Menu with all options visible
- Clear text, good contrast
- Full menu window

**Save as**: `public/assets/screenshots/tools-bat.png`

### SF2 Editor (SID Factory II)
**Option 1**: Use existing SF2 file
```bash
# Open a converted SF2 file in SID Factory II
# (If you have it installed)
```

**Option 2**: Find reference images online
- Search for "SID Factory II screenshot"
- Ensure image is appropriately licensed

**What to show**:
- Main editing interface
- Pattern/sequence view
- Professional music production tool

**Save as**: `public/assets/screenshots/sf2-editor.png`

---

## 📹 2. Capture Tool Videos (Optional)

### Screen Recording Tools

**Windows**:
- **Xbox Game Bar** (Built-in): Win + G
- **OBS Studio** (Free): https://obsproject.com/
- **ShareX** (Free): https://getsharex.com/

**Recommended Settings**:
- Resolution: 1920x1080 or 1280x720
- Frame rate: 30fps
- Duration: 5-10 seconds per clip
- Format: MP4 (H.264)

### SF2 Viewer Demo Video
1. Start recording
2. Launch SF2 Viewer
3. Load an SF2 file
4. Show table scrolling
5. Navigate tabs
6. Stop recording (5-10 seconds total)

**Save as**: `public/assets/videos/sf2-viewer-demo.mp4`

### Conversion Demo Video
1. Start recording
2. Launch Conversion Cockpit
3. Select input file
4. Click convert button
5. Show progress
6. Show completion
7. Stop recording (8-12 seconds total)

**Save as**: `public/assets/videos/conversion-demo.mp4`

---

## 🎵 3. Add Background Music

### Option 1: Use SID Music (Recommended!)
This showcases your actual project output:

```bash
# Convert a SID file to WAV
tools/SID2WAV.EXE input.sid output.wav

# Or use Python siddump to export audio
python pyscript/siddump_complete.py music.sid -t55
```

Then convert WAV to MP3:
- Use online converter: https://cloudconvert.com/wav-to-mp3
- Or Audacity (free): https://www.audacityteam.org/

**Best SID files for background music**:
- Look in `test_collections/Laxity/` for melodic tracks
- Choose upbeat, non-distracting music
- Duration: ~60 seconds (slightly longer than video)

**Save as**: `public/assets/audio/background-music.mp3`

### Option 2: Royalty-Free Music
Free music sources:
- **YouTube Audio Library**: https://studio.youtube.com/
- **Free Music Archive**: https://freemusicarchive.org/
- **Incompetech**: https://incompetech.com/music/royalty-free/

**Requirements**:
- Upbeat, tech-focused
- No vocals (instrumental only)
- 60 seconds duration
- MP3 or WAV format

**Save as**: `public/assets/audio/background-music.mp3`

---

## 📸 Screenshot Tips

### Windows Screenshot Tools
1. **Snipping Tool** (Built-in): Win + Shift + S
2. **ShareX** (Advanced, free): Auto-upload, editing
3. **Greenshot** (Simple, free): Quick captures

### Best Practices
- **Resolution**: At least 1280x720, prefer 1920x1080
- **Format**: PNG for screenshots (better quality)
- **Clarity**: Ensure text is readable
- **Lighting**: Use light mode if interface is easier to read
- **Crop**: Remove unnecessary UI elements (taskbar, etc.)
- **Clean**: Close extra windows, hide sensitive info

---

## 🎬 Quick Capture Checklist

### Screenshots (Required)
- [ ] SF2 Viewer - `sf2-viewer.png`
- [ ] Conversion Cockpit - `conversion-cockpit.png`
- [ ] SF2 Editor - `sf2-editor.png`
- [ ] Tools.bat menu - `tools-bat.png`

### Videos (Optional)
- [ ] SF2 Viewer demo - `sf2-viewer-demo.mp4`
- [ ] Conversion demo - `conversion-demo.mp4`

### Audio
- [ ] Background music - `background-music.mp3` (60 seconds)

---

## 🚀 After Capturing

1. **Create folders**:
```bash
cd video-demo/sidm2-demo
mkdir -p public/assets/screenshots
mkdir -p public/assets/videos
mkdir -p public/assets/audio
```

2. **Copy files** to appropriate folders

3. **Re-render video**:
```bash
npm start  # Preview in browser first
npx remotion render SIDM2Demo out/sidm2-demo.mp4
```

---

## 📏 Recommended Specifications

| Media Type | Format | Resolution | Duration | Size |
|------------|--------|------------|----------|------|
| Screenshots | PNG | 1920x1080 | N/A | <2MB |
| Videos | MP4 (H.264) | 1920x1080 | 5-10s | <10MB |
| Audio | MP3 | N/A | 60s | <2MB |

---

## 🆘 Troubleshooting

**Screenshots too large?**
- Use PNG compression tools: TinyPNG, PNGGauntlet
- Or save as JPG (quality 85-90%)

**Videos too large?**
- Reduce resolution to 1280x720
- Use HandBrake to compress: https://handbrake.fr/

**Can't capture SF2 Editor?**
- Use placeholder image
- Search Google Images with "site:reddit.com SID Factory II"
- Check SID Factory II documentation

---

## 💡 Pro Tips

1. **SID Music**: Using actual converted SID music as background makes the video authentic!
2. **Consistency**: Keep all screenshots in the same resolution
3. **Branding**: Ensure SIDM2 is visible in screenshots
4. **Quality**: Better to have fewer high-quality captures than many poor ones
5. **Testing**: Preview in Remotion Studio before final render

---

Need help? Check `README.md` for Remotion integration details.
