import { AbsoluteFill, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { VideoIntroScene } from './scenes/VideoIntroScene.jsx';
import { TitleScene } from './scenes/TitleScene.jsx';
import { ProblemScene } from './scenes/ProblemScene.jsx';
import { FeaturesScene } from './scenes/FeaturesScene.jsx';
import { ToolsDemoScene } from './scenes/ToolsDemoScene.jsx';
import { WorkflowScene } from './scenes/WorkflowScene.jsx';
import { TechStackScene } from './scenes/TechStackScene.jsx';
import { ResultsScene } from './scenes/ResultsScene.jsx';
import { ClosingScene } from './scenes/ClosingScene.jsx';

export const SIDM2Demo = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Audio fade out in last 3 seconds (90 frames)
  const audioVolume = interpolate(
    frame,
    [durationInFrames - 90, durationInFrames],
    [0.3, 0],
    { extrapolateRight: 'clamp' }
  );

  // Intro video is 47.8 seconds = ~1434 frames at 30fps
  const introFrames = 1434;

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f0f1e' }}>
      {/* Background Music - plays throughout with fade out at end */}
      <Audio
        src={staticFile('assets/audio/background-music.mp3')}
        volume={(f) => {
          // Start from intro end
          if (f < introFrames) return 0;
          // Fade in over 1 second after intro
          if (f < introFrames + 30) {
            return interpolate(f, [introFrames, introFrames + 30], [0, 0.3]);
          }
          // Fade out at end
          return interpolate(
            f,
            [durationInFrames - 90, durationInFrames],
            [0.3, 0],
            { extrapolateRight: 'clamp' }
          );
        }}
        startFrom={0}
      />

      {/* Video Intro - 47.8 seconds (~1434 frames) */}
      <Sequence from={0} durationInFrames={introFrames}>
        <VideoIntroScene />
      </Sequence>

      {/* Title Scene - 5 seconds (150 frames) */}
      <Sequence from={introFrames} durationInFrames={150}>
        <TitleScene />
      </Sequence>

      {/* Problem Statement - 5 seconds (150 frames) */}
      <Sequence from={introFrames + 150} durationInFrames={150}>
        <ProblemScene />
      </Sequence>

      {/* Key Features - 8 seconds (240 frames) */}
      <Sequence from={introFrames + 300} durationInFrames={240}>
        <FeaturesScene />
      </Sequence>

      {/* Workflow Demo - 10 seconds (300 frames) */}
      <Sequence from={introFrames + 540} durationInFrames={300}>
        <WorkflowScene />
      </Sequence>

      {/* Tools Demo - 10 seconds (300 frames) */}
      <Sequence from={introFrames + 840} durationInFrames={300}>
        <ToolsDemoScene />
      </Sequence>

      {/* Technical Stack - 8 seconds (240 frames) */}
      <Sequence from={introFrames + 1140} durationInFrames={240}>
        <TechStackScene />
      </Sequence>

      {/* Results - 7 seconds (210 frames) */}
      <Sequence from={introFrames + 1380} durationInFrames={210}>
        <ResultsScene />
      </Sequence>

      {/* Closing - 5 seconds (150 frames) */}
      <Sequence from={introFrames + 1590} durationInFrames={150}>
        <ClosingScene />
      </Sequence>
    </AbsoluteFill>
  );
};
