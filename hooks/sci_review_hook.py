#!/usr/bin/env python3
"""Read-only hook adapter for SCI Review System projects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def find_state(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        state = candidate / ".sci-review-system" / "state" / "project_state.json"
        if state.exists():
            return state
    return None


def emit(event: str) -> int:
    state_path = find_state(Path.cwd())
    if state_path is None:
        print(json.dumps({"event": event, "status": "NO_PROJECT_STATE", "action": "show_dashboard_and_offer_intake"}, ensure_ascii=False))
        return 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    payload = {
        "event": event,
        "status": state.get("status"),
        "mode": state.get("mode"),
        "current_unit_id": state.get("current_unit_id"),
        "project_profile": state.get("project_profile"),
        "venue": state.get("venue", {"status": "not_selected"}),
        "capabilities": {key: value.get("status", "NOT_CHECKED") for key, value in state.get("capabilities", {}).items()},
        "source_count": len(state.get("sources", {})),
        "lookup_statuses": {key: value.get("status", "NOT_CHECKED") for key, value in state.get("lookups", {}).items()},
        "blockers": [item for item in state.get("blockers", []) if item.get("status") == "open"],
        "pending_decisions": state.get("decisions", [])[-3:],
        "reading_anchor": state.get("baseline", {}).get("current_anchor"),
        "reminder": "Do not preload PDFs or overwrite a frozen baseline. Run capability preflight before external work; record actual sources/lookups; preserve NOT_CHECKED; keep submission and sending under human control.",
        "state": str(state_path),
    }
    registry = json.loads((SKILL_ROOT / "work-units" / "unit-registry.json").read_text(encoding="utf-8"))
    unit = next((item for item in registry.get("units", []) if item.get("unit_id") == payload["current_unit_id"]), None)
    if unit:
        payload["active_contract"] = {
            "contract_version": registry.get("schema_version"),
            "write_root": registry.get("unit_write_roots", {}).get(unit["unit_id"]),
            "required_outputs": registry.get("completion_outputs", {}).get(unit["unit_id"], {}),
            "required_gates": unit.get("required_gates", []),
            "capability_requirements": registry.get("capability_requirements", {}).get(unit["unit_id"], {}),
            "source_requirements": registry.get("source_requirements", {}).get(unit["unit_id"], {}),
            "next_candidates": unit.get("next_candidates", []),
        }
    if any(item for item in payload["blockers"]):
        payload["gate"] = "BLOCK"
    else:
        payload["gate"] = "CHECK_REQUIRED"
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", choices=["session", "unit"])
    return emit(parser.parse_args().event)


if __name__ == "__main__":
    raise SystemExit(main())
