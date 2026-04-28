import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const ToolsMenuScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // Batch tools - cascade animation
  const batchTools = [
    { name: 'sid-to-sf2.bat', desc: 'Main converter - auto driver selection', icon: '🎯' },
    { name: 'sf2-viewer.bat', desc: 'SF2 GUI viewer & analyzer', icon: '👁️' },
    { name: 'conversion-cockpit.bat', desc: 'Mission control for batch operations', icon: '🚀' },
    { name: 'batch-convert-laxity.bat', desc: 'Process all 286 Laxity files', icon: '⚡' },
    { name: 'test-all.bat', desc: 'Run 200+ validation tests', icon: '✅' },
    { name: 'cleanup.bat', desc: 'Clean + update inventory', icon: '🧹' },
  ];

  // Python tools - cascade animation with delay
  const pythonTools = [
    { name: 'siddump_complete.py', desc: 'Pure Python frame dumper', icon: '🐍' },
    { name: 'sidwinder_trace.py', desc: 'Frame-aggregated SID tracing', icon: '🔄' },
    { name: 'conversion_cockpit_gui.py', desc: 'PyQt6 batch converter GUI', icon: '🎮' },
    { name: 'sf2_viewer_gui.py', desc: 'Professional SF2 viewer', icon: '📊' },
  ];

  // Floating code particles
  const codeParticles = [...Array(50)].map((_, i) => {
    const angle = (i / 50) * Math.PI * 2;
    const radius = 300 + Math.sin(frame * 0.02 + i) * 100;
    const x = 960 + Math.cos(angle) * radius;
    const y = 540 + Math.sin(angle) * radius;
    const opacity = interpolate(
      Math.sin(frame * 0.05 + i),
      [-1, 1],
      [0.1, 0.5]
    );
    return { x, y, opacity, char: ['$', '#', '>', '@', '%'][i % 5] };
  });

  // Rotating hexagon background
  const hexRotation = interpolate(frame, [0, 600], [0, 360]);

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0a1f3f 0%, #1a0033 50%, #0f0f1e 100%)',
        overflow: 'hidden',
      }}
    >
      {/* Animated hexagon grid background */}
      <div
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          opacity: 0.1,
          transform: `rotate(${hexRotation}deg)`,
        }}
      >
        {[...Array(12)].map((_, i) => {
          const row = Math.floor(i / 4);
          const col = i % 4;
          return (
            <svg
              key={i}
              style={{
                position: 'absolute',
                left: `${col * 25}%`,
                top: `${row * 33}%`,
              }}
              width="300"
              height="300"
              viewBox="0 0 100 100"
            >
              <polygon
                points="50,5 90,25 90,75 50,95 10,75 10,25"
                fill="none"
                stroke="#00ff88"
                strokeWidth="0.5"
              />
            </svg>
          );
        })}
      </div>

      {/* Floating code particles */}
      {codeParticles.map((particle, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: particle.x,
            top: particle.y,
            color: '#00ff88',
            fontFamily: "'Courier New', monospace",
            fontSize: 20,
            opacity: particle.opacity,
            pointerEvents: 'none',
          }}
        >
          {particle.char}
        </div>
      ))}

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
            fontSize: 80,
            fontWeight: 'bold',
            background: 'linear-gradient(135deg, #00ff88 0%, #00ddff 50%, #ff00ff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '10px',
            textShadow: '0 0 40px rgba(0, 255, 136, 0.5)',
          }}
        >
          Tools Arsenal
        </h2>
        <p
          style={{
            fontSize: 32,
            color: '#aaaaaa',
            margin: 0,
          }}
        >
          Complete Automation Suite
        </p>
      </div>

      {/* Batch Tools Section - Left Column */}
      <div
        style={{
          position: 'absolute',
          left: '80px',
          top: '200px',
          width: '800px',
        }}
      >
        <div
          style={{
            fontSize: 36,
            color: '#00ff88',
            fontFamily: "'Courier New', monospace",
            marginBottom: '20px',
            textShadow: '0 0 20px rgba(0, 255, 136, 0.5)',
          }}
        >
          💻 Batch Tools
        </div>
        {batchTools.map((tool, i) => {
          const delay = 40 + i * 15;
          const opacity = interpolate(frame, [delay, delay + 20], [0, 1], {
            extrapolateRight: 'clamp',
          });
          const x = interpolate(frame, [delay, delay + 30], [-100, 0], {
            extrapolateRight: 'clamp',
          });
          const scale = interpolate(frame, [delay, delay + 20], [0.8, 1], {
            extrapolateRight: 'clamp',
          });

          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `translateX(${x}px) scale(${scale})`,
                marginBottom: '15px',
                background: `linear-gradient(90deg, rgba(0, 255, 136, 0.${2 + i}) 0%, rgba(0, 221, 255, 0.${1 + i}) 100%)`,
                padding: '15px 25px',
                borderRadius: '12px',
                border: '2px solid rgba(0, 255, 136, 0.4)',
                boxShadow: '0 0 20px rgba(0, 255, 136, 0.2)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <span style={{ fontSize: 32 }}>{tool.icon}</span>
                <div>
                  <div
                    style={{
                      fontSize: 20,
                      color: '#00ff88',
                      fontFamily: "'Courier New', monospace",
                      fontWeight: 'bold',
                    }}
                  >
                    {tool.name}
                  </div>
                  <div style={{ fontSize: 16, color: '#aaaaaa' }}>
                    {tool.desc}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Python Tools Section - Right Column */}
      <div
        style={{
          position: 'absolute',
          right: '80px',
          top: '200px',
          width: '800px',
        }}
      >
        <div
          style={{
            fontSize: 36,
            color: '#00ddff',
            fontFamily: "'Courier New', monospace",
            marginBottom: '20px',
            textShadow: '0 0 20px rgba(0, 221, 255, 0.5)',
          }}
        >
          🐍 Python Tools
        </div>
        {pythonTools.map((tool, i) => {
          const delay = 130 + i * 15;
          const opacity = interpolate(frame, [delay, delay + 20], [0, 1], {
            extrapolateRight: 'clamp',
          });
          const x = interpolate(frame, [delay, delay + 30], [100, 0], {
            extrapolateRight: 'clamp',
          });
          const scale = interpolate(frame, [delay, delay + 20], [0.8, 1], {
            extrapolateRight: 'clamp',
          });

          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `translateX(${x}px) scale(${scale})`,
                marginBottom: '15px',
                background: `linear-gradient(90deg, rgba(0, 221, 255, 0.${2 + i}) 0%, rgba(255, 0, 255, 0.${1 + i}) 100%)`,
                padding: '15px 25px',
                borderRadius: '12px',
                border: '2px solid rgba(0, 221, 255, 0.4)',
                boxShadow: '0 0 20px rgba(0, 221, 255, 0.2)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <span style={{ fontSize: 32 }}>{tool.icon}</span>
                <div>
                  <div
                    style={{
                      fontSize: 20,
                      color: '#00ddff',
                      fontFamily: "'Courier New', monospace",
                      fontWeight: 'bold',
                    }}
                  >
                    {tool.name}
                  </div>
                  <div style={{ fontSize: 16, color: '#aaaaaa' }}>
                    {tool.desc}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Pulsating stats at bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: '80px',
          width: '100%',
          display: 'flex',
          justifyContent: 'center',
          gap: '60px',
        }}
      >
        {[
          { label: 'Batch Tools', value: '20+', color: '#00ff88' },
          { label: 'Python Scripts', value: '50+', color: '#00ddff' },
          { label: 'Test Suite', value: '200+', color: '#ff00ff' },
        ].map((stat, i) => {
          const delay = 240 + i * 15;
          const opacity = interpolate(frame, [delay, delay + 20], [0, 1], {
            extrapolateRight: 'clamp',
          });
          const scale = interpolate(
            Math.sin(frame * 0.1 + i * 2),
            [-1, 1],
            [0.95, 1.05]
          );

          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `scale(${scale})`,
                textAlign: 'center',
                background: `rgba(${
                  i === 0 ? '0, 255, 136' : i === 1 ? '0, 221, 255' : '255, 0, 255'
                }, 0.1)`,
                padding: '25px 40px',
                borderRadius: '15px',
                border: `3px solid ${stat.color}`,
                boxShadow: `0 0 30px ${stat.color}40`,
              }}
            >
              <div
                style={{
                  fontSize: 56,
                  fontWeight: 'bold',
                  color: stat.color,
                  fontFamily: "'Courier New', monospace",
                  textShadow: `0 0 20px ${stat.color}`,
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 22, color: '#aaaaaa', marginTop: '5px' }}>
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
