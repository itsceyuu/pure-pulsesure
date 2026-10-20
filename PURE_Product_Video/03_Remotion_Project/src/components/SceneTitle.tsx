import React from 'react';
import {COLORS, TYPE} from '../theme';

type Props = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  width?: number | string;
  center?: boolean;
};

export const SceneTitle: React.FC<Props> = ({eyebrow, title, subtitle, width = 1120, center = false}) => {
  return (
    <div style={{width, textAlign: center ? 'center' : 'left', margin: center ? '0 auto' : 0}}>
      {eyebrow ? (
        <div style={{...TYPE.label, color: COLORS.signalMint, letterSpacing: 3, marginBottom: 18}}>{eyebrow.toUpperCase()}</div>
      ) : null}
      <div style={{...TYPE.h1, color: COLORS.pureWhite, letterSpacing: -1.8}}>{title}</div>
      {subtitle ? (
        <div style={{...TYPE.body, color: COLORS.coolIvory, opacity: 0.76, marginTop: 22, maxWidth: 1080}}>{subtitle}</div>
      ) : null}
    </div>
  );
};
