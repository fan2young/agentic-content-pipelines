#!/usr/bin/env python3
"""Lock exact approved narration bytes, record metadata, and invalidate timing on change."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from pipeline_utils import digest, invalidate, load_manifest, now_iso, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--approve", action="store_true", help="confirm user approval of delivery and pronunciation")
    parser.add_argument("--replace", action="store_true", help="replace a different existing locked file")
    parser.add_argument("--provider", default="dashscope")
    parser.add_argument("--model", default="")
    parser.add_argument("--voice", default="")
    parser.add_argument("--confirmed-sha256", required=True, help="SHA-256 of the exact candidate the user heard and approved")
    parser.add_argument("--nonstandard-provider-approved-by", help="Explicit user approval for a provider other than DashScope")
    parser.add_argument("--duration-change-approved-by", help="Explicit user approval when replacement duration differs by more than 10 percent")
    parser.add_argument("--reviewer", default="user")
    args = parser.parse_args()
    if not args.approve:
        parser.error("--approve is required after explicit user approval")
    root = args.project.resolve()
    source = args.audio.resolve()
    if not source.is_file():
        parser.error(f"audio not found: {source}")
    manifest_path, manifest = load_manifest(root)
    suffix = source.suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".flac"}:
        parser.error(f"unsupported narration extension: {suffix}")
    destination = root / f"narration-final{suffix}"
    source_hash = digest(source)
    if args.confirmed_sha256 != source_hash:
        parser.error("--confirmed-sha256 does not match the exact candidate bytes")
    provider = args.provider.strip().lower()
    if provider != "dashscope" and not args.nonstandard_provider_approved_by:
        parser.error("non-DashScope narration requires --nonstandard-provider-approved-by after explicit user approval")
    if provider == "dashscope" and (not args.model.strip() or not args.voice.strip()):
        parser.error("DashScope narration requires non-empty --model and --voice")
    analyzer = Path(__file__).with_name("analyze_audio.py")
    result = subprocess.run([sys.executable, str(analyzer), str(source)], check=True, capture_output=True, text=True)
    report = json.loads(result.stdout)
    old_duration = manifest.get("audio", {}).get("durationSeconds")
    new_duration = report.get("duration")
    if args.replace and isinstance(old_duration, (int, float)) and old_duration > 0 and isinstance(new_duration, (int, float)):
        duration_delta = abs(float(new_duration) - float(old_duration)) / float(old_duration)
        if duration_delta > 0.10 and not args.duration_change_approved_by:
            parser.error(f"replacement duration changed by {duration_delta:.1%}; pass --duration-change-approved-by after explicit review")
    if destination.exists() and digest(destination) != source_hash and not args.replace:
        parser.error("a different locked audio already exists; pass --replace only after approving the replacement")
    if source != destination and (not destination.exists() or digest(destination) != source_hash):
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copy2(source, temporary)
        temporary.replace(destination)
    old_hash = manifest.get("audio", {}).get("sha256", "")
    audio = manifest.setdefault("audio", {})
    audio.update({
        "path": destination.name, "source": str(source), "provider": provider,
        "model": args.model, "voice": args.voice, "sha256": source_hash,
        "durationSeconds": report.get("duration"), "sampleRate": report.get("sampleRate"),
        "channels": report.get("channels"), "integratedLufs": report.get("integratedLufs"),
        "truePeakDbtp": report.get("truePeakDbtp"), "lockedAt": now_iso(), "reviewer": args.reviewer,
    })
    manifest.setdefault("stages", {})["audio_lock"] = "approved"
    invalidated = []
    if old_hash and old_hash != source_hash:
        invalidated = invalidate(manifest, "audio_lock", "locked audio SHA-256 changed")
    manifest.setdefault("history", []).append({
        "at": now_iso(), "event": "audio_locked", "sha256": source_hash, "path": destination.name,
        "provider": provider, "model": args.model, "voice": args.voice, "reviewer": args.reviewer,
        "nonstandardProviderApprovedBy": args.nonstandard_provider_approved_by or "",
        "durationChangeApprovedBy": args.duration_change_approved_by or "",
    })
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "approved", "path": destination.name, "sha256": source_hash, "metadata": report, "invalidated": invalidated}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
