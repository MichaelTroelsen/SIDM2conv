import { AbsoluteFill, Video, staticFile } from 'remotion';

export const VideoIntroScene = () => {
  return (
    <AbsoluteFill style={{
      backgroundColor: '#000',
      justifyContent: 'center',
      alignItems: 'center',
    }}>
      <Video
        src={staticFile('assets/intro-video.mp4')}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
        }}
      />
    </AbsoluteFill>
  );
};
