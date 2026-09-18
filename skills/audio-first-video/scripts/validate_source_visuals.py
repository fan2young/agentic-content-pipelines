#!/usr/bin/env python3
"""Validate the shared source-visual ledger and usage decisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema_utils import validate


def validate_ledger(path: Path, require_decided: bool = False) -> tuple[list[str], list[str]]:
    root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((root / "schemas/source-visuals.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings

    if require_decided and data["status"] != "decided":
        errors.append("source visual ledger must be decided before channel production")
    ids = [item["id"] for item in data["visuals"]]
    if len(ids) != len(set(ids)):
        errors.append("source visual ids must be unique")

    used = 0
    for item in data["visuals"]:
        if item["usageDecision"] != "use":
            continue
        used += 1
        prefix = f"visual {item['id']}"
        if item["rightsStatus"] in {"unknown", "prohibited"}:
            errors.append(f"{prefix}: selected visual has unusable rightsStatus")
        for key in ("localPath", "owner", "rightsNote", "attribution", "cropNotes"):
            if not item[key].strip():
                errors.append(f"{prefix}: selected visual requires {key}")
        local_path = Path(item["localPath"])
        if local_path.is_absolute() or ".." in local_path.parts:
            errors.append(f"{prefix}: localPath must be project-local")
        elif not (path.parent / local_path).is_file():
            errors.append(f"{prefix}: local file missing: {item['localPath']}")
        if not item["sourceContextPreserved"]:
            errors.append(f"{prefix}: crop must preserve source context")
        if not item["channels"]:
            errors.append(f"{prefix}: selected visual requires at least one channel")
        if item["isThirdPartyEmbedded"] and not item["licenseEvidenceUrl"].startswith(("http://", "https://")):
            errors.append(f"{prefix}: third-party embedded visual requires independent rights evidence")

    if used == 0:
        if require_decided and not data["visualGapReason"].strip():
            errors.append("decided ledger with no selected visual requires visualGapReason")
        else:
            warnings.append("no source visual selected; record the visual gap before ImageGen")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--require-decided", action="store_true")
    args = parser.parse_args()
    errors, warnings = validate_ledger(args.ledger.resolve(), args.require_decided)
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
