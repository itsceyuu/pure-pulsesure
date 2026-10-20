import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS} from '../theme';
import type {ReliabilityStatus} from './ReliabilityBadge';

const POSITIONS: Record<ReliabilityStatus, number> = {
  not_assessed: 0.12,
  unreliable: 0.24,
  caution: 0.56,
  reliable: 0.86,
};

export const QualityGauge: React.FC<{status: ReliabilityStatus}> = ({status}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const animated = spring({frame, fps, from: 0, to: POSITIONS[status], config: {damping: 16, stiffness: 90}});
  const degrees = interpolate(animated, [0, 1], [-110, 110]);

  return (
    <div style={{width: 330, textAlign: 'center'}}>
      <div style={{position: 'relative', height: 178, overflow: 'hidden'}}>
        <div
          style={{
            position: 'absolute',
            width: 300,
            height: 300,
            left: 15,
            top: 18,
            borderRadius: '50%',
            border: `28px solid ${COLORS.pureWhite}12`,
            borderBottomColor: `${COLORS.signalMint}66`,
            borderLeftColor: '#F27A7A66',
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: 126,
            height: 5,
            background: COLORS.pureWhite,
            borderRadius: 99,
            left: 165,
            bottom: 17,
            transformOrigin: '0% 50%',
            transform: `rotate(${degrees - 90}deg)`,
          }}
        />
        <div style={{position: 'absolute', left: 153, bottom: 3, width: 24, height: 24, borderRadius: '50%', background: COLORS.signalMint}} />
      </div>
      <div style={{marginTop: 12, color: COLORS.coolIvory, fontSize: 15, fontWeight: 800, letterSpacing: 1.8}}>SIGNAL QUALITY</div>
      <div style={{marginTop: 7, color: COLORS.coolIvory, opacity: 0.56, fontSize: 13}}>Real-time reliability state</div>
    </div>
  );
};
