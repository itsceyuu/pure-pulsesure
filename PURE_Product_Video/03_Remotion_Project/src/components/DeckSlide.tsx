import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {PureLogo} from './PureLogo';

type Props = {
  slide: number;
  durationInFrames: number;
  fromScale?: number;
  toScale?: number;
  fromX?: number;
  toX?: number;
  fromY?: number;
  toY?: number;
  showLogo?: boolean;
  fadeInFrames?: number;
  fadeOutFrames?: number;
};

export const DeckSlide: React.FC<Props> = ({
  slide,
  durationInFrames,
  fromScale = 1,
  toScale = 1.025,
  fromX = 0,
  toX = 0,
  fromY = 0,
  toY = 0,
  showLogo = true,
  fadeInFrames = 10,
  fadeOutFrames = 10,
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [fromScale, toScale], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const x = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [fromX, toX], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const y = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [fromY, toY], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opacity = interpolate(
    frame,
    [0, fadeInFrames, Math.max(fadeInFrames, durationInFrames - fadeOutFrames), durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const filename = `deck/slide-${String(slide).padStart(2, '0')}.png`;

  return (
    <AbsoluteFill style={{background: '#F7FAFA', overflow: 'hidden', opacity}}>
      <Img
        src={staticFile(filename)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `translate3d(${x}px, ${y}px, 0) scale(${scale})`,
          transformOrigin: 'center center',
        }}
      />
      {showLogo ? (
        <div style={{position: 'absolute', right: 30, top: 24}}>
          <PureLogo compact />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
