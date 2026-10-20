#!/usr/bin/env python3
"""Build the versioned V2 waveform notebooks with stable cell identifiers."""

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


PATH_SETUP = r'''
from pathlib import Path
import os
import sys


def find_repository_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() and (candidate / "apps").exists():
            return candidate
    raise RuntimeError("Run this notebook from inside the pure-pulsesure repository")


REPO_ROOT = find_repository_root(Path.cwd().resolve())
AI_SERVICE_ROOT = REPO_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

RAW_DIR = Path(
    os.environ.get("PURE_BUT_PPG_DIR", REPO_ROOT / "data" / "raw" / "but-ppg-2.0.0")
).expanduser().resolve()
WAVEFORM_DIR = Path(
    os.environ.get("PURE_WAVEFORM_DIR", REPO_ROOT / "data" / "processed" / "but-ppg-waveforms-v2")
).expanduser().resolve()
MODEL_DIR = Path(os.environ.get("PURE_MODEL_DIR", REPO_ROOT / "models")).expanduser().resolve()

print("Repository:", REPO_ROOT)
print("Raw dataset:", RAW_DIR)
print("Waveform dataset:", WAVEFORM_DIR)
print("Model directory:", MODEL_DIR)
'''


def build_preprocessing_notebook() -> dict:
    return notebook([
        markdown("v2-pre-01", """
        # 05 — Waveform preprocessing V2

        This pipeline corrects the annotated-channel mismatch in the baseline and
        preserves the complete 10-second waveform for temporal modeling.

        - `PPG_R` is used because BUT PPG quality labels were created from red PPG.
        - Each record becomes three aligned views: robust raw, Butterworth band-pass,
          and first derivative.
        - The original subject-disjoint split is retained.
        - No label-dependent transformation or overlapping cross-subject windowing is used.
        """),
        code("v2-pre-02", PATH_SETUP),
        code("v2-pre-03", r'''
        import subprocess

        command = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "prepare_but_ppg_waveforms.py"),
            "--raw-dir", str(RAW_DIR),
            "--output-dir", str(WAVEFORM_DIR),
        ]
        subprocess.run(command, check=True)
        '''),
        code("v2-pre-04", r'''
        import json
        import numpy as np
        import pandas as pd

        archive = np.load(WAVEFORM_DIR / "waveforms.npz")
        X, y = archive["X"], archive["y"]
        metadata = pd.DataFrame({
            "record_id": archive["record_id"],
            "subject_id": archive["subject_id"],
            "split": archive["split"],
            "label_good_quality": y,
            "selected_channel": archive["selected_channel"],
        })
        print("X shape:", X.shape)
        print("finite:", bool(np.isfinite(X).all()))
        display(pd.crosstab(metadata["split"], metadata["label_good_quality"], margins=True))
        display(pd.crosstab(metadata["selected_channel"], metadata["label_good_quality"], margins=True))
        json.loads((WAVEFORM_DIR / "manifest.json").read_text())
        '''),
        code("v2-pre-05", r'''
        import matplotlib.pyplot as plt

        view_names = ["raw robust", "band-pass", "first derivative"]
        figure, axes = plt.subplots(2, 3, figsize=(15, 6), sharex=True)
        for row, label in enumerate([1, 0]):
            index = int(np.flatnonzero(y == label)[0])
            for column in range(3):
                axes[row, column].plot(X[index, column], linewidth=1)
                axes[row, column].set_title(f"{'Good' if label else 'Poor'} — {view_names[column]}")
        plt.tight_layout()
        ''')
    ])


def build_training_notebook() -> dict:
    return notebook([
        markdown("v2-train-01", """
        # 06 — Train the waveform ResNet1D

        Training uses only train subjects; early stopping and model selection use
        validation subjects. The held-out test split is deliberately not evaluated here.
        Class weighting addresses the 830/3,058 good/poor imbalance without duplicating
        subjects or manufacturing new labels.
        """),
        code("v2-train-02", PATH_SETUP),
        code("v2-train-03", r'''
        import json
        import random
        import time

        import matplotlib.pyplot as plt
        import numpy as np
        import torch
        from sklearn.metrics import (
            average_precision_score,
            balanced_accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
        from torch import nn
        from torch.utils.data import DataLoader, Dataset

        from app.models.waveform_resnet import PPGQualityResNet1D, parameter_count

        SEED = 2026
        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(SEED)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("Device:", DEVICE)
        if DEVICE.type == "cuda":
            print("GPU:", torch.cuda.get_device_name(0))
        '''),
        code("v2-train-04", r'''
        archive = np.load(WAVEFORM_DIR / "waveforms.npz")
        X = archive["X"].astype(np.float32)
        y = archive["y"].astype(np.float32)
        split = archive["split"].astype(str)

        train_indices = np.flatnonzero(split == "train")
        validation_indices = np.flatnonzero(split == "validation")

        class PPGDataset(Dataset):
            def __init__(self, indices):
                self.indices = np.asarray(indices)

            def __len__(self):
                return len(self.indices)

            def __getitem__(self, item):
                index = self.indices[item]
                return torch.from_numpy(X[index]), torch.tensor(y[index], dtype=torch.float32)

        train_loader = DataLoader(PPGDataset(train_indices), batch_size=64, shuffle=True, num_workers=0)
        validation_loader = DataLoader(PPGDataset(validation_indices), batch_size=128, shuffle=False, num_workers=0)
        print("Train / validation:", len(train_indices), len(validation_indices))
        '''),
        code("v2-train-05", r'''
        def predict(model, loader):
            model.eval()
            logits, labels = [], []
            with torch.no_grad():
                for inputs, targets in loader:
                    logits.append(model(inputs.to(DEVICE)).cpu().numpy())
                    labels.append(targets.numpy())
            logits = np.concatenate(logits)
            labels = np.concatenate(labels).astype(int)
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
            return labels, logits, probabilities


        def classification_metrics(labels, probabilities, threshold=0.5):
            predictions = (probabilities >= threshold).astype(int)
            return {
                "accuracy": float(np.mean(predictions == labels)),
                "balanced_accuracy": balanced_accuracy_score(labels, predictions),
                "precision_good": precision_score(labels, predictions, zero_division=0),
                "recall_good": recall_score(labels, predictions, zero_division=0),
                "f1_good": f1_score(labels, predictions, zero_division=0),
                "roc_auc": roc_auc_score(labels, probabilities),
                "average_precision": average_precision_score(labels, probabilities),
            }
        '''),
        code("v2-train-06", r'''
        model = PPGQualityResNet1D().to(DEVICE)
        negative_count = float(np.sum(y[train_indices] == 0))
        positive_count = float(np.sum(y[train_indices] == 1))
        positive_weight = torch.tensor([negative_count / positive_count], device=DEVICE)
        criterion = nn.BCEWithLogitsLoss(pos_weight=positive_weight)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", factor=0.5, patience=3, min_lr=1e-5
        )

        print("Trainable parameters:", parameter_count(model))
        print("Positive-class loss weight:", float(positive_weight.item()))
        '''),
        code("v2-train-07", r'''
        MAX_EPOCHS = 60
        EARLY_STOPPING_PATIENCE = 10
        checkpoint_directory = MODEL_DIR / "candidates"
        checkpoint_directory.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_directory / "waveform_resnet1d.pt"

        history = []
        best_score = -np.inf
        epochs_without_improvement = 0
        started = time.time()

        for epoch in range(1, MAX_EPOCHS + 1):
            model.train()
            batch_losses = []
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(model(inputs), targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
                batch_losses.append(float(loss.item()))

            labels_val, _, probability_val = predict(model, validation_loader)
            metrics_val = classification_metrics(labels_val, probability_val)
            score = metrics_val["balanced_accuracy"]
            scheduler.step(score)
            history.append({
                "epoch": epoch,
                "train_loss": float(np.mean(batch_losses)),
                "learning_rate": optimizer.param_groups[0]["lr"],
                **metrics_val,
            })
            print(
                f"epoch={epoch:02d} loss={history[-1]['train_loss']:.4f} "
                f"val_bal_acc={score:.4f} val_auc={metrics_val['roc_auc']:.4f} "
                f"val_f1={metrics_val['f1_good']:.4f}"
            )

            if score > best_score + 1e-4:
                best_score = score
                epochs_without_improvement = 0
                torch.save(model.state_dict(), checkpoint_path)
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= EARLY_STOPPING_PATIENCE:
                    print("Early stopping")
                    break

        elapsed_seconds = time.time() - started
        print(f"Best validation balanced accuracy: {best_score:.4f}")
        print(f"Training time: {elapsed_seconds:.1f}s")
        '''),
        code("v2-train-08", r'''
        import pandas as pd

        history_frame = pd.DataFrame(history)
        display(history_frame.tail())
        figure, axes = plt.subplots(1, 2, figsize=(12, 4))
        history_frame.plot(x="epoch", y="train_loss", ax=axes[0], title="Training loss")
        history_frame.plot(x="epoch", y=["balanced_accuracy", "roc_auc", "f1_good"], ax=axes[1], title="Validation metrics")
        plt.tight_layout()

        training_metadata = {
            "model": "PPGQualityResNet1D",
            "checkpoint": str(checkpoint_path.relative_to(REPO_ROOT)),
            "input_shape": [3, 300],
            "view_order": ["raw_robust", "butterworth_bandpass", "first_derivative"],
            "selection_metric": "validation balanced accuracy at threshold 0.5",
            "best_validation_balanced_accuracy": float(best_score),
            "epochs_completed": len(history),
            "seed": SEED,
            "parameter_count": parameter_count(model),
            "class_weight_good": float(positive_weight.item()),
        }
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        (MODEL_DIR / "waveform_training_metadata.json").write_text(json.dumps(training_metadata, indent=2) + "\n")
        training_metadata
        ''')
    ])


def build_evaluation_notebook() -> dict:
    return notebook([
        markdown("v2-eval-01", """
        # 07 — Calibrate and evaluate the waveform model

        Validation subjects are used for probability calibration and threshold selection.
        The frozen policy is then evaluated once on held-out test subjects. Report accuracy
        together with balanced accuracy, good-class F1, sensitivity, specificity, ROC-AUC,
        and false-acceptance rate; accuracy alone is misleading for this imbalanced dataset.
        """),
        code("v2-eval-02", PATH_SETUP),
        code("v2-eval-03", r'''
        import json
        import shutil

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns
        import torch
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            average_precision_score,
            balanced_accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
        from torch.utils.data import DataLoader, TensorDataset

        from app.models.waveform_resnet import PPGQualityResNet1D

        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        archive = np.load(WAVEFORM_DIR / "waveforms.npz")
        X = archive["X"].astype(np.float32)
        y = archive["y"].astype(int)
        split = archive["split"].astype(str)
        record_ids = archive["record_id"].astype(str)

        checkpoint_path = MODEL_DIR / "candidates" / "waveform_resnet1d.pt"
        model = PPGQualityResNet1D().to(DEVICE)
        model.load_state_dict(torch.load(checkpoint_path, map_location=DEVICE, weights_only=True))
        model.eval()
        '''),
        code("v2-eval-04", r'''
        def infer(indices):
            loader = DataLoader(
                TensorDataset(torch.from_numpy(X[indices]), torch.from_numpy(y[indices])),
                batch_size=128,
                shuffle=False,
            )
            logits, labels = [], []
            with torch.no_grad():
                for inputs, targets in loader:
                    logits.append(model(inputs.to(DEVICE)).cpu().numpy())
                    labels.append(targets.numpy())
            return np.concatenate(labels).astype(int), np.concatenate(logits)

        validation_indices = np.flatnonzero(split == "validation")
        test_indices = np.flatnonzero(split == "test")
        y_validation, logits_validation = infer(validation_indices)
        y_test, logits_test = infer(test_indices)

        # Platt calibration is fitted only on validation subjects.
        calibrator = LogisticRegression(C=1e3, solver="lbfgs", random_state=2026)
        calibrator.fit(logits_validation.reshape(-1, 1), y_validation)
        probability_validation = calibrator.predict_proba(logits_validation.reshape(-1, 1))[:, 1]
        probability_test = calibrator.predict_proba(logits_test.reshape(-1, 1))[:, 1]
        '''),
        code("v2-eval-05", r'''
        def binary_metrics(labels, probabilities, threshold):
            predictions = (probabilities >= threshold).astype(int)
            matrix = confusion_matrix(labels, predictions, labels=[0, 1])
            tn, fp, fn, tp = matrix.ravel()
            return {
                "threshold": float(threshold),
                "accuracy": float(np.mean(predictions == labels)),
                "balanced_accuracy": balanced_accuracy_score(labels, predictions),
                "precision_good": precision_score(labels, predictions, zero_division=0),
                "recall_good_sensitivity": recall_score(labels, predictions, zero_division=0),
                "specificity_poor": float(tn / max(tn + fp, 1)),
                "f1_good": f1_score(labels, predictions, zero_division=0),
                "false_acceptance_rate": float(fp / max(tn + fp, 1)),
                "false_rejection_rate": float(fn / max(fn + tp, 1)),
                "roc_auc": roc_auc_score(labels, probabilities),
                "average_precision": average_precision_score(labels, probabilities),
                "confusion_matrix": matrix.tolist(),
            }

        candidates = [binary_metrics(y_validation, probability_validation, threshold) for threshold in np.linspace(0.02, 0.98, 193)]
        safe_candidates = [item for item in candidates if item["false_acceptance_rate"] <= 0.10]
        selection_pool = safe_candidates or candidates
        validation_choice = max(selection_pool, key=lambda item: (item["balanced_accuracy"], item["f1_good"]))
        binary_threshold = validation_choice["threshold"]

        test_binary = binary_metrics(y_test, probability_test, binary_threshold)
        display(pd.DataFrame([validation_choice, test_binary], index=["validation", "test"]).drop(columns="confusion_matrix"))
        '''),
        code("v2-eval-06", r'''
        def gate_metrics(labels, probabilities, lower, upper):
            reliable = probabilities >= upper
            unreliable = probabilities <= lower
            caution = ~(reliable | unreliable)
            good = labels == 1
            poor = labels == 0
            return {
                "lower_threshold": float(lower),
                "upper_threshold": float(upper),
                "false_acceptance_rate": float(np.mean(reliable[poor])),
                "false_rejection_rate": float(np.mean(unreliable[good])),
                "good_acceptance_rate": float(np.mean(reliable[good])),
                "poor_rejection_rate": float(np.mean(unreliable[poor])),
                "reliable_coverage": float(np.mean(reliable)),
                "caution_rate": float(np.mean(caution)),
                "unreliable_rate": float(np.mean(unreliable)),
            }

        upper_candidates = []
        for upper in np.linspace(binary_threshold, 0.99, 150):
            upper_candidates.append(gate_metrics(y_validation, probability_validation, 0.0, upper))
        feasible_upper = [item for item in upper_candidates if item["false_acceptance_rate"] <= 0.05]
        upper_threshold = max(feasible_upper or upper_candidates, key=lambda item: item["good_acceptance_rate"])["upper_threshold"]

        lower_candidates = []
        for lower in np.linspace(0.01, min(binary_threshold, upper_threshold - 0.01), 150):
            lower_candidates.append(gate_metrics(y_validation, probability_validation, lower, upper_threshold))
        feasible_lower = [item for item in lower_candidates if item["false_rejection_rate"] <= 0.05]
        lower_threshold = max(feasible_lower or lower_candidates, key=lambda item: item["poor_rejection_rate"])["lower_threshold"]

        validation_gate = gate_metrics(y_validation, probability_validation, lower_threshold, upper_threshold)
        test_gate = gate_metrics(y_test, probability_test, lower_threshold, upper_threshold)
        display(pd.DataFrame([validation_gate, test_gate], index=["validation", "test"]))
        '''),
        code("v2-eval-07", r'''
        predictions_test = (probability_test >= binary_threshold).astype(int)
        figure, axes = plt.subplots(1, 2, figsize=(12, 4))
        sns.heatmap(
            confusion_matrix(y_test, predictions_test, labels=[0, 1]),
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=["Poor", "Good"],
            yticklabels=["Poor", "Good"],
            ax=axes[0],
        )
        axes[0].set_title("Held-out test confusion matrix")
        axes[0].set_xlabel("Predicted")
        axes[0].set_ylabel("Reference")

        sns.histplot(x=probability_test, hue=y_test, bins=25, element="step", ax=axes[1])
        axes[1].axvline(lower_threshold, color="#E76F51", linestyle="--")
        axes[1].axvline(upper_threshold, color="#147D78", linestyle="--")
        axes[1].set_title("Held-out calibrated probabilities")
        plt.tight_layout()
        '''),
        code("v2-eval-08", r'''
        production_directory = MODEL_DIR / "production"
        production_directory.mkdir(parents=True, exist_ok=True)
        production_model = production_directory / "quality_model.pt"
        shutil.copy2(checkpoint_path, production_model)

        calibration = {
            "method": "platt_logistic_validation_subjects",
            "coefficient": float(calibrator.coef_[0, 0]),
            "intercept": float(calibrator.intercept_[0]),
        }
        thresholds = {
            "model": "PPGQualityResNet1D",
            "binary_threshold": float(binary_threshold),
            "lower_threshold": float(lower_threshold),
            "upper_threshold": float(upper_threshold),
            "calibration": calibration,
            "quality_score_definition": "round(100 * calibrated_good_quality_probability)",
            "status_policy": {
                "reliable": "probability >= upper_threshold",
                "caution": "lower_threshold < probability < upper_threshold",
                "unreliable": "probability <= lower_threshold",
            },
        }
        metrics = {
            "validation_binary": validation_choice,
            "test_binary": test_binary,
            "validation_gate": validation_gate,
            "test_gate": test_gate,
            "test_records": int(len(test_indices)),
            "test_subjects": int(np.unique(archive["subject_id"][test_indices]).size),
            "limitations": [
                "BUT PPG is smartphone-camera PPG; MAX30102 deployment requires domain validation.",
                "The dataset label is binary and applies to the full ten-second record.",
                "No target performance is guaranteed before this held-out evaluation runs.",
            ],
        }
        metadata = {
            "architecture": "PPGQualityResNet1D",
            "input_shape": [3, 300],
            "sampling_rate_hz": 30.0,
            "view_order": ["raw_robust", "butterworth_bandpass", "first_derivative"],
            "channel_policy": "PPG_R matches BUT PPG annotations",
            "model_file": "quality_model.pt",
            "threshold_file": "quality_gate_thresholds.json",
        }

        (production_directory / "quality_gate_thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n")
        (production_directory / "model_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        (MODEL_DIR / "test_metrics_waveform_v2.json").write_text(json.dumps(metrics, indent=2) + "\n")
        print("Production bundle:", production_directory)
        print(json.dumps(test_binary, indent=2))
        ''')
    ])


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "05_preprocess_waveforms_v2.ipynb": build_preprocessing_notebook(),
        "06_train_waveform_resnet.ipynb": build_training_notebook(),
        "07_evaluate_waveform_resnet.ipynb": build_evaluation_notebook(),
    }
    for filename, payload in outputs.items():
        path = NOTEBOOK_DIR / filename
        path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()

