import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS} from '../theme';

type Props = {
  index: number;
  title: string;
  detail: string;
  active?: boolean;
};

export const PipelineStep: React.FC<Props> = ({index, title, detail, active = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame: frame - index * 9, fps, config: {damping: 18, stiffness: 120}});
  const opacity = interpolate(reveal, [0, 1], [0, 1]);

  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        padding: '24px 22px',
        borderRadius: 22,
        background: active ? `${COLORS.clinicalTeal}35` : COLORS.deepSlate,
        border: `1px solid ${active ? COLORS.signalMint : COLORS.pureWhite}2c`,
        transform: `translateY(${(1 - reveal) * 22}px)`,
        opacity,
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 12,
          display: 'grid',
          placeItems: 'center',
          background: active ? COLORS.signalMint : `${COLORS.pureWhite}12`,
          color: active ? COLORS.midnightNavy : COLORS.coolIvory,
          fontWeight: 800,
        }}
      >
        {String(index + 1).padStart(2, '0')}
      </div>
      <div style={{fontSize: 22, fontWeight: 700, marginTop: 22}}>{title}</div>
      <div style={{fontSize: 16, lineHeight: 1.45, color: COLORS.coolIvory, opacity: 0.64, marginTop: 10}}>{detail}</div>
    </div>
  );
};
