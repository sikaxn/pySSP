# `pyssp/web_remote.py`

- Source: `pyssp/web_remote.py`
- Module path: `pyssp.web_remote`
- API entries: `11`

## Module Docstring

No module docstring.

## Constants

### Public

- `WEB_REMOTE_GUEST_USERNAME` [constant] (pyssp/web_remote.py:31)
  Detail: Value: 'guest'

## Functions

### Public

- `build_web_remote_ssl_context() -> ssl.SSLContext` [function] (pyssp/web_remote.py:149)

### Internal

- `_parse_basic_auth_header(raw_header: object) -> tuple[str, str] | None` [function] (pyssp/web_remote.py:35)
- `_web_remote_tls_dir() -> Path` [function] (pyssp/web_remote.py:58)
- `_web_remote_tls_paths() -> tuple[Path, Path]` [function] (pyssp/web_remote.py:64)
- `_web_remote_certificate_hostnames() -> list[str]` [function] (pyssp/web_remote.py:69)
- `_web_remote_certificate_ipv4s() -> list[IPv4Address]` [function] (pyssp/web_remote.py:78)
- `_write_web_remote_self_signed_cert(cert_path: Path, key_path: Path) -> None` [function] (pyssp/web_remote.py:107)
- `_normalize_asset_relpath(raw_path: str) -> str` [function] (pyssp/web_remote.py:171)

## Classes

### `QuietRequestHandler`

- Defined at `pyssp/web_remote.py:185`
- Bases: WSGIRequestHandler

#### Public Members

- `log_request(self, _code: int | str = '-', _size: int | str = '-') -> None` [method] (pyssp/web_remote.py:186)
- `log_message(self, _format: str, *args) -> None` [method] (pyssp/web_remote.py:189)

### `WebRemoteServer`

- Defined at `pyssp/web_remote.py:193`

#### Public Members

- `is_running(self) -> bool` [property] (pyssp/web_remote.py:253)
- `start(self) -> None` [method] (pyssp/web_remote.py:256)
- `stop(self) -> None` [method] (pyssp/web_remote.py:295)

#### Internal Members

- `__init__(self, dispatch: DispatchFn, host: str = '0.0.0.0', port: int = 5050, ws_port: int | None = None, *, https_enabled: bool = False, https_port: int | None = None, wss_port: int | None = None, enforce_https: bool = False, require_authentication: bool = False, username: str = 'admin', password: str = '', guest_view_enabled: bool = False) -> None` [constructor] (pyssp/web_remote.py:194)
- `_configure_logging(self) -> None` [method] (pyssp/web_remote.py:330)
- `_resolve_access_role(self, authorization_header: object) -> str` [method] (pyssp/web_remote.py:334)
- `_json_error_response(status: int, code: str, message: str) -> tuple[Response, int]` [staticmethod] (pyssp/web_remote.py:348)
- `_auth_challenge_response(self, *, as_json: bool) -> tuple[Response, int] | Response` [method] (pyssp/web_remote.py:351)
- `_websocket_http_response(status: HTTPStatus, body: str, *, challenge: bool = False) -> tuple[HTTPStatus, list[tuple[str, str]], bytes]` [staticmethod] (pyssp/web_remote.py:360)
- `_guest_can_access_api_path(self, raw_path: str) -> bool` [method] (pyssp/web_remote.py:366)
- `_guest_can_access_http_path(self, path: str) -> bool` [method] (pyssp/web_remote.py:387)
- `_secure_redirect_url(self) -> str` [method] (pyssp/web_remote.py:417)
- `_before_request(self)` [method] (pyssp/web_remote.py:426)
- `_ws_process_request(self, path, request_headers, *, secure_transport: bool)` [method] (pyssp/web_remote.py:442)
- `async _ws_client_handler(self, websocket, *, secure_transport: bool = False) -> None` [method] (pyssp/web_remote.py:457)
- `_safe_int(raw: Any, default: int = 0) -> int` [staticmethod] (pyssp/web_remote.py:483)
- `_merge_params(*sources: Dict[str, Any]) -> Dict[str, Any]` [staticmethod] (pyssp/web_remote.py:490)
- `_dispatch_api_path(self, path: str, method: str = 'GET', params: Dict[str, Any] | None = None) -> Dict[str, Any]` [method] (pyssp/web_remote.py:497)
- `_handle_ws_message(self, raw_message: Any, role: str = 'admin') -> Dict[str, Any] | None` [method] (pyssp/web_remote.py:629)
- `_run_dedicated_ws_server(self) -> None` [method] (pyssp/web_remote.py:668)
- `_start_dedicated_ws_server(self) -> None` [method] (pyssp/web_remote.py:709)
- `async _ws_broadcast_async(self, message: str) -> None` [method] (pyssp/web_remote.py:722)
- `_broadcast_dedicated_ws(self, message: str) -> None` [method] (pyssp/web_remote.py:736)
- `_run_secure_ws_server(self) -> None` [method] (pyssp/web_remote.py:745)
- `_start_secure_ws_server(self) -> None` [method] (pyssp/web_remote.py:787)
- `async _wss_broadcast_async(self, message: str) -> None` [method] (pyssp/web_remote.py:800)
- `_broadcast_secure_ws(self, message: str) -> None` [method] (pyssp/web_remote.py:814)
- `_stop_dedicated_ws_server(self) -> None` [method] (pyssp/web_remote.py:823)
- `_stop_secure_ws_server(self) -> None` [method] (pyssp/web_remote.py:832)
- `_lyric_payload_bundle(self) -> dict` [method] (pyssp/web_remote.py:841)
- `_lyric_broadcast_loop(self) -> None` [method] (pyssp/web_remote.py:873)
- `_broadcast_lyric_ws(self, message: str) -> None` [method] (pyssp/web_remote.py:883)
- `_close_all_lyric_ws_clients(self) -> None` [method] (pyssp/web_remote.py:899)
- `_handle_lyric_ws(self) -> str` [method] (pyssp/web_remote.py:909)
- `_lyric_stage_dir(self, view_name: str) -> Path` [method] (pyssp/web_remote.py:931)
- `_register_routes(self) -> None` [method] (pyssp/web_remote.py:947)
