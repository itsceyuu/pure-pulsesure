#!/usr/bin/env python3
"""Export subject-disjoint, waveform-level BUT PPG arrays for temporal models."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.services.preprocessing import load_but_ppg_record  # noqa: E402
from app.services.waveform_preprocessing import (  # noqa: E402
    WaveformPreprocessingConfig,
    preprocess_waveform_views,
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
        default=REPOSITORY_ROOT / "data" / "processed" / "but-ppg-waveforms-v2",
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    raw_dir = args.raw_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    annotations = read_csv_by_id(raw_dir / "quality-hr-ann.csv")
    available = sorted(
        record_id
        for record_id in annotations
        if (raw_dir / record_id / f"{record_id}_PPG.hea").exists()
    )
    if args.limit is not None:
        available = available[: args.limit]

    subject_to_split, split_subjects = create_subject_splits(
        available,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
        seed=args.seed,
    )

    waveforms: list[np.ndarray] = []
    labels: list[int] = []
    record_ids: list[str] = []
    subject_ids: list[str] = []
    splits: list[str] = []
    selected_channels: list[str] = []
    reference_hr: list[float] = []
    failures: list[dict[str, str]] = []

    base_config = WaveformPreprocessingConfig()
    for record_id in available:
        try:
            record = load_but_ppg_record(raw_dir / record_id)
            record_config = WaveformPreprocessingConfig(
                sampling_rate_hz=record.sampling_rate_hz,
                low_cut_hz=base_config.low_cut_hz,
                high_cut_hz=base_config.high_cut_hz,
                filter_order=base_config.filter_order,
                robust_clip=base_config.robust_clip,
                epsilon=base_config.epsilon,
            )
            waveforms.append(preprocess_waveform_views(record.waveform, record_config))
            labels.append(int(annotations[record_id]["Quality"]))
            record_ids.append(record_id)
            subject_ids.append(record_id[:3])
            splits.append(subject_to_split[record_id[:3]])
            selected_channels.append(record.selected_channel)
            reference_hr.append(float(annotations[record_id]["HR"]))
        except Exception as error:
            failures.append({"record_id": record_id, "error": str(error)})

    if not waveforms:
        raise RuntimeError("No waveforms were exported")

    shapes = {waveform.shape for waveform in waveforms}
    if len(shapes) != 1:
        raise ValueError(f"Expected a common waveform shape, found: {sorted(shapes)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_dir / "waveforms.npz",
        X=np.stack(waveforms),
        y=np.asarray(labels, dtype=np.int64),
        record_id=np.asarray(record_ids),
        subject_id=np.asarray(subject_ids),
        split=np.asarray(splits),
        selected_channel=np.asarray(selected_channels),
        reference_hr_bpm=np.asarray(reference_hr, dtype=np.float32),
    )

    split_summary = {}
    split_array = np.asarray(splits)
    label_array = np.asarray(labels)
    subject_array = np.asarray(subject_ids)
    for split_name in ("train", "validation", "test"):
        mask = split_array == split_name
        split_summary[split_name] = {
            "records": int(mask.sum()),
            "subjects": int(np.unique(subject_array[mask]).size),
            "good_quality": int(label_array[mask].sum()),
            "poor_quality": int(mask.sum() - label_array[mask].sum()),
        }

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "BUT PPG v2.0.0",
        "source_url": "https://physionet.org/content/butppg/2.0.0/",
        "array_shape": list(np.stack(waveforms).shape),
        "view_order": ["raw_robust", "butterworth_bandpass", "first_derivative"],
        "annotated_channel_policy": "PPG_R, then PPG_G/PPG_B only as fallback",
        "preprocessing": base_config.to_dict(),
        "seed": args.seed,
        "split_subjects": split_subjects,
        "split_summary": split_summary,
        "records_failed": len(failures),
        "warnings": [
            "Quality labels are binary and apply to the full ten-second record.",
            "Do not create overlapping train/test windows from the same subject.",
            "Smartphone camera PPG differs from the proposed MAX30102 deployment domain.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if failures:
        with (output_dir / "failures.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["record_id", "error"])
            writer.writeheader()
            writer.writerows(failures)
    else:
        (output_dir / "failures.csv").unlink(missing_ok=True)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

