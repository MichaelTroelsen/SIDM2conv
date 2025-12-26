# VSID 240-Second Configuration - Final

**Date**: 2025-12-26
**Duration**: 240 seconds (4 minutes)
**Status**: ✅ Tested and Working

---

## Summary

Successfully configured VSID to capture 4 minutes (240 seconds) of SID playback for video demo background music.

---

## Test Results

### ✅ Full 240-Second Conversion Test

**Command**:
```bash
python pyscript/sid_to_wav_vsid.py "tools/Stinsens_Last_Night_of_89.sid" \
  "video-demo/sidm2-demo/temp/background-music-240s.wav" --time 240
```

**Result**:
- ✅ Success
- Output: `background-music-240s.wav`
- File size: **22.80 MB**
- Duration: **240 seconds (4 minutes)**
- Sample rate: **48kHz**
- Format: **16-bit PCM WAV**
- Conversion time: **~250 seconds**

---

## Pipeline Configuration

### Updated Files

1. **`pyscript/setup_video_assets.py`**
   - Line 76: Duration changed from 70s → 240s
   - Line 104: Description updated to "240 seconds (4 minutes)"
   - Line 118: Timeout changed from 80s → 250s
   - Line 124: Timeout parameter: 250 seconds (240s + 10s buffer)

2. **Documentation**
   - `docs/VIDEO_CREATION_GUIDE.md` - Updated to 240s
   - `VIDEO_DEMO_SUMMARY.md` - Updated to 240s
   - `VSID_INTEGRATION_SUMMARY.md` - Test results updated

---

## VSID Command

### Current Command Used
```bash
vsid -sounddev wav -soundarg output.wav input.sid
# Runs for 240 seconds, then killed by timeout
```

### Recommended Enhanced Configuration

For best quality with Laxity SID files:

```bash
"C:\winvice\bin\vsid.exe" \
  -sounddev wav \
  -soundarg "background-music.wav" \
  -sidenginemodel 257 \         # ReSID 8580 (Laxity standard)
  -residsamp 2 \                # Resampling (best quality)
  -residpass 90 \               # Maximum passband
  -residgain 97 \               # Standard gain
  -sidfilters \                 # Enable SID filters
  -pal \                        # PAL timing (50Hz, European)
  -soundrate 48000 \            # 48kHz (video standard)
  "Stinsens_Last_Night_of_89.sid"
```

**Note**: These enhanced options can be added to `setup_video_assets.py` for better quality.

---

## File Size Comparison

| Duration | File Size (48kHz) | Estimated MP3 |
|----------|-------------------|---------------|
| 70s | 7.21 MB | ~1.1 MB |
| 240s | 22.80 MB | ~3.7 MB |
| 300s | 28.50 MB | ~4.6 MB |

**Current**: 240 seconds = **22.80 MB WAV** → **~3.7 MB MP3**

---

## Performance Metrics

### Asset Pipeline (Updated)

| Step | Duration | Output Size |
|------|----------|-------------|
| 1. Find SID | <1s | - |
| 2. SID → WAV (VSID) | **~250s (4.2 min)** | **22.8 MB** |
| 3. WAV → MP3 (ffmpeg) | ~3-5s | ~3.7 MB |
| 4. Screenshots | ~15s | 743 KB |
| **Total** | **~270s (4.5 min)** | **~4.5 MB** |

---

## Quality Settings

### Current (Default)
- **Sample Rate**: 48000 Hz (video standard)
- **SID Engine**: ReSID 8580 (VICE default)
- **Sampling**: Resampling (best quality)
- **Filters**: Enabled
- **Timing**: Auto-detected (likely PAL for Laxity)

### Potential Improvements

If you want even better quality, add these to the VSID command in `setup_video_assets.py`:

```python
cmd = [
    str(vsid_exe),
    '-sounddev', 'wav',
    '-soundarg', str(wav_path),
    '-sidenginemodel', '257',    # ReSID 8580
    '-residsamp', '2',           # Resampling
    '-residpass', '90',          # Max passband
    '-residgain', '97',          # Standard gain
    '-sidfilters',               # Enable filters
    '-pal',                      # PAL timing
    '-soundrate', '48000',       # 48kHz
    str(sid_path)
]
```

---

## Usage

### Run Full Pipeline
```bash
# Automated (all steps)
setup-video-assets.bat

# Or manual
python pyscript/setup_video_assets.py
```

### Convert SID Only (240 seconds)
```bash
python pyscript/sid_to_wav_vsid.py \
  "tools/Stinsens_Last_Night_of_89.sid" \
  "output.wav" \
  --time 240
```

### Convert with Custom Duration
```bash
# 5 minutes (300 seconds)
python pyscript/sid_to_wav_vsid.py input.sid output.wav --time 300

# 2 minutes (120 seconds)
python pyscript/sid_to_wav_vsid.py input.sid output.wav --time 120
```

---

## Next Steps

1. ✅ **Configuration Complete** - 240 seconds set
2. ✅ **Tested Successfully** - 22.80 MB output
3. 🔄 **Ready for Full Pipeline** - Run `setup-video-assets.bat`
4. Optional: Add enhanced VSID quality settings

---

## Notes

- **VSID runs indefinitely**: Must use timeout to stop it
- **Real-time capture**: 240 seconds playback = 240 seconds conversion time
- **High quality**: 48kHz 16-bit PCM (perfect for video)
- **Authentic**: Uses actual C64 SID chip emulation (ReSID)

---

**Configuration Complete** ✅
**Ready for Production Use**
