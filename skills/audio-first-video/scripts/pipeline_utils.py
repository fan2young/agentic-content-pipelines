#!/usr/bin/env python3
"""Shared, dependency-free helpers for the V2 pipeline control scripts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


STAGE_VALUES = {"pending", "ready", "approved", "invalidated", "failed", "skipped"}
INVALIDATION_MAP = {
    "editorial_brief": ["distribution_strategy", "hook_selection", "sources", "article", "narration", "audio_lock", "alignment", "timing", "wechat", "social_cards", "slides", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "distribution_strategy": ["hook_selection", "narration", "audio_lock", "alignment", "timing", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "hook_selection": ["narration", "audio_lock", "alignment", "timing", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "sources": ["article", "distribution_strategy", "hook_selection", "narration", "audio_lock", "alignment", "timing", "wechat", "social_cards", "slides", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "article": ["distribution_strategy", "hook_selection", "narration", "audio_lock", "alignment", "timing", "wechat", "social_cards", "slides", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "narration": ["audio_lock", "alignment", "timing", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "audio_lock": ["alignment", "timing", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "alignment": ["timing", "visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "timing": ["visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "wechat": ["wechat"],
    "social_cards": ["social_cards"],
    "slides": ["slides"],
    "visuals": ["visual_direction", "first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "visual_direction": ["first_five_proof", "video_review", "video_final", "distribution_package", "performance_review"],
    "first_five_proof": ["video_review", "video_final", "distribution_package", "performance_review"],
    "video_review": ["video_final", "distribution_package", "performance_review"],
    "distribution_package": ["distribution_package", "performance_review"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_manifest(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing manifest: {path}")
    return path, load_json(path)


def invalidate(manifest: dict[str, Any], source: str, reason: str) -> list[str]:
    targets = INVALIDATION_MAP.get(source)
    if targets is None:
        raise ValueError(f"unknown invalidation source: {source}")
    stages = manifest.setdefault("stages", {})
    changed: list[str] = []
    for target in targets:
        if stages.get(target) not in {"pending", "invalidated"}:
            stages[target] = "invalidated"
            changed.append(target)
        elif target not in stages:
            stages[target] = "invalidated"
            changed.append(target)
    manifest.setdefault("history", []).append({
        "at": now_iso(), "event": "invalidate", "source": source,
        "reason": reason, "stages": targets,
    })
    return changed


def resolve_project_path(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"path escapes project root: {value}") from error
    return candidate


def resolve_media_runtime(root: Path) -> tuple[Path, Path]:
    """Resolve the fingerprinted project runtime, with PATH fallback for standalone tools."""
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        report_name = manifest.get("outputs", {}).get("runtimePreflight", "runtime-preflight.json")
        report_path = resolve_project_path(root, report_name)
        if not report_path.is_file():
            raise RuntimeError("runtime preflight report is required before media processing")
        report = load_json(report_path)
        if report.get("status") != "ready":
            raise RuntimeError("runtime preflight is not ready")
        runtime = report.get("runtime", {})
        resolved = []
        for name in ("ffmpeg", "ffprobe"):
            record = runtime.get(name, {})
            binary = Path(record.get("path", ""))
            if not binary.is_file() or digest(binary) != record.get("sha256"):
                raise RuntimeError(f"fingerprinted {name} runtime is missing or changed")
            resolved.append(binary)
        return resolved[0], resolved[1]
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required")
    return Path(ffmpeg), Path(ffprobe)
