# Convert Stinsens WAV to MP3

## ✅ Step 1: WAV Created!
Your WAV file has been created:
- **Location**: `video-demo/sidm2-demo/temp/stinsens.wav`
- **Size**: 3.0 MB
- **Duration**: 70 seconds
- **Song**: "Stinsen's Last Night of '89" by Thomas E. Petersen (Laxity)

## 🎵 Step 2: Convert to MP3 (2 minutes)

### Option A: CloudConvert (Recommended - Free & Easy)
1. **Open browser**: https://cloudconvert.com/wav-to-mp3

2. **Upload file**:
   - Click "Select File"
   - Navigate to: `video-demo/sidm2-demo/temp/stinsens.wav`
   - Select the file

3. **Convert**:
   - Click "Convert" button
   - Wait ~30 seconds

4. **Download**:
   - Click "Download" button
   - Save as: `background-music.mp3`

5. **Move file**:
   - Move `background-music.mp3` to:
     `video-demo/sidm2-demo/public/assets/audio/background-music.mp3`

### Option B: Online-Convert.com
1. Go to: https://audio.online-convert.com/convert-to-mp3
2. Upload `stinsens.wav`
3. Click "Start conversion"
4. Download and save as `background-music.mp3`
5. Move to `public/assets/audio/`

### Option C: Use VLC Media Player (If installed)
1. Open VLC Media Player
2. Media → Convert/Save
3. Add `stinsens.wav`
4. Click "Convert/Save"
5. Choose MP3 codec
6. Save as `background-music.mp3`
7. Move to `public/assets/audio/`

## ✅ Step 3: Verify

After conversion, check:
```bash
ls -lh video-demo/sidm2-demo/public/assets/audio/background-music.mp3
```

File should be ~700KB - 1.5MB

## 🎬 Step 4: Test in Video

```bash
cd video-demo/sidm2-demo
npm start
```

Open http://localhost:3000 and you should hear the music playing!

## 🎵 About the Music

**Song**: Stinsen's Last Night of '89
**Composer**: Thomas E. Petersen (Laxity)
**Year**: 2021 Bonzai
**Format**: Laxity NewPlayer v21
**Perfect for**: Background music - melodic C64 SID music!

This is authentic C64 music converted from your own SIDM2 project - perfect for the demo video!

---

**Next**: Once MP3 is in place, continue with screenshot capture from SETUP-ENHANCED-VIDEO.md
