import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const ClosingScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const linkOpacity = interpolate(frame, [40, 60], [0, 1]);
  const ctaOpacity = interpolate(frame, [80, 100], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1a1a2e',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div style={{ textAlign: 'center', opacity: titleOpacity }}>
        <h2
          style={{
            fontSize: 80,
            color: '#00ff88',
            marginBottom: '40px',
            fontFamily: 'Arial, sans-serif',
          }}
        >
          SIDM2
        </h2>
        <p
          style={{
            fontSize: 40,
            color: '#ffffff',
            margin: '0 0 60px 0',
            fontFamily: 'Arial, sans-serif',
          }}
        >
          Professional C64 SID Conversion
        </p>
      </div>

      <div style={{ opacity: linkOpacity, textAlign: 'center' }}>
        <div
          style={{
            backgroundColor: 'rgba(0, 255, 136, 0.2)',
            padding: '30px 60px',
            borderRadius: '15px',
            border: '3px solid #00ff88',
            marginBottom: '40px',
          }}
        >
          <p
            style={{
              fontSize: 36,
              color: '#00ff88',
              margin: 0,
              fontFamily: 'monospace',
            }}
          >
            github.com/MichaelTroelsen/SIDM2conv
          </p>
        </div>
      </div>

      <div style={{ opacity: ctaOpacity, textAlign: 'center' }}>
        <p
          style={{
            fontSize: 32,
            color: '#aaaaaa',
            margin: 0,
            fontFamily: 'Arial, sans-serif',
          }}
        >
          Start Converting Today • Free & Open Source
        </p>
      </div>
    </AbsoluteFill>
  );
};
