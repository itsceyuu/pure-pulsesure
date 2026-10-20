"""Load and execute the frozen PURE V3 signal-quality ensemble."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Protocol

import joblib
import numpy as np
import torch

from app.api.schemas import QualityStatus
from app.models.v3_models import CompactPPGQualityCNN, CompactSTFTQualityCNN
from app.services.v3_preprocessing import (
    V3PreprocessingConfig,
    create_log_stft,
    extract_v3_sqi_features,
    preprocess_ppg_fdp_sdp,
)


EXPECTED_SAMPLES = 300


class SignalQualityPredictor(Protocol):
    model_version: str

    def predict(
        self,
        waveform: np.ndarray,
        sampling_rate_hz: float,
        candidate_bpm: float | None,
    ) -> dict: ...

    def model_info(self) -> dict: ...


@dataclass(frozen=True)
class FrozenThresholds:
    binary: float
    lower: float
    upper: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_bundle(bundle_dir: Path) -> None:
    checksums_path = bundle_dir / "artifact_checksums.json"
    if not checksums_path.is_file():
        raise FileNotFoundError(f"Missing checksum manifest: {checksums_path}")
    checksums = json.loads(checksums_path.read_text())
    errors: list[str] = []
    for name, expected in checksums.get("sha256", {}).items():
        path = bundle_dir / name
        if not path.is_file():
            errors.append(f"missing {name}")
        elif _sha256(path) != expected:
            errors.append(f"checksum mismatch for {name}")
    if errors:
        raise RuntimeError("Frozen model verification failed: " + "; ".join(errors))


def choose_device(value: str) -> torch.device:
    requested = value.strip().lower()
    if requested == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    if requested not in {"cpu", "cuda", "mps"}:
        raise ValueError("PURE_AI_DEVICE must be one of auto, cpu, cuda, or mps")
    device = torch.device(requested)
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("PURE_AI_DEVICE=cuda but CUDA is unavailable")
    if requested == "mps" and not (
        getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
    ):
        raise RuntimeError("PURE_AI_DEVICE=mps but MPS is unavailable")
    return device


class FrozenV3Predictor:
    """Thread-safe inference wrapper around the immutable five-fold bundle."""

    def __init__(self, bundle_dir: Path, device: torch.device) -> None:
        self.bundle_dir = bundle_dir.expanduser().resolve()
        self.device = device
        verify_frozen_bundle(self.bundle_dir)

        self.freeze_manifest = json.loads((self.bundle_dir / "freeze_manifest.json").read_text())
        self.metadata = json.loads((self.bundle_dir / "metadata.json").read_text())
        self.preprocessing_contract = json.loads(
            (self.bundle_dir / "preprocessing_config.json").read_text()
        )
        threshold_data = json.loads((self.bundle_dir / "thresholds.json").read_text())
        self.thresholds = FrozenThresholds(
            binary=float(threshold_data["binary_threshold"]),
            lower=float(threshold_data["lower_threshold"]),
            upper=float(threshold_data["upper_threshold"]),
        )
        self.model_version = str(self.freeze_manifest["freeze_id"])
        self.fold_count = int(self.metadata["folds"])
        self.sqi_feature_names = list(self.metadata["sqi_feature_names"])
        self.preprocessing_config = V3PreprocessingConfig(
            **self.preprocessing_contract["config"]
        )
        self._lock = threading.Lock()

        self.waveform_models = [
            self._load_torch_model(CompactPPGQualityCNN(), f"waveform_fold_{fold}.pt")
            for fold in range(1, self.fold_count + 1)
        ]
        self.stft_models = [
            self._load_torch_model(CompactSTFTQualityCNN(), f"stft_fold_{fold}.pt")
            for fold in range(1, self.fold_count + 1)
        ]
        self.sqi_models = [
            joblib.load(self.bundle_dir / f"sqi_fold_{fold}.joblib")
            for fold in range(1, self.fold_count + 1)
        ]
        self.calibrator = joblib.load(self.bundle_dir / "ensemble_calibrator.joblib")

    @classmethod
    def load(cls, bundle_dir: Path, device_name: str = "auto") -> "FrozenV3Predictor":
        return cls(bundle_dir=bundle_dir, device=choose_device(device_name))

    def _load_torch_model(self, model: torch.nn.Module, filename: str) -> torch.nn.Module:
        state = torch.load(
            self.bundle_dir / filename,
            map_location=self.device,
            weights_only=True,
        )
        model.load_state_dict(state)
        model.to(self.device)
        model.eval()
        return model

    @staticmethod
    def _probability_from_logits(logits: torch.Tensor) -> float:
        return float(torch.sigmoid(logits).detach().cpu().reshape(-1)[0].item())

    def _torch_ensemble_probability(
        self,
        models: list[torch.nn.Module],
        inputs: np.ndarray,
    ) -> float:
        tensor = torch.from_numpy(inputs.astype(np.float32, copy=False)).to(self.device)
        with torch.inference_mode():
            probabilities = [self._probability_from_logits(model(tensor)) for model in models]
        return float(np.mean(probabilities))

    def predict(
        self,
        waveform: np.ndarray,
        sampling_rate_hz: float,
        candidate_bpm: float | None,
    ) -> dict:
        started = time.perf_counter()
        waveform = np.asarray(waveform, dtype=np.float64)
        if waveform.shape != (EXPECTED_SAMPLES,):
            raise ValueError(f"Expected exactly {EXPECTED_SAMPLES} PPG samples")
        if not np.isfinite(waveform).all():
            raise ValueError("Every PPG sample must be finite")
        expected_rate = self.preprocessing_config.sampling_rate_hz
        if not np.isclose(sampling_rate_hz, expected_rate, rtol=0.0, atol=1e-6):
            raise ValueError(f"Expected sampling_rate_hz={expected_rate:g}")

        views = preprocess_ppg_fdp_sdp(waveform, self.preprocessing_config)
        spectrogram = create_log_stft(views[0], self.preprocessing_config)
        features = extract_v3_sqi_features(waveform, views, sampling_rate_hz)
        feature_vector = np.asarray(
            [[features[name] for name in self.sqi_feature_names]],
            dtype=np.float32,
        )

        with self._lock:
            waveform_probability = self._torch_ensemble_probability(
                self.waveform_models,
                views[np.newaxis, :, :],
            )
            stft_probability = self._torch_ensemble_probability(
                self.stft_models,
                spectrogram[np.newaxis, :, :, :],
            )
            sqi_probability = float(
                np.mean(
                    [model.predict_proba(feature_vector)[0, 1] for model in self.sqi_models]
                )
            )
            raw_ensemble = float(
                np.mean([waveform_probability, stft_probability, sqi_probability])
            )
            calibrated = float(self.calibrator.predict_proba([raw_ensemble])[0, 1])

        probability = float(np.clip(calibrated, 0.0, 1.0))
        if probability >= self.thresholds.upper:
            status = QualityStatus.RELIABLE
            recommendation = "Display BPM and continue monitoring."
        elif probability <= self.thresholds.lower:
            status = QualityStatus.UNRELIABLE
            recommendation = "Withhold BPM and repeat the measurement."
        else:
            status = QualityStatus.CAUTION
            recommendation = "Check sensor placement and motion, then reacquire the signal."
        display_bpm = status is QualityStatus.RELIABLE
        return {
            "model_version": self.model_version,
            "quality_score": int(round(100.0 * probability)),
            "good_quality_probability": probability,
            "status": status,
            "display_bpm": display_bpm,
            "heart_rate_bpm": candidate_bpm if display_bpm else None,
            "recommended_action": recommendation,
            "branch_probabilities": {
                "waveform": waveform_probability,
                "stft": stft_probability,
                "sqi": sqi_probability,
            },
            "processing_ms": (time.perf_counter() - started) * 1000.0,
        }

    def model_info(self) -> dict:
        limitations = list(self.freeze_manifest.get("known_limitations", []))
        return {
            "model_version": self.model_version,
            "status": str(self.freeze_manifest.get("status", "frozen_prototype_candidate")),
            "expected_samples": EXPECTED_SAMPLES,
            "sampling_rate_hz": self.preprocessing_config.sampling_rate_hz,
            "window_seconds": EXPECTED_SAMPLES / self.preprocessing_config.sampling_rate_hz,
            "thresholds": {
                "binary": self.thresholds.binary,
                "lower": self.thresholds.lower,
                "upper": self.thresholds.upper,
            },
            "labels": [status.value for status in QualityStatus],
            "deployment_scope": str(
                self.freeze_manifest.get(
                    "deployment_scope",
                    "hackathon prototype and non-diagnostic measurement-quality support only",
                )
            ),
            "limitations": limitations,
        }
