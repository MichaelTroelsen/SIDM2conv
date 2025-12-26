import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

export const ExcitingFinale = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Explosion particles
  const particles = [...Array(100)].map((_, i) => {
    const angle = (i / 100) * Math.PI * 2;
    const distance = spring({
      frame: frame - 30,
      fps,
      config: { damping: 15, mass: 1 }
    }) * 800;

    const x = Math.cos(angle) * distance + 960;
    const y = Math.sin(angle) * distance + 540;

    const opacity = interpolate(
      frame,
      [30, 60, 120],
      [1, 1, 0],
      { extrapolateRight: 'clamp' }
    );

    return { x, y, opacity, color: i % 2 === 0 ? '#FF6B6B' : '#4ECDC4' };
  });

  // Title animation
  const titleScale = spring({
    frame: frame - 90,
    fps,
    config: { damping: 10, mass: 0.5 }
  });

  const titleOpacity = interpolate(
    frame,
    [90, 120],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  // Stats animation
  const statsDelay = 150;
  const statsOpacity = interpolate(
    frame,
    [statsDelay, statsDelay + 30],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  const statsScale = spring({
    frame: frame - statsDelay,
    fps,
    config: { damping: 12 }
  });

  return (
    <AbsoluteFill style={{
      background: 'radial-gradient(circle at center, #1a1a2e 0%, #0f0f1e 100%)',
    }}>
      {/* Particle explosion */}
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: p.x,
            top: p.y,
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: p.color,
            opacity: p.opacity,
            boxShadow: `0 0 20px ${p.color}`,
          }}
        />
      ))}

      {/* Glowing rings */}
      {[0, 1, 2].map(i => {
        const ringScale = spring({
          frame: frame - (i * 20),
          fps,
          config: { damping: 20 }
        });

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: 200 * ringScale,
              height: 200 * ringScale,
              transform: 'translate(-50%, -50%)',
              border: '4px solid rgba(255,107,107,0.3)',
              borderRadius: '50%',
              opacity: interpolate(frame, [i * 20, i * 20 + 60], [0.8, 0]),
            }}
          />
        );
      })}

      {/* Main Title */}
      <div style={{
        position: 'absolute',
        top: '20%',
        width: '100%',
        textAlign: 'center',
        transform: `scale(${titleScale})`,
        opacity: titleOpacity,
      }}>
        <div style={{
          fontSize: 120,
          fontWeight: 'bold',
          background: 'linear-gradient(45deg, #FF6B6B, #4ECDC4, #45B7D1)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textShadow: '0 0 40px rgba(255,107,107,0.5)',
          marginBottom: 20,
        }}>
          SIDM2
        </div>
        <div style={{
          fontSize: 48,
          color: 'white',
          fontWeight: 'bold',
          opacity: 0.9,
        }}>
          SID to SF2 Converter
        </div>
      </div>

      {/* Achievements */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: `translate(-50%, -50%) scale(${statsScale})`,
        opacity: statsOpacity,
        display: 'flex',
        gap: 80,
      }}>
        {[
          { value: '99.93%', label: 'Accuracy', color: '#27ae60' },
          { value: '240s', label: 'Music', color: '#4ECDC4' },
          { value: '48kHz', label: 'Quality', color: '#FF6B6B' },
        ].map((stat, i) => (
          <div
            key={i}
            style={{
              textAlign: 'center',
              padding: 40,
              backgroundColor: 'rgba(255,255,255,0.1)',
              borderRadius: 20,
              backdropFilter: 'blur(10px)',
              border: `3px solid ${stat.color}`,
              boxShadow: `0 0 30px ${stat.color}`,
            }}
          >
            <div style={{
              fontSize: 72,
              fontWeight: 'bold',
              color: stat.color,
              marginBottom: 10,
            }}>
              {stat.value}
            </div>
            <div style={{
              fontSize: 28,
              color: 'white',
              opacity: 0.8,
            }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Call to Action */}
      <div style={{
        position: 'absolute',
        bottom: 100,
        width: '100%',
        textAlign: 'center',
        opacity: interpolate(frame, [240, 270], [0, 1]),
      }}>
        <div style={{
          fontSize: 36,
          color: 'white',
          fontWeight: 'bold',
          marginBottom: 20,
        }}>
          Try it now on GitHub
        </div>
        <div style={{
          fontSize: 48,
          fontWeight: 'bold',
          color: '#4ECDC4',
          fontFamily: 'monospace',
        }}>
          github.com/MichaelTroelsen/SIDM2conv
        </div>
      </div>

      {/* Pulsing glow effect */}
      <div style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: 1000,
        height: 1000,
        background: 'radial-gradient(circle, rgba(255,107,107,0.2) 0%, transparent 70%)',
        opacity: Math.sin(frame / 15) * 0.5 + 0.5,
      }} />
    </AbsoluteFill>
  );
};
