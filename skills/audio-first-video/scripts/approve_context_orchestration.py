#!/usr/bin/env python3
"""Record or revoke one-project authorization for automatic fresh-task handoffs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import load_manifest, now_iso, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--approve", action="store_true")
    action.add_argument("--revoke", action="store_true")
    parser.add_argument("--approved-by", default="user")
    args = parser.parse_args()

    path, manifest = load_manifest(args.project.resolve())
    status = "approved" if args.approve else "revoked"
    manifest.setdefault("project", {})["contextOrchestration"] = {
        "mode": "fresh_tasks",
        "status": status,
        "approvedBy": args.approved_by if args.approve else "",
        "approvedAt": now_iso() if args.approve else None,
    }
    manifest.setdefault("history", []).append({
        "at": now_iso(), "event": f"context_orchestration_{status}",
        "approvedBy": args.approved_by,
    })
    write_json(path, manifest)
    print(json.dumps({"status": status, "project": str(args.project.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
