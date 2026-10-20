import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {COLORS} from '../theme';

type Node = {
  title: string;
  detail: string;
};

type Props = {
  nodes?: readonly Node[];
  activeIndex?: number;
};

const DEFAULT_NODES: readonly Node[] = [
  {title: 'Sensing', detail: 'MAX30102 + MPU6050'},
  {title: 'Edge device', detail: 'ESP32-C3'},
  {title: 'Signal pipeline', detail: 'Preprocess + context'},
  {title: 'AI exploration', detail: 'Candidate approach'},
  {title: 'Dashboard', detail: 'Quality support UI'},
];

export const ArchitectureFlow: React.FC<Props> = ({nodes = DEFAULT_NODES, activeIndex}) => {
  const frame = useCurrentFrame();

  return (
    <div style={{display: 'flex', alignItems: 'center', width: '100%', gap: 13}}>
      {nodes.map((node, index) => {
        const autoActive = Math.min(nodes.length - 1, Math.floor(frame / 38));
        const active = index <= (activeIndex ?? autoActive);
        return (
          <React.Fragment key={node.title}>
            <div
              style={{
                flex: 1,
                minHeight: 155,
                padding: '24px 20px',
                borderRadius: 20,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                background: active ? `${COLORS.clinicalTeal}3d` : COLORS.deepSlate,
                border: `1px solid ${active ? COLORS.signalMint : COLORS.pureWhite}3a`,
                boxShadow: active ? `0 14px 45px ${COLORS.signalMint}12` : 'none',
              }}
            >
              <div style={{fontSize: 18, fontWeight: 800, color: active ? COLORS.signalMint : COLORS.coolIvory}}>{node.title}</div>
              <div style={{fontSize: 14, lineHeight: 1.35, marginTop: 8, color: COLORS.coolIvory, opacity: 0.63}}>{node.detail}</div>
            </div>
            {index < nodes.length - 1 ? (
              <div style={{width: 42, position: 'relative', height: 2, background: `${COLORS.pureWhite}22`}}>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    transformOrigin: 'left',
                    transform: `scaleX(${interpolate(frame - index * 38, [0, 22], [0, 1], {
                      extrapolateLeft: 'clamp',
                      extrapolateRight: 'clamp',
                    })})`,
                    background: COLORS.signalMint,
                  }}
                />
                <div style={{position: 'absolute', right: -2, top: -6, color: COLORS.signalMint, fontSize: 14}}>›</div>
              </div>
            ) : null}
          </React.Fragment>
        );
      })}
    </div>
  );
};
