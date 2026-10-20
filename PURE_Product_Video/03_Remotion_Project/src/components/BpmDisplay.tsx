import React from 'react';
import {COLORS} from '../theme';

type Props = {
  available: boolean;
};

export const BpmDisplay: React.FC<Props> = ({available}) => {
  return (
    <div
      style={{
        minHeight: 180,
        padding: '28px 32px',
        borderRadius: 24,
        background: available ? `${COLORS.clinicalTeal}2f` : `${COLORS.pureWhite}0b`,
        border: `1px solid ${available ? COLORS.signalMint : COLORS.pureWhite}33`,
      }}
    >
      <div style={{color: COLORS.coolIvory, opacity: 0.56, fontSize: 14, fontWeight: 800, letterSpacing: 1.5}}>HEART RATE</div>
      <div style={{display: 'flex', alignItems: 'baseline', gap: 15, marginTop: 18}}>
        <span style={{fontSize: available ? 42 : 68, fontWeight: 800, color: available ? COLORS.signalMint : COLORS.coolIvory}}>
          {available ? 'AVAILABLE' : '— —'}
        </span>
        {available ? <span style={{fontSize: 18, fontWeight: 700, color: COLORS.coolIvory}}>after quality check</span> : null}
      </div>
      <div style={{marginTop: 12, color: COLORS.coolIvory, opacity: 0.62, fontSize: 16}}>
        {available ? 'BPM shown after the signal-quality check' : 'BPM withheld until signal quality is sufficient'}
      </div>
    </div>
  );
};
