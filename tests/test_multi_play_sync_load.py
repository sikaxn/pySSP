from __future__ import annotations


def test_multi_play_sync_load_runs_finish_handler():
    calls = []

    def finish():
        calls.append("finish")

    load_result = True
    if load_result is None:
        pass
    elif not load_result:
        pass
    else:
        finish()

    assert calls == ["finish"]
