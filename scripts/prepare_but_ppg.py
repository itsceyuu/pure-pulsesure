#!/usr/bin/env python3
"""Prepare BUT PPG v2 for PURE baseline training and demo playback."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.services.preprocessing import (  # noqa: E402
    PreprocessingConfig,
    extract_signal_features,
    load_but_ppg_record,
    preprocess_ppg,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize BUT PPG waveform layouts, create subject-wise splits, "
            "extract baseline features, and export a small real-signal demo set."
        )
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "raw" / "but-ppg-2.0.0",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "processed" / "but-ppg-v2",
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional record limit for a quick smoke test.",
    )
    parser.add_argument("--demo-records-per-class", type=int, default=2)
    return parser.parse_args()


def read_csv_by_id(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        return {str(row["ID"]).strip(): dict(row) for row in rows}


def create_subject_splits(
    record_ids: list[str],
    train_fraction: float,
    validation_fraction: float,
    seed: int,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    if train_fraction <= 0 or validation_fraction <= 0:
        raise ValueError("Training and validation fractions must be positive")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Training + validation fractions must be below 1")

    subjects = sorted({record_id[:3] for record_id in record_ids})
    rng = np.random.default_rng(seed)
    rng.shuffle(subjects)

    subject_count = len(subjects)
    if subject_count < 3:
        raise ValueError("At least three distinct subjects are required for subject-wise splits")
    train_count = max(1, int(round(subject_count * train_fraction)))
    validation_count = max(1, int(round(subject_count * validation_fraction)))
    if train_count + validation_count >= subject_count:
        validation_count = max(1, subject_count - train_count - 1)

    split_subjects = {
        "train": sorted(subjects[:train_count]),
        "validation": sorted(subjects[train_count : train_count + validation_count]),
        "test": sorted(subjects[train_count + validation_count :]),
    }
    subject_to_split = {
        subject: split
        for split, split_values in split_subjects.items()
        for subject in split_values
    }
    return subject_to_split, split_subjects


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split in ("train", "validation", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        labels = [int(row["label_good_quality"]) for row in split_rows]
        summary[split] = {
            "records": len(split_rows),
            "subjects": len({row["subject_id"] for row in split_rows}),
            "good_quality": int(sum(labels)),
            "poor_quality": int(len(labels) - sum(labels)),
            "good_quality_fraction": float(np.mean(labels)) if labels else None,
        }
    return summary


def main() -> int:
    args = parse_arguments()
    raw_dir = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    annotation_path = raw_dir / "quality-hr-ann.csv"
    subject_info_path = raw_dir / "subject-info.csv"
    if not annotation_path.exists():
        raise FileNotFoundError(f"Missing annotation file: {annotation_path}")

    annotations = read_csv_by_id(annotation_path)
    subject_information = read_csv_by_id(subject_info_path) if subject_info_path.exists() else {}
    available_records = sorted(
        record_id
        for record_id in annotations
        if (raw_dir / record_id / f"{record_id}_PPG.hea").exists()
    )
    if args.limit is not None:
        available_records = available_records[: args.limit]
    if len(available_records) < 3:
        raise ValueError("At least three records are required to create train/validation/test splits")

    subject_to_split, split_subjects = create_subject_splits(
        available_records,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
        seed=args.seed,
    )
    config = PreprocessingConfig()
    feature_rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    demo_candidates: dict[int, list[dict[str, Any]]] = {0: [], 1: []}

    for record_id in available_records:
        try:
            record = load_but_ppg_record(raw_dir / record_id)
            record_config = PreprocessingConfig(
                sampling_rate_hz=record.sampling_rate_hz,
                low_cut_hz=config.low_cut_hz,
                high_cut_hz=config.high_cut_hz,
                epsilon=config.epsilon,
            )
            processed = preprocess_ppg(record.waveform, record_config)
            features = extract_signal_features(
                raw_waveform=record.waveform,
                processed_waveform=processed,
                sampling_rate_hz=record.sampling_rate_hz,
            )
            annotation = annotations[record_id]
            subject_info = subject_information.get(record_id, {})
            label = int(annotation["Quality"])
            row: dict[str, Any] = {
                "record_id": record_id,
                "subject_id": record_id[:3],
                "split": subject_to_split[record_id[:3]],
                "label_good_quality": label,
                "reference_hr_bpm": float(annotation["HR"]),
                "sampling_rate_hz": record.sampling_rate_hz,
                "sample_count": int(record.waveform.size),
                "selected_channel": record.selected_channel,
                "source_layout": record.source_layout,
                "motion": subject_info.get("Motion", ""),
                "has_acc": int((raw_dir / record_id / f"{record_id}_ACC.hea").exists()),
                **features,
            }
            feature_rows.append(row)

            if (
                row["split"] == "test"
                and len(demo_candidates[label]) < args.demo_records_per_class
            ):
                demo_candidates[label].append(
                    {
                        "record_id": record_id,
                        "subject_id": record_id[:3],
                        "label_good_quality": label,
                        "reference_hr_bpm": float(annotation["HR"]),
                        "sampling_rate_hz": record.sampling_rate_hz,
                        "selected_channel": record.selected_channel,
                        "source": "BUT PPG v2.0.0",
                        "waveform": [round(float(value), 6) for value in processed],
                    }
                )
        except Exception as error:  # keep the batch auditable instead of silently stopping
            failures.append({"record_id": record_id, "error": str(error)})

    if not feature_rows:
        raise RuntimeError("No BUT PPG records were processed successfully")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "features.csv", feature_rows)
    if failures:
        write_csv(output_dir / "failures.csv", failures)

    summary = summarize_rows(feature_rows)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "Brno University of Technology Smartphone PPG Database",
        "dataset_version": "2.0.0",
        "dataset_url": "https://physionet.org/content/butppg/2.0.0/",
        "license": "Creative Commons Attribution 4.0 International",
        "seed": args.seed,
        "preprocessing": config.to_dict(),
        "records_available": len(available_records),
        "records_processed": len(feature_rows),
        "records_failed": len(failures),
        "split_summary": summary,
        "label_semantics": {
            "1": "good quality for heart-rate estimation",
            "0": "poor quality; heart rate cannot be detected reliably",
        },
        "notes": [
            "Splits are subject-disjoint using the first three record-ID digits.",
            "Caution is not a dataset label; it must be derived from model uncertainty thresholds.",
            "The exported quality label is record-level, not a temporal artifact annotation.",
        ],
    }
    write_json(output_dir / "manifest.json", manifest)
    write_json(output_dir / "splits.json", split_subjects)
    write_json(output_dir / "preprocessing_config.json", config.to_dict())

    demo_dir = output_dir / "demo_records"
    for label, candidates in demo_candidates.items():
        status = "reliable" if label == 1 else "unreliable"
        for index, payload in enumerate(candidates, start=1):
            write_json(demo_dir / f"{status}_{index}_{payload['record_id']}.json", payload)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
