from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from pyssp.i18n import tr

MANIFEST_MEMBER = "manifest.json"
SETTINGS_MEMBER = "settings.ini"


class ArchiveOperationCancelled(Exception):
    pass


@dataclass(frozen=True)
class PageSelectionItem:
    key: str
    label: str
    checked: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class PackedAudioEntry:
    source_path: str
    archive_member: str
    set_path: str


@dataclass(frozen=True)
class PackReportRow:
    location: str
    slot: int
    title: str
    file_path: str
    status: str
    cause: str = ""


@dataclass(frozen=True)
class UnpackDialogResult:
    package_path: str
    destination_dir: str
    restore_settings: bool
    open_set_after_unpack: bool
    maintain_directory_structure: bool


@dataclass(frozen=True)
class UnpackResult:
    extracted_set_path: str
    extracted_settings_path: str
    audio_path_map: dict[str, str]
    manifest: dict


class PackAudioLibraryDialog(QDialog):
    def __init__(self, items: list[PageSelectionItem], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Pack Audio Library"))
        self.resize(460, 600)

        layout = QVBoxLayout(self)

        note = QLabel(tr("Select pages to include in the packed audio library."))
        note.setWordWrap(True)
        layout.addWidget(note)

        self.page_list = QListWidget(self)
        for item in items:
            widget_item = QListWidgetItem(item.label, self.page_list)
            flags = Qt.ItemIsUserCheckable
            if item.enabled:
                flags |= Qt.ItemIsEnabled | Qt.ItemIsSelectable
            widget_item.setFlags(flags)
            widget_item.setCheckState(Qt.Checked if item.checked and item.enabled else Qt.Unchecked)
            widget_item.setData(Qt.UserRole, item.key)
            font = widget_item.font()
            font.setStrikeOut(not item.enabled)
            widget_item.setFont(font)
            if not item.enabled:
                widget_item.setToolTip(tr("Empty page"))
        layout.addWidget(self.page_list, 1)

        action_row = QHBoxLayout()
        select_all_button = QPushButton(tr("Select All"), self)
        select_all_button.clicked.connect(self._select_all)
        action_row.addWidget(select_all_button)

        deselect_all_button = QPushButton(tr("Deselect All"), self)
        deselect_all_button.clicked.connect(self._deselect_all)
        action_row.addWidget(deselect_all_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.include_settings_checkbox = QCheckBox(tr("Pack pySSP Settings"), self)
        self.include_settings_checkbox.setChecked(False)
        layout.addWidget(self.include_settings_checkbox)

        self.maintain_structure_checkbox = QCheckBox(tr("Maintain directory structure"), self)
        self.maintain_structure_checkbox.setChecked(True)
        layout.addWidget(self.maintain_structure_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_all(self) -> None:
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            if bool(item.flags() & Qt.ItemIsEnabled):
                item.setCheckState(Qt.Checked)

    def _deselect_all(self) -> None:
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            if bool(item.flags() & Qt.ItemIsEnabled):
                item.setCheckState(Qt.Unchecked)

    def selected_keys(self) -> list[str]:
        keys: list[str] = []
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            if item.checkState() == Qt.Checked:
                keys.append(str(item.data(Qt.UserRole)))
        return keys


class UnpackLibraryDialog(QDialog):
    def __init__(self, initial_package_path: str, initial_destination_dir: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Unpack Library"))
        self.resize(640, 220)

        layout = QVBoxLayout(self)

        form = QGridLayout()
        form.setColumnStretch(1, 1)
        layout.addLayout(form)

        form.addWidget(QLabel(tr("pyssppak Location")), 0, 0)
        self.package_path_edit = QLineEdit(initial_package_path, self)
        form.addWidget(self.package_path_edit, 0, 1)
        package_browse = QPushButton(tr("Browse"), self)
        package_browse.clicked.connect(self._browse_package)
        form.addWidget(package_browse, 0, 2)

        form.addWidget(QLabel(tr("Unpack Directory")), 1, 0)
        self.destination_dir_edit = QLineEdit(initial_destination_dir, self)
        form.addWidget(self.destination_dir_edit, 1, 1)
        destination_browse = QPushButton(tr("Browse"), self)
        destination_browse.clicked.connect(self._browse_destination)
        form.addWidget(destination_browse, 1, 2)

        self.restore_settings_checkbox = QCheckBox(tr("Try restore setting if exist"), self)
        self.restore_settings_checkbox.setChecked(True)
        layout.addWidget(self.restore_settings_checkbox)

        self.open_set_checkbox = QCheckBox(tr("Open unpack set file after unpack"), self)
        self.open_set_checkbox.setChecked(True)
        layout.addWidget(self.open_set_checkbox)

        self.maintain_structure_checkbox = QCheckBox(tr("Maintain directory structure"), self)
        self.maintain_structure_checkbox.setChecked(True)
        layout.addWidget(self.maintain_structure_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.package_path_edit.textChanged.connect(self._auto_update_destination_dir)
        self._auto_update_destination_dir(self.package_path_edit.text())

    def _browse_package(self) -> None:
        start_dir = os.path.dirname(self.package_path_edit.text().strip()) or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select pySSP Audio Library"),
            start_dir,
            tr("pySSP Audio Library (*.pyssppak);;All Files (*.*)"),
        )
        if file_path:
            self.package_path_edit.setText(file_path)

    def _browse_destination(self) -> None:
        start_dir = self.destination_dir_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, tr("Select Unpack Directory"), start_dir)
        if directory:
            self.destination_dir_edit.setText(directory)

    def _auto_update_destination_dir(self, package_path: str) -> None:
        package_path = str(package_path or "").strip()
        if not package_path:
            return
        self.destination_dir_edit.setText(default_unpack_directory(package_path))

    def values(self) -> UnpackDialogResult:
        return UnpackDialogResult(
            package_path=self.package_path_edit.text().strip(),
            destination_dir=self.destination_dir_edit.text().strip(),
            restore_settings=bool(self.restore_settings_checkbox.isChecked()),
            open_set_after_unpack=bool(self.open_set_checkbox.isChecked()),
            maintain_directory_structure=bool(self.maintain_structure_checkbox.isChecked()),
        )


class PackReportDialog(QDialog):
    def __init__(self, rows: list[PackReportRow], default_export_dir: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Pack Audio Library Report"))
        self.resize(820, 520)
        self._rows = list(rows)
        self._default_export_dir = default_export_dir

        layout = QVBoxLayout(self)
        packed_count = sum(1 for row in self._rows if row.status.casefold() == "packed")
        skipped_count = sum(1 for row in self._rows if row.status.casefold() != "packed")

        summary = QLabel(f"{tr('Packed:')} {packed_count} {tr('button(s)')} | {tr('Skipped:')} {skipped_count} {tr('button(s)')}")
        layout.addWidget(summary)

        self.results_list = QListWidget(self)
        for row in self._rows:
            item = QListWidgetItem(pack_report_row_to_line(row))
            self.results_list.addItem(item)
        layout.addWidget(self.results_list, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        export_button = QPushButton(tr("Export CSV"), self)
        export_button.clicked.connect(self._export_csv)
        button_row.addWidget(export_button)
        close_button = QPushButton(tr("Close"), self)
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def _export_csv(self) -> None:
        initial_path = os.path.join(self._default_export_dir or str(Path.home()), "PackAudioLibraryReport.csv")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export"),
            initial_path,
            tr("CSV (*.csv);;All Files (*.*)"),
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"
        write_pack_report_csv(file_path, self._rows)


def default_unpack_directory(package_path: str) -> str:
    appdata = os.getenv("APPDATA")
    base = (Path(appdata) / "pyssp") if appdata else (Path.home() / ".config" / "pyssp")
    stem = Path(package_path).stem or "package"
    return str((base / "unpack" / stem).resolve())


def build_archive_audio_entries(file_paths: list[str], maintain_directory_structure: bool) -> list[PackedAudioEntry]:
    entries: list[PackedAudioEntry] = []
    used_members: set[str] = set()
    for index, source_path in enumerate(file_paths, start=1):
        archive_member = (
            _structured_archive_member(source_path)
            if maintain_directory_structure
            else _flattened_archive_member(source_path, index)
        )
        candidate = archive_member
        suffix = 2
        while candidate.casefold() in used_members:
            stem, ext = os.path.splitext(archive_member)
            candidate = f"{stem}_{suffix}{ext}"
            suffix += 1
        used_members.add(candidate.casefold())
        entries.append(PackedAudioEntry(source_path=source_path, archive_member=candidate, set_path=candidate))
    return entries


def build_manifest(set_member_name: str, audio_entries: list[PackedAudioEntry], settings_included: bool) -> dict:
    return {
        "format": "pyssppak",
        "version": 1,
        "set_member": set_member_name,
        "settings_member": SETTINGS_MEMBER if settings_included else "",
        "audio_entries": [
            {
                "source_name": os.path.basename(entry.source_path),
                "archive_member": entry.archive_member,
                "set_path": entry.set_path,
            }
            for entry in audio_entries
        ],
    }


def write_manifest(archive: zipfile.ZipFile, manifest: dict) -> None:
    archive.writestr(MANIFEST_MEMBER, json.dumps(manifest, indent=2))


def read_pyssppak_manifest(package_path: str) -> dict:
    with zipfile.ZipFile(package_path, "r") as archive:
        try:
            raw = archive.read(MANIFEST_MEMBER)
        except KeyError:
            return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def unpack_pyssppak(
    package_path: str,
    destination_dir: str,
    maintain_directory_structure: bool,
    progress_callback=None,
    is_cancelled=None,
) -> UnpackResult:
    manifest = read_pyssppak_manifest(package_path)
    audio_entries = manifest.get("audio_entries", []) if isinstance(manifest.get("audio_entries"), list) else []
    set_member = str(manifest.get("set_member") or "")
    settings_member = str(manifest.get("settings_member") or "")
    if not set_member:
        raise ValueError("Package manifest is missing the packed .set entry.")

    os.makedirs(destination_dir, exist_ok=True)
    total = 1 + len(audio_entries) + (1 if settings_member else 0)
    step = 0
    audio_path_map: dict[str, str] = {}
    used_targets: set[str] = set()

    with zipfile.ZipFile(package_path, "r") as archive:
        _check_cancelled(is_cancelled)
        extracted_set_path = _extract_to_file(
            archive,
            set_member,
            os.path.join(destination_dir, os.path.basename(set_member)),
        )
        step += 1
        _report_progress(progress_callback, step, total, f"Extracting {os.path.basename(set_member)}...")

        for item in audio_entries:
            _check_cancelled(is_cancelled)
            if not isinstance(item, dict):
                continue
            archive_member = str(item.get("archive_member") or "")
            set_path = str(item.get("set_path") or archive_member)
            if not archive_member:
                continue
            target_path = build_unpack_target_path(destination_dir, archive_member, maintain_directory_structure, used_targets)
            extracted_audio_path = _extract_to_file(archive, archive_member, target_path)
            audio_path_map[set_path] = extracted_audio_path
            step += 1
            _report_progress(progress_callback, step, total, f"Extracting {os.path.basename(extracted_audio_path)}...")

        extracted_settings_path = ""
        if settings_member:
            _check_cancelled(is_cancelled)
            extracted_settings_path = _extract_to_file(
                archive,
                settings_member,
                os.path.join(destination_dir, SETTINGS_MEMBER),
            )
            step += 1
            _report_progress(progress_callback, step, total, "Extracting settings.ini...")

    return UnpackResult(
        extracted_set_path=os.path.abspath(extracted_set_path),
        extracted_settings_path=os.path.abspath(extracted_settings_path) if extracted_settings_path else "",
        audio_path_map=audio_path_map,
        manifest=manifest,
    )


def build_unpack_target_path(
    destination_dir: str,
    archive_member: str,
    maintain_directory_structure: bool,
    used_targets: set[str],
) -> str:
    if maintain_directory_structure:
        target_path = os.path.join(destination_dir, *archive_member.split("/"))
    else:
        basename = os.path.basename(archive_member)
        target_path = os.path.join(destination_dir, "audio", basename)
    target_path = _unique_target_path(target_path, used_targets)
    return os.path.abspath(target_path)


def rewrite_packed_set_paths(set_file_path: str, replacements: dict[str, str]) -> None:
    text, encoding = _read_text_with_fallback(set_file_path)
    lines = text.splitlines(True)
    output: list[str] = []
    for line in lines:
        updated = line
        if "=" in line:
            key, value = line.split("=", 1)
            if re.fullmatch(r"s\d+", key.strip(), re.IGNORECASE):
                raw_value = value.rstrip("\r\n").strip()
                replacement = replacements.get(raw_value)
                if replacement:
                    line_ending = value[len(value.rstrip("\r\n")) :]
                    updated = f"{key}={replacement}{line_ending}"
        output.append(updated)
    with open(set_file_path, "w", encoding=encoding, newline="") as fh:
        fh.write("".join(output))


def pack_report_row_to_line(row: PackReportRow) -> str:
    base = f"{row.status} | {row.location} - Button {row.slot} | {row.title} | {row.file_path}"
    if row.cause:
        return f"{base} | {row.cause}"
    return base


def write_pack_report_csv(file_path: str, rows: list[PackReportRow]) -> None:
    def _csv_cell(value: str) -> str:
        cell = str(value or "").replace("\r", " ").replace("\n", " ").replace('"', '""')
        return f'"{cell}"'

    lines = ['"Page","Button Number","Sound Button Name","File Path","Status","Cause"']
    for row in rows:
        lines.append(
            ",".join(
                [
                    _csv_cell(row.location),
                    _csv_cell(str(row.slot)),
                    _csv_cell(row.title),
                    _csv_cell(row.file_path),
                    _csv_cell(row.status),
                    _csv_cell(row.cause),
                ]
            )
        )
    with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write("\r\n".join(lines))


def _flattened_archive_member(source_path: str, index: int) -> str:
    basename = os.path.basename(source_path) or f"audio_{index}"
    return f"audio/{index:03d}_{_sanitize_segment(basename)}"


def _structured_archive_member(source_path: str) -> str:
    path = os.path.abspath(source_path)
    drive, tail = os.path.splitdrive(path)
    segments = [segment for segment in re.split(r"[\\/]+", tail.strip("\\/")) if segment]
    safe_segments = [_sanitize_segment(segment) for segment in segments]
    if drive:
        safe_segments.insert(0, _sanitize_segment(drive.replace(":", "")))
    return "/".join(["audio", *safe_segments]) if safe_segments else "audio/file"


def _sanitize_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(value or "").strip())
    return cleaned or "item"


def _unique_target_path(target_path: str, used_targets: set[str]) -> str:
    base = os.path.abspath(target_path)
    candidate = base
    stem, ext = os.path.splitext(base)
    suffix = 2
    while candidate.casefold() in used_targets:
        candidate = f"{stem}_{suffix}{ext}"
        suffix += 1
    used_targets.add(candidate.casefold())
    return candidate


def _report_progress(callback, current: int, total: int, label: str) -> None:
    if callback is not None:
        callback(current, total, label)


def _check_cancelled(is_cancelled) -> None:
    if is_cancelled is not None and is_cancelled():
        raise ArchiveOperationCancelled()


def _extract_to_file(archive: zipfile.ZipFile, member: str, target_path: str) -> str:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with archive.open(member, "r") as source, open(target_path, "wb") as target:
        shutil.copyfileobj(source, target)
    return target_path


def _read_text_with_fallback(file_path: str) -> tuple[str, str]:
    raw = open(file_path, "rb").read()
    for encoding in ("utf-8-sig", "utf-16", "gbk", "cp1252", "latin1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="replace"), "latin1"
