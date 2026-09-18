#!/usr/bin/env python3
"""Validate a WeChat 2.35:1 article cover and optional 1:1 share export."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from schema_utils import validate


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9}:
                continue
            length = int.from_bytes(data[i:i + 2], "big")
            if marker in range(0xC0, 0xC4):
                return int.from_bytes(data[i + 5:i + 7], "big"), int.from_bytes(data[i + 3:i + 5], "big")
            i += length
    raise ValueError(f"unsupported or corrupt image: {path}")


def validate_cover(path: Path) -> tuple[list[str], list[str]]:
    root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((root / "schemas/wechat-cover-report.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if data["status"] != "approved" or not data["safeMaster"]:
        errors.append("WeChat cover report must be approved from a square-safe master")
    expected = {"wide": None, "square": (900, 900)}
    for name, dimensions in expected.items():
        if name not in data:
            if name == "square":
                continue
            errors.append(f"{name} cover report is missing")
            continue
        item = data[name]
        target = path.parent / item["path"]
        if not target.is_file():
            errors.append(f"{name} cover is missing: {item['path']}")
            continue
        try:
            actual = image_size(target)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if name == "wide" and abs(actual[0] / actual[1] - 2.35) > 0.01:
            errors.append(f"wide cover must use a 2.35:1 ratio, got {actual[0]}x{actual[1]}")
        if name == "wide" and actual[0] < 900:
            warnings.append(f"wide cover is below the canonical 900px width: {actual[0]}px")
        if dimensions is not None and actual != dimensions:
            errors.append(f"{name} cover must be {dimensions[0]}x{dimensions[1]}, got {actual[0]}x{actual[1]}")
        if actual != (item["width"], item["height"]):
            errors.append(f"{name} report dimensions do not match the file")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_cover(args.report.resolve())
    status = "failed" if errors else "ready"
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
