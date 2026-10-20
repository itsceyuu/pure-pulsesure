import React, {useEffect, useMemo, useState} from 'react';
import {continueRender, delayRender, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {COLORS} from '../theme';
import {ArtifactOverlay} from './ArtifactOverlay';

type Props = {
  mode?: 'clean' | 'motion' | 'heavy';
  height?: number;
  showArtifact?: boolean;
  label?: string;
  dataFile?: string;
  sampleRange?: readonly [number, number];
};

type SyntheticSample = {
  ppg: number;
};

type SyntheticDataset = {
  metadata: {
    synthetic: true;
    intended_use: string;
    not_medically_validated: true;
  };
  samples: SyntheticSample[];
};

const makePath = (mode: NonNullable<Props['mode']>, width: number, height: number) => {
  const points = Array.from({length: 180}, (_, index) => {
    const x = (index / 179) * width;
    const phase = index / 7.2;
    const pulse = Math.pow(Math.max(0, Math.sin(phase)), 8) * 56;
    const notch = Math.pow(Math.max(0, Math.sin(phase - 0.85)), 12) * 18;
    const baseline = Math.sin(index / 18) * 4;
    const inArtifact = index > 76 && index < 124;
    const motion = inArtifact && mode !== 'clean' ? Math.sin(index * 1.65) * (mode === 'heavy' ? 46 : 24) : 0;
    const drift = inArtifact && mode === 'heavy' ? Math.sin(index / 3.1) * 18 : 0;
    const y = height / 2 + baseline - pulse + notch + motion + drift;
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  return points.join(' ');
};

const makeDataPath = (samples: SyntheticSample[], width: number, height: number) => {
  return samples.map((sample, index) => {
    const x = (index / Math.max(1, samples.length - 1)) * width;
    const y = 38 + (1 - sample.ppg) * (height - 76);
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
};

export const PpgWaveform: React.FC<Props> = ({mode = 'clean', height = 250, showArtifact = false, label = 'PPG SIGNAL', dataFile, sampleRange}) => {
  const frame = useCurrentFrame();
  const [dataset, setDataset] = useState<SyntheticDataset | null>(null);
  const [handle] = useState(() => dataFile ? delayRender(`Loading synthetic PPG: ${dataFile}`) : null);
  const width = 1200;
  const reveal = interpolate(frame, [8, 58], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const path = useMemo(
    () => {
      if (!dataset) return makePath(mode, width, height);
      const samples = sampleRange ? dataset.samples.slice(sampleRange[0], sampleRange[1]) : dataset.samples;
      return makeDataPath(samples, width, height);
    },
    [dataset, height, mode, sampleRange],
  );

  useEffect(() => {
    if (!dataFile || handle === null) return;
    fetch(staticFile(dataFile))
      .then((response) => {
        if (!response.ok) throw new Error(`Unable to load ${dataFile}`);
        return response.json() as Promise<SyntheticDataset>;
      })
      .then((loaded) => setDataset(loaded))
      .catch((error) => console.error(error))
      .finally(() => continueRender(handle));
  }, [dataFile, handle]);

  return (
    <div
      style={{
        position: 'relative',
        height,
        borderRadius: 24,
        overflow: 'hidden',
        border: `1px solid ${COLORS.pureWhite}18`,
        background: `${COLORS.deepSlate}dd`,
      }}
    >
      <div style={{position: 'absolute', left: 22, top: 18, color: COLORS.coolIvory, opacity: 0.6, fontSize: 14, fontWeight: 700}}>
        {label}
      </div>
      {dataFile ? (
        <div style={{position: 'absolute', right: 20, top: 16, zIndex: 3, padding: '7px 10px', borderRadius: 8, background: `${COLORS.midnightNavy}dd`, color: COLORS.signalMint, fontSize: 11, fontWeight: 800, letterSpacing: 0.45}}>
          SIMULATED DATA
        </div>
      ) : null}
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        {Array.from({length: 9}, (_, index) => (
          <line
            key={index}
            x1="0"
            x2={width}
            y1={(index / 8) * height}
            y2={(index / 8) * height}
            stroke={COLORS.pureWhite}
            strokeOpacity="0.06"
          />
        ))}
        <path
          d={path}
          fill="none"
          stroke={mode === 'heavy' ? COLORS.coolIvory : COLORS.signalMint}
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength="1"
          strokeDasharray="1"
          strokeDashoffset={1 - reveal}
        />
      </svg>
      {showArtifact ? <ArtifactOverlay label={mode === 'heavy' ? 'HEAVY ARTIFACT' : 'MOTION ARTIFACT'} /> : null}
    </div>
  );
};
