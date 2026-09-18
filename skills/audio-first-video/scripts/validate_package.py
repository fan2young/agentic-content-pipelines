#!/usr/bin/env python3
"""Validate package schemas, fingerprints, adjudication, and timing invariants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import digest, load_json, resolve_project_path
from schema_utils import validate
from validate_editorial_brief import validate_brief
from validate_distribution_brief import validate_brief as validate_distribution_brief
from validate_short_video_release import validate_release as validate_short_video_release
from validate_first_five_proof import validate_proof as validate_first_five_proof
from validate_visual_direction import validate_direction as validate_visual_direction
from validate_hook_package import validate_hooks
from validate_source_visuals import validate_ledger
from validate_visual_proof import validate_proof


BASE_FILES = ["manifest.json", "sources.md", "article.md", "narration-final.txt", "scenes-draft.json", "captions.json", "timing.json", "DESIGN.md"]


def schema_errors(skill_root: Path, name: str, data: dict) -> list[str]:
    schema = load_json(skill_root / "schemas" / name)
    return validate(data, schema)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--stage", choices=["timing", "review", "final"], default="timing")
    args = parser.parse_args()
    root = args.project.resolve()
    skill_root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    warnings: list[str] = []
    required = list(BASE_FILES)
    if args.stage in {"review", "final"}:
        required.extend(["review.mp4", "review-report.json"])
    if args.stage == "final":
        required.extend(["final.mp4", "final-report.json"])
    for name in required:
        if not (root / name).is_file():
            errors.append(f"missing required file: {name}")
    if errors:
        print(json.dumps({"status": "failed", "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 1

    manifest = load_json(root / "manifest.json")
    version = int(manifest.get("schemaVersion", 1))
    is_short_video = manifest.get("project", {}).get("distributionProfile") == "short-video"
    if is_short_video and set(manifest.get("project", {}).get("distributionTargets", [])) != {"douyin", "video-account"}:
        errors.append("short-video project must declare exactly douyin and video-account distributionTargets")
    if version >= 2:
        errors.extend(f"manifest {item}" for item in schema_errors(skill_root, "manifest.schema.json", manifest))
        has_editorial_gate = "editorial_brief" in manifest.get("stages", {})
        if has_editorial_gate:
            brief_path = root / manifest.get("outputs", {}).get("editorialBrief", "editorial-brief.json")
            if not brief_path.is_file():
                errors.append("missing required file: editorial-brief.json")
            else:
                brief_errors, brief_warnings = validate_brief(brief_path, require_publish=True)
                errors.extend(f"editorial brief {item}" for item in brief_errors)
                warnings.extend(f"editorial brief {item}" for item in brief_warnings)
            if manifest.get("stages", {}).get("editorial_brief") != "approved":
                errors.append("editorial_brief stage is not approved")
        else:
            warnings.append("legacy V2 project without editorial brief gate; historical package remains valid")
        source_visuals_name = manifest.get("outputs", {}).get("sourceVisuals")
        if source_visuals_name:
            source_visuals_path = resolve_project_path(root, source_visuals_name)
            if not source_visuals_path.is_file():
                errors.append("missing required file: source-visuals.json")
            else:
                visual_errors, visual_warnings = validate_ledger(source_visuals_path, require_decided=True)
                errors.extend(f"source visuals {item}" for item in visual_errors)
                warnings.extend(f"source visuals {item}" for item in visual_warnings)
        else:
            warnings.append("legacy V2 project without shared source visual gate")
        if is_short_video:
            distribution_gates = (
                ("distributionBrief", "distribution-brief.json", "distribution_strategy", validate_distribution_brief),
                ("hookPackage", "hook-package.json", "hook_selection", validate_hooks),
            )
            for output_key, fallback, stage_name, validator in distribution_gates:
                artifact_name = manifest.get("outputs", {}).get(output_key, fallback)
                artifact_path = resolve_project_path(root, artifact_name)
                if not artifact_path.is_file():
                    errors.append(f"missing required short-video file: {fallback}")
                    continue
                gate_errors, gate_warnings = validator(artifact_path)
                errors.extend(f"{stage_name} {item}" for item in gate_errors)
                warnings.extend(f"{stage_name} {item}" for item in gate_warnings)
                if manifest.get("stages", {}).get(stage_name) != "approved":
                    errors.append(f"{stage_name} stage is not approved")
    else:
        warnings.append("legacy schemaVersion 1 manifest: V2 schema and alignment adjudication are not enforced")
    audio_value = manifest.get("audio", {}).get("path", "")
    try:
        audio_path = resolve_project_path(root, audio_value)
    except ValueError as error:
        errors.append(str(error)); audio_path = root / "__invalid__"
    if not audio_path.is_file():
        errors.append(f"locked audio not found: {audio_value}")
    else:
        recorded = manifest.get("audio", {}).get("sha256")
        actual = digest(audio_path)
        if recorded and recorded != actual:
            errors.append("audio fingerprint changed; timing-derived artifacts are invalid")
        elif not recorded:
            warnings.append("manifest has no audio SHA-256 fingerprint")

    if args.stage in {"review", "final"}:
        delivery_name = manifest.get("outputs", {}).get("deliveryAudioPreflight", "delivery-audio-preflight.json")
        delivery_path = resolve_project_path(root, delivery_name)
        if not delivery_path.is_file():
            errors.append("delivery audio preflight report is missing")
        else:
            delivery_report = load_json(delivery_path)
            if delivery_report.get("status") != "ready":
                errors.append("delivery audio preflight is not ready")
            if audio_path.is_file():
                locked_hash = digest(audio_path)
                lineage_hash = delivery_report.get("upstreamSourceSha256")
                if lineage_hash and lineage_hash != locked_hash:
                    errors.append("delivery audio preflight lineage is stale")
                elif not lineage_hash and delivery_report.get("sourceSha256") != locked_hash:
                    warnings.append("legacy delivery preflight has no locked-audio lineage fingerprint")

    captions = load_json(root / "captions.json")
    errors.extend(f"captions {item}" for item in schema_errors(skill_root, "captions.schema.json", captions))
    duration = float(captions.get("duration", 0))
    previous_end = 0.0
    for caption in captions.get("captions", []):
        start, end = float(caption.get("start", 0)), float(caption.get("end", 0))
        if start < previous_end - 0.001:
            errors.append(f"overlapping caption: {caption.get('id')}")
        if start < 0 or end <= start or end > duration + 0.05:
            errors.append(f"caption out of bounds: {caption.get('id')}")
        previous_end = end
    if version >= 2:
        alignment = manifest.get("alignment", {})
        if manifest.get("stages", {}).get("alignment") != "approved":
            errors.append("alignment stage is not approved")
        if alignment.get("captionsSha256") != digest(root / "captions.json"):
            errors.append("approved captions fingerprint is missing or stale")
        adjudication_name = manifest.get("outputs", {}).get("alignmentAdjudication", "timing-work/alignment-adjudication.json")
        adjudication_path = resolve_project_path(root, adjudication_name)
        if not adjudication_path.is_file():
            errors.append("alignment adjudication record is missing")
        elif load_json(adjudication_path).get("status") != "approved":
            errors.append("alignment adjudication is not approved")

    timing = load_json(root / "timing.json")
    errors.extend(f"timing {item}" for item in schema_errors(skill_root, "timing.schema.json", timing))
    ranges = timing.get("sceneRanges", [])
    if ranges:
        if abs(float(ranges[0]["start"])) > 0.001:
            errors.append("first scene must start at zero")
        for left, right in zip(ranges, ranges[1:]):
            if abs(float(left["end"]) - float(right["start"])) > 0.001:
                errors.append(f"scene gap or overlap between {left['scene']} and {right['scene']}")
        if abs(float(ranges[-1]["end"]) - float(timing.get("compositionDuration", 0))) > 0.001:
            errors.append("last scene must end at compositionDuration")
        if float(timing.get("compositionDuration", 0)) < duration:
            errors.append("composition is shorter than narration audio")

    if args.stage in {"review", "final"}:
        if is_short_video:
            visual_direction_name = manifest.get("outputs", {}).get("visualDirectionProof", "visual-direction-proof.json")
            visual_direction_path = resolve_project_path(root, visual_direction_name)
            if not visual_direction_path.is_file():
                errors.append(f"missing visual direction proof: {visual_direction_name}")
            else:
                direction_errors, direction_warnings = validate_visual_direction(visual_direction_path)
                errors.extend(f"visual_direction {item}" for item in direction_errors)
                warnings.extend(f"visual_direction {item}" for item in direction_warnings)
            if manifest.get("stages", {}).get("visual_direction") != "approved":
                errors.append("visual_direction stage is not approved")
            proof_name = manifest.get("outputs", {}).get("firstFiveProof", "first-five-proof.json")
            proof_path = resolve_project_path(root, proof_name)
            if not proof_path.is_file():
                errors.append("missing required short-video file: first-five-proof.json")
            else:
                proof_errors, proof_warnings = validate_first_five_proof(proof_path)
                errors.extend(f"first_five_proof {item}" for item in proof_errors)
                warnings.extend(f"first_five_proof {item}" for item in proof_warnings)
            if manifest.get("stages", {}).get("first_five_proof") != "approved":
                errors.append("first_five_proof stage is not approved")
        runtime_name = manifest.get("outputs", {}).get("runtimePreflight")
        if runtime_name:
            runtime_path = resolve_project_path(root, runtime_name)
            if not runtime_path.is_file():
                errors.append("runtime preflight report is missing")
            else:
                runtime_report = load_json(runtime_path)
                errors.extend(f"runtime preflight {item}" for item in schema_errors(skill_root, "runtime-preflight-report.schema.json", runtime_report))
                if runtime_report.get("status") != "ready":
                    errors.append("runtime preflight did not pass a real H.264/AAC smoke encode")
                if manifest.get("stages", {}).get("runtime_preflight") != "ready":
                    errors.append("runtime_preflight stage is not ready")
        elif version >= 2:
            warnings.append("legacy V2 project without render runtime preflight")
        proof_name = manifest.get("outputs", {}).get("visualProofReport")
        if proof_name:
            proof_path = resolve_project_path(root, proof_name)
            if not proof_path.is_file():
                errors.append("visual proof report is missing")
            else:
                proof_errors, proof_warnings = validate_proof(proof_path)
                errors.extend(f"visual proof {item}" for item in proof_errors)
                warnings.extend(f"visual proof {item}" for item in proof_warnings)
        elif version >= 2:
            warnings.append("legacy V2 project without pre-full-render visual proof gate")
        review_report = load_json(root / "review-report.json")
        if version >= 2:
            errors.extend(f"review report {item}" for item in schema_errors(skill_root, "review-report.schema.json", review_report))
        if review_report.get("sha256") != digest(root / "review.mp4"):
            errors.append("review.mp4 fingerprint differs from review-report.json")
        if review_report.get("status") != "ready":
            errors.append("review-report.json status must be exactly ready")
        if review_report.get("qa", {}).get("visualReview", {}).get("status") != "approved":
            errors.append("encoded-media visual review is not approved")
        reported_duration = review_report.get("containerDurationSeconds", review_report.get("durationSeconds"))
        if reported_duration is not None and abs(float(reported_duration) - float(timing.get("compositionDuration", 0))) > 0.10:
            errors.append("release candidate duration differs from timing.json")
    if args.stage == "final":
        final_report = load_json(root / "final-report.json")
        if version >= 2:
            errors.extend(f"final report {item}" for item in schema_errors(skill_root, "final-report.schema.json", final_report))
        final_hash = digest(root / "final.mp4")
        if final_report.get("sha256") != final_hash:
            errors.append("final.mp4 fingerprint differs from final-report.json")
        if final_hash != digest(root / "review.mp4"):
            errors.append("final.mp4 is not byte-identical to the approved release candidate")
        final_video = manifest.get("finalVideo", {})
        if final_video.get("sha256") != final_hash:
            errors.append("manifest finalVideo fingerprint is missing or incorrect")
        final_audio = final_video.get("audio", {})
        if final_audio.get("integratedLufs") is None or final_audio.get("truePeakDbtp") is None:
            errors.append("manifest finalVideo loudness metadata is incomplete")
        if is_short_video:
            release_name = manifest.get("outputs", {}).get("shortVideoReleasePackage", "short-video/release-package.json")
            release_path = resolve_project_path(root, release_name)
            if not release_path.is_file():
                errors.append("missing required short-video file: short-video/release-package.json")
            else:
                release_errors, release_warnings = validate_short_video_release(release_path, require_video=True)
                errors.extend(f"distribution_package {item}" for item in release_errors)
                warnings.extend(f"distribution_package {item}" for item in release_warnings)
            if manifest.get("stages", {}).get("distribution_package") != "approved":
                errors.append("distribution_package stage is not approved")
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
