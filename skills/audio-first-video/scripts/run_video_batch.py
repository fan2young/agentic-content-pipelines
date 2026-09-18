#!/usr/bin/env python3
"""Run deterministic preflight or render/QA work and report exceptions only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from pipeline_utils import load_json, write_json


def execute(command: list[str], dry_run: bool) -> dict:
    if dry_run:
        return {"status": "planned", "command": command}
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    combined = (result.stdout + result.stderr).strip()
    return {
        "status": "ready" if result.returncode == 0 else "failed",
        "returnCode": result.returncode,
        "exception": combined[-3000:] if result.returncode else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--mode", choices=("preflight", "review"), required=True)
    parser.add_argument("--composition", type=Path)
    parser.add_argument("--visual-review", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.project.resolve()
    scripts = Path(__file__).resolve().parent
    py = sys.executable
    commands: list[tuple[str, list[str]]] = []
    if args.mode == "preflight":
        commands = [
            ("runtime", [py, str(scripts / "preflight_render_runtime.py"), str(root), "--prefer-hardware"]),
            ("deliveryAudio", [py, str(scripts / "preflight_delivery_audio.py"), str(root / "narration-final.wav"), "--output", str(root / "delivery-audio-preflight.json")]),
        ]
    else:
        composition = (args.composition or root / "hyperframes-video").resolve()
        visual_review = (args.visual_review or root / "visual-review.json").resolve()
        runtime_path = root / "runtime-preflight.json"
        hardware = runtime_path.is_file() and load_json(runtime_path).get("runtime", {}).get("videoEncoder") == "h264_videotoolbox"
        render = [py, str(scripts / "render_local_accelerated.py"), str(root), str(composition), str(root / "review.mp4"), "--quality", "high"]
        if hardware:
            render.append("--require-hardware-encode")
        commands = [
            ("render", render),
            ("encodedQa", [py, str(scripts / "qa_encoded_media.py"), str(root / "review.mp4"), "--timing", str(root / "timing.json"), "--visual-review", str(visual_review), "--output", str(root / "review-report.json")]),
            ("package", [py, str(scripts / "validate_package.py"), str(root), "--stage", "review"]),
        ]

    results = {}
    failed = False
    for name, command in commands:
        if failed:
            results[name] = {"status": "skipped_after_failure"}
            continue
        result = execute(command, args.dry_run)
        results[name] = result
        failed = result["status"] == "failed"
    status = "planned" if args.dry_run else ("failed" if failed else "ready")
    report = {"schemaVersion": 1, "status": status, "mode": args.mode, "results": results}
    report_path = root / f"batch-{args.mode}-report.json"
    if not args.dry_run:
        write_json(report_path, report)
    summary = {
        "status": status,
        "report": None if args.dry_run else str(report_path),
        "failedStep": next((name for name, item in results.items() if item["status"] == "failed"), None),
        "exceptions": {name: item["exception"] for name, item in results.items() if item.get("exception")},
    }
    if args.dry_run:
        summary["steps"] = results
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
