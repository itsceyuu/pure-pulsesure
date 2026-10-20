# PURE AI Service

This directory contains the Python signal-processing and machine-learning
service used by PURE. The first implemented stage is a reproducible BUT PPG v2
preprocessing pipeline.

## Preprocessing contract

The offline preparation and future FastAPI inference endpoint share the same
operations:

1. Decode either BUT PPG v2 waveform layout.
2. Select the green channel for RGB recordings.
3. Interpolate non-finite samples.
4. Remove the linear trend.
5. Retain the 0.5-5 Hz PPG band using a deterministic FFT filter.
6. Apply per-record z-normalization.
7. Extract explainable morphology and spectral features.

The dataset quality label is binary and applies to the complete 10-second
record. It does not provide temporal artifact boundaries. PURE therefore uses
the terms `good_quality_probability` and `quality_score`; the `Caution` state
will later be derived from model uncertainty thresholds on the validation set.

## Prepare the dataset

From the repository root:

```bash
python3 scripts/prepare_but_ppg.py
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

## Test

The preprocessing test suite only requires NumPy:

```bash
python3 -m unittest discover -s tests/ai -p 'test_*.py'
```
