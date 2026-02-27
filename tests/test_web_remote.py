from pyssp.web_remote import WebRemoteServer


def _make_client(calls):
    def dispatch(command, params):
        calls.append((command, dict(params)))
        return {"ok": True, "status": 200, "result": {"command": command, "params": params}}

    server = WebRemoteServer(dispatch=dispatch, host="127.0.0.1", port=5050)
    return server._app.test_client()


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
