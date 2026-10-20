#!/usr/bin/env python3
"""Prepare waveform, STFT, and SQI representations for the PURE V3 ensemble."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.services.preprocessing import load_but_ppg_record  # noqa: E402
from app.services.v3_preprocessing import (  # noqa: E402
    V3PreprocessingConfig,
    create_log_stft,
    extract_v3_sqi_features,
    preprocess_ppg_fdp_sdp,
)
from prepare_but_ppg import create_subject_splits, read_csv_by_id  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "raw" / "but-ppg-2.0.0",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "processed" / "but-ppg-v3",
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    raw_dir = args.raw_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    annotations = read_csv_by_id(raw_dir / "quality-hr-ann.csv")
    subject_information = read_csv_by_id(raw_dir / "subject-info.csv")
    available = sorted(
        record_id
        for record_id in annotations
        if (raw_dir / record_id / f"{record_id}_PPG.hea").exists()
    )
    if args.limit is not None:
        available = available[: args.limit]
    subject_to_split, split_subjects = create_subject_splits(
        available,
        train_fraction=0.70,
        validation_fraction=0.15,
        seed=args.seed,
    )

    waveform_views: list[np.ndarray] = []
    spectrograms: list[np.ndarray] = []
    feature_rows: list[list[float]] = []
    feature_names: list[str] | None = None
    labels: list[int] = []
    record_ids: list[str] = []
    subject_ids: list[str] = []
    original_splits: list[str] = []
    measurement_spots: list[str] = []
    motions: list[str] = []
    channels: list[str] = []
    failures: list[dict[str, str]] = []
    base_config = V3PreprocessingConfig()

    for record_id in available:
        try:
            record = load_but_ppg_record(raw_dir / record_id)
            config = V3PreprocessingConfig(
                sampling_rate_hz=record.sampling_rate_hz,
                low_cut_hz=base_config.low_cut_hz,
                high_cut_hz=base_config.high_cut_hz,
                filter_order=base_config.filter_order,
                stft_window_samples=base_config.stft_window_samples,
                stft_overlap_samples=base_config.stft_overlap_samples,
                stft_fft_samples=base_config.stft_fft_samples,
                epsilon=base_config.epsilon,
            )
            views = preprocess_ppg_fdp_sdp(record.waveform, config)
            spectrogram = create_log_stft(views[0], config)
            features = extract_v3_sqi_features(
                raw_waveform=record.waveform,
                views=views,
                sampling_rate_hz=record.sampling_rate_hz,
                epsilon=config.epsilon,
            )
            if feature_names is None:
                feature_names = list(features)
            elif list(features) != feature_names:
                raise RuntimeError("SQI feature order changed between records")

            info = subject_information.get(record_id, {})
            waveform_views.append(views)
            spectrograms.append(spectrogram)
            feature_rows.append(list(features.values()))
            labels.append(int(annotations[record_id]["Quality"]))
            record_ids.append(record_id)
            subject_ids.append(record_id[:3])
            original_splits.append(subject_to_split[record_id[:3]])
            measurement_spots.append(info.get("Ear/finger", ""))
            motions.append(info.get("Motion", ""))
            channels.append(record.selected_channel)
        except Exception as error:
            failures.append({"record_id": record_id, "error": str(error)})

    if not waveform_views or feature_names is None:
        raise RuntimeError("No V3 records were prepared")
    if failures:
        raise RuntimeError(f"V3 preprocessing failed for {len(failures)} records: {failures[:3]}")

    X_waveform = np.stack(waveform_views).astype(np.float32)
    X_stft = np.stack(spectrograms).astype(np.float32)
    X_sqi = np.asarray(feature_rows, dtype=np.float32)
    y = np.asarray(labels, dtype=np.int64)
    split = np.asarray(original_splits)
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_dir / "v3_representations.npz",
        X_waveform=X_waveform,
        X_stft=X_stft,
        X_sqi=X_sqi,
        y=y,
        record_id=np.asarray(record_ids),
        subject_id=np.asarray(subject_ids),
        original_split=split,
        measurement_spot=np.asarray(measurement_spots),
        motion=np.asarray(motions),
        selected_channel=np.asarray(channels),
        sqi_feature_names=np.asarray(feature_names),
    )

    split_summary = {}
    for split_name in ("train", "validation", "test"):
        mask = split == split_name
        split_summary[split_name] = {
            "records": int(mask.sum()),
            "subjects": int(np.unique(np.asarray(subject_ids)[mask]).size),
            "good": int(y[mask].sum()),
            "poor": int(mask.sum() - y[mask].sum()),
        }
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "BUT PPG v2.0.0",
        "records": int(y.size),
        "waveform_shape": list(X_waveform.shape),
        "waveform_view_order": ["filtered_ppg", "first_derivative", "second_derivative"],
        "stft_shape": list(X_stft.shape),
        "sqi_shape": list(X_sqi.shape),
        "sqi_feature_names": feature_names,
        "preprocessing": base_config.to_dict(),
        "channel_policy": "PPG_R matches the annotated BUT PPG channel",
        "development_policy": "original train + validation subjects; original test subjects remain audit-only",
        "split_subjects": split_subjects,
        "split_summary": split_summary,
        "seed": args.seed,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
