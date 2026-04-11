from __future__ import annotations

import configparser
import glob
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
from typing import List, Optional

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


def _get_library_versions() -> List[str]:
    versions = [
        f"python: {platform.python_version()}",
        f"PyQt5: {_safe_package_version('PyQt5')}",
        f"pygame-ce: {_safe_package_version('pygame-ce')}",
        f"numpy: {_safe_package_version('numpy')}",
        f"sounddevice: {_safe_package_version('sounddevice')}",
        f"Flask: {_safe_package_version('Flask')}",
        f"simple-websocket: {_safe_package_version('simple-websocket')}",
        f"websockets: {_safe_package_version('websockets')}",
        f"Werkzeug: {_safe_package_version('Werkzeug')}",
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


def _resolve_sdl_mixer_library_path(pygame_module) -> str:
    base = os.path.dirname(getattr(pygame_module, "__file__", "") or "")
    if not base:
        return ""
    candidates = [
        os.path.join(base, "SDL2_mixer.dll"),
        os.path.join(base, "libSDL2_mixer-2.0.0.dylib"),
        os.path.join(base, "libSDL2_mixer.dylib"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    for pattern in ["*SDL2_mixer*.dll", "*SDL2_mixer*.dylib", "*SDL2_mixer*.so", "*SDL2_mixer*.so.*"]:
        matches = glob.glob(os.path.join(base, pattern))
        if matches:
            return matches[0]
    return ""


def _get_pygame_decoder_report() -> List[str]:
    lines: List[str] = []
    original_audio_driver = os.environ.get("SDL_AUDIODRIVER")
    touched_audio_driver = False
    try:
        import ctypes
        import pygame

        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                os.environ["SDL_AUDIODRIVER"] = "dummy"
                touched_audio_driver = True
                pygame.mixer.init()

        lines.append(f"pygame version: {getattr(pygame.version, 'ver', 'unknown')}")
        try:
            lines.append(f"SDL version: {pygame.get_sdl_version()}")
        except Exception as exc:
            lines.append(f"SDL version: unavailable ({exc})")

        try:
            lines.append(f"SDL_mixer version: {pygame.mixer.get_sdl_mixer_version()}")
        except Exception as exc:
            lines.append(f"SDL_mixer version: unavailable ({exc})")

        mixer_lib = _resolve_sdl_mixer_library_path(pygame)
        lines.append(f"SDL_mixer shared library path: {mixer_lib or 'not found'}")
        if not mixer_lib:
            lines.append("pygame-ce supported format: unable to locate SDL2_mixer shared library")
            return lines

        lib = ctypes.CDLL(mixer_lib)
        mix_init_features = []
        if hasattr(lib, "Mix_Init"):
            lib.Mix_Init.argtypes = [ctypes.c_int]
            lib.Mix_Init.restype = ctypes.c_int
            mix_init_flac = 0x1
            mix_init_mod = 0x2
            mix_init_mp3 = 0x8
            mix_init_ogg = 0x10
            mix_init_mid = 0x20
            mix_init_opus = 0x40
            mix_init_wavpack = 0x80
            all_flags = (
                mix_init_flac
                | mix_init_mod
                | mix_init_mp3
                | mix_init_ogg
                | mix_init_mid
                | mix_init_opus
                | mix_init_wavpack
            )
            mask = int(lib.Mix_Init(all_flags))
            lines.append(f"Mix_Init mask: 0x{mask:X}")
            for name, flag in [
                ("FLAC", mix_init_flac),
                ("MOD", mix_init_mod),
                ("MP3", mix_init_mp3),
                ("OGG", mix_init_ogg),
                ("MID", mix_init_mid),
                ("OPUS", mix_init_opus),
                ("WAVPACK", mix_init_wavpack),
            ]:
                if mask & flag:
                    mix_init_features.append(name)
            lines.append("Mix_Init features: " + (", ".join(mix_init_features) if mix_init_features else "none"))

        lib.Mix_GetNumChunkDecoders.restype = ctypes.c_int
        lib.Mix_GetChunkDecoder.argtypes = [ctypes.c_int]
        lib.Mix_GetChunkDecoder.restype = ctypes.c_char_p

        chunk_decoders: List[str] = []
        chunk_count = int(lib.Mix_GetNumChunkDecoders())
        lines.append(f"Chunk decoders count: {chunk_count}")
        for idx in range(max(0, chunk_count)):
            raw = lib.Mix_GetChunkDecoder(idx)
            if not raw:
                continue
            decoder_name = raw.decode("utf-8", errors="replace")
            chunk_decoders.append(decoder_name)
            lines.append(f"Chunk decoder [{idx}]: {decoder_name}")

        music_decoders: List[str] = []
        if hasattr(lib, "Mix_GetNumMusicDecoders") and hasattr(lib, "Mix_GetMusicDecoder"):
            lib.Mix_GetNumMusicDecoders.restype = ctypes.c_int
            lib.Mix_GetMusicDecoder.argtypes = [ctypes.c_int]
            lib.Mix_GetMusicDecoder.restype = ctypes.c_char_p
            music_count = int(lib.Mix_GetNumMusicDecoders())
            lines.append(f"Music decoders count: {music_count}")
            for idx in range(max(0, music_count)):
                raw = lib.Mix_GetMusicDecoder(idx)
                if not raw:
                    continue
                decoder_name = raw.decode("utf-8", errors="replace")
                music_decoders.append(decoder_name)
                lines.append(f"Music decoder [{idx}]: {decoder_name}")

        lines.append("pygame-ce supported format (chunk): " + (", ".join(_dedupe(chunk_decoders)) or "none"))
        lines.append("pygame-ce supported format (music): " + (", ".join(_dedupe(music_decoders)) or "none"))
        base = os.path.dirname(getattr(pygame, "__file__", "") or "")
        codec_bins = []
        for token in ["ogg", "vorbis", "opus", "flac", "mp3", "wavpack", "xmp", "modplug", "mikmod"]:
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.dll")))
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.dylib")))
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.so")))
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.so.*")))
        codec_bins = _dedupe([os.path.basename(path) for path in codec_bins])
        lines.append("Detected codec shared libraries: " + (", ".join(codec_bins) if codec_bins else "none"))
    except Exception as exc:
        lines.append(f"pygame-ce supported format: unavailable ({exc})")
    finally:
        try:
            import pygame

            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except Exception:
            pass
        if touched_audio_driver:
            if original_audio_driver is None:
                if "SDL_AUDIODRIVER" in os.environ:
                    del os.environ["SDL_AUDIODRIVER"]
            else:
                os.environ["SDL_AUDIODRIVER"] = original_audio_driver
    return lines


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


def build_system_information_text(app_version_text: str) -> str:
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
    for item in _get_pygame_decoder_report():
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


class SystemInformationDialog(QDialog):
    def __init__(self, app_version_text: str, parent=None) -> None:
        super().__init__(parent)
        self._app_version_text = str(app_version_text or "")
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
        self._text_box.setPlainText(build_system_information_text(self._app_version_text))

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
