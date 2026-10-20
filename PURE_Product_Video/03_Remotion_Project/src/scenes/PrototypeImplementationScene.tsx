import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {COLORS} from '../theme';
import {PpgWaveform} from '../components/PpgWaveform';
import {SceneContainer} from '../components/SceneContainer';
import {SceneTitle} from '../components/SceneTitle';

const phases = [
  {title: 'Wearable sensing', detail: 'Optical pulse sensing with motion context', range: [0, 220]},
  {title: 'Backend processing', detail: 'Signal preparation, inference, and reliability gating', range: [220, 440]},
  {title: 'Monitoring interface', detail: 'Reliability status and corrective guidance', range: [440, 660]},
] as const;

const hardware = [
  {name: 'MAX30102', file: 'hardware/hardware_max30102-render_approved_v1.png'},
  {name: 'MPU6050', file: 'hardware/hardware_mpu6050-render_approved_v1.png'},
  {name: 'ESP32-C3', file: 'hardware/hardware_esp32-c3-render_approved_v1.png'},
] as const;

export const PrototypeImplementationScene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const phase = Math.min(2, Math.floor(frame / 220));
  const local = frame - phase * 220;

  return (
    <SceneContainer scene={scene} footerNote="PROTOTYPE IMPLEMENTATION">
      <div style={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <div style={{opacity: phase === 1 ? 0 : 1}}>
          <SceneTitle
            eyebrow="Prototype Implementation"
            title={phases[phase].title}
            subtitle={phases[phase].detail}
          />
          <div style={{display: 'flex', gap: 12, marginTop: 36}}>
            {phases.map((item, index) => (
              <div key={item.title} style={{height: 5, flex: 1, borderRadius: 999, background: index <= phase ? COLORS.signalMint : `${COLORS.pureWhite}1b`}} />
            ))}
          </div>
        </div>
        <div style={{marginTop: 46}}>
          {phase === 0 ? (
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 30, alignItems: 'stretch'}}>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, padding: 22, borderRadius: 28, background: COLORS.deepSlate, border: `1px solid ${COLORS.pureWhite}25`}}>
                {hardware.map((item) => (
                  <div key={item.name} style={{display: 'grid', gridTemplateRows: '1fr auto', minWidth: 0, borderRadius: 18, background: `${COLORS.pureWhite}08`, overflow: 'hidden'}}>
                    <Img src={staticFile(item.file)} style={{width: '100%', height: 210, objectFit: 'contain'}} />
                    <div style={{padding: '11px 8px 15px', textAlign: 'center', fontSize: 15, color: COLORS.coolIvory, fontWeight: 700}}>{item.name}</div>
                  </div>
                ))}
              </div>
              <PpgWaveform
                mode={local > 110 ? 'motion' : 'clean'}
                showArtifact={local > 110}
                height={350}
                label="SYNTHETIC SENSOR STREAM"
                dataFile={local > 110 ? 'ppg/ppg_mild-artifact-synthetic_approved_v1.json' : 'ppg/ppg_clean-synthetic_approved_v1.json'}
              />
            </div>
          ) : null}
          {phase === 1 ? (
            <div style={{position: 'absolute', inset: '18px 54px 18px', padding: 14, borderRadius: 28, overflow: 'hidden', background: COLORS.deepSlate, border: `1px solid ${COLORS.pureWhite}25`, display: 'grid', placeItems: 'center', zIndex: 5}}>
              <Img src={staticFile('architecture/architecture_system-diagram_approved_v1.png')} style={{width: '100%', height: '100%', objectFit: 'contain', borderRadius: 16}} />
              <div style={{position: 'absolute', left: 30, top: 28, padding: '10px 14px', borderRadius: 10, background: `${COLORS.midnightNavy}e8`, color: COLORS.signalMint, fontSize: 14, fontWeight: 800, letterSpacing: 1}}>
                PURE SYSTEM ARCHITECTURE
              </div>
            </div>
          ) : null}
          {phase === 2 ? (
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24}}>
              {[
                ['01', 'Assess', 'Check signal conditions before showing a result.'],
                ['02', 'Communicate', 'Use a visible qualitative reliability state.'],
                ['03', 'Guide', 'Offer a simple next step when a retry is needed.'],
              ].map(([number, title, detail], index) => {
                const reveal = interpolate(local, [18 + index * 24, 54 + index * 24], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
                return (
                  <div key={number} style={{minHeight: 300, padding: 34, borderRadius: 28, background: index === 1 ? `${COLORS.clinicalTeal}32` : COLORS.deepSlate, border: `1px solid ${index === 1 ? COLORS.signalMint : COLORS.pureWhite}2d`, opacity: reveal}}>
                    <div style={{color: COLORS.signalMint, fontWeight: 800, fontSize: 18}}>{number}</div>
                    <div style={{fontSize: 34, fontWeight: 700, marginTop: 42}}>{title}</div>
                    <div style={{fontSize: 20, lineHeight: 1.5, color: COLORS.coolIvory, opacity: 0.67, marginTop: 18}}>{detail}</div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
    </SceneContainer>
  );
};
