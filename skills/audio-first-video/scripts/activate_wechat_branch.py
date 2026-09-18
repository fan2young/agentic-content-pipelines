#!/usr/bin/env python3
"""Reopen the post-final WeChat branch from an explicit human approval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import load_manifest, now_iso, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.approved_by.strip().lower() in {"model", "codex", "assistant", "auto"}:
        parser.error("WeChat branch activation requires an explicit human identity")

    manifest_path, manifest = load_manifest(args.project.resolve())
    stages = manifest.setdefault("stages", {})
    if stages.get("video_final") != "approved":
        parser.error("video_final must be approved before activating the WeChat branch")
    previous = stages.get("wechat")
    if previous in {"failed", "invalidated"}:
        parser.error(f"cannot activate WeChat from unresolved state {previous!r}")
    if previous not in {"skipped", "pending", "ready", "approved"}:
        parser.error(f"unknown WeChat stage state {previous!r}")

    requested = set(manifest.setdefault("project", {}).get("requestedBranches", []))
    requested.add("wechat")
    manifest["project"]["requestedBranches"] = sorted(requested)
    if previous == "skipped":
        stages["wechat"] = "pending"
    approval = {
        "status": "approved",
        "approvedBy": args.approved_by,
        "approvedAt": now_iso(),
        "scope": ["article-edit", "article-titles", "cover-2.35:1", "inline-images"],
        "reason": args.reason,
    }
    manifest.setdefault("branchApprovals", {})["wechat"] = approval
    manifest.setdefault("history", []).append({
        "at": approval["approvedAt"], "event": "optional_branch_activated",
        "branch": "wechat", "from": previous, "to": stages["wechat"],
        "approvedBy": args.approved_by, "reason": args.reason,
    })
    if manifest.get("closeout", {}).get("status") == "complete" and stages["wechat"] == "pending":
        manifest["closeout"] = {
            "status": "incomplete", "reopenedAt": approval["approvedAt"],
            "reason": "WeChat branch activated after video final", "unresolvedStages": ["wechat"],
        }
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "activated", "stage": stages["wechat"], "approval": approval}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
