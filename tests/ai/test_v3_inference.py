from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
import torch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps" / "ai-service"))

from app.models.v3_models import CompactPPGQualityCNN, CompactSTFTQualityCNN  # noqa: E402
from app.services.model_evaluation import PlattCalibrator  # noqa: E402
from app.services.v3_inference import FrozenV3Predictor  # noqa: E402
from app.services.v3_preprocessing import V3PreprocessingConfig  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class FrozenInferenceTests(unittest.TestCase):
    def test_complete_bundle_loads_and_predicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            torch.save(CompactPPGQualityCNN().state_dict(), bundle / "waveform_fold_1.pt")
            torch.save(CompactSTFTQualityCNN().state_dict(), bundle / "stft_fold_1.pt")

            rng = np.random.default_rng(2026)
            features = rng.normal(size=(24, 25))
            labels = np.asarray([0, 1] * 12)
            sqi_model = ExtraTreesClassifier(n_estimators=4, random_state=2026).fit(
                features,
                labels,
            )
            joblib.dump(sqi_model, bundle / "sqi_fold_1.joblib")
            calibrator = PlattCalibrator().fit(
                np.linspace(0.05, 0.95, labels.size),
                labels,
            )
            joblib.dump(calibrator, bundle / "ensemble_calibrator.joblib")

            feature_names = [f"feature_{index}" for index in range(25)]
            actual_names = [
                "raw_range",
                "raw_std",
                "perfusion_proxy",
                "clipping_ratio",
                "filtered_skewness",
                "filtered_excess_kurtosis",
                "first_derivative_rms",
                "second_derivative_rms",
                "zero_crossing_rate",
                "hjorth_mobility",
                "hjorth_complexity",
                "spectral_entropy",
                "pulse_band_power_ratio",
                "high_frequency_power_ratio",
                "spectral_purity",
                "dominant_frequency_hz",
                "autocorrelation_peak",
                "autocorrelation_bpm",
                "peak_count",
                "peak_interval_cv",
                "peak_bpm",
                "template_correlation",
                "peak_prominence_cv",
                "window_dominant_frequency_std",
                "window_pulse_power_std",
            ]
            self.assertEqual(len(feature_names), len(actual_names))
            (bundle / "metadata.json").write_text(
                json.dumps(
                    {
                        "folds": 1,
                        "waveform_input": ["filtered_ppg", "first_derivative", "second_derivative"],
                        "sqi_feature_names": actual_names,
                    }
                )
            )
            (bundle / "preprocessing_config.json").write_text(
                json.dumps({"config": V3PreprocessingConfig().to_dict()})
            )
            (bundle / "thresholds.json").write_text(
                json.dumps(
                    {
                        "binary_threshold": 0.50,
                        "lower_threshold": 0.25,
                        "upper_threshold": 0.75,
                    }
                )
            )
            (bundle / "freeze_manifest.json").write_text(
                json.dumps(
                    {
                        "freeze_id": "test-freeze",
                        "status": "frozen_prototype_candidate",
                        "deployment_scope": "test",
                        "known_limitations": [],
                    }
                )
            )
            artifacts = [path for path in bundle.iterdir() if path.is_file()]
            (bundle / "artifact_checksums.json").write_text(
                json.dumps({"algorithm": "sha256", "sha256": {p.name: sha256(p) for p in artifacts}})
            )

            predictor = FrozenV3Predictor.load(bundle, device_name="cpu")
            time = np.arange(300) / 30.0
            waveform = np.sin(2.0 * np.pi * 1.2 * time)
            result = predictor.predict(waveform, sampling_rate_hz=30.0, candidate_bpm=72.0)

            self.assertEqual(result["model_version"], "test-freeze")
            self.assertGreaterEqual(result["quality_score"], 0)
            self.assertLessEqual(result["quality_score"], 100)
            self.assertIn(result["status"].value, {"reliable", "caution", "unreliable"})
            self.assertTrue(np.isfinite(list(result["branch_probabilities"].values())).all())


if __name__ == "__main__":
    unittest.main()
