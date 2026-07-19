#!/usr/bin/env python3
"""Compare number/unit tokens between a baseline and a candidate text."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOKEN = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:\s*[×x–-]\s*\d+(?:\.\d+)?)?\s*(?:%|mm|cm|m|MHz|kHz|GHz|dB|μm|um|°C|MPa|s|ms|μs|us)?", re.IGNORECASE)


def tokens(path: str) -> list[str]:
    return [match.group(0).strip() for match in TOKEN.finditer(Path(path).read_text(encoding="utf-8"))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    args = parser.parse_args()
    before, after = tokens(args.baseline), tokens(args.candidate)
    result = {"verdict": "PASS" if before == after else "BLOCK", "baseline_tokens": before, "candidate_tokens": after, "added": [x for x in after if x not in before], "removed": [x for x in before if x not in after]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

