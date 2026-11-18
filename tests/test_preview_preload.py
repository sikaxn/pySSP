from __future__ import annotations

from pyssp.ui import preview_preload


class _ProcessService:
    def __init__(self) -> None:
        self.commands = []

    def post_runtime(self, command, payload) -> None:
        self.commands.append((command, payload))

    def is_audio_preloaded(self, path: str) -> bool:
        return path == "ready.wav"


def test_editor_preload_uses_preview_players_process(monkeypatch) -> None:
    service = _ProcessService()
    bridge = preview_preload.PreviewPreload(service)
    monkeypatch.setattr(
        preview_preload, "request_audio_preload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("UI preload used")),
    )

    bridge.request("ready.wav")

    assert service.commands == [(
        "preload", {"paths": ["ready.wav"], "prioritize": True, "force": True},
    )]
    assert bridge.is_ready("ready.wav")
