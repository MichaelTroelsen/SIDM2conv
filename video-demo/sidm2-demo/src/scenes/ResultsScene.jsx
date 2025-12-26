import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const ResultsScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);

  const stats = [
    { value: '99.93%', label: 'Frame Accuracy', delay: 40 },
    { value: '286', label: 'Laxity Files Converted', delay: 80 },
    { value: '100%', label: 'Test Pass Rate', delay: 120 },
    { value: '8.1', label: 'Files/Second', delay: 160 },
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1a1a2e',
        padding: '80px',
        justifyContent: 'center',
      }}
    >
      <div style={{ opacity: titleOpacity }}>
        <h2
          style={{
            fontSize: 60,
            color: '#00ff88',
            marginBottom: '80px',
            fontFamily: 'Arial, sans-serif',
            textAlign: 'center',
          }}
        >
          Proven Results
        </h2>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '60px',
          padding: '0 100px',
        }}
      >
        {stats.map((stat, index) => {
          const statOpacity = interpolate(
            frame,
            [stat.delay, stat.delay + 20],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          );

          const statScale = interpolate(
            frame,
            [stat.delay, stat.delay + 20],
            [0.8, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          );

          return (
            <div
              key={index}
              style={{
                opacity: statOpacity,
                transform: `scale(${statScale})`,
                textAlign: 'center',
                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                padding: '50px',
                borderRadius: '15px',
                border: '3px solid #00ff88',
              }}
            >
              <div
                style={{
                  fontSize: 100,
                  fontWeight: 'bold',
                  color: '#00ff88',
                  marginBottom: '20px',
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                {stat.value}
              </div>
              <p
                style={{
                  fontSize: 32,
                  color: '#ffffff',
                  margin: 0,
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                {stat.label}
              </p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
