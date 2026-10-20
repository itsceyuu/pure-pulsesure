import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {PpgWaveform} from '../components/PpgWaveform';
import {ReliabilityBadge, type ReliabilityStatus} from '../components/ReliabilityBadge';
import {SceneContainer} from '../components/SceneContainer';

type DemoState = {
  title: string;
  status: ReliabilityStatus;
  image: string;
  guidance: string;
  behavior: string;
  accent: string;
  sampleRange: readonly [number, number] | null;
  waveformMode: 'clean' | 'motion' | 'heavy';
};

const states: readonly DemoState[] = [
  {
    title: 'Not Assessed',
    status: 'not_assessed',
    image: 'dashboard/dashboard_not-assessed_approved_v1.png',
    guidance: 'Hold still while signal conditions are assessed.',
    behavior: 'BPM pending',
    accent: '#9BA8B4',
    sampleRange: null,
    waveformMode: 'clean',
  },
  {
    title: 'Reliable',
    status: 'reliable',
    image: 'dashboard/dashboard_reliable_approved_v1.png',
    guidance: 'Signal appears stable for the monitoring interface.',
    behavior: 'BPM shown',
    accent: COLORS.signalMint,
    sampleRange: [0, 75],
    waveformMode: 'clean',
  },
  {
    title: 'Caution',
    status: 'caution',
    image: 'dashboard/dashboard_caution_approved_v1.png',
    guidance: 'Check sensor position and reduce movement.',
    behavior: 'Guidance shown',
    accent: '#F1C75B',
    sampleRange: [75, 150],
    waveformMode: 'motion',
  },
  {
    title: 'Unreliable',
    status: 'unreliable',
    image: 'dashboard/dashboard_unreliable_approved_v1.png',
    guidance: 'Reposition the sensor and retry the measurement.',
    behavior: 'BPM withheld',
    accent: '#F27A7A',
    sampleRange: [150, 225],
    waveformMode: 'heavy',
  },
  {
    title: 'Recovery',
    status: 'reliable',
    image: 'dashboard/dashboard_reliable_approved_v1.png',
    guidance: 'Signal stable after corrective action.',
    behavior: 'Returns to reliable',
    accent: COLORS.signalMint,
    sampleRange: [225, 300],
    waveformMode: 'motion',
  },
] as const;

export const DashboardDemoScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const index = Math.min(states.length - 1, Math.floor(frame / 90));
  const state = states[index];
  const localFrame = frame - index * 90;
  const fade = interpolate(localFrame, [0, 10, 78, 89], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <SceneContainer scene={scene} footerNote="DASHBOARD MONITORING">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'end', marginBottom: 20}}>
          <div>
            <div style={{fontSize: 16, fontWeight: 800, color: COLORS.signalMint, letterSpacing: 2.4}}>DASHBOARD DEMO • {index + 1}/5</div>
            <div style={{fontSize: 43, fontWeight: 700, marginTop: 8}}>Measurement quality at a glance</div>
          </div>
          <ReliabilityBadge status={state.status} />
        </div>
        <div
          style={{
            position: 'relative',
            height: 680,
            borderRadius: 28,
            overflow: 'hidden',
            background: '#E9F3F2',
            border: `2px solid ${state.accent}88`,
            boxShadow: '0 30px 80px rgba(0,0,0,0.28)',
            opacity: fade,
          }}
        >
          <Img src={staticFile(state.image)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top center'}} />
          <div style={{position: 'absolute', inset: 0, boxShadow: 'inset 0 -190px 110px rgba(11,23,38,0.76)'}} />
          <div style={{position: 'absolute', left: 30, bottom: 26, width: 290}}>
            <div style={{fontSize: 27, fontWeight: 800, color: state.accent}}>{state.title}</div>
            <div style={{fontSize: 14, lineHeight: 1.35, fontWeight: 600, marginTop: 7, color: COLORS.coolIvory, opacity: 0.82}}>{state.guidance}</div>
          </div>
          <div style={{position: 'absolute', left: 340, right: 390, bottom: 18}}>
            {state.sampleRange ? (
              <PpgWaveform
                height={146}
                mode={state.waveformMode}
                showArtifact={state.status === 'caution' || state.status === 'unreliable'}
                label={`COMBINED SEQUENCE • ${state.title.toUpperCase()}`}
                dataFile="ppg/ppg_demo-sequence-synthetic_approved_v1.json"
                sampleRange={state.sampleRange}
              />
            ) : (
              <div style={{height: 144, borderRadius: 22, display: 'grid', placeItems: 'center', border: `1px dashed ${COLORS.pureWhite}44`, background: `${COLORS.midnightNavy}d8`, color: COLORS.coolIvory, fontSize: 16, fontWeight: 700, opacity: 0.8}}>
                Signal preview available after assessment
              </div>
            )}
          </div>
          <div style={{position: 'absolute', right: 30, bottom: 68, padding: '11px 15px', borderRadius: 12, background: `${state.accent}22`, border: `1px solid ${state.accent}77`, color: state.accent, fontSize: 15, fontWeight: 800}}>
              {state.behavior}
          </div>
          <div style={{position: 'absolute', right: 24, top: 22, padding: '8px 12px', borderRadius: 9, background: `${COLORS.midnightNavy}e8`, color: COLORS.signalMint, fontSize: 12, fontWeight: 800}}>
            SIMULATED DATA
          </div>
        </div>
      </div>
    </SceneContainer>
  );
};
