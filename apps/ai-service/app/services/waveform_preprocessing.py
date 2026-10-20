"""Waveform-preserving preprocessing for BUT PPG quality classification.

The feature baseline compresses every ten-second recording into a small set of
summary statistics.  This module instead creates three aligned views of the
complete waveform for a temporal model:

1. robust-scaled raw red PPG, retaining clipping and morphology;
2. zero-phase Butterworth band-pass PPG, emphasizing the pulse band;
3. the normalized first derivative, emphasizing abrupt artifacts.

The red channel is selected by ``load_but_ppg_record`` because BUT PPG quality
annotations were created from that channel.  All fitted decisions remain
subject-disjoint; this module never uses the quality label during preprocessing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt

from app.services.preprocessing import _interpolate_non_finite, _linear_detrend


@dataclass(frozen=True)
class WaveformPreprocessingConfig:
    sampling_rate_hz: float = 30.0
    low_cut_hz: float = 0.5
    high_cut_hz: float = 5.0
    filter_order: int = 4
    robust_clip: float = 10.0
    epsilon: float = 1e-8

    def validate(self) -> None:
        if self.sampling_rate_hz <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if not 0 < self.low_cut_hz < self.high_cut_hz:
            raise ValueError("Expected 0 < low_cut_hz < high_cut_hz")
        if self.high_cut_hz >= self.sampling_rate_hz / 2:
            raise ValueError("high_cut_hz must be below the Nyquist frequency")
        if self.filter_order < 1:
            raise ValueError("filter_order must be positive")
        if self.robust_clip <= 0:
            raise ValueError("robust_clip must be positive")

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _standardize(signal: np.ndarray, epsilon: float) -> np.ndarray:
    centered = signal - float(np.mean(signal))
    scale = float(np.std(centered))
    if scale <= epsilon:
        return np.zeros_like(signal)
    return centered / scale


def _robust_scale(signal: np.ndarray, clip: float, epsilon: float) -> np.ndarray:
    median = float(np.median(signal))
    mad = float(np.median(np.abs(signal - median)))
    scale = 1.4826 * mad
    if scale <= epsilon:
        scale = float(np.std(signal))
    if scale <= epsilon:
        return np.zeros_like(signal)
    scaled = (signal - median) / scale
    return np.clip(scaled, -clip, clip)


def preprocess_waveform_views(
    waveform: np.ndarray,
    config: WaveformPreprocessingConfig | None = None,
) -> np.ndarray:
    """Return ``[raw_robust, bandpassed, derivative]`` as ``float32``.

    The output shape is ``(3, sample_count)`` and is suitable for a 1-D CNN.
    A zero-phase SOS Butterworth filter is used instead of an FFT brick-wall
    mask to avoid circular boundary artifacts and sharp frequency truncation.
    """

    config = config or WaveformPreprocessingConfig()
    config.validate()
    signal = _interpolate_non_finite(np.asarray(waveform, dtype=np.float64))
    if signal.ndim != 1:
        raise ValueError(f"Expected a 1-D waveform, received shape {signal.shape}")
    if signal.size < 32:
        raise ValueError("Waveform is too short for zero-phase filtering")

    raw_view = _robust_scale(signal, config.robust_clip, config.epsilon)
    detrended = _linear_detrend(signal)
    sos = butter(
        config.filter_order,
        [config.low_cut_hz, config.high_cut_hz],
        btype="bandpass",
        fs=config.sampling_rate_hz,
        output="sos",
    )
    filtered = sosfiltfilt(sos, detrended)
    filtered_view = _standardize(filtered, config.epsilon)
    derivative_view = _standardize(np.gradient(filtered_view), config.epsilon)

    views = np.stack([raw_view, filtered_view, derivative_view]).astype(np.float32)
    if not np.isfinite(views).all():
        raise ValueError("Preprocessed waveform contains non-finite values")
    return views

