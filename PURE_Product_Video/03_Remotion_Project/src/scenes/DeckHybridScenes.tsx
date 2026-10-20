import React from 'react';
import {AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import type {TimelineScene} from '../data/timeline';
import {DeckSlide} from '../components/DeckSlide';
import {PureLogo} from '../components/PureLogo';
import {COLORS} from '../theme';

type SceneProps = {scene: TimelineScene};

type FocusFrameProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  opacity: number;
  label: string;
  accent?: string;
};

const phaseOpacity = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, start + 12, Math.max(start + 13, end - 12), end], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

const FocusFrame: React.FC<FocusFrameProps> = ({
  x,
  y,
  width,
  height,
  opacity,
  label,
  accent = COLORS.signalMint,
}) => {
  const frame = useCurrentFrame();
  const pulse = 0.82 + Math.sin(frame / 10) * 0.08;

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width,
        height,
        borderRadius: 24,
        border: `4px solid ${accent}`,
        background: `${accent}0d`,
        boxShadow: `0 0 ${42 * pulse}px ${accent}55`,
        opacity,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 18,
          top: 16,
          padding: '9px 14px',
          borderRadius: 999,
          color: '#FFFFFF',
          background: accent,
          fontSize: 16,
          fontWeight: 800,
          letterSpacing: 0.4,
          boxShadow: '0 8px 24px rgba(11,23,38,0.18)',
        }}
      >
        {label}
      </div>
    </div>
  );
};

export const DeckTeamScene: React.FC<SceneProps> = ({scene}) => (
  <DeckSlide
    slide={1}
    durationInFrames={scene.durationInFrames}
    fromScale={1}
    toScale={1.018}
    fromX={0}
    toX={-8}
    showLogo={false}
  />
);

export const DeckProblemStatementScene: React.FC<SceneProps> = ({scene}) => (
  <DeckSlide
    slide={3}
    durationInFrames={scene.durationInFrames}
    fromScale={1.01}
    toScale={1.045}
    fromX={10}
    toX={-14}
  />
);

export const DeckProblemUnderstandingScene: React.FC<SceneProps> = ({scene}) => (
  <DeckSlide
    slide={4}
    durationInFrames={scene.durationInFrames}
    fromScale={1}
    toScale={1.028}
    fromY={0}
    toY={-7}
  />
);

export const DeckSolutionScene: React.FC<SceneProps> = ({scene}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{background: '#F7FAFA'}}>
      <DeckSlide slide={5} durationInFrames={scene.durationInFrames} fromScale={1} toScale={1.018} />
      <FocusFrame
        x={58}
        y={372}
        width={372}
        height={505}
        label="1  Current challenge"
        accent="#F08B8B"
        opacity={phaseOpacity(frame, 18, 126)}
      />
      <FocusFrame
        x={548}
        y={365}
        width={842}
        height={530}
        label="2  PURE reliability layer"
        opacity={phaseOpacity(frame, 112, 248)}
      />
      <FocusFrame
        x={1478}
        y={374}
        width={376}
        height={508}
        label="3  Safer measurement workflow"
        opacity={phaseOpacity(frame, 232, 352)}
      />
    </AbsoluteFill>
  );
};

export const DeckInnovationScene: React.FC<SceneProps> = ({scene}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{background: '#F7FAFA'}}>
      <DeckSlide slide={10} durationInFrames={scene.durationInFrames} fromScale={1.005} toScale={1.025} />
      <FocusFrame
        x={24}
        y={150}
        width={930}
        height={802}
        label="Quality-to-Action innovation"
        opacity={phaseOpacity(frame, 12, 164)}
      />
      <FocusFrame
        x={968}
        y={150}
        width={925}
        height={802}
        label="Expected impact"
        opacity={phaseOpacity(frame, 146, 292)}
      />
    </AbsoluteFill>
  );
};

export const DeckAiApproachScene: React.FC<SceneProps> = ({scene}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{background: '#F7FAFA'}}>
      <DeckSlide slide={6} durationInFrames={scene.durationInFrames} fromScale={1} toScale={1.018} />

      <div
        style={{
          position: 'absolute',
          left: 998,
          top: 226,
          width: 357,
          height: 108,
          borderRadius: 18,
          display: 'grid',
          placeItems: 'center',
          textAlign: 'center',
          background: '#35C4B5',
          color: '#0B1726',
          boxShadow: '0 8px 24px rgba(11,23,38,0.16)',
        }}
      >
        <div>
          <div style={{fontSize: 24, fontWeight: 800}}>1D TIME-SERIES MODEL</div>
          <div style={{fontSize: 15, fontWeight: 600, marginTop: 6}}>Selected through benchmarking</div>
        </div>
      </div>

      <FocusFrame
        x={58}
        y={145}
        width={920}
        height={246}
        label="Input and preprocessing"
        opacity={phaseOpacity(frame, 10, 152) * 0.92}
      />
      <FocusFrame
        x={390}
        y={182}
        width={980}
        height={500}
        label="Model, calibration, and gate"
        opacity={phaseOpacity(frame, 136, 292) * 0.92}
      />
      <FocusFrame
        x={1384}
        y={175}
        width={476}
        height={552}
        label="Reliability decision"
        opacity={phaseOpacity(frame, 276, 414) * 0.92}
      />
    </AbsoluteFill>
  );
};

export const DeckPrototypeScene: React.FC<SceneProps> = ({scene}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{background: '#F7FAFA'}}>
      <DeckSlide slide={7} durationInFrames={scene.durationInFrames} fromScale={1} toScale={1.02} />
      <FocusFrame
        x={18}
        y={125}
        width={1330}
        height={510}
        label="1  End-to-end system flow"
        opacity={phaseOpacity(frame, 18, 230)}
      />
      <FocusFrame
        x={1390}
        y={126}
        width={490}
        height={520}
        label="2  Technology stack"
        opacity={phaseOpacity(frame, 214, 450)}
      />
      <FocusFrame
        x={20}
        y={682}
        width={1860}
        height={315}
        label="3  Wearable prototype plan"
        opacity={phaseOpacity(frame, 432, 652)}
      />
    </AbsoluteFill>
  );
};

const dashboardStates = [
  {
    title: 'NOT ASSESSED',
    behavior: 'BPM pending while signal quality is checked',
    image: 'dashboard/dashboard_not-assessed_approved_v1.png',
    accent: '#7C8996',
  },
  {
    title: 'RELIABLE',
    behavior: 'Signal accepted and BPM displayed',
    image: 'dashboard/dashboard_reliable_approved_v1.png',
    accent: COLORS.clinicalTeal,
  },
  {
    title: 'CAUTION',
    behavior: 'Check placement and reduce movement',
    image: 'dashboard/dashboard_caution_approved_v1.png',
    accent: '#D79D21',
  },
  {
    title: 'UNRELIABLE',
    behavior: 'BPM withheld and remeasurement requested',
    image: 'dashboard/dashboard_unreliable_approved_v1.png',
    accent: '#D85D62',
  },
  {
    title: 'RECOVERY',
    behavior: 'Signal stabilizes and BPM returns',
    image: 'dashboard/dashboard_reliable_approved_v1.png',
    accent: COLORS.clinicalTeal,
  },
] as const;

const DashboardStateDemo: React.FC<{durationInFrames: number}> = ({durationInFrames}) => {
  const frame = useCurrentFrame();
  const framesPerState = durationInFrames / dashboardStates.length;
  const index = Math.min(dashboardStates.length - 1, Math.floor(frame / framesPerState));
  const localFrame = frame - index * framesPerState;
  const state = dashboardStates[index];
  const opacity = interpolate(localFrame, [0, 8, framesPerState - 8, framesPerState], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{background: '#F7FAFA', color: '#132443', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 58, top: 45}}>
        <div style={{fontSize: 17, fontWeight: 800, letterSpacing: 2.1, color: COLORS.clinicalTeal}}>
          DASHBOARD PROTOTYPE DEMO
        </div>
        <div style={{fontSize: 47, fontWeight: 800, marginTop: 6}}>From signal quality to a clear action</div>
      </div>
      <div style={{position: 'absolute', right: 38, top: 34}}>
        <PureLogo />
      </div>

      <div style={{position: 'absolute', left: 170, top: 155, width: 1580, height: 889, opacity}}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 28,
            overflow: 'hidden',
            background: '#FFFFFF',
            border: `4px solid ${state.accent}`,
            boxShadow: '0 28px 70px rgba(11,23,38,0.19)',
          }}
        >
          <Img src={staticFile(state.image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
          <div
            style={{
              position: 'absolute',
              left: 26,
              bottom: 24,
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: '15px 20px',
              borderRadius: 16,
              background: 'rgba(255,255,255,0.94)',
              borderLeft: `8px solid ${state.accent}`,
              boxShadow: '0 10px 30px rgba(11,23,38,0.18)',
            }}
          >
            <div style={{fontSize: 21, fontWeight: 800, color: state.accent}}>{state.title}</div>
            <div style={{fontSize: 17, fontWeight: 600, color: '#263951'}}>{state.behavior}</div>
          </div>
          <div
            style={{
              position: 'absolute',
              right: 24,
              bottom: 24,
              padding: '10px 14px',
              borderRadius: 12,
              background: '#0B1726',
              color: '#6EF0D7',
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            SIMULATED PROTOTYPE DATA
          </div>
        </div>
      </div>

      <div style={{position: 'absolute', left: 690, top: 125, display: 'flex', gap: 10}}>
        {dashboardStates.map((item, itemIndex) => (
          <div
            key={item.title}
            style={{
              width: itemIndex === index ? 56 : 18,
              height: 7,
              borderRadius: 99,
              background: itemIndex === index ? state.accent : '#D5E0E3',
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const DeckDashboardScene: React.FC<SceneProps> = ({scene}) => {
  const deckFrames = 120;
  const demoStart = 104;
  const demoFrames = scene.durationInFrames - demoStart;

  return (
    <AbsoluteFill style={{background: '#F7FAFA'}}>
      <Sequence from={0} durationInFrames={deckFrames}>
        <DeckSlide slide={9} durationInFrames={deckFrames} fromScale={1} toScale={1.025} showLogo={false} />
      </Sequence>
      <Sequence from={demoStart} durationInFrames={demoFrames}>
        <DashboardStateDemo durationInFrames={demoFrames} />
      </Sequence>
    </AbsoluteFill>
  );
};

export const DeckImpactClosingScene: React.FC<SceneProps> = ({scene}) => {
  const impactFrames = 156;
  const closingStart = 138;
  const closingFrames = scene.durationInFrames - closingStart;

  return (
    <AbsoluteFill style={{background: '#F7FAFA'}}>
      <Sequence from={0} durationInFrames={impactFrames}>
        <DeckSlide
          slide={10}
          durationInFrames={impactFrames}
          fromScale={1.02}
          toScale={1.065}
          fromX={-12}
          toX={-54}
        />
      </Sequence>
      <Sequence from={closingStart} durationInFrames={closingFrames}>
        <DeckSlide slide={11} durationInFrames={closingFrames} fromScale={1} toScale={1.02} showLogo={false} />
      </Sequence>
    </AbsoluteFill>
  );
};
