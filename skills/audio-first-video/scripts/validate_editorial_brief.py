#!/usr/bin/env python3
"""Validate a Next Variable editorial brief and its production gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from schema_utils import validate


LANES = {"ai", "business", "career"}
TEST_KEYS = {"newFact", "mechanism", "changedChoice", "evidence", "clearerJudgment"}


def parse_when(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.fromisoformat(normalized + "T00:00:00")
    return parsed.replace(tzinfo=None)


def validate_brief(path: Path, require_publish: bool = False) -> tuple[list[str], list[str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((skill_root / "schemas" / "editorial-brief.schema.json").read_text(encoding="utf-8"))
    errors = validate(data, schema)
    warnings: list[str] = []
    if errors:
        return errors, warnings

    discovery = data["discovery"]
    if set(discovery["scannedLanes"]) != LANES:
        errors.append("discovery.scannedLanes must include ai, business, and career")

    candidates = data["candidates"]
    ids = [item["id"] for item in candidates]
    if len(ids) != len(set(ids)):
        errors.append("candidate ids must be unique")
    represented = {item["lane"] for item in candidates}
    if len(represented) < 2:
        errors.append("candidate pool must represent at least two lanes")
    for missing in LANES - represented:
        if not discovery["laneGapReasons"].get(missing, "").strip():
            errors.append(f"missing candidate lane requires laneGapReasons.{missing}")
    for candidate in candidates:
        try:
            first_public = parse_when(candidate["firstPublicAt"])
            meaningful_update = parse_when(candidate["meaningfulUpdateAt"])
            if meaningful_update < first_public:
                errors.append(f"candidate {candidate['id']}: meaningfulUpdateAt precedes firstPublicAt")
        except ValueError:
            errors.append(f"candidate {candidate['id']}: freshness timestamps must be ISO dates or datetimes")

    decision = data["decision"]
    if decision["status"] == "publish":
        selected_id = decision["selectedCandidateId"]
        selected = next((item for item in candidates if item["id"] == selected_id), None)
        if selected is None:
            errors.append("decision.selectedCandidateId must match a candidate")
        else:
            if selected["brandFitScore"] < 4:
                errors.append("selected candidate brandFitScore must be at least 4")
            if selected["evidenceCount"] < 3:
                errors.append("selected candidate evidenceCount must be at least 3")
            if selected["saturationRisk"] == "high":
                errors.append("selected candidate saturationRisk cannot be high")
            try:
                discovery_at = parse_when(discovery["retrievedAt"])
                meaningful_update = parse_when(selected["meaningfulUpdateAt"])
                freshness_age = discovery_at - meaningful_update
                if freshness_age > timedelta(days=7) and not str(selected.get("freshnessException", "")).strip():
                    errors.append(
                        "selected candidate meaningful update is more than 7 days old; "
                        "record candidate.freshnessException or select a fresher topic"
                    )
            except (KeyError, ValueError):
                pass
            failed_tests = sorted(key for key in TEST_KEYS if not selected["variableTest"].get(key))
            if failed_tests:
                errors.append("selected candidate failed variable tests: " + ", ".join(failed_tests))
        if len(decision["evidence"]) < 3:
            errors.append("publish decision requires at least three evidence points")
        if len(decision["watchSignals"]) < 2:
            errors.append("publish decision requires at least two watch signals")
        for key in ("primaryColumn", "contentType", "targetReader", "readerDecision", "mechanism", "impactMap", "uncertainty"):
            if decision.get(key) is None or not str(decision.get(key, "")).strip():
                errors.append(f"publish decision requires decision.{key}")
        approval = data["approval"]
        if approval["status"] != "approved" or not approval["approvedBy"].strip() or not approval["approvedAt"]:
            errors.append("publish decision requires explicit approval metadata")
    elif require_publish:
        errors.append("editorial decision is no-publish; production must stop")

    if decision["status"] == "no-publish" and data["approval"]["status"] == "approved":
        warnings.append("no-publish decision is approved; retain the brief and do not initialize production")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--require-publish", action="store_true")
    args = parser.parse_args()
    errors, warnings = validate_brief(args.brief.resolve(), args.require_publish)
    status = "failed" if errors else ("ready_with_warnings" if warnings else "ready")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
