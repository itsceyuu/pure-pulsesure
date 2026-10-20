"""Validated public request and response schemas for the PURE AI API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import math
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QualityStatus(str, Enum):
    RELIABLE = "reliable"
    CAUTION = "caution"
    UNRELIABLE = "unreliable"


class SignalQualityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=128)
    sampling_rate_hz: float = Field(default=30.0, gt=0)
    ppg: list[float] = Field(min_length=300, max_length=300)
    candidate_bpm: Optional[float] = Field(default=None, ge=30.0, le=240.0)
    captured_at: Optional[datetime] = None

    @field_validator("ppg")
    @classmethod
    def ppg_must_be_finite(cls, values: list[float]) -> list[float]:
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Every PPG sample must be finite")
        return values


class BranchProbabilities(BaseModel):
    waveform: float = Field(ge=0.0, le=1.0)
    stft: float = Field(ge=0.0, le=1.0)
    sqi: float = Field(ge=0.0, le=1.0)


class SignalQualityResponse(BaseModel):
    device_id: str
    model_version: str
    quality_score: int = Field(ge=0, le=100)
    good_quality_probability: float = Field(ge=0.0, le=1.0)
    status: QualityStatus
    display_bpm: bool
    heart_rate_bpm: Optional[float]
    recommended_action: str
    branch_probabilities: BranchProbabilities
    processing_ms: float = Field(ge=0.0)


class HealthResponse(BaseModel):
    status: str
    ready: bool
    model_version: str


class ModelInfoResponse(BaseModel):
    model_version: str
    status: str
    expected_samples: int
    sampling_rate_hz: float
    window_seconds: float
    thresholds: dict[str, float]
    labels: list[str]
    deployment_scope: str
    limitations: list[str]
