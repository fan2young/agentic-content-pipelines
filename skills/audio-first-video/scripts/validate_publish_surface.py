#!/usr/bin/env python3
"""Reject internal production language from reader-facing HTML and SVG assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


FORBIDDEN = {
    "原创机制图": "remove authorship/process labels from the public artwork",
    "设计思路": "remove internal design rationale",
    "连线以": "remove connector implementation notes",
    "框体边缘": "remove geometry implementation notes",
    "安全区": "remove production safe-area language",
    "制作说明": "remove production notes",
    "内部编辑说明": "remove internal editorial notes",
    "变量母稿包": "remove internal master-package labels",
    "发布交付包": "remove internal delivery-package labels",
}

FORBIDDEN_PATTERNS = {
    r"\[S\d+\]": "remove internal source-ledger markers such as [S1]",
    r"\{\{[^{}]+\}\}": "resolve template placeholders before public handoff",
    r"\[待核实[^\]]*\]": "resolve verification placeholders before public handoff",
    r"(?<![A-Za-z])TODO(?![A-Za-z])": "remove unresolved TODO markers from public surfaces",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    findings = []
    for supplied in args.paths:
        targets = sorted(supplied.rglob("*")) if supplied.is_dir() else [supplied]
        for path in targets:
            if not path.is_file() or path.suffix.lower() not in {".html", ".svg", ".md"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for phrase, fix in FORBIDDEN.items():
                if phrase in text:
                    findings.append({"path": str(path), "phrase": phrase, "fix": fix})
            for pattern, fix in FORBIDDEN_PATTERNS.items():
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    findings.append({"path": str(path), "phrase": match.group(0), "fix": fix})
    payload = {"status": "failed" if findings else "ready", "findings": findings}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
