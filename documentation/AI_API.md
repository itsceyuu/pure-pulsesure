# PURE AI API Contract

The Python AI service owns signal preprocessing, frozen-model inference, and
the three-state quality gate. The Go backend is its only intended client; the
dashboard should continue to call the Go backend rather than this service
directly.

## Runtime

From the repository root on the training/inference host:

```bash
source .venv/bin/activate
python -m pip install -r apps/ai-service/requirements.txt

export PURE_MODEL_BUNDLE_DIR="$PWD/models/production/frozen/v3-ensemble"
export PURE_AI_DEVICE=auto

uvicorn app.main:app \
  --app-dir apps/ai-service \
  --host 127.0.0.1 \
  --port 8001
```

Keep the service on loopback when Go runs on the same host. If Go runs on a
different machine during development, forward port 8001 with SSH instead of
publishing the model service directly to the internet.

With the service running, execute `python scripts/smoke_test_ai_api.py` from a
second terminal. It submits a deterministic 300-sample synthetic window and
prints both the health response and inference result. Synthetic input verifies
the integration path only; it is not model-performance evidence.

## `GET /health`

Returns HTTP 200 only after the complete frozen bundle has passed SHA-256
verification and every model has loaded.

```json
{
  "status": "ok",
  "ready": true,
  "model_version": "pure-ppg-quality-v3-ensemble-2026-10-20"
}
```

## `GET /model-info`

Returns the immutable model version, exact input contract, frozen thresholds,
deployment scope, and known limitations. It does not return model binaries.

## `POST /v1/signal-quality`

The endpoint accepts one complete analytical window: exactly 300 finite PPG
samples at 30 Hz. `candidate_bpm` is optional. PURE does not estimate heart
rate in this API version; it only decides whether a supplied candidate BPM may
be displayed.

```json
{
  "device_id": "pure-demo-01",
  "sampling_rate_hz": 30,
  "ppg": [0.012, 0.018, 0.027],
  "candidate_bpm": 74,
  "captured_at": "2026-10-20T15:30:00+07:00"
}
```

The abbreviated `ppg` array above is illustrative; a real request must contain
exactly 300 values.

```json
{
  "device_id": "pure-demo-01",
  "model_version": "pure-ppg-quality-v3-ensemble-2026-10-20",
  "quality_score": 67,
  "good_quality_probability": 0.67,
  "status": "reliable",
  "display_bpm": true,
  "heart_rate_bpm": 74,
  "recommended_action": "Display BPM and continue monitoring.",
  "branch_probabilities": {
    "waveform": 0.66,
    "stft": 0.63,
    "sqi": 0.70
  },
  "processing_ms": 18.4
}
```

Status behavior:

| Status | BPM behavior | Recommended UI action |
| --- | --- | --- |
| `reliable` | Candidate BPM may be displayed | Continue monitoring |
| `caution` | BPM is withheld | Check placement and motion |
| `unreliable` | BPM is withheld | Repeat the measurement |

The Go client should use a timeout, treat non-200 responses as `not_assessed`,
and never convert an AI-service failure into `reliable`. The model is a
non-diagnostic hackathon prototype.
