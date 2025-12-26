import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';

export const ResearchDocsScene = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const titleY = interpolate(frame, [0, 30], [-50, 0]);

  // Documentation categories with files
  const docCategories = [
    {
      title: '📘 User Guides',
      color: '#00ff88',
      docs: [
        'TROUBLESHOOTING.md - Complete error solutions',
        'SF2_VIEWER_GUIDE.md - Viewer & exporter',
        'CONVERSION_COCKPIT_USER_GUIDE.md - Batch GUI',
        'LAXITY_DRIVER_USER_GUIDE.md - 99.93% accuracy',
        'VALIDATION_GUIDE.md - Quality assurance',
      ],
      delay: 40,
    },
    {
      title: '🔬 Technical Research',
      color: '#00ddff',
      docs: [
        'ARCHITECTURE.md - System design',
        'SF2_FORMAT_SPEC.md - File format deep dive',
        'LAXITY_DRIVER_TECHNICAL_REFERENCE.md',
        'WAVE_TABLE_FORMAT_FIX.md - Critical breakthrough',
        'ACCURACY_OPTIMIZATION_ANALYSIS.md',
      ],
      delay: 140,
    },
    {
      title: '⚙️ Implementation Docs',
      color: '#ff00ff',
      docs: [
        'SIDDUMP_PYTHON_IMPLEMENTATION.md',
        'SIDWINDER_PYTHON_DESIGN.md',
        'SF2_EDITOR_INTEGRATION_IMPLEMENTATION.md',
        'LAXITY_DRIVER_IMPLEMENTATION.md - 6 phases',
        'COMPLETE_CONVERSION_PIPELINE.md',
      ],
      delay: 240,
    },
    {
      title: '📊 Analysis & Results',
      color: '#ffaa00',
      docs: [
        'ACCURACY_FIX_VERIFICATION_REPORT.md',
        'BATCH_HISTORY_FEATURE.md',
        'COMPLETE_TOOL_INTEGRATION_PLAN.md',
        'LAXITY_FULL_COLLECTION_CONVERSION_RESULTS.md',
        'Pattern analysis tools & databases',
      ],
      delay: 340,
    },
  ];

  // Scrolling research highlights
  const scrollY = interpolate(frame, [80, 600], [0, -1200], { extrapolateRight: 'clamp' });

  const researchHighlights = [
    {
      title: 'Wave Table Format Discovery',
      content: 'Critical breakthrough: Identified SF2 row-major vs Laxity column-major mismatch',
      impact: '497x accuracy improvement (0.20% → 99.93%)',
      color: '#00ff88',
    },
    {
      title: 'Python siddump Implementation',
      content: 'Pure Python replacement for siddump.exe - 595 lines, zero dependencies',
      impact: '100% musical content accuracy, cross-platform',
      color: '#00ddff',
    },
    {
      title: 'Automatic Driver Selection',
      content: 'Quality-First Policy v2.0 - intelligent driver selection based on player type',
      impact: 'Laxity: 99.93%, SF2: 100%, NP20: 70-90%',
      color: '#ff00ff',
    },
    {
      title: 'SID Inventory System',
      content: 'Complete catalog of 658+ SID files with pattern validation',
      impact: 'Automated player detection & optimal conversion',
      color: '#ffaa00',
    },
    {
      title: 'Validation Framework',
      content: '200+ automated tests, frame-by-frame accuracy validation',
      impact: '100% pass rate across test suite',
      color: '#00ff88',
    },
    {
      title: 'SF2 Format Validation',
      content: 'Fixed metadata corruption causing editor rejection',
      impact: 'Production-ready SF2 files for SID Factory II',
      color: '#00ddff',
    },
  ];

  // Floating document pages
  const floatingDocs = [...Array(15)].map((_, i) => {
    const angle = (i / 15) * Math.PI * 2;
    const radius = 400 + Math.sin(frame * 0.02 + i) * 100;
    const x = 960 + Math.cos(angle + frame * 0.01) * radius;
    const y = 540 + Math.sin(angle + frame * 0.01) * radius;
    const opacity = interpolate(
      Math.sin(frame * 0.04 + i),
      [-1, 1],
      [0.05, 0.15]
    );
    const rotation = interpolate(frame, [0, 600], [0, 360]);
    return { x, y, opacity, rotation: rotation + i * 24 };
  });

  // Stats counters
  const stats = [
    { label: 'Documentation Files', value: '50+', icon: '📚' },
    { label: 'Research Hours', value: '500+', icon: '⏱️' },
    { label: 'Code Examples', value: '100+', icon: '💻' },
  ];

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #1a0033 0%, #0a1f3f 50%, #0f0f1e 100%)',
        overflow: 'hidden',
      }}
    >
      {/* Floating document pages */}
      {floatingDocs.map((doc, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: doc.x,
            top: doc.y,
            width: 60,
            height: 80,
            background: 'rgba(255, 255, 255, 0.9)',
            borderRadius: '4px',
            opacity: doc.opacity,
            transform: `rotate(${doc.rotation}deg)`,
            boxShadow: '0 0 10px rgba(0, 255, 136, 0.3)',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              width: '100%',
              height: '100%',
              background: 'linear-gradient(180deg, #00ff88 0%, #00ddff 100%)',
              opacity: 0.2,
            }}
          />
        </div>
      ))}

      {/* Matrix-style falling characters */}
      {[...Array(30)].map((_, i) => {
        const x = (i * 64) % 1920;
        const y = ((frame * (2 + (i % 5))) % 1200) - 200;
        const opacity = interpolate(y, [-200, 0, 1000, 1200], [0, 0.3, 0.3, 0]);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              color: '#00ff88',
              fontFamily: "'Courier New', monospace",
              fontSize: 16,
              opacity,
              pointerEvents: 'none',
            }}
          >
            #
          </div>
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
          zIndex: 10,
        }}
      >
        <h2
          style={{
            fontSize: 80,
            fontWeight: 'bold',
            background: 'linear-gradient(135deg, #00ff88 0%, #00ddff 50%, #ff00ff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '10px',
            textShadow: '0 0 40px rgba(0, 255, 136, 0.5)',
          }}
        >
          Research & Documentation
        </h2>
        <p
          style={{
            fontSize: 32,
            color: '#aaaaaa',
            margin: 0,
          }}
        >
          Comprehensive Technical Knowledge Base
        </p>
      </div>

      {/* Scrolling content */}
      <div
        style={{
          position: 'absolute',
          top: '180px',
          left: '60px',
          right: '60px',
          transform: `translateY(${scrollY}px)`,
        }}
      >
        {/* Documentation categories */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '30px',
            marginBottom: '60px',
          }}
        >
          {docCategories.map((category, i) => {
            const opacity = interpolate(
              frame,
              [category.delay, category.delay + 30],
              [0, 1],
              { extrapolateRight: 'clamp' }
            );
            const scale = interpolate(
              frame,
              [category.delay, category.delay + 30],
              [0.9, 1],
              { extrapolateRight: 'clamp' }
            );

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: 'rgba(0, 0, 0, 0.7)',
                  borderRadius: '15px',
                  padding: '25px',
                  border: `2px solid ${category.color}60`,
                  boxShadow: `0 0 30px ${category.color}40`,
                  backdropFilter: 'blur(10px)',
                }}
              >
                <h3
                  style={{
                    fontSize: 28,
                    color: category.color,
                    fontFamily: "'Courier New', monospace",
                    marginBottom: '15px',
                    textShadow: `0 0 20px ${category.color}`,
                  }}
                >
                  {category.title}
                </h3>
                {category.docs.map((doc, j) => (
                  <div
                    key={j}
                    style={{
                      fontSize: 16,
                      color: '#aaaaaa',
                      fontFamily: "'Courier New', monospace",
                      marginBottom: '8px',
                      paddingLeft: '10px',
                      borderLeft: `2px solid ${category.color}40`,
                    }}
                  >
                    • {doc}
                  </div>
                ))}
              </div>
            );
          })}
        </div>

        {/* Research highlights */}
        <div style={{ marginTop: '60px' }}>
          <h3
            style={{
              fontSize: 48,
              color: '#00ff88',
              fontFamily: "'Courier New', monospace",
              textAlign: 'center',
              marginBottom: '40px',
              textShadow: '0 0 30px rgba(0, 255, 136, 0.5)',
            }}
          >
            🔬 Key Research Breakthroughs
          </h3>
          {researchHighlights.map((highlight, i) => (
            <div
              key={i}
              style={{
                marginBottom: '30px',
                background: `linear-gradient(90deg, ${highlight.color}20 0%, transparent 100%)`,
                borderRadius: '15px',
                padding: '25px',
                border: `2px solid ${highlight.color}60`,
                boxShadow: `0 0 25px ${highlight.color}30`,
              }}
            >
              <h4
                style={{
                  fontSize: 28,
                  color: highlight.color,
                  fontFamily: "'Courier New', monospace",
                  marginBottom: '10px',
                  textShadow: `0 0 15px ${highlight.color}`,
                }}
              >
                {highlight.title}
              </h4>
              <p
                style={{
                  fontSize: 18,
                  color: '#cccccc',
                  marginBottom: '10px',
                  lineHeight: 1.6,
                }}
              >
                {highlight.content}
              </p>
              <div
                style={{
                  fontSize: 20,
                  color: '#00ff88',
                  fontFamily: "'Courier New', monospace",
                  fontWeight: 'bold',
                }}
              >
                💡 Impact: {highlight.impact}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stats at bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: '60px',
          width: '100%',
          display: 'flex',
          justifyContent: 'center',
          gap: '60px',
          zIndex: 10,
        }}
      >
        {stats.map((stat, i) => {
          const delay = 480 + i * 20;
          const opacity = interpolate(
            frame,
            [delay, delay + 20],
            [0, 1],
            { extrapolateRight: 'clamp' }
          );
          const scale = interpolate(
            Math.sin(frame * 0.1 + i * 2),
            [-1, 1],
            [0.95, 1.05]
          );

          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `scale(${scale})`,
                textAlign: 'center',
                background: 'rgba(0, 255, 136, 0.1)',
                padding: '25px 40px',
                borderRadius: '15px',
                border: '3px solid #00ff88',
                boxShadow: '0 0 30px rgba(0, 255, 136, 0.3)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <div style={{ fontSize: 48, marginBottom: '10px' }}>{stat.icon}</div>
              <div
                style={{
                  fontSize: 48,
                  fontWeight: 'bold',
                  color: '#00ff88',
                  fontFamily: "'Courier New', monospace",
                  textShadow: '0 0 20px rgba(0, 255, 136, 0.8)',
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 20, color: '#aaaaaa', marginTop: '5px' }}>
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
