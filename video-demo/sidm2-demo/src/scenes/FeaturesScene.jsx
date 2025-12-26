import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const FeaturesScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const features = [
    { text: '99.93% Frame Accuracy', delay: 40 },
    { text: 'Automatic Driver Selection', delay: 80 },
    { text: '200+ Passing Tests', delay: 120 },
    { text: '658+ Files Cataloged', delay: 160 },
    { text: 'Cross-Platform Python Tools', delay: 200 },
    { text: 'GUI & CLI Interfaces', delay: 240 },
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

          return (
            <div
              key={index}
              style={{
                opacity: featureOpacity,
                transform: `translateY(${featureTranslate}px)`,
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                padding: '30px',
                borderRadius: '10px',
                border: '2px solid rgba(0, 255, 136, 0.3)',
              }}
            >
              <div
                style={{
                  fontSize: 80,
                  marginBottom: '15px',
                }}
              >
                ✓
              </div>
              <p
                style={{
                  fontSize: 32,
                  color: '#ffffff',
                  margin: 0,
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                {feature.text}
              </p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
