from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyssp.i18n import normalize_language, tr


class GettingStartedDialog(QDialog):
    def __init__(
        self,
        *,
        language: str = "en",
        version_text: str,
        build_text: str,
        beta_build: bool,
        splash_image_path: str = "",
        add_page_image_path: str = "",
        drag_file_image_path: str = "",
        open_audio_device_options: Optional[Callable[[], None]] = None,
        open_latest_version_page: Optional[Callable[[], None]] = None,
        open_docs_page: Optional[Callable[[], None]] = None,
        open_options_page: Optional[Callable[[], None]] = None,
        open_about_window: Optional[Callable[[], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._language = normalize_language(language)
        self._version_text = str(version_text or "")
        self._build_text = str(build_text or "")
        self._beta_build = bool(beta_build)
        self._open_audio_device_options = open_audio_device_options
        self._open_latest_version_page = open_latest_version_page
        self._open_docs_page = open_docs_page
        self._open_options_page = open_options_page
        self._open_about_window = open_about_window

        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self.resize(980, 760)
        self.setStyleSheet("QDialog{background:#FFFDF7;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        self._page_indicator = QLabel("", self)
        self._page_indicator.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._page_indicator.setStyleSheet("QLabel{color:#7A6E5E;font-size:12pt;font-weight:600;}")
        root.addWidget(self._page_indicator)

        self._stack = QStackedWidget(self)
        root.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_welcome_page(splash_image_path))
        if self._beta_build:
            self._stack.addWidget(self._build_beta_page())
        self._stack.addWidget(self._build_add_sound_page(add_page_image_path, drag_file_image_path))
        self._stack.addWidget(self._build_audio_device_page())
        self._stack.addWidget(self._build_finish_page())

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self._next_button = QPushButton(self)
        self._next_button.setMinimumHeight(78)
        next_font = QFont(self.font())
        next_font.setPointSize(max(next_font.pointSize(), 18))
        next_font.setBold(True)
        self._next_button.setFont(next_font)
        self._next_button.setMinimumWidth(260)
        self._next_button.setStyleSheet(
            "QPushButton{background:#177245;color:white;border:0;border-radius:18px;padding:16px 34px;}"
            "QPushButton:hover{background:#125C37;}"
            "QPushButton:pressed{background:#0E492C;}"
        )
        self._next_button.clicked.connect(self._advance_page)
        button_row.addWidget(self._next_button)

        self._close_button = QPushButton(self)
        self._close_button.setMinimumHeight(64)
        close_font = QFont(self.font())
        close_font.setPointSize(max(close_font.pointSize(), 15))
        close_font.setBold(True)
        self._close_button.setFont(close_font)
        self._close_button.setMinimumWidth(220)
        self._close_button.setStyleSheet(
            "QPushButton{background:#F0E7D9;color:#3E3429;border:0;border-radius:18px;padding:14px 28px;}"
            "QPushButton:hover{background:#E7DCCB;}"
            "QPushButton:pressed{background:#DDD0BC;}"
        )
        self._close_button.clicked.connect(self.close)
        button_row.addWidget(self._close_button)

        root.addLayout(button_row)
        self.set_language(self._language)
        self._sync_buttons()

    def _build_welcome_page(self, splash_image_path: str) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        self._welcome_title = QLabel(page)
        title_font = QFont(self.font())
        title_font.setPointSize(max(title_font.pointSize(), 26))
        title_font.setBold(True)
        self._welcome_title.setFont(title_font)
        self._welcome_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._welcome_title)

        self._welcome_subtitle = QLabel(page)
        self._welcome_subtitle.setAlignment(Qt.AlignCenter)
        self._welcome_subtitle.setStyleSheet("QLabel{font-size:16pt;color:#6D6256;font-weight:500;}")
        layout.addWidget(self._welcome_subtitle)

        splash_label = self._image_label(splash_image_path, max_width=760, max_height=330)
        splash_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(splash_label, 1)

        info_card = self._card_widget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 10, 18, 10)
        info_layout.setSpacing(10)
        self._version_label = self._info_line()
        self._build_label = self._info_line()
        info_layout.addWidget(self._version_label)
        info_layout.addWidget(self._build_label)
        layout.addWidget(info_card)

        self._welcome_notice = QLabel(page)
        self._welcome_notice.setAlignment(Qt.AlignCenter)
        self._welcome_notice.setWordWrap(True)
        self._welcome_notice.setStyleSheet("QLabel{font-size:13pt;color:#766A5E;line-height:1.35;padding:8px 24px;}")
        layout.addWidget(self._welcome_notice)
        return page

    def _build_beta_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(18)
        layout.addStretch(1)

        self._beta_title = QLabel(page)
        title_font = QFont(self.font())
        title_font.setPointSize(max(title_font.pointSize(), 24))
        title_font.setBold(True)
        self._beta_title.setFont(title_font)
        self._beta_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._beta_title)

        self._beta_body = QLabel(page)
        self._beta_body.setAlignment(Qt.AlignCenter)
        self._beta_body.setWordWrap(True)
        self._beta_body.setStyleSheet(
            "QLabel{background:#FFF3CD;color:#6A4A00;border:0;border-radius:22px;padding:30px;font-size:16pt;line-height:1.4;}"
        )
        layout.addWidget(self._beta_body)
        layout.addStretch(1)
        return page

    def _build_add_sound_page(self, add_page_image_path: str, drag_file_image_path: str) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        self._add_sound_title = QLabel(page)
        self._add_sound_title.setStyleSheet("QLabel{font-size:22pt;font-weight:700;color:#2B221A;}")
        layout.addWidget(self._add_sound_title)

        self._add_sound_body = QLabel(page)
        self._add_sound_body.setWordWrap(True)
        self._add_sound_body.setStyleSheet("QLabel{font-size:15pt;color:#5C5348;}")
        layout.addWidget(self._add_sound_body)

        self._add_sound_alt = QLabel(page)
        self._add_sound_alt.setWordWrap(True)
        self._add_sound_alt.setStyleSheet("QLabel{font-size:13pt;color:#6C5F52;padding:2px 0 4px 0;}")
        layout.addWidget(self._add_sound_alt)

        self._add_sound_warning = QLabel(page)
        self._add_sound_warning.setWordWrap(True)
        self._add_sound_warning.setStyleSheet(
            "QLabel{background:#F9E9D7;color:#6A4A00;border:0;border-radius:18px;padding:18px;font-size:13pt;line-height:1.35;}"
        )
        layout.addWidget(self._add_sound_warning)

        image_row = QHBoxLayout()
        image_row.setSpacing(12)
        self._add_page_card_title, add_page_card = self._image_card(add_page_image_path)
        self._drag_file_card_title, drag_file_card = self._image_card(drag_file_image_path)
        image_row.addWidget(add_page_card, 1)
        image_row.addWidget(drag_file_card, 1)
        layout.addLayout(image_row, 1)
        return page

    def _build_audio_device_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.addStretch(1)

        self._audio_device_title = QLabel(page)
        self._audio_device_title.setStyleSheet("QLabel{font-size:22pt;font-weight:700;color:#2B221A;}")
        self._audio_device_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._audio_device_title)

        self._audio_device_body = QLabel(page)
        self._audio_device_body.setAlignment(Qt.AlignCenter)
        self._audio_device_body.setWordWrap(True)
        self._audio_device_body.setStyleSheet("QLabel{font-size:15pt;color:#5C5348;}")
        layout.addWidget(self._audio_device_body)

        self._audio_device_button = QPushButton(page)
        self._audio_device_button.setMinimumHeight(58)
        self._audio_device_button.setStyleSheet(
            "QPushButton{font-size:14pt;font-weight:600;padding:12px 22px;background:#F3E9D8;border:0;border-radius:16px;color:#3E3429;}"
            "QPushButton:hover{background:#EADFCB;}"
            "QPushButton:pressed{background:#DFD0B8;}"
        )
        self._audio_device_button.clicked.connect(self._handle_open_audio_device_options)
        layout.addWidget(self._audio_device_button, 0, Qt.AlignHCenter)
        layout.addStretch(1)
        return page

    def _build_finish_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        self._finish_title = QLabel(page)
        self._finish_title.setStyleSheet("QLabel{font-size:22pt;font-weight:700;color:#2B221A;}")
        layout.addWidget(self._finish_title)

        self._finish_body = QLabel(page)
        self._finish_body.setWordWrap(True)
        self._finish_body.setStyleSheet("QLabel{font-size:15pt;color:#5C5348;}")
        layout.addWidget(self._finish_body)

        actions = self._card_widget()
        actions_layout = QVBoxLayout(actions)
        actions_layout.setSpacing(10)
        self._latest_button = self._action_button(self._handle_open_latest_version_page)
        self._docs_button = self._action_button(self._handle_open_docs_page)
        self._options_button = self._action_button(self._handle_open_options_page)
        self._about_button = self._action_button(self._handle_open_about_window)
        actions_layout.addWidget(self._latest_button)
        actions_layout.addWidget(self._docs_button)
        actions_layout.addWidget(self._options_button)
        actions_layout.addWidget(self._about_button)
        layout.addWidget(actions)
        layout.addStretch(1)
        return page

    def _action_button(self, handler: Callable[[], None]) -> QPushButton:
        button = QPushButton(self)
        button.setMinimumHeight(54)
        button.setStyleSheet(
            "QPushButton{font-size:13.5pt;font-weight:600;padding:10px 18px;text-align:left;background:#F6EEDF;border:0;border-radius:16px;color:#3E3429;}"
            "QPushButton:hover{background:#EEE4D1;}"
            "QPushButton:pressed{background:#E5D8C1;}"
        )
        button.clicked.connect(handler)
        return button

    def _card_widget(self) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.NoFrame)
        frame.setStyleSheet("QFrame{background:#F8F2E8;border:0;border-radius:22px;}")
        return frame

    def _image_card(self, image_path: str) -> tuple[QLabel, QWidget]:
        frame = self._card_widget()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(frame)
        title.setStyleSheet("QLabel{font-size:15pt;font-weight:700;color:#342A21;}")
        layout.addWidget(title)

        image = self._image_label(image_path, max_width=440, max_height=320)
        image.setAlignment(Qt.AlignCenter)
        layout.addWidget(image, 1)
        return title, frame

    def _image_label(self, image_path: str, *, max_width: int, max_height: int) -> QLabel:
        label = QLabel(self)
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setMinimumHeight(min(200, max_height))
        pixmap = QPixmap(str(image_path or "").strip())
        if not pixmap.isNull():
            label.setPixmap(pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return label
        label.setText("Image not found")
        label.setStyleSheet("QLabel{color:#7A6E5E;border:0;border-radius:12px;padding:16px;background:#F4EBDC;font-size:13pt;}")
        return label

    def _info_line(self) -> QLabel:
        label = QLabel(self)
        label.setStyleSheet("QLabel{font-size:15pt;font-weight:600;color:#342A21;}")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self.setWindowTitle(tr("Getting Started", self._language))
        self._welcome_title.setText(tr("Welcome to pySSP", self._language))
        self._welcome_subtitle.setText(tr("Python Sports Sounds Pro", self._language))
        self._version_label.setText(f"{tr('Version:', self._language)} {self._version_text or '-'}")
        self._build_label.setText(f"{tr('Build:', self._language)} {self._build_text or '-'}")
        self._welcome_notice.setText(
            tr(
                "pySSP is an independent project. It is not affiliated with, endorsed by, or distributed by the original Sports Sounds Pro (SSP).",
                self._language,
            )
        )
        if self._beta_build:
            self._beta_title.setText(tr("Beta Build Warning", self._language))
            self._beta_body.setText(
                tr(
                    "You are running a beta build.\n\nExpect unfinished features, behavior changes, and possible regressions.\nBack up your settings and verify playback before live use.",
                    self._language,
                )
            )
        self._add_sound_title.setText(tr("Add a Page and Load a Sound", self._language))
        self._add_sound_body.setText(
            tr("To start, add a page, then drag a file to a sound button to add sound.", self._language)
        )
        self._add_sound_alt.setText(
            tr("Alternatively, open an existing SSP .set file to bring in your current pages and buttons.", self._language)
        )
        self._add_sound_warning.setText(
            tr(
                "Compatibility warning: not all pySSP features are supported by the original SSP. If you move sets back to the original SSP, some pySSP-specific settings or behavior may not carry over.",
                self._language,
            )
        )
        self._add_page_card_title.setText(tr("1. Add a page", self._language))
        self._drag_file_card_title.setText(tr("2. Drag file to sound button", self._language))
        self._audio_device_title.setText(tr("Set the Audio Output Device", self._language))
        self._audio_device_body.setText(
            tr("Set the audio output device under Setup > Options > Audio Device & Timecode.", self._language)
        )
        self._audio_device_button.setText(tr("Open Audio Device Options", self._language))
        self._finish_title.setText(tr("You're Ready", self._language))
        self._finish_body.setText(
            tr("Use the links below to open release notes, docs, options, or license info any time.", self._language)
        )
        self._latest_button.setText(tr("Get Latest Version / Release Log", self._language))
        self._docs_button.setText(tr("Open Docs", self._language))
        self._options_button.setText(tr("Open Options", self._language))
        self._about_button.setText(tr("Open About / License", self._language))
        self._next_button.setText(tr("Next", self._language))
        self._close_button.setText(tr("Close", self._language))
        self._sync_buttons()

    def _advance_page(self) -> None:
        index = self._stack.currentIndex()
        if index < (self._stack.count() - 1):
            self._stack.setCurrentIndex(index + 1)
            self._sync_buttons()

    def reset_to_first_page(self) -> None:
        self._stack.setCurrentIndex(0)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        page_count = self._stack.count()
        page_index = self._stack.currentIndex()
        is_last = page_index >= (page_count - 1)
        self._page_indicator.setText(
            tr("Page {current} of {total}", self._language).format(current=page_index + 1, total=page_count)
        )
        self._next_button.setVisible(not is_last)
        self._close_button.setVisible(is_last)

    def _handle_open_audio_device_options(self) -> None:
        if callable(self._open_audio_device_options):
            self._open_audio_device_options()

    def _handle_open_latest_version_page(self) -> None:
        if callable(self._open_latest_version_page):
            self._open_latest_version_page()

    def _handle_open_docs_page(self) -> None:
        if callable(self._open_docs_page):
            self._open_docs_page()

    def _handle_open_options_page(self) -> None:
        if callable(self._open_options_page):
            self._open_options_page()

    def _handle_open_about_window(self) -> None:
        if callable(self._open_about_window):
            self._open_about_window()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_buttons()
