from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def _normalize_csv_text(value: str) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in str(value or "").replace(";", ",").split(","):
        token = str(raw or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return ",".join(tokens)


def _normalize_adapter_list(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _normalize_csv_text(value)
        return tuple(text.split(",")) if text else ()
    if isinstance(value, (list, tuple, set)):
        text = _normalize_csv_text(",".join(str(item or "") for item in value))
        return tuple(text.split(",")) if text else ()
    return ()


def _normalize_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _normalize_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = int(default)
    return max(int(minimum), min(int(maximum), int(parsed)))


@dataclass(frozen=True)
class NDIAccessManagerSettings:
    send_groups: str = "Public"
    discovery_servers: str = ""
    allowed_adapters: tuple[str, ...] = ()
    multicast_send_enabled: bool = False
    multicast_send_ttl: int = 1
    multicast_send_netmask: str = "255.255.0.0"
    multicast_send_netprefix: str = "239.255.0.0"

    @classmethod
    def normalized(
        cls,
        *,
        send_groups: object = "Public",
        discovery_servers: object = "",
        allowed_adapters: object = (),
        multicast_send_enabled: object = False,
        multicast_send_ttl: object = 1,
        multicast_send_netmask: object = "255.255.0.0",
        multicast_send_netprefix: object = "239.255.0.0",
    ) -> "NDIAccessManagerSettings":
        groups = _normalize_csv_text(str(send_groups or ""))
        discovery = _normalize_csv_text(str(discovery_servers or ""))
        adapters = _normalize_adapter_list(allowed_adapters)
        return cls(
            send_groups=groups or "Public",
            discovery_servers=discovery,
            allowed_adapters=adapters,
            multicast_send_enabled=_normalize_bool(multicast_send_enabled, False),
            multicast_send_ttl=_normalize_int(multicast_send_ttl, 1, 1, 255),
            multicast_send_netmask=str(multicast_send_netmask or "255.255.0.0").strip() or "255.255.0.0",
            multicast_send_netprefix=str(multicast_send_netprefix or "239.255.0.0").strip() or "239.255.0.0",
        )


def ndi_access_manager_config_path() -> Path:
    override = str(os.getenv("PYSSP_NDI_CONFIG_PATH", "") or "").strip()
    if override:
        return Path(override)
    config_dir_override = str(os.getenv("NDI_CONFIG_DIR", "") or "").strip()
    if config_dir_override:
        return Path(config_dir_override) / "ndi-config.v1.json"
    if os.name == "nt":
        program_data = str(os.getenv("PROGRAMDATA", "") or "").strip()
        if program_data:
            return Path(program_data) / "NDI" / "ndi-config.v1.json"
    return Path.home() / ".ndi" / "ndi-config.v1.json"


def load_ndi_access_manager_settings(path: Optional[Path] = None) -> NDIAccessManagerSettings:
    data = read_ndi_access_manager_json(path)
    ndi = data.get("ndi", {}) if isinstance(data, dict) else {}
    groups = ndi.get("groups", {}) if isinstance(ndi, dict) else {}
    networks = ndi.get("networks", {}) if isinstance(ndi, dict) else {}
    adapters = ndi.get("adapters", {}) if isinstance(ndi, dict) else {}
    multicast = ndi.get("multicast", {}) if isinstance(ndi, dict) else {}
    multicast_send = multicast.get("send", {}) if isinstance(multicast, dict) else {}
    return NDIAccessManagerSettings.normalized(
        send_groups=groups.get("send", "Public") if isinstance(groups, dict) else "Public",
        discovery_servers=networks.get("discovery", "") if isinstance(networks, dict) else "",
        allowed_adapters=adapters.get("allowed", []) if isinstance(adapters, dict) else [],
        multicast_send_enabled=multicast_send.get("enable", False) if isinstance(multicast_send, dict) else False,
        multicast_send_ttl=multicast_send.get("ttl", 1) if isinstance(multicast_send, dict) else 1,
        multicast_send_netmask=multicast_send.get("netmask", "255.255.0.0")
        if isinstance(multicast_send, dict)
        else "255.255.0.0",
        multicast_send_netprefix=multicast_send.get("netprefix", "239.255.0.0")
        if isinstance(multicast_send, dict)
        else "239.255.0.0",
    )


def read_ndi_access_manager_json(path: Optional[Path] = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else ndi_access_manager_config_path()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def apply_ndi_access_manager_settings(
    settings: NDIAccessManagerSettings,
    *,
    path: Optional[Path] = None,
) -> Path:
    config_path = Path(path) if path is not None else ndi_access_manager_config_path()
    payload = read_ndi_access_manager_json(config_path)
    ndi = payload.setdefault("ndi", {})
    if not isinstance(ndi, dict):
        ndi = {}
        payload["ndi"] = ndi
    groups = ndi.setdefault("groups", {})
    if not isinstance(groups, dict):
        groups = {}
        ndi["groups"] = groups
    groups["send"] = str(settings.send_groups or "Public")

    networks = ndi.setdefault("networks", {})
    if not isinstance(networks, dict):
        networks = {}
        ndi["networks"] = networks
    networks["discovery"] = str(settings.discovery_servers or "")

    adapters = ndi.setdefault("adapters", {})
    if not isinstance(adapters, dict):
        adapters = {}
        ndi["adapters"] = adapters
    adapters["allowed"] = list(settings.allowed_adapters)

    multicast = ndi.setdefault("multicast", {})
    if not isinstance(multicast, dict):
        multicast = {}
        ndi["multicast"] = multicast
    multicast_send = multicast.setdefault("send", {})
    if not isinstance(multicast_send, dict):
        multicast_send = {}
        multicast["send"] = multicast_send
    multicast_send["enable"] = bool(settings.multicast_send_enabled)
    multicast_send["ttl"] = int(settings.multicast_send_ttl)
    multicast_send["netmask"] = str(settings.multicast_send_netmask or "255.255.0.0")
    multicast_send["netprefix"] = str(settings.multicast_send_netprefix or "239.255.0.0")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return config_path


__all__ = [
    "NDIAccessManagerSettings",
    "apply_ndi_access_manager_settings",
    "load_ndi_access_manager_settings",
    "ndi_access_manager_config_path",
    "read_ndi_access_manager_json",
]
