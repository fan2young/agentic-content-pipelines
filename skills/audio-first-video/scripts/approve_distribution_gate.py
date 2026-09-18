#!/usr/bin/env python3
"""Validate and record explicit approval of a short-video distribution gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import load_manifest, now_iso, resolve_project_path, write_json
from validate_distribution_brief import validate_brief
from validate_short_video_release import validate_release
from validate_first_five_proof import validate_proof
from validate_hook_package import validate_hooks
from validate_performance_review import validate_review
from validate_visual_direction import validate_direction


GATES = {
    "distribution": ("distributionBrief", "distribution-brief.json", "distribution_strategy", validate_brief),
    "hook": ("hookPackage", "hook-package.json", "hook_selection", validate_hooks),
    "visual-direction": ("visualDirectionProof", "visual-direction-proof.json", "visual_direction", validate_direction),
    "first-five": ("firstFiveProof", "first-five-proof.json", "first_five_proof", validate_proof),
    "release": ("shortVideoReleasePackage", "short-video/release-package.json", "distribution_package", validate_release),
    "performance": ("performanceReview", "short-video/performance-review.json", "performance_review", validate_review),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--gate", choices=sorted(GATES), required=True)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--reviewer", default="user")
    args = parser.parse_args()
    if not args.approve:
        parser.error("--approve is required after explicit review")
    root = args.project.resolve()
    manifest_path, manifest = load_manifest(root)
    if args.gate != "visual-direction" and manifest.get("project", {}).get("distributionProfile") != "short-video":
        parser.error("short-video gates require project.distributionProfile=short-video")
    if args.gate == "visual-direction" and args.reviewer.strip().lower() in {"model", "model:auto", "auto"}:
        parser.error("visual-direction gate requires a human reviewer")
    output_key, fallback, stage, validator = GATES[args.gate]
    artifact_name = manifest.get("outputs", {}).get(output_key, fallback)
    artifact = resolve_project_path(root, artifact_name)
    if not artifact.is_file():
        parser.error(f"missing gate artifact: {artifact_name}")
    errors, warnings = validator(artifact)
    if errors:
        print(json.dumps({"status": "failed", "gate": args.gate, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 1
    approved_at = now_iso()
    manifest.setdefault("stages", {})[stage] = "approved"
    manifest.setdefault("history", []).append({
        "at": approved_at,
        "event": "distribution_gate_approved",
        "gate": args.gate,
        "stage": stage,
        "artifact": artifact_name,
        "reviewer": args.reviewer,
        "warnings": warnings,
    })
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "approved", "gate": args.gate, "stage": stage, "artifact": artifact_name, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
