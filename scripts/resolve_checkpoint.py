#!/usr/bin/env python3
"""Resolve a human checkpoint and update only its affected uncertainty records."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state")
    parser.add_argument("checkpoint_id")
    parser.add_argument("--answer", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--resolution-state", choices=["verified", "supported", "uncertain"], required=True)
    args = parser.parse_args()
    path = Path(args.state)
    state = json.loads(path.read_text(encoding="utf-8"))
    checkpoints = state.setdefault("human_checkpoints", {})
    checkpoint = checkpoints.get(args.checkpoint_id)
    if checkpoint is None:
        print(json.dumps({"status": "BLOCK", "error": f"checkpoint not found: {args.checkpoint_id}"}, ensure_ascii=False))
        return 1
    timestamp = now_iso()
    checkpoint.update({"status": "accepted", "answered_at": timestamp, "answer": args.answer, "decision_id": args.decision_id})
    resolved = []
    for uncertainty_id in checkpoint.get("uncertainty_ids", []):
        record = state.setdefault("uncertainties", {}).get(uncertainty_id)
        if record is None:
            continue
        record.update({"state": args.resolution_state, "status": "resolved" if args.resolution_state != "uncertain" else "open", "resolved_at": timestamp if args.resolution_state != "uncertain" else None, "resolution": args.answer, "human_checkpoint_id": args.checkpoint_id})
        resolved.append(uncertainty_id)
    for blocker in state.setdefault("blockers", []):
        if blocker.get("blocker_id") == args.checkpoint_id:
            blocker["status"] = "resolved" if args.resolution_state != "uncertain" else "open"
            blocker["resolved_at"] = timestamp if args.resolution_state != "uncertain" else None
            blocker["decision_id"] = args.decision_id
    state.setdefault("decisions", []).append({"decision_id": args.decision_id, "checkpoint_id": args.checkpoint_id, "answer": args.answer, "created_at": timestamp})
    state["state_version"] = int(state.get("state_version", 0)) + 1
    state["updated_at"] = timestamp
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "RESOLVED" if args.resolution_state != "uncertain" else "REOPENED", "checkpoint_id": args.checkpoint_id, "resolved_uncertainties": resolved, "re_audit_required": True, "state_version": state["state_version"]}, ensure_ascii=False, indent=2))
    return 0 if args.resolution_state != "uncertain" else 2


if __name__ == "__main__":
    raise SystemExit(main())

