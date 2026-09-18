#!/usr/bin/env python3
"""Validate a short-video 24/72-hour learning record without inventing missing metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


RATE_FIELDS = ("twoSecondBounceRate", "fiveSecondRetentionRate", "averageWatchRatio", "completionRate", "engagementRate", "followerConversionRate")


def validate_review(path: Path) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "performance-review.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if set(data["platforms"]) != {"douyin", "video-account"} or len(data["platforms"]) != 2:
        errors.append("platforms must contain exactly douyin and video-account for the shared release")
    snapshots_by_platform = {platform: [] for platform in data["platforms"]}
    for snapshot in data["snapshots"]:
        snapshots_by_platform.setdefault(snapshot["platform"], []).append(float(snapshot["hoursAfterPublish"]))
        for field in RATE_FIELDS:
            value = snapshot[field]
            if value is not None and float(value) > 100:
                errors.append(f"{field} must be a percentage between 0 and 100")
    for platform, hours in snapshots_by_platform.items():
        if hours != sorted(hours) or len(hours) != len(set(hours)):
            errors.append(f"{platform} snapshots must be ordered with unique hoursAfterPublish")
        if not hours:
            errors.append(f"missing performance snapshots for {platform}")
            continue
        if not any(abs(value - 24) <= 6 for value in hours):
            warnings.append(f"{platform} has no snapshot near 24 hours")
        if max(hours) < 60:
            warnings.append(f"{platform} 72-hour learning is not available yet")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_review(args.review.resolve())
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
