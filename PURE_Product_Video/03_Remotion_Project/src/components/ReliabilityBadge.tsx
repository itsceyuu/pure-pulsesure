import React from 'react';
import {COLORS} from '../theme';

export type ReliabilityStatus = 'not_assessed' | 'reliable' | 'caution' | 'unreliable';

const CONFIG: Record<ReliabilityStatus, {label: string; color: string; symbol: string}> = {
  not_assessed: {label: 'NOT ASSESSED', color: '#9BA8B4', symbol: '○'},
  reliable: {label: 'RELIABLE', color: COLORS.signalMint, symbol: '✓'},
  caution: {label: 'CAUTION', color: '#F1C75B', symbol: '!'},
  unreliable: {label: 'UNRELIABLE', color: '#F27A7A', symbol: '×'},
};

type Props = {
  status: ReliabilityStatus;
  compact?: boolean;
};

export const ReliabilityBadge: React.FC<Props> = ({status, compact = false}) => {
  const config = CONFIG[status];
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: compact ? 9 : 13,
        padding: compact ? '9px 13px' : '14px 18px',
        borderRadius: 999,
        color: config.color,
        background: `${config.color}18`,
        border: `1px solid ${config.color}66`,
        fontSize: compact ? 14 : 18,
        fontWeight: 800,
        letterSpacing: 1.2,
      }}
    >
      <span style={{fontSize: compact ? 18 : 24, lineHeight: 1}}>{config.symbol}</span>
      {config.label}
    </div>
  );
};
