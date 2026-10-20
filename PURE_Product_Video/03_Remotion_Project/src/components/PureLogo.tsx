import React from 'react';
import {Img, staticFile} from 'remotion';

type Props = {
  compact?: boolean;
  hero?: boolean;
};

export const PureLogo: React.FC<Props> = ({compact = false, hero = false}) => {
  const width = hero ? 214 : compact ? 58 : 112;
  const height = hero ? 185 : compact ? 50 : 97;

  return (
    <div
      style={{
        width,
        height,
        display: 'grid',
        placeItems: 'center',
        padding: compact ? 6 : 0,
        borderRadius: compact ? 16 : 0,
        background: compact ? 'rgba(246,248,247,0.94)' : 'transparent',
        border: compact ? '1px solid rgba(53,196,181,0.30)' : 'none',
        boxShadow: compact ? '0 10px 28px rgba(0,0,0,0.20)' : 'none',
      }}
    >
      <Img
        src={staticFile('brand/brand_pure-logo-symbol_approved_v1.svg')}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          filter: hero ? 'drop-shadow(0 15px 25px rgba(53,196,181,0.26))' : 'none',
        }}
      />
    </div>
  );
};
