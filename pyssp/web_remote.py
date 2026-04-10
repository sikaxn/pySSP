from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, unquote, urlsplit

from flask import Flask, jsonify, redirect, request, send_from_directory
from simple_websocket import ConnectionClosed, Server
from werkzeug.serving import WSGIRequestHandler, make_server
try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None


DispatchFn = Callable[[str, Dict[str, Any]], Dict[str, Any]]


class QuietRequestHandler(WSGIRequestHandler):
    def log_request(self, _code: int | str = "-", _size: int | str = "-") -> None:
        return

    def log_message(self, _format: str, *args) -> None:
        return


class WebRemoteServer:
    def __init__(self, dispatch: DispatchFn, host: str = "0.0.0.0", port: int = 5050, ws_port: int | None = None) -> None:
        self._dispatch = dispatch
        self.host = host
        self.port = int(port)
        self.ws_port = int(ws_port) if ws_port is not None else (int(port) + 1)
        self._app = Flask("pyssp_web_remote")
        self._lyric_assets_root = Path(__file__).resolve().parent / "assets" / "lyric_stage"
        self._web_remote_assets_root = Path(__file__).resolve().parent / "assets" / "web_remote"
        self._server = None
        self._thread: threading.Thread | None = None
        self._lyric_push_thread: threading.Thread | None = None
        self._ws_thread: threading.Thread | None = None
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._ws_server = None
        self._ws_clients: set[Any] = set()
        self._ws_lock = threading.Lock()
        self._ws_ready = threading.Event()
        self._ws_enabled = False
        self._lyric_ws_clients: set[Server] = set()
        self._lyric_ws_lock = threading.Lock()
        self._lyric_stop_event = threading.Event()
        self._lock = threading.Lock()
        self._configure_logging()
        self._register_routes()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            self._lyric_stop_event.clear()
            self._server = make_server(
                self.host,
                self.port,
                self._app,
                threaded=True,
                request_handler=QuietRequestHandler,
            )
            self._thread = threading.Thread(target=self._server.serve_forever, name="pyssp-web-remote", daemon=True)
            self._thread.start()
            self._lyric_push_thread = threading.Thread(
                target=self._lyric_broadcast_loop,
                name="pyssp-lyric-ws",
                daemon=True,
            )
            self._lyric_push_thread.start()
            self._start_dedicated_ws_server()

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            lyric_thread = self._lyric_push_thread
            ws_thread = self._ws_thread
            self._server = None
            self._thread = None
            self._lyric_push_thread = None
            self._ws_thread = None
            self._lyric_stop_event.set()
            self._close_all_lyric_ws_clients()
            self._stop_dedicated_ws_server()
        if server is not None:
            server.shutdown()
        if thread is not None:
            thread.join(timeout=2.0)
        if lyric_thread is not None:
            lyric_thread.join(timeout=2.0)
        if ws_thread is not None:
            ws_thread.join(timeout=2.0)

    def _configure_logging(self) -> None:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self._app.logger.setLevel(logging.ERROR)

    async def _ws_client_handler(self, websocket) -> None:
        with self._ws_lock:
            self._ws_clients.add(websocket)
        try:
            await websocket.send(json.dumps({"results": self._lyric_payload_bundle()["ws"]}, ensure_ascii=False))
            async for raw_message in websocket:
                response = self._handle_ws_message(raw_message)
                if response is None:
                    continue
                await websocket.send(json.dumps(response, ensure_ascii=False))
        except Exception:
            pass
        finally:
            with self._ws_lock:
                self._ws_clients.discard(websocket)

    @staticmethod
    def _safe_int(raw: Any, default: int = 0) -> int:
        try:
            return int(raw)
        except Exception:
            return int(default)

    @staticmethod
    def _merge_params(*sources: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for source in sources:
            if isinstance(source, dict):
                merged.update(source)
        return merged

    def _dispatch_api_path(self, path: str, method: str = "GET", params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        merged_params = dict(params or {})
        raw_path = str(path or "").strip()
        if not raw_path:
            raw_path = "/api/health"
        split = urlsplit(raw_path)
        endpoint = unquote(split.path or "")
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        query_params_raw = parse_qs(split.query or "", keep_blank_values=True)
        query_params: Dict[str, Any] = {k: (v[-1] if isinstance(v, list) and v else "") for k, v in query_params_raw.items()}
        merged_params = self._merge_params(query_params, merged_params)

        def send(command: str, **cmd_params: Any) -> Dict[str, Any]:
            payload = self._dispatch(command, cmd_params)
            if not isinstance(payload, dict):
                return {"ok": False, "status": 500, "error": {"code": "invalid_payload", "message": "Invalid dispatch payload."}}
            if "status" not in payload:
                payload = dict(payload)
                payload["status"] = 200
            return payload

        norm_method = str(method or "GET").strip().upper()
        if norm_method not in {"GET", "POST"}:
            return {"ok": False, "status": 405, "error": {"code": "method_not_allowed", "message": "Only GET and POST are supported."}}

        if endpoint == "/api/health":
            return send("health")

        m = re.fullmatch(r"/api/play/([^/]+)", endpoint)
        if m:
            return send("play", button_id=m.group(1))

        fixed_routes: Dict[str, tuple[str, Dict[str, Any]]] = {
            "/api/pause": ("pause", {}),
            "/api/resume": ("resume", {}),
            "/api/stop": ("stop", {}),
            "/api/forcestop": ("forcestop", {}),
            "/api/rapidfire": ("rapidfire", {}),
            "/api/playnext": ("playnext", {}),
            "/api/playlist/enableshuffle": ("playlist_shuffle", {"mode": "enable"}),
            "/api/playlist/disableshuffle": ("playlist_shuffle", {"mode": "disable"}),
            "/api/mute": ("mute", {}),
            "/api/lock": ("lock", {}),
            "/api/automation-lock": ("automation_lock", {}),
            "/api/automation_lock": ("automation_lock", {}),
            "/api/unlock": ("unlock", {}),
            "/api/group/next": ("navigate", {"target": "group", "direction": "next"}),
            "/api/group/prev": ("navigate", {"target": "group", "direction": "prev"}),
            "/api/page/next": ("navigate", {"target": "page", "direction": "next"}),
            "/api/page/prev": ("navigate", {"target": "page", "direction": "prev"}),
            "/api/soundbutton/next": ("navigate", {"target": "sound_button", "direction": "next"}),
            "/api/soundbutton/prev": ("navigate", {"target": "sound_button", "direction": "prev"}),
            "/api/playselected": ("playselected", {}),
            "/api/playselectedpause": ("playselectedpause", {}),
            "/api/alert/clear": ("alert", {"clear": True}),
            "/api/query": ("query_all", {}),
        }
        fixed = fixed_routes.get(endpoint)
        if fixed is not None:
            cmd, cmd_params = fixed
            return send(cmd, **cmd_params)

        m = re.fullmatch(r"/api/lyric/([^/]+)", endpoint)
        if m:
            return send("lyric_display", mode=m.group(1))

        m = re.fullmatch(r"/api/talk/([^/]+)", endpoint)
        if m:
            return send("talk", mode=m.group(1))
        m = re.fullmatch(r"/api/playlist/([^/]+)", endpoint)
        if m:
            return send("playlist", mode=m.group(1))
        m = re.fullmatch(r"/api/playlist/shuffle/([^/]+)", endpoint)
        if m:
            return send("playlist_shuffle", mode=m.group(1))
        m = re.fullmatch(r"/api/goto/(.+)", endpoint)
        if m:
            return send("goto", target=m.group(1))
        m = re.fullmatch(r"/api/resetpage/([^/]+)", endpoint)
        if m:
            return send("resetpage", scope=m.group(1))
        m = re.fullmatch(r"/api/multiplay/([^/]+)", endpoint)
        if m:
            return send("multiplay", mode=m.group(1))
        m = re.fullmatch(r"/api/fadein/([^/]+)", endpoint)
        if m:
            return send("fade", kind="fadein", mode=m.group(1))
        m = re.fullmatch(r"/api/fadeout/([^/]+)", endpoint)
        if m:
            return send("fade", kind="fadeout", mode=m.group(1))
        m = re.fullmatch(r"/api/crossfade/([^/]+)", endpoint)
        if m:
            return send("fade", kind="crossfade", mode=m.group(1))
        m = re.fullmatch(r"/api/volume/([^/]+)", endpoint)
        if m:
            return send("volume_set", level=self._safe_int(m.group(1), default=-1))
        m = re.fullmatch(r"/api/seek/percent/(.+)", endpoint)
        if m:
            return send("seek", percent=m.group(1))
        m = re.fullmatch(r"/api/seek/time/(.+)", endpoint)
        if m:
            return send("seek", time=m.group(1))
        if endpoint == "/api/seek":
            return send("seek", percent=merged_params.get("percent"), time=merged_params.get("time"))
        if endpoint == "/api/alert":
            return send(
                "alert",
                text=merged_params.get("text", ""),
                keep=merged_params.get("keep"),
                seconds=merged_params.get("seconds"),
                clear=merged_params.get("clear"),
                mode=merged_params.get("mode"),
            )
        m = re.fullmatch(r"/api/query/button/(.+)", endpoint)
        if m:
            return send("query_button", button_id=m.group(1))
        m = re.fullmatch(r"/api/query/pagegroup/([^/]+)", endpoint)
        if m:
            return send("query_pagegroup", group_id=m.group(1))
        m = re.fullmatch(r"/api/query/page/(.+)", endpoint)
        if m:
            return send("query_page", page_id=m.group(1))

        return {"ok": False, "status": 404, "error": {"code": "not_found", "message": f"Unknown API path '{endpoint}'."}}

    def _handle_ws_message(self, raw_message: Any) -> Dict[str, Any] | None:
        if raw_message is None:
            return None
        try:
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode("utf-8", errors="ignore")
            payload = json.loads(str(raw_message))
        except Exception:
            return {"type": "ws_error", "error": {"code": "invalid_json", "message": "Message must be valid JSON."}}
        if not isinstance(payload, dict):
            return {"type": "ws_error", "error": {"code": "invalid_message", "message": "Message must be a JSON object."}}

        msg_type = str(payload.get("type", "")).strip().lower()
        if msg_type in {"ping", "heartbeat"}:
            return {"type": "pong", "at": int(time.time())}
        if msg_type in {"api_request", "api"} or ("path" in payload):
            req_id = payload.get("id")
            path = str(payload.get("path", "")).strip()
            method = str(payload.get("method", "GET")).strip().upper()
            body = payload.get("body", {})
            query = payload.get("query", {})
            params = self._merge_params(query if isinstance(query, dict) else {}, body if isinstance(body, dict) else {})
            result = self._dispatch_api_path(path=path, method=method, params=params)
            status = int(result.get("status", 200))
            body_result = {k: v for k, v in result.items() if k != "status"}
            return {"type": "api_response", "id": req_id, "status": status, "payload": body_result}

        return {"type": "ws_error", "error": {"code": "unknown_type", "message": f"Unknown message type '{msg_type or '<empty>'}'."}}

    def _run_dedicated_ws_server(self) -> None:
        loop = asyncio.new_event_loop()
        self._ws_loop = loop
        asyncio.set_event_loop(loop)
        try:
            async def _start_server():
                return await websockets.serve(self._ws_client_handler, self.host, self.ws_port)

            self._ws_server = loop.run_until_complete(_start_server())
            self._ws_enabled = True
            self._ws_ready.set()
            loop.run_forever()
        except Exception:
            self._ws_enabled = False
            self._ws_ready.set()
        finally:
            try:
                if self._ws_server is not None:
                    self._ws_server.close()
                    loop.run_until_complete(self._ws_server.wait_closed())
            except Exception:
                pass
            with self._ws_lock:
                self._ws_clients.clear()
            self._ws_server = None
            self._ws_loop = None
            self._ws_enabled = False
            try:
                loop.close()
            except Exception:
                pass

    def _start_dedicated_ws_server(self) -> None:
        if websockets is None:
            self._ws_enabled = False
            return
        self._ws_ready.clear()
        self._ws_thread = threading.Thread(
            target=self._run_dedicated_ws_server,
            name="pyssp-lyric-ws-dedicated",
            daemon=True,
        )
        self._ws_thread.start()
        self._ws_ready.wait(timeout=1.5)

    async def _ws_broadcast_async(self, message: str) -> None:
        with self._ws_lock:
            clients = list(self._ws_clients)
        stale: list[Any] = []
        for client in clients:
            try:
                await client.send(message)
            except Exception:
                stale.append(client)
        if stale:
            with self._ws_lock:
                for client in stale:
                    self._ws_clients.discard(client)

    def _broadcast_dedicated_ws(self, message: str) -> None:
        loop = self._ws_loop
        if not self._ws_enabled or loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._ws_broadcast_async(message), loop)
        except Exception:
            pass

    def _stop_dedicated_ws_server(self) -> None:
        loop = self._ws_loop
        if loop is not None:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
        self._ws_enabled = False

    def _lyric_payload_bundle(self) -> dict:
        payload = self._dispatch("query_lyric_openlp", {})
        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, dict):
                ws = result.get("ws")
                live_items = result.get("live_items")
                service_items = result.get("service_items")
                if isinstance(ws, dict) and isinstance(live_items, dict) and isinstance(service_items, list):
                    return {
                        "ws": ws,
                        "live_items": live_items,
                        "service_items": service_items,
                    }
        return {
            "ws": {"item": "", "service": "", "slide": 0, "twelve": False, "display": "blank", "blank": True, "theme": False},
            "live_items": {
                "item": "",
                "slides": [
                    {
                        "title": "no song is playing",
                        "text": "\u200b",
                        "html": "&#8203;",
                        "img": "",
                        "tag": "L0",
                        "selected": True,
                    }
                ],
            },
            "service_items": [],
        }

    def _lyric_broadcast_loop(self) -> None:
        last_payload = ""
        while not self._lyric_stop_event.wait(0.35):
            bundle = self._lyric_payload_bundle()
            message = json.dumps({"results": bundle["ws"]}, ensure_ascii=False)
            if message == last_payload:
                continue
            last_payload = message
            self._broadcast_lyric_ws(message)

    def _broadcast_lyric_ws(self, message: str) -> None:
        self._broadcast_dedicated_ws(message)
        stale_clients: list[Server] = []
        with self._lyric_ws_lock:
            clients = list(self._lyric_ws_clients)
        for ws in clients:
            try:
                ws.send(message)
            except Exception:
                stale_clients.append(ws)
        if stale_clients:
            with self._lyric_ws_lock:
                for ws in stale_clients:
                    self._lyric_ws_clients.discard(ws)

    def _close_all_lyric_ws_clients(self) -> None:
        with self._lyric_ws_lock:
            clients = list(self._lyric_ws_clients)
            self._lyric_ws_clients.clear()
        for ws in clients:
            try:
                ws.close()
            except Exception:
                pass

    def _handle_lyric_ws(self) -> str:
        ws = Server.accept(request.environ)
        with self._lyric_ws_lock:
            self._lyric_ws_clients.add(ws)
        try:
            ws.send(json.dumps({"results": self._lyric_payload_bundle()["ws"]}, ensure_ascii=False))
            while not self._lyric_stop_event.is_set():
                try:
                    ws.receive(timeout=15.0)
                except TimeoutError:
                    continue
                except ConnectionClosed:
                    break
        finally:
            with self._lyric_ws_lock:
                self._lyric_ws_clients.discard(ws)
            try:
                ws.close()
            except Exception:
                pass
        return ""

    def _lyric_stage_dir(self, view_name: str) -> Path:
        lowered = str(view_name or "").strip()
        mapping = {
            "caption": "caption",
            "overhead": "overhead",
            "banner": "banner",
            "vmixoverlay": "vmixOverlay",
        }
        target = mapping.get(lowered.casefold())
        if not target:
            raise FileNotFoundError("Unknown stage view.")
        stage_dir = self._lyric_assets_root / target
        if not stage_dir.is_dir():
            raise FileNotFoundError("Stage view assets are missing.")
        return stage_dir

    def _register_routes(self) -> None:
        app = self._app

        @app.get("/")
        def index():
            index_path = self._web_remote_assets_root / "index.html"
            if not index_path.exists() or not index_path.is_file():
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Web Remote index asset not found."}}), 404
            return send_from_directory(self._web_remote_assets_root, "index.html")

        @app.get("/webremote/<path:filename>")
        def webremote_asset(filename: str):
            clean_name = str(filename or "").replace("\\", "/")
            if clean_name.startswith("../") or "/../" in clean_name:
                return jsonify({"ok": False, "error": {"code": "invalid_path", "message": "Invalid asset path."}}), 400
            asset_path = self._web_remote_assets_root / clean_name
            if not asset_path.exists() or not asset_path.is_file():
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Asset not found."}}), 404
            return send_from_directory(self._web_remote_assets_root, clean_name)


        @app.get("/lyric")
        @app.get("/lyric/")
        @app.get("/stage")
        @app.get("/stage/")
        def lyric_index():
            return jsonify(
                {
                    "ok": True,
                    "views": {
                        "caption": "/lyric/caption/",
                        "overhead": "/lyric/overhead/",
                        "banner": "/lyric/banner/",
                        "vmixoverlay": "/lyric/vmixoverlay/",
                        "stage_caption": "/stage/caption/",
                        "stage_overhead": "/stage/overhead/",
                        "stage_banner": "/stage/banner/",
                        "stage_vmixoverlay": "/stage/vmixoverlay/",
                    },
                    "websocket": ["/ws", "/lyric/ws", "/stage/ws"],
                    "ws_port": self.ws_port,
                    "ws_path": "/ws",
                    "api": [
                        "/lyric/api/v2/controller/live-items",
                        "/lyric/api/v2/service/items",
                    ],
                }
            )

        @app.get("/lyric/ws")
        @app.get("/stage/ws")
        def lyric_ws():
            return self._handle_lyric_ws()

        @app.get("/lyric/shared/<path:filename>")
        @app.get("/stage/shared/<path:filename>")
        def lyric_shared_asset(filename: str):
            shared_dir = self._lyric_assets_root / "shared"
            clean_name = str(filename or "").replace("\\", "/")
            if clean_name.startswith("../") or "/../" in clean_name:
                return jsonify({"ok": False, "error": {"code": "invalid_path", "message": "Invalid asset path."}}), 400
            asset_path = shared_dir / clean_name
            if not asset_path.exists() or not asset_path.is_file():
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Asset not found."}}), 404
            return send_from_directory(shared_dir, clean_name)

        @app.get("/lyric/pyssp.ico")
        @app.get("/stage/pyssp.ico")
        def lyric_pyssp_favicon():
            return lyric_shared_asset("pyssp.ico")

        @app.get("/api/v2/controller/live-items")
        @app.get("/lyric/api/v2/controller/live-items")
        @app.get("/stage/api/v2/controller/live-items")
        def lyric_api_live_items():
            return jsonify(self._lyric_payload_bundle()["live_items"])

        @app.get("/api/v2/service/items")
        @app.get("/lyric/api/v2/service/items")
        @app.get("/stage/api/v2/service/items")
        def lyric_api_service_items():
            return jsonify(self._lyric_payload_bundle()["service_items"])

        @app.get("/lyric/<string:view_name>")
        @app.get("/lyric/<string:view_name>/")
        @app.get("/stage/<string:view_name>")
        @app.get("/stage/<string:view_name>/")
        def lyric_stage_entry(view_name: str):
            # Canonicalize with trailing slash so relative stage assets resolve under the view path.
            if not request.path.endswith("/"):
                return redirect(f"{request.path}/", code=308)
            try:
                stage_dir = self._lyric_stage_dir(view_name)
            except FileNotFoundError:
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Unknown stage view."}}), 404
            return send_from_directory(stage_dir, "stage.html")

        @app.get("/lyric/<string:view_name>/<path:filename>")
        @app.get("/stage/<string:view_name>/<path:filename>")
        def lyric_stage_asset(view_name: str, filename: str):
            try:
                stage_dir = self._lyric_stage_dir(view_name)
            except FileNotFoundError:
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Unknown stage view."}}), 404
            clean_name = str(filename or "").replace("\\", "/")
            if clean_name.startswith("../") or "/../" in clean_name:
                return jsonify({"ok": False, "error": {"code": "invalid_path", "message": "Invalid asset path."}}), 400
            asset_path = stage_dir / clean_name
            if not asset_path.exists() or not asset_path.is_file():
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Asset not found."}}), 404
            return send_from_directory(stage_dir, clean_name)

        @app.route("/api", defaults={"subpath": ""}, methods=["GET", "POST"])
        @app.route("/api/<path:subpath>", methods=["GET", "POST"])
        def api_dispatch(subpath: str):
            endpoint = "/api" if not str(subpath or "").strip() else f"/api/{subpath}"
            params: Dict[str, Any] = {}
            if request.method == "POST":
                payload = request.get_json(silent=True)
                if isinstance(payload, dict):
                    params.update(payload)
                params.update(request.form.to_dict())
            params.update(request.args.to_dict())
            payload = self._dispatch_api_path(endpoint, method=request.method, params=params)
            status = int(payload.get("status", 200))
            body = {k: v for k, v in payload.items() if k != "status"}
            return jsonify(body), status
