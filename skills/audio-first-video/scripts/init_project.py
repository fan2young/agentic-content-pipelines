#!/usr/bin/env python3
"""Initialize a V2 project manifest and stable working directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from pipeline_utils import now_iso, write_json
from validate_editorial_brief import validate_brief


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--editorial-brief", type=Path, required=True)
    parser.add_argument("--platform", default="")
    parser.add_argument("--distribution-profile", choices=["auto", "standard", "short-video"], default="auto")
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--narration-mode", choices=["reporting", "explainer", "review"], default="explainer")
    parser.add_argument("--target-duration", type=float)
    parser.add_argument("--context-orchestration-approved-by", help="Record one-time user authorization for automatic fresh-task handoffs")
    parser.add_argument(
        "--branch", action="append", choices=["wechat", "social_cards", "slides"], default=[],
        help="Enable an optional output branch. Repeat for multiple branches.",
    )
    args = parser.parse_args()

    platform_key = args.platform.strip().lower()
    short_video_tokens = ("抖音", "douyin", "tiktok china", "视频号", "video account", "wechat channels", "weixin channels", "短视频")
    inferred_profile = "short-video" if any(token in platform_key for token in short_video_tokens) else "standard"
    profile = inferred_profile if args.distribution_profile == "auto" else args.distribution_profile
    # 45 seconds is the initial operating hypothesis for short video: the current
    # best episode averages about 9 seconds watched, so 45 seconds makes that a
    # 20% average-view target. It is not treated as a permanent platform rule.
    target_duration = args.target_duration if args.target_duration is not None else (45.0 if profile == "short-video" else None)

    brief_path = args.editorial_brief.resolve()
    brief_errors, brief_warnings = validate_brief(brief_path, require_publish=True)
    if brief_errors:
        parser.error("editorial brief failed production gate: " + "; ".join(brief_errors))
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    selected_id = brief["decision"]["selectedCandidateId"]
    selected = next(item for item in brief["candidates"] if item["id"] == selected_id)

    root = args.project.resolve()
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        parser.error(f"refusing to replace existing manifest: {manifest_path}")
    root.mkdir(parents=True, exist_ok=True)
    for directory in ("timing-work", "assets", "wechat", "social-cards", "slides", "short-video"):
        (root / directory).mkdir(exist_ok=True)
    template = Path(__file__).resolve().parents[1] / "assets" / "manifest.template.json"
    manifest = json.loads(template.read_text(encoding="utf-8"))
    manifest["project"].update({
        "topic": selected["title"], "audience": brief["decision"]["targetReader"], "platform": args.platform,
        "aspectRatio": args.aspect_ratio, "narrationMode": args.narration_mode,
        "targetDurationSeconds": target_duration, "distributionProfile": profile,
        "distributionTargets": ["douyin", "video-account"] if profile == "short-video" else [],
        "contextOrchestration": {
            "mode": "fresh_tasks",
            "status": "approved" if args.context_orchestration_approved_by else "pending",
            "approvedBy": args.context_orchestration_approved_by or "",
            "approvedAt": now_iso() if args.context_orchestration_approved_by else None,
        },
    })
    if profile == "standard":
        for stage in ("distribution_strategy", "hook_selection", "first_five_proof", "distribution_package", "performance_review"):
            manifest["stages"][stage] = "skipped"
    requested_branches = set(args.branch)
    if "公众号" in args.platform or "official account" in platform_key:
        requested_branches.add("wechat")
    for stage in ("wechat", "social_cards", "slides"):
        if stage not in requested_branches:
            manifest["stages"][stage] = "skipped"
    manifest["project"]["requestedBranches"] = sorted(requested_branches)
    shutil.copy2(brief_path, root / "editorial-brief.json")
    manifest["stages"]["editorial_brief"] = "approved"
    manifest["outputs"]["editorialBrief"] = "editorial-brief.json"
    manifest["history"].append({"at": now_iso(), "event": "project_initialized", "editorialBriefWarnings": brief_warnings})
    if args.context_orchestration_approved_by:
        manifest["history"].append({
            "at": now_iso(), "event": "context_orchestration_approved",
            "approvedBy": args.context_orchestration_approved_by,
        })
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "ready", "project": str(root), "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
