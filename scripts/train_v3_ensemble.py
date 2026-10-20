#!/usr/bin/env python3
"""Train the V3 subject-wise waveform, STFT, and SQI ensemble."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import sys
import time

import joblib
import numpy as np
import torch
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, Dataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.models.v3_models import (  # noqa: E402
    CompactPPGQualityCNN,
    CompactSTFTQualityCNN,
    parameter_count,
)
from app.services.model_evaluation import (  # noqa: E402
    PlattCalibrator,
    binary_metrics,
    choose_binary_threshold,
    choose_gate_thresholds,
)


@dataclass(frozen=True)
class TrainConfig:
    epochs: int
    patience: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    seed: int


class IndexedArrayDataset(Dataset):
    def __init__(self, inputs: np.ndarray, labels: np.ndarray, indices: np.ndarray) -> None:
        self.inputs = inputs
        self.labels = labels
        self.indices = np.asarray(indices)

    def __len__(self) -> int:
        return int(self.indices.size)

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor]:
        index = int(self.indices[item])
        return torch.from_numpy(self.inputs[index]), torch.tensor(self.labels[index], dtype=torch.float32)


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
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=2026)
    return parser.parse_args()


def choose_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def predict_probabilities(
    model: nn.Module,
    inputs: np.ndarray,
    labels: np.ndarray,
    indices: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = DataLoader(
        IndexedArrayDataset(inputs, labels, indices),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    logits: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for batch_inputs, _ in loader:
            logits.append(model(batch_inputs.to(device)).cpu().numpy())
    combined = np.concatenate(logits)
    return 1.0 / (1.0 + np.exp(-np.clip(combined, -30, 30)))


def train_torch_branch(
    model: nn.Module,
    inputs: np.ndarray,
    labels: np.ndarray,
    train_indices: np.ndarray,
    validation_indices: np.ndarray,
    checkpoint_path: Path,
    config: TrainConfig,
    device: torch.device,
) -> dict:
    set_seed(config.seed)
    model = model.to(device)
    train_labels = labels[train_indices]
    negative_count = float(np.sum(train_labels == 0))
    positive_count = float(np.sum(train_labels == 1))
    soft_positive_weight = math.sqrt(negative_count / max(positive_count, 1.0))
    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor([soft_positive_weight], dtype=torch.float32, device=device)
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=3,
        min_lr=1e-6,
    )
    train_loader = DataLoader(
        IndexedArrayDataset(inputs, labels, train_indices),
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
        generator=torch.Generator().manual_seed(config.seed),
    )

    best_auc = -np.inf
    best_epoch = 0
    epochs_without_improvement = 0
    history: list[dict] = []
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, config.epochs + 1):
        model.train()
        losses: list[float] = []
        for batch_inputs, batch_labels in train_loader:
            batch_inputs = batch_inputs.to(device)
            batch_labels = batch_labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(batch_inputs), batch_labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            losses.append(float(loss.item()))

        probability = predict_probabilities(
            model,
            inputs,
            labels,
            validation_indices,
            config.batch_size * 2,
            device,
        )
        validation_auc = float(roc_auc_score(labels[validation_indices], probability))
        scheduler.step(validation_auc)
        history.append(
            {
                "epoch": epoch,
                "loss": float(np.mean(losses)),
                "validation_auc": validation_auc,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
            }
        )
        if validation_auc > best_auc + 1e-4:
            best_auc = validation_auc
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(model.state_dict(), checkpoint_path)
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                break

    model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True))
    validation_probability = predict_probabilities(
        model,
        inputs,
        labels,
        validation_indices,
        config.batch_size * 2,
        device,
    )
    return {
        "probability": validation_probability,
        "best_auc": best_auc,
        "best_epoch": best_epoch,
        "epochs_completed": len(history),
        "positive_weight": soft_positive_weight,
        "parameter_count": parameter_count(model),
    }


def main() -> int:
    args = parse_arguments()
    input_dir = args.input_dir.expanduser().resolve()
    model_dir = args.model_dir.expanduser().resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    archive = np.load(input_dir / "v3_representations.npz")
    X_waveform = archive["X_waveform"].astype(np.float32)
    X_stft = archive["X_stft"].astype(np.float32)
    X_sqi = archive["X_sqi"].astype(np.float32)
    labels = archive["y"].astype(int)
    subjects = archive["subject_id"].astype(str)
    original_split = archive["original_split"].astype(str)

    development_global = np.flatnonzero(original_split != "test")
    y_development = labels[development_global]
    groups_development = subjects[development_global]
    splitter = StratifiedGroupKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
    fold_pairs = list(splitter.split(np.zeros(y_development.size), y_development, groups_development))
    device = choose_device()
    print(f"Device: {device}; development records: {development_global.size}; folds: {args.folds}")

    oof_waveform = np.full(y_development.size, np.nan, dtype=np.float64)
    oof_stft = np.full(y_development.size, np.nan, dtype=np.float64)
    oof_sqi = np.full(y_development.size, np.nan, dtype=np.float64)
    fold_reports: list[dict] = []
    started = time.time()

    for fold_index, (train_local, validation_local) in enumerate(fold_pairs, start=1):
        train_global = development_global[train_local]
        validation_global = development_global[validation_local]
        train_subjects = sorted(set(subjects[train_global]))
        validation_subjects = sorted(set(subjects[validation_global]))
        if set(train_subjects) & set(validation_subjects):
            raise RuntimeError("Subject leakage detected in V3 fold")
        print(
            f"Fold {fold_index}/{args.folds}: train={train_global.size}, "
            f"validation={validation_global.size}, validation_subjects={validation_subjects}"
        )
        config = TrainConfig(
            epochs=args.epochs,
            patience=args.patience,
            batch_size=args.batch_size,
            learning_rate=1e-4,
            weight_decay=1e-5,
            seed=args.seed + fold_index,
        )
        set_seed(config.seed)
        waveform_result = train_torch_branch(
            CompactPPGQualityCNN(),
            X_waveform,
            labels,
            train_global,
            validation_global,
            model_dir / f"waveform_fold_{fold_index}.pt",
            config,
            device,
        )
        oof_waveform[validation_local] = waveform_result.pop("probability")

        set_seed(config.seed + 10_000)
        stft_result = train_torch_branch(
            CompactSTFTQualityCNN(),
            X_stft,
            labels,
            train_global,
            validation_global,
            model_dir / f"stft_fold_{fold_index}.pt",
            config,
            device,
        )
        oof_stft[validation_local] = stft_result.pop("probability")

        negative_count = float(np.sum(labels[train_global] == 0))
        positive_count = float(np.sum(labels[train_global] == 1))
        positive_weight = math.sqrt(negative_count / max(positive_count, 1.0))
        sample_weight = np.where(labels[train_global] == 1, positive_weight, 1.0)
        sqi_model = ExtraTreesClassifier(
            n_estimators=600,
            min_samples_leaf=3,
            max_features="sqrt",
            n_jobs=-1,
            random_state=args.seed + fold_index,
        )
        sqi_model.fit(X_sqi[train_global], labels[train_global], sample_weight=sample_weight)
        joblib.dump(sqi_model, model_dir / f"sqi_fold_{fold_index}.joblib")
        oof_sqi[validation_local] = sqi_model.predict_proba(X_sqi[validation_global])[:, 1]

        fold_reports.append(
            {
                "fold": fold_index,
                "train_subjects": train_subjects,
                "validation_subjects": validation_subjects,
                "train_records": int(train_global.size),
                "validation_records": int(validation_global.size),
                "waveform": waveform_result,
                "stft": stft_result,
            }
        )
        print(
            f"  AUC waveform={waveform_result['best_auc']:.4f}, "
            f"STFT={stft_result['best_auc']:.4f}"
        )

    if not (
        np.isfinite(oof_waveform).all()
        and np.isfinite(oof_stft).all()
        and np.isfinite(oof_sqi).all()
    ):
        raise RuntimeError("OOF predictions are incomplete")

    branch_probabilities = np.column_stack([oof_waveform, oof_stft, oof_sqi])
    raw_ensemble_probability = np.mean(branch_probabilities, axis=1)
    calibrator = PlattCalibrator(l2_strength=1.0).fit(
        raw_ensemble_probability,
        y_development,
    )
    calibrated_oof = calibrator.predict_proba(raw_ensemble_probability)[:, 1]
    joblib.dump(calibrator, model_dir / "ensemble_calibrator.joblib")

    binary_threshold, oof_binary = choose_binary_threshold(y_development, calibrated_oof)
    lower_threshold, upper_threshold, oof_gate = choose_gate_thresholds(
        y_development,
        calibrated_oof,
        binary_threshold,
    )
    branch_metrics = {}
    for name, probability in {
        "waveform": oof_waveform,
        "stft": oof_stft,
        "sqi": oof_sqi,
        "raw_equal_weight_ensemble": raw_ensemble_probability,
    }.items():
        branch_threshold, metrics = choose_binary_threshold(y_development, probability)
        branch_metrics[name] = {"selected_threshold": branch_threshold, **metrics}

    thresholds = {
        "binary_threshold": binary_threshold,
        "lower_threshold": lower_threshold,
        "upper_threshold": upper_threshold,
        "branch_fusion": "equal mean of waveform, STFT, and SQI probabilities",
        "calibration": "Platt logistic calibration fitted to subject-wise OOF ensemble scores",
        "quality_score_definition": "round(100 * calibrated ensemble score)",
        "status_policy": {
            "reliable": "score >= upper_threshold",
            "caution": "lower_threshold < score < upper_threshold",
            "unreliable": "score <= lower_threshold",
        },
    }
    metadata = {
        "model": "PURE V3 subject-wise ensemble",
        "folds": args.folds,
        "development_records": int(development_global.size),
        "development_subjects": int(np.unique(groups_development).size),
        "audit_test_subjects_excluded": sorted(set(subjects[original_split == "test"])),
        "waveform_input": ["filtered_ppg", "first_derivative", "second_derivative"],
        "stft_input_shape": list(X_stft.shape[1:]),
        "sqi_feature_names": archive["sqi_feature_names"].astype(str).tolist(),
        "soft_class_weight_policy": "sqrt(poor/good) within each fold",
        "elapsed_seconds": float(time.time() - started),
    }
    report = {
        "oof_binary": oof_binary,
        "oof_gate": oof_gate,
        "branch_oof_metrics": branch_metrics,
        "folds": fold_reports,
        "note": "OOF metrics are primary development estimates; the original test subjects remain audit-only.",
    }
    np.savez_compressed(
        model_dir / "oof_predictions.npz",
        record_id=archive["record_id"][development_global],
        subject_id=groups_development,
        y=y_development,
        waveform_probability=oof_waveform,
        stft_probability=oof_stft,
        sqi_probability=oof_sqi,
        ensemble_probability=calibrated_oof,
    )
    (model_dir / "thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n")
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (model_dir / "oof_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"oof_binary": oof_binary, "oof_gate": oof_gate}, indent=2))
    print(f"Saved V3 ensemble to {model_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
