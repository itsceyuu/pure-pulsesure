#!/usr/bin/env python3
"""Build the versioned PURE AI notebooks with deterministic, empty outputs."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIRECTORY = ROOT / "notebooks"


def markdown(source: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": dedent(source).strip().splitlines(keepends=True),
    }


def code(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(source).strip().splitlines(keepends=True),
    }


def notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    for index, cell in enumerate(cells, start=1):
        cell["id"] = f"cell-{index:02d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP_CELL = r"""
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
PROCESSED_DIR = Path(
    os.environ.get("PURE_PROCESSED_DIR", REPO_ROOT / "data" / "processed" / "but-ppg-v2")
).expanduser().resolve()
MODEL_DIR = Path(os.environ.get("PURE_MODEL_DIR", REPO_ROOT / "models")).expanduser().resolve()

print("Repository:", REPO_ROOT)
print("Raw dataset:", RAW_DIR)
print("Processed dataset:", PROCESSED_DIR)
print("Model directory:", MODEL_DIR)
"""


def eda_notebook() -> dict[str, Any]:
    return notebook(
        [
            markdown(
                """
                # 01 Exploratory Data Analysis for BUT PPG

                This notebook audits the dataset before modeling. It verifies label and
                subject distributions, explores motion and reference heart rate, and
                visually inspects both legacy and RGB waveform layouts.

                **Rule:** EDA may inspect labels across the complete dataset, but model
                selection and threshold decisions must use only train and validation data.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                import numpy as np
                import pandas as pd
                import matplotlib.pyplot as plt
                import seaborn as sns

                from app.services.preprocessing import load_but_ppg_record, preprocess_ppg

                sns.set_theme(style="whitegrid")
                annotations = pd.read_csv(RAW_DIR / "quality-hr-ann.csv", encoding="utf-8-sig")
                subject_info = pd.read_csv(RAW_DIR / "subject-info.csv", encoding="utf-8-sig")
                annotations["ID"] = annotations["ID"].astype(str).str.zfill(6)
                subject_info["ID"] = subject_info["ID"].astype(str).str.zfill(6)
                annotations["subject_id"] = annotations["ID"].str[:3]
                dataset = annotations.merge(subject_info, on="ID", how="left")
                dataset.head()
                """
            ),
            code(
                """
                summary = pd.Series({
                    "records": len(dataset),
                    "subjects": dataset["subject_id"].nunique(),
                    "good_quality": int((dataset["Quality"] == 1).sum()),
                    "poor_quality": int((dataset["Quality"] == 0).sum()),
                    "missing_reference_hr": int(dataset["HR"].isna().sum()),
                    "duplicate_record_ids": int(dataset["ID"].duplicated().sum()),
                })
                display(summary.to_frame("value"))
                """
            ),
            code(
                """
                fig, axes = plt.subplots(1, 2, figsize=(12, 4))
                sns.countplot(data=dataset, x="Quality", ax=axes[0], palette="Set2", hue="Quality", legend=False)
                axes[0].set_title("Record-level quality labels")
                axes[0].set_xticks([0, 1], ["Poor", "Good"])

                records_per_subject = dataset.groupby("subject_id").size()
                sns.histplot(records_per_subject, bins=15, ax=axes[1])
                axes[1].set_title("Records per subject")
                axes[1].set_xlabel("Record count")
                plt.tight_layout()
                """
            ),
            code(
                """
                fig, axes = plt.subplots(1, 2, figsize=(14, 4))
                sns.histplot(data=dataset, x="HR", hue="Quality", bins=25, element="step", ax=axes[0])
                axes[0].set_title("Reference HR by quality label")

                motion_quality = pd.crosstab(dataset["Motion"].fillna("unknown").astype(str), dataset["Quality"], normalize="index")
                motion_quality.columns = ["Poor", "Good"]
                motion_quality.sort_values("Good").plot(kind="bar", stacked=True, ax=axes[1], color=["#E76F51", "#2A9D8F"])
                axes[1].set_title("Quality fraction by motion annotation")
                axes[1].set_ylabel("Fraction")
                axes[1].legend(loc="lower right")
                plt.tight_layout()
                """
            ),
            code(
                """
                legacy = dataset[dataset["ID"].astype(int) < 112000]
                modern = dataset[dataset["ID"].astype(int) >= 112000]
                preview_ids = [
                    legacy.loc[legacy["Quality"] == 1, "ID"].iloc[0],
                    legacy.loc[legacy["Quality"] == 0, "ID"].iloc[0],
                    modern.loc[modern["Quality"] == 1, "ID"].iloc[0],
                    modern.loc[modern["Quality"] == 0, "ID"].iloc[0],
                ]

                fig, axes = plt.subplots(len(preview_ids), 2, figsize=(14, 10), sharex=True)
                for row_index, record_id in enumerate(preview_ids):
                    record = load_but_ppg_record(RAW_DIR / record_id)
                    processed = preprocess_ppg(record.waveform)
                    time = np.arange(record.waveform.size) / record.sampling_rate_hz
                    label = int(dataset.loc[dataset["ID"] == record_id, "Quality"].iloc[0])
                    axes[row_index, 0].plot(time, record.waveform, color="#142638")
                    axes[row_index, 0].set_title(f"{record_id} raw | label={label} | {record.selected_channel}")
                    axes[row_index, 1].plot(time, processed, color="#147D78")
                    axes[row_index, 1].set_title(f"{record_id} preprocessed")
                axes[-1, 0].set_xlabel("Seconds")
                axes[-1, 1].set_xlabel("Seconds")
                plt.tight_layout()
                """
            ),
            markdown(
                """
                ## Interpretation checklist

                Record observed imbalance, suspicious label or HR values, motion-related
                shifts, and visual differences between good and poor signals here. Do not
                convert these observations into test-set-driven modeling decisions.
                """
            ),
        ]
    )


def preprocessing_notebook() -> dict[str, Any]:
    return notebook(
        [
            markdown(
                """
                # 02 BUT PPG Preprocessing

                This notebook demonstrates the exact preprocessing contract used by the
                offline dataset builder and future FastAPI inference service.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                import json
                import subprocess
                import numpy as np
                import pandas as pd
                import matplotlib.pyplot as plt

                from app.services.preprocessing import (
                    PreprocessingConfig,
                    extract_signal_features,
                    load_but_ppg_record,
                    preprocess_ppg,
                )

                CONFIG = PreprocessingConfig()
                CONFIG.to_dict()
                """
            ),
            code(
                """
                record_ids = ["100001", "146014"]
                rows = []
                fig, axes = plt.subplots(len(record_ids), 2, figsize=(14, 6), sharex=True)

                for row_index, record_id in enumerate(record_ids):
                    record = load_but_ppg_record(RAW_DIR / record_id)
                    processed = preprocess_ppg(record.waveform, CONFIG)
                    features = extract_signal_features(record.waveform, processed, record.sampling_rate_hz)
                    rows.append({
                        "record_id": record_id,
                        "layout": record.source_layout,
                        "channel": record.selected_channel,
                        **features,
                    })
                    time = np.arange(record.waveform.size) / record.sampling_rate_hz
                    axes[row_index, 0].plot(time, record.waveform, color="#142638")
                    axes[row_index, 0].set_title(f"{record_id} raw | {record.source_layout}")
                    axes[row_index, 1].plot(time, processed, color="#35C4B5")
                    axes[row_index, 1].set_title(f"{record_id} filtered and normalized")

                plt.tight_layout()
                display(pd.DataFrame(rows).T)
                """
            ),
            code(
                """
                # First validate the complete path on a small subset.
                smoke_output = REPO_ROOT / "data" / "processed" / "but-ppg-notebook-smoke"
                command = [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "prepare_but_ppg.py"),
                    "--raw-dir", str(RAW_DIR),
                    "--output-dir", str(smoke_output),
                    "--limit", "100",
                ]
                subprocess.run(command, check=True)
                """
            ),
            code(
                """
                smoke_manifest = json.loads((smoke_output / "manifest.json").read_text())
                display(pd.DataFrame(smoke_manifest["split_summary"]).T)
                print("Failures:", smoke_manifest["records_failed"])
                """
            ),
            code(
                """
                # Change to True only after the smoke run succeeds.
                RUN_FULL_PREPROCESSING = False

                if RUN_FULL_PREPROCESSING:
                    full_command = [
                        sys.executable,
                        str(REPO_ROOT / "scripts" / "prepare_but_ppg.py"),
                        "--raw-dir", str(RAW_DIR),
                        "--output-dir", str(PROCESSED_DIR),
                    ]
                    subprocess.run(full_command, check=True)
                else:
                    print("Full preprocessing skipped. Set RUN_FULL_PREPROCESSING=True to run it.")
                """
            ),
            code(
                """
                if (PROCESSED_DIR / "manifest.json").exists():
                    manifest = json.loads((PROCESSED_DIR / "manifest.json").read_text())
                    display(pd.DataFrame(manifest["split_summary"]).T)
                    print("Processed:", manifest["records_processed"], "Failed:", manifest["records_failed"])
                else:
                    print("Run the full preprocessing cell before training.")
                """
            ),
        ]
    )


FEATURE_COLUMNS = [
    "raw_range",
    "raw_std",
    "derivative_rms",
    "derivative_std",
    "zero_crossing_rate",
    "clipping_ratio",
    "skewness",
    "excess_kurtosis",
    "spectral_entropy",
    "dominant_frequency_hz",
    "pulse_band_power_ratio",
    "peak_count",
    "peak_interval_cv",
]


def training_notebook() -> dict[str, Any]:
    feature_literal = repr(FEATURE_COLUMNS)
    return notebook(
        [
            markdown(
                """
                # 03 Train Signal Quality Baselines

                This notebook compares two fast, interpretable baselines using the
                subject-disjoint split produced in Stage 02. Test data remains untouched.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                import json
                import joblib
                import numpy as np
                import pandas as pd

                from sklearn.compose import ColumnTransformer
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.impute import SimpleImputer
                from sklearn.linear_model import LogisticRegression
                from sklearn.metrics import average_precision_score, balanced_accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
                from sklearn.pipeline import Pipeline
                from sklearn.preprocessing import StandardScaler

                features_path = PROCESSED_DIR / "features.csv"
                if not features_path.exists():
                    raise FileNotFoundError("Run notebook 02 or scripts/prepare_but_ppg.py first")
                frame = pd.read_csv(features_path)
                frame.groupby("split")["label_good_quality"].agg(["count", "mean", "sum"])
                """
            ),
            code(
                f"""
                FEATURE_COLUMNS = {feature_literal}
                TARGET = "label_good_quality"

                train = frame[frame["split"] == "train"].copy()
                validation = frame[frame["split"] == "validation"].copy()
                X_train, y_train = train[FEATURE_COLUMNS], train[TARGET].astype(int)
                X_validation, y_validation = validation[FEATURE_COLUMNS], validation[TARGET].astype(int)
                """
            ),
            code(
                """
                models = {
                    "logistic_regression": Pipeline([
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                        ("model", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=2026)),
                    ]),
                    "random_forest": Pipeline([
                        ("imputer", SimpleImputer(strategy="median")),
                        ("model", RandomForestClassifier(
                            n_estimators=400,
                            min_samples_leaf=3,
                            class_weight="balanced_subsample",
                            n_jobs=-1,
                            random_state=2026,
                        )),
                    ]),
                }

                def binary_metrics(y_true, probability, threshold=0.5):
                    prediction = (probability >= threshold).astype(int)
                    poor = y_true == 0
                    false_acceptance_rate = float(np.mean(prediction[poor] == 1))
                    return {
                        "precision_good": precision_score(y_true, prediction, zero_division=0),
                        "recall_good": recall_score(y_true, prediction, zero_division=0),
                        "f1_good": f1_score(y_true, prediction, zero_division=0),
                        "balanced_accuracy": balanced_accuracy_score(y_true, prediction),
                        "roc_auc": roc_auc_score(y_true, probability),
                        "average_precision": average_precision_score(y_true, probability),
                        "false_acceptance_rate_at_0_5": false_acceptance_rate,
                    }

                results = {}
                trained_models = {}
                for name, model in models.items():
                    model.fit(X_train, y_train)
                    probability = model.predict_proba(X_validation)[:, 1]
                    results[name] = binary_metrics(y_validation.to_numpy(), probability)
                    trained_models[name] = model

                results_frame = pd.DataFrame(results).T.sort_values(
                    ["false_acceptance_rate_at_0_5", "average_precision"],
                    ascending=[True, False],
                )
                display(results_frame)
                """
            ),
            code(
                """
                # Selection uses validation data only. Lower false acceptance is prioritized.
                selected_model_name = results_frame.index[0]
                candidate_directory = MODEL_DIR / "candidates"
                candidate_directory.mkdir(parents=True, exist_ok=True)
                for name, model in trained_models.items():
                    joblib.dump(model, candidate_directory / f"{name}.joblib")

                selection = {
                    "selected_model": selected_model_name,
                    "feature_columns": FEATURE_COLUMNS,
                    "seed": 2026,
                    "validation_metrics": results,
                    "selection_rule": "lowest validation false acceptance rate at 0.5, then highest average precision",
                }
                MODEL_DIR.mkdir(parents=True, exist_ok=True)
                (MODEL_DIR / "model_selection.json").write_text(json.dumps(selection, indent=2) + "\\n")
                selection
                """
            ),
        ]
    )


def evaluation_notebook() -> dict[str, Any]:
    return notebook(
        [
            markdown(
                """
                # 04 Evaluate the Reliability Gate

                This notebook selects two probability thresholds on validation data and
                evaluates the frozen policy once on the held-out test subjects.

                - Reliable: probability is at or above the upper threshold.
                - Caution: probability lies between both thresholds.
                - Unreliable: probability is at or below the lower threshold.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                import json
                import joblib
                import numpy as np
                import pandas as pd
                import matplotlib.pyplot as plt
                import seaborn as sns

                selection = json.loads((MODEL_DIR / "model_selection.json").read_text())
                FEATURE_COLUMNS = selection["feature_columns"]
                model_name = selection["selected_model"]
                model = joblib.load(MODEL_DIR / "candidates" / f"{model_name}.joblib")
                frame = pd.read_csv(PROCESSED_DIR / "features.csv")
                validation = frame[frame["split"] == "validation"].copy()
                test = frame[frame["split"] == "test"].copy()
                validation_probability = model.predict_proba(validation[FEATURE_COLUMNS])[:, 1]
                test_probability = model.predict_proba(test[FEATURE_COLUMNS])[:, 1]
                """
            ),
            code(
                """
                def gate_metrics(labels, probabilities, lower, upper):
                    labels = np.asarray(labels).astype(int)
                    probabilities = np.asarray(probabilities)
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

                labels_validation = validation["label_good_quality"].to_numpy()
                TARGET_FAR = 0.05
                TARGET_FRR = 0.05

                upper_candidates = []
                for upper in np.linspace(0.50, 0.99, 100):
                    metrics = gate_metrics(labels_validation, validation_probability, 0.0, upper)
                    upper_candidates.append(metrics)
                feasible_upper = [m for m in upper_candidates if m["false_acceptance_rate"] <= TARGET_FAR]
                if feasible_upper:
                    upper_threshold = max(feasible_upper, key=lambda m: m["good_acceptance_rate"])["upper_threshold"]
                else:
                    upper_threshold = min(upper_candidates, key=lambda m: (m["false_acceptance_rate"], -m["good_acceptance_rate"]))["upper_threshold"]

                lower_candidates = []
                for lower in np.linspace(0.01, min(0.49, upper_threshold - 0.01), 100):
                    metrics = gate_metrics(labels_validation, validation_probability, lower, upper_threshold)
                    lower_candidates.append(metrics)
                feasible_lower = [m for m in lower_candidates if m["false_rejection_rate"] <= TARGET_FRR]
                if feasible_lower:
                    lower_threshold = max(feasible_lower, key=lambda m: m["poor_rejection_rate"])["lower_threshold"]
                else:
                    lower_threshold = min(lower_candidates, key=lambda m: (m["false_rejection_rate"], -m["poor_rejection_rate"]))["lower_threshold"]

                validation_gate = gate_metrics(labels_validation, validation_probability, lower_threshold, upper_threshold)
                validation_gate
                """
            ),
            code(
                """
                labels_test = test["label_good_quality"].to_numpy()
                test_gate = gate_metrics(labels_test, test_probability, lower_threshold, upper_threshold)

                accepted = test_probability >= upper_threshold
                valid_hr = accepted & np.isfinite(test["estimated_bpm"]) & (test["estimated_bpm"] > 0)
                hr_mae = float(np.mean(np.abs(
                    test.loc[valid_hr, "estimated_bpm"] - test.loc[valid_hr, "reference_hr_bpm"]
                ))) if valid_hr.any() else None

                test_metrics = {
                    "model": model_name,
                    "validation_gate": validation_gate,
                    "test_gate": test_gate,
                    "accepted_signal_hr_mae_bpm": hr_mae,
                    "accepted_signal_hr_sample_count": int(valid_hr.sum()),
                    "limitations": [
                        "Thresholds are prototype validation-set decisions, not clinical standards.",
                        "BUT PPG labels are record-level and binary.",
                        "Caution represents model uncertainty, not a native dataset class.",
                    ],
                }
                display(pd.Series(test_gate).to_frame("test"))
                print("Accepted-signal HR MAE:", hr_mae)
                """
            ),
            code(
                """
                fig, axes = plt.subplots(1, 2, figsize=(13, 4))
                sns.histplot(x=test_probability, hue=test["label_good_quality"], bins=25, element="step", ax=axes[0])
                axes[0].axvline(lower_threshold, color="#E9C46A", linestyle="--", label="lower")
                axes[0].axvline(upper_threshold, color="#147D78", linestyle="--", label="upper")
                axes[0].set_title("Held-out probability distribution")
                axes[0].legend()

                states = np.where(test_probability >= upper_threshold, "Reliable", np.where(test_probability <= lower_threshold, "Unreliable", "Caution"))
                pd.Series(states).value_counts().reindex(["Reliable", "Caution", "Unreliable"]).plot(kind="bar", ax=axes[1], color=["#35C4B5", "#E9C46A", "#E76F51"])
                axes[1].set_title("Held-out quality-gate decisions")
                axes[1].set_ylabel("Records")
                plt.tight_layout()
                """
            ),
            code(
                """
                thresholds = {
                    "model": model_name,
                    "lower_threshold": float(lower_threshold),
                    "upper_threshold": float(upper_threshold),
                    "quality_score_definition": "round(100 * good_quality_probability)",
                    "status_policy": {
                        "reliable": "probability >= upper_threshold",
                        "caution": "lower_threshold < probability < upper_threshold",
                        "unreliable": "probability <= lower_threshold",
                    },
                }
                MODEL_DIR.mkdir(parents=True, exist_ok=True)
                (MODEL_DIR / "quality_gate_thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\\n")
                (MODEL_DIR / "test_metrics.json").write_text(json.dumps(test_metrics, indent=2) + "\\n")
                thresholds
                """
            ),
        ]
    )


def main() -> None:
    NOTEBOOK_DIRECTORY.mkdir(parents=True, exist_ok=True)
    notebooks = {
        "01_eda_but_ppg.ipynb": eda_notebook(),
        "02_preprocessing_but_ppg.ipynb": preprocessing_notebook(),
        "03_train_baselines.ipynb": training_notebook(),
        "04_evaluate_quality_gate.ipynb": evaluation_notebook(),
    }
    for filename, payload in notebooks.items():
        path = NOTEBOOK_DIRECTORY / filename
        path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
