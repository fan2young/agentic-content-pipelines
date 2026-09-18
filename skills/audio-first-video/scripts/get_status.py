#!/usr/bin/env python3
"""Report pipeline state, artifact presence, and fingerprint drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import digest, load_manifest, resolve_project_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.project.resolve()
    _, manifest = load_manifest(root)
    stages = manifest.get("stages", {})
    outputs = manifest.get("outputs", {})
    output_stages = {
        "distributionBrief": "distribution_strategy", "hookPackage": "hook_selection",
        "visualDirectionProof": "visual_direction", "firstFiveProof": "first_five_proof", "captions": "alignment",
        "alignmentAdjudication": "alignment", "timing": "timing",
        "videoReview": "video_review", "videoReviewReport": "video_review",
        "videoFinal": "video_final", "videoFinalReport": "video_final",
        "shortVideoReleasePackage": "distribution_package", "performanceReview": "performance_review",
    }
    missing = []
    for key, value in outputs.items():
        stage = output_stages.get(key)
        expected_now = stage is None or stages.get(stage) in {"ready", "approved"}
        if expected_now and isinstance(value, str) and value and not resolve_project_path(root, value).exists():
            missing.append({"output": key, "path": value})
    audio = manifest.get("audio", {})
    audio_drift = None
    if audio.get("path"):
        audio_path = resolve_project_path(root, audio["path"])
        if audio_path.is_file() and audio.get("sha256"):
            actual = digest(audio_path)
            if actual != audio["sha256"]:
                audio_drift = {"recorded": audio["sha256"], "actual": actual}
    payload = {
        "schemaVersion": manifest.get("schemaVersion"), "project": str(root),
        "stages": stages, "missingDeclaredOutputs": missing, "audioFingerprintDrift": audio_drift,
        "readyForReview": all(stages.get(name) in {"ready", "approved"} for name in ("audio_lock", "alignment", "timing")) and audio_drift is None,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"project: {root}\nschema: {payload['schemaVersion']}\nready for review: {str(payload['readyForReview']).lower()}")
        for stage, status in stages.items():
            print(f"{stage:16} {status}")
        if audio_drift:
            print("warning: locked audio fingerprint changed")
        if missing:
            print(f"missing declared outputs: {len(missing)}")
    return 2 if audio_drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
