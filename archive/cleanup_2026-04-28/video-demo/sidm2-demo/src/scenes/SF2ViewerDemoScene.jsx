import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const SF2ViewerDemoScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // GUI window animation
  const windowScale = interpolate(frame, [20, 60], [0.8, 1], { extrapolateRight: 'clamp' });
  const windowOpacity = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Feature list animations
  const features = [
    { icon: '📄', title: 'Load SF2 Files', delay: 80 },
    { icon: '🎵', title: 'View Music Data', delay: 110 },
    { icon: '📊', title: 'Analyze Structure', delay: 140 },
    { icon: '💾', title: 'Export to Text', delay: 170 },
    { icon: '🔍', title: 'Debug Tools', delay: 200 },
  ];

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #1a1a2e 0%, #0a1f3f 50%, #1a1a2e 100%)',
        padding: '60px',
        justifyContent: 'center',
        alignItems: 'center',
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
          SF2 Viewer GUI
        </h2>
        <p
          style={{
            fontSize: 28,
            color: '#aaaaaa',
            margin: 0,
          }}
        >
          Professional PyQt6 Interface
        </p>
      </div>

      {/* Mock GUI Window */}
      <div
        style={{
          position: 'relative',
          width: '1200px',
          height: '600px',
          background: 'rgba(20, 20, 40, 0.9)',
          borderRadius: '15px',
          border: '3px solid rgba(0, 255, 136, 0.5)',
          boxShadow: '0 0 60px rgba(0, 255, 136, 0.3)',
          transform: `scale(${windowScale})`,
          opacity: windowOpacity,
          overflow: 'hidden',
        }}
      >
        {/* Window Title Bar */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(0, 255, 136, 0.2), rgba(0, 221, 255, 0.2))',
            padding: '15px 30px',
            borderBottom: '2px solid rgba(0, 255, 136, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span
            style={{
              fontSize: 24,
              color: '#00ff88',
              fontFamily: "'Courier New', monospace",
            }}
          >
            SF2 Viewer - Professional Edition
          </span>
          <div style={{ display: 'flex', gap: '10px' }}>
            <div style={{ width: 15, height: 15, borderRadius: '50%', background: '#ff5555' }} />
            <div style={{ width: 15, height: 15, borderRadius: '50%', background: '#ffaa00' }} />
            <div style={{ width: 15, height: 15, borderRadius: '50%', background: '#00ff88' }} />
          </div>
        </div>

        {/* Content Area - Code-style display */}
        <div style={{ padding: '30px' }}>
          <pre
            style={{
              fontSize: 20,
              color: '#00ddff',
              fontFamily: "'Courier New', monospace",
              margin: 0,
              lineHeight: '1.8',
            }}
          >
{`File: Stinsens_Last_Night_of_89.sf2
Size: 10,892 bytes
Driver: Laxity NewPlayer v21
Accuracy: 99.93%

[METADATA]
Title: Stin's Last Night of 89
Author: Laxity
Copyright: 1989

[MUSIC DATA]
├─ Orderlists (3 voices)
├─ Sequences (47 total)
├─ Instruments (32 entries)
└─ Wave Tables (optimized)`}
          </pre>
        </div>
      </div>

      {/* Feature List */}
      <div
        style={{
          position: 'absolute',
          bottom: '80px',
          display: 'flex',
          gap: '40px',
          justifyContent: 'center',
        }}
      >
        {features.map((feature, i) => {
          const opacity = interpolate(
            frame,
            [feature.delay, feature.delay + 20],
            [0, 1],
            { extrapolateRight: 'clamp' }
          );
          const y = interpolate(
            frame,
            [feature.delay, feature.delay + 20],
            [30, 0],
            { extrapolateRight: 'clamp' }
          );
          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `translateY(${y}px)`,
                textAlign: 'center',
                background: 'rgba(0, 255, 136, 0.1)',
                padding: '15px 25px',
                borderRadius: '10px',
                border: '2px solid rgba(0, 255, 136, 0.3)',
              }}
            >
              <div style={{ fontSize: 36, marginBottom: '5px' }}>{feature.icon}</div>
              <div
                style={{
                  fontSize: 18,
                  color: '#00ff88',
                  fontFamily: "'Courier New', monospace",
                }}
              >
                {feature.title}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
