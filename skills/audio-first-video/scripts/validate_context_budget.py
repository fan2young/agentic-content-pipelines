#!/usr/bin/env python3
"""Validate this multi-stage skill's context architecture release gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("budget", type=Path)
    parser.add_argument("--allow-pending-cold-start", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.budget.read_text(encoding="utf-8"))
    errors = []
    if data.get("workflowKind") != "multi-stage":
        errors.append("workflowKind must be multi-stage")
    contexts = data.get("contexts", [])
    ids = {item.get("id") for item in contexts if isinstance(item, dict)}
    if len(ids) < 2:
        errors.append("multi-stage workflow needs at least two contexts")
    for item in contexts:
        if not item.get("modelInputs") or not item.get("machineState"):
            errors.append(f"context {item.get('id')} must separate modelInputs from machineState")
        if not isinstance(item.get("maxModelInputFiles"), int) or item["maxModelInputFiles"] < 1:
            errors.append(f"context {item.get('id')} needs a positive maxModelInputFiles")
    for boundary in data.get("boundaries", []):
        if boundary.get("from") not in ids or boundary.get("to") not in ids:
            errors.append("boundary references an unknown context")
        if boundary.get("freshTask") is not True or boundary.get("forkAllowed") is not False or boundary.get("carriesConversationHistory") is not False:
            errors.append("every boundary must use a fresh non-forked task without conversation history")
    batching = data.get("deterministicBatching", {})
    if not batching.get("operations") or batching.get("exceptionsOnly") is not True:
        errors.append("deterministic batching must list operations and return exceptions only")
    cold = data.get("coldStartTest", {})
    if cold.get("required") is not True:
        errors.append("cold-start test must be required")
    if not args.allow_pending_cold_start and cold.get("status") != "passed":
        errors.append("cold-start test has not passed")
    print(json.dumps({"status": "failed" if errors else "ready", "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
