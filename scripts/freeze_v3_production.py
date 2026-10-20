#!/usr/bin/env python3
"""Create an immutable local deployment bundle from the trained V3 ensemble."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "apps" / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))

from app.services.v3_preprocessing import V3PreprocessingConfig  # noqa: E402


FOLD_ARTIFACT_PATTERNS = (
    "waveform_fold_{fold}.pt",
    "stft_fold_{fold}.pt",
    "sqi_fold_{fold}.joblib",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=REPOSITORY_ROOT / "models" / "production" / "v3",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "models" / "production" / "frozen" / "v3-ensemble",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify hashes in an existing bundle instead of creating it.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(output_dir: Path) -> None:
    checksums_path = output_dir / "artifact_checksums.json"
    checksums = json.loads(checksums_path.read_text())
    errors: list[str] = []
    for relative_path, expected in checksums["sha256"].items():
        path = output_dir / relative_path
        if not path.is_file():
            errors.append(f"missing: {relative_path}")
        elif sha256(path) != expected:
            errors.append(f"checksum mismatch: {relative_path}")
    if errors:
        raise RuntimeError("Frozen bundle verification failed: " + "; ".join(errors))
    print(f"Verified {len(checksums['sha256'])} frozen artifacts in {output_dir}")


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    args = parse_arguments()
    source_dir = args.source_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if args.verify_only:
        verify_bundle(output_dir)
        return 0
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to replace frozen bundle {output_dir}. "
            "Use a new versioned directory if the model changes."
        )

    metadata = json.loads((source_dir / "metadata.json").read_text())
    fold_count = int(metadata["folds"])
    binary_artifacts = ["ensemble_calibrator.joblib"]
    for fold in range(1, fold_count + 1):
        binary_artifacts.extend(pattern.format(fold=fold) for pattern in FOLD_ARTIFACT_PATTERNS)
    required_source_files = binary_artifacts + [
        "metadata.json",
        "oof_metrics.json",
        "test_metrics.json",
        "thresholds.json",
    ]
    missing = [name for name in required_source_files if not (source_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Cannot freeze an incomplete ensemble. Missing: " + ", ".join(missing)
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=".v3-freeze-", dir=output_dir.parent))
    try:
        for name in required_source_files:
            shutil.copy2(source_dir / name, temporary_root / name)

        preprocessing = {
            "config": V3PreprocessingConfig().to_dict(),
            "waveform_view_order": metadata["waveform_input"],
            "sqi_feature_names": metadata["sqi_feature_names"],
            "channel_policy": "PPG_R matches the annotated BUT PPG channel",
        }
        (temporary_root / "preprocessing_config.json").write_text(
            json.dumps(preprocessing, indent=2) + "\n"
        )

        decision = json.loads((source_dir / "freeze_decision.json").read_text())
        decision["bundle_source_commit"] = git_commit()
        decision["fold_count"] = fold_count
        decision["runtime_artifacts"] = binary_artifacts
        (temporary_root / "freeze_manifest.json").write_text(
            json.dumps(decision, indent=2) + "\n"
        )

        files_to_hash = sorted(
            path for path in temporary_root.iterdir() if path.name != "artifact_checksums.json"
        )
        checksums = {
            "algorithm": "sha256",
            "sha256": {path.name: sha256(path) for path in files_to_hash},
        }
        (temporary_root / "artifact_checksums.json").write_text(
            json.dumps(checksums, indent=2) + "\n"
        )
        temporary_root.rename(output_dir)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise

    verify_bundle(output_dir)
    print(f"Frozen PURE V3 prototype bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
