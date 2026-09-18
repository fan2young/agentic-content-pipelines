#!/usr/bin/env python3
"""Gate a full video render behind representative frames and a motion proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


def validate_proof(path: Path) -> tuple[list[str], list[str]]:
    root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((root / "schemas/visual-proof.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if data["status"] != "approved":
        errors.append("visual proof must be approved before a full render")
    if int(data.get("schemaVersion", 1)) >= 2:
        if data.get("checks", {}).get("logoAssetExact") is not True:
            errors.append("visual proof must confirm the official logo asset was used without redrawing")
        if data.get("checks", {}).get("logoAxisIsolation") is not True:
            errors.append("visual proof must confirm logo axes are isolated from narrative lines and connectors")
    else:
        warnings.append("legacy visual proof does not record logo asset exactness or axis isolation")
    for name, frame in data["coverage"].items():
        if frame["status"] == "approved":
            target = path.parent / frame["path"]
            if not frame["path"].strip() or not target.is_file() or target.stat().st_size == 0:
                errors.append(f"coverage.{name}: approved frame file is missing or empty")
        elif not frame["reason"].strip():
            errors.append(f"coverage.{name}: not-applicable requires a reason")
    motion = path.parent / data["motionProof"]["path"]
    if not motion.is_file() or motion.stat().st_size == 0:
        errors.append("motionProof.path is missing or empty")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_proof(args.report.resolve())
    status = "failed" if errors else "ready"
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
