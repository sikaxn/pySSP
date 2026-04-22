from pyssp.audio_runtime import PlaybackRuntimeTracker


class _DummyPlayer:
    def __init__(self, name: str) -> None:
        self.name = name


def test_newest_active_player_remains_after_oldest_cleared():
    tracker = PlaybackRuntimeTracker()
    a = _DummyPlayer("a")
    b = _DummyPlayer("b")
    c = _DummyPlayer("c")

    tracker.mark_started(a, ("A", 0, 0))
    tracker.mark_started(b, ("A", 0, 1))
    tracker.mark_started(c, ("A", 0, 2))
    tracker.clear(c)

    newest = tracker.newest_active_player([a, b, c])
    assert newest is b
    assert tracker.slot_key_for(newest) == ("A", 0, 1)
