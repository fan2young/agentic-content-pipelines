#!/usr/bin/env python3
"""Update one manifest stage without hand-editing canonical state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import load_manifest, now_iso, write_json


ALLOWED = {"pending", "ready", "approved", "invalidated", "failed", "skipped"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("stage")
    parser.add_argument("status", choices=sorted(ALLOWED))
    parser.add_argument("--reason", required=True)
    parser.add_argument("--reviewer", default="model")
    args = parser.parse_args()
    path, manifest = load_manifest(args.project.resolve())
    stages = manifest.setdefault("stages", {})
    if args.stage not in stages:
        parser.error(f"unknown stage: {args.stage}")
    previous = stages[args.stage]
    if previous == args.status:
        print(json.dumps({"status": "unchanged", "stage": args.stage, "value": previous}, ensure_ascii=False))
        return 0
    if args.status == "approved" and args.reviewer == "model":
        parser.error("approved requires --reviewer user or another explicit human identity")
    stages[args.stage] = args.status
    manifest.setdefault("history", []).append({
        "at": now_iso(), "event": "stage_marked", "stage": args.stage,
        "from": previous, "to": args.status, "reason": args.reason, "reviewer": args.reviewer,
    })
    write_json(path, manifest)
    print(json.dumps({"status": "updated", "stage": args.stage, "from": previous, "to": args.status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
