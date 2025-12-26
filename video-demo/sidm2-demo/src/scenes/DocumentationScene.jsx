import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const DocumentationScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // Scrolling code effect
  const scrollY = interpolate(frame, [30, 450], [0, -800], { extrapolateRight: 'clamp' });

  const codeBlocks = [
    {
      title: '## Quick Start',
      code: `sid-to-sf2.bat input.sid output.sf2\n# → Auto-selects best driver\n# → 99.93% accuracy for Laxity\n# → 100% accuracy for SF2 files`
    },
    {
      title: '## SF2 Viewer',
      code: `sf2-viewer.bat file.sf2\n# Professional PyQt6 GUI\n# View all SF2 components\n# Export to text format`
    },
    {
      title: '## Batch Processing',
      code: `batch-convert-laxity.bat\n# Process 286 files\n# 8.1 files/second\n# 100% success rate`
    },
    {
      title: '## Python Tools',
      code: `python pyscript/siddump_complete.py music.sid -t30\npython pyscript/sidwinder_trace.py input.sid\n# Cross-platform, zero dependencies`
    }
  ];

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0a1f3f 0%, #1a1a2e 100%)',
        padding: '60px',
      }}
    >
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: '60px',
          width: '100%',
          textAlign: 'center',
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <h2
          style={{
            fontSize: 70,
            fontWeight: 'bold',
            background: 'linear-gradient(135deg, #00ff88 0%, #00ddff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '10px',
          }}
        >
          Documentation
        </h2>
        <p
          style={{
            fontSize: 28,
            color: '#aaaaaa',
            margin: 0,
          }}
        >
          Complete Guides & Examples
        </p>
      </div>

      {/* Scrolling documentation content */}
      <div
        style={{
          position: 'absolute',
          top: '200px',
          left: '100px',
          right: '100px',
          transform: `translateY(${scrollY}px)`,
        }}
      >
        {codeBlocks.map((block, i) => (
          <div
            key={i}
            style={{
              marginBottom: '60px',
              background: 'rgba(0, 0, 0, 0.5)',
              borderRadius: '15px',
              padding: '30px',
              border: '2px solid rgba(0, 255, 136, 0.3)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <h3
              style={{
                fontSize: 36,
                color: '#00ff88',
                fontFamily: "'Courier New', monospace",
                marginBottom: '20px',
              }}
            >
              {block.title}
            </h3>
            <pre
              style={{
                fontSize: 24,
                color: '#00ddff',
                fontFamily: "'Courier New', monospace",
                margin: 0,
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap',
              }}
            >
              {block.code}
            </pre>
          </div>
        ))}
      </div>

      {/* Floating particles */}
      {[...Array(20)].map((_, i) => {
        const angle = (i / 20) * Math.PI * 2;
        const distance = 50 + (frame % 60) * 1.5;
        const x = Math.cos(angle) * distance;
        const y = Math.sin(angle) * distance;
        const opacity = interpolate(frame, [0, 30, 420, 450], [0, 0.3, 0.3, 0]);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `50%`,
              top: `50%`,
              transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
              width: 3,
              height: 3,
              borderRadius: '50%',
              background: '#00ff88',
              opacity: opacity,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
