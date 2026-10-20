import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {PpgWaveform} from '../components/PpgWaveform';
import {SceneContainer} from '../components/SceneContainer';
import {SceneTitle} from '../components/SceneTitle';

const factors = [
  {icon: '↝', title: 'Motion', detail: 'Movement may introduce artifacts into the optical waveform.'},
  {icon: '◉', title: 'Sensor contact', detail: 'Placement and contact can change the captured signal.'},
  {icon: '◎', title: 'Measurement context', detail: 'Signal conditions should be considered before a value is shown.'},
];

export const ProblemUnderstandingScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <SceneContainer scene={scene} accent="#F1C75B" footerNote="UNDERSTANDING UNCERTAINTY">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <SceneTitle
          eyebrow="Problem understanding"
          title="Signal quality is part of the measurement."
          subtitle="The experience distinguishes the signal, its measurement context, and the decision to display or withhold a result."
        />
        <div style={{display: 'grid', gridTemplateColumns: '1.05fr 0.95fr', gap: 44, marginTop: 46}}>
          <PpgWaveform
            mode="heavy"
            showArtifact
            height={360}
            label="SYNTHETIC HEAVY-ARTIFACT EXAMPLE"
            dataFile="ppg/ppg_heavy-artifact-synthetic_approved_v1.json"
          />
          <div style={{display: 'flex', flexDirection: 'column', gap: 14}}>
            {factors.map((factor, index) => {
              const reveal = spring({frame: frame - 28 - index * 14, fps, config: {damping: 18, stiffness: 100}});
              return (
                <div
                  key={factor.title}
                  style={{
                    flex: 1,
                    display: 'grid',
                    gridTemplateColumns: '66px 1fr',
                    alignItems: 'center',
                    gap: 18,
                    padding: '18px 22px',
                    background: COLORS.deepSlate,
                    border: `1px solid ${COLORS.pureWhite}22`,
                    borderRadius: 20,
                    opacity: reveal,
                    transform: `translateX(${(1 - reveal) * 26}px)`,
                  }}
                >
                  <div style={{width: 54, height: 54, borderRadius: 16, display: 'grid', placeItems: 'center', background: '#F1C75B18', color: '#F1C75B', fontSize: 28}}>
                    {factor.icon}
                  </div>
                  <div>
                    <div style={{fontSize: 21, fontWeight: 700}}>{factor.title}</div>
                    <div style={{fontSize: 15, lineHeight: 1.4, color: COLORS.coolIvory, opacity: 0.62, marginTop: 5}}>{factor.detail}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </SceneContainer>
  );
};
