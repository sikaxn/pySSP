from __future__ import annotations

import argparse
import json
import os
import re
from typing import List


def _parse_plugin_names_from_error(error_text: str) -> List[str]:
    text = str(error_text or "")
    if "plugin_name" not in text:
        return []
    names: List[str] = []
    for match in re.finditer(r'"([^"\r\n]+)"', text):
        value = str(match.group(1) or "").strip()
        if not value or value in {"plugin_name", "__pyssp_probe_nonexistent_plugin__"}:
            continue
        names.append(value)
    output: List[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(name)
    return output


def discover_plugin_names(file_path: str) -> List[str]:
    normalized = os.path.normpath(str(file_path or "").strip())
    if not normalized:
        return []
    try:
        import pedalboard as pb
    except Exception:
        return []
    probe_name = "__pyssp_probe_nonexistent_plugin__"
    for timeout in (2.5, 8.0):
        try:
            pb.load_plugin(normalized, plugin_name=probe_name, initialization_timeout=timeout)
        except Exception as exc:
            names = _parse_plugin_names_from_error(str(exc))
            if names:
                return names
        try:
            plugin = pb.load_plugin(normalized, initialization_timeout=timeout)
            name = str(getattr(plugin, "name", "") or "").strip()
            if name:
                return [name]
        except Exception:
            continue
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    names = discover_plugin_names(str(args.file))
    # Prefix marker so callers can reliably extract payload even if plugin
    # binaries write unrelated logs to stdout/stderr.
    print("PYSSP_VST_PROBE_JSON:" + json.dumps({"ok": True, "names": names}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
