# PURE AI Notebooks

The notebooks document each experimental stage while keeping production logic
inside `apps/ai-service/app/`. They are intended to run from a local machine or
an SSH training server after cloning the same repository.

Run them in order:

1. `01_eda_but_ppg.ipynb` - dataset integrity, labels, subjects, motion, HR, and waveform review.
2. `02_preprocessing_but_ppg.ipynb` - waveform decoding, filtering, normalization, features, and batch preparation.
3. `03_train_baselines.ipynb` - Logistic Regression and Random Forest baselines.
4. `04_evaluate_quality_gate.ipynb` - validation thresholds and final held-out evaluation.
5. `05_preprocess_waveforms_v2.ipynb` - corrected red-channel, waveform-preserving preprocessing.
6. `06_train_waveform_resnet.ipynb` - compact ResNet1D training with class-weighted loss.
7. `07_evaluate_waveform_resnet.ipynb` - validation-only calibration and held-out evaluation.
8. `08_prepare_multiview_v3.ipynb` - PPG/FDP/SDP, log-STFT, and extended SQI preparation.
9. `09_train_subject_ensemble_v3.ipynb` - five-fold subject ensemble with OOF calibration.
10. `10_evaluate_ensemble_v3.ipynb` - frozen V3 audit on the original test subjects.

Install notebook-only dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/ai-service/requirements-training.txt
jupyter lab
```

By default, notebooks expect BUT PPG v2 at
`data/raw/but-ppg-2.0.0`. On a server, set a different location without editing
the notebooks:

```bash
export PURE_BUT_PPG_DIR=/absolute/path/to/but-ppg-2.0.0
export PURE_PROCESSED_DIR=/absolute/path/to/processed/but-ppg-v2
export PURE_WAVEFORM_DIR=/absolute/path/to/processed/but-ppg-waveforms-v2
```

The V2 notebooks do not guarantee a target score. They correct a material
channel mismatch and retain temporal information that the feature baseline
discarded. Compare models on the same subject-disjoint test set using balanced
accuracy, good-class F1, specificity, and false-acceptance rate in addition to
ordinary accuracy.

V3 addresses the large V2 validation-to-test gap. It combines a compact
no-SE waveform CNN, a small STFT CNN, and an SQI ExtraTrees branch. Five
subject-disjoint folds produce out-of-fold development predictions; the
original V2 test subjects remain excluded until notebook 10. Since those test
results informed the decision to build V3, V3 OOF metrics are the primary
performance estimate and notebook 10 is an audit comparison.

Generated datasets and model binaries remain ignored by Git. Commit only code,
notebooks, documentation, and small JSON metric/threshold summaries that the
team intentionally reviews.
