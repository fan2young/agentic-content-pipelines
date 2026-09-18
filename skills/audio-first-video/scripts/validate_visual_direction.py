#!/usr/bin/env python3
"""Validate the user-approved three-frame channel visual direction gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_utils import digest
from schema_utils import validate


def validate_direction(path: Path) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "visual-direction-proof.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings
    if data["status"] != "approved":
        errors.append("visual direction must be explicitly approved")
    if data["approvedBy"].strip().lower() in {"model", "model:auto", "auto"}:
        errors.append("visual direction requires user approval; model:auto is forbidden")
    project = path.parent
    references = project / "brand-references.json"
    if not references.is_file():
        errors.append("brand-references.json is required")
    elif digest(references) != data["brandReferencesSha256"]:
        errors.append("brand reference fingerprint changed after visual review")
    else:
        ledger = json.loads(references.read_text(encoding="utf-8"))
        if ledger.get("copiedEpisodeCount") != min(ledger.get("availableEpisodeCount", 0), 3):
            errors.append("latest available episode reference pack is incomplete")
    roles = {item["role"] for item in data["frames"]}
    if roles != {"opening", "core-mechanism", "close"}:
        errors.append("visual direction needs exactly opening, core-mechanism, and close frames")
    for item in data["frames"]:
        frame = project / item["path"]
        if not frame.is_file() or frame.stat().st_size == 0:
            errors.append(f"style frame is missing or empty: {item['path']}")
    if not data["checks"]["warmPaperInkRedDefault"] and not data["comparison"]["deviationReason"].strip():
        errors.append("a palette departure requires an episode-specific deviation reason")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_direction(args.report.resolve())
    print(json.dumps({"status": "failed" if errors else "ready", "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
