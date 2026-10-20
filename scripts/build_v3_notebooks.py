#!/usr/bin/env python3
"""Build thin, reproducible notebooks for the PURE V3 ensemble workflow."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"


def markdown(cell_id: str, source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": dedent(source).strip().splitlines(keepends=True),
    }


def code(cell_id: str, source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": dedent(source).strip().splitlines(keepends=True),
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


PATHS = r'''
from pathlib import Path
import os
import sys


def find_repository_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    raise RuntimeError("Run this notebook inside the pure-pulsesure repository")


REPO_ROOT = find_repository_root(Path.cwd().resolve())
RAW_DIR = Path(os.environ.get("PURE_BUT_PPG_DIR", REPO_ROOT / "data" / "raw" / "but-ppg-2.0.0")).expanduser().resolve()
V3_DATA_DIR = Path(os.environ.get("PURE_V3_DATA_DIR", REPO_ROOT / "data" / "processed" / "but-ppg-v3")).expanduser().resolve()
V3_MODEL_DIR = Path(os.environ.get("PURE_V3_MODEL_DIR", REPO_ROOT / "models" / "production" / "v3")).expanduser().resolve()

print("Raw:", RAW_DIR)
print("V3 data:", V3_DATA_DIR)
print("V3 models:", V3_MODEL_DIR)
'''


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    notebooks = {
        "08_prepare_multiview_v3.ipynb": notebook([
            markdown("v3-pre-01", """
            # 08 — Prepare V3 multi-view data

            This stage creates three complementary representations from the annotated red PPG:

            - filtered PPG + first derivative + second derivative;
            - compact log-power STFT;
            - morphology, periodicity, beat-template, and spectral SQIs.

            The original test subjects remain marked as audit-only.
            """),
            code("v3-pre-02", PATHS),
            code("v3-pre-03", r'''
            import subprocess

            subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "prepare_but_ppg_v3.py"),
                    "--raw-dir", str(RAW_DIR),
                    "--output-dir", str(V3_DATA_DIR),
                ],
                check=True,
            )
            '''),
            code("v3-pre-04", r'''
            import json
            import numpy as np

            archive = np.load(V3_DATA_DIR / "v3_representations.npz")
            manifest = json.loads((V3_DATA_DIR / "manifest.json").read_text())
            print("Waveform:", archive["X_waveform"].shape)
            print("STFT:", archive["X_stft"].shape)
            print("SQI:", archive["X_sqi"].shape)
            print("All finite:", all(np.isfinite(archive[name]).all() for name in ["X_waveform", "X_stft", "X_sqi"]))
            manifest
            '''),
            code("v3-pre-05", r'''
            import matplotlib.pyplot as plt

            y = archive["y"]
            figure, axes = plt.subplots(2, 2, figsize=(12, 7))
            for row, label in enumerate([1, 0]):
                index = int(np.flatnonzero(y == label)[0])
                axes[row, 0].plot(archive["X_waveform"][index, 0], label="PPG")
                axes[row, 0].plot(archive["X_waveform"][index, 1], alpha=0.6, label="FDP")
                axes[row, 0].set_title("Good" if label else "Poor")
                axes[row, 1].imshow(archive["X_stft"][index, 0], origin="lower", aspect="auto", cmap="magma")
                axes[row, 1].set_title("Log-STFT")
            axes[0, 0].legend()
            plt.tight_layout()
            ''')
        ]),
        "09_train_subject_ensemble_v3.ipynb": notebook([
            markdown("v3-train-01", """
            # 09 — Train the V3 subject-wise ensemble

            Five subject-disjoint folds train compact waveform and STFT CNNs plus an SQI
            ExtraTrees model. Every development record receives an out-of-fold prediction.
            Calibration and quality-gate thresholds use only these OOF scores; original test
            subjects are never opened by this notebook.
            """),
            code("v3-train-02", PATHS),
            code("v3-train-03", r'''
            import subprocess

            subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "train_v3_ensemble.py"),
                    "--input-dir", str(V3_DATA_DIR),
                    "--model-dir", str(V3_MODEL_DIR),
                    "--epochs", os.environ.get("PURE_V3_EPOCHS", "50"),
                    "--patience", os.environ.get("PURE_V3_PATIENCE", "8"),
                ],
                check=True,
            )
            '''),
            code("v3-train-04", r'''
            import json
            import pandas as pd

            report = json.loads((V3_MODEL_DIR / "oof_metrics.json").read_text())
            display(pd.Series(report["oof_binary"]).to_frame("OOF ensemble"))
            display(pd.Series(report["oof_gate"]).to_frame("OOF quality gate"))
            display(pd.DataFrame(report["branch_oof_metrics"]).T[["accuracy", "balanced_accuracy", "f1_good", "roc_auc", "false_acceptance_rate"]])
            ''')
        ]),
        "10_evaluate_ensemble_v3.ipynb": notebook([
            markdown("v3-eval-01", """
            # 10 — Audit the frozen V3 ensemble

            This stage loads the already-frozen five-fold models and thresholds, then
            evaluates the original seven test subjects once. Because those subjects were
            inspected during V2 development, OOF performance remains the primary estimate;
            this result is an audit comparison rather than a pristine final test.
            """),
            code("v3-eval-02", PATHS),
            code("v3-eval-03", r'''
            import subprocess

            subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "evaluate_v3_ensemble.py"),
                    "--input-dir", str(V3_DATA_DIR),
                    "--model-dir", str(V3_MODEL_DIR),
                ],
                check=True,
            )
            '''),
            code("v3-eval-04", r'''
            import json
            import pandas as pd

            report = json.loads((V3_MODEL_DIR / "test_metrics.json").read_text())
            display(pd.Series(report["test_binary"]).to_frame("audit test"))
            display(pd.Series(report["test_gate"]).to_frame("audit gate"))
            display(pd.DataFrame(report["branch_test_metrics"]).T[["accuracy", "balanced_accuracy", "f1_good", "roc_auc", "false_acceptance_rate"]])
            print("Reliable precision:", report["reliable_precision"])
            ''')
        ]),
    }
    for filename, payload in notebooks.items():
        path = NOTEBOOK_DIR / filename
        path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
