from pyssp.audio_runtime import PlaybackRuntimeTracker


class _DummyPlayer:
    pass


def test_runtime_tracker_assigns_monotonic_ids_and_selects_newest_normal_mode():
    tracker = PlaybackRuntimeTracker()
    a = _DummyPlayer()
    b = _DummyPlayer()

    assert tracker.mark_started(a, ("A", 0, 0)) == 0
    assert tracker.mark_started(b, ("A", 0, 1)) == 1
    assert tracker.runtime_id_for(a) == 0
    assert tracker.runtime_id_for(b) == 1
    assert tracker.timecode_player([a, b], multi_play_enabled=False) is b


def test_runtime_tracker_uses_smallest_active_id_for_multi_play():
    tracker = PlaybackRuntimeTracker()
    a = _DummyPlayer()
    b = _DummyPlayer()
    c = _DummyPlayer()

    tracker.mark_started(a, ("A", 0, 0))
    tracker.mark_started(b, ("A", 0, 1))
    tracker.mark_started(c, ("A", 0, 2))
    tracker.clear(a)

    assert tracker.timecode_player([a, b, c], multi_play_enabled=True) is b
    assert tracker.oldest_active_player([a, b, c]) is b
    assert tracker.newest_active_player([a, b, c]) is c
