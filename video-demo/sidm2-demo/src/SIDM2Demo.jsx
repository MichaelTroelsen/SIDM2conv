import { AbsoluteFill, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { VideoIntroScene } from './scenes/VideoIntroScene.jsx';
import { TitleScene } from './scenes/TitleScene.jsx';
import { ProblemScene } from './scenes/ProblemScene.jsx';
import { FeaturesScene } from './scenes/FeaturesScene.jsx';
import { ConversionPipelineAnimated } from './scenes/ConversionPipelineAnimated.jsx';
import { WorkflowScene } from './scenes/WorkflowScene.jsx';
import { SF2ViewerDemoScene } from './scenes/SF2ViewerDemoScene.jsx';
import { ToolsDemoScene } from './scenes/ToolsDemoScene.jsx';
import { PythonToolsScene } from './scenes/PythonToolsScene.jsx';
import { GitHubRepoScene } from './scenes/GitHubRepoScene.jsx';
import { ResearchDocsScene } from './scenes/ResearchDocsScene.jsx';
import { TechStackScene } from './scenes/TechStackScene.jsx';
import { ResultsScene } from './scenes/ResultsScene.jsx';
import { ExcitingFinale } from './scenes/ExcitingFinale.jsx';
import { ClosingScene } from './scenes/ClosingScene.jsx';

export const SIDM2Demo = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Audio fade out in last 3 seconds (90 frames)
  const audioVolume = interpolate(
    frame,
    [durationInFrames - 90, durationInFrames],
    [0.42, 0],
    { extrapolateRight: 'clamp' }
  );

  // Intro video is 16 seconds = 480 frames at 30fps
  const introFrames = 16 * 30; // 480 frames

  // Music starts at 17 seconds = 510 frames (1 second after intro ends)
  const musicStartFrame = 17 * 30; // 510 frames

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f0f1e' }}>
      {/* Background Music - starts at 17 seconds, plays for entire video at 0.42 volume (40% increase) */}
      <Audio
        src={staticFile('assets/audio/background-music.mp3')}
        volume={0.42}
        startFrom={musicStartFrame}
        endAt={durationInFrames - 30}
        loop={true}
      />

      {/* Video Intro - 16 seconds (480 frames) */}
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

      {/* Key Features - 10 seconds (300 frames) - extended */}
      <Sequence from={introFrames + 300} durationInFrames={300}>
        <FeaturesScene />
      </Sequence>

      {/* Conversion Pipeline Animated - 12 seconds (360 frames) */}
      <Sequence from={introFrames + 600} durationInFrames={360}>
        <ConversionPipelineAnimated />
      </Sequence>

      {/* Workflow Demo - 10 seconds (300 frames) */}
      <Sequence from={introFrames + 960} durationInFrames={300}>
        <WorkflowScene />
      </Sequence>

      {/* SF2 Viewer Demo - 12 seconds (360 frames) */}
      <Sequence from={introFrames + 1260} durationInFrames={360}>
        <SF2ViewerDemoScene />
      </Sequence>

      {/* Tools Demo - 10 seconds (300 frames) */}
      <Sequence from={introFrames + 1620} durationInFrames={300}>
        <ToolsDemoScene />
      </Sequence>

      {/* Python Tools - 12 seconds (360 frames) */}
      <Sequence from={introFrames + 1920} durationInFrames={360}>
        <PythonToolsScene />
      </Sequence>

      {/* GitHub Repository - 12 seconds (360 frames) */}
      <Sequence from={introFrames + 2280} durationInFrames={360}>
        <GitHubRepoScene />
      </Sequence>

      {/* Research & Documentation - 16 seconds (480 frames) */}
      <Sequence from={introFrames + 2640} durationInFrames={480}>
        <ResearchDocsScene />
      </Sequence>

      {/* Technical Stack - 8 seconds (240 frames) */}
      <Sequence from={introFrames + 3120} durationInFrames={240}>
        <TechStackScene />
      </Sequence>

      {/* Results - 8 seconds (240 frames) */}
      <Sequence from={introFrames + 3360} durationInFrames={240}>
        <ResultsScene />
      </Sequence>

      {/* Exciting Finale - 12 seconds (360 frames) */}
      <Sequence from={introFrames + 3600} durationInFrames={360}>
        <ExcitingFinale />
      </Sequence>

      {/* Closing - 12 seconds (360 frames) - Final credits */}
      <Sequence from={introFrames + 3960} durationInFrames={360}>
        <ClosingScene />
      </Sequence>
    </AbsoluteFill>
  );
};
