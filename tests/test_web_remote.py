import json

from pyssp.web_remote import WebRemoteServer


def _make_client(calls):
    def dispatch(command, params):
        calls.append((command, dict(params)))
        return {"ok": True, "status": 200, "result": {"command": command, "params": params}}

    server = WebRemoteServer(dispatch=dispatch, host="127.0.0.1", port=5050)
    return server._app.test_client()


def _make_server(calls):
    def dispatch(command, params):
        calls.append((command, dict(params)))
        return {"ok": True, "status": 200, "result": {"command": command, "params": params}}

    return WebRemoteServer(dispatch=dispatch, host="127.0.0.1", port=5050)


def _ws_api_request(server: WebRemoteServer, path: str, method: str = "POST", body: dict | None = None, req_id: str = "req-1"):
    message = {
        "type": "api_request",
        "id": req_id,
        "path": path,
        "method": method,
    }
    if isinstance(body, dict):
        message["body"] = body
    response = server._handle_ws_message(json.dumps(message))
    assert isinstance(response, dict)
    assert response.get("type") == "api_response"
    assert response.get("id") == req_id
    assert isinstance(response.get("status"), int)
    assert isinstance(response.get("payload"), dict)
    return response


def test_alert_route_accepts_json_payload():
    calls = []
    client = _make_client(calls)

    response = client.post("/api/alert", json={"text": "Test alert", "keep": False, "seconds": 7})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert calls[-1][0] == "alert"
    assert calls[-1][1]["text"] == "Test alert"
    assert calls[-1][1]["keep"] is False
    assert calls[-1][1]["seconds"] == 7


def test_alert_clear_route_dispatches_clear_flag():
    calls = []
    client = _make_client(calls)

    response = client.post("/api/alert/clear")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert calls[-1][0] == "alert"
    assert calls[-1][1]["clear"] is True


def test_volume_set_route_dispatches_level():
    calls = []
    client = _make_client(calls)

    response = client.post("/api/volume/73")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert calls[-1][0] == "volume_set"
    assert calls[-1][1]["level"] == 73


def test_lock_routes_dispatch():
    calls = []
    client = _make_client(calls)

    response = client.post("/api/lock")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "lock"

    response = client.post("/api/automation-lock")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "automation_lock"

    response = client.post("/api/automation_lock")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "automation_lock"

    response = client.post("/api/unlock")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "unlock"


def test_navigation_and_selected_play_routes_dispatch():
    calls = []
    client = _make_client(calls)

    for path, target, direction in [
        ("/api/group/next", "group", "next"),
        ("/api/group/prev", "group", "prev"),
        ("/api/page/next", "page", "next"),
        ("/api/page/prev", "page", "prev"),
        ("/api/soundbutton/next", "sound_button", "next"),
        ("/api/soundbutton/prev", "sound_button", "prev"),
    ]:
        response = client.post(path)
        assert response.status_code == 200
        assert response.get_json()["ok"] is True
        assert calls[-1][0] == "navigate"
        assert calls[-1][1]["target"] == target
        assert calls[-1][1]["direction"] == direction

    response = client.post("/api/playselected")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "playselected"

    response = client.post("/api/playselectedpause")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "playselectedpause"

    response = client.post("/api/mute")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "mute"


def test_seek_routes_dispatch_payload():
    calls = []
    client = _make_client(calls)

    response = client.post("/api/seek/percent/33.5")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "seek"
    assert calls[-1][1]["percent"] == "33.5"

    response = client.post("/api/seek/time/01:23")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "seek"
    assert calls[-1][1]["time"] == "01:23"

    response = client.post("/api/seek", json={"percent": 25})
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert calls[-1][0] == "seek"
    assert calls[-1][1]["percent"] == 25


def test_lyric_stage_routes_and_openlp_api_dispatch():
    calls = []
    client = _make_client(calls)

    response = client.get("/lyric/caption", follow_redirects=True)
    assert response.status_code == 200
    assert b"Audience Caption View" in response.data

    response = client.get("/stage/vmixoverlay", follow_redirects=True)
    assert response.status_code == 200
    assert b"Lyric Overlay" in response.data

    response = client.get("/lyric/api/v2/controller/live-items")
    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)
    assert calls[-1][0] == "query_lyric_openlp"

    response = client.get("/stage/api/v2/service/items")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    assert calls[-1][0] == "query_lyric_openlp"


def test_dispatch_api_path_matches_http_routes():
    calls = []
    server = _make_server(calls)
    checks = [
        ("/api/health", "health"),
        ("/api/play/a-1-1", "play"),
        ("/api/pause", "pause"),
        ("/api/resume", "resume"),
        ("/api/stop", "stop"),
        ("/api/forcestop", "forcestop"),
        ("/api/rapidfire", "rapidfire"),
        ("/api/playnext", "playnext"),
        ("/api/talk/toggle", "talk"),
        ("/api/playlist/enable", "playlist"),
        ("/api/playlist/shuffle/disable", "playlist_shuffle"),
        ("/api/playlist/enableshuffle", "playlist_shuffle"),
        ("/api/playlist/disableshuffle", "playlist_shuffle"),
        ("/api/goto/a-1", "goto"),
        ("/api/resetpage/current", "resetpage"),
        ("/api/multiplay/toggle", "multiplay"),
        ("/api/fadein/toggle", "fade"),
        ("/api/fadeout/toggle", "fade"),
        ("/api/crossfade/toggle", "fade"),
        ("/api/lyric/show", "lyric_display"),
        ("/api/lyric/blank", "lyric_display"),
        ("/api/lyric/toggle", "lyric_display"),
        ("/api/volume/73", "volume_set"),
        ("/api/mute", "mute"),
        ("/api/lock", "lock"),
        ("/api/automation-lock", "automation_lock"),
        ("/api/automation_lock", "automation_lock"),
        ("/api/unlock", "unlock"),
        ("/api/group/next", "navigate"),
        ("/api/page/prev", "navigate"),
        ("/api/soundbutton/next", "navigate"),
        ("/api/playselected", "playselected"),
        ("/api/playselectedpause", "playselectedpause"),
        ("/api/seek/percent/22.5", "seek"),
        ("/api/seek/time/01:23", "seek"),
        ("/api/seek", "seek"),
        ("/api/alert", "alert"),
        ("/api/alert/clear", "alert"),
        ("/api/query", "query_all"),
        ("/api/query/button/a-1-1", "query_button"),
        ("/api/query/pagegroup/a", "query_pagegroup"),
        ("/api/query/page/a-1", "query_page"),
    ]
    for path, command in checks:
        payload = server._dispatch_api_path(path, method="POST", params={"text": "x", "percent": 10})
        assert payload["ok"] is True
        assert calls[-1][0] == command


def test_dispatch_api_path_merges_query_and_body_params():
    calls = []
    server = _make_server(calls)

    payload = server._dispatch_api_path(
        "/api/seek?percent=42",
        method="POST",
        params={"time": "00:10"},
    )
    assert payload["ok"] is True
    assert calls[-1][0] == "seek"
    assert calls[-1][1]["percent"] == "42"
    assert calls[-1][1]["time"] == "00:10"

    payload = server._dispatch_api_path(
        "/api/alert?keep=false",
        method="POST",
        params={"text": "hello", "seconds": 3},
    )
    assert payload["ok"] is True
    assert calls[-1][0] == "alert"
    assert calls[-1][1]["keep"] == "false"
    assert calls[-1][1]["text"] == "hello"
    assert calls[-1][1]["seconds"] == 3


def test_ws_api_request_dispatches_same_commands_as_http():
    calls = []
    server = _make_server(calls)
    client = server._app.test_client()

    checks = [
        ("/api/play/a-1-1", "play"),
        ("/api/seek/percent/22.5", "seek"),
        ("/api/seek/time/01:23", "seek"),
        ("/api/lyric/toggle", "lyric_display"),
        ("/api/alert/clear", "alert"),
        ("/api/query/page/a-1", "query_page"),
    ]

    for path, command in checks:
        calls.clear()
        http_response = client.post(path)
        assert http_response.status_code == 200
        assert http_response.get_json()["ok"] is True
        assert calls[-1][0] == command
        http_call = calls[-1]

        calls.clear()
        ws_response = _ws_api_request(server, path=path, method="POST", req_id=f"ws-{command}")
        assert ws_response["status"] == 200
        assert ws_response["payload"]["ok"] is True
        assert calls[-1][0] == command
        ws_call = calls[-1]

        assert ws_call[0] == http_call[0]
        assert ws_call[1] == http_call[1]


def test_ws_api_request_protocol_errors():
    calls = []
    server = _make_server(calls)

    invalid_json = server._handle_ws_message("{not-json")
    assert invalid_json["type"] == "ws_error"
    assert invalid_json["error"]["code"] == "invalid_json"

    unknown_type = server._handle_ws_message(json.dumps({"type": "something_else"}))
    assert unknown_type["type"] == "ws_error"
    assert unknown_type["error"]["code"] == "unknown_type"


def test_lyric_payload_fallback_includes_single_blank_slide():
    def dispatch(_command, _params):
        return {"ok": False, "status": 500, "error": {"code": "bad", "message": "bad"}}

    server = WebRemoteServer(dispatch=dispatch, host="127.0.0.1", port=5050)
    payload = server._lyric_payload_bundle()
    slides = payload["live_items"]["slides"]
    assert isinstance(slides, list)
    assert len(slides) == 1
    assert slides[0]["selected"] is True
    assert slides[0]["text"] == "\u200b"
