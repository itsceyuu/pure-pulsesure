import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {CorrectiveGuidance} from '../components/CorrectiveGuidance';
import {QualityGauge} from '../components/QualityGauge';
import {ReliabilityBadge} from '../components/ReliabilityBadge';
import {SceneContainer} from '../components/SceneContainer';
import {SceneTitle} from '../components/SceneTitle';

export const ProposedSolutionScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const phase = Math.min(2, Math.floor(frame / 108));
  const statuses = ['not_assessed', 'caution', 'reliable'] as const;
  const status = statuses[phase];
  const progress = interpolate(frame % 108, [0, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <SceneContainer scene={scene} footerNote="PURE SYSTEM">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <SceneTitle
          eyebrow="PURE solution"
          title="PURE makes measurement quality visible."
          subtitle="A support layer that assesses signal conditions, communicates reliability, and guides the next action."
        />
        <div style={{display: 'grid', gridTemplateColumns: '0.72fr 1.28fr', gap: 46, marginTop: 42}}>
          <div style={{display: 'grid', gridTemplateRows: '200px 1fr', placeItems: 'center', padding: 22, borderRadius: 28, background: COLORS.deepSlate, border: `1px solid ${COLORS.pureWhite}22`}}>
            <Img src={staticFile('hardware/hardware_pure-prototype-front_approved_v1.png')} style={{width: '100%', height: 190, objectFit: 'contain'}} />
            <QualityGauge status={status} />
          </div>
          <div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 18, opacity: progress}}>
              <ReliabilityBadge status={status} />
              <span style={{fontSize: 20, color: COLORS.coolIvory, opacity: 0.66}}>Live signal-quality state</span>
            </div>
            <CorrectiveGuidance
              tone={status === 'reliable' ? 'positive' : status === 'caution' ? 'caution' : 'neutral'}
              message={
                status === 'reliable'
                  ? 'Signal condition appears suitable for the interface flow.'
                  : status === 'caution'
                    ? 'Reduce movement and keep the sensor steady.'
                    : 'Hold still while the signal is assessed.'
              }
            />
            <div style={{padding: '18px 22px', borderLeft: `4px solid ${COLORS.signalMint}`, color: COLORS.coolIvory, fontSize: 18, lineHeight: 1.5, background: `${COLORS.pureWhite}08`}}>
              PURE supports measurement quality decisions. It is not a medical diagnostic tool.
            </div>
          </div>
        </div>
      </div>
    </SceneContainer>
  );
};
