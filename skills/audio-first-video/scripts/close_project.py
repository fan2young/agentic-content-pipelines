#!/usr/bin/env python3
"""Close optional branches explicitly so a finished project has no ambiguous pending work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import load_manifest, now_iso, write_json


OPTIONAL = {"wechat", "social_cards", "slides", "performance_review"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--skip", action="append", choices=sorted(OPTIONAL), default=[])
    parser.add_argument("--skip-pending-optional", action="store_true")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    manifest_path, manifest = load_manifest(root)
    stages = manifest.setdefault("stages", {})
    targets = set(args.skip)
    if args.skip_pending_optional:
        targets.update(name for name in OPTIONAL if stages.get(name) == "pending")
    changed = []
    for name in sorted(targets):
        if stages.get(name) == "pending":
            stages[name] = "skipped"
            changed.append(name)
        elif stages.get(name) not in {"ready", "approved", "skipped"}:
            parser.error(f"cannot close {name} from state {stages.get(name)!r}")
    unresolved = [name for name, value in stages.items() if value in {"pending", "invalidated", "failed"}]
    manifest["closeout"] = {
        "status": "complete" if not unresolved else "incomplete",
        "closedAt": now_iso(),
        "reason": args.reason,
        "skippedStages": changed,
        "unresolvedStages": unresolved,
    }
    manifest.setdefault("history", []).append({"at": now_iso(), "event": "project_closeout", **manifest["closeout"]})
    write_json(manifest_path, manifest)
    print(json.dumps(manifest["closeout"], ensure_ascii=False, indent=2))
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
