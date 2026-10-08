"""Run with the independent Spleeter environment using unittest discover."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile


CLI = Path(__file__).resolve().parents[1] / "main.py"


class SampleRateTests(unittest.TestCase):
    def test_samples_and_configuration_keep_source_rate(self):
        spec = importlib.util.spec_from_file_location("spleeter_cli_main", CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        for rate in (22050, 44100, 48000, 96000):
            with self.subTest(rate=rate), tempfile.TemporaryDirectory() as directory:
                source, output = Path(directory) / "in.wav", Path(directory) / "out.wav"
                t = np.arange(rate // 10) / rate
                waveform = np.column_stack([0.25 * np.sin(2 * np.pi * 1000 * t)] * 2).astype(np.float32)
                wavfile.write(source, rate, waveform)

                class Separator:
                    def __init__(self, descriptor, multiprocess):
                        params = json.loads(Path(descriptor).read_text())
                        assert params["sample_rate"] == rate
                        assert params["model_dir"] == "2stems"
                        assert multiprocess is False

                    def separate(self, samples, audio_descriptor):
                        np.testing.assert_array_equal(samples, waveform)
                        assert audio_descriptor == str(source)
                        return {"vocals": np.zeros_like(samples), "accompaniment": samples}

                modules = {
                    "tensorflow": SimpleNamespace(config=SimpleNamespace(set_visible_devices=lambda *args: None)),
                    "spleeter.separator": SimpleNamespace(Separator=Separator),
                    "spleeter.utils.configuration": SimpleNamespace(
                        load_configuration=lambda descriptor: {"sample_rate": 44100, "model_dir": "2stems"}
                    ),
                }
                with patch.dict(sys.modules, modules), patch.dict(os.environ), patch.object(
                    sys, "argv", ["spleeter-cli", "--input", str(source), "--output", str(output)]
                ):
                    self.assertEqual(cli.main(), 0)
                actual_rate, actual = wavfile.read(output)
                self.assertEqual(actual_rate, rate)
                self.assertEqual(actual.shape, waveform.shape)
                np.testing.assert_allclose(actual / 32767.0, waveform, atol=1 / 32767.0)

    def test_residual_preserves_high_frequencies_removed_from_model_stems(self):
        spec = importlib.util.spec_from_file_location("spleeter_cli_main", CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        t = np.arange(44100) / 44100
        vocals = np.column_stack([0.2 * np.sin(2 * np.pi * 1000 * t)] * 2).astype(np.float32)
        upper_band = np.column_stack([0.2 * np.sin(2 * np.pi * 15000 * t)] * 2).astype(np.float32)
        result = cli._full_band_accompaniment(vocals + upper_band, {
            "vocals": vocals, "accompaniment": np.zeros_like(vocals),
        })
        np.testing.assert_allclose(result, upper_band, atol=3e-8)

    @unittest.skipUnless(os.environ.get("SPLEETER_MODEL_TEST") == "1", "opt-in real model test")
    def test_real_model_preserves_rate_and_frame_count(self):
        for rate in (22050, 48000):
            with self.subTest(rate=rate), tempfile.TemporaryDirectory() as directory:
                source, output = Path(directory) / "in.wav", Path(directory) / "out.wav"
                t = np.arange(rate) / rate
                # Above the model's F=1024 / frame_length=4096 cutoff.
                frequency = rate * 0.35
                waveform = np.column_stack([0.25 * np.sin(2 * np.pi * frequency * t)] * 2).astype(np.float32)
                wavfile.write(source, rate, waveform)
                result = subprocess.run(
                    [sys.executable, str(CLI), "--input", str(source), "--output", str(output)],
                    capture_output=True, text=True, timeout=180,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                actual_rate, actual = wavfile.read(output)
                self.assertEqual(actual_rate, rate)
                self.assertEqual(actual.shape, waveform.shape)
                self.assertTrue(np.any(actual))
                # Verify actual upper-band energy, not just WAV metadata.
                center = slice(rate // 4, 3 * rate // 4)
                error = actual[center] / 32767.0 - waveform[center]
                self.assertLess(float(np.sqrt(np.mean(error ** 2))), 0.005)


if __name__ == "__main__":
    unittest.main()
