from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


def _load_spleeter_cli_main_module():
    module_path = Path(__file__).resolve().parent.parent / "spleeter-cli" / "main.py"
    spec = importlib.util.spec_from_file_location("spleeter_cli_main", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    fake_numpy = types.ModuleType("numpy")
    with mock.patch.dict(sys.modules, {"numpy": fake_numpy}):
        spec.loader.exec_module(module)
    return module


class _FakeDevice:
    def __init__(self, name: str, device_type: str = "GPU") -> None:
        self.name = name
        self.device_type = device_type


class _FakeConfig:
    def __init__(self, devices):
        self._devices = list(devices)
        self.visible_calls = []

    def list_physical_devices(self, kind: str):
        if kind != "GPU":
            return []
        return list(self._devices)

    def set_visible_devices(self, devices, kind: str) -> None:
        self.visible_calls.append((list(devices), kind))


class _FakeSysConfig:
    def __init__(self, build_info):
        self._build_info = build_info

    def get_build_info(self):
        return self._build_info


class _FakeTf:
    def __init__(self, devices, build_info):
        self.config = _FakeConfig(devices)
        self.sysconfig = _FakeSysConfig(build_info)


class SpleeterCliMainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_spleeter_cli_main_module()

    def test_select_backend_prefers_cpu_when_no_gpu(self):
        tf = _FakeTf([], {})
        with mock.patch.object(self.module.sys, "platform", "win32"):
            backend, detail = self.module._select_backend(tf, "auto")

        self.assertEqual(backend, "cpu")
        self.assertIn("no GPU devices", detail)

    def test_select_backend_prefers_cuda_when_gpu_and_cuda_build(self):
        tf = _FakeTf([_FakeDevice("/physical_device:GPU:0")], {"cuda_version": "11.8"})
        with mock.patch.object(self.module.sys, "platform", "win32"):
            backend, detail = self.module._select_backend(tf, "auto")

        self.assertEqual(backend, "cuda")
        self.assertIn("GPU:0", detail)

    def test_select_backend_prefers_metal_on_macos(self):
        tf = _FakeTf([_FakeDevice("/physical_device:GPU:0")], {})
        with mock.patch.object(self.module.sys, "platform", "darwin"):
            backend, detail = self.module._select_backend(tf, "auto")

        self.assertEqual(backend, "metal")
        self.assertIn("GPU:0", detail)

    def test_select_backend_falls_back_to_cpu_when_requested_accelerator_unavailable(self):
        tf = _FakeTf([], {})
        with mock.patch.object(self.module.sys, "platform", "win32"):
            backend, detail = self.module._select_backend(tf, "cuda")

        self.assertEqual(backend, "cpu")
        self.assertIn("requested cuda unavailable", detail)

    def test_configure_backend_hides_gpu_only_for_cpu(self):
        tf = _FakeTf([_FakeDevice("/physical_device:GPU:0")], {"cuda_version": "11.8"})

        self.module._configure_backend(tf, "cpu")

        self.assertEqual(tf.config.visible_calls, [([], "GPU")])

    def test_configure_backend_leaves_gpu_visible_for_accelerated_mode(self):
        tf = _FakeTf([_FakeDevice("/physical_device:GPU:0")], {"cuda_version": "11.8"})

        self.module._configure_backend(tf, "cuda")

        self.assertEqual(tf.config.visible_calls, [])


if __name__ == "__main__":
    unittest.main()
