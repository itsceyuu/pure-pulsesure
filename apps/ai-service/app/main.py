"""
PURE AI service: estimates an artifact probability for every PPG sample.

Contract (used by the Go backend in internal/ai/client.go):
  GET  /health
  POST /predict   {"fs": 100, "samples": [...]}
       -> {"prob": [...], "model_name": "...", "model_version": "..."}

The current model is a rule-based baseline (spikes and flat segments are
treated as artifacts). Replace the body of load_model() with a trained model
(TFLite / ONNX / Keras) without changing the contract above.
"""
import os
from typing import Callable

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

MODEL_NAME = os.getenv("MODEL_NAME", "pure-rule-baseline")
MODEL_VERSION = os.getenv("MODEL_VERSION", "0.1")

SPIKE_STEP = float(os.getenv("SPIKE_STEP", "0.8"))   # jump between adjacent samples
SPIKE_MARGIN = int(os.getenv("SPIKE_MARGIN", "16"))  # margin left/right of a spike (samples)
FLAT_EPS = 1e-4                                       # difference treated as "flat"
FLAT_MIN = int(os.getenv("FLAT_MIN_SAMPLES", "32"))  # minimum length of a flat segment
BASE_PROB = 0.05
HIGH_PROB = 0.95

PredictFn = Callable[[np.ndarray, float], np.ndarray]


def _runs(mask: np.ndarray):
    """Return (start, end_exclusive) for every run of True values."""
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    diff = np.diff(padded)
    return zip(np.flatnonzero(diff == 1), np.flatnonzero(diff == -1))


def rule_baseline(x: np.ndarray, fs: float) -> np.ndarray:
    """Baseline: large jumps and long flat segments are treated as artifacts."""
    n = len(x)
    prob = np.full(n, BASE_PROB)
    if n < 2:
        return prob

    step = np.abs(np.diff(x))  # step[i] = |x[i+1] - x[i]|

    for i in np.flatnonzero(step > SPIKE_STEP) + 1:
        prob[max(0, i - SPIKE_MARGIN): min(n, i + SPIKE_MARGIN + 1)] = HIGH_PROB

    for start, end in _runs(step < FLAT_EPS):
        if end - start >= FLAT_MIN:
            prob[start: end + 1] = HIGH_PROB

    return prob


def load_model() -> PredictFn:
    """
    Integration point for a trained model. Example (not active yet):
      interpreter = tflite.Interpreter(model_path=os.environ["MODEL_PATH"])
      ...then, inside the returned function, run the interpreter per window
      and return an array of probabilities with the same length as the input.
    """
    return rule_baseline


PREDICT = load_model()
app = FastAPI(title="PURE AI service", version=MODEL_VERSION)


class PredictIn(BaseModel):
    fs: float = Field(..., gt=0)
    samples: list[float] = Field(..., min_length=64, max_length=200_000)


class PredictOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prob: list[float]
    model_name: str
    model_version: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_NAME, "version": MODEL_VERSION}


@app.post("/predict", response_model=PredictOut)
def predict(body: PredictIn) -> PredictOut:
    x = np.asarray(body.samples, dtype=np.float64)
    prob = np.clip(PREDICT(x, body.fs), 0.0, 1.0)
    return PredictOut(
        prob=prob.tolist(),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
    )
