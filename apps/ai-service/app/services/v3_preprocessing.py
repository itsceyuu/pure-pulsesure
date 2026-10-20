"""V3 multi-representation preprocessing for PPG quality assessment."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import math

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt, stft

from app.services.preprocessing import _interpolate_non_finite, _linear_detrend


@dataclass(frozen=True)
class V3PreprocessingConfig:
    sampling_rate_hz: float = 30.0
    low_cut_hz: float = 0.5
    high_cut_hz: float = 8.0
    filter_order: int = 3
    stft_window_samples: int = 64
    stft_overlap_samples: int = 48
    stft_fft_samples: int = 128
    epsilon: float = 1e-8

    def validate(self) -> None:
        if self.sampling_rate_hz <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if not 0 < self.low_cut_hz < self.high_cut_hz < self.sampling_rate_hz / 2:
            raise ValueError("Expected 0 < low_cut < high_cut < Nyquist")
        if self.filter_order < 1:
            raise ValueError("filter_order must be positive")
        if not 0 <= self.stft_overlap_samples < self.stft_window_samples:
            raise ValueError("STFT overlap must be smaller than its window")
        if self.stft_fft_samples < self.stft_window_samples:
            raise ValueError("STFT FFT size must be at least the window size")

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _standardize(values: np.ndarray, epsilon: float) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    centered = values - float(np.mean(values))
    scale = float(np.std(centered))
    if scale <= epsilon:
        return np.zeros_like(centered)
    return centered / scale


def preprocess_ppg_fdp_sdp(
    waveform: np.ndarray,
    config: V3PreprocessingConfig | None = None,
) -> np.ndarray:
    """Create filtered PPG, first derivative, and second derivative views."""

    config = config or V3PreprocessingConfig()
    config.validate()
    signal = _interpolate_non_finite(np.asarray(waveform, dtype=np.float64))
    if signal.ndim != 1 or signal.size < config.stft_window_samples:
        raise ValueError(f"Unexpected waveform shape: {signal.shape}")

    detrended = _linear_detrend(signal)
    sos = butter(
        config.filter_order,
        [config.low_cut_hz, config.high_cut_hz],
        btype="bandpass",
        fs=config.sampling_rate_hz,
        output="sos",
    )
    filtered = _standardize(sosfiltfilt(sos, detrended), config.epsilon)
    first_derivative = _standardize(np.gradient(filtered), config.epsilon)
    second_derivative = _standardize(np.gradient(first_derivative), config.epsilon)
    views = np.stack([filtered, first_derivative, second_derivative]).astype(np.float32)
    if not np.isfinite(views).all():
        raise ValueError("V3 waveform views contain non-finite values")
    return views


def create_log_stft(
    filtered_waveform: np.ndarray,
    config: V3PreprocessingConfig | None = None,
) -> np.ndarray:
    """Create a compact, standardized log-power STFT tensor ``[1, F, T]``."""

    config = config or V3PreprocessingConfig()
    config.validate()
    frequencies, _, coefficients = stft(
        np.asarray(filtered_waveform, dtype=np.float64),
        fs=config.sampling_rate_hz,
        window="hann",
        nperseg=config.stft_window_samples,
        noverlap=config.stft_overlap_samples,
        nfft=config.stft_fft_samples,
        boundary=None,
        padded=False,
    )
    keep = (frequencies >= config.low_cut_hz) & (frequencies <= config.high_cut_hz)
    log_power = np.log1p(np.abs(coefficients[keep]) ** 2)
    normalized = _standardize(log_power, config.epsilon).astype(np.float32)
    return normalized[np.newaxis, :, :]


def _safe_skew_kurtosis(values: np.ndarray, epsilon: float) -> tuple[float, float]:
    normalized = _standardize(values, epsilon)
    return float(np.mean(normalized**3)), float(np.mean(normalized**4) - 3.0)


def _spectral_sqi(filtered: np.ndarray, sampling_rate_hz: float, epsilon: float) -> dict[str, float]:
    frequencies = np.fft.rfftfreq(filtered.size, d=1.0 / sampling_rate_hz)
    power = np.abs(np.fft.rfft(filtered)) ** 2
    valid = frequencies > 0
    frequencies, power = frequencies[valid], power[valid]
    total = float(power.sum()) + epsilon
    probabilities = power / total
    entropy = -float(np.sum(probabilities * np.log(probabilities + epsilon))) / math.log(max(power.size, 2))

    pulse_mask = (frequencies >= 0.7) & (frequencies <= 3.0)
    high_mask = (frequencies > 3.0) & (frequencies <= 8.0)
    pulse_power = float(power[pulse_mask].sum())
    high_power = float(power[high_mask].sum())
    if np.any(pulse_mask):
        pulse_frequencies = frequencies[pulse_mask]
        pulse_spectrum = power[pulse_mask]
        dominant_frequency = float(pulse_frequencies[int(np.argmax(pulse_spectrum))])
    else:
        dominant_frequency = 0.0
    fundamental = np.abs(frequencies - dominant_frequency) <= 0.15
    harmonic = np.abs(frequencies - 2.0 * dominant_frequency) <= 0.20
    harmonic_power = float(power[fundamental | harmonic].sum())
    return {
        "spectral_entropy": entropy,
        "pulse_band_power_ratio": pulse_power / total,
        "high_frequency_power_ratio": high_power / total,
        "spectral_purity": harmonic_power / total,
        "dominant_frequency_hz": dominant_frequency,
    }


def _periodicity_sqi(filtered: np.ndarray, sampling_rate_hz: float, epsilon: float) -> dict[str, float]:
    autocorrelation = np.correlate(filtered, filtered, mode="full")[filtered.size - 1 :]
    if autocorrelation[0] <= epsilon:
        normalized_autocorrelation = np.zeros_like(autocorrelation)
    else:
        normalized_autocorrelation = autocorrelation / autocorrelation[0]
    minimum_lag = max(1, int(round(sampling_rate_hz * 60.0 / 180.0)))
    maximum_lag = min(filtered.size - 1, int(round(sampling_rate_hz * 60.0 / 30.0)))
    region = normalized_autocorrelation[minimum_lag : maximum_lag + 1]
    if region.size:
        relative_index = int(np.argmax(region))
        best_lag = minimum_lag + relative_index
        autocorrelation_peak = float(region[relative_index])
        autocorrelation_bpm = 60.0 * sampling_rate_hz / best_lag
    else:
        autocorrelation_peak, autocorrelation_bpm = 0.0, 0.0
    return {
        "autocorrelation_peak": autocorrelation_peak,
        "autocorrelation_bpm": autocorrelation_bpm,
    }


def _beat_sqi(filtered: np.ndarray, sampling_rate_hz: float, epsilon: float) -> dict[str, float]:
    minimum_distance = max(1, int(round(0.30 * sampling_rate_hz)))
    peaks, properties = find_peaks(filtered, distance=minimum_distance, prominence=0.20)
    if peaks.size >= 2:
        intervals = np.diff(peaks) / sampling_rate_hz
        interval_mean = float(np.mean(intervals))
        interval_cv = float(np.std(intervals) / max(interval_mean, epsilon))
        peak_bpm = 60.0 / max(float(np.median(intervals)), epsilon)
    else:
        interval_cv, peak_bpm = 1.0, 0.0

    before = max(2, int(round(0.25 * sampling_rate_hz)))
    after = max(3, int(round(0.55 * sampling_rate_hz)))
    beats = [filtered[peak - before : peak + after] for peak in peaks if peak >= before and peak + after <= filtered.size]
    correlations: list[float] = []
    if len(beats) >= 2:
        beat_matrix = np.stack(beats)
        template = np.median(beat_matrix, axis=0)
        template_std = float(np.std(template))
        if template_std > epsilon:
            for beat in beat_matrix:
                if float(np.std(beat)) > epsilon:
                    correlations.append(float(np.corrcoef(beat, template)[0, 1]))
    template_correlation = float(np.nanmedian(correlations)) if correlations else 0.0
    prominence = properties.get("prominences", np.asarray([], dtype=float))
    prominence_cv = (
        float(np.std(prominence) / max(float(np.mean(prominence)), epsilon))
        if prominence.size >= 2
        else 1.0
    )
    return {
        "peak_count": float(peaks.size),
        "peak_interval_cv": interval_cv,
        "peak_bpm": peak_bpm,
        "template_correlation": template_correlation,
        "peak_prominence_cv": prominence_cv,
    }


def _window_stability_sqi(filtered: np.ndarray, sampling_rate_hz: float, epsilon: float) -> dict[str, float]:
    dominant_frequencies: list[float] = []
    pulse_ratios: list[float] = []
    for window in np.array_split(filtered, 5):
        frequencies = np.fft.rfftfreq(window.size, d=1.0 / sampling_rate_hz)
        power = np.abs(np.fft.rfft(window)) ** 2
        valid = (frequencies >= 0.7) & (frequencies <= 3.0)
        if not np.any(valid):
            continue
        dominant_frequencies.append(float(frequencies[valid][int(np.argmax(power[valid]))]))
        pulse_ratios.append(float(power[valid].sum() / (power[frequencies > 0].sum() + epsilon)))
    return {
        "window_dominant_frequency_std": float(np.std(dominant_frequencies)) if dominant_frequencies else 0.0,
        "window_pulse_power_std": float(np.std(pulse_ratios)) if pulse_ratios else 0.0,
    }


def extract_v3_sqi_features(
    raw_waveform: np.ndarray,
    views: np.ndarray,
    sampling_rate_hz: float,
    epsilon: float = 1e-8,
) -> OrderedDict[str, float]:
    """Extract complementary morphology, periodicity, and spectrum SQIs."""

    raw = _interpolate_non_finite(np.asarray(raw_waveform, dtype=np.float64))
    filtered, first_derivative, second_derivative = np.asarray(views, dtype=np.float64)
    raw_min, raw_max = float(np.min(raw)), float(np.max(raw))
    tolerance = max((raw_max - raw_min) * 1e-4, epsilon)
    clipped = (np.abs(raw - raw_min) <= tolerance) | (np.abs(raw - raw_max) <= tolerance)
    skewness, excess_kurtosis = _safe_skew_kurtosis(filtered, epsilon)

    variance_signal = float(np.var(filtered))
    variance_first = float(np.var(first_derivative))
    variance_second = float(np.var(second_derivative))
    hjorth_mobility = math.sqrt(variance_first / max(variance_signal, epsilon))
    second_mobility = math.sqrt(variance_second / max(variance_first, epsilon))
    hjorth_complexity = second_mobility / max(hjorth_mobility, epsilon)

    features: dict[str, float] = {
        "raw_range": raw_max - raw_min,
        "raw_std": float(np.std(raw)),
        "perfusion_proxy": float(np.std(raw) / max(abs(float(np.mean(raw))), epsilon)),
        "clipping_ratio": float(np.mean(clipped)),
        "filtered_skewness": skewness,
        "filtered_excess_kurtosis": excess_kurtosis,
        "first_derivative_rms": float(np.sqrt(np.mean(first_derivative**2))),
        "second_derivative_rms": float(np.sqrt(np.mean(second_derivative**2))),
        "zero_crossing_rate": float(np.mean(np.signbit(filtered[1:]) != np.signbit(filtered[:-1]))),
        "hjorth_mobility": hjorth_mobility,
        "hjorth_complexity": hjorth_complexity,
    }
    features.update(_spectral_sqi(filtered, sampling_rate_hz, epsilon))
    features.update(_periodicity_sqi(filtered, sampling_rate_hz, epsilon))
    features.update(_beat_sqi(filtered, sampling_rate_hz, epsilon))
    features.update(_window_stability_sqi(filtered, sampling_rate_hz, epsilon))
    ordered = OrderedDict((name, float(value) if np.isfinite(value) else 0.0) for name, value in features.items())
    return ordered
