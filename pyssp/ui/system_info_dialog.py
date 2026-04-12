from __future__ import annotations

import configparser
import importlib
import importlib.metadata
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Callable, List, Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from pyssp.audio_engine import list_output_devices
from pyssp.midi_control import list_midi_input_devices
from pyssp.settings_store import get_settings_path, load_settings
from pyssp.timecode import list_midi_output_devices


@dataclass
class NetworkInterfaceInfo:
    name: str
    mac: str
    ipv4: List[str]
    ipv6: List[str]


def _safe_package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return "not installed"


def _safe_runtime_module_version(import_name: str, attributes: List[str], package_name: Optional[str] = None) -> str:
    if import_name == "pygame":
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        module = importlib.import_module(import_name)
    except Exception:
        return _safe_package_version(package_name or import_name)
    for attr in attributes:
        value = getattr(module, attr, None)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return _safe_package_version(package_name or import_name)


def _safe_pyqt_version() -> str:
    try:
        from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR

        pyqt = str(PYQT_VERSION_STR or "").strip()
        qt = str(QT_VERSION_STR or "").strip()
        if pyqt and qt:
            return f"{pyqt} (Qt {qt})"
        if pyqt:
            return pyqt
    except Exception:
        pass
    return _safe_package_version("PyQt5")


def _get_library_versions() -> List[str]:
    versions = [
        f"python: {platform.python_version()}",
        f"PyQt5: {_safe_pyqt_version()}",
        f"pygame-ce: {_safe_runtime_module_version('pygame', ['__version__'], package_name='pygame-ce')}",
        f"numpy: {_safe_runtime_module_version('numpy', ['__version__'])}",
        f"sounddevice: {_safe_runtime_module_version('sounddevice', ['__version__'])}",
        f"Flask: {_safe_runtime_module_version('flask', ['__version__'], package_name='Flask')}",
        f"simple-websocket: {_safe_runtime_module_version('simple_websocket', ['__version__'], package_name='simple-websocket')}",
        f"websockets: {_safe_runtime_module_version('websockets', ['__version__'])}",
        f"Werkzeug: {_safe_runtime_module_version('werkzeug', ['__version__'], package_name='Werkzeug')}",
    ]
    return versions


def _run_command(args: List[str]) -> str:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=4, check=False)
        text = (proc.stdout or "").strip()
        if text:
            return text
        return (proc.stderr or "").strip()
    except Exception:
        return ""


def _dedupe(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in values:
        token = str(item or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _parse_windows_ipconfig(raw: str) -> List[NetworkInterfaceInfo]:
    interfaces: List[NetworkInterfaceInfo] = []
    current: Optional[NetworkInterfaceInfo] = None
    for line in (raw or "").splitlines():
        line = line.rstrip()
        if not line:
            continue
        if (not line.startswith(" ")) and line.endswith(":"):
            if current is not None:
                interfaces.append(current)
            current = NetworkInterfaceInfo(name=line[:-1].strip(), mac="", ipv4=[], ipv6=[])
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if "physical address" in key:
            current.mac = value
        elif "ipv4 address" in key:
            current.ipv4.append(value.split("(", 1)[0].strip())
        elif "ipv6 address" in key or "link-local ipv6 address" in key:
            current.ipv6.append(value.split("%", 1)[0].strip())
    if current is not None:
        interfaces.append(current)
    return [
        NetworkInterfaceInfo(
            name=item.name,
            mac=item.mac,
            ipv4=_dedupe(item.ipv4),
            ipv6=_dedupe(item.ipv6),
        )
        for item in interfaces
        if item.mac or item.ipv4 or item.ipv6
    ]


def _parse_unix_ifconfig(raw: str) -> List[NetworkInterfaceInfo]:
    interfaces: List[NetworkInterfaceInfo] = []
    current: Optional[NetworkInterfaceInfo] = None
    header_re = re.compile(r"^([A-Za-z0-9_.:-]+):")
    for line in (raw or "").splitlines():
        if not line.strip():
            continue
        m = header_re.match(line)
        if m:
            if current is not None:
                interfaces.append(current)
            current = NetworkInterfaceInfo(name=m.group(1), mac="", ipv4=[], ipv6=[])
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("ether "):
            parts = stripped.split()
            if len(parts) >= 2:
                current.mac = parts[1]
        elif stripped.startswith("inet "):
            parts = stripped.split()
            if len(parts) >= 2:
                current.ipv4.append(parts[1])
        elif stripped.startswith("inet6 "):
            parts = stripped.split()
            if len(parts) >= 2:
                current.ipv6.append(parts[1].split("%", 1)[0])
    if current is not None:
        interfaces.append(current)
    return [
        NetworkInterfaceInfo(
            name=item.name,
            mac=item.mac,
            ipv4=_dedupe(item.ipv4),
            ipv6=_dedupe(item.ipv6),
        )
        for item in interfaces
        if item.mac or item.ipv4 or item.ipv6
    ]


def _fallback_network_info() -> List[NetworkInterfaceInfo]:
    ipv4: List[str] = []
    ipv6: List[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            fam = info[0]
            addr = str(info[4][0])
            if fam == socket.AF_INET:
                ipv4.append(addr)
            elif fam == socket.AF_INET6:
                ipv6.append(addr.split("%", 1)[0])
    except Exception:
        pass

    mac = ""
    try:
        node = int(uuid.getnode())
        mac = ":".join(f"{(node >> shift) & 0xFF:02X}" for shift in range(40, -1, -8))
    except Exception:
        mac = ""

    if not ipv4 and not ipv6 and not mac:
        return []
    return [NetworkInterfaceInfo(name="host", mac=mac, ipv4=_dedupe(ipv4), ipv6=_dedupe(ipv6))]


def _get_network_interfaces() -> List[NetworkInterfaceInfo]:
    if os.name == "nt":
        raw = _run_command(["ipconfig", "/all"])
        parsed = _parse_windows_ipconfig(raw)
        if parsed:
            return parsed
    else:
        raw = _run_command(["ifconfig", "-a"]) or _run_command(["ifconfig"])
        parsed = _parse_unix_ifconfig(raw)
        if parsed:
            return parsed
    return _fallback_network_info()


def _list_midi_outputs_cross_platform() -> List[str]:
    output_names = [name for _device_id, name in list_midi_output_devices()]
    if output_names:
        return _dedupe(output_names)

    try:
        import pygame.midi as pg_midi

        pg_midi.init()
        names: List[str] = []
        for idx in range(int(pg_midi.get_count())):
            info = pg_midi.get_device_info(idx)
            if not info or len(info) < 5:
                continue
            if int(info[3]) != 1:
                continue
            raw_name = info[1]
            if isinstance(raw_name, (bytes, bytearray)):
                names.append(bytes(raw_name).decode(errors="replace").strip())
            else:
                names.append(str(raw_name).strip())
        return _dedupe(names)
    except Exception:
        return []


def _get_pygame_decoder_report(
    register_process: Optional[Callable[[Optional[subprocess.Popen[str]]], None]] = None,
    timeout_sec: float = 12.0,
) -> List[str]:
    cmd: List[str]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--system-info-probe"]
    else:
        cmd = [sys.executable, "-m", "pyssp.system_info_probe"]
    proc: Optional[subprocess.Popen[str]] = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            creationflags=creationflags,
        )
        if register_process is not None:
            register_process(proc)
        stdout, stderr = proc.communicate(timeout=max(1.0, float(timeout_sec)))
        stdout = (stdout or "").strip()
        stderr = (stderr or "").strip()
        lines = [line.rstrip() for line in stdout.splitlines() if line.strip()]
        if stderr:
            lines.append(f"probe stderr: {stderr}")
        if lines:
            return lines
        if proc.returncode != 0:
            return [f"pygame-ce supported format: probe failed with exit code {proc.returncode}"]
        return ["pygame-ce supported format: probe returned no data"]
    except subprocess.TimeoutExpired:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
        return ["pygame-ce supported format: probe timed out"]
    except Exception as exc:
        return [f"pygame-ce supported format: unavailable ({exc})"]
    finally:
        if register_process is not None:
            register_process(None)


def detect_supported_audio_format_extensions(
    timeout_sec: float = 10.0,
    register_process: Optional[Callable[[Optional[subprocess.Popen[str]]], None]] = None,
) -> List[str]:
    lines = _get_pygame_decoder_report(register_process=register_process, timeout_sec=timeout_sec)
    for line in lines:
        text = str(line or "").strip()
        if not text.lower().startswith("pyssp supported audio extensions:"):
            continue
        raw = text.split(":", 1)[1].strip()
        if raw.lower() == "none":
            return []
        output: List[str] = []
        seen: set[str] = set()
        for token in raw.split(","):
            value = str(token or "").strip().lower()
            if not value:
                continue
            if not value.startswith("."):
                value = f".{value.lstrip('.')}"
            if value in seen:
                continue
            seen.add(value)
            output.append(value)
        return output
    return []


def _get_current_running_config_report() -> List[str]:
    lines: List[str] = []
    settings_path = get_settings_path()
    lines.append(f"settings_file: {settings_path}")
    lines.append(f"settings_exists: {settings_path.exists()}")
    if settings_path.exists():
        try:
            stat = settings_path.stat()
            lines.append(f"settings_mtime: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))}")
            lines.append(f"settings_size_bytes: {int(stat.st_size)}")
        except Exception as exc:
            lines.append(f"settings_stat_error: {exc}")
        try:
            parser = configparser.ConfigParser()
            parser.read(settings_path, encoding="utf-8")
            lines.append("settings_ini_dump_begin")
            sections = parser.sections()
            if not sections:
                lines.append("  <no sections>")
            for section_name in sections:
                lines.append(f"  [{section_name}]")
                for key, value in parser.items(section_name):
                    lines.append(f"  {key}={value}")
            lines.append("settings_ini_dump_end")
        except Exception as exc:
            lines.append(f"settings_ini_dump_error: {exc}")
    try:
        cfg = load_settings()
        lines.append("normalized_runtime_snapshot_begin")
        lines.append(f"ui_language: {cfg.ui_language}")
        lines.append(f"audio_output_device: {cfg.audio_output_device or '(default)'}")
        lines.append(f"volume: {cfg.volume}")
        lines.append(f"talk_volume_level: {cfg.talk_volume_level}")
        lines.append(f"fade_in_sec: {cfg.fade_in_sec}")
        lines.append(f"cross_fade_sec: {cfg.cross_fade_sec}")
        lines.append(f"fade_out_sec: {cfg.fade_out_sec}")
        lines.append(f"preload_audio_enabled: {cfg.preload_audio_enabled}")
        lines.append(f"preload_audio_memory_limit_mb: {cfg.preload_audio_memory_limit_mb}")
        lines.append(f"midi_input_device_ids: {cfg.midi_input_device_ids}")
        lines.append(f"timecode_mode: {cfg.timecode_mode}")
        lines.append(f"timecode_audio_output_device: {cfg.timecode_audio_output_device}")
        lines.append(f"timecode_midi_output_device: {cfg.timecode_midi_output_device}")
        lines.append(f"timecode_fps: {cfg.timecode_fps}")
        lines.append(f"timecode_mtc_fps: {cfg.timecode_mtc_fps}")
        lines.append(f"web_remote_enabled: {cfg.web_remote_enabled}")
        lines.append(f"web_remote_port: {cfg.web_remote_port}")
        lines.append(f"web_remote_ws_port: {cfg.web_remote_ws_port}")
        lines.append("normalized_runtime_snapshot_end")
    except Exception as exc:
        lines.append(f"load_settings_error: {exc}")
    return lines


def build_system_information_text(
    app_version_text: str,
    register_probe_process: Optional[Callable[[Optional[subprocess.Popen[str]]], None]] = None,
) -> str:
    now_local = time.strftime("%Y-%m-%d %H:%M:%S")
    system_name = f"{platform.system()} {platform.release()} ({platform.machine()})"

    lines: List[str] = []
    lines.append("pySSP System Information")
    lines.append("=" * 80)
    lines.append(f"Collected at: {now_local}")
    lines.append(f"System name: {system_name}")
    lines.append(f"Software version: {app_version_text}")
    lines.append(f"Running path: {os.path.abspath(sys.executable)}")
    lines.append(f"Current working directory: {os.path.abspath(os.getcwd())}")
    lines.append(f"Frozen build: {bool(getattr(sys, 'frozen', False))}")
    lines.append(f"Platform: {platform.platform()}")
    lines.append(f"Hostname: {socket.gethostname()}")
    lines.append(f"System timezone: {time.tzname}")
    lines.append("")

    lines.append("Available audio hardware:")
    audio_devices = list_output_devices()
    if audio_devices:
        for item in audio_devices:
            lines.append(f"- {item}")
    else:
        lines.append("- none detected")
    lines.append("")

    lines.append("Available MIDI hardware:")
    midi_inputs = [name for _device_id, name in list_midi_input_devices(force_refresh=False)]
    midi_outputs = _list_midi_outputs_cross_platform()
    lines.append("- MIDI Input Devices:")
    if midi_inputs:
        for item in _dedupe(midi_inputs):
            lines.append(f"  - {item}")
    else:
        lines.append("  - none detected")
    lines.append("- MIDI Output Devices:")
    if midi_outputs:
        for item in _dedupe(midi_outputs):
            lines.append(f"  - {item}")
    else:
        lines.append("  - none detected")
    lines.append("")

    lines.append("pygame-ce / SDL_mixer supported format:")
    for item in _get_pygame_decoder_report(register_process=register_probe_process):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("Current running config (info):")
    for item in _get_current_running_config_report():
        lines.append(f"- {item}")
    lines.append("")

    lines.append("Library versions on this build/runtime:")
    for item in _get_library_versions():
        lines.append(f"- {item}")
    lines.append("")

    lines.append("Available NIC MAC/IP:")
    interfaces = _get_network_interfaces()
    if interfaces:
        for interface in interfaces:
            lines.append(f"- {interface.name}")
            lines.append(f"  MAC: {interface.mac or 'n/a'}")
            lines.append(f"  IPv4: {', '.join(interface.ipv4) if interface.ipv4 else 'n/a'}")
            lines.append(f"  IPv6: {', '.join(interface.ipv6) if interface.ipv6 else 'n/a'}")
    else:
        lines.append("- none detected")
    lines.append("")

    lines.append("Environment diagnostics:")
    lines.append(f"- SDL_AUDIODRIVER: {os.environ.get('SDL_AUDIODRIVER', '(not set)')}")
    lines.append(f"- PATH length: {len(os.environ.get('PATH', ''))}")
    lines.append(f"- argv: {sys.argv}")

    return "\n".join(lines)


class _SystemInfoWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    cancel_requested = pyqtSignal()

    def __init__(self, app_version_text: str) -> None:
        super().__init__()
        self._app_version_text = str(app_version_text or "")
        self._probe_process: Optional[subprocess.Popen[str]] = None
        self.cancel_requested.connect(self.cancel)

    def run(self) -> None:
        try:
            self.finished.emit(
                build_system_information_text(self._app_version_text, register_probe_process=self._set_probe_process)
            )
        except Exception as exc:
            self.failed.emit(str(exc))

    def _set_probe_process(self, proc: Optional[subprocess.Popen[str]]) -> None:
        self._probe_process = proc

    def cancel(self) -> None:
        proc = self._probe_process
        if proc is None:
            return
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=1.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        self._probe_process = None


class SystemInformationDialog(QDialog):
    def __init__(self, app_version_text: str, parent=None) -> None:
        super().__init__(parent)
        self._app_version_text = str(app_version_text or "")
        self._refresh_thread: Optional[QThread] = None
        self._refresh_worker: Optional[_SystemInfoWorker] = None
        self.setWindowTitle("System Information")
        self.resize(980, 700)

        root = QVBoxLayout(self)

        note = QLabel(
            "Diagnostic information for troubleshooting. Use Refresh to re-scan devices and network.",
            self,
        )
        note.setWordWrap(True)
        root.addWidget(note)

        self._text_box = QPlainTextEdit(self)
        self._text_box.setReadOnly(True)
        self._text_box.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._text_box.setPlainText("Refreshing system information...")
        root.addWidget(self._text_box, 1)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh", self)
        self._copy_btn = QPushButton("Copy", self)
        self._export_btn = QPushButton("Export...", self)
        self._export_settings_btn = QPushButton("Export settings.ini...", self)
        self._close_btn = QPushButton("Close", self)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._export_btn)
        btn_row.addWidget(self._export_settings_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self._close_btn)
        root.addLayout(btn_row)

        self._refresh_btn.clicked.connect(self.refresh)
        self._copy_btn.clicked.connect(self._copy_text)
        self._export_btn.clicked.connect(self._export_text)
        self._export_settings_btn.clicked.connect(self._export_settings_ini)
        self._close_btn.clicked.connect(self.close)

        self.refresh()

    def set_app_version_text(self, value: str) -> None:
        self._app_version_text = str(value or "")

    def refresh(self) -> None:
        if self._refresh_thread is not None:
            return
        self._set_refresh_in_progress(True)
        self._text_box.setPlainText("Refreshing system information...")
        thread = QThread(self)
        worker = _SystemInfoWorker(self._app_version_text)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_refresh_finished)
        worker.failed.connect(self._handle_refresh_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._clear_refresh_thread)
        thread.finished.connect(thread.deleteLater)
        self._refresh_thread = thread
        self._refresh_worker = worker
        thread.start()

    def _set_refresh_in_progress(self, active: bool) -> None:
        self._refresh_btn.setEnabled(not active)
        self._copy_btn.setEnabled(not active)
        self._export_btn.setEnabled(not active)
        self._export_settings_btn.setEnabled(not active)

    def _handle_refresh_finished(self, text: str) -> None:
        self._text_box.setPlainText(text)
        self._set_refresh_in_progress(False)

    def _handle_refresh_failed(self, error: str) -> None:
        self._text_box.setPlainText(f"Could not collect system information.\n\n{error}")
        self._set_refresh_in_progress(False)

    def _clear_refresh_thread(self) -> None:
        self._refresh_thread = None
        self._refresh_worker = None

    def closeEvent(self, event) -> None:
        worker = self._refresh_worker
        if worker is not None:
            try:
                worker.cancel_requested.emit()
            except Exception:
                pass
        super().closeEvent(event)

    def _copy_text(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._text_box.toPlainText())

    def _export_text(self) -> None:
        default_name = f"pySSP_SystemInfo_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export System Information",
            os.path.join(os.path.expanduser("~"), default_name),
            "Text Files (*.txt);;All Files (*.*)",
        )
        target = str(file_path or "").strip()
        if not target:
            return
        try:
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(self._text_box.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", f"Could not export system information:\n{exc}")
            return
        QMessageBox.information(self, "Export Complete", f"Exported system information to:\n{target}")

    def _export_settings_ini(self) -> None:
        source = get_settings_path()
        if not source.exists():
            QMessageBox.warning(self, "Export Failed", f"settings.ini not found:\n{source}")
            return
        default_name = f"pySSP_settings_{time.strftime('%Y%m%d_%H%M%S')}.ini"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export settings.ini",
            os.path.join(os.path.expanduser("~"), default_name),
            "INI Files (*.ini);;All Files (*.*)",
        )
        target = str(file_path or "").strip()
        if not target:
            return
        try:
            shutil.copyfile(str(source), target)
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", f"Could not export settings.ini:\n{exc}")
            return
        QMessageBox.information(self, "Export Complete", f"Exported settings.ini to:\n{target}")
