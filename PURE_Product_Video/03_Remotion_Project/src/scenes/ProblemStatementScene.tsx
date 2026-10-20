import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {BpmDisplay} from '../components/BpmDisplay';
import {PpgWaveform} from '../components/PpgWaveform';
import {SceneContainer} from '../components/SceneContainer';
import {SceneTitle} from '../components/SceneTitle';

export const ProblemStatementScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const transition = interpolate(frame, [75, 115], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <SceneContainer scene={scene} accent="#F1C75B" footerNote="THE PROBLEM">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <SceneTitle
          eyebrow="Problem statement"
          title="A clear number can hide an unclear signal."
          subtitle="Motion, sensor contact, and changing conditions can affect a wearable PPG reading."
        />
        <div style={{display: 'grid', gridTemplateColumns: '1.7fr 0.78fr', gap: 30, marginTop: 54, alignItems: 'stretch'}}>
          <div style={{position: 'relative'}}>
            <PpgWaveform
              mode={transition > 0.5 ? 'motion' : 'clean'}
              showArtifact={transition > 0.25}
              height={310}
              dataFile={transition > 0.5 ? 'ppg/ppg_mild-artifact-synthetic_approved_v1.json' : 'ppg/ppg_clean-synthetic_approved_v1.json'}
            />
            <div
              style={{
                position: 'absolute',
                right: 24,
                bottom: 20,
                padding: '10px 14px',
                borderRadius: 10,
                background: COLORS.midnightNavy,
                color: transition > 0.5 ? '#F1C75B' : COLORS.signalMint,
                fontSize: 14,
                fontWeight: 800,
                letterSpacing: 1.2,
              }}
            >
              {transition > 0.5 ? 'SIGNAL DISTURBED' : 'SIGNAL APPEARS STABLE'}
            </div>
          </div>
          <BpmDisplay available={transition < 0.35} />
        </div>
        <div style={{fontSize: 22, fontWeight: 600, color: COLORS.coolIvory, opacity: 0.7, marginTop: 28}}>
          The interface needs a way to communicate measurement confidence—before presenting a result.
        </div>
      </div>
    </SceneContainer>
  );
};
