#!/usr/bin/env python3
"""Build or verify a minimal, hash-bound handoff for a fresh production task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from pipeline_utils import digest, load_manifest, now_iso, resolve_project_path, write_json
from stage_context import CONTEXTS, context_for_stage


DONE = {"ready", "approved", "skipped"}
FLOW_ORDER = (
    "editorial_brief", "sources", "distribution_strategy", "hook_selection", "article", "narration",
    "audio_lock", "alignment", "timing", "visual_direction", "runtime_preflight", "first_five_proof", "video_review",
    "distribution_package", "video_final", "wechat", "performance_review",
)


def active_stage(manifest: dict) -> str | None:
    stages = manifest.get("stages", {})
    return next((stage for stage in FLOW_ORDER if stage in stages and stages[stage] not in DONE), None)


def candidate_inputs(root: Path, manifest: dict, target: str) -> tuple[list[tuple[str, str, bool]], list[str]]:
    outputs = manifest.get("outputs", {})
    if target == "audio_timing":
        items = [
            ("narration", "narration-final.txt", True),
            ("sceneDraft", "scenes-draft.json", True),
        ]
        directories = ["timing-work"]
    elif target == "visual_release":
        items = [
            ("narration", "narration-final.txt", True),
            ("lockedAudio", manifest.get("audio", {}).get("path", "narration-final.wav"), True),
            ("captions", outputs.get("captions", "captions.json"), True),
            ("timing", outputs.get("timing", "timing.json"), True),
            ("sceneDraft", "scenes-draft.json", True),
            ("sources", "sources.md", True),
            ("sourceVisuals", outputs.get("sourceVisuals", "source-visuals.json"), True),
            ("distributionBrief", outputs.get("distributionBrief", "distribution-brief.json"), False),
            ("hookPackage", outputs.get("hookPackage", "hook-package.json"), False),
            ("design", "DESIGN.md", False),
            ("assetLedger", "asset-ledger.json", False),
            ("brandReferences", "brand-references.json", True),
        ]
        directories = ["assets", "brand-references", "hyperframes-video", "short-video"]
    elif target == "article_external":
        items = [
            ("editorialBrief", outputs.get("editorialBrief", "editorial-brief.json"), True),
            ("sources", "sources.md", True),
            ("article", "article.md", True),
        ]
        directories = ["wechat"]
    else:
        raise ValueError(f"handoff is not needed for context: {target}")
    return items, directories


def build(project: Path, target: str) -> int:
    root = project.resolve()
    if target == "visual_release" and not (root / "brand-references.json").is_file():
        discovery = Path(__file__).with_name("discover_recent_video_references.py")
        subprocess.run([sys.executable, str(discovery), str(root)], check=True, capture_output=True, text=True)
    _, manifest = load_manifest(root)
    stage = active_stage(manifest)
    if stage is None:
        raise SystemExit("project has no unfinished stage")
    expected = context_for_stage(stage)
    if target != expected:
        raise SystemExit(f"active stage {stage} requires context {expected}, not {target}")
    items, directories = candidate_inputs(root, manifest, target)
    files = []
    missing = []
    for role, relative, required in items:
        path = resolve_project_path(root, relative)
        if not path.is_file():
            if required:
                missing.append(relative)
            continue
        files.append({"role": role, "path": relative, "sha256": digest(path), "bytes": path.stat().st_size})
    if target == "visual_release" and not missing:
        brand_manifest = json.loads((root / "brand-references.json").read_text(encoding="utf-8"))
        for episode in brand_manifest.get("episodes", []):
            for key in ("designPath", "framePaths"):
                values = episode.get(key, [])
                if isinstance(values, str):
                    values = [values]
                for index, relative in enumerate(values):
                    path = resolve_project_path(root, relative)
                    if not path.is_file():
                        missing.append(relative)
                    else:
                        files.append({"role": f"brandReference:{episode.get('id', 'episode')}:{key}:{index}", "path": relative, "sha256": digest(path), "bytes": path.stat().st_size})
    if missing:
        print(json.dumps({"status": "failed", "missing": missing}, ensure_ascii=False))
        return 1
    handoff = {
        "schemaVersion": 1,
        "status": "ready",
        "createdAt": now_iso(),
        "projectRoot": str(root),
        "nextContext": target,
        "activeStage": stage,
        "orchestration": manifest.get("project", {}).get("contextOrchestration", {"status": "pending"}),
        "machineState": {"path": "manifest.json", "sha256": digest(root / "manifest.json")},
        "modelInputs": files,
        "directories": [value for value in directories if (root / value).is_dir()],
        "forbidden": ["conversationHistory", "priorToolLogs", "fullRenderLogs", "unlistedSiblingFiles"],
        "resumeCommand": f"python3 {Path(__file__).resolve().parent / 'next_action.py'} {root} --context {target}",
    }
    output = root / "handoffs" / f"to-{target.replace('_', '-')}.json"
    write_json(output, handoff)
    print(json.dumps({"status": "ready", "handoff": str(output), "modelInputs": len(files), "nextContext": target}, ensure_ascii=False))
    return 0


def verify(handoff_path: Path) -> int:
    handoff = json.loads(handoff_path.resolve().read_text(encoding="utf-8"))
    root = Path(handoff.get("projectRoot", "")).resolve()
    errors = []
    if handoff.get("status") != "ready" or handoff.get("nextContext") not in CONTEXTS:
        errors.append("invalid handoff header")
    state = handoff.get("machineState", {})
    state_path = root / state.get("path", "manifest.json")
    if not state_path.is_file() or digest(state_path) != state.get("sha256"):
        errors.append("machine state fingerprint changed")
    for item in handoff.get("modelInputs", []):
        try:
            path = resolve_project_path(root, item.get("path", ""))
        except ValueError as error:
            errors.append(str(error))
            continue
        if not path.is_file():
            errors.append(f"missing: {item.get('path')}")
        elif digest(path) != item.get("sha256"):
            errors.append(f"fingerprint changed: {item.get('path')}")
    print(json.dumps({"status": "failed" if errors else "ready", "errors": errors, "nextContext": handoff.get("nextContext"), "resumeCommand": handoff.get("resumeCommand")}, ensure_ascii=False))
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path)
    parser.add_argument("--to-context", choices=CONTEXTS)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        return verify(args.verify)
    if not args.project or not args.to_context:
        parser.error("project and --to-context are required when not verifying")
    return build(args.project, args.to_context)


if __name__ == "__main__":
    raise SystemExit(main())
