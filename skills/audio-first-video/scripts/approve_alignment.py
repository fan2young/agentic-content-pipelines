#!/usr/bin/env python3
"""Record caption adjudication with stricter rules for model approval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from pipeline_utils import digest, invalidate, load_json, load_manifest, now_iso, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--reviewer", default="user")
    parser.add_argument("--note", default="")
    parser.add_argument("--captions", default="timing-work/captions.json")
    args = parser.parse_args()
    if not args.approve:
        parser.error("--approve is required after caption timing review")
    root = args.project.resolve()
    source = root / args.captions
    report_path = root / "timing-work/alignment-report.json"
    if not source.is_file() or not report_path.is_file():
        parser.error("timing-work/captions.json and timing-work/alignment-report.json are required")
    report = load_json(report_path)
    if args.reviewer.startswith("model"):
        exception_count = sum(len(value) for value in report.get("exceptions", {}).values() if isinstance(value, list))
        safe = (
            report.get("status") == "ready" and float(report.get("matchRatio", 0)) >= 0.90
            and not report.get("warnings") and exception_count == 0
        )
        if not safe:
            raise SystemExit("model approval requires ready status, matchRatio >= 0.90, and zero warnings/exceptions")
    canonical = root / "captions.json"
    new_hash = digest(source)
    old_hash = digest(canonical) if canonical.is_file() else ""
    if source.resolve() != canonical.resolve():
        temporary = canonical.with_suffix(".json.tmp")
        shutil.copy2(source, temporary)
        temporary.replace(canonical)
    manifest_path, manifest = load_manifest(root)
    invalidated = []
    if old_hash and old_hash != new_hash:
        invalidated = invalidate(manifest, "alignment", "approved captions SHA-256 changed")
    approved_at = now_iso()
    adjudication = {
        "schemaVersion": 1, "status": "approved", "approvedAt": approved_at,
        "reviewer": args.reviewer, "note": args.note, "captions": canonical.name,
        "captionsSha256": new_hash, "audioSha256": manifest.get("audio", {}).get("sha256", ""),
        "alignmentStatusBeforeAdjudication": report.get("status"),
        "reviewedWarnings": report.get("warnings", []), "reviewedExceptions": report.get("exceptions", {}),
    }
    adjudication_path = root / "timing-work/alignment-adjudication.json"
    write_json(adjudication_path, adjudication)
    manifest["alignment"] = {"captionsSha256": new_hash, "approvedAt": approved_at, "reviewer": args.reviewer}
    manifest.setdefault("stages", {})["alignment"] = "approved"
    manifest.setdefault("outputs", {})["alignmentAdjudication"] = "timing-work/alignment-adjudication.json"
    manifest.setdefault("history", []).append({"at": approved_at, "event": "alignment_approved", "captionsSha256": new_hash})
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "approved", "captionsSha256": new_hash, "adjudication": str(adjudication_path), "invalidated": invalidated}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
