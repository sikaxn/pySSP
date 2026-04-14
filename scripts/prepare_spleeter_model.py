from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download/copy Spleeter 2stems model into project assets.")
    parser.add_argument(
        "--output",
        default="pyssp/assets/spleeter_models",
        help="Output model root directory (default: pyssp/assets/spleeter_models)",
    )
    args = parser.parse_args()
    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    target_dir = output_root / "2stems"

    with tempfile.TemporaryDirectory(prefix="pyssp_spleeter_model_") as temp_dir:
        os.environ["MODEL_PATH"] = temp_dir
        from spleeter.model.provider import ModelProvider  # type: ignore

        provider = ModelProvider.default()
        resolved_model_dir = Path(provider.get("2stems")).resolve()
        if not resolved_model_dir.exists():
            raise RuntimeError(f"Spleeter model path not found: {resolved_model_dir}")
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(resolved_model_dir, target_dir)

    probe_file = target_dir / ".probe"
    probe_file.write_text("pySSP bundled Spleeter 2stems model", encoding="utf-8")
    print(f"model_dir={target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
