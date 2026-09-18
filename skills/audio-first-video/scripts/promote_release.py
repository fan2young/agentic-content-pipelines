#!/usr/bin/env python3
"""Promote an explicitly approved, QA-passed candidate without rerendering."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from pipeline_utils import digest, load_json, load_manifest, now_iso, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--approve", action="store_true", help="Deprecated; the approved release gate is the authority")
    parser.add_argument("--approved-by", default="user")
    parser.add_argument("--candidate", default="review.mp4")
    parser.add_argument("--review-report", default="review-report.json")
    parser.add_argument("--final", default="final.mp4")
    args = parser.parse_args()
    root = args.project.resolve()
    candidate, report_path, final = root / args.candidate, root / args.review_report, root / args.final
    manifest_path, manifest = load_manifest(root)
    is_short_video = manifest.get("project", {}).get("distributionProfile") == "short-video"
    if is_short_video and manifest.get("stages", {}).get("distribution_package") != "approved":
        raise SystemExit("approve the shared release package before promotion")
    for path in (candidate, report_path):
        if not path.is_file():
            parser.error(f"missing required file: {path.name}")
    report = load_json(report_path)
    if report.get("status") != "ready":
        raise SystemExit("cannot promote until review-report.status is exactly ready")
    candidate_hash = digest(candidate)
    if report.get("sha256") != candidate_hash:
        raise SystemExit("release candidate fingerprint differs from review-report.json")
    validator = Path(__file__).with_name("validate_package.py")
    review_validation = subprocess.run([sys.executable, str(validator), str(root), "--stage", "review"], capture_output=True, text=True)
    if review_validation.returncode:
        detail = review_validation.stdout.strip() or review_validation.stderr.strip()
        raise SystemExit("review package validation failed before promotion: " + detail)
    if final.exists() and digest(final) != candidate_hash:
        raise SystemExit(f"refusing to overwrite different existing final: {final.name}")
    existing = manifest.get("finalVideo", {})
    if final.exists() and existing.get("sha256") == candidate_hash and (root / "final-report.json").is_file():
        print(json.dumps({"status": "approved_final", "cached": True, "final": final.name, "sha256": candidate_hash}, ensure_ascii=False))
        return 0
    if not final.exists():
        try:
            os.link(candidate, final)
        except OSError:
            shutil.copy2(candidate, final)
    if digest(final) != candidate_hash:
        raise SystemExit("promoted final is not byte-identical to the approved candidate")
    approved_at = now_iso()
    final_report = dict(report)
    if "containerDurationSeconds" not in final_report and "durationSeconds" in final_report:
        final_report["containerDurationSeconds"] = final_report.pop("durationSeconds")
    final_report.update({
        "schemaVersion": 2, "file": final.name, "status": "approved_final", "sha256": candidate_hash,
        "sizeBytes": final.stat().st_size, "promotedFrom": candidate.name,
        "byteIdenticalToApprovedCandidate": True,
        "approval": {"status": "approved", "approvedAt": approved_at, "approvedBy": args.approved_by},
    })
    write_json(root / "final-report.json", final_report)
    stages = manifest.setdefault("stages", {})
    stages["video_review"] = "approved"; stages["video_final"] = "approved"
    outputs = manifest.setdefault("outputs", {})
    outputs.update({"videoFinal": final.name, "videoFinalReport": "final-report.json"})
    manifest["finalVideo"] = {
        "path": final.name, "sha256": candidate_hash, "sizeBytes": final.stat().st_size,
        "containerDurationSeconds": final_report.get("containerDurationSeconds"),
        "video": final_report.get("video", {}), "audio": final_report.get("audio", {}),
        "promotedFrom": candidate.name, "approvedAt": approved_at,
    }
    manifest.setdefault("history", []).append({"at": approved_at, "event": "release_promoted", "sha256": candidate_hash})
    write_json(manifest_path, manifest)
    result = subprocess.run([sys.executable, str(validator), str(root), "--stage", "final"], capture_output=True, text=True)
    validation = json.loads(result.stdout) if result.stdout.strip() else {"status": "failed", "errors": [result.stderr.strip() or "validator produced no output"]}
    print(json.dumps({"status": "approved_final" if result.returncode == 0 else "failed", "cached": False, "candidate": candidate.name, "final": final.name, "sha256": candidate_hash, "byteIdentical": True, "validationStatus": validation.get("status")}, ensure_ascii=False, indent=2))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
