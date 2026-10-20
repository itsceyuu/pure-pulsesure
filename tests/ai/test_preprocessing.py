from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps" / "ai-service"))

from app.services.preprocessing import (  # noqa: E402
    PreprocessingConfig,
    extract_signal_features,
    load_but_ppg_record,
    preprocess_ppg,
)


class LoaderTests(unittest.TestCase):
    def test_reads_legacy_transposed_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            record_directory = Path(temporary_directory) / "100001"
            record_directory.mkdir()
            header = ["100001_PPG 8 2 1"]
            header.extend(["100001_PPG.dat 16 1(0)/a.u. 0 0 0 0 0"] * 8)
            (record_directory / "100001_PPG.hea").write_text("\n".join(header) + "\n")
            np.asarray([1, 2, 3, 4, 5, 6, 7, 8], dtype="<i2").tofile(
                record_directory / "100001_PPG.dat"
            )

            record = load_but_ppg_record(record_directory)

            np.testing.assert_allclose(record.waveform, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
            self.assertEqual(record.source_layout, "legacy_8_signals_x_1_sample")

    def test_prefers_green_channel_in_modern_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            record_directory = Path(temporary_directory) / "146014"
            record_directory.mkdir()
            header = [
                "146014_PPG 3 2 8",
                "146014_PPG.dat 16 1(0)/a.u. 0 0 0 0 0 PPG_R",
                "146014_PPG.dat 16 1(0)/a.u. 0 0 0 0 0 PPG_G",
                "146014_PPG.dat 16 1(0)/a.u. 0 0 0 0 0 PPG_B",
            ]
            (record_directory / "146014_PPG.hea").write_text("\n".join(header) + "\n")
            frames = np.asarray(
                [
                    [1, 10, 100],
                    [2, 20, 200],
                    [3, 30, 300],
                    [4, 40, 400],
                    [5, 50, 500],
                    [6, 60, 600],
                    [7, 70, 700],
                    [8, 80, 800],
                ],
                dtype="<i2",
            )
            frames.tofile(record_directory / "146014_PPG.dat")

            record = load_but_ppg_record(record_directory)

            np.testing.assert_allclose(
                record.waveform,
                [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
            )
            self.assertEqual(record.selected_channel, "PPG_G")


class PreprocessingTests(unittest.TestCase):
    def test_preprocessing_preserves_length_and_normalizes(self) -> None:
        sampling_rate_hz = 30.0
        time = np.arange(300) / sampling_rate_hz
        waveform = 0.4 * time + np.sin(2 * np.pi * 1.2 * time)

        processed = preprocess_ppg(waveform, PreprocessingConfig())

        self.assertEqual(processed.shape, waveform.shape)
        self.assertTrue(np.isfinite(processed).all())
        self.assertAlmostEqual(float(np.mean(processed)), 0.0, places=7)
        self.assertAlmostEqual(float(np.std(processed)), 1.0, places=7)

    def test_feature_extraction_produces_finite_values(self) -> None:
        sampling_rate_hz = 30.0
        time = np.arange(300) / sampling_rate_hz
        waveform = np.sin(2 * np.pi * 1.25 * time)
        processed = preprocess_ppg(waveform)

        features = extract_signal_features(waveform, processed, sampling_rate_hz)

        self.assertIn("spectral_entropy", features)
        self.assertIn("peak_interval_cv", features)
        self.assertTrue(all(np.isfinite(value) for value in features.values()))
        self.assertGreater(features["estimated_bpm"], 60.0)
        self.assertLess(features["estimated_bpm"], 90.0)


if __name__ == "__main__":
    unittest.main()
