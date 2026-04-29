import json

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMessageBox

from pyssp.ui.remote_display_client import RemoteWebSocketClient
from pyssp.ui.remote_display_client import RemoteDisplayClientWindow


def test_request_lyric_bundle_uses_legacy_http_mode_when_new_route_is_unsupported():
    client = RemoteWebSocketClient("127.0.0.1", 5050)
    client._lyric_query_supported = False

    client.request_lyric_bundle()

    path, body = client._outbound.get_nowait()
    assert path == "__legacy_http_lyric_bundle__"
    assert body is None


def test_remote_ws_client_falls_back_to_legacy_http_bundle_on_query_route_error():
    client = RemoteWebSocketClient("127.0.0.1", 5050)
    bundles = []
    client.lyric_bundle_received.connect(lambda payload: bundles.append(payload))
    client._pending_paths["req-1"] = "/api/query/lyric-openlp"
    client._latest_ws_state = {"item": "a-1-1", "slide": 2, "display": "show"}
    expected = {
        "ws": {"item": "a-1-1", "slide": 2, "display": "show"},
        "live_items": {"item": "a-1-1", "slides": [{"html": "hello"}]},
        "service_items": [{"title": "Song", "selected": True}],
    }
    client._fetch_legacy_lyric_bundle_http = lambda: expected  # type: ignore[method-assign]

    client._handle_message(
        json.dumps(
            {
                "type": "api_response",
                "id": "req-1",
                "status": 404,
                "payload": {
                    "ok": False,
                    "error": {"code": "not_found", "message": "Unknown API path."},
                },
            }
        )
    )

    assert client._lyric_query_supported is False
    assert bundles == [expected]


def test_remote_display_hides_zero_width_idle_placeholder():
    app = QApplication.instance() or QApplication([])
    window = RemoteDisplayClientWindow()
    try:
        window._stop_connection()
        window._ws_state = {"item": "", "slide": 0, "display": "show", "blank": False}
        window._lyric_bundle = {
            "ws": dict(window._ws_state),
            "live_items": {
                "item": "",
                "slides": [
                    {
                        "title": "no song is playing",
                        "text": "\u200b",
                        "html": "&#8203;",
                        "selected": True,
                    }
                ],
            },
            "service_items": [],
        }

        assert window._resolved_lyric_html() == ""
    finally:
        window._confirm_close = False
        window.close()


def test_remote_display_starts_with_main_ui_and_opens_lyric_window():
    app = QApplication.instance() or QApplication([])
    window = RemoteDisplayClientWindow()
    try:
        window._stop_connection()
        assert window._lyric_display_window is None
        if window._stage_display_window is not None:
            window._close_stage_display()

        window._show_lyric_display()

        assert window._lyric_display_window is not None
        assert window._lyric_display_window.isVisible() is True
    finally:
        window._close_lyric_display()
        window._confirm_close = False
        window.close()


def test_main_window_close_requires_confirmation(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = RemoteDisplayClientWindow()
    try:
        window._stop_connection()
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)
        event = QEvent(QEvent.Close)
        accepted = []

        class _CloseEvent:
            def ignore(self):
                accepted.append(False)

            def accept(self):
                accepted.append(True)

        close_event = _CloseEvent()
        window.closeEvent(close_event)

        assert accepted == [False]
    finally:
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
        window.close()
