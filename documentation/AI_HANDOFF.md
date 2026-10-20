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
python -m pip install -r apps/ai-service/requirements-notebooks.txt
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

Start Jupyter without exposing it publicly:

```bash
jupyter lab --no-browser --port 8888
```

From the local computer, create an SSH tunnel:

```bash
ssh -L 8888:localhost:8888 USER@SERVER
```

Then open `http://localhost:8888` locally and run the notebooks in order.

## Reproducibility contract

- The default random seed is `2026`.
- Train, validation, and test splits are disjoint by subject.
- Test data must not be used to select features, models, or thresholds.
- `Caution` is derived from validation-set uncertainty; it is not a native BUT PPG label.
- Raw and generated datasets must remain outside Git.
- Only metrics actually produced by the notebooks may be reported as results.

## Expected artifacts

```text
data/processed/but-ppg-v2/features.csv
data/processed/but-ppg-v2/manifest.json
models/candidates/logistic_regression.joblib
models/candidates/random_forest.joblib
models/model_selection.json
models/quality_gate_thresholds.json
models/test_metrics.json
```
