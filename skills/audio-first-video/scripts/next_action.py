#!/usr/bin/env python3
"""Return the single next production action and only the references it needs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import load_manifest, resolve_project_path
from stage_context import CONTEXTS, context_for_stage


FLOW = [
    ("editorial_brief", "Approve a fresh editorial decision", ["references/editorial-topic-gate.md"], "validate_editorial_brief.py"),
    ("sources", "Build sources.md and decide source-visuals.json", ["references/source-visuals.md"], None),
    ("distribution_strategy", "Draft and validate the shared distribution strategy", ["references/short-video-distribution.md"], "validate_distribution_brief.py; mark_stage.py distribution_strategy ready"),
    ("hook_selection", "Draft and validate three openings; select one", ["references/short-video-distribution.md"], "validate_hook_package.py; mark_stage.py hook_selection ready"),
    ("article", "Write the evidence-backed mother article", ["references/contracts.md"], None),
    ("narration", "Approve the strategy, chosen hook, and exact spoken copy as one content lock", ["references/spoken-script-design.md", "references/autonomy-policy.md"], "approve_distribution_gate.py; mark_stage.py narration approved"),
    ("audio_lock", "Generate, review, and lock the exact DashScope narration candidate", ["references/dashscope-tts.md", "references/audio-timing.md"], "synthesize_dashscope.py; lock_audio.py"),
    ("alignment", "Align and adjudicate captions", ["references/audio-timing.md"], "transcribe_and_align.py; approve_alignment.py"),
    ("timing", "Build semantic timing from approved captions", ["references/audio-timing.md"], "build_timing.py"),
    ("visual_direction", "Approve three channel-reference style frames before animation authoring", ["references/visual-direction-lock.md", "references/video-design.md", "references/autonomy-policy.md"], "discover_recent_video_references.py; validate_visual_direction.py; approve_distribution_gate.py --gate visual-direction"),
    ("runtime_preflight", "Verify the exact render runtime and delivery audio", ["references/qa-gates.md"], "run_video_batch.py --mode preflight"),
    ("first_five_proof", "Approve the opening proof before full render", ["references/short-video-distribution.md", "references/video-design.md"], "approve_distribution_gate.py --gate first-five"),
    ("video_review", "Render and QA one final-grade candidate", ["references/qa-gates.md"], "run_video_batch.py --mode review"),
    ("distribution_package", "Approve the final-grade candidate and one shared publishing package as the final release lock", ["references/short-video-distribution.md", "references/autonomy-policy.md"], "approve_distribution_gate.py --gate release"),
    ("video_final", "Promote the approved candidate byte-for-byte", ["references/qa-gates.md"], "promote_release.py"),
    ("wechat", "Produce the explicitly approved post-final WeChat article, titles, 2.35:1 cover, and inline images", ["references/wechat-branch.md", "references/source-visuals.md"], "validate_publish_surface.py; audit_project_assets.py; mark_stage.py wechat ready"),
    ("performance_review", "Record platform-tagged 24/72-hour learning", ["references/short-video-distribution.md"], "validate_performance_review.py"),
]
DONE = {"ready", "approved", "skipped"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--context", choices=CONTEXTS, help="Fresh-task context declared by a verified stage handoff")
    args = parser.parse_args()
    root = args.project.resolve()
    _, manifest = load_manifest(root)
    stages = manifest.get("stages", {})
    missing = []
    for key, value in manifest.get("outputs", {}).items():
        if isinstance(value, str) and value and stages.get({
            "editorialBrief": "editorial_brief", "distributionBrief": "distribution_strategy",
            "hookPackage": "hook_selection", "captions": "alignment", "timing": "timing",
            "visualDirectionProof": "visual_direction", "videoReview": "video_review", "videoFinal": "video_final",
        }.get(key, "")) in DONE and not resolve_project_path(root, value).exists():
            missing.append({"output": key, "path": value})
    if missing:
        payload = {"status": "blocked", "nextAction": "Restore or invalidate missing canonical outputs", "missing": missing, "requiredReads": ["references/failure-recovery.md"]}
    else:
        active = next((item for item in FLOW if item[0] in stages and stages[item[0]] not in DONE), None)
        if active is None:
            payload = {"status": "complete", "nextAction": "Close the project", "requiredReads": [], "command": "close_project.py"}
        else:
            stage, action, refs, command = active
            state = stages.get(stage, "pending")
            required_context = context_for_stage(stage)
            effective_context = args.context or "content"
            if required_context != effective_context:
                handoff = f"handoffs/to-{required_context.replace('_', '-')}.json"
                orchestration = manifest.get("project", {}).get("contextOrchestration", {})
                approved = orchestration.get("status") == "approved"
                payload = {
                    "status": "context_boundary",
                    "stage": stage,
                    "stageStatus": state,
                    "nextAction": "End this task and continue in a fresh task from the minimal handoff",
                    "requiredReads": [],
                    "command": f"build_stage_handoff.py {root} --to-context {required_context}",
                    "handoff": handoff,
                    "resumeCommand": f"next_action.py {root} --context {required_context}",
                    "fromContext": effective_context,
                    "toContext": required_context,
                    "handoffPolicy": "create_fresh_task" if approved else "return_to_user",
                    "orchestrationApproved": approved,
                    "humanCheckpoint": False,
                    "deliverableStatus": "complete" if stage == "performance_review" and stages.get("video_final") == "approved" else "in_progress",
                }
            else:
                payload = {
                    "status": "blocked" if state in {"failed", "invalidated"} else ("awaiting_external" if stage == "performance_review" else "ready"),
                    "stage": stage, "stageStatus": state, "nextAction": action,
                    "requiredReads": refs, "command": command,
                    "context": required_context,
                    "humanCheckpoint": stage in {"narration", "audio_lock", "visual_direction", "distribution_package"},
                    "deliverableStatus": "complete" if stage == "performance_review" and stages.get("video_final") == "approved" else "in_progress",
                }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2 if payload["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
