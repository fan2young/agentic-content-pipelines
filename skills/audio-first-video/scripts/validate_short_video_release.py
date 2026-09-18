#!/usr/bin/env python3
"""Validate short-video cover, publish copy, pinned comment, and release mapping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


def validate_release(path: Path, require_video: bool = False) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "short-video-release.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if data["status"] != "approved":
        errors.append("short-video release package must be explicitly approved")
    title_package = data.get("titlePackage")
    if int(data.get("schemaVersion", 1)) >= 2:
        if not isinstance(title_package, dict):
            errors.append("schema-version-2 release package requires titlePackage")
        else:
            titles = [title_package.get("recommended", ""), *title_package.get("alternatives", [])]
            if len(titles) < 3:
                errors.append("titlePackage requires one recommended title and at least two alternatives")
            if len(titles) > 5:
                errors.append("titlePackage allows at most one recommended title and four alternatives")
            if len(titles) != len(set(titles)):
                errors.append("titlePackage titles must be meaningfully distinct and duplicate-free")
    elif title_package is None:
        warnings.append("legacy schema-version-1 release package has no titlePackage")
    if set(data["platforms"]) != {"douyin", "video-account"} or len(data["platforms"]) != 2:
        errors.append("platforms must contain exactly douyin and video-account for the shared release")
    if len(data["topics"]) != len(set(data["topics"])):
        errors.append("topics must be one shared duplicate-free set")
    required_paths = [data["cover"]["path"], data["publishCopyPath"], data["pinnedCommentPath"]]
    if require_video:
        required_paths.append(data["videoPath"])
    for value in required_paths:
        target = path.parents[1] / value
        if not target.is_file() or target.stat().st_size == 0:
            errors.append(f"short-video release artifact is missing or empty: {value}")
    public_copy = [data["cover"]["headline"], data["cover"]["supportText"], *data["topics"]]
    if isinstance(title_package, dict):
        public_copy.extend([title_package.get("recommended", ""), *title_package.get("alternatives", [])])
    for value in (data["publishCopyPath"], data["pinnedCommentPath"]):
        target = path.parents[1] / value
        if target.is_file():
            public_copy.append(target.read_text(encoding="utf-8", errors="replace"))
    platform_terms = ("抖音", "视频号", "douyin", "video account")
    if any(term in text.lower() for text in public_copy for term in platform_terms):
        errors.append("shared public surfaces must not contain platform-named wording")
    if len(data["cover"]["headline"]) > 18:
        warnings.append("cover headline exceeds 18 characters; verify phone-size hierarchy")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--require-video", action="store_true")
    args = parser.parse_args()
    errors, warnings = validate_release(args.package.resolve(), args.require_video)
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
