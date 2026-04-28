import { Composition } from 'remotion';
import { SIDM2Demo } from './SIDM2Demo.jsx';

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="SIDM2Demo"
        component={SIDM2Demo}
        durationInFrames={4800} // 160 seconds (2:40) at 30fps - 16s intro + 144s content
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
