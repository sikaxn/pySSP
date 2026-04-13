from __future__ import annotations

import argparse
import json
import secrets
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _toronto_now() -> datetime:
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("America/Toronto"))
        except Exception:
            pass
    return datetime.now()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate build metadata into version.json payload.")
    parser.add_argument("--source", required=True, help="Source version.json path")
    parser.add_argument("--output", required=True, help="Output version.json path")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    raw = json.loads(source.read_text(encoding="utf-8"))

    build_number = _toronto_now().strftime("%Y%m%d-%H%M%S")
    build_seed = secrets.token_hex(3).upper()
    build_id = f"{build_number}-{build_seed}"

    raw["build_number"] = build_number
    raw["build_seed"] = build_seed
    raw["build_id"] = build_id

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"version={str(raw.get('version', '')).strip()}")
    print(f"build_id={build_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

