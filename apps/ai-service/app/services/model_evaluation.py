"""Shared classification and reliability-gate evaluation helpers."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


class PlattCalibrator:
    """Regularized monotonic logistic calibration for a single model score."""

    def __init__(self, l2_strength: float = 1.0) -> None:
        self.l2_strength = float(l2_strength)
        self.slope_: float | None = None
        self.intercept_: float | None = None

    def fit(self, scores: np.ndarray, labels: np.ndarray) -> "PlattCalibrator":
        scores = np.asarray(scores, dtype=np.float64).reshape(-1)
        labels = np.asarray(labels, dtype=np.float64).reshape(-1)
        if scores.size != labels.size or scores.size == 0:
            raise ValueError("Scores and labels must be non-empty and have the same length")
        if not np.isfinite(scores).all() or not np.isfinite(labels).all():
            raise ValueError("Scores and labels must be finite")
        if np.unique(labels).size != 2:
            raise ValueError("Platt calibration requires both binary classes")

        prevalence = float(np.clip(np.mean(labels), 1e-6, 1.0 - 1e-6))
        initial = np.asarray([1.0, np.log(prevalence / (1.0 - prevalence))])

        def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
            slope, intercept = parameters
            logits = slope * scores + intercept
            probabilities = expit(logits)
            loss = np.mean(np.logaddexp(0.0, logits) - labels * logits)
            loss += 0.5 * self.l2_strength * slope * slope / scores.size
            residual = probabilities - labels
            gradient = np.asarray(
                [
                    np.mean(residual * scores) + self.l2_strength * slope / scores.size,
                    np.mean(residual),
                ]
            )
            return float(loss), gradient

        result = minimize(
            objective,
            initial,
            method="L-BFGS-B",
            jac=True,
            bounds=[(0.0, 100.0), (-100.0, 100.0)],
        )
        if not result.success:
            raise RuntimeError(f"Platt calibration failed: {result.message}")
        self.slope_, self.intercept_ = (float(value) for value in result.x)
        return self

    def predict_proba(self, scores: np.ndarray) -> np.ndarray:
        if self.slope_ is None or self.intercept_ is None:
            raise RuntimeError("PlattCalibrator must be fitted before prediction")
        scores = np.asarray(scores, dtype=np.float64).reshape(-1)
        positive = expit(self.slope_ * scores + self.intercept_)
        return np.column_stack([1.0 - positive, positive])


def binary_metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(np.mean(predictions == labels)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "precision_good": float(precision_score(labels, predictions, zero_division=0)),
        "recall_good_sensitivity": float(recall_score(labels, predictions, zero_division=0)),
        "specificity_poor": float(tn / max(tn + fp, 1)),
        "f1_good": float(f1_score(labels, predictions, zero_division=0)),
        "false_acceptance_rate": float(fp / max(tn + fp, 1)),
        "false_rejection_rate": float(fn / max(fn + tp, 1)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
    }


def choose_binary_threshold(
    labels: np.ndarray,
    probabilities: np.ndarray,
    maximum_false_acceptance_rate: float = 0.10,
) -> tuple[float, dict]:
    candidates = [binary_metrics(labels, probabilities, value) for value in np.linspace(0.01, 0.99, 197)]
    feasible = [item for item in candidates if item["false_acceptance_rate"] <= maximum_false_acceptance_rate]
    pool = feasible or candidates
    choice = max(pool, key=lambda item: (item["balanced_accuracy"], item["f1_good"]))
    return float(choice["threshold"]), choice


def gate_metrics(labels: np.ndarray, probabilities: np.ndarray, lower: float, upper: float) -> dict:
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    reliable = probabilities >= upper
    unreliable = probabilities <= lower
    caution = ~(reliable | unreliable)
    good = labels == 1
    poor = labels == 0
    return {
        "lower_threshold": float(lower),
        "upper_threshold": float(upper),
        "false_acceptance_rate": float(np.mean(reliable[poor])),
        "false_rejection_rate": float(np.mean(unreliable[good])),
        "good_acceptance_rate": float(np.mean(reliable[good])),
        "poor_rejection_rate": float(np.mean(unreliable[poor])),
        "reliable_coverage": float(np.mean(reliable)),
        "caution_rate": float(np.mean(caution)),
        "unreliable_rate": float(np.mean(unreliable)),
    }


def choose_gate_thresholds(
    labels: np.ndarray,
    probabilities: np.ndarray,
    binary_threshold: float,
    target_false_acceptance_rate: float = 0.05,
    target_false_rejection_rate: float = 0.05,
) -> tuple[float, float, dict]:
    upper_candidates = [
        gate_metrics(labels, probabilities, 0.0, upper)
        for upper in np.linspace(binary_threshold, 0.995, 200)
    ]
    feasible_upper = [
        item for item in upper_candidates if item["false_acceptance_rate"] <= target_false_acceptance_rate
    ]
    upper_choice = max(
        feasible_upper or upper_candidates,
        key=lambda item: (item["good_acceptance_rate"], -item["false_acceptance_rate"]),
    )
    upper_threshold = float(upper_choice["upper_threshold"])

    lower_candidates = [
        gate_metrics(labels, probabilities, lower, upper_threshold)
        for lower in np.linspace(0.005, min(binary_threshold, upper_threshold - 0.005), 200)
    ]
    feasible_lower = [
        item for item in lower_candidates if item["false_rejection_rate"] <= target_false_rejection_rate
    ]
    lower_choice = max(
        feasible_lower or lower_candidates,
        key=lambda item: (item["poor_rejection_rate"], -item["false_rejection_rate"]),
    )
    lower_threshold = float(lower_choice["lower_threshold"])
    return lower_threshold, upper_threshold, gate_metrics(
        labels, probabilities, lower_threshold, upper_threshold
    )
