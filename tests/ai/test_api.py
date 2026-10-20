from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps" / "ai-service"))

try:
    from fastapi.testclient import TestClient
    from app.main import create_app
except ImportError:  # pragma: no cover - dependency availability is checked on the training host
    TestClient = None
    create_app = None


class FakePredictor:
    model_version = "test-model"

    def predict(self, waveform, sampling_rate_hz, candidate_bpm):
        assert np.asarray(waveform).shape == (300,)
        assert sampling_rate_hz == 30.0
        return {
            "model_version": self.model_version,
            "quality_score": 72,
            "good_quality_probability": 0.72,
            "status": "reliable",
            "display_bpm": True,
            "heart_rate_bpm": candidate_bpm,
            "recommended_action": "Display BPM and continue monitoring.",
            "branch_probabilities": {"waveform": 0.70, "stft": 0.71, "sqi": 0.75},
            "processing_ms": 4.2,
        }

    def model_info(self):
        return {
            "model_version": self.model_version,
            "status": "frozen_prototype_candidate",
            "expected_samples": 300,
            "sampling_rate_hz": 30.0,
            "window_seconds": 10.0,
            "thresholds": {"binary": 0.235, "lower": 0.073, "upper": 0.411},
            "labels": ["reliable", "caution", "unreliable"],
            "deployment_scope": "test",
            "limitations": [],
        }


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client_context = TestClient(create_app(predictor=FakePredictor()))
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def test_health_and_model_info(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["ready"])
        self.assertEqual(health.json()["model_version"], "test-model")

        model_info = self.client.get("/model-info")
        self.assertEqual(model_info.status_code, 200)
        self.assertEqual(model_info.json()["expected_samples"], 300)

    def test_quality_request_contract(self) -> None:
        response = self.client.post(
            "/v1/signal-quality",
            json={
                "device_id": "pure-demo-01",
                "sampling_rate_hz": 30,
                "ppg": [0.0] * 300,
                "candidate_bpm": 72,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "reliable")
        self.assertTrue(payload["display_bpm"])
        self.assertEqual(payload["heart_rate_bpm"], 72.0)

    def test_rejects_wrong_window_length_and_unknown_fields(self) -> None:
        short = self.client.post(
            "/v1/signal-quality",
            json={"device_id": "demo", "sampling_rate_hz": 30, "ppg": [0.0] * 299},
        )
        self.assertEqual(short.status_code, 422)

        extra = self.client.post(
            "/v1/signal-quality",
            json={
                "device_id": "demo",
                "sampling_rate_hz": 30,
                "ppg": [0.0] * 300,
                "unexpected": True,
            },
        )
        self.assertEqual(extra.status_code, 422)


if __name__ == "__main__":
    unittest.main()
