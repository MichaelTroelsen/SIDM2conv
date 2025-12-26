# SIDM2 Demo Video - Remotion Project

**Video Location**: `out/sidm2-demo.mp4`
**Duration**: 55 seconds | **Resolution**: 1920x1080 | **Size**: 3.9 MB

---

## Quick Start

### Preview & Edit Video
```bash
cd video-demo/sidm2-demo
npm start
```
Then open http://localhost:3000 in your browser.

### Render Video
```bash
cd video-demo/sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo.mp4
```

---

## Project Structure

```
sidm2-demo/
├── src/
│   ├── index.js              # Entry point
│   ├── Root.jsx              # Composition registration
│   ├── SIDM2Demo.jsx         # Main video component (timeline)
│   └── scenes/               # Individual scene components
│       ├── TitleScene.jsx        # (0-5s) Title introduction
│       ├── ProblemScene.jsx      # (5-13s) Problem statement
│       ├── FeaturesScene.jsx     # (13-25s) 6 key features
│       ├── WorkflowScene.jsx     # (25-35s) Conversion pipeline
│       ├── TechStackScene.jsx    # (35-43s) Technical stack
│       ├── ResultsScene.jsx      # (43-50s) Statistics
│       └── ClosingScene.jsx      # (50-55s) GitHub link & CTA
├── out/
│   └── sidm2-demo.mp4        # Rendered video
├── package.json
├── remotion.config.js
└── README.md                 # This file
```

---

## How to Edit the Video

### 1. Start the Remotion Studio
```bash
cd video-demo/sidm2-demo
npm start
```
Open http://localhost:3000 - you'll see the interactive video editor.

### 2. Edit a Scene
Open any scene file in `src/scenes/` and modify:

**Change Text**:
```jsx
// In TitleScene.jsx
<h1 style={{...}}>
  SIDM2  {/* Change this text */}
</h1>
```

**Change Colors**:
```jsx
// Change the green accent color (#00ff88)
color: '#00ff88'  // Try: '#ff0088', '#00aaff', etc.

// Change background color (#1a1a2e)
backgroundColor: '#1a1a2e'  // Try: '#000000', '#1a1a3e', etc.
```

**Change Timing** (in SIDM2Demo.jsx):
```jsx
// Make Title Scene longer (currently 150 frames = 5 seconds)
<Sequence from={0} durationInFrames={150}>
  <TitleScene />
</Sequence>

// Change to 9 seconds (270 frames):
<Sequence from={0} durationInFrames={270}>
  <TitleScene />
</Sequence>

// NOTE: Update all subsequent "from" values when changing durations!
```

**Change Animations**:
```jsx
// In any scene, adjust interpolate values:
const opacity = interpolate(frame, [0, 20], [0, 1]);
//                                   ↑   ↑    ↑  ↑
//                            start frame  |    |  end value
//                                    end frame  start value

// Slower fade-in (0-60 frames instead of 0-20):
const opacity = interpolate(frame, [0, 60], [0, 1]);
```

### 3. Preview Changes
The Remotion Studio auto-reloads when you save files. Scrub the timeline to see your changes.

### 4. Re-render Video
```bash
cd video-demo/sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo.mp4
```

---

## Common Edits

### Change Video Duration
**Current**: 55 seconds (1650 frames @ 30fps)

Edit `src/Root.jsx`:
```jsx
<Composition
  id="SIDM2Demo"
  component={SIDM2Demo}
  durationInFrames={1650}  // Change this (frames = seconds × 30)
  fps={30}
  width={1920}
  height={1080}
/>
```

### Add New Scene
1. Create new file: `src/scenes/MyScene.jsx`
```jsx
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const MyScene = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1]);

  return (
    <AbsoluteFill style={{ backgroundColor: '#1a1a2e', opacity }}>
      <div style={{ padding: '80px' }}>
        <h2 style={{ fontSize: 60, color: '#00ff88' }}>
          My New Scene
        </h2>
      </div>
    </AbsoluteFill>
  );
};
```

2. Add to `src/SIDM2Demo.jsx`:
```jsx
import { MyScene } from './scenes/MyScene.jsx';

// Add sequence:
<Sequence from={1650} durationInFrames={150}>
  <MyScene />
</Sequence>
```

3. Update total duration in `src/Root.jsx` (1650 + 150 = 1800)

### Change Font Sizes
Search for `fontSize` in scene files:
```jsx
fontSize: 120  // Title - try 140, 100, etc.
fontSize: 60   // Headers - try 70, 50, etc.
fontSize: 40   // Body text - try 48, 36, etc.
```

### Update Content
**Features** (FeaturesScene.jsx):
```jsx
const features = [
  { text: '99.93% Frame Accuracy', delay: 40 },
  { text: 'Your New Feature Here', delay: 80 },  // Edit these
  // ...
];
```

**Statistics** (ResultsScene.jsx):
```jsx
const stats = [
  { value: '99.93%', label: 'Frame Accuracy', delay: 40 },
  { value: '300', label: 'Files Converted', delay: 80 },  // Update values
  // ...
];
```

**GitHub Link** (ClosingScene.jsx):
```jsx
<p style={{...}}>
  github.com/MichaelTroelsen/SIDM2conv  {/* Update if URL changes */}
</p>
```

---

## Video Configuration

### Output Format (remotion.config.js)
```javascript
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');  // Image format for frames
Config.setOverwriteOutput(true);     // Overwrite existing video
```

### Render Options
```bash
# Default quality (current)
npx remotion render SIDM2Demo out/sidm2-demo.mp4

# High quality
npx remotion render SIDM2Demo out/sidm2-demo.mp4 --quality 100

# Different codec
npx remotion render SIDM2Demo out/sidm2-demo.webm --codec=vp8

# Specific frame range (frames 0-300 = first 10 seconds)
npx remotion render SIDM2Demo out/preview.mp4 --frames=0-300

# Custom resolution
npx remotion render SIDM2Demo out/sidm2-demo-720p.mp4 --height=720
```

---

## Scene Timeline Reference

| Scene          | Frames      | Duration | Content                          |
|----------------|-------------|----------|----------------------------------|
| TitleScene     | 0-150       | 5s       | Title + "99.93% Accuracy"        |
| ProblemScene   | 150-390     | 8s       | Challenge explanation            |
| FeaturesScene  | 390-750     | 12s      | 6 animated feature cards         |
| WorkflowScene  | 750-1050    | 10s      | Conversion pipeline with icons   |
| TechStackScene | 1050-1290   | 8s       | Technical components             |
| ResultsScene   | 1290-1500   | 7s       | Statistics with animations       |
| ClosingScene   | 1500-1650   | 5s       | GitHub link + CTA                |

**Total**: 1650 frames = 55 seconds @ 30fps

---

## Useful Commands

```bash
# Start dev studio
npm start

# Render video
npm run build SIDM2Demo out/sidm2-demo.mp4

# Upgrade Remotion
npm run upgrade

# Install dependencies
npm install

# Check compositions
npx remotion compositions
```

---

## Remotion Resources

- **Documentation**: https://www.remotion.dev/docs/
- **API Reference**: https://www.remotion.dev/docs/api
- **Examples**: https://www.remotion.dev/showcase
- **Discord**: https://remotion.dev/discord

---

## Tips & Tricks

### Performance
- Use `spring()` for smooth physics-based animations
- Use `interpolate()` for linear transitions
- Preview at lower quality with `--quality=50` flag

### Debugging
- Use `console.log(frame)` to debug timing issues
- Check browser console in Remotion Studio for errors
- Use `--log=verbose` flag when rendering

### Colors
Current palette:
- Primary: `#00ff88` (green accent)
- Background: `#1a1a2e` (dark blue)
- Text: `#ffffff` (white)
- Secondary text: `#aaaaaa` (gray)

### Frame Math (30fps)
- 1 second = 30 frames
- 5 seconds = 150 frames
- 10 seconds = 300 frames
- 1 minute = 1800 frames

---

## Troubleshooting

**Studio won't start**:
```bash
rm -rf node_modules
npm install
npm start
```

**Build fails**:
- Check all imports have `.jsx` extensions
- Verify `"type": "module"` in package.json
- Run `npm install` to ensure dependencies are installed

**Video looks different than Studio**:
- Clear browser cache
- Re-render with `--overwrite` flag

**Render is slow**:
- Use `--concurrency=8` for faster rendering (adjust based on CPU cores)
- Reduce `--quality` for faster draft renders

---

## Project Info

- **Created**: 2025-12-26
- **Remotion Version**: 4.0.395
- **React Version**: 19.2.3
- **Node Version**: 24.11.1

---

**Need Help?** Check the Remotion docs or ask in the Remotion Discord community!
