import React from 'react';
import {useCurrentFrame} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {PipelineStep} from '../components/PipelineStep';
import {SceneContainer} from '../components/SceneContainer';
import {SceneTitle} from '../components/SceneTitle';

const steps = [
  {title: 'PPG input', detail: 'Illustrative optical waveform'},
  {title: 'Preprocess', detail: 'Prepare and segment the signal'},
  {title: 'Artifact context', detail: 'Consider motion and signal cues'},
  {title: 'Model benchmark', detail: 'Compare baselines and 1D-CNN'},
  {title: 'Quality state', detail: 'Support a UI decision'},
];

export const AiApproachScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const active = Math.min(steps.length - 1, Math.floor(frame / 76));

  return (
    <SceneContainer scene={scene} footerNote="AI SIGNAL-QUALITY PIPELINE">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <SceneTitle
          eyebrow="AI approach"
          title="Benchmark models for signal-quality support."
          subtitle="PPG windows are preprocessed, evaluated, and calibrated into a reliability decision before BPM is displayed."
        />
        <div style={{display: 'flex', gap: 15, marginTop: 66, alignItems: 'stretch'}}>
          {steps.map((step, index) => (
            <React.Fragment key={step.title}>
              <PipelineStep index={index} title={step.title} detail={step.detail} active={index === active} />
              {index < steps.length - 1 ? (
                <div style={{display: 'grid', placeItems: 'center', color: index < active ? COLORS.signalMint : `${COLORS.pureWhite}44`, fontSize: 30}}>→</div>
              ) : null}
            </React.Fragment>
          ))}
        </div>
        <div
          style={{
            alignSelf: 'flex-end',
            marginTop: 34,
            padding: '14px 18px',
            borderRadius: 12,
            border: `1px solid ${COLORS.signalMint}55`,
            color: COLORS.signalMint,
            fontSize: 16,
            fontWeight: 700,
          }}
        >
          Model selection uses subject-independent validation
        </div>
      </div>
    </SceneContainer>
  );
};
