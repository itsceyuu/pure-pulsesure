import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const requiredAssets = [
  'public/brand/brand_pure-logo-symbol_approved_v1.svg',
  'public/architecture/architecture_system-diagram_approved_v1.png',
  'public/dashboard/dashboard_not-assessed_approved_v1.png',
  'public/dashboard/dashboard_reliable_approved_v1.png',
  'public/dashboard/dashboard_caution_approved_v1.png',
  'public/dashboard/dashboard_unreliable_approved_v1.png',
  'public/hardware/hardware_max30102-render_approved_v1.png',
  'public/hardware/hardware_esp32-c3-render_approved_v1.png',
  'public/hardware/hardware_mpu6050-render_approved_v1.png',
  'public/hardware/hardware_pure-prototype-front_approved_v1.png',
  'public/hardware/hardware_pure-prototype-side_approved_v1.png',
  'public/ppg/ppg_clean-synthetic_approved_v1.json',
  'public/ppg/ppg_mild-artifact-synthetic_approved_v1.json',
  'public/ppg/ppg_heavy-artifact-synthetic_approved_v1.json',
  'public/ppg/ppg_recovery-synthetic_approved_v1.json',
  'public/ppg/ppg_demo-sequence-synthetic_approved_v1.json',
];

const failures = [];

for (const relativePath of requiredAssets) {
  const absolutePath = path.join(PROJECT_ROOT, relativePath);
  if (!fs.existsSync(absolutePath)) failures.push(`Missing: ${relativePath}`);
}

for (const relativePath of requiredAssets.filter((file) => file.endsWith('.json'))) {
  const dataset = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, relativePath), 'utf8'));
  const metadata = dataset.metadata ?? {};
  if (metadata.synthetic !== true) failures.push(`${relativePath}: synthetic must be true`);
  if (metadata.intended_use !== 'visual prototype demonstration only') failures.push(`${relativePath}: intended_use mismatch`);
  if (metadata.not_medically_validated !== true) failures.push(`${relativePath}: not_medically_validated must be true`);
  if (metadata.sample_rate_hz !== 30) failures.push(`${relativePath}: expected 30 Hz`);
  if (metadata.duration_seconds !== 10 || dataset.samples?.length !== 300) failures.push(`${relativePath}: expected 10 seconds / 300 samples`);
  if (JSON.stringify(dataset).includes('model_score')) failures.push(`${relativePath}: prohibited model_score field found`);
}

if (failures.length > 0) {
  console.error(failures.join('\n'));
  process.exit(1);
}

console.log(`Asset QA passed: ${requiredAssets.length} runtime assets present; synthetic metadata and sample counts valid.`);
