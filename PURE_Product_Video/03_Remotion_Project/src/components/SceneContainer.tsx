import React, {type ReactNode} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS, LAYOUT} from '../theme';
import {PureLogo} from './PureLogo';

type Props = {
  scene: TimelineScene;
  children: ReactNode;
  accent?: string;
  footerNote?: string;
};

export const SceneContainer: React.FC<Props> = ({scene, children, accent = COLORS.signalMint, footerNote}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = spring({frame, fps, config: {damping: 18, stiffness: 110, mass: 0.8}});
  const exit = interpolate(frame, [scene.durationInFrames - 18, scene.durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const progress = interpolate(frame, [0, scene.durationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        overflow: 'hidden',
        background: `radial-gradient(circle at 82% 18%, ${accent}1f 0%, transparent 33%), ${COLORS.midnightNavy}`,
        color: COLORS.pureWhite,
        opacity: exit,
      }}
    >
      <AbsoluteFill
        style={{
          opacity: 0.16,
          backgroundImage:
            'linear-gradient(rgba(246,248,247,0.10) 1px, transparent 1px), linear-gradient(90deg, rgba(246,248,247,0.10) 1px, transparent 1px)',
          backgroundSize: '72px 72px',
          transform: `translateX(${frame * -0.08}px)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: `${LAYOUT.marginTop}px ${LAYOUT.marginX}px ${LAYOUT.marginBottom}px`,
          transform: `translateY(${(1 - entrance) * 24}px)`,
          opacity: entrance,
        }}
      >
        {children}
      </div>
      <div style={{position: 'absolute', right: LAYOUT.marginX, top: 28}}>
        <PureLogo compact />
      </div>
      <div
        style={{
          position: 'absolute',
          left: LAYOUT.marginX,
          right: LAYOUT.marginX,
          bottom: 30,
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          color: COLORS.coolIvory,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: 0.8,
        }}
      >
        <span style={{minWidth: 220, opacity: 0.68}}>{scene.title.toUpperCase()}</span>
        <div style={{height: 3, flex: 1, borderRadius: 99, background: `${COLORS.pureWhite}22`, overflow: 'hidden'}}>
          <div style={{height: '100%', width: `${progress * 100}%`, background: accent}} />
        </div>
        <span style={{opacity: 0.68}}>{scene.timecode}</span>
        {footerNote ? <span style={{color: accent}}>{footerNote}</span> : null}
      </div>
    </AbsoluteFill>
  );
};
