import React from 'react';
import {COLORS} from '../theme';

type Props = {
  message: string;
  tone?: 'neutral' | 'caution' | 'positive';
};

const TONES = {
  neutral: '#9BA8B4',
  caution: '#F1C75B',
  positive: COLORS.signalMint,
} as const;

export const CorrectiveGuidance: React.FC<Props> = ({message, tone = 'neutral'}) => {
  const color = TONES[tone];
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        padding: '20px 24px',
        borderRadius: 18,
        background: `${color}12`,
        border: `1px solid ${color}44`,
        color: COLORS.coolIvory,
      }}
    >
      <div
        style={{
          width: 42,
          height: 42,
          display: 'grid',
          placeItems: 'center',
          borderRadius: 13,
          background: `${color}28`,
          color,
          fontSize: 22,
          fontWeight: 800,
        }}
      >
        →
      </div>
      <div>
        <div style={{fontSize: 13, color, fontWeight: 800, letterSpacing: 1.5}}>CORRECTIVE GUIDANCE</div>
        <div style={{fontSize: 20, fontWeight: 600, marginTop: 5}}>{message}</div>
      </div>
    </div>
  );
};
