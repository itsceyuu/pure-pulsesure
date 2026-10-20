#!/usr/bin/env python3
"""Evaluate the frozen V3 ensemble on the original audit subjects."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.models.v3_models import CompactPPGQualityCNN, CompactSTFTQualityCNN  # noqa: E402
from app.services.model_evaluation import binary_metrics, gate_metrics  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "processed" / "but-ppg-v3",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=REPOSITORY_ROOT / "models" / "production" / "v3",
    )
    parser.add_argument("--batch-size", type=int, default=128)
    return parser.parse_args()


def choose_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def predict_torch(
    model: torch.nn.Module,
    inputs: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = DataLoader(
        TensorDataset(torch.from_numpy(inputs)),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    logits: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for (batch_inputs,) in loader:
            logits.append(model(batch_inputs.to(device)).cpu().numpy())
    combined = np.concatenate(logits)
    return 1.0 / (1.0 + np.exp(-np.clip(combined, -30, 30)))


def simple_group_metrics(labels: np.ndarray, predictions: np.ndarray, values: np.ndarray) -> dict:
    result = {}
    for value in sorted(set(values.astype(str))):
        mask = values.astype(str) == value
        group_labels = labels[mask]
        group_predictions = predictions[mask]
        good = group_labels == 1
        poor = group_labels == 0
        result[value] = {
            "records": int(mask.sum()),
            "good": int(good.sum()),
            "poor": int(poor.sum()),
            "accuracy": float(np.mean(group_predictions == group_labels)),
            "recall_good": float(np.mean(group_predictions[good] == 1)) if np.any(good) else None,
            "specificity_poor": float(np.mean(group_predictions[poor] == 0)) if np.any(poor) else None,
            "false_acceptance_rate": float(np.mean(group_predictions[poor] == 1)) if np.any(poor) else None,
        }
    return result


def main() -> int:
    args = parse_arguments()
    input_dir = args.input_dir.expanduser().resolve()
    model_dir = args.model_dir.expanduser().resolve()
    archive = np.load(input_dir / "v3_representations.npz")
    original_split = archive["original_split"].astype(str)
    test_indices = np.flatnonzero(original_split == "test")
    labels = archive["y"][test_indices].astype(int)
    X_waveform = archive["X_waveform"][test_indices].astype(np.float32)
    X_stft = archive["X_stft"][test_indices].astype(np.float32)
    X_sqi = archive["X_sqi"][test_indices].astype(np.float32)
    device = choose_device()
    metadata = json.loads((model_dir / "metadata.json").read_text())
    folds = int(metadata["folds"])

    waveform_fold_probabilities: list[np.ndarray] = []
    stft_fold_probabilities: list[np.ndarray] = []
    sqi_fold_probabilities: list[np.ndarray] = []
    for fold_index in range(1, folds + 1):
        waveform_model = CompactPPGQualityCNN().to(device)
        waveform_model.load_state_dict(
            torch.load(model_dir / f"waveform_fold_{fold_index}.pt", map_location=device, weights_only=True)
        )
        waveform_fold_probabilities.append(
            predict_torch(waveform_model, X_waveform, args.batch_size, device)
        )

        stft_model = CompactSTFTQualityCNN().to(device)
        stft_model.load_state_dict(
            torch.load(model_dir / f"stft_fold_{fold_index}.pt", map_location=device, weights_only=True)
        )
        stft_fold_probabilities.append(predict_torch(stft_model, X_stft, args.batch_size, device))

        sqi_model = joblib.load(model_dir / f"sqi_fold_{fold_index}.joblib")
        sqi_fold_probabilities.append(sqi_model.predict_proba(X_sqi)[:, 1])

    waveform_probability = np.mean(np.stack(waveform_fold_probabilities), axis=0)
    stft_probability = np.mean(np.stack(stft_fold_probabilities), axis=0)
    sqi_probability = np.mean(np.stack(sqi_fold_probabilities), axis=0)
    raw_ensemble = np.mean(
        np.column_stack([waveform_probability, stft_probability, sqi_probability]),
        axis=1,
    )
    calibrator = joblib.load(model_dir / "ensemble_calibrator.joblib")
    ensemble_probability = calibrator.predict_proba(raw_ensemble)[:, 1]

    thresholds = json.loads((model_dir / "thresholds.json").read_text())
    binary_threshold = float(thresholds["binary_threshold"])
    lower_threshold = float(thresholds["lower_threshold"])
    upper_threshold = float(thresholds["upper_threshold"])
    test_binary = binary_metrics(labels, ensemble_probability, binary_threshold)
    test_gate = gate_metrics(labels, ensemble_probability, lower_threshold, upper_threshold)
    predictions = (ensemble_probability >= binary_threshold).astype(int)
    states = np.where(
        ensemble_probability >= upper_threshold,
        "Reliable",
        np.where(ensemble_probability <= lower_threshold, "Unreliable", "Caution"),
    )
    reliable = states == "Reliable"
    reliable_precision = (
        float(np.mean(labels[reliable] == 1)) if np.any(reliable) else None
    )

    oof_report = json.loads((model_dir / "oof_metrics.json").read_text())
    branch_test_metrics = {}
    for name, probability in {
        "waveform": waveform_probability,
        "stft": stft_probability,
        "sqi": sqi_probability,
    }.items():
        threshold = float(oof_report["branch_oof_metrics"][name]["selected_threshold"])
        branch_test_metrics[name] = binary_metrics(labels, probability, threshold)

    report = {
        "test_binary": test_binary,
        "test_gate": test_gate,
        "reliable_precision": reliable_precision,
        "branch_test_metrics": branch_test_metrics,
        "test_records": int(labels.size),
        "test_subjects": int(np.unique(archive["subject_id"][test_indices]).size),
        "by_measurement_spot": simple_group_metrics(
            labels,
            predictions,
            archive["measurement_spot"][test_indices],
        ),
        "by_motion": simple_group_metrics(labels, predictions, archive["motion"][test_indices]),
        "limitations": [
            "These original test subjects were previously inspected during V2 development and are now an audit set.",
            "Primary development evidence is the subject-wise OOF result in oof_metrics.json.",
            "BUT PPG smartphone-camera measurements do not replace MAX30102 domain validation.",
        ],
    }
    (model_dir / "test_metrics.json").write_text(json.dumps(report, indent=2) + "\n")

    with (model_dir / "test_predictions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "record_id",
                "subject_id",
                "label_good_quality",
                "waveform_probability",
                "stft_probability",
                "sqi_probability",
                "ensemble_probability",
                "binary_prediction",
                "quality_state",
            ]
        )
        for row in zip(
            archive["record_id"][test_indices],
            archive["subject_id"][test_indices],
            labels,
            waveform_probability,
            stft_probability,
            sqi_probability,
            ensemble_probability,
            predictions,
            states,
        ):
            writer.writerow(row)
    print(json.dumps({"test_binary": test_binary, "test_gate": test_gate, "reliable_precision": reliable_precision}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
