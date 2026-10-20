import React from 'react';
import {Composition} from 'remotion';
import {PureExplainer} from './PureExplainer';
import {FPS, TOTAL_DURATION_IN_FRAMES} from './data/timeline';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="PUREExplainer"
      component={PureExplainer}
      durationInFrames={TOTAL_DURATION_IN_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
  );
};
