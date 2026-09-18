#!/usr/bin/env python3
"""Copy a bounded latest-three channel reference pack into the current project."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil

from pipeline_utils import digest, write_json


DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
FRAME_CANDIDATES = (
    "review-scenes-sheet.png",
    "proof-contact-sheet.png",
    "short-video/cover.png",
    "encoded-review-frames/contact-sheet.jpg",
)


def infer_library_root(project: Path) -> Path:
    for parent in (project, *project.parents):
        if (parent / "daily-production").is_dir() or (parent / "video-production").is_dir():
            return parent
    raise ValueError("cannot infer brand library root; pass --library-root")


def episode_sort_key(project: Path) -> tuple[str, float]:
    match = DATE_RE.search(str(project))
    date = match.group(1) if match else "0000-00-00"
    return date, project.stat().st_mtime


def reference_frames(project: Path) -> list[Path]:
    selected = [project / value for value in FRAME_CANDIDATES if (project / value).is_file()]
    if selected:
        return selected[:3]
    for directory in (project / "encoded-review-frames-v2", project / "encoded-review-frames"):
        if directory.is_dir():
            frames = sorted(path for path in directory.glob("*.png") if not path.name.startswith(("black-", "final-")))
            if frames:
                return frames[:3]
    return []


def discover(project: Path, library_root: Path | None = None) -> dict:
    project = project.resolve()
    library_root = (library_root or infer_library_root(project)).resolve()
    candidates: list[tuple[Path, Path, list[Path]]] = []
    for manifest in library_root.rglob("project/manifest.json"):
        candidate = manifest.parent.resolve()
        if candidate == project:
            continue
        design = candidate / "DESIGN.md"
        frames = reference_frames(candidate)
        has_video = any((candidate / name).is_file() for name in ("final.mp4", "review.mp4"))
        if design.is_file() and frames and has_video:
            candidates.append((candidate, design, frames))
    candidates.sort(key=lambda item: episode_sort_key(item[0]), reverse=True)
    output_dir = project / "brand-references"
    output_dir.mkdir(parents=True, exist_ok=True)
    episodes = []
    for index, (source, design, frames) in enumerate(candidates[:3], 1):
        episode_id = f"episode-{index:02d}"
        target_dir = output_dir / episode_id
        target_dir.mkdir(parents=True, exist_ok=True)
        design_target = target_dir / "DESIGN.md"
        shutil.copy2(design, design_target)
        copied_frames = []
        for frame_index, frame in enumerate(frames, 1):
            target = target_dir / f"frame-{frame_index:02d}{frame.suffix.lower()}"
            shutil.copy2(frame, target)
            copied_frames.append(str(target.relative_to(project)))
        episodes.append({
            "id": episode_id,
            "sourceProject": str(source),
            "date": episode_sort_key(source)[0],
            "designPath": str(design_target.relative_to(project)),
            "framePaths": copied_frames,
            "designSha256": digest(design_target),
            "frameSha256": [digest(project / value) for value in copied_frames],
        })
    report = {
        "schemaVersion": 1,
        "status": "ready",
        "libraryRoot": str(library_root),
        "availableEpisodeCount": len(candidates),
        "copiedEpisodeCount": len(episodes),
        "episodes": episodes,
    }
    write_json(project / "brand-references.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--library-root", type=Path)
    args = parser.parse_args()
    try:
        report = discover(args.project, args.library_root)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({
        "status": report["status"],
        "availableEpisodeCount": report["availableEpisodeCount"],
        "copiedEpisodeCount": report["copiedEpisodeCount"],
        "output": str(args.project.resolve() / "brand-references.json"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
