"""FastAPI entry point for the PURE frozen signal-quality model."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.api.schemas import (
    HealthResponse,
    ModelInfoResponse,
    SignalQualityRequest,
    SignalQualityResponse,
)
from app.services.v3_inference import FrozenV3Predictor, SignalQualityPredictor


AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = AI_SERVICE_ROOT.parents[1]
DEFAULT_BUNDLE_DIR = REPOSITORY_ROOT / "models" / "production" / "frozen" / "v3-ensemble"


def create_app(
    predictor: SignalQualityPredictor | None = None,
    bundle_dir: Path | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if predictor is not None:
            app.state.predictor = predictor
        else:
            configured_dir = Path(
                os.environ.get("PURE_MODEL_BUNDLE_DIR", str(bundle_dir or DEFAULT_BUNDLE_DIR))
            )
            device_name = os.environ.get("PURE_AI_DEVICE", "auto")
            app.state.predictor = await run_in_threadpool(
                FrozenV3Predictor.load,
                configured_dir,
                device_name,
            )
        yield

    app = FastAPI(
        title="PURE Signal Quality API",
        version="1.0.0",
        description=(
            "Non-diagnostic PPG measurement-quality support using the frozen PURE V3 ensemble."
        ),
        lifespan=lifespan,
    )

    def current_predictor(request: Request) -> SignalQualityPredictor:
        return request.app.state.predictor

    @app.get("/", tags=["service"])
    async def root() -> dict:
        return {
            "service": "PURE Signal Quality API",
            "documentation": "/docs",
            "health": "/health",
            "model_info": "/model-info",
        }

    @app.get("/health", response_model=HealthResponse, tags=["service"])
    async def health(request: Request) -> dict:
        loaded = current_predictor(request)
        return {"status": "ok", "ready": True, "model_version": loaded.model_version}

    @app.get("/model-info", response_model=ModelInfoResponse, tags=["model"])
    async def model_info(request: Request) -> dict:
        return current_predictor(request).model_info()

    @app.post(
        "/v1/signal-quality",
        response_model=SignalQualityResponse,
        tags=["inference"],
    )
    async def signal_quality(payload: SignalQualityRequest, request: Request) -> dict:
        loaded = current_predictor(request)
        try:
            result = await run_in_threadpool(
                loaded.predict,
                np.asarray(payload.ppg, dtype=np.float64),
                payload.sampling_rate_hz,
                payload.candidate_bpm,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"device_id": payload.device_id, **result}

    return app


app = create_app()
