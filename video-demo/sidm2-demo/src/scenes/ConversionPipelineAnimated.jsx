import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Sequence, spring } from 'remotion';

export const ConversionPipelineAnimated = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animation stages (each 90 frames = 3 seconds)
  const stages = [
    { start: 0, end: 90, title: "Step 1: SID Analysis", color: "#FF6B6B" },
    { start: 90, end: 180, title: "Step 2: Player Detection", color: "#4ECDC4" },
    { start: 180, end: 270, title: "Step 3: Data Extraction", color: "#45B7D1" },
    { start: 270, end: 360, title: "Step 4: SF2 Generation", color: "#96CEB4" },
    { start: 360, end: 450, title: "Step 5: Validation", color: "#FFEAA7" }
  ];

  return (
    <AbsoluteFill style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      {/* Animated Background Particles */}
      {[...Array(20)].map((_, i) => {
        const delay = i * 10;
        const movement = spring({
          frame: frame - delay,
          fps,
          config: { damping: 100, mass: 0.5 }
        });
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${(i * 5) % 100}%`,
              top: `${Math.sin(frame / 30 + i) * 20 + 50}%`,
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: 'rgba(255,255,255,0.3)',
              opacity: movement,
            }}
          />
        );
      })}

      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 60,
        width: '100%',
        textAlign: 'center',
        fontSize: 64,
        fontWeight: 'bold',
        color: 'white',
        textShadow: '0 0 20px rgba(0,0,0,0.5)',
        opacity: interpolate(frame, [0, 30], [0, 1]),
      }}>
        Conversion Pipeline
      </div>

      {/* Conversion Steps */}
      <div style={{
        position: 'absolute',
        top: 200,
        left: 100,
        right: 100,
        display: 'flex',
        flexDirection: 'column',
        gap: 30,
      }}>
        {stages.map((stage, index) => {
          const isActive = frame >= stage.start && frame < stage.end;
          const isPast = frame >= stage.end;

          const scale = spring({
            frame: frame - stage.start,
            fps,
            config: { damping: 20 }
          });

          const opacity = interpolate(
            frame,
            [stage.start, stage.start + 15],
            [0, 1],
            { extrapolateRight: 'clamp' }
          );

          return (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                opacity,
                transform: `scale(${isActive ? scale : 1})`,
              }}
            >
              {/* Step Number */}
              <div style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                backgroundColor: isPast ? '#27ae60' : isActive ? stage.color : '#555',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 36,
                fontWeight: 'bold',
                color: 'white',
                boxShadow: isActive ? `0 0 30px ${stage.color}` : 'none',
                transition: 'all 0.3s',
              }}>
                {index + 1}
              </div>

              {/* Arrow */}
              <div style={{
                width: 80,
                height: 4,
                backgroundColor: isPast ? '#27ae60' : isActive ? stage.color : '#555',
                marginLeft: 20,
                marginRight: 20,
              }} />

              {/* Step Title */}
              <div style={{
                flex: 1,
                padding: 20,
                backgroundColor: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.1)',
                borderRadius: 10,
                backdropFilter: 'blur(10px)',
                border: isActive ? `3px solid ${stage.color}` : '3px solid transparent',
              }}>
                <div style={{
                  fontSize: 32,
                  fontWeight: 'bold',
                  color: 'white',
                  marginBottom: 10,
                }}>
                  {stage.title}
                </div>
                <div style={{
                  fontSize: 20,
                  color: 'rgba(255,255,255,0.8)',
                }}>
                  {index === 0 && "Parsing SID file header and music data"}
                  {index === 1 && "Detecting Laxity NewPlayer v21 format"}
                  {index === 2 && "Extracting sequences, instruments, wave tables"}
                  {index === 3 && "Generating SF2 format with custom driver"}
                  {index === 4 && "99.93% frame accuracy validation"}
                </div>
              </div>

              {/* Checkmark for completed */}
              {isPast && (
                <div style={{
                  marginLeft: 20,
                  fontSize: 48,
                  color: '#27ae60',
                }}>
                  ✓
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Progress Bar */}
      <div style={{
        position: 'absolute',
        bottom: 100,
        left: 100,
        right: 100,
        height: 20,
        backgroundColor: 'rgba(255,255,255,0.2)',
        borderRadius: 10,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${(frame / 450) * 100}%`,
          height: '100%',
          background: 'linear-gradient(90deg, #FF6B6B, #4ECDC4, #45B7D1, #96CEB4, #FFEAA7)',
          transition: 'width 0.3s',
        }} />
      </div>
    </AbsoluteFill>
  );
};
