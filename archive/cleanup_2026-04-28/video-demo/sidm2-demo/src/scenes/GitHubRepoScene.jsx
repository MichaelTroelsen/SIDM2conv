import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const GitHubRepoScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // Repository structure - file tree animation
  const fileTree = [
    { name: '📁 pyscript/', indent: 0, delay: 40, color: '#00ff88' },
    { name: '  🐍 siddump_complete.py', indent: 1, delay: 50, color: '#00ddff' },
    { name: '  🔄 sidwinder_trace.py', indent: 1, delay: 60, color: '#00ddff' },
    { name: '  🎮 conversion_cockpit_gui.py', indent: 1, delay: 70, color: '#00ddff' },
    { name: '  📊 sf2_viewer_gui.py', indent: 1, delay: 80, color: '#00ddff' },
    { name: '  ✅ test_*.py (50+ files)', indent: 1, delay: 90, color: '#888888' },
    { name: '📁 scripts/', indent: 0, delay: 100, color: '#00ff88' },
    { name: '  🔧 sid_to_sf2.py', indent: 1, delay: 110, color: '#00ddff' },
    { name: '  🔄 sf2_to_sid.py', indent: 1, delay: 120, color: '#00ddff' },
    { name: '  ✅ validate_sid_accuracy.py', indent: 1, delay: 130, color: '#00ddff' },
    { name: '📁 sidm2/', indent: 0, delay: 140, color: '#00ff88' },
    { name: '  🧬 laxity_parser.py', indent: 1, delay: 150, color: '#00ddff' },
    { name: '  🔄 laxity_converter.py', indent: 1, delay: 160, color: '#00ddff' },
    { name: '  📦 sf2_packer.py', indent: 1, delay: 170, color: '#00ddff' },
    { name: '  🎯 driver_selector.py', indent: 1, delay: 180, color: '#00ddff' },
    { name: '📁 docs/', indent: 0, delay: 190, color: '#00ff88' },
    { name: '  📖 50+ MD files', indent: 1, delay: 200, color: '#888888' },
    { name: '📁 G5/drivers/', indent: 0, delay: 210, color: '#00ff88' },
    { name: '  ⚙️ laxity/', indent: 1, delay: 220, color: '#00ddff' },
    { name: '  ⚙️ driver11/', indent: 1, delay: 230, color: '#00ddff' },
    { name: '  ⚙️ np20/', indent: 1, delay: 240, color: '#00ddff' },
  ];

  // GitHub stats - animated counters
  const stats = [
    { label: 'Lines of Code', value: '50K+', icon: '💻', delay: 260 },
    { label: 'Test Coverage', value: '200+', icon: '✅', delay: 280 },
    { label: 'Documentation', value: '50+ MD', icon: '📚', delay: 300 },
    { label: 'Accuracy', value: '99.93%', icon: '🎯', delay: 320 },
  ];

  // Commit graph animation (fake but looks cool)
  const commits = [...Array(30)].map((_, i) => {
    const height = 20 + Math.sin(i * 0.5) * 60;
    const delay = 40 + i * 3;
    return { height, delay, x: i * 35 };
  });

  // Floating GitHub octocats
  const octocats = [...Array(8)].map((_, i) => {
    const angle = (i / 8) * Math.PI * 2;
    const radius = 200 + Math.sin(frame * 0.03 + i) * 50;
    const x = 960 + Math.cos(angle + frame * 0.01) * radius;
    const y = 540 + Math.sin(angle + frame * 0.01) * radius;
    const opacity = interpolate(
      Math.sin(frame * 0.05 + i),
      [-1, 1],
      [0.1, 0.3]
    );
    const scale = interpolate(
      Math.sin(frame * 0.08 + i * 1.5),
      [-1, 1],
      [0.8, 1.2]
    );
    return { x, y, opacity, scale };
  });

  // Repository URL typing effect
  const repoUrl = 'github.com/MichaelTroelsen/SIDM2conv';
  const urlProgress = Math.min(Math.floor(interpolate(frame, [20, 80], [0, repoUrl.length])), repoUrl.length);
  const displayUrl = repoUrl.substring(0, urlProgress);

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%)',
        overflow: 'hidden',
      }}
    >
      {/* Floating GitHub octocats */}
      {octocats.map((cat, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: cat.x,
            top: cat.y,
            opacity: cat.opacity,
            transform: `scale(${cat.scale})`,
            fontSize: 60,
            pointerEvents: 'none',
          }}
        >
          🐙
        </div>
      ))}

      {/* Scanline effect */}
      {[...Array(20)].map((_, i) => {
        const y = (frame * 2 + i * 50) % 1080;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              top: y,
              left: 0,
              right: 0,
              height: 2,
              background: 'rgba(0, 255, 136, 0.1)',
              pointerEvents: 'none',
            }}
          />
        );
      })}

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
            background: 'linear-gradient(135deg, #00ff88 0%, #00ddff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '10px',
            textShadow: '0 0 40px rgba(0, 255, 136, 0.5)',
          }}
        >
          GitHub Repository
        </h2>
        <div
          style={{
            fontSize: 28,
            color: '#00ff88',
            fontFamily: "'Courier New', monospace",
            marginTop: '10px',
          }}
        >
          {displayUrl}
          <span
            style={{
              opacity: Math.sin(frame * 0.3) > 0 ? 1 : 0,
              color: '#00ff88',
            }}
          >
            _
          </span>
        </div>
      </div>

      {/* File Tree - Left Side */}
      <div
        style={{
          position: 'absolute',
          left: '80px',
          top: '200px',
          width: '700px',
        }}
      >
        <div
          style={{
            fontSize: 32,
            color: '#00ff88',
            fontFamily: "'Courier New', monospace",
            marginBottom: '20px',
            textShadow: '0 0 20px rgba(0, 255, 136, 0.5)',
          }}
        >
          📂 Repository Structure
        </div>
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.6)',
            borderRadius: '15px',
            padding: '20px',
            border: '2px solid rgba(0, 255, 136, 0.3)',
            boxShadow: '0 0 30px rgba(0, 255, 136, 0.2)',
          }}
        >
          {fileTree.map((item, i) => {
            const opacity = interpolate(
              frame,
              [item.delay, item.delay + 15],
              [0, 1],
              { extrapolateRight: 'clamp' }
            );
            const x = interpolate(
              frame,
              [item.delay, item.delay + 20],
              [-30, 0],
              { extrapolateRight: 'clamp' }
            );

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `translateX(${x}px)`,
                  fontSize: 18,
                  color: item.color,
                  fontFamily: "'Courier New', monospace",
                  marginBottom: '8px',
                  paddingLeft: `${item.indent * 20}px`,
                }}
              >
                {item.name}
              </div>
            );
          })}
        </div>
      </div>

      {/* Commit Graph - Right Side */}
      <div
        style={{
          position: 'absolute',
          right: '80px',
          top: '200px',
          width: '900px',
        }}
      >
        <div
          style={{
            fontSize: 32,
            color: '#00ddff',
            fontFamily: "'Courier New', monospace",
            marginBottom: '20px',
            textShadow: '0 0 20px rgba(0, 221, 255, 0.5)',
          }}
        >
          📈 Development Activity
        </div>
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.6)',
            borderRadius: '15px',
            padding: '30px',
            border: '2px solid rgba(0, 221, 255, 0.3)',
            boxShadow: '0 0 30px rgba(0, 221, 255, 0.2)',
            height: '300px',
            display: 'flex',
            alignItems: 'flex-end',
            gap: '5px',
          }}
        >
          {commits.map((commit, i) => {
            const opacity = interpolate(
              frame,
              [commit.delay, commit.delay + 10],
              [0, 1],
              { extrapolateRight: 'clamp' }
            );
            const height = interpolate(
              frame,
              [commit.delay, commit.delay + 20],
              [0, commit.height],
              { extrapolateRight: 'clamp' }
            );

            return (
              <div
                key={i}
                style={{
                  width: 25,
                  height: `${height}%`,
                  background: `linear-gradient(180deg, #00ff88 0%, #00ddff 100%)`,
                  borderRadius: '3px',
                  opacity,
                  boxShadow: '0 0 10px rgba(0, 255, 136, 0.5)',
                }}
              />
            );
          })}
        </div>

        {/* Stats Grid */}
        <div
          style={{
            marginTop: '30px',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '20px',
          }}
        >
          {stats.map((stat, i) => {
            const opacity = interpolate(
              frame,
              [stat.delay, stat.delay + 20],
              [0, 1],
              { extrapolateRight: 'clamp' }
            );
            const scale = interpolate(
              frame,
              [stat.delay, stat.delay + 20],
              [0.8, 1],
              { extrapolateRight: 'clamp' }
            );

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: 'rgba(0, 221, 255, 0.1)',
                  padding: '20px',
                  borderRadius: '12px',
                  border: '2px solid rgba(0, 221, 255, 0.4)',
                  boxShadow: '0 0 20px rgba(0, 221, 255, 0.2)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 40, marginBottom: '10px' }}>
                  {stat.icon}
                </div>
                <div
                  style={{
                    fontSize: 36,
                    fontWeight: 'bold',
                    color: '#00ddff',
                    fontFamily: "'Courier New', monospace",
                    marginBottom: '5px',
                  }}
                >
                  {stat.value}
                </div>
                <div style={{ fontSize: 16, color: '#aaaaaa' }}>
                  {stat.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom banner - version info */}
      <div
        style={{
          position: 'absolute',
          bottom: '60px',
          width: '100%',
          textAlign: 'center',
        }}
      >
        {[
          { label: 'Version', value: 'v2.9.1', delay: 340 },
          { label: 'License', value: 'Open Source', delay: 360 },
          { label: 'Platform', value: 'Cross-Platform', delay: 380 },
        ].map((item, i) => {
          const opacity = interpolate(
            frame,
            [item.delay, item.delay + 20],
            [0, 1],
            { extrapolateRight: 'clamp' }
          );

          return (
            <span
              key={i}
              style={{
                opacity,
                display: 'inline-block',
                margin: '0 30px',
                fontSize: 20,
                color: '#00ff88',
                fontFamily: "'Courier New', monospace",
              }}
            >
              {item.label}: <strong style={{ color: '#00ddff' }}>{item.value}</strong>
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
