import React from 'react';
import {AbsoluteFill, Series} from 'remotion';
import {FONT_FAMILY} from './theme';
import {TIMELINE} from './data/timeline';
import {TeamIntroductionScene} from './scenes/TeamIntroductionScene';
import {ProblemStatementScene} from './scenes/ProblemStatementScene';
import {ProblemUnderstandingScene} from './scenes/ProblemUnderstandingScene';
import {ProposedSolutionScene} from './scenes/ProposedSolutionScene';
import {InnovationScene} from './scenes/InnovationScene';
import {AiApproachScene} from './scenes/AiApproachScene';
import {PrototypeImplementationScene} from './scenes/PrototypeImplementationScene';
import {DashboardDemoScene} from './scenes/DashboardDemoScene';
import {ImpactClosingScene} from './scenes/ImpactClosingScene';

const scenes = [
  TeamIntroductionScene,
  ProblemStatementScene,
  ProblemUnderstandingScene,
  ProposedSolutionScene,
  InnovationScene,
  AiApproachScene,
  PrototypeImplementationScene,
  DashboardDemoScene,
  ImpactClosingScene,
] as const;

export const PureExplainer: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#F7FAFA', color: '#132443', fontFamily: FONT_FAMILY}}>
      <Series>
        {TIMELINE.map((scene, index) => {
          const Scene = scenes[index];
          return (
            <Series.Sequence key={scene.key} durationInFrames={scene.durationInFrames} name={scene.title}>
              <Scene scene={scene} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
