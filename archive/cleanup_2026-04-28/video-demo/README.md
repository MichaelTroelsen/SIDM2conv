# SIDM2 Demo Video Project

This folder contains the Remotion project for creating the SIDM2 demo video.

## Quick Access

📹 **Rendered Video**: `sidm2-demo/out/sidm2-demo.mp4` (3.9 MB, 55 seconds, 1920x1080)

📚 **Documentation**:
- **Quick Start**: `sidm2-demo/QUICK-START.md` - Common tasks & quick reference
- **Full Guide**: `sidm2-demo/README.md` - Complete documentation

## What is This?

A professional video showcasing the SIDM2 project:
- 99.93% conversion accuracy
- Automatic driver selection
- 200+ passing tests
- Cross-platform Python tools
- Complete workflow demonstration

Built with [Remotion](https://remotion.dev) - React-based programmatic video creation.

## Quick Commands

```bash
# Preview & edit video
cd sidm2-demo
npm start
# Then open http://localhost:3000

# Render video
cd sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo.mp4
```

## Project Structure

```
video-demo/
├── sidm2-demo/
│   ├── src/
│   │   ├── scenes/           # 7 video scenes
│   │   ├── SIDM2Demo.jsx     # Timeline
│   │   └── Root.jsx          # Config
│   ├── out/
│   │   └── sidm2-demo.mp4    # Rendered video ✨
│   ├── README.md             # Full documentation
│   ├── QUICK-START.md        # Quick reference
│   └── package.json
└── README.md                 # This file
```

## Video Scenes

1. **Title** (5s) - Bold SIDM2 introduction
2. **Problem** (8s) - Challenge explanation
3. **Features** (12s) - 6 animated feature cards
4. **Workflow** (10s) - Conversion pipeline
5. **Tech Stack** (8s) - Technical components
6. **Results** (7s) - Statistics showcase
7. **Closing** (5s) - GitHub link & CTA

Total: 55 seconds @ 1920x1080, 30fps

## Need Help?

- Read `sidm2-demo/QUICK-START.md` for common tasks
- Read `sidm2-demo/README.md` for complete guide
- Visit https://www.remotion.dev/docs/ for Remotion docs

---

Created: 2025-12-26 | Framework: Remotion 4.0 | React 19.2
