from __future__ import annotations

import json

from pyssp.ndi_config import (
    NDIAccessManagerSettings,
    apply_ndi_access_manager_settings,
    load_ndi_access_manager_settings,
)


def test_apply_ndi_access_manager_settings_writes_expected_fields(tmp_path):
    config_path = tmp_path / "NDI" / "ndi-config.v1.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "ndi": {
                    "groups": {"recv": "Public"},
                    "multicast": {"recv": {"enable": True, "subnets": []}},
                }
            }
        ),
        encoding="utf-8",
    )

    apply_ndi_access_manager_settings(
        NDIAccessManagerSettings.normalized(
            send_groups="Public,Sanctuary",
            discovery_servers="10.0.0.2,10.0.0.3",
            allowed_adapters=("10.0.0.177", "10.0.0.181"),
            multicast_send_enabled=True,
            multicast_send_ttl=8,
            multicast_send_netmask="255.255.255.0",
            multicast_send_netprefix="239.10.10.0",
        ),
        path=config_path,
    )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["ndi"]["groups"]["send"] == "Public,Sanctuary"
    assert payload["ndi"]["groups"]["recv"] == "Public"
    assert payload["ndi"]["networks"]["discovery"] == "10.0.0.2,10.0.0.3"
    assert payload["ndi"]["adapters"]["allowed"] == ["10.0.0.177", "10.0.0.181"]
    assert payload["ndi"]["multicast"]["send"]["enable"] is True
    assert payload["ndi"]["multicast"]["send"]["ttl"] == 8
    assert payload["ndi"]["multicast"]["send"]["netmask"] == "255.255.255.0"
    assert payload["ndi"]["multicast"]["send"]["netprefix"] == "239.10.10.0"
    assert payload["ndi"]["multicast"]["recv"]["enable"] is True


def test_load_ndi_access_manager_settings_reads_defaults_and_normalizes(tmp_path):
    config_path = tmp_path / "ndi-config.v1.json"
    config_path.write_text(
        json.dumps(
            {
                "ndi": {
                    "groups": {"send": "  Public, Choir  "},
                    "networks": {"discovery": "10.0.0.2;10.0.0.3"},
                    "adapters": {"allowed": ["10.0.0.177", "10.0.0.177", "10.0.0.181"]},
                    "multicast": {
                        "send": {
                            "enable": "true",
                            "ttl": "6",
                            "netmask": "255.255.255.0",
                            "netprefix": "239.20.20.0",
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    settings = load_ndi_access_manager_settings(config_path)

    assert settings.send_groups == "Public,Choir"
    assert settings.discovery_servers == "10.0.0.2,10.0.0.3"
    assert settings.allowed_adapters == ("10.0.0.177", "10.0.0.181")
    assert settings.multicast_send_enabled is True
    assert settings.multicast_send_ttl == 6
    assert settings.multicast_send_netmask == "255.255.255.0"
    assert settings.multicast_send_netprefix == "239.20.20.0"
