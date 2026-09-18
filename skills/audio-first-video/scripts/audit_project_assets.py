#!/usr/bin/env python3
"""List used and unused project attachment assets before public handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".mp3", ".m4a", ".wav", ".mp4", ".mov", ".pdf"}
TEXT_SUFFIXES = {".json", ".md", ".html", ".svg", ".js", ".jsx", ".ts", ".tsx", ".css"}
PATH_PATTERN = re.compile(r"(?:\.\.?/)?[^\s\"'<>()[\]{}]+\.(?:png|jpe?g|webp|gif|svg|mp3|m4a|wav|mp4|mov|pdf)", re.IGNORECASE)


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    output = (args.output or (root / "asset-inventory.json")).resolve()

    candidates = []
    for directory in (root / "assets", root / "wechat" / "assets", root / "short-video"):
        if directory.is_dir():
            candidates.extend(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES)
    candidates = sorted(set(path.resolve() for path in candidates))
    references: dict[Path, set[str]] = {path: set() for path in candidates}

    for source in root.rglob("*"):
        if not source.is_file() or source.resolve() == output or source.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        for raw in PATH_PATTERN.findall(text):
            cleaned = raw.rstrip(".,;:，。；：")
            options = [(source.parent / cleaned).resolve(), (root / cleaned).resolve()]
            for target in options:
                if inside(root, target) and target in references and target != source.resolve():
                    references[target].add(source.relative_to(root).as_posix())

    assets = []
    for path in candidates:
        used_by = sorted(references[path])
        assets.append({
            "path": path.relative_to(root).as_posix(),
            "status": "used" if used_by else "unused",
            "usedBy": used_by,
            "sizeBytes": path.stat().st_size,
        })
    payload = {
        "schemaVersion": 1,
        "status": "ready",
        "summary": {
            "total": len(assets),
            "used": sum(item["status"] == "used" for item in assets),
            "unused": sum(item["status"] == "unused" for item in assets),
        },
        "assets": assets,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
