from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps" / "ai-service"))

from app.services.model_evaluation import (  # noqa: E402
    PlattCalibrator,
    binary_metrics,
    choose_binary_threshold,
    choose_gate_thresholds,
)


class ModelEvaluationTests(unittest.TestCase):
    def test_platt_calibrator_is_monotonic_and_finite(self) -> None:
        scores = np.asarray([0.05, 0.10, 0.20, 0.65, 0.80, 0.95])
        labels = np.asarray([0, 0, 0, 1, 1, 1])
        calibrator = PlattCalibrator().fit(scores, labels)
        probabilities = calibrator.predict_proba(scores)[:, 1]

        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue(np.all(np.diff(probabilities) >= 0.0))
        self.assertLess(probabilities[0], probabilities[-1])

    def test_threshold_selection_respects_false_acceptance_constraint(self) -> None:
        labels = np.asarray([0, 0, 0, 0, 1, 1, 1, 1])
        probabilities = np.asarray([0.01, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 0.95])

        threshold, metrics = choose_binary_threshold(
            labels,
            probabilities,
            maximum_false_acceptance_rate=0.25,
        )

        self.assertGreaterEqual(threshold, 0.20)
        self.assertLessEqual(metrics["false_acceptance_rate"], 0.25)
        self.assertGreater(metrics["balanced_accuracy"], 0.75)

    def test_gate_thresholds_create_ordered_regions(self) -> None:
        labels = np.asarray([0] * 20 + [1] * 20)
        probabilities = np.linspace(0.01, 0.99, 40)
        binary_threshold, _ = choose_binary_threshold(labels, probabilities)
        lower, upper, gate = choose_gate_thresholds(labels, probabilities, binary_threshold)

        self.assertLess(lower, upper)
        self.assertAlmostEqual(
            gate["reliable_coverage"] + gate["caution_rate"] + gate["unreliable_rate"],
            1.0,
        )
        direct = binary_metrics(labels, probabilities, binary_threshold)
        self.assertGreater(direct["balanced_accuracy"], 0.9)


if __name__ == "__main__":
    unittest.main()
