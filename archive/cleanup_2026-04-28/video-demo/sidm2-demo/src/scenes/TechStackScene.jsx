import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const TechStackScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);

  const tools = [
    { name: 'Python 3.9+', desc: 'Core Language', delay: 40 },
    { name: 'PyQt6', desc: 'GUI Framework', delay: 70 },
    { name: 'Custom Drivers', desc: 'Laxity, NP20, Driver 11', delay: 100 },
    { name: 'Validation System', desc: 'Frame-by-frame accuracy', delay: 130 },
    { name: 'siddump & SIDwinder', desc: '100% Python ports', delay: 160 },
    { name: 'Test Suite', desc: '200+ automated tests', delay: 190 },
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1a1a2e',
        padding: '80px',
      }}
    >
      <div style={{ opacity: titleOpacity }}>
        <h2
          style={{
            fontSize: 60,
            color: '#00ff88',
            marginBottom: '60px',
            fontFamily: 'Arial, sans-serif',
          }}
        >
          Technical Stack
        </h2>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: '40px',
        }}
      >
        {tools.map((tool, index) => {
          const toolOpacity = interpolate(
            frame,
            [tool.delay, tool.delay + 20],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          );

          const toolSlide = interpolate(
            frame,
            [tool.delay, tool.delay + 20],
            [-50, 0],
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
                transform: `translateX(${toolSlide}px)`,
                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                padding: '30px',
                borderRadius: '10px',
                border: '2px solid rgba(0, 255, 136, 0.3)',
              }}
            >
              <h3
                style={{
                  fontSize: 32,
                  color: '#00ff88',
                  margin: '0 0 15px 0',
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                {tool.name}
              </h3>
              <p
                style={{
                  fontSize: 24,
                  color: '#aaaaaa',
                  margin: 0,
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                {tool.desc}
              </p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
