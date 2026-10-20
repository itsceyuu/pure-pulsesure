import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RAW_DATA_DIR = path.resolve(HERE, '../../01_Raw_Assets/ppg/waveform_csv_json');
const RAW_PREVIEW_DIR = path.resolve(HERE, '../../01_Raw_Assets/ppg/waveform_previews');
const APPROVED_DIR = path.resolve(HERE, '../../02_Approved_Assets/ppg');
const PUBLIC_DIR = path.resolve(HERE, '../public/ppg');

const SAMPLE_RATE_HZ = 30;
const DURATION_SECONDS = 10;
const SAMPLE_COUNT = SAMPLE_RATE_HZ * DURATION_SECONDS;
const INTENDED_USE = 'visual prototype demonstration only';

for (const directory of [RAW_DATA_DIR, RAW_PREVIEW_DIR, APPROVED_DIR, PUBLIC_DIR]) {
  fs.mkdirSync(directory, {recursive: true});
}

const createRandom = (seed) => {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 4294967296;
  };
};

const gaussianish = (random) =>
  (random() + random() + random() + random() + random() + random() - 3) / 3;

const segmentForCombinedTime = (timeSeconds) => {
  if (timeSeconds < 2.5) return 'clean';
  if (timeSeconds < 5) return 'mild_artifact';
  if (timeSeconds < 7.5) return 'heavy_artifact';
  return 'recovery';
};

const statusFor = (condition, progress) => {
  if (condition === 'clean') return 'reliable';
  if (condition === 'mild_artifact') return 'caution';
  if (condition === 'heavy_artifact') return 'unreliable';
  if (condition === 'recovery') return progress < 0.55 ? 'caution' : 'reliable';
  return 'not_assessed';
};

const scoreFor = (condition, progress) => {
  if (condition === 'clean') return 92;
  if (condition === 'mild_artifact') return 65;
  if (condition === 'heavy_artifact') return 22;
  return Math.round(38 + progress * 52);
};

const sampleFor = ({condition, timeSeconds, segmentProgress, random}) => {
  const heartRateHz = 1.28;
  const phase = (timeSeconds * heartRateHz) % 1;
  const systolic = Math.exp(-Math.pow((phase - 0.17) / 0.055, 2));
  const diastolic = 0.28 * Math.exp(-Math.pow((phase - 0.43) / 0.09, 2));
  const base = 0.18 + 0.68 * systolic + 0.22 * diastolic + 0.015 * Math.sin(timeSeconds * 0.8);
  const cleanNoise = gaussianish(random) * 0.012;
  const mildWindow = Math.sin(timeSeconds * 1.9) > -0.18 ? 1 : 0;
  const mildNoise = condition === 'mild_artifact' ? mildWindow * (0.08 * Math.sin(timeSeconds * 29) + gaussianish(random) * 0.05) : 0;
  const heavySpike = condition === 'heavy_artifact' && (segmentProgress > 0.2 && segmentProgress < 0.72)
    ? 0.3 * Math.sin(timeSeconds * 34) + gaussianish(random) * 0.22
    : 0;
  const recoveryFactor = condition === 'recovery' ? Math.max(0, 1 - segmentProgress * 1.25) : 0;
  const recoveryNoise = recoveryFactor * (0.2 * Math.sin(timeSeconds * 31) + gaussianish(random) * 0.12);
  const ppg = Math.max(0, Math.min(1, base + cleanNoise + mildNoise + heavySpike + recoveryNoise));

  const motionLevel = condition === 'clean' ? 0.012
    : condition === 'mild_artifact' ? 0.12
      : condition === 'heavy_artifact' ? 0.42
        : 0.34 * (1 - segmentProgress) + 0.015;
  const spike = condition === 'heavy_artifact' && segmentProgress > 0.35 && segmentProgress < 0.48 ? 0.9 : 0;

  return {
    ppg: Number(ppg.toFixed(6)),
    acc_x_g: Number((motionLevel * Math.sin(timeSeconds * 17) + spike + gaussianish(random) * 0.008).toFixed(6)),
    acc_y_g: Number((motionLevel * 0.75 * Math.cos(timeSeconds * 13) - spike * 0.35 + gaussianish(random) * 0.008).toFixed(6)),
    acc_z_g: Number((1 + motionLevel * 0.5 * Math.sin(timeSeconds * 11) + spike * 0.25 + gaussianish(random) * 0.006).toFixed(6)),
    artifact: condition === 'clean' ? false : condition === 'recovery' ? segmentProgress < 0.55 : true,
  };
};

const makeDataset = ({condition, seed, slug}) => {
  const random = createRandom(seed);
  const samples = Array.from({length: SAMPLE_COUNT}, (_, index) => {
    const timeSeconds = index / SAMPLE_RATE_HZ;
    const resolvedCondition = condition === 'combined' ? segmentForCombinedTime(timeSeconds) : condition;
    const segmentStart = condition === 'combined'
      ? resolvedCondition === 'clean' ? 0 : resolvedCondition === 'mild_artifact' ? 2.5 : resolvedCondition === 'heavy_artifact' ? 5 : 7.5
      : 0;
    const segmentDuration = condition === 'combined' ? 2.5 : DURATION_SECONDS;
    const segmentProgress = Math.min(1, Math.max(0, (timeSeconds - segmentStart) / segmentDuration));
    const values = sampleFor({condition: resolvedCondition, timeSeconds, segmentProgress, random});
    const status = statusFor(resolvedCondition, segmentProgress);
    return {
      time_seconds: Number(timeSeconds.toFixed(6)),
      ...values,
      condition: resolvedCondition,
      status,
      demo_quality_score: scoreFor(resolvedCondition, segmentProgress),
      bpm_display: status === 'reliable' ? 'shown' : 'withheld',
    };
  });

  return {
    metadata: {
      synthetic: true,
      intended_use: INTENDED_USE,
      not_medically_validated: true,
      seed,
      sample_rate_hz: SAMPLE_RATE_HZ,
      duration_seconds: DURATION_SECONDS,
      unit: 'normalized arbitrary units',
      condition,
      lifecycle_status: 'review',
      score_note: 'demo_quality_score is an illustrative interface value, not a model or clinical performance metric',
    },
    samples,
    slug,
  };
};

const csvEscape = (value) => {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

const toCsv = (dataset) => {
  const headers = [
    'time_seconds', 'ppg', 'acc_x_g', 'acc_y_g', 'acc_z_g', 'artifact', 'condition', 'status',
    'demo_quality_score', 'bpm_display', 'synthetic', 'intended_use', 'not_medically_validated',
    'seed', 'sample_rate_hz', 'unit',
  ];
  const rows = dataset.samples.map((sample) => headers.map((header) => csvEscape(
    header in sample ? sample[header] : dataset.metadata[header],
  )).join(','));
  return `${headers.join(',')}\n${rows.join('\n')}\n`;
};

const toSvg = (dataset) => {
  const width = 1600;
  const height = 620;
  const left = 76;
  const top = 118;
  const chartWidth = 1460;
  const chartHeight = 390;
  const points = dataset.samples.map((sample, index) => {
    const x = left + (index / (dataset.samples.length - 1)) * chartWidth;
    const y = top + (1 - sample.ppg) * chartHeight;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(' ');
  const labels = dataset.metadata.condition === 'combined'
    ? '<text x="260" y="565">CLEAN</text><text x="610" y="565">MILD</text><text x="970" y="565">HEAVY</text><text x="1320" y="565">RECOVERY</text>'
    : `<text x="800" y="565" text-anchor="middle">${dataset.metadata.condition.replaceAll('_', ' ').toUpperCase()}</text>`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="620" viewBox="0 0 1600 620">
  <rect width="1600" height="620" rx="28" fill="#0B1726"/>
  <text x="76" y="64" fill="#F6F8F7" font-family="Arial, sans-serif" font-size="28" font-weight="700">Synthetic PPG preview • ${dataset.metadata.condition.replaceAll('_', ' ')}</text>
  <text x="76" y="94" fill="#F6F8F7" opacity="0.64" font-family="Arial, sans-serif" font-size="16">Simulated data for prototype demonstration • not medically validated • seed ${dataset.metadata.seed}</text>
  ${Array.from({length: 7}, (_, index) => `<line x1="${left}" x2="${left + chartWidth}" y1="${top + index * chartHeight / 6}" y2="${top + index * chartHeight / 6}" stroke="#FFFFFF" stroke-opacity="0.08"/>`).join('\n  ')}
  <polyline points="${points}" fill="none" stroke="#35C4B5" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  <g fill="#F6F8F7" opacity="0.58" font-family="Arial, sans-serif" font-size="16" font-weight="700">${labels}</g>
</svg>\n`;
};

const definitions = [
  {condition: 'clean', seed: 41001, slug: 'ppg_clean-synthetic'},
  {condition: 'mild_artifact', seed: 41002, slug: 'ppg_mild-artifact-synthetic'},
  {condition: 'heavy_artifact', seed: 41003, slug: 'ppg_heavy-artifact-synthetic'},
  {condition: 'recovery', seed: 41004, slug: 'ppg_recovery-synthetic'},
  {condition: 'combined', seed: 41005, slug: 'ppg_demo-sequence-synthetic'},
];

for (const definition of definitions) {
  const dataset = makeDataset(definition);
  const reviewBase = `${definition.slug}_review_v1`;
  const approvedBase = `${definition.slug}_approved_v1`;
  const json = `${JSON.stringify({metadata: dataset.metadata, samples: dataset.samples}, null, 2)}\n`;
  const csv = toCsv(dataset);
  const svg = toSvg(dataset);

  fs.writeFileSync(path.join(RAW_DATA_DIR, `${reviewBase}.json`), json);
  fs.writeFileSync(path.join(RAW_DATA_DIR, `${reviewBase}.csv`), csv);
  fs.writeFileSync(path.join(RAW_PREVIEW_DIR, `${reviewBase}.svg`), svg);

  fs.writeFileSync(path.join(APPROVED_DIR, `${approvedBase}.json`), json.replace('"lifecycle_status": "review"', '"lifecycle_status": "approved"'));
  fs.writeFileSync(path.join(APPROVED_DIR, `${approvedBase}.csv`), csv);
  fs.writeFileSync(path.join(APPROVED_DIR, `${approvedBase}.svg`), svg);

  fs.writeFileSync(path.join(PUBLIC_DIR, `${approvedBase}.json`), json.replace('"lifecycle_status": "review"', '"lifecycle_status": "approved"'));
  fs.writeFileSync(path.join(PUBLIC_DIR, `${approvedBase}.svg`), svg);
}

console.log(`Generated ${definitions.length} deterministic synthetic PPG datasets at ${SAMPLE_RATE_HZ} Hz.`);
