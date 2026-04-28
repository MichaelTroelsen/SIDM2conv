import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const ProblemScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const problemOpacity = interpolate(frame, [30, 50], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const solutionOpacity = interpolate(frame, [90, 110], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

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
            marginBottom: '40px',
            fontFamily: 'Arial, sans-serif',
          }}
        >
          The Challenge
        </h2>
      </div>

      <div style={{ opacity: problemOpacity }}>
        <p
          style={{
            fontSize: 36,
            color: '#ffffff',
            marginBottom: '30px',
            fontFamily: 'Arial, sans-serif',
            lineHeight: 1.6,
          }}
        >
          Converting Commodore 64 SID music files<br />
          to SID Factory II (SF2) format for editing
        </p>
      </div>

      <div style={{ opacity: solutionOpacity }}>
        <div
          style={{
            backgroundColor: 'rgba(0, 255, 136, 0.1)',
            padding: '30px',
            borderLeft: '5px solid #00ff88',
            marginTop: '40px',
          }}
        >
          <p
            style={{
              fontSize: 32,
              color: '#00ff88',
              margin: 0,
              fontFamily: 'Arial, sans-serif',
            }}
          >
            Preserve musical accuracy while maintaining<br />
            editability in modern tools
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};
