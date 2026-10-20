import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS, TYPE} from '../theme';
import {PureLogo} from '../components/PureLogo';
import {SceneContainer} from '../components/SceneContainer';

export const TeamIntroductionScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const mark = spring({frame: frame - 6, fps, config: {damping: 15, stiffness: 95}});
  const title = spring({frame: frame - 16, fps, config: {damping: 17, stiffness: 100}});
  const roles = ['Sensing', 'Signal Quality', 'AI Pipeline', 'Product Design'];

  return (
    <SceneContainer scene={scene} footerNote="TEAM PURE">
      <div style={{height: '100%', display: 'grid', gridTemplateColumns: '0.74fr 1.26fr', alignItems: 'center', gap: 110}}>
        <div style={{position: 'relative', height: 520, display: 'grid', placeItems: 'center'}}>
          {[1, 0.74, 0.48].map((scale, index) => (
            <div
              key={scale}
              style={{
                position: 'absolute',
                width: 430,
                height: 430,
                borderRadius: '50%',
                border: `${index === 2 ? 16 : 3}px solid ${index === 2 ? COLORS.signalMint : COLORS.signalMint}55`,
                transform: `scale(${scale * mark}) rotate(${frame * (index % 2 ? -0.18 : 0.12)}deg)`,
                borderTopColor: index === 2 ? COLORS.signalMint : 'transparent',
              }}
            />
          ))}
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${mark})`}}>
            <PureLogo hero />
            <div style={{fontSize: 52, fontWeight: 800, letterSpacing: -2, color: COLORS.pureWhite, marginTop: -16}}>PURE</div>
          </div>
        </div>
        <div style={{transform: `translateX(${(1 - title) * 42}px)`, opacity: title}}>
          <div style={{...TYPE.label, color: COLORS.signalMint, letterSpacing: 3}}>MEET THE TEAM</div>
          <div style={{...TYPE.display, marginTop: 18}}>Quality before the number.</div>
          <div style={{...TYPE.body, color: COLORS.coolIvory, opacity: 0.72, marginTop: 28, maxWidth: 820}}>
            A measurement-quality support system for wearable PPG monitoring.
          </div>
          <div style={{display: 'flex', flexWrap: 'wrap', gap: 13, marginTop: 46}}>
            {roles.map((role, index) => {
              const opacity = interpolate(frame, [38 + index * 7, 52 + index * 7], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
              return (
                <div
                  key={role}
                  style={{
                    padding: '13px 18px',
                    borderRadius: 999,
                    background: `${COLORS.pureWhite}0d`,
                    border: `1px solid ${COLORS.pureWhite}24`,
                    fontSize: 16,
                    fontWeight: 600,
                    opacity,
                  }}
                >
                  {role}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </SceneContainer>
  );
};
