import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from 'remotion';

export const TitleScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Camera zoom effect
  const zoom = interpolate(frame, [0, 150], [1.5, 1], {
    extrapolateRight: 'clamp',
  });

  // Title reveal with glitch effect
  const titleOpacity = interpolate(frame, [10, 40], [0, 1]);
  const titleY = interpolate(frame, [10, 50], [100, 0]);

  // Glitch effect
  const glitchOffset = frame % 15 === 0 ? Math.random() * 10 - 5 : 0;
  const glitchOpacity = frame % 15 === 0 ? 0.7 : 0;

  // Hexagon grid background
  const hexagons = [...Array(20)].map((_, i) => {
    const row = Math.floor(i / 5);
    const col = i % 5;
    const x = col * 380 + (row % 2) * 190;
    const y = row * 270;
    const delay = i * 3;
    const opacity = interpolate(frame, [delay, delay + 30], [0, 0.15], {
      extrapolateRight: 'clamp',
    });
    const scale = interpolate(frame, [delay, delay + 30], [0, 1], {
      extrapolateRight: 'clamp',
    });
    const rotate = interpolate(frame, [0, 150], [0, 360]);

    return { x, y, opacity, scale, rotate };
  });

  // Particle system - more dynamic
  const particles = [...Array(100)].map((_, i) => {
    const angle = (i / 100) * Math.PI * 2;
    const speed = 2 + (i % 5);
    const distance = (frame * speed) % 1000;
    const x = 960 + Math.cos(angle) * distance;
    const y = 540 + Math.sin(angle) * distance;
    const opacity = interpolate(distance, [0, 300, 700, 1000], [0, 0.8, 0.8, 0]);
    const size = 2 + (i % 4);
    const hue = (i * 3.6 + frame * 2) % 360; // Rainbow colors

    return { x, y, opacity, size, hue };
  });

  // Cyberpunk grid lines
  const gridLines = [...Array(30)].map((_, i) => {
    const progress = (frame * 3 + i * 20) % 1080;
    const opacity = interpolate(progress, [0, 200, 880, 1080], [0, 0.4, 0.4, 0]);
    return { y: progress, opacity };
  });

  // Subtitle animation
  const subtitleOpacity = interpolate(frame, [60, 90], [0, 1]);
  const subtitleY = interpolate(frame, [60, 90], [30, 0]);

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at center, #1a0033 0%, #000011 100%)',
        transform: `scale(${zoom})`,
        overflow: 'hidden',
      }}
    >
      {/* Hexagon grid background */}
      {hexagons.map((hex, i) => (
        <div
          key={`hex-${i}`}
          style={{
            position: 'absolute',
            left: hex.x,
            top: hex.y,
            width: '200px',
            height: '230px',
            opacity: hex.opacity,
            transform: `scale(${hex.scale}) rotate(${hex.rotate}deg)`,
          }}
        >
          <svg viewBox="0 0 100 115" style={{ width: '100%', height: '100%' }}>
            <polygon
              points="50,0 93.3,25 93.3,75 50,100 6.7,75 6.7,25"
              fill="none"
              stroke="url(#hexGradient)"
              strokeWidth="1"
            />
            <defs>
              <linearGradient id="hexGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00ffff" />
                <stop offset="100%" stopColor="#ff00ff" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      ))}

      {/* Cyberpunk grid lines */}
      {gridLines.map((line, i) => (
        <div
          key={`line-${i}`}
          style={{
            position: 'absolute',
            left: 0,
            top: line.y,
            width: '100%',
            height: '2px',
            background: `linear-gradient(90deg,
              transparent 0%,
              rgba(0, 255, 255, ${line.opacity}) 50%,
              transparent 100%
            )`,
            boxShadow: `0 0 10px rgba(0, 255, 255, ${line.opacity})`,
          }}
        />
      ))}

      {/* Particle system */}
      {particles.map((particle, i) => (
        <div
          key={`particle-${i}`}
          style={{
            position: 'absolute',
            left: particle.x,
            top: particle.y,
            width: particle.size,
            height: particle.size,
            borderRadius: '50%',
            background: `hsl(${particle.hue}, 100%, 60%)`,
            opacity: particle.opacity,
            boxShadow: `0 0 ${particle.size * 2}px hsl(${particle.hue}, 100%, 60%)`,
          }}
        />
      ))}

      {/* Main title with 3D effect */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: `translate(-50%, calc(-50% + ${titleY}px))`,
          opacity: titleOpacity,
          textAlign: 'center',
        }}
      >
        {/* Glitch layer */}
        <h1
          style={{
            position: 'absolute',
            top: glitchOffset,
            left: -glitchOffset,
            fontSize: 180,
            fontWeight: 'bold',
            fontFamily: "'Courier New', monospace",
            color: '#ff00ff',
            opacity: glitchOpacity,
            transform: 'translate(-50%, -50%)',
            textShadow: '0 0 20px #ff00ff',
          }}
        >
          SIDM2
        </h1>

        {/* Main title */}
        <h1
          style={{
            position: 'relative',
            fontSize: 180,
            fontWeight: 'bold',
            fontFamily: "'Courier New', monospace",
            background: 'linear-gradient(135deg, #00ffff 0%, #ff00ff 50%, #00ffff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundSize: '200% 200%',
            animation: 'gradient 3s ease infinite',
            textShadow: '0 0 30px rgba(0, 255, 255, 0.5), 0 0 60px rgba(255, 0, 255, 0.3)',
            letterSpacing: '0.1em',
          }}
        >
          SIDM2
        </h1>

        {/* 3D shadow layers */}
        {[...Array(5)].map((_, i) => (
          <h1
            key={`shadow-${i}`}
            style={{
              position: 'absolute',
              top: i * 2,
              left: i * 2,
              fontSize: 180,
              fontWeight: 'bold',
              fontFamily: "'Courier New', monospace",
              color: `rgba(255, 0, 255, ${0.1 - i * 0.02})`,
              WebkitTextStroke: '2px rgba(255, 0, 255, 0.1)',
              transform: 'translate(-50%, -50%)',
              zIndex: -i,
            }}
          >
            SIDM2
          </h1>
        ))}
      </div>

      {/* Subtitle with typing effect */}
      <div
        style={{
          position: 'absolute',
          top: '65%',
          left: '50%',
          transform: `translate(-50%, ${subtitleY}px)`,
          opacity: subtitleOpacity,
          textAlign: 'center',
        }}
      >
        <p
          style={{
            fontSize: 36,
            color: '#00ffff',
            fontFamily: "'Courier New', monospace",
            textShadow: '0 0 10px #00ffff',
            letterSpacing: '0.2em',
            margin: 0,
          }}
        >
          [ SID TO SF2 CONVERTER ]
        </p>
        <p
          style={{
            fontSize: 24,
            color: '#ff00ff',
            fontFamily: "'Courier New', monospace",
            textShadow: '0 0 10px #ff00ff',
            marginTop: '20px',
          }}
        >
          99.93% Frame Accuracy
        </p>
      </div>

      {/* Scanline effect */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.15) 1px, transparent 1px, transparent 2px)',
          pointerEvents: 'none',
        }}
      />

      <style>
        {`
          @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
          }
        `}
      </style>
    </AbsoluteFill>
  );
};
