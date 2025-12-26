# SIDM2 Video - Quick Reference

## 🚀 Most Common Tasks

### Edit & Preview
```bash
cd video-demo/sidm2-demo
npm start
# Opens http://localhost:3000
```

### Render Video
```bash
cd video-demo/sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo.mp4
```

---

## 📝 Quick Edits

### Change Text
**File**: `src/scenes/TitleScene.jsx`
```jsx
<h1 style={{...}}>SIDM2</h1>          // Line 35
<p style={{...}}>Your text here</p>   // Line 43
```

### Change Colors
**Green accent**: `#00ff88` → Search & replace in all scene files
**Background**: `#1a1a2e` → Search & replace in all scene files

### Change Scene Duration
**File**: `src/SIDM2Demo.jsx`
```jsx
<Sequence from={0} durationInFrames={150}>  // 150 frames = 5 seconds
```
⚠️ Update all subsequent `from` values when changing durations!

### Update Stats
**File**: `src/scenes/ResultsScene.jsx`
```jsx
const stats = [
  { value: '99.93%', label: 'Frame Accuracy', delay: 40 },
  // Edit values here
];
```

---

## 📂 File Locations

| What                  | Where                              |
|-----------------------|------------------------------------|
| Rendered video        | `out/sidm2-demo.mp4`              |
| Edit scenes           | `src/scenes/*.jsx`                |
| Change timeline       | `src/SIDM2Demo.jsx`               |
| Video settings        | `src/Root.jsx`                    |

---

## ⏱️ Scene Timing

| Scene     | Start | Duration | Edit File              |
|-----------|-------|----------|------------------------|
| Title     | 0s    | 5s       | TitleScene.jsx         |
| Problem   | 5s    | 8s       | ProblemScene.jsx       |
| Features  | 13s   | 12s      | FeaturesScene.jsx      |
| Workflow  | 25s   | 10s      | WorkflowScene.jsx      |
| Tech      | 35s   | 8s       | TechStackScene.jsx     |
| Results   | 43s   | 7s       | ResultsScene.jsx       |
| Closing   | 50s   | 5s       | ClosingScene.jsx       |

---

## 🎨 Color Palette

```
Primary:    #00ff88  (green)
Background: #1a1a2e  (dark blue)
Text:       #ffffff  (white)
Gray:       #aaaaaa  (secondary text)
```

---

## 📏 Frame Calculations (30fps)

- 1 second = 30 frames
- 5 seconds = 150 frames
- 10 seconds = 300 frames
- Current total = 1650 frames (55 seconds)

---

## 🔧 Render Options

```bash
# High quality
npx remotion render SIDM2Demo out/video.mp4 --quality=100

# Fast draft
npx remotion render SIDM2Demo out/draft.mp4 --quality=50

# First 10 seconds only
npx remotion render SIDM2Demo out/preview.mp4 --frames=0-300

# 720p version
npx remotion render SIDM2Demo out/video-720p.mp4 --height=720
```

---

## 💡 Pro Tips

1. **Save time**: Edit in Remotion Studio (http://localhost:3000) - see changes instantly
2. **Test renders**: Use `--frames=0-300` to render first 10 seconds only
3. **Reuse animations**: Copy animation code from existing scenes
4. **Frame math**: Multiply seconds by 30 to get frame count
5. **Background colors**: All scenes use `<AbsoluteFill style={{ backgroundColor: '#1a1a2e' }}>`

---

## 🆘 Help

- Full guide: See `README.md` in this folder
- Remotion docs: https://www.remotion.dev/docs/
- Can't start? Run `npm install` first
