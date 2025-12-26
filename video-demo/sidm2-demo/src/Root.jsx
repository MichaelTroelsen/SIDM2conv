import { Composition } from 'remotion';
import { SIDM2Demo } from './SIDM2Demo.jsx';

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="SIDM2Demo"
        component={SIDM2Demo}
        durationInFrames={3174} // 105.8 seconds at 30fps (47.8s intro + 58s content)
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
