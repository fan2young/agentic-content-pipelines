#!/usr/bin/env python3
"""Apply deterministic downstream invalidation to a V2 manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import INVALIDATION_MAP, invalidate, load_manifest, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--from-stage", required=True, choices=sorted(INVALIDATION_MAP))
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    path, manifest = load_manifest(args.project.resolve())
    changed = invalidate(manifest, args.from_stage, args.reason)
    write_json(path, manifest)
    print(json.dumps({"status": "ready", "source": args.from_stage, "invalidated": INVALIDATION_MAP[args.from_stage], "changed": changed}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
