from __future__ import annotations

from .audio_devices import AudioDevicesPageMixin
from .audio_loading_format import AudioLoadingFormatPageMixin
from .colors import ColorsPageMixin
from .common import CommonPageBuilderMixin
from .display import DisplayPageMixin
from .fade import FadePageMixin
from .general import GeneralPageMixin
from .hotkeys import HotkeysPageMixin
from .language import LanguagePageMixin
from .lock_screen import LockScreenPageMixin
from .lyrics import LyricsPageMixin
from .playback import PlaybackPageMixin
from .talk import TalkPageMixin
from .web_remote import WebRemotePageMixin
from .window_layout import WindowLayoutPageMixin


class PageBuilderMixin(
    CommonPageBuilderMixin,
    GeneralPageMixin,
    LanguagePageMixin,
    LockScreenPageMixin,
    HotkeysPageMixin,
    ColorsPageMixin,
    FadePageMixin,
    PlaybackPageMixin,
    AudioDevicesPageMixin,
    AudioLoadingFormatPageMixin,
    TalkPageMixin,
    WebRemotePageMixin,
    LyricsPageMixin,
    DisplayPageMixin,
    WindowLayoutPageMixin,
):
    pass


__all__ = ["PageBuilderMixin"]
