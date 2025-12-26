import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';

export const FeaturesScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Title scale with spring animation
  const titleScale = spring({
    frame: frame,
    fps,
    config: { damping: 15, mass: 0.5 }
  });

  const features = [
    { text: '99.93% Frame Accuracy', delay: 40, color: '#00ff88', icon: '⚡' },
    { text: 'Automatic Driver Selection', delay: 80, color: '#4ECDC4', icon: '🎯' },
    { text: '200+ Passing Tests', delay: 120, color: '#45B7D1', icon: '✓' },
    { text: '658+ Files Cataloged', delay: 160, color: '#96CEB4', icon: '📁' },
    { text: 'Cross-Platform Python Tools', delay: 200, color: '#FFEAA7', icon: '🐍' },
    { text: 'GUI & CLI Interfaces', delay: 240, color: '#FF6B6B', icon: '💻' },
  ];

  // Floating particles in background
  const particles = [...Array(30)].map((_, i) => {
    const angle = (i / 30) * Math.PI * 2;
    const distance = 150 + (frame % 120) * 3;
    const x = 960 + Math.cos(angle + frame * 0.01) * distance;
    const y = 540 + Math.sin(angle + frame * 0.01) * distance;
    const opacity = interpolate(frame, [0, 30], [0, 0.3], { extrapolateRight: 'clamp' });
    const size = 3 + (i % 5);
    return { x, y, opacity, size };
  });

  // Pulsing glow
  const glowIntensity = Math.sin(frame / 30) * 0.3 + 0.7;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at center, #1a1a2e 0%, #0f0f1e 100%)',
        padding: '80px',
      }}
    >
      {/* Floating particles */}
      {particles.map((particle, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: particle.x,
            top: particle.y,
            width: particle.size,
            height: particle.size,
            borderRadius: '50%',
            backgroundColor: '#00ff88',
            opacity: particle.opacity,
            boxShadow: `0 0 ${particle.size * 3}px #00ff88`,
          }}
        />
      ))}

      {/* Title with spring animation */}
      <div style={{
        opacity: titleOpacity,
        transform: `scale(${titleScale})`,
      }}>
        <h2
          style={{
            fontSize: 60,
            background: 'linear-gradient(135deg, #00ff88 0%, #00ddff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '60px',
            fontFamily: 'Arial, sans-serif',
            fontWeight: 'bold',
            textShadow: `0 0 ${40 * glowIntensity}px rgba(0, 255, 136, ${0.5 * glowIntensity})`,
          }}
        >
          Key Features
        </h2>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '40px',
        }}
      >
        {features.map((feature, index) => {
          const featureOpacity = interpolate(
            frame,
            [feature.delay, feature.delay + 20],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          );

          const featureTranslate = interpolate(
            frame,
            [feature.delay, feature.delay + 20],
            [30, 0],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          );

          // Spring scale animation for each feature
          const featureScale = spring({
            frame: frame - feature.delay,
            fps,
            config: { damping: 12, mass: 0.5 }
          });

          // Pulsing glow for each feature
          const pulseGlow = Math.sin((frame - feature.delay) / 20) * 0.3 + 0.7;

          return (
            <div
              key={index}
              style={{
                opacity: featureOpacity,
                transform: `translateY(${featureTranslate}px) scale(${frame >= feature.delay ? featureScale : 1})`,
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                padding: '30px',
                borderRadius: '15px',
                border: `3px solid ${feature.color}`,
                boxShadow: `0 0 ${30 * pulseGlow}px ${feature.color}`,
                backdropFilter: 'blur(10px)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* Animated gradient overlay */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: `-${frame % 200}%`,
                  width: '200%',
                  height: '100%',
                  background: `linear-gradient(90deg, transparent 0%, ${feature.color}15 50%, transparent 100%)`,
                  opacity: featureOpacity,
                }}
              />

              {/* Icon with rotation */}
              <div
                style={{
                  fontSize: 80,
                  marginBottom: '15px',
                  transform: `rotate(${interpolate(frame, [feature.delay, feature.delay + 30], [0, 360], { extrapolateRight: 'clamp' })}deg)`,
                  display: 'inline-block',
                }}
              >
                {feature.icon}
              </div>

              {/* Feature text */}
              <p
                style={{
                  fontSize: 32,
                  color: '#ffffff',
                  margin: 0,
                  fontFamily: 'Arial, sans-serif',
                  fontWeight: 'bold',
                  position: 'relative',
                  zIndex: 1,
                }}
              >
                {feature.text}
              </p>

              {/* Accent glow in corner */}
              <div
                style={{
                  position: 'absolute',
                  bottom: -20,
                  right: -20,
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: `radial-gradient(circle, ${feature.color}40 0%, transparent 70%)`,
                  opacity: featureOpacity * pulseGlow,
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Scanline effect */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0.1) 2px, transparent 2px, transparent 4px)',
          pointerEvents: 'none',
          opacity: 0.3,
        }}
      />
    </AbsoluteFill>
  );
};
