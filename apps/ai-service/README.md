# PURE AI Service

This directory contains the Python signal-processing and machine-learning
service used by PURE. The first implemented stage is a reproducible BUT PPG v2
preprocessing pipeline.

## Preprocessing contract

The offline preparation and future FastAPI inference endpoint share the same
operations:

1. Decode either BUT PPG v2 waveform layout.
2. Select the annotated red channel for RGB recordings.
3. Interpolate non-finite samples.
4. Remove the linear trend.
5. Retain the 0.5-5 Hz PPG band using a deterministic FFT filter.
6. Apply per-record z-normalization.
7. Extract explainable morphology and spectral features.

That path remains the transparent baseline. The improved waveform path uses a
zero-phase fourth-order Butterworth filter and preserves three full-length
views (`raw_robust`, `butterworth_bandpass`, `first_derivative`) for the compact
ResNet1D. Raw morphology is retained because aggressive filtering alone can
hide clipping and motion artifacts.

The dataset quality label is binary and applies to the complete 10-second
record. It does not provide temporal artifact boundaries. PURE therefore uses
the terms `good_quality_probability` and `quality_score`; the `Caution` state
will later be derived from model uncertainty thresholds on the validation set.

## Prepare the dataset

From the repository root:

```bash
python3 scripts/prepare_but_ppg.py
```

Prepare the V2 waveform dataset with:

```bash
python3 scripts/prepare_but_ppg_waveforms.py
```

Run a small smoke test first when needed:

```bash
python3 scripts/prepare_but_ppg.py --limit 100 \
  --output-dir data/processed/but-ppg-smoke
```

Generated measurement data stays under `data/processed/` and is excluded from
Git. The script writes:

- `features.csv`: one feature row per record;
- `manifest.json`: provenance, preprocessing settings, and split statistics;
- `splits.json`: subject IDs assigned to train, validation, and test;
- `preprocessing_config.json`: parameters required by online inference;
- `demo_records/`: a small set of real, processed test waveforms;
- `failures.csv`: auditable errors, only when a record cannot be processed.

## Train the waveform candidate

Install the training environment, then run notebooks 05-07 in order:

```bash
python -m pip install -r apps/ai-service/requirements-training.txt
jupyter lab --no-browser --ip=127.0.0.1 --port=8888
```

The production bundle is written to `models/production/` only after notebook
07 freezes validation-derived calibration and evaluates the held-out subjects.

## Test

The preprocessing test suite requires the AI service dependencies:

```bash
python3 -m unittest discover -s tests/ai -p 'test_*.py'
```
