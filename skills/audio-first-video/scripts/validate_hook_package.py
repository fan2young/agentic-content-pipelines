#!/usr/bin/env python3
"""Validate evidence-backed short-video hook options and the approved selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


GENERIC_OPENINGS = ("大家好", "欢迎来到", "今天我们来聊", "这一期我们聊", "本期视频")


def validate_hooks(path: Path) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "hook-package.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    ids = [item["id"] for item in data["candidates"]]
    if len(ids) != len(set(ids)):
        errors.append("hook candidate ids must be unique")
    if data["selectedId"] not in ids:
        errors.append("selectedId must resolve to a hook candidate")
        return errors, warnings
    if data["status"] != "approved" or data["approval"]["status"] != "approved":
        errors.append("selected hook must be explicitly approved")
    if set(data["platforms"]) != {"douyin", "video-account"} or len(data["platforms"]) != 2:
        errors.append("platforms must contain exactly douyin and video-account for the shared release")
    selected = next(item for item in data["candidates"] if item["id"] == data["selectedId"])
    if float(selected["payoffBySeconds"]) > 5:
        errors.append("selected hook payoff must land by 5 seconds")
    if any(selected["spokenText"].lstrip().startswith(value) for value in GENERIC_OPENINGS):
        errors.append("selected hook starts with a generic greeting or episode setup")
    if len(selected["firstFrameText"]) > 18:
        warnings.append("selected firstFrameText exceeds 18 characters; verify phone-size readability")
    angles = {item["angle"] for item in data["candidates"]}
    if len(angles) < 2:
        warnings.append("all hook candidates use the same angle; exploration is probably token")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_hooks(args.package.resolve())
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
