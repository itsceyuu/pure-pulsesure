# AI Workflow Handoff

## Current implementation

The `feat/ai-service` branch contains a tested preprocessing pipeline for BUT
PPG v2. It handles both dataset layouts, performs subject-wise splitting, and
exports baseline features and real waveform examples.

## Run on the SSH server

```bash
git clone https://github.com/itsceyuu/pure-pulsesure.git
cd pure-pulsesure
git checkout feat/ai-service

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/ai-service/requirements-training.txt
```

Place or link the dataset on the server, then configure its path:

```bash
export PURE_BUT_PPG_DIR=/absolute/path/to/but-ppg-2.0.0
export PURE_PROCESSED_DIR=/absolute/path/to/processed/but-ppg-v2
```

Prepare all records:

```bash
python scripts/prepare_but_ppg.py \
  --raw-dir "$PURE_BUT_PPG_DIR" \
  --output-dir "$PURE_PROCESSED_DIR"
```

For the corrected waveform model, use the red-channel V2 exporter instead:

```bash
python scripts/prepare_but_ppg_waveforms.py \
  --raw-dir "$PURE_BUT_PPG_DIR" \
  --output-dir "${PURE_WAVEFORM_DIR:-data/processed/but-ppg-waveforms-v2}"
```

Start Jupyter without exposing it publicly:

```bash
jupyter lab --no-browser --port 8888
```

From the local computer, create an SSH tunnel:

```bash
ssh -L 8888:localhost:8888 USER@SERVER
```

Then open `http://localhost:8888` locally and run the notebooks in order.

For the waveform candidate, run notebooks 05, 06, and 07. Notebook 06 never
uses held-out test subjects for early stopping. Notebook 07 fits calibration
and thresholds on validation subjects before opening the test split once.

For the multi-view V3 ensemble, run notebooks 08, 09, and 10. V3 uses:

- filtered red PPG, first derivative, and second derivative;
- a compact log-power STFT branch;
- morphology, periodicity, template-correlation, and spectral SQIs;
- five subject-disjoint development folds;
- equal-probability branch fusion followed by OOF Platt calibration.

Notebook 09 is the long GPU stage. It writes every fold model and all OOF
metrics under `models/production/v3/`. Notebook 10 does not retrain or retune;
it only applies the frozen ensemble to the original audit subjects.

## Reproducibility contract

- The default random seed is `2026`.
- Train, validation, and test splits are disjoint by subject.
- Test data must not be used to select features, models, or thresholds.
- `Caution` is derived from validation-set uncertainty; it is not a native BUT PPG label.
- Raw and generated datasets must remain outside Git.
- Only metrics actually produced by the notebooks may be reported as results.
- Ordinary accuracy is not sufficient because 3,058/3,888 records are poor
  quality. Always report balanced accuracy, good-class F1, specificity, and
  false-acceptance rate.

## Expected artifacts

```text
data/processed/but-ppg-v2/features.csv
data/processed/but-ppg-v2/manifest.json
models/candidates/logistic_regression.joblib
models/candidates/random_forest.joblib
models/model_selection.json
models/quality_gate_thresholds.json
models/test_metrics.json
data/processed/but-ppg-waveforms-v2/waveforms.npz
models/candidates/waveform_resnet1d.pt
models/production/quality_model.pt
models/production/model_metadata.json
models/production/quality_gate_thresholds.json
models/test_metrics_waveform_v2.json
data/processed/but-ppg-v3/v3_representations.npz
models/production/v3/waveform_fold_1.pt
models/production/v3/stft_fold_1.pt
models/production/v3/sqi_fold_1.joblib
models/production/v3/ensemble_calibrator.joblib
models/production/v3/oof_metrics.json
models/production/v3/thresholds.json
models/production/v3/test_metrics.json
```
