#!/usr/bin/env python3
"""Detect drift in common scientific protected spans."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PATTERNS = {
    "citations": re.compile(r"(?:\\cite\{[^}]+\}|\[[A-Za-z]?\d+(?:[-,]\d+)*\])"),
    "latex_commands": re.compile(r"\\[A-Za-z]+(?:\[[^]]*\])?(?:\{[^}]*\})?"),
    "figures_tables": re.compile(r"\b(?:Fig(?:ure)?|Table|Eq(?:uation)?)\.?\s*\d+(?:[A-Za-z])?", re.IGNORECASE),
}


def spans(path: str) -> dict[str, list[str]]:
    text = Path(path).read_text(encoding="utf-8")
    return {name: pattern.findall(text) for name, pattern in PATTERNS.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    args = parser.parse_args()
    before, after = spans(args.baseline), spans(args.candidate)
    drift = {key: {"baseline": before[key], "candidate": after[key]} for key in before if before[key] != after[key]}
    result = {"verdict": "PASS" if not drift else "BLOCK", "drift": drift}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not drift else 2


if __name__ == "__main__":
    raise SystemExit(main())

