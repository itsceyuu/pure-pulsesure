import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {COLORS} from '../theme';

type Props = {
  left?: number;
  width?: number;
  label?: string;
};

export const ArtifactOverlay: React.FC<Props> = ({left = 44, width = 24, label = 'MOTION ARTIFACT'}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(Math.sin(frame / 8), [-1, 1], [0.14, 0.26]);

  return (
    <div
      style={{
        position: 'absolute',
        left: `${left}%`,
        width: `${width}%`,
        top: 0,
        bottom: 0,
        borderLeft: `2px dashed ${COLORS.signalMint}99`,
        borderRight: `2px dashed ${COLORS.signalMint}99`,
        background: `rgba(53,196,181,${opacity})`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 14,
          padding: '7px 11px',
          borderRadius: 8,
          background: COLORS.midnightNavy,
          color: COLORS.signalMint,
          fontSize: 13,
          fontWeight: 800,
          letterSpacing: 1,
        }}
      >
        {label}
      </div>
    </div>
  );
};
