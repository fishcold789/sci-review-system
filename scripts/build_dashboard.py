#!/usr/bin/env python3
"""Render a compact human-readable dashboard from project_state.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state")
    args = parser.parse_args()
    path = Path(args.state)
    state = json.loads(path.read_text(encoding="utf-8"))
    anchor = state.get("baseline", {}).get("current_anchor") or {}
    print(f"【Project】{state.get('project_title', '')} ({state.get('project_id', '')})")
    print(f"【Mode】{state.get('mode')}  【Status】{state.get('status')}  【Unit】{state.get('current_unit_id') or '未选择'}")
    print(f"【State】v{state.get('state_version')}  【Run】{state.get('run_id')}")
    print(f"【Anchor】{anchor.get('source', 'none')} | {anchor.get('pages_or_lines', '')}")
    print(f"【Uncertainties】{len(state.get('uncertainties', {}))}  【Human checkpoints】{len(state.get('human_checkpoints', {}))}")
    print(f"【Blockers】{len(state.get('blockers', []))}  【Decisions】{len(state.get('decisions', []))}")
    print("【Reminder】缺证据、冲突或需要专家判断时，暂停受影响主张并生成 human checkpoint。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

