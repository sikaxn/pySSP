from __future__ import annotations

import socket
import urllib.error
import urllib.request


def normalize_companion_command_mode(raw: object) -> str:
    token = str(raw or "").strip().lower()
    return token if token in {"udp", "tcp", "http"} else "tcp"


def normalize_companion_command_action(raw: object) -> str:
    token = str(raw or "").strip().lower()
    return token if token in {"press", "down", "up"} else "press"


def send_companion_location_command(
    *,
    host: str,
    mode: str,
    tcp_port: int,
    udp_port: int,
    http_port: int,
    location: str,
    action: str,
    timeout: float = 2.0,
) -> tuple[bool, str]:
    target_host = str(host or "").strip() or "127.0.0.1"
    target_mode = normalize_companion_command_mode(mode)
    target_action = normalize_companion_command_action(action)
    target_location = str(location or "").strip()
    if not target_location:
        return False, "Missing location"
    if target_mode == "http":
        return _send_http(target_host, int(http_port), target_location, target_action, timeout=timeout)
    if target_mode == "udp":
        return _send_udp(target_host, int(udp_port), target_location, target_action, timeout=timeout)
    return _send_tcp(target_host, int(tcp_port), target_location, target_action, timeout=timeout)


def _send_tcp(host: str, port: int, location: str, action: str, *, timeout: float) -> tuple[bool, str]:
    payload = f"LOCATION {location} {action.upper()}\n".encode("utf-8")
    try:
        with socket.create_connection((host, max(1, int(port))), timeout=timeout) as sock:
            sock.sendall(payload)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def _send_udp(host: str, port: int, location: str, action: str, *, timeout: float) -> tuple[bool, str]:
    payload = f"LOCATION {location} {action.upper()}".encode("utf-8")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(payload, (host, max(1, int(port))))
    except Exception as exc:
        return False, str(exc)
    return True, ""


def _send_http(host: str, port: int, location: str, action: str, *, timeout: float) -> tuple[bool, str]:
    url = f"http://{host}:{max(1, int(port))}/api/location/{location}/{action}"
    request = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if int(getattr(response, "status", 200)) >= 400:
                return False, f"HTTP {int(response.status)}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {int(exc.code)}"
    except Exception as exc:
        return False, str(exc)
    return True, ""
