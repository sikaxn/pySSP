from types import SimpleNamespace

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.ui.main_window.actions_input import ActionsInputMixin
from pyssp.ui.main_window.lyrics_stage import LyricsStageMixin
from pyssp.ui.main_window.pages_slots import PagesSlotsMixin
from pyssp.ui.main_window.playback import PlaybackMixin


class _Player:
    def __init__(self):
        self.position_ms = 0

    def duration(self):
        return 120_000

    def setPosition(self, position_ms):
        self.position_ms = position_ms

    def position(self):
        return self.position_ms


class _LyricHost(LyricsStageMixin, ActionsInputMixin, PagesSlotsMixin):
    def __init__(self, player=None, cue_start_ms=0, cue_end_ms=120_000, mode="cue_region", action="ignore_cue"):
        self.current_playing = ("A", 0, 0)
        self.player = player or _Player()
        self.active_player = self.player
        self._cue_start_ms = cue_start_ms
        self._cue_end_ms = cue_end_ms
        self.main_transport_timeline_mode = mode
        self.main_jog_outside_cue_action = action
        self._player_ignore_cue_end = set()
        self._player_end_override_ms = {}
        self.current_duration_ms = 120_000
        self.seek_slider = SimpleNamespace(setValue=self._record_display_position)
        self._mtc_sender = SimpleNamespace(request_resync=lambda: None)
        self.display_position_ms = None
        self.stop_count = 0
        self.refresh_count = 0

    def _player_for_slot_key(self, _slot_key):
        return self.active_player

    def _main_transport_bounds(self):
        if self.main_transport_timeline_mode == "audio_file":
            return 0, self.current_duration_ms
        return self._cue_start_ms, self._cue_end_ms

    def _slot_for_key(self, _slot_key):
        return SimpleNamespace(cue_start_ms=self._cue_start_ms, cue_end_ms=self._cue_end_ms)

    def _cue_start_for_playback(self, slot, _duration_ms):
        return slot.cue_start_ms

    def _cue_end_for_playback(self, slot, _duration_ms):
        return slot.cue_end_ms

    def _record_display_position(self, position_ms):
        self.display_position_ms = position_ms

    def _sync_shadow_transport_from_primary(self, _player):
        pass

    def _stop_playback(self):
        self.stop_count += 1

    def _refresh_lyric_display(self, force=False):
        self.refresh_count += int(force)


def test_lyric_uses_current_audio_clock_when_last_position_sample_is_old():
    player = SimpleNamespace(
        state=lambda: ExternalMediaPlayer.PlayingState,
        position=lambda: 31_000,
        enginePositionMs=lambda: 35_000,
    )
    host = _LyricHost(player=player, cue_start_ms=30_000)

    assert host._lyric_position_ms_for_key(host.current_playing) == 35_000


def test_lyric_and_script_navigator_seek_uses_absolute_file_timestamp():
    host = _LyricHost(cue_start_ms=30_000, cue_end_ms=90_000)

    host._seek_to_lyric_timestamp(35_000)

    assert host.player.position_ms == 35_000
    assert host.display_position_ms == 5_000
    assert host.refresh_count == 1


def test_navigator_seek_outside_cue_applies_selected_jog_behavior():
    host = _LyricHost(cue_start_ms=30_000, cue_end_ms=90_000, action="next_cue_or_stop")

    host._seek_to_lyric_timestamp(10_000)

    assert host.player.position_ms == 10_000
    assert host.display_position_ms == 0
    assert host._player_end_override_ms[id(host.player)] == 30_000


def test_navigator_seek_outside_cue_can_stop_immediately():
    host = _LyricHost(cue_start_ms=30_000, cue_end_ms=90_000, action="stop_immediately")

    host._seek_to_lyric_timestamp(10_000)

    assert host.stop_count == 1


def test_navigator_seek_past_cue_end_can_ignore_cue():
    host = _LyricHost(cue_start_ms=30_000, cue_end_ms=90_000, action="ignore_cue")

    host._seek_to_lyric_timestamp(100_000)

    assert host.player.position_ms == 100_000
    assert host.display_position_ms == 60_000
    assert id(host.player) in host._player_ignore_cue_end


def test_audio_file_mode_navigator_seek_keeps_absolute_transport_position():
    host = _LyricHost(cue_start_ms=30_000, cue_end_ms=90_000, mode="audio_file")

    host._seek_to_lyric_timestamp(35_000)

    assert host.player.position_ms == 35_000
    assert host.display_position_ms == 35_000


def test_navigator_seeks_the_player_for_the_current_lyric():
    host = _LyricHost(cue_start_ms=30_000, cue_end_ms=90_000)
    host.active_player = _Player()

    host._seek_to_lyric_timestamp(35_000)

    assert host.active_player.position_ms == 35_000
    assert host.player.position_ms == 0


def test_playback_start_rebuilds_cue_relative_jog_range_after_media_load():
    host = _LyricHost(cue_start_ms=70_200, cue_end_ms=180_033)
    host.current_duration_ms = 299_470
    host.slider_range = (0, 299_470)
    host.seek_slider = SimpleNamespace(
        setRange=lambda low, high: setattr(host, "slider_range", (low, high)),
        setValue=host._record_display_position,
    )
    host.total_time = SimpleNamespace(setText=lambda value: setattr(host, "total_label", value))
    host.elapsed_time = SimpleNamespace(setText=lambda value: None)
    host.remaining_time = SimpleNamespace(setText=lambda value: None)
    host._refresh_main_jog_meta = lambda display_ms, total_ms: None
    host.main_progress_display_mode = "progress_bar"

    PlaybackMixin._prepare_transport_for_new_playback(host)

    assert host.slider_range == (0, 109_833)
    assert host.display_position_ms == 0
    assert host.total_label == "01:49:24"


def test_playback_start_shows_file_position_in_audio_file_timeline():
    host = _LyricHost(cue_start_ms=70_200, cue_end_ms=180_033, mode="audio_file")
    host.current_duration_ms = 299_470
    host.player.setPosition(70_200)
    host.slider_range = (0, 0)
    host.seek_slider = SimpleNamespace(
        setRange=lambda low, high: setattr(host, "slider_range", (low, high)),
        setValue=host._record_display_position,
    )
    host.total_time = SimpleNamespace(setText=lambda value: setattr(host, "total_label", value))
    host.elapsed_time = SimpleNamespace(setText=lambda value: None)
    host.remaining_time = SimpleNamespace(setText=lambda value: None)
    host._refresh_main_jog_meta = lambda display_ms, total_ms: None
    host.main_progress_display_mode = "progress_bar"

    PlaybackMixin._prepare_transport_for_new_playback(host)

    assert host.slider_range == (0, 299_470)
    assert host.display_position_ms == 70_200
