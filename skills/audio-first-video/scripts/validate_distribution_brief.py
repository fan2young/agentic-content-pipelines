#!/usr/bin/env python3
"""Validate an approved short-video distribution brief before narration approval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


def validate_brief(path: Path) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "distribution-brief.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if data["status"] != "approved" or data["approval"]["status"] != "approved":
        errors.append("distribution brief must be explicitly approved")
    if set(data["platforms"]) != {"douyin", "video-account"} or len(data["platforms"]) != 2:
        errors.append("platforms must contain exactly douyin and video-account for the shared release")
    duration = float(data["format"]["targetDurationSeconds"])
    if not 20 <= duration <= 75:
        duration_exception = data["format"].get("durationException")
        if not duration_exception:
            errors.append("short-video targetDurationSeconds must be between 20 and 75 unless an explicit durationException is approved")
        else:
            warnings.append("an explicitly approved project-specific duration exception is in effect")
    elif not 45 <= duration <= 60:
        warnings.append("target duration is outside the initial 45–60 second validation range")
    if float(data["format"]["payoffBySeconds"]) > 5:
        errors.append("format.payoffBySeconds must be no later than 5 seconds")
    if float(data["format"]["earlyVisualCadenceSeconds"]) > 2.5:
        errors.append("earlyVisualCadenceSeconds must be 2.5 seconds or faster")
    action = data["engagement"]["primaryAction"]
    if action == "none":
        if not data["engagement"]["reason"].strip():
            errors.append("engagement.reason is required when primaryAction is none")
    else:
        for key in ("prompt", "pinnedComment"):
            if not data["engagement"][key].strip():
                errors.append(f"engagement.{key} is required for primaryAction {action}")
    if len(data["cover"]["headline"]) > 18:
        warnings.append("cover.headline exceeds 18 characters; verify phone-size hierarchy")
    if len(data["cover"]["supportText"]) > 18:
        warnings.append("cover.supportText exceeds 18 characters; verify phone-size hierarchy")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_brief(args.brief.resolve())
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
