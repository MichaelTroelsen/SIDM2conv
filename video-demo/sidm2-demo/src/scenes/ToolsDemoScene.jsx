import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from 'remotion';

export const ToolsDemoScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // Tool screenshots with staggered animations
  const tools = [
    {
      name: 'SF2 Viewer',
      desc: 'Inspect & Export',
      image: 'screenshots/sf2-viewer.png',
      delay: 40
    },
    {
      name: 'Conversion Cockpit',
      desc: 'Batch Processing',
      image: 'screenshots/conversion-cockpit.png',
      delay: 100
    },
    {
      name: 'SID Factory II',
      desc: 'Professional Editing',
      image: 'screenshots/sf2-editor.png',
      delay: 160
    },
  ];

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #0a3d3d 100%)',
      }}
    >
      {/* Animated background particles */}
      {[...Array(20)].map((_, i) => {
        const particleY = interpolate(
          frame,
          [0, 300],
          [Math.random() * 1080, Math.random() * 1080 - 200],
          { extrapolateRight: 'wrap' }
        );
        const particleX = 50 + Math.random() * 1820;
        const particleSize = 2 + Math.random() * 4;
        const particleOpacity = 0.1 + Math.random() * 0.3;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: particleX,
              top: particleY,
              width: particleSize,
              height: particleSize,
              borderRadius: '50%',
              background: '#00ff88',
              opacity: particleOpacity,
            }}
          />
        );
      })}

      <div style={{ padding: '60px', position: 'relative', zIndex: 1 }}>
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
          }}
        >
          <h2
            style={{
              fontSize: 70,
              background: 'linear-gradient(90deg, #00ff88 0%, #00ddff 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              marginBottom: '20px',
              fontFamily: 'Arial, sans-serif',
              fontWeight: 'bold',
            }}
          >
            Professional Tools
          </h2>
          <div
            style={{
              height: '4px',
              width: '200px',
              background: 'linear-gradient(90deg, #00ff88 0%, transparent 100%)',
              marginBottom: '60px',
            }}
          />
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: '40px',
            marginTop: '40px',
          }}
        >
          {tools.map((tool, index) => {
            const toolOpacity = interpolate(
              frame,
              [tool.delay, tool.delay + 30],
              [0, 1],
              {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }
            );

            const toolScale = interpolate(
              frame,
              [tool.delay, tool.delay + 30],
              [0.8, 1],
              {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }
            );

            const toolRotate = interpolate(
              frame,
              [tool.delay, tool.delay + 30],
              [-5, 0],
              {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }
            );

            return (
              <div
                key={index}
                style={{
                  opacity: toolOpacity,
                  transform: `scale(${toolScale}) rotate(${toolRotate}deg)`,
                }}
              >
                <div
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '15px',
                    padding: '20px',
                    border: '2px solid rgba(0, 255, 136, 0.3)',
                    boxShadow: '0 8px 32px rgba(0, 255, 136, 0.2)',
                    backdropFilter: 'blur(10px)',
                    transition: 'all 0.3s ease',
                  }}
                >
                  {/* Screenshot container */}
                  <div
                    style={{
                      width: '100%',
                      height: '280px',
                      backgroundColor: 'rgba(0, 0, 0, 0.3)',
                      borderRadius: '10px',
                      marginBottom: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                      border: '1px solid rgba(0, 255, 136, 0.2)',
                    }}
                  >
                    <Img
                      src={staticFile(`assets/${tool.image}`)}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                      }}
                      onError={(e) => {
                        // Fallback if image doesn't exist
                        e.currentTarget.style.display = 'none';
                        e.currentTarget.parentElement.innerHTML = `
                          <div style="color: #00ff88; font-size: 48px;">📸</div>
                          <div style="color: #888; font-size: 14px; margin-top: 10px;">
                            Screenshot<br/>pending
                          </div>
                        `;
                      }}
                    />
                  </div>

                  <h3
                    style={{
                      fontSize: 28,
                      color: '#00ff88',
                      margin: '0 0 10px 0',
                      fontFamily: 'Arial, sans-serif',
                      fontWeight: 'bold',
                    }}
                  >
                    {tool.name}
                  </h3>
                  <p
                    style={{
                      fontSize: 20,
                      color: '#aaaaaa',
                      margin: 0,
                      fontFamily: 'Arial, sans-serif',
                    }}
                  >
                    {tool.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
