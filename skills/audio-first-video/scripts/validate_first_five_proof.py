#!/usr/bin/env python3
"""Gate a short-video full render behind a reviewed first-five-second proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


REQUIRED_TIMESTAMPS = (0.0, 0.5, 1.0, 2.0, 3.0, 5.0)


def validate_proof(path: Path) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "first-five-proof.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if data["status"] != "approved":
        errors.append("first-five proof must be explicitly approved")
    duration = float(data["clip"]["durationSeconds"])
    if duration > 8:
        errors.append("first-five proof clip must be no longer than 8 seconds")
    clip = path.parent / data["clip"]["path"]
    if not clip.is_file() or clip.stat().st_size == 0:
        errors.append("first-five proof clip is missing or empty")
    actual = [float(frame["timestamp"]) for frame in data["frames"]]
    for required in REQUIRED_TIMESTAMPS:
        if not any(abs(value - required) <= 0.05 for value in actual):
            errors.append(f"missing sampled frame near {required:.1f} seconds")
    for frame in data["frames"]:
        target = path.parent / frame["path"]
        if not target.is_file() or target.stat().st_size == 0:
            errors.append(f"sampled frame is missing or empty: {frame['path']}")
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
