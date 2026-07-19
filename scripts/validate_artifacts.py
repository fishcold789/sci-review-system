#!/usr/bin/env python3
"""Validate required frontmatter fields for a Markdown artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {"artifact_id", "project_id", "artifact_kind", "work_unit", "status", "language", "run_id", "gate_status", "next_intents"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    args = parser.parse_args()
    text = Path(args.artifact).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        result = {"verdict": "BLOCK", "error": "missing YAML frontmatter"}
    else:
        end = text.find("\n---", 4)
        header = text[4:end] if end >= 0 else ""
        keys = {line.split(":", 1)[0].strip() for line in header.splitlines() if ":" in line and not line.startswith(" ")}
        missing = sorted(REQUIRED - keys)
        result = {"verdict": "PASS" if not missing else "BLOCK", "missing": missing, "fields": sorted(keys)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

