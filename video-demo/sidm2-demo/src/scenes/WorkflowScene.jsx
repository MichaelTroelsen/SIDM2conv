import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from 'remotion';

export const WorkflowScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0], { extrapolateRight: 'clamp' });

  // Conversion Cockpit screenshot animation
  const screenshotOpacity = interpolate(frame, [20, 50], [0, 1], { extrapolateRight: 'clamp' });
  const screenshotScale = interpolate(frame, [20, 50], [0.8, 1], { extrapolateRight: 'clamp' });
  const screenshotY = interpolate(frame, [20, 50], [100, 0], { extrapolateRight: 'clamp' });

  // Animated glow around screenshot
  const glowPulse = interpolate(
    frame,
    [0, 60, 120, 180, 240, 300],
    [0.3, 0.7, 0.3, 0.7, 0.3, 0.7],
    { extrapolateRight: 'clamp' }
  );

  // Progress bar animations
  const progressBar1 = interpolate(frame, [80, 150], [0, 100], { extrapolateRight: 'clamp' });
  const progressBar2 = interpolate(frame, [100, 170], [0, 100], { extrapolateRight: 'clamp' });
  const progressBar3 = interpolate(frame, [120, 190], [0, 100], { extrapolateRight: 'clamp' });

  // Stats counter animations
  const filesProcessed = Math.floor(interpolate(frame, [150, 250], [0, 286], { extrapolateRight: 'clamp' }));
  const successRate = Math.floor(interpolate(frame, [150, 250], [0, 100], { extrapolateRight: 'clamp' }));

  // Floating particles
  const particles = [...Array(15)].map((_, i) => {
    const angle = (i / 15) * Math.PI * 2;
    const distance = 50 + (frame % 60) * 2;
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;
    const opacity = interpolate(frame, [0, 40, 260, 300], [0, 0.4, 0.4, 0]);
    return { x, y, opacity, size: 2 + (i % 3) };
  });

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #1a1a2e 0%, #0a1f3f 50%, #1a1a2e 100%)',
        padding: '60px',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      {/* Floating particles */}
      {particles.map((particle, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `50%`,
            top: `50%`,
            transform: `translate(calc(-50% + ${particle.x}px), calc(-50% + ${particle.y}px))`,
            width: particle.size,
            height: particle.size,
            borderRadius: '50%',
            background: '#00ff88',
            opacity: particle.opacity,
          }}
        />
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
            fontSize: 70,
            fontWeight: 'bold',
            background: 'linear-gradient(135deg, #00ff88 0%, #00ddff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '10px',
          }}
        >
          Conversion Workflow
        </h2>
        <p
          style={{
            fontSize: 28,
            color: '#aaaaaa',
            margin: 0,
          }}
        >
          Powered by Conversion Cockpit
        </p>
      </div>

      {/* Main screenshot with animated glow */}
      <div
        style={{
          position: 'relative',
          opacity: screenshotOpacity,
          transform: `scale(${screenshotScale}) translateY(${screenshotY}px)`,
          boxShadow: `0 0 ${60 * glowPulse}px rgba(0, 255, 136, ${glowPulse})`,
          borderRadius: '15px',
          overflow: 'hidden',
          border: '3px solid rgba(0, 255, 136, 0.5)',
          background: 'rgba(0, 0, 0, 0.3)',
        }}
      >
        <Img
          src={staticFile('assets/screenshots/conversion-cockpit.png')}
          style={{
            width: '1200px',
            height: 'auto',
            display: 'block',
          }}
        />
      </div>

      {/* Animated stats overlay */}
      <div
        style={{
          position: 'absolute',
          bottom: '80px',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: '60px',
          opacity: interpolate(frame, [150, 180], [0, 1], { extrapolateRight: 'clamp' }),
        }}
      >
        {/* Files Processed */}
        <div
          style={{
            textAlign: 'center',
            background: 'rgba(0, 255, 136, 0.1)',
            padding: '20px 40px',
            borderRadius: '15px',
            border: '2px solid rgba(0, 255, 136, 0.3)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <div
            style={{
              fontSize: 50,
              fontWeight: 'bold',
              color: '#00ff88',
              fontFamily: 'monospace',
            }}
          >
            {filesProcessed}
          </div>
          <div style={{ fontSize: 20, color: '#aaaaaa' }}>Files Processed</div>
        </div>

        {/* Success Rate */}
        <div
          style={{
            textAlign: 'center',
            background: 'rgba(0, 221, 255, 0.1)',
            padding: '20px 40px',
            borderRadius: '15px',
            border: '2px solid rgba(0, 221, 255, 0.3)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <div
            style={{
              fontSize: 50,
              fontWeight: 'bold',
              color: '#00ddff',
              fontFamily: 'monospace',
            }}
          >
            {successRate}%
          </div>
          <div style={{ fontSize: 20, color: '#aaaaaa' }}>Success Rate</div>
        </div>

        {/* Speed */}
        <div
          style={{
            textAlign: 'center',
            background: 'rgba(255, 136, 0, 0.1)',
            padding: '20px 40px',
            borderRadius: '15px',
            border: '2px solid rgba(255, 136, 0, 0.3)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <div
            style={{
              fontSize: 50,
              fontWeight: 'bold',
              color: '#ff8800',
              fontFamily: 'monospace',
            }}
          >
            8.1
          </div>
          <div style={{ fontSize: 20, color: '#aaaaaa' }}>Files/Second</div>
        </div>
      </div>

      {/* Animated progress bars (subtle overlay) */}
      <div
        style={{
          position: 'absolute',
          top: '200px',
          right: '100px',
          width: '300px',
          opacity: interpolate(frame, [80, 100], [0, 0.7], { extrapolateRight: 'clamp' }),
        }}
      >
        {[progressBar1, progressBar2, progressBar3].map((progress, i) => (
          <div
            key={i}
            style={{
              marginBottom: '15px',
              background: 'rgba(0, 0, 0, 0.5)',
              borderRadius: '10px',
              padding: '5px',
              backdropFilter: 'blur(10px)',
            }}
          >
            <div
              style={{
                height: '8px',
                background: `linear-gradient(90deg, #00ff88 0%, #00ddff 100%)`,
                borderRadius: '5px',
                width: `${progress}%`,
                transition: 'width 0.3s ease-out',
              }}
            />
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
