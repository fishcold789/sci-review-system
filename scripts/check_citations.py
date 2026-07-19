#!/usr/bin/env python3
"""Check simple citation-key coverage between a manuscript and reference file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


KEY_PATTERN = re.compile(r"\\cite\{([^}]+)\}|\[([A-Za-z]?\d+(?:[-,]\d+)*)\]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manuscript")
    parser.add_argument("references")
    args = parser.parse_args()
    manuscript = Path(args.manuscript).read_text(encoding="utf-8")
    references = Path(args.references).read_text(encoding="utf-8")
    cited: set[str] = set()
    for match in KEY_PATTERN.finditer(manuscript):
        cited.update((match.group(1) or match.group(2)).split(","))
    # BibTeX keys and bracket-style labels are both supported; this is a lint,
    # not a semantic citation verifier.
    ref_keys = set(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)|\[([A-Za-z]?\d+)\]", references))
    refs = {a or b for a, b in ref_keys}
    missing = sorted(cited - refs) if refs else sorted(cited)
    result = {"verdict": "PASS" if not missing else "BLOCK", "cited": sorted(cited), "reference_keys": sorted(refs), "missing": missing, "note": "semantic claim support still requires evidence audit"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())

