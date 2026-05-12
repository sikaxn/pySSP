from __future__ import annotations

import asyncio
import base64
import datetime as dt
import hmac
import json
import socket
import ssl
import logging
import re
import threading
import time
from http import HTTPStatus
from ipaddress import IPv4Address, ip_address
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, unquote, urlsplit

from flask import Flask, Response, jsonify, redirect, request, send_from_directory
from simple_websocket import ConnectionClosed, Server
from werkzeug.serving import WSGIRequestHandler, make_server
from pyssp.settings_store import get_settings_path
try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None


DispatchFn = Callable[[str, Dict[str, Any]], Dict[str, Any]]
WEB_REMOTE_GUEST_USERNAME = "guest"
_BASIC_AUTH_REALM = 'Basic realm="pySSP Web Remote", charset="UTF-8"'


def _parse_basic_auth_header(raw_header: object) -> tuple[str, str] | None:
    header = str(raw_header or "").strip()
    if not header or not header.lower().startswith("basic "):
        return None
    token = header[6:].strip()
    if not token:
        return None
    try:
        decoded = base64.b64decode(token.encode("ascii"), validate=True)
    except Exception:
        return None
    for encoding in ("utf-8", "latin1"):
        try:
            text = decoded.decode(encoding)
            break
        except UnicodeDecodeError:
            text = ""
    if ":" not in text:
        return None
    username, password = text.split(":", 1)
    return username, password


def _web_remote_tls_dir() -> Path:
    target = get_settings_path().parent / "web_remote_tls"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _web_remote_tls_paths() -> tuple[Path, Path]:
    base = _web_remote_tls_dir()
    return base / "cert.pem", base / "key.pem"


def _web_remote_certificate_hostnames() -> list[str]:
    values: list[str] = ["localhost"]
    for raw in (socket.gethostname(), socket.getfqdn()):
        token = str(raw or "").strip()
        if token and token not in values:
            values.append(token)
    return values


def _web_remote_certificate_ipv4s() -> list[IPv4Address]:
    values: list[IPv4Address] = []
    seen: set[str] = set()
    candidates = ["127.0.0.1"]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidates.append(sock.getsockname()[0])
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidates.append(str(info[4][0] or "").strip())
    except Exception:
        pass
    for raw in candidates:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        try:
            parsed = ip_address(token)
        except ValueError:
            continue
        if isinstance(parsed, IPv4Address):
            values.append(parsed)
    return values


def _write_web_remote_self_signed_cert(cert_path: Path, key_path: Path) -> None:
    try:
        from cryptography import x509  # type: ignore
        from cryptography.hazmat.primitives import hashes, serialization  # type: ignore
        from cryptography.hazmat.primitives.asymmetric import rsa  # type: ignore
        from cryptography.x509.oid import NameOID  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised in runtime integration
        raise RuntimeError(
            "HTTPS Web Remote requires the 'cryptography' package to generate a local certificate."
        ) from exc

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    hostname = _web_remote_certificate_hostnames()[0]
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    san_entries: list[x509.GeneralName] = []
    for item in _web_remote_certificate_hostnames():
        san_entries.append(x509.DNSName(item))
    for item in _web_remote_certificate_ipv4s():
        san_entries.append(x509.IPAddress(item))
    now = dt.datetime.now(dt.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def build_web_remote_ssl_context() -> ssl.SSLContext:
    cert_path, key_path = _web_remote_tls_paths()
    for attempt in range(2):
        if not cert_path.exists() or not key_path.exists():
            _write_web_remote_self_signed_cert(cert_path, key_path)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
            return context
        except Exception:
            if attempt >= 1:
                raise
            try:
                cert_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                key_path.unlink(missing_ok=True)
            except Exception:
                pass
    raise RuntimeError("Could not initialize the Web Remote TLS certificate.")

def _normalize_asset_relpath(raw_path: str) -> str:
    text = str(raw_path or "").replace("\\", "/").strip()
    if not text:
        raise ValueError("Asset path is empty.")
    if text.startswith("/"):
        raise ValueError("Asset path must be relative.")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise ValueError("Invalid asset path.")
    if any("\x00" in part for part in parts):
        raise ValueError("Invalid asset path.")
    return "/".join(parts)


class QuietRequestHandler(WSGIRequestHandler):
    def log_request(self, _code: int | str = "-", _size: int | str = "-") -> None:
        return

    def log_message(self, _format: str, *args) -> None:
        return


class WebRemoteServer:
    def __init__(
        self,
        dispatch: DispatchFn,
        host: str = "0.0.0.0",
        port: int = 5050,
        ws_port: int | None = None,
        *,
        https_enabled: bool = False,
        https_port: int | None = None,
        wss_port: int | None = None,
        enforce_https: bool = False,
        require_authentication: bool = False,
        username: str = "admin",
        password: str = "",
        guest_view_enabled: bool = False,
    ) -> None:
        self._dispatch = dispatch
        self.host = host
        self.port = int(port)
        self.ws_port = int(ws_port) if ws_port is not None else (int(port) + 1)
        self.https_enabled = bool(https_enabled or enforce_https)
        self.https_port = int(https_port) if https_port is not None else (int(port) + 2)
        self.wss_port = int(wss_port) if wss_port is not None else (int(port) + 3)
        self.enforce_https = bool(enforce_https)
        self.require_authentication = bool(require_authentication)
        self.username = str(username or "").strip() or "admin"
        self.password = str(password or "")
        self.guest_view_enabled = bool(guest_view_enabled)
        self._app = Flask("pyssp_web_remote")
        self._lyric_assets_root = Path(__file__).resolve().parent / "assets" / "lyric_stage"
        self._web_remote_assets_root = Path(__file__).resolve().parent / "assets" / "web_remote"
        self._server = None
        self._https_server = None
        self._thread: threading.Thread | None = None
        self._https_thread: threading.Thread | None = None
        self._lyric_push_thread: threading.Thread | None = None
        self._ws_thread: threading.Thread | None = None
        self._wss_thread: threading.Thread | None = None
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._wss_loop: asyncio.AbstractEventLoop | None = None
        self._ws_server = None
        self._wss_server = None
        self._ws_clients: set[Any] = set()
        self._wss_clients: set[Any] = set()
        self._ws_lock = threading.Lock()
        self._wss_lock = threading.Lock()
        self._ws_ready = threading.Event()
        self._wss_ready = threading.Event()
        self._ws_enabled = False
        self._wss_enabled = False
        self._lyric_ws_clients: set[Server] = set()
        self._lyric_ws_lock = threading.Lock()
        self._lyric_stop_event = threading.Event()
        self._ssl_context: ssl.SSLContext | None = None
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
            self._ssl_context = build_web_remote_ssl_context() if self.https_enabled else None
            self._server = make_server(
                self.host,
                self.port,
                self._app,
                threaded=True,
                request_handler=QuietRequestHandler,
            )
            self._thread = threading.Thread(target=self._server.serve_forever, name="pyssp-web-remote", daemon=True)
            self._thread.start()
            if self.https_enabled:
                self._https_server = make_server(
                    self.host,
                    self.https_port,
                    self._app,
                    threaded=True,
                    request_handler=QuietRequestHandler,
                    ssl_context=self._ssl_context,
                )
                self._https_thread = threading.Thread(
                    target=self._https_server.serve_forever,
                    name="pyssp-web-remote-https",
                    daemon=True,
                )
                self._https_thread.start()
            self._lyric_push_thread = threading.Thread(
                target=self._lyric_broadcast_loop,
                name="pyssp-lyric-ws",
                daemon=True,
            )
            self._lyric_push_thread.start()
            self._start_dedicated_ws_server()
            self._start_secure_ws_server()

    def stop(self) -> None:
        with self._lock:
            server = self._server
            https_server = self._https_server
            thread = self._thread
            https_thread = self._https_thread
            lyric_thread = self._lyric_push_thread
            ws_thread = self._ws_thread
            wss_thread = self._wss_thread
            self._server = None
            self._https_server = None
            self._thread = None
            self._https_thread = None
            self._lyric_push_thread = None
            self._ws_thread = None
            self._wss_thread = None
            self._lyric_stop_event.set()
            self._close_all_lyric_ws_clients()
            self._stop_dedicated_ws_server()
            self._stop_secure_ws_server()
        if server is not None:
            server.shutdown()
        if https_server is not None:
            https_server.shutdown()
        if thread is not None:
            thread.join(timeout=2.0)
        if https_thread is not None:
            https_thread.join(timeout=2.0)
        if lyric_thread is not None:
            lyric_thread.join(timeout=2.0)
        if ws_thread is not None:
            ws_thread.join(timeout=2.0)
        if wss_thread is not None:
            wss_thread.join(timeout=2.0)

    def _configure_logging(self) -> None:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self._app.logger.setLevel(logging.ERROR)

    def _resolve_access_role(self, authorization_header: object) -> str:
        if not self.require_authentication:
            return "admin"
        credentials = _parse_basic_auth_header(authorization_header)
        if credentials is None:
            return ""
        username, password = credentials
        if hmac.compare_digest(username, self.username) and hmac.compare_digest(password, self.password):
            return "admin"
        if self.guest_view_enabled and hmac.compare_digest(username, WEB_REMOTE_GUEST_USERNAME) and password == "":
            return "guest"
        return ""

    @staticmethod
    def _json_error_response(status: int, code: str, message: str) -> tuple[Response, int]:
        return jsonify({"ok": False, "error": {"code": code, "message": message}}), int(status)

    def _auth_challenge_response(self, *, as_json: bool) -> tuple[Response, int] | Response:
        headers = {"WWW-Authenticate": _BASIC_AUTH_REALM}
        if as_json:
            response = jsonify({"ok": False, "error": {"code": "authentication_required", "message": "Authentication required."}})
            response.headers.update(headers)
            return response, 401
        return Response("Authentication required.\n", status=401, headers=headers)

    @staticmethod
    def _websocket_http_response(status: HTTPStatus, body: str, *, challenge: bool = False) -> tuple[HTTPStatus, list[tuple[str, str]], bytes]:
        headers = [("Content-Type", "text/plain; charset=utf-8")]
        if challenge:
            headers.append(("WWW-Authenticate", _BASIC_AUTH_REALM))
        return status, headers, body.encode("utf-8", errors="replace")

    def _guest_can_access_api_path(self, raw_path: str) -> bool:
        endpoint = unquote(urlsplit(str(raw_path or "").strip()).path or "")
        if endpoint in {
            "/api/health",
            "/api/query",
            "/api/v2/controller/live-items",
            "/api/v2/service/items",
            "/lyric/api/v2/controller/live-items",
            "/lyric/api/v2/service/items",
            "/stage/api/v2/controller/live-items",
            "/stage/api/v2/service/items",
        }:
            return True
        if re.fullmatch(r"/api/query/button/(.+)", endpoint):
            return True
        if re.fullmatch(r"/api/query/pagegroup/([^/]+)", endpoint):
            return True
        if re.fullmatch(r"/api/query/page/(.+)", endpoint):
            return True
        return False

    def _guest_can_access_http_path(self, path: str) -> bool:
        endpoint = unquote(urlsplit(str(path or "").strip()).path or "")
        if not endpoint:
            return False
        if self._guest_can_access_api_path(endpoint):
            return True
        if endpoint in {
            "/",
            "/legacy-index",
            "/legacy-index/",
            "/lyric",
            "/lyric/",
            "/stage",
            "/stage/",
            "/lyric/ws",
            "/stage/ws",
            "/lyric/pyssp.ico",
            "/stage/pyssp.ico",
        }:
            return True
        if endpoint.startswith("/webremote/"):
            return True
        if endpoint.startswith("/lyric/shared/") or endpoint.startswith("/stage/shared/"):
            return True
        if re.fullmatch(r"/(?:lyric|stage)/(caption|overhead|banner|vmixoverlay)/?", endpoint):
            return True
        if re.fullmatch(r"/(?:lyric|stage)/(caption|overhead|banner|vmixoverlay)/.+", endpoint):
            return True
        return False

    def _secure_redirect_url(self) -> str:
        host = (request.host or "").split(":", 1)[0] or request.host or "127.0.0.1"
        path = request.path or "/"
        query = request.query_string.decode("utf-8", errors="ignore")
        url = f"https://{host}:{int(self.https_port)}{path}"
        if query:
            url = f"{url}?{query}"
        return url

    def _before_request(self):
        upgrade = str(request.headers.get("Upgrade", "") or "").strip().lower()
        is_websocket_upgrade = upgrade == "websocket"
        path = request.path or "/"
        wants_json = path.startswith("/api") or path.startswith("/lyric/api/") or path.startswith("/stage/api/")
        if self.enforce_https and (not request.is_secure):
            if is_websocket_upgrade:
                return self._json_error_response(426, "https_required", "Use HTTPS/WSS for Web Remote access.")
            return redirect(self._secure_redirect_url(), code=308)
        role = self._resolve_access_role(request.headers.get("Authorization"))
        if not role:
            return self._auth_challenge_response(as_json=wants_json)
        if role == "guest" and not self._guest_can_access_http_path(path):
            return self._json_error_response(403, "forbidden", "Guest access is view only.")
        return None

    def _ws_process_request(self, path, request_headers, *, secure_transport: bool):
        if self.enforce_https and (not secure_transport):
            return self._websocket_http_response(
                HTTPStatus.UPGRADE_REQUIRED,
                "Use the secure WSS endpoint for Web Remote access.\n",
            )
        role = self._resolve_access_role(request_headers.get("Authorization"))
        if not role:
            return self._websocket_http_response(
                HTTPStatus.UNAUTHORIZED,
                "Authentication required.\n",
                challenge=True,
            )
        return None

    async def _ws_client_handler(self, websocket, *, secure_transport: bool = False) -> None:
        role = self._resolve_access_role(getattr(websocket, "request_headers", {}).get("Authorization"))
        if not role:
            try:
                await websocket.close(code=4401, reason="authentication required")
            except Exception:
                pass
            return
        lock = self._wss_lock if secure_transport else self._ws_lock
        clients = self._wss_clients if secure_transport else self._ws_clients
        with lock:
            clients.add(websocket)
        try:
            await websocket.send(json.dumps({"results": self._lyric_payload_bundle()["ws"]}, ensure_ascii=False))
            async for raw_message in websocket:
                response = self._handle_ws_message(raw_message, role=role)
                if response is None:
                    continue
                await websocket.send(json.dumps(response, ensure_ascii=False))
        except Exception:
            pass
        finally:
            with lock:
                clients.discard(websocket)

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
        m = re.fullmatch(r"/api/vocal-removed/([^/]+)", endpoint)
        if m:
            return send("vocal_removed", mode=m.group(1))
        m = re.fullmatch(r"/api/vocalremoved/([^/]+)", endpoint)
        if m:
            return send("vocal_removed", mode=m.group(1))
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

    def _handle_ws_message(self, raw_message: Any, role: str = "admin") -> Dict[str, Any] | None:
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
            if role != "admin" and not self._guest_can_access_api_path(path):
                return {
                    "type": "api_response",
                    "id": req_id,
                    "status": 403,
                    "payload": {
                        "ok": False,
                        "error": {"code": "forbidden", "message": "Guest access is view only."},
                    },
                }
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
                return await websockets.serve(
                    lambda websocket: self._ws_client_handler(websocket, secure_transport=False),
                    self.host,
                    self.ws_port,
                    process_request=lambda path, request_headers: self._ws_process_request(
                        path,
                        request_headers,
                        secure_transport=False,
                    ),
                )

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
        if websockets is None or self.enforce_https:
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

    def _run_secure_ws_server(self) -> None:
        loop = asyncio.new_event_loop()
        self._wss_loop = loop
        asyncio.set_event_loop(loop)
        try:
            async def _start_server():
                return await websockets.serve(
                    lambda websocket: self._ws_client_handler(websocket, secure_transport=True),
                    self.host,
                    self.wss_port,
                    ssl=self._ssl_context,
                    process_request=lambda path, request_headers: self._ws_process_request(
                        path,
                        request_headers,
                        secure_transport=True,
                    ),
                )

            self._wss_server = loop.run_until_complete(_start_server())
            self._wss_enabled = True
            self._wss_ready.set()
            loop.run_forever()
        except Exception:
            self._wss_enabled = False
            self._wss_ready.set()
        finally:
            try:
                if self._wss_server is not None:
                    self._wss_server.close()
                    loop.run_until_complete(self._wss_server.wait_closed())
            except Exception:
                pass
            with self._wss_lock:
                self._wss_clients.clear()
            self._wss_server = None
            self._wss_loop = None
            self._wss_enabled = False
            try:
                loop.close()
            except Exception:
                pass

    def _start_secure_ws_server(self) -> None:
        if websockets is None or (not self.https_enabled):
            self._wss_enabled = False
            return
        self._wss_ready.clear()
        self._wss_thread = threading.Thread(
            target=self._run_secure_ws_server,
            name="pyssp-lyric-wss-dedicated",
            daemon=True,
        )
        self._wss_thread.start()
        self._wss_ready.wait(timeout=1.5)

    async def _wss_broadcast_async(self, message: str) -> None:
        with self._wss_lock:
            clients = list(self._wss_clients)
        stale: list[Any] = []
        for client in clients:
            try:
                await client.send(message)
            except Exception:
                stale.append(client)
        if stale:
            with self._wss_lock:
                for client in stale:
                    self._wss_clients.discard(client)

    def _broadcast_secure_ws(self, message: str) -> None:
        loop = self._wss_loop
        if not self._wss_enabled or loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._wss_broadcast_async(message), loop)
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

    def _stop_secure_ws_server(self) -> None:
        loop = self._wss_loop
        if loop is not None:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
        self._wss_enabled = False

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
        self._broadcast_secure_ws(message)
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
        app.before_request(self._before_request)

        @app.get("/")
        def index():
            index_path = self._web_remote_assets_root / "index.html"
            if not index_path.exists() or not index_path.is_file():
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Web Remote index asset not found."}}), 404
            return send_from_directory(self._web_remote_assets_root, "index.html")

        @app.get("/legacy-index")
        @app.get("/legacy-index/")
        def legacy_index():
            index_path = self._web_remote_assets_root / "legacy-index.html"
            if not index_path.exists() or not index_path.is_file():
                return jsonify({"ok": False, "error": {"code": "not_found", "message": "Legacy Web Remote index asset not found."}}), 404
            return send_from_directory(self._web_remote_assets_root, "legacy-index.html")

        @app.get("/webremote/<path:filename>")
        def webremote_asset(filename: str):
            try:
                clean_name = _normalize_asset_relpath(filename)
            except ValueError:
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
            try:
                clean_name = _normalize_asset_relpath(filename)
            except ValueError:
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
            try:
                clean_name = _normalize_asset_relpath(filename)
            except ValueError:
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
