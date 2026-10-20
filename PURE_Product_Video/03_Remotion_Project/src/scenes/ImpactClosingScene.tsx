import React from 'react';
import {Img, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS, TYPE} from '../theme';
import {SceneContainer} from '../components/SceneContainer';

const outcomes = ['Visible signal quality', 'Clearer retry guidance', 'More transparent measurement flow'];

export const ImpactClosingScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const logo = spring({frame: frame - 25, fps, config: {damping: 15, stiffness: 90}});

  return (
    <SceneContainer scene={scene} footerNote="PURE • QUALITY BEFORE THE NUMBER">
      <div style={{height: '100%', display: 'grid', gridTemplateColumns: '1.18fr 0.82fr', gap: 90, alignItems: 'center'}}>
        <div>
          <div style={{...TYPE.label, color: COLORS.signalMint, letterSpacing: 3}}>INTENDED IMPACT</div>
          <div style={{...TYPE.display, marginTop: 22, maxWidth: 980}}>Help people understand when a measurement needs another look.</div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 13, marginTop: 42}}>
            {outcomes.map((outcome, index) => {
              const reveal = spring({frame: frame - 54 - index * 14, fps, config: {damping: 18, stiffness: 110}});
              return (
                <div key={outcome} style={{display: 'flex', alignItems: 'center', gap: 16, opacity: reveal, transform: `translateX(${(1 - reveal) * 24}px)`}}>
                  <div style={{width: 30, height: 30, borderRadius: '50%', display: 'grid', placeItems: 'center', color: COLORS.midnightNavy, background: COLORS.signalMint, fontWeight: 800}}>✓</div>
                  <div style={{fontSize: 24, fontWeight: 600}}>{outcome}</div>
                </div>
              );
            })}
          </div>
          <div style={{marginTop: 48, padding: '18px 22px', borderRadius: 16, border: `1px solid ${COLORS.pureWhite}22`, color: COLORS.coolIvory, opacity: 0.68, fontSize: 17, lineHeight: 1.5}}>
            PURE is a measurement-quality support system. It is not a medical diagnostic tool.
          </div>
        </div>
        <div style={{position: 'relative', height: 540, display: 'grid', placeItems: 'center'}}>
          <div style={{position: 'absolute', width: 500, height: 500, borderRadius: '50%', background: `radial-gradient(circle, ${COLORS.signalMint}35 0%, transparent 68%)`, transform: `scale(${logo})`}} />
          <Img src={staticFile('hardware/hardware_pure-prototype-front_approved_v1.png')} style={{position: 'absolute', width: 510, height: 510, objectFit: 'contain', transform: `scale(${logo})`}} />
          <div style={{position: 'absolute', bottom: 62, padding: '12px 18px', borderRadius: 999, textAlign: 'center', background: `${COLORS.midnightNavy}e8`, border: `1px solid ${COLORS.signalMint}66`, transform: `scale(${logo})`}}>
            <div style={{fontSize: 30, fontWeight: 800, letterSpacing: -1}}>PURE</div>
            <div style={{fontSize: 11, fontWeight: 700, letterSpacing: 2, color: COLORS.signalMint, marginTop: 4}}>QUALITY BEFORE THE NUMBER</div>
          </div>
        </div>
      </div>
    </SceneContainer>
  );
};
