import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const PythonToolsScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // Terminal animations
  const terminal1Opacity = interpolate(frame, [30, 60], [0, 1]);
  const terminal1Y = interpolate(frame, [30, 60], [50, 0]);

  const terminal2Opacity = interpolate(frame, [90, 120], [0, 1]);
  const terminal2Y = interpolate(frame, [90, 120], [50, 0]);

  // Typing effect - simulate terminal output appearing
  const typingProgress = Math.min(frame - 60, 200);
  const siddumpText = `$ python pyscript/siddump_complete.py music.sid -t30

SIDdump v1.0 - Pure Python Implementation
Loading: music.sid (8,234 bytes)
Format: PSID v2
Player: Laxity NewPlayer v21
Init: $1000  Play: $10A1

Dumping 30 seconds...
[████████████████████████████████] 900/900 frames
Musical content extracted successfully!
Accuracy: 100% (validated)`.substring(0, typingProgress * 3);

  const sidwinderText = `$ python pyscript/sidwinder_trace.py input.sid --frames 1500

SIDwinder Trace v1.0
Frame-aggregated SID register tracing
Output: trace.txt

Processing frames...
[████████████████████████████████] 1500/1500
Frame aggregation: 100%
Write compression: 97.3%
Output size: 2.7 KB

Trace complete! 🎵`.substring(0, Math.max(0, (typingProgress - 100) * 3));

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f0f1e 0%, #1a0033 50%, #0f0f1e 100%)',
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
          Python Tools
        </h2>
        <p
          style={{
            fontSize: 28,
            color: '#aaaaaa',
            margin: 0,
          }}
        >
          Cross-Platform, Zero Dependencies
        </p>
      </div>

      {/* Terminal 1 - siddump */}
      <div
        style={{
          position: 'absolute',
          top: '250px',
          left: '100px',
          right: '100px',
          opacity: terminal1Opacity,
          transform: `translateY(${terminal1Y}px)`,
        }}
      >
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.8)',
            borderRadius: '10px',
            border: '2px solid rgba(0, 255, 136, 0.5)',
            padding: '20px',
            boxShadow: '0 0 30px rgba(0, 255, 136, 0.2)',
          }}
        >
          <div
            style={{
              fontSize: 18,
              color: '#00ff88',
              fontFamily: "'Courier New', monospace",
              marginBottom: '10px',
              borderBottom: '1px solid rgba(0, 255, 136, 0.3)',
              paddingBottom: '10px',
            }}
          >
            🐍 Python siddump - Musical Content Extractor
          </div>
          <pre
            style={{
              fontSize: 16,
              color: '#00ddff',
              fontFamily: "'Courier New', monospace",
              margin: 0,
              lineHeight: '1.6',
            }}
          >
            {siddumpText}
          </pre>
        </div>
      </div>

      {/* Terminal 2 - sidwinder */}
      <div
        style={{
          position: 'absolute',
          top: '600px',
          left: '100px',
          right: '100px',
          opacity: terminal2Opacity,
          transform: `translateY(${terminal2Y}px)`,
        }}
      >
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.8)',
            borderRadius: '10px',
            border: '2px solid rgba(0, 221, 255, 0.5)',
            padding: '20px',
            boxShadow: '0 0 30px rgba(0, 221, 255, 0.2)',
          }}
        >
          <div
            style={{
              fontSize: 18,
              color: '#00ddff',
              fontFamily: "'Courier New', monospace",
              marginBottom: '10px',
              borderBottom: '1px solid rgba(0, 221, 255, 0.3)',
              paddingBottom: '10px',
            }}
          >
            🔄 Python SIDwinder - Frame-Aggregated Tracing
          </div>
          <pre
            style={{
              fontSize: 16,
              color: '#00ff88',
              fontFamily: "'Courier New', monospace",
              margin: 0,
              lineHeight: '1.6',
            }}
          >
            {sidwinderText}
          </pre>
        </div>
      </div>

      {/* Stats badges */}
      <div
        style={{
          position: 'absolute',
          bottom: '80px',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: '40px',
        }}
      >
        {[
          { label: 'Pure Python', value: '100%', color: '#00ff88' },
          { label: 'Cross-Platform', value: '✓', color: '#00ddff' },
          { label: 'Zero Dependencies', value: '0', color: '#ff00ff' },
        ].map((stat, i) => {
          const opacity = interpolate(
            frame,
            [200 + i * 20, 220 + i * 20],
            [0, 1],
            { extrapolateRight: 'clamp' }
          );
          return (
            <div
              key={i}
              style={{
                opacity,
                textAlign: 'center',
                background: `rgba(${i === 0 ? '0, 255, 136' : i === 1 ? '0, 221, 255' : '255, 0, 255'}, 0.1)`,
                padding: '20px 30px',
                borderRadius: '10px',
                border: `2px solid ${stat.color}40`,
              }}
            >
              <div
                style={{
                  fontSize: 48,
                  fontWeight: 'bold',
                  color: stat.color,
                  fontFamily: "'Courier New', monospace",
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 20, color: '#aaaaaa', marginTop: '5px' }}>
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
