#!/usr/bin/env python3
"""Classify an uncertainty record and emit a human checkpoint package."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


HIGH_RISK = {
    "missing_source",
    "abstract_only",
    "missing_anchor",
    "missing_conditions",
    "conflicting_evidence",
    "mechanism_interpretation",
    "causal_inference",
    "novel_or_time_sensitive",
    "incomparable_metrics",
    "ambiguous_term_or_formula",
    "expert_or_internal_judgment",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="triage uncertainty and build a checkpoint")
    parser.add_argument("record", help="JSON uncertainty record")
    parser.add_argument("--output", help="optional JSON checkpoint output")
    parser.add_argument("--state", help="optional project_state.json to update")
    args = parser.parse_args()
    path = Path(args.record)
    record = json.loads(path.read_text(encoding="utf-8"))
    state = record.get("state", "uncertain")
    trigger = record.get("trigger", "other")
    if state == "verified":
        verdict = "PASS"
        action = "write_bounded"
    elif state == "supported" and trigger not in HIGH_RISK:
        verdict = "WARN"
        action = "write_with_qualification"
    else:
        verdict = "BLOCK"
        action = "pause_and_escalate"
    checkpoint = {
        "checkpoint_id": f"HC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "uncertainty_ids": [record.get("uncertainty_id", "UNREGISTERED")],
        "question": record.get("problem", "请核验该主张的事实、解释或适用范围。"),
        "source_text_or_judgment": record.get("source_text_or_judgment", ""),
        "evidence": record.get("known_facts", []),
        "conflict_or_uncertainty": record.get("unknown_or_contested", []),
        "known_boundary": record.get("known_facts", []),
        "non_self_judgment": ["模型不自行选择冲突解释或补写缺失条件。"],
        "suggested_expert": (record.get("escalation_target") if record.get("escalation_target") in {"advisor", "peer", "domain_expert", "user_choice"} else "user_choice") if verdict == "BLOCK" else "user_choice",
        "status": "open" if verdict == "BLOCK" else "not_required",
        "created_at": now_iso(),
        "answered_at": None,
        "answer": None,
        "decision_id": None,
        "resume_from_artifact": record.get("baseline_artifact", ""),
        "re_audit_required": verdict == "BLOCK",
        "verdict": verdict,
        "permitted_action": action,
    }
    payload = {"verdict": verdict, "uncertainty": record, "human_checkpoint": checkpoint}
    if args.state:
        state_path = Path(args.state)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("uncertainties", {})[record.get("uncertainty_id", checkpoint["uncertainty_ids"][0])] = record
        state.setdefault("human_checkpoints", {})[checkpoint["checkpoint_id"]] = checkpoint
        if verdict == "BLOCK":
            state.setdefault("blockers", []).append({
                "blocker_id": checkpoint["checkpoint_id"],
                "kind": "uncertainty",
                "uncertainty_ids": checkpoint["uncertainty_ids"],
                "affected_unit_ids": record.get("affected_unit_ids", []),
                "status": "open",
                "message": checkpoint["question"],
                "created_at": checkpoint["created_at"],
            })
        state["state_version"] = int(state.get("state_version", 0)) + 1
        state["updated_at"] = now_iso()
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["state_updated"] = str(state_path)
    if args.output:
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if verdict != "BLOCK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
