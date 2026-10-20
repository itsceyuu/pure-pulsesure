"""Preprocessing utilities for the BUT PPG v2 dataset.

The dataset contains two WFDB layouts:

* records 100-111 store one 10-second waveform as 300 one-sample signals;
* records 112 onward store three RGB signals with 300 samples each.

This module reads both layouts without requiring the external ``wfdb``
package and normalizes them to one 1-D PPG waveform at 30 Hz. For RGB
records, the red channel is preferred because the BUT PPG quality labels were
created from the red waveform. Matching the annotated channel is more
important here than the generic convention of using green smartphone PPG.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import math
import re
from typing import Iterable

import numpy as np


_GAIN_PATTERN = re.compile(
    r"^(?P<gain>[-+]?\d+(?:\.\d+)?)"
    r"(?:\((?P<baseline>[-+]?\d+(?:\.\d+)?)\))?"
    r"(?:/(?P<units>\S+))?$"
)


@dataclass(frozen=True)
class PreprocessingConfig:
    """Configuration shared by offline preparation and online inference."""

    sampling_rate_hz: float = 30.0
    low_cut_hz: float = 0.5
    high_cut_hz: float = 5.0
    epsilon: float = 1e-8

    def validate(self) -> None:
        if self.sampling_rate_hz <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if not 0 < self.low_cut_hz < self.high_cut_hz:
            raise ValueError("Expected 0 < low_cut_hz < high_cut_hz")
        if self.high_cut_hz >= self.sampling_rate_hz / 2:
            raise ValueError("high_cut_hz must be below the Nyquist frequency")

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class PPGRecord:
    """A normalized in-memory representation of one BUT PPG record."""

    record_id: str
    sampling_rate_hz: float
    waveform: np.ndarray
    selected_channel: str
    source_layout: str


@dataclass(frozen=True)
class _SignalDefinition:
    filename: str
    sample_format: str
    gain: float
    baseline: float
    units: str
    description: str


def _parse_signal_definition(line: str) -> _SignalDefinition:
    parts = line.split()
    if len(parts) < 3:
        raise ValueError(f"Malformed WFDB signal line: {line!r}")

    match = _GAIN_PATTERN.match(parts[2])
    if match is None:
        raise ValueError(f"Unsupported WFDB gain definition: {parts[2]!r}")

    gain = float(match.group("gain"))
    if math.isclose(gain, 0.0):
        raise ValueError("WFDB gain cannot be zero")

    baseline_group = match.group("baseline")
    baseline = float(baseline_group) if baseline_group is not None else 0.0
    units = match.group("units") or "a.u."
    description = " ".join(parts[8:]).strip()

    return _SignalDefinition(
        filename=parts[0],
        sample_format=parts[1],
        gain=gain,
        baseline=baseline,
        units=units,
        description=description,
    )


def _read_header(header_path: Path) -> tuple[int, float, int, list[_SignalDefinition]]:
    lines = [
        line.strip()
        for line in header_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        raise ValueError(f"Empty WFDB header: {header_path}")

    record_fields = lines[0].split()
    if len(record_fields) < 4:
        raise ValueError(f"Malformed WFDB record line: {lines[0]!r}")

    signal_count = int(record_fields[1])
    sampling_rate_hz = float(record_fields[2].split("/", maxsplit=1)[0])
    sample_count = int(record_fields[3])
    signal_lines = lines[1 : 1 + signal_count]
    if len(signal_lines) != signal_count:
        raise ValueError(
            f"Header declares {signal_count} signals but contains {len(signal_lines)}"
        )

    definitions = [_parse_signal_definition(line) for line in signal_lines]
    unsupported = [definition.sample_format for definition in definitions if definition.sample_format != "16"]
    if unsupported:
        raise ValueError(f"Only 16-bit WFDB files are supported, found: {unsupported[:3]}")

    filenames = {definition.filename for definition in definitions}
    if len(filenames) != 1:
        raise ValueError("Multi-file WFDB records are not supported")

    return signal_count, sampling_rate_hz, sample_count, definitions


def load_but_ppg_record(
    record_directory: str | Path,
    preferred_channels: Iterable[str] = ("PPG_R", "PPG_G", "PPG_B"),
) -> PPGRecord:
    """Load one BUT PPG record and return a single 1-D waveform.

    Args:
        record_directory: Directory named with the six-digit record ID.
        preferred_channels: Ordered channel names for modern RGB records.

    Raises:
        FileNotFoundError: When the header or signal file is missing.
        ValueError: When the WFDB layout is malformed or unsupported.
    """

    record_directory = Path(record_directory)
    record_id = record_directory.name
    header_path = record_directory / f"{record_id}_PPG.hea"
    if not header_path.exists():
        raise FileNotFoundError(f"Missing PPG header: {header_path}")

    signal_count, sampling_rate_hz, sample_count, definitions = _read_header(header_path)
    signal_path = record_directory / definitions[0].filename
    if not signal_path.exists():
        raise FileNotFoundError(f"Missing PPG signal: {signal_path}")

    digital = np.fromfile(signal_path, dtype="<i2")
    expected_values = signal_count * sample_count
    if digital.size != expected_values:
        raise ValueError(
            f"Expected {expected_values} values in {signal_path}, found {digital.size}"
        )

    frames = digital.reshape(sample_count, signal_count).astype(np.float64)
    gains = np.asarray([definition.gain for definition in definitions])
    baselines = np.asarray([definition.baseline for definition in definitions])
    physical = (frames - baselines) / gains

    if sample_count == 1 and signal_count > 1:
        waveform = physical[0, :]
        selected_channel = "legacy_combined_ppg"
        source_layout = f"legacy_{signal_count}_signals_x_1_sample"
    else:
        descriptions = [definition.description.upper() for definition in definitions]
        selected_index = 0
        for preferred in preferred_channels:
            preferred_upper = preferred.upper()
            if preferred_upper in descriptions:
                selected_index = descriptions.index(preferred_upper)
                break
        waveform = physical[:, selected_index]
        selected_channel = definitions[selected_index].description or f"channel_{selected_index}"
        source_layout = f"{signal_count}_signals_x_{sample_count}_samples"

    waveform = np.asarray(waveform, dtype=np.float64)
    if waveform.ndim != 1 or waveform.size < 8:
        raise ValueError(f"Unexpected waveform shape for {record_id}: {waveform.shape}")

    return PPGRecord(
        record_id=record_id,
        sampling_rate_hz=sampling_rate_hz,
        waveform=waveform,
        selected_channel=selected_channel,
        source_layout=source_layout,
    )


def _interpolate_non_finite(signal: np.ndarray) -> np.ndarray:
    signal = np.asarray(signal, dtype=np.float64).copy()
    finite = np.isfinite(signal)
    if finite.all():
        return signal
    if not finite.any():
        raise ValueError("Waveform contains no finite values")
    indices = np.arange(signal.size)
    signal[~finite] = np.interp(indices[~finite], indices[finite], signal[finite])
    return signal


def _linear_detrend(signal: np.ndarray) -> np.ndarray:
    positions = np.linspace(-1.0, 1.0, signal.size)
    slope, intercept = np.polyfit(positions, signal, deg=1)
    return signal - (slope * positions + intercept)


def _fft_bandpass(
    signal: np.ndarray,
    sampling_rate_hz: float,
    low_cut_hz: float,
    high_cut_hz: float,
) -> np.ndarray:
    spectrum = np.fft.rfft(signal)
    frequencies = np.fft.rfftfreq(signal.size, d=1.0 / sampling_rate_hz)
    passband = (frequencies >= low_cut_hz) & (frequencies <= high_cut_hz)
    spectrum[~passband] = 0.0
    return np.fft.irfft(spectrum, n=signal.size)


def preprocess_ppg(
    waveform: np.ndarray,
    config: PreprocessingConfig | None = None,
) -> np.ndarray:
    """Interpolate, detrend, filter, and z-normalize a PPG waveform."""

    config = config or PreprocessingConfig()
    config.validate()
    signal = np.asarray(waveform, dtype=np.float64)
    if signal.ndim != 1:
        raise ValueError(f"Expected a 1-D waveform, received shape {signal.shape}")
    if signal.size < 8:
        raise ValueError("Waveform is too short to preprocess")

    signal = _interpolate_non_finite(signal)
    signal = _linear_detrend(signal)
    signal = _fft_bandpass(
        signal,
        sampling_rate_hz=config.sampling_rate_hz,
        low_cut_hz=config.low_cut_hz,
        high_cut_hz=config.high_cut_hz,
    )
    standard_deviation = float(np.std(signal))
    if standard_deviation <= config.epsilon:
        raise ValueError("Waveform is constant or has negligible variance")
    return (signal - np.mean(signal)) / standard_deviation


def _spectral_features(signal: np.ndarray, sampling_rate_hz: float) -> dict[str, float]:
    frequencies = np.fft.rfftfreq(signal.size, d=1.0 / sampling_rate_hz)
    power = np.abs(np.fft.rfft(signal)) ** 2
    non_dc = frequencies > 0
    frequencies = frequencies[non_dc]
    power = power[non_dc]
    total_power = float(power.sum())
    if total_power <= 0:
        return {
            "spectral_entropy": 0.0,
            "dominant_frequency_hz": 0.0,
            "pulse_band_power_ratio": 0.0,
        }

    probabilities = power / total_power
    entropy = -float(np.sum(probabilities * np.log(probabilities + 1e-12)))
    entropy /= math.log(max(probabilities.size, 2))
    dominant_frequency = float(frequencies[int(np.argmax(power))])
    pulse_band = (frequencies >= 0.7) & (frequencies <= 3.0)
    pulse_band_ratio = float(power[pulse_band].sum() / total_power)
    return {
        "spectral_entropy": entropy,
        "dominant_frequency_hz": dominant_frequency,
        "pulse_band_power_ratio": pulse_band_ratio,
    }


def _peak_features(signal: np.ndarray, sampling_rate_hz: float) -> dict[str, float]:
    candidates = np.where(
        (signal[1:-1] > signal[:-2])
        & (signal[1:-1] >= signal[2:])
        & (signal[1:-1] > 0.15)
    )[0] + 1

    minimum_distance = max(1, int(round(0.30 * sampling_rate_hz)))
    selected: list[int] = []
    for candidate in candidates:
        if not selected or candidate - selected[-1] >= minimum_distance:
            selected.append(int(candidate))
        elif signal[candidate] > signal[selected[-1]]:
            selected[-1] = int(candidate)

    if len(selected) < 2:
        return {
            "peak_count": float(len(selected)),
            "peak_interval_cv": 1.0,
            "estimated_bpm": 0.0,
        }

    intervals = np.diff(selected) / sampling_rate_hz
    mean_interval = float(np.mean(intervals))
    interval_cv = float(np.std(intervals) / mean_interval) if mean_interval > 0 else 1.0
    estimated_bpm = 60.0 / float(np.median(intervals))
    return {
        "peak_count": float(len(selected)),
        "peak_interval_cv": interval_cv,
        "estimated_bpm": estimated_bpm,
    }


def extract_signal_features(
    raw_waveform: np.ndarray,
    processed_waveform: np.ndarray,
    sampling_rate_hz: float,
) -> dict[str, float]:
    """Extract compact, explainable features for a fast baseline model."""

    raw = _interpolate_non_finite(np.asarray(raw_waveform, dtype=np.float64))
    processed = np.asarray(processed_waveform, dtype=np.float64)
    derivative = np.diff(processed)

    raw_min = float(np.min(raw))
    raw_max = float(np.max(raw))
    tolerance = max((raw_max - raw_min) * 1e-4, 1e-12)
    clipped = (np.abs(raw - raw_min) <= tolerance) | (np.abs(raw - raw_max) <= tolerance)

    centered = processed - float(np.mean(processed))
    standard_deviation = float(np.std(centered))
    normalized = centered / max(standard_deviation, 1e-12)
    skewness = float(np.mean(normalized**3))
    kurtosis = float(np.mean(normalized**4) - 3.0)

    features = {
        "raw_range": raw_max - raw_min,
        "raw_std": float(np.std(raw)),
        "derivative_rms": float(np.sqrt(np.mean(derivative**2))),
        "derivative_std": float(np.std(derivative)),
        "zero_crossing_rate": float(np.mean(np.signbit(processed[1:]) != np.signbit(processed[:-1]))),
        "clipping_ratio": float(np.mean(clipped)),
        "skewness": skewness,
        "excess_kurtosis": kurtosis,
    }
    features.update(_spectral_features(processed, sampling_rate_hz))
    features.update(_peak_features(processed, sampling_rate_hz))
    return features
