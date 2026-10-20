import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {ReliabilityBadge} from '../components/ReliabilityBadge';
import {SceneContainer} from '../components/SceneContainer';
import {SceneTitle} from '../components/SceneTitle';

const principles = [
  {number: '01', title: 'Assess first', detail: 'Evaluate signal conditions before the interface presents a result.'},
  {number: '02', title: 'Communicate uncertainty', detail: 'Use clear qualitative states instead of implying certainty.'},
  {number: '03', title: 'Guide recovery', detail: 'Pair caution with a simple action the user can take.'},
];

export const InnovationScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <SceneContainer scene={scene} footerNote="QUALITY-FIRST EXPERIENCE">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <SceneTitle
          eyebrow="Innovation"
          title="Move from number-first to quality-first."
          subtitle="The innovation is the decision flow around the measurement—not a claim of clinical diagnosis."
        />
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, marginTop: 58}}>
          {principles.map((item, index) => {
            const reveal = spring({frame: frame - 24 - index * 13, fps, config: {damping: 16, stiffness: 100}});
            return (
              <div
                key={item.number}
                style={{
                  minHeight: 270,
                  padding: 30,
                  borderRadius: 26,
                  background: index === 1 ? `${COLORS.clinicalTeal}35` : COLORS.deepSlate,
                  border: `1px solid ${index === 1 ? COLORS.signalMint : COLORS.pureWhite}2e`,
                  opacity: reveal,
                  transform: `translateY(${(1 - reveal) * 34}px)`,
                }}
              >
                <div style={{fontSize: 18, fontWeight: 800, color: COLORS.signalMint}}>{item.number}</div>
                <div style={{fontSize: 30, fontWeight: 700, marginTop: 36}}>{item.title}</div>
                <div style={{fontSize: 19, lineHeight: 1.5, color: COLORS.coolIvory, opacity: 0.67, marginTop: 14}}>{item.detail}</div>
                <div style={{marginTop: 26}}>
                  <ReliabilityBadge status={index === 0 ? 'not_assessed' : index === 1 ? 'caution' : 'reliable'} compact />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </SceneContainer>
  );
};
