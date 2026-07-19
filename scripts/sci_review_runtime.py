#!/usr/bin/env python3
"""Dependency-free runtime helper for SCI Review System projects.

The helper initializes a project state, proposes stable artifact names, validates
the minimum state contract, and appends hash-linked events. It is intentionally
conservative: it never deletes files, overwrites an existing state, reads PDF
content, or claims that a scientific gate passed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_STATE_DIR = ".sci-review-system"
SEMANTIC_DIRS = (
    "control",
    "scope",
    "sources",
    "evidence",
    "argument",
    "drafts",
    "language",
    "reading",
    "visuals",
    "reviews",
    "journal",
    "editorial",
    "rights",
    "delivery",
    "_runs",
    "_archive",
)
STATUSES = {"initializing", "running", "paused", "awaiting_decision", "completed", "aborted", "blocked"}
MODES = {"pipeline", "checkpoint", "audit_only", "translation", "revision", "submission"}
STRUCTURED_JSON_REQUIRED_FIELDS = {
    "journal_profile": {"schema_version", "profile_id", "status", "target_journal", "use_mode", "decision", "freshness_policy", "sources", "requirements", "updated_at"},
    "package_plan": {"schema_version", "package_plan_id", "project_id", "status", "journal_context", "package_bases", "items", "mappings", "conflicts", "user_control", "updated_at"},
    "submission_check_report": {"schema_version", "report_id", "package_plan_id", "package_fingerprint", "checked_at", "overall_status", "checks", "unresolved_items", "user_review", "submission_status"},
    "editorial_decision": {"decision_id", "input_state", "source", "journal", "manuscript", "decision", "comment_index", "revision_context", "response_controls", "created_at", "updated_at"},
    "editorial_comment_map": {"comment_map_id", "decision_id", "decision_record_ref", "source_confirmation", "manuscript_baseline", "revision_artifact", "formal_reply_state", "comments", "global_reaudits", "human_control", "updated_at"},
}
STRUCTURED_JSON_SCHEMAS = {
    "journal_profile": "venue-profile.schema.json",
    "package_plan": "package-plan.schema.json",
    "submission_check_report": "submission-check-report.schema.json",
    "editorial_decision": "editorial-decision.schema.json",
    "editorial_comment_map": "editorial-comment-map.schema.json",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def slugify(value: str, fallback: str = "artifact") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    if slug:
        return slug
    return f"{fallback}-{stable_hash(value)[:8]}"


def read_anchor(project_root: Path) -> dict[str, str] | None:
    session = project_root / ".codex" / "reading-session.md"
    if not session.exists():
        return None
    source = None
    anchor = None
    for line in session.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Current source:"):
            source = line.split(":", 1)[1].strip().strip("`")
        elif line.startswith("- Current anchor:"):
            anchor = line.split(":", 1)[1].strip()
    if not source and not anchor:
        return None
    return {"source": source or "", "pages_or_lines": anchor or "", "recorded_in": str(session)}


def project_manifest(project_root: Path) -> dict[str, Any]:
    files: list[str] = []
    skip_dirs = {".git", PROJECT_STATE_DIR, "tmp", "_runs"}
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root)
        if any(part in skip_dirs for part in relative.parts):
            continue
        files.append(relative.as_posix())
    payload = "\n".join(files)
    return {
        "schema_version": "0.1",
        "project_root": str(project_root.resolve()),
        "captured_at": now_iso(),
        "files": files,
        "manifest_hash": f"sha256:{stable_hash(payload)}",
    }


def state_paths(project_root: Path) -> tuple[Path, Path, Path]:
    base = project_root / PROJECT_STATE_DIR
    return base / "state" / "project_state.json", base / "manifests" / "baseline--v001.json", base / "events.jsonl"


def load_profile_index() -> list[dict[str, Any]]:
    path = SKILL_ROOT / "project-profiles" / "index.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("profiles", [])


def select_project_profile(text: str, requested: str) -> dict[str, str] | None:
    profiles = load_profile_index()
    if requested == "none":
        return None
    if requested != "auto":
        match = next((item for item in profiles if item.get("profile_id") == requested), None)
        if match is None:
            raise ValueError(f"unknown project profile: {requested}")
        reason = "explicit user/runtime selection"
    else:
        lowered = text.casefold()
        match = next(
            (
                item
                for item in profiles
                if not any(term.casefold() in lowered for term in item.get("exclusions", []))
                and any(term.casefold() in lowered for term in [*item.get("triggers", []), *item.get("aliases", [])])
            ),
            None,
        )
        if match is None:
            return None
        reason = "matched profile index trigger"
    return {
        "profile_id": match["profile_id"],
        "profile_version": match["version"],
        "path": match["path"],
        "selection_reason": reason,
    }


def append_event(events_path: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    previous_hash = ""
    if events_path.exists():
        lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            previous_hash = json.loads(lines[-1]).get("event_hash", "")
    event = {
        "event_id": f"evt-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "event_type": event_type,
        "created_at": now_iso(),
        "prev_event_hash": previous_hash,
        "payload": payload,
    }
    canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    event["event_hash"] = f"sha256:{stable_hash(canonical)}"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def init_project(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    workspace_root = SKILL_ROOT.parent.resolve()
    if root == workspace_root and not args.allow_root_project:
        print(json.dumps({
            "status": "BLOCK",
            "error": "refusing to initialize project outputs in the repository root",
            "reason": "use a named project directory or a path under <skill-root>/res for a smoke test",
            "override": "rerun with --allow-root-project only when the user explicitly wants root-level project state",
        }, ensure_ascii=False, indent=2))
        return 1
    if root == SKILL_ROOT.resolve():
        print(json.dumps({"status": "BLOCK", "error": "refusing to initialize project outputs inside the skill package"}, ensure_ascii=False, indent=2))
        return 1
    root.mkdir(parents=True, exist_ok=True)
    state_path, manifest_path, events_path = state_paths(root)
    if state_path.exists():
        print(json.dumps({"status": "EXISTS", "state": str(state_path)}, ensure_ascii=False))
        return 2
    for directory in SEMANTIC_DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = project_manifest(root)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_id = f"run-{datetime.now().strftime('%Y%m%d')}-001"
    anchor = read_anchor(root)
    project_profile = select_project_profile(f"{args.title}\n{args.intent}", args.profile)
    state = {
        "schema_version": "0.3",
        "project_id": slugify(args.project_id, fallback="project"),
        "project_title": args.title,
        "project_root": str(root),
        "run_id": run_id,
        "status": "running",
        "mode": args.mode,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "state_version": 1,
        "current_unit_id": None,
        "project_profile": project_profile,
        "entry": {
            "intent": args.intent,
            "entry_kind": "topic",
            "detected_artifact_ids": [],
            "assumptions": [],
            "user_confirmed": False,
        },
        "scope": {
            "research_question": None,
            "in_scope": [],
            "out_of_scope": [],
            "target_languages": ["zh", "en"],
            "target_outputs": ["review_manuscript"],
            "scope_version": "v001",
        },
        "baseline": {
            "manifest_path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "reading_session_path": str(root / ".codex" / "reading-session.md"),
            "current_anchor": anchor,
            "captured_at": now_iso(),
        },
        "units": {},
        "artifacts": {},
        "sources": {},
        "lookups": {},
        "capabilities": {},
        "venue": {
            "status": "not_selected",
            "journal_name": None,
            "decision_id": None,
            "set_by": "runtime_default",
            "updated_at": now_iso(),
        },
        "gates": {},
        "handoffs": {},
        "review_protocol": None,
        "uncertainties": {},
        "human_checkpoints": {},
        "pause_records": [],
        "decisions": [],
        "blockers": [],
        "policy": {
            "write_mode": "scoped",
            "allow_parallel_agents": False,
            "require_human_at": ["scope_lock", "evidence_conflict", "final_release"],
            "allow_auto_scientific_rewrite": False,
            "sensitive_material_upload": "deny",
        },
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_event(events_path, "project_initialized", {"project_id": state["project_id"], "run_id": run_id})
    print(json.dumps({"status": "CREATED", "state": str(state_path), "manifest": str(manifest_path), "run_id": run_id, "project_profile": project_profile}, ensure_ascii=False, indent=2))
    return 0


def load_state(project_root: str) -> tuple[Path, dict[str, Any]]:
    path, _, _ = state_paths(Path(project_root).expanduser().resolve())
    if not path.exists():
        raise FileNotFoundError(f"project state not found: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def load_registry() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = SKILL_ROOT / "work-units" / "unit-registry.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    units = {unit["unit_id"]: unit for unit in registry.get("units", [])}
    dangling = {unit_id: [next_id for next_id in unit.get("next_candidates", []) if next_id not in units] for unit_id, unit in units.items()}
    dangling = {unit_id: values for unit_id, values in dangling.items() if values}
    if dangling:
        raise ValueError(f"unit registry contains dangling transitions: {dangling}")
    return registry, units


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state["state_version"] = int(state.get("state_version", 0)) + 1
    state["updated_at"] = now_iso()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_expected_version(state: dict[str, Any], expected: int | None) -> dict[str, Any] | None:
    if expected is not None and state.get("state_version") != expected:
        return {"status": "CONFLICT", "expected_state_version": expected, "actual_state_version": state.get("state_version")}
    return None


def registered_artifact_types(state: dict[str, Any], unit_id: str | None = None, artifact_ids: set[str] | None = None) -> set[str]:
    return {
        artifact.get("artifact_type", "")
        for key, artifact in state.get("artifacts", {}).items()
        if artifact.get("status") in {"candidate", "verified"}
        and (unit_id is None or artifact.get("source_unit_id") == unit_id)
        and (artifact_ids is None or key in artifact_ids)
    }


def start_requirements_for_mode(registry: dict[str, Any], unit_id: str, mode: str) -> dict[str, list[str]]:
    raw = registry.get("start_requirements", {}).get(unit_id, {})
    all_items = list(raw.get("all", []))
    any_items = list(raw.get("any", []))
    if mode == "pipeline":
        all_items.extend(raw.get("pipeline_all", []))
        any_items.extend(raw.get("pipeline_any", []))
    return {"all": all_items, "any": any_items}


def latest_gate(state: dict[str, Any], unit_id: str, kind: str, gate_ids: set[str] | None = None) -> dict[str, Any] | None:
    matches = [gate for key, gate in state.get("gates", {}).items() if gate.get("unit_id") == unit_id and gate.get("kind") == kind and (gate_ids is None or key in gate_ids)]
    return sorted(matches, key=lambda item: item.get("created_at", ""))[-1] if matches else None


def open_uncertainty_blockers(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in state.get("blockers", []) if item.get("kind") == "uncertainty" and item.get("status") == "open"]


def relevant_uncertainty_blockers(state: dict[str, Any], unit_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in open_uncertainty_blockers(state)
        if not item.get("affected_unit_ids") or unit_id in item.get("affected_unit_ids", [])
    ]


def uncertainty_blockers_for_unit(registry: dict[str, Any], unit: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    unit_id = unit["unit_id"]
    if unit_id in set(registry.get("contract_defaults", {}).get("uncertainty_resolution_units", [])):
        return []
    blockers = relevant_uncertainty_blockers(state, unit_id)
    if not blockers:
        return []
    required = set(unit.get("required_gates", []))
    if "uncertainty" in required:
        return blockers
    if registry.get("contract_defaults", {}).get("block_science_units_on_open_uncertainty") and "science" in required:
        return blockers
    return []


def known_decision_ids(state: dict[str, Any]) -> set[str]:
    return {item.get("decision_id", "") for item in state.get("decisions", []) if item.get("decision_id")}


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def project_file_record(root: Path, raw_path: str) -> tuple[Path | None, str | None, str | None]:
    if not raw_path:
        return None, None, None
    path = Path(raw_path)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    if path != root and root not in path.parents:
        return None, None, "file is outside project root"
    if not path.exists() or not path.is_file():
        return None, None, "file does not exist"
    digest = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    return path, digest, None


def capability_requirement_errors(state: dict[str, Any], registry: dict[str, Any], unit_id: str, phase: str) -> list[str]:
    requirement = registry.get("capability_requirements", {}).get(unit_id, {})
    if not requirement or requirement.get("phase", "start") != phase:
        return []
    accepted = set(requirement.get("accepted_statuses", ["READY", "DEGRADED"]))
    capabilities = state.get("capabilities", {})
    def status_for(name: str) -> str:
        matches = [item for key, item in capabilities.items() if key == name or item.get("category") == name]
        if any(item.get("status") == "READY" for item in matches):
            return "READY"
        if any(item.get("status") == "DEGRADED" for item in matches):
            return "DEGRADED"
        if any(item.get("status") == "BLOCKED" for item in matches):
            return "BLOCKED"
        return "NOT_CHECKED"
    required_all = requirement.get("all", [])
    required_any = requirement.get("any", [])
    errors = [
        f"capability {name} is {status_for(name)}"
        for name in required_all
        if status_for(name) not in accepted
    ]
    if required_any and not any(status_for(name) in accepted for name in required_any):
        observed = {name: status_for(name) for name in required_any}
        errors.append(f"none of the alternative capabilities is executable: {observed}")
    return errors


def source_requirement_errors(state: dict[str, Any], registry: dict[str, Any], unit_id: str, phase: str) -> list[str]:
    requirement = registry.get("source_requirements", {}).get(unit_id, {})
    if not requirement or requirement.get("phase", "complete") != phase:
        return []
    required_venue_status = requirement.get("when_venue_status")
    if required_venue_status and state.get("venue", {}).get("status") != required_venue_status:
        return []

    errors: list[str] = []
    allowed_authority = set(requirement.get("authority", []))
    max_age_days = requirement.get("max_age_days")
    require_snapshot = bool(requirement.get("require_snapshot"))
    qualifying: list[dict[str, Any]] = []
    for source in state.get("sources", {}).values():
        if source.get("record_check", {}).get("status") != "PASS" or source.get("freshness", {}).get("status") != "PASS":
            continue
        if allowed_authority and source.get("authority_level") not in allowed_authority:
            continue
        accessed_at = source.get("accessed_at") or ""
        accessed = parse_iso_date(accessed_at[:10])
        if max_age_days is not None and (accessed is None or (date.today() - accessed).days < 0 or (date.today() - accessed).days > int(max_age_days)):
            continue
        if require_snapshot and not source.get("provenance", {}).get("trace_ref"):
            continue
        qualifying.append(source)

    qualifying_types = {source.get("source_type") for source in qualifying}
    for group in requirement.get("required_source_groups", []):
        if not qualifying_types.intersection(group):
            errors.append(f"missing verified source from required group: {group}")

    minimum_sources = int(requirement.get("min_verified_sources", 0))
    if len(qualifying) < minimum_sources:
        errors.append(f"requires at least {minimum_sources} verified sources; found {len(qualifying)}")

    minimum_lookups = int(requirement.get("min_pass_lookups", 0))
    passed_lookups = [item for item in state.get("lookups", {}).values() if item.get("status") == "PASS"]
    if unit_id == "journal-fit" and qualifying:
        qualifying_ids = {item.get("source_id") for item in qualifying}
        passed_lookups = [item for item in passed_lookups if qualifying_ids.intersection(item.get("source_ids", []))]
    if len(passed_lookups) < minimum_lookups:
        errors.append(f"requires at least {minimum_lookups} evidence-backed PASS lookup records; found {len(passed_lookups)}")
    return errors


def mutation_error(state: dict[str, Any]) -> str | None:
    if state.get("policy", {}).get("write_mode") != "scoped":
        return "project policy is read-only"
    if state.get("status") != "running":
        return f"project is not mutable from status: {state.get('status')}"
    return None


def active_unit_error(state: dict[str, Any], unit_id: str, registry: dict[str, Any], allowed_statuses: set[str]) -> str | None:
    if state.get("current_unit_id") != unit_id:
        return f"unit is not the active work unit: {unit_id}"
    unit_state = state.get("units", {}).get(unit_id)
    if not unit_state or not unit_state.get("started_at"):
        return "unit has not been started through the runtime"
    if unit_state.get("contract_version") != registry.get("schema_version"):
        return "active unit contract version does not match the registry"
    if unit_state.get("status") not in allowed_statuses:
        return f"unit status does not permit this action: {unit_state.get('status')}"
    return None


def parse_markdown_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return {}


def json_schema_errors(data: Any, artifact_type: str) -> list[str]:
    schema_name = STRUCTURED_JSON_SCHEMAS.get(artifact_type)
    if schema_name is None:
        return []
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["JSON Schema validation is unavailable; install requirements.txt"]

    schema_path = SKILL_ROOT / "schemas" / schema_name
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"cannot load JSON Schema {schema_name}: {exc}"]

    errors: list[str] = []
    for issue in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in issue.absolute_path
        )
        errors.append(f"{artifact_type} schema {location}: {issue.message}")
    return errors


def structured_json_errors(data: Any, artifact_type: str) -> list[str]:
    if artifact_type not in STRUCTURED_JSON_REQUIRED_FIELDS:
        return []
    if not isinstance(data, dict):
        return [f"{artifact_type} must be a JSON object"]
    schema_errors = json_schema_errors(data, artifact_type)
    if schema_errors:
        return schema_errors
    errors: list[str] = []
    missing = sorted(STRUCTURED_JSON_REQUIRED_FIELDS[artifact_type] - set(data))
    if missing:
        errors.append(f"{artifact_type} missing schema fields: {', '.join(missing)}")
        return errors
    if artifact_type == "journal_profile":
        status = data.get("status")
        if status == "not_selected" and (data.get("target_journal") is not None or data.get("sources") or data.get("requirements") or data.get("use_mode") != "skipped"):
            errors.append("not_selected journal profile must be empty and skipped")
        if status == "candidate" and any(item.get("enforcement") != "exploratory" for item in data.get("requirements", []) if isinstance(item, dict)):
            errors.append("candidate journal requirements may only be exploratory")
        if status == "confirmed":
            source_types = {item.get("source_type") for item in data.get("sources", []) if isinstance(item, dict) and item.get("freshness", {}).get("status") == "current"}
            if not {"author_guidelines", "submission_system"}.issubset(source_types):
                errors.append("confirmed journal profile needs current official author-guideline and submission-system sources")
            if not data.get("decision", {}).get("confirmed_by_user"):
                errors.append("confirmed journal profile lacks user confirmation")
    elif artifact_type == "package_plan":
        if not data.get("package_bases"):
            errors.append("package plan must be driven by a user manifest, template, or instruction")
        user_control = data.get("user_control", {})
        if user_control.get("final_shape_owner") != "user" or user_control.get("submission_actor") != "user" or user_control.get("system_may_submit") is not False:
            errors.append("package shape and submission action must remain under user control")
        journal_status = data.get("journal_context", {}).get("status")
        if journal_status in {"not_selected", "candidate"}:
            if data.get("journal_context", {}).get("compliance_claim_allowed"):
                errors.append("journal compliance cannot be claimed before confirmation")
            if any(item.get("required_by") == "confirmed_journal" for item in data.get("items", []) if isinstance(item, dict)):
                errors.append("unconfirmed journal cannot impose package items")
    elif artifact_type == "submission_check_report":
        overall = data.get("overall_status")
        checks = [item for item in data.get("checks", []) if isinstance(item, dict)]
        if overall == "PASS" and (not checks or any(item.get("status") != "PASS" or not item.get("evidence") for item in checks) or data.get("unresolved_items")):
            errors.append("submission report PASS requires evidence-bearing PASS checks and no unresolved items")
        if overall == "FAIL" and not any(item.get("status") == "FAIL" for item in checks):
            errors.append("submission report FAIL needs a failed check")
        if overall == "NOT_CHECKED" and any(item.get("status") == "FAIL" for item in checks):
            errors.append("NOT_CHECKED report cannot hide a failed check")
    elif artifact_type == "editorial_decision" and data.get("input_state") != "actual_received":
        errors.append("formal editorial intake requires an actual received decision; otherwise use strategy-only guidance")
    return errors


def artifact_file_errors(path: Path, artifact_id: str, artifact_type: str, unit_id: str, run_id: str, project_id: str) -> list[str]:
    errors: list[str] = []
    if not path.exists() or not path.is_file():
        return ["artifact file does not exist"]
    if path.stat().st_size == 0:
        return ["artifact file is empty"]
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in {"md", "json", "jsonl", "csv", "svg", "png", "pdf", "docx"}:
        errors.append(f"unsupported artifact format: {suffix or '<none>'}")
    if suffix == "md":
        frontmatter = parse_markdown_frontmatter(path)
        required = {"artifact_id", "project_id", "artifact_kind", "work_unit", "status", "language", "baseline_artifact", "source_registry", "run_id", "gate_status", "next_intents"}
        missing = sorted(required - set(frontmatter))
        if missing:
            errors.append(f"missing Markdown frontmatter fields: {', '.join(missing)}")
        expected = {"artifact_id": artifact_id, "project_id": project_id, "artifact_kind": artifact_type, "work_unit": unit_id, "run_id": run_id}
        for key, value in expected.items():
            if frontmatter.get(key) and frontmatter[key] != value:
                errors.append(f"frontmatter {key} does not match runtime contract")
        if frontmatter.get("gate_status") not in {"pending", "runtime-managed"}:
            errors.append("frontmatter gate_status may only be pending or runtime-managed; PASS/BLOCK verdicts belong to runtime state")
    elif suffix == "json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            errors.extend(structured_json_errors(data, artifact_type))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON artifact: {exc}")
    elif suffix == "jsonl":
        try:
            rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not rows:
                errors.append("JSONL artifact has no records")
            for line in rows:
                json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSONL artifact: {exc}")
    return errors


def structured_evidence_errors(state: dict[str, Any], root: Path, refs: list[str]) -> list[str]:
    errors: list[str] = []
    decisions = known_decision_ids(state)
    for ref in refs:
        if ref.startswith("artifact:"):
            artifact_id = ref.split(":", 1)[1]
            if artifact_id not in state.get("artifacts", {}):
                errors.append(f"unknown artifact evidence: {artifact_id}")
        elif ref.startswith("decision:"):
            decision_id = ref.split(":", 1)[1]
            if decision_id not in decisions:
                errors.append(f"unknown decision evidence: {decision_id}")
        elif ref.startswith("source:"):
            source_id = ref.split(":", 1)[1]
            source = state.get("sources", {}).get(source_id)
            if source is None:
                errors.append(f"unknown source evidence: {source_id}")
            elif source.get("record_check", {}).get("status") != "PASS":
                errors.append(f"source evidence is not verified PASS: {source_id}")
        elif ref.startswith("lookup:"):
            lookup_id = ref.split(":", 1)[1]
            lookup = state.get("lookups", {}).get(lookup_id)
            if lookup is None:
                errors.append(f"unknown lookup evidence: {lookup_id}")
            elif lookup.get("status") != "PASS":
                errors.append(f"lookup evidence is not PASS: {lookup_id}")
        elif ref.startswith("capability:"):
            capability = ref.split(":", 1)[1]
            status = state.get("capabilities", {}).get(capability, {}).get("status", "NOT_CHECKED")
            if status not in {"READY", "DEGRADED"}:
                errors.append(f"capability evidence is not executable: {capability}={status}")
        elif ref.startswith("file:"):
            evidence_path = Path(ref.split(":", 1)[1])
            evidence_path = evidence_path.resolve() if evidence_path.is_absolute() else (root / evidence_path).resolve()
            if evidence_path != root and root not in evidence_path.parents:
                errors.append(f"evidence file is outside project root: {evidence_path}")
            elif not evidence_path.exists() or not evidence_path.is_file():
                errors.append(f"evidence file does not exist: {evidence_path}")
        elif ref.startswith("check:") and ref.split(":", 1)[1].strip():
            continue
        else:
            errors.append(f"unstructured evidence reference: {ref}")
    return errors


def registered_artifact_integrity_errors(state: dict[str, Any], unit_id: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for artifact in state.get("artifacts", {}).values():
        if artifact.get("source_unit_id") != unit_id or artifact.get("status") not in {"candidate", "verified"}:
            continue
        path = Path(artifact.get("path", ""))
        if not path.exists() or not path.is_file():
            errors.append({"artifact_id": artifact.get("artifact_id", ""), "error": "file missing"})
            continue
        actual_hash = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        if actual_hash != artifact.get("content_hash"):
            errors.append({"artifact_id": artifact.get("artifact_id", ""), "error": "content hash changed"})
        for error in artifact_file_errors(path, artifact["artifact_id"], artifact["artifact_type"], unit_id, state.get("run_id", ""), state.get("project_id", "")):
            errors.append({"artifact_id": artifact.get("artifact_id", ""), "error": error})
    return errors


def intact_registered_artifact_types(state: dict[str, Any]) -> set[str]:
    bad_ids = {
        issue["artifact_id"]
        for unit_id in {item.get("source_unit_id", "") for item in state.get("artifacts", {}).values()}
        for issue in registered_artifact_integrity_errors(state, unit_id)
    }
    return {
        item.get("artifact_type", "")
        for artifact_id, item in state.get("artifacts", {}).items()
        if artifact_id not in bad_ids and item.get("status") in {"candidate", "verified"}
    }


def validate_state(args: argparse.Namespace) -> int:
    path, state = load_state(args.project_root)
    registry, units = load_registry()
    required = {"schema_version", "project_id", "project_title", "project_root", "run_id", "status", "mode", "state_version", "current_unit_id", "project_profile", "entry", "scope", "baseline", "units", "artifacts", "sources", "lookups", "capabilities", "venue", "gates", "handoffs", "review_protocol", "uncertainties", "human_checkpoints", "pause_records", "decisions", "blockers", "policy"}
    missing = sorted(required - set(state))
    errors: list[str] = []
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if state.get("status") not in STATUSES:
        errors.append(f"invalid status: {state.get('status')}")
    if state.get("mode") not in MODES:
        errors.append(f"invalid mode: {state.get('mode')}")
    if state.get("policy", {}).get("allow_auto_scientific_rewrite") is not False:
        errors.append("allow_auto_scientific_rewrite must be false")
    if state.get("venue", {}).get("status") not in {"not_selected", "candidate", "confirmed"}:
        errors.append("invalid venue status")
    if state.get("venue", {}).get("status") == "confirmed" and state.get("venue", {}).get("decision_id") not in known_decision_ids(state):
        errors.append("confirmed venue lacks a registered decision")
    gate_fields = {"gate_id", "unit_id", "kind", "verdict", "blocking", "advisory", "checks", "evidence", "human_decision_id", "created_at", "run_id"}
    artifact_fields = {"artifact_id", "artifact_type", "title", "path", "format", "source_unit_id", "version", "status", "created_at", "content_hash", "schema_version", "input_artifact_ids", "source_refs", "gate_ids", "human_review", "supersedes"}
    handoff_fields = {"handoff_id", "from_unit", "to_units", "status", "artifact_ids", "gate_ids", "open_questions", "human_decisions", "created_at", "run_id"}
    for gate_id, gate in state.get("gates", {}).items():
        missing_gate = sorted(gate_fields - set(gate))
        if missing_gate:
            errors.append(f"gate {gate_id} missing fields: {', '.join(missing_gate)}")
        if gate.get("run_id") != state.get("run_id"):
            errors.append(f"gate {gate_id} is not bound to the current run")
        if gate.get("unit_id") not in units:
            errors.append(f"gate {gate_id} references an unknown unit")
        if gate.get("kind") == "human" and not gate.get("advisory") and gate.get("verdict") in {"PASS", "PASS_WITH_CONDITIONS"} and gate.get("human_decision_id") not in known_decision_ids(state):
            errors.append(f"human gate {gate_id} lacks a registered decision")
    for artifact_id, artifact in state.get("artifacts", {}).items():
        missing_artifact = sorted(artifact_fields - set(artifact))
        if missing_artifact:
            errors.append(f"artifact {artifact_id} missing fields: {', '.join(missing_artifact)}")
        if artifact.get("schema_version") != registry.get("schema_version"):
            errors.append(f"artifact {artifact_id} is not bound to the current contract version")
    for source_id, source in state.get("sources", {}).items():
        if source.get("source_id") != source_id:
            errors.append(f"source key/id mismatch: {source_id}")
        trace_ref = source.get("provenance", {}).get("trace_ref")
        if trace_ref and trace_ref.startswith("file:") and "#sha256:" in trace_ref:
            raw_path, expected_hash = trace_ref[5:].rsplit("#", 1)
            path = Path(raw_path)
            if not path.exists() or not path.is_file():
                errors.append(f"source {source_id} trace file is missing")
            elif f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}" != expected_hash:
                errors.append(f"source {source_id} trace file hash changed")
    for lookup_id, lookup in state.get("lookups", {}).items():
        if lookup.get("lookup_id") != lookup_id:
            errors.append(f"lookup key/id mismatch: {lookup_id}")
        if lookup.get("status") == "PASS" and (not lookup.get("source_ids") or not lookup.get("trace_refs")):
            errors.append(f"PASS lookup {lookup_id} lacks sources or traces")
        for source_id in lookup.get("source_ids", []):
            if source_id not in state.get("sources", {}):
                errors.append(f"lookup {lookup_id} references unknown source {source_id}")
    for capability_id, capability in state.get("capabilities", {}).items():
        if capability.get("status") not in {"READY", "DEGRADED", "BLOCKED"}:
            errors.append(f"capability {capability_id} has invalid status")
        if capability.get("category") in {"consensus", "scite"} and (capability.get("required") or not capability.get("enhancement_only")):
            errors.append(f"capability {capability_id} must remain optional enhancement-only")
    for handoff_id, handoff in state.get("handoffs", {}).items():
        missing_handoff = sorted(handoff_fields - set(handoff))
        if missing_handoff:
            errors.append(f"handoff {handoff_id} missing fields: {', '.join(missing_handoff)}")
        if handoff.get("run_id") != state.get("run_id"):
            errors.append(f"handoff {handoff_id} is not bound to the current run")
    for unit_id in {item.get("source_unit_id", "") for item in state.get("artifacts", {}).values()}:
        for issue in registered_artifact_integrity_errors(state, unit_id):
            errors.append(f"artifact {issue['artifact_id']}: {issue['error']}")
    result = {"status": "PASS" if not errors else "BLOCK", "state": str(path), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def suggest_name(args: argparse.Namespace) -> int:
    kind = slugify(args.kind, fallback="artifact")
    subject = slugify(args.subject, fallback="subject")
    variant = slugify(args.variant, fallback="default")
    status = slugify(args.status, fallback="candidate")
    version = args.version if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", args.version) else "v0.1.0"
    artifact_id = f"{kind}__{subject}__{variant}__{status}__{version}"
    payload = {"artifact_id": artifact_id, "suggested_path": f"{args.directory.rstrip('/')}/{artifact_id}.{args.extension.lstrip('.')}", "reason": "semantic kind + subject + variant + status + semantic version"}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def record_event(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    _, _, events_path = state_paths(root)
    try:
        payload = json.loads(args.payload) if args.payload else {}
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "BLOCK", "error": f"payload must be valid JSON: {exc}"}, ensure_ascii=False))
        return 1
    event = append_event(events_path, args.event_type, payload)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def record_capability(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    enhancement_only = args.category in {"consensus", "scite"}
    required = bool(args.required and not enhancement_only)
    if args.status == "READY" and (not args.route or not args.evidence):
        print(json.dumps({"status": "BLOCK", "error": "READY capability requires --route and external/deterministic --evidence"}, ensure_ascii=False))
        return 2
    if args.status == "DEGRADED" and not args.limitation and not args.fallback:
        print(json.dumps({"status": "BLOCK", "error": "DEGRADED capability requires --limitation or --fallback"}, ensure_ascii=False))
        return 2
    if required and args.status == "BLOCKED" and not args.dependent_unit:
        print(json.dumps({"status": "BLOCK", "error": "required BLOCKED capability must name at least one --dependent-unit"}, ensure_ascii=False))
        return 2
    check_status = "PASS" if args.status == "READY" else ("FAIL" if args.status == "BLOCKED" else "NOT_CHECKED")
    checked_at = now_iso() if check_status != "NOT_CHECKED" else None
    record = {
        "capability_id": args.capability_id,
        "category": args.category,
        "required": required,
        "enhancement_only": enhancement_only,
        "status": args.status,
        "checked_at": checked_at,
        "checks": [{
            "check_id": f"{args.capability_id}-check",
            "operation": args.operation,
            "status": check_status,
            "observed_at": checked_at,
            "method": args.method if check_status != "NOT_CHECKED" else None,
            "evidence_refs": args.evidence,
            "reason": args.reason,
        }],
        "available_routes": args.available_route or ([args.route] if args.route else ["none"]),
        "selected_route": args.route,
        "fallback": ({"route": args.fallback, "validated": args.fallback_validated, "limitations": args.limitation} if args.fallback else None),
        "limitations": args.limitation,
        "dependent_unit_ids": args.dependent_unit,
    }
    state.setdefault("capabilities", {})[args.capability_id] = record
    save_state(state_path, state)
    event = append_event(events_path, "capability_recorded", {"capability_id": args.capability_id, "status": args.status, "category": args.category})
    print(json.dumps({"status": "RECORDED", "capability": record, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def capability_preflight(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2

    browser_path = next((shutil.which(name) for name in ("msedge", "chrome", "chromium", "firefox") if shutil.which(name)), None)
    pdf_ready = importlib.util.find_spec("pypdf") is not None or importlib.util.find_spec("pdfplumber") is not None or shutil.which("pdftotext") is not None
    docx_ready = importlib.util.find_spec("docx") is not None
    zotero_path = shutil.which("zotero")
    detected = {
        "browser": ("READY", "local_application", [f"file:{browser_path}"] if browser_path else [], "browser executable detected" if browser_path else "no browser executable detected on PATH"),
        "pdf": ("READY", "native_tool", ["check:python-module-or-pdftotext"] if pdf_ready else [], "PDF reader detected" if pdf_ready else "no PDF parser detected"),
        "docx": ("READY", "native_tool", ["check:python-docx-module"] if docx_ready else [], "DOCX parser detected" if docx_ready else "no DOCX parser detected"),
        "reference_manager": ("READY", "local_application", [f"file:{zotero_path}"] if zotero_path else [], "Zotero executable detected" if zotero_path else "reference-manager integration not detected"),
    }
    capabilities: list[dict[str, Any]] = []
    for category, (ready_status, route, evidence, reason) in detected.items():
        status = ready_status if evidence else "DEGRADED"
        checked_at = now_iso() if evidence else None
        capabilities.append({
            "capability_id": category,
            "category": category,
            "required": False,
            "enhancement_only": False,
            "status": status,
            "checked_at": checked_at,
            "checks": [{"check_id": f"{category}-probe", "operation": f"detect {category} support", "status": "PASS" if evidence else "NOT_CHECKED", "observed_at": checked_at, "method": "local deterministic probe" if evidence else None, "evidence_refs": evidence, "reason": reason}],
            "available_routes": [route] if evidence else ["user_assisted", "manual_equivalent"],
            "selected_route": route if evidence else "user_assisted",
            "fallback": None,
            "limitations": [] if evidence else [reason],
            "dependent_unit_ids": [],
        })
    for category in ("network", "academic_database", "consensus", "scite"):
        capabilities.append({
            "capability_id": category,
            "category": category,
            "required": False,
            "enhancement_only": category in {"consensus", "scite"},
            "status": "DEGRADED",
            "checked_at": None,
            "checks": [{"check_id": f"{category}-probe", "operation": f"verify {category} access and authentication", "status": "NOT_CHECKED", "observed_at": None, "method": None, "evidence_refs": [], "reason": "passive preflight does not perform network, login, or subscription actions"}],
            "available_routes": ["browser", "user_assisted", "manual_equivalent"],
            "selected_route": "user_assisted",
            "fallback": None,
            "limitations": ["availability and authentication remain NOT_CHECKED until an actual lookup is recorded"],
            "dependent_unit_ids": [],
        })
    report = {
        "report_id": "CAP-001",
        "run_id": state.get("run_id"),
        "generated_at": now_iso(),
        "environment": "passive local runtime preflight",
        "overall_status": "DEGRADED",
        "capabilities": capabilities,
        "blocking_reasons": [],
        "degraded_reasons": ["network, authentication, Consensus, and scite require an actual recorded lookup or user-assisted check"],
        "human_decision_id": None,
    }
    report_path = state_path.parent / "capability_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state["capabilities"] = {item["capability_id"]: item for item in capabilities}
    save_state(state_path, state)
    event = append_event(events_path, "capability_preflight_recorded", {"report_id": report["report_id"], "overall_status": report["overall_status"], "path": str(report_path)})
    print(json.dumps({"status": "RECORDED", "report": str(report_path), "overall_status": report["overall_status"], "capabilities": {item["capability_id"]: item["status"] for item in capabilities}, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def register_source(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    if not re.fullmatch(r"SRC-[0-9]{3,}", args.source_id):
        print(json.dumps({"status": "BLOCK", "error": "source id must match SRC-<three or more digits>"}, ensure_ascii=False))
        return 2
    if args.source_id in state.setdefault("sources", {}):
        print(json.dumps({"status": "CONFLICT", "error": f"source id already exists: {args.source_id}"}, ensure_ascii=False))
        return 2
    if args.lookup_id and args.lookup_id not in state.get("lookups", {}):
        print(json.dumps({"status": "BLOCK", "error": f"lookup id is not registered: {args.lookup_id}"}, ensure_ascii=False))
        return 2
    if args.capability_id and args.capability_id not in state.get("capabilities", {}):
        print(json.dumps({"status": "BLOCK", "error": f"capability id is not registered: {args.capability_id}"}, ensure_ascii=False))
        return 2
    snapshot_path, snapshot_hash, snapshot_error = project_file_record(root, args.snapshot)
    if snapshot_error:
        print(json.dumps({"status": "BLOCK", "error": f"source snapshot {snapshot_error}"}, ensure_ascii=False))
        return 2
    evidence_refs = list(args.evidence_ref)
    trace_ref = None
    if snapshot_path and snapshot_hash:
        trace_ref = f"file:{snapshot_path}#{snapshot_hash}"
        evidence_refs.append(trace_ref)
    if args.check_status == "PASS" and not evidence_refs:
        print(json.dumps({"status": "BLOCK", "error": "PASS source registration requires --snapshot or --evidence-ref"}, ensure_ascii=False))
        return 2
    if args.source_type in {"official_guidance", "submission_portal", "personal_communication"} and args.check_status == "PASS" and not trace_ref:
        print(json.dumps({"status": "BLOCK", "error": "official guidance, submission portals, and editor correspondence require a project-local snapshot"}, ensure_ascii=False))
        return 2
    prohibited_high_uses = {"scientific_claim", "numeric_claim", "field_synthesis", "journal_requirement", "submission_requirement"}
    if args.authority_level in {"C_DISCOVERY_ONLY", "U_UNVERIFIED"} and prohibited_high_uses.intersection(args.permitted_use):
        print(json.dumps({"status": "BLOCK", "error": "discovery-only or unverified sources cannot support claims or requirements"}, ensure_ascii=False))
        return 2
    accessed_at = args.accessed_at or now_iso()
    try:
        datetime.fromisoformat(accessed_at)
        if args.publication_date:
            date.fromisoformat(args.publication_date)
    except ValueError:
        print(json.dumps({"status": "BLOCK", "error": "accessed-at must be ISO date-time and publication-date must be ISO date"}, ensure_ascii=False))
        return 2
    freshness_checked = now_iso() if args.freshness_status == "PASS" else None
    record = {
        "source_id": args.source_id,
        "title": args.title,
        "source_type": args.source_type,
        "locator": {"kind": args.locator_kind, "value": args.locator, "anchor": args.anchor},
        "authority_level": args.authority_level,
        "review_status": args.review_status,
        "publication_date": args.publication_date,
        "accessed_at": accessed_at,
        "version_or_revision": args.version_or_revision,
        "freshness": {"class": args.freshness_class, "max_age_days": args.max_age_days, "checked_at": freshness_checked, "expires_at": None, "status": args.freshness_status, "reason": args.reason},
        "record_check": {"status": args.check_status, "checked_at": now_iso() if args.check_status == "PASS" else None, "method": args.method if args.check_status == "PASS" else None, "evidence_refs": evidence_refs, "reason": args.reason},
        "permitted_uses": args.permitted_use,
        "provenance": {"acquisition_method": args.acquisition_method, "lookup_id": args.lookup_id, "capability_id": args.capability_id, "observed_at": now_iso() if args.check_status == "PASS" else None, "trace_ref": trace_ref},
        "notes": args.note,
    }
    state["sources"][args.source_id] = record
    save_state(state_path, state)
    event = append_event(events_path, "source_registered", {"source_id": args.source_id, "source_type": args.source_type, "check_status": args.check_status})
    print(json.dumps({"status": "REGISTERED", "source": record, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def record_lookup(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    registry, units = load_registry()
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    if not re.fullmatch(r"LKP-[0-9]{3,}", args.lookup_id):
        print(json.dumps({"status": "BLOCK", "error": "lookup id must match LKP-<three or more digits>"}, ensure_ascii=False))
        return 2
    if args.lookup_id in state.setdefault("lookups", {}):
        print(json.dumps({"status": "CONFLICT", "error": f"lookup id already exists: {args.lookup_id}"}, ensure_ascii=False))
        return 2
    if args.unit_id not in units:
        print(json.dumps({"status": "BLOCK", "error": f"unknown work unit: {args.unit_id}"}, ensure_ascii=False))
        return 2
    if args.planned_capability_id not in state.get("capabilities", {}):
        print(json.dumps({"status": "BLOCK", "error": f"capability id is not registered: {args.planned_capability_id}"}, ensure_ascii=False))
        return 2
    unknown_sources = sorted(set(args.source_id) - set(state.get("sources", {})))
    if unknown_sources:
        print(json.dumps({"status": "BLOCK", "error": "lookup cites unregistered sources", "source_ids": unknown_sources}, ensure_ascii=False, indent=2))
        return 2
    trace_path, trace_hash, trace_error = project_file_record(root, args.trace_file)
    if trace_error:
        print(json.dumps({"status": "BLOCK", "error": f"lookup trace {trace_error}"}, ensure_ascii=False))
        return 2
    trace_refs = list(args.trace_ref)
    if trace_path and trace_hash:
        trace_refs.append(f"file:{trace_path}#{trace_hash}")
    if args.status == "PASS" and (not args.source_id or not trace_refs or args.actual_route == "not_executed"):
        print(json.dumps({"status": "BLOCK", "error": "PASS lookup requires registered --source-id, a trace, and an executed route"}, ensure_ascii=False))
        return 2
    if args.status == "NOT_CHECKED" and args.source_id:
        print(json.dumps({"status": "BLOCK", "error": "NOT_CHECKED lookup cannot claim source results"}, ensure_ascii=False))
        return 2
    record = {
        "lookup_id": args.lookup_id,
        "unit_id": args.unit_id,
        "question": args.question,
        "purpose": args.purpose,
        "obligation": {"required": args.required, "authority_floor": args.authority_floor, "freshness_required": args.freshness_required, "acceptance_rule": args.acceptance_rule},
        "planned_capability_id": args.planned_capability_id,
        "actual_route": args.actual_route,
        "query_or_action": args.query,
        "executed_at": now_iso() if args.status != "NOT_CHECKED" else None,
        "status": args.status,
        "source_ids": args.source_id,
        "trace_refs": trace_refs,
        "fallback": ({"used": True, "route": args.fallback, "limitations": args.limitation} if args.fallback else None),
        "reason": args.reason,
    }
    state["lookups"][args.lookup_id] = record
    for source_id in args.source_id:
        state["sources"][source_id]["provenance"]["lookup_id"] = args.lookup_id
        state["sources"][source_id]["provenance"]["capability_id"] = args.planned_capability_id
    save_state(state_path, state)
    event = append_event(events_path, "lookup_recorded", {"lookup_id": args.lookup_id, "unit_id": args.unit_id, "status": args.status, "route": args.actual_route})
    print(json.dumps({"status": "RECORDED", "lookup": record, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0 if args.status == "PASS" else 2


def set_journal_status(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    if args.status in {"candidate", "confirmed"} and not args.journal_name:
        print(json.dumps({"status": "BLOCK", "error": f"{args.status} journal status requires --journal-name"}, ensure_ascii=False))
        return 2
    if args.status == "confirmed" and (not args.decision_id or args.decision_id not in known_decision_ids(state)):
        print(json.dumps({"status": "BLOCK", "error": "confirmed journal status requires a registered --decision-id"}, ensure_ascii=False))
        return 2
    state["venue"] = {"status": args.status, "journal_name": args.journal_name if args.status != "not_selected" else None, "decision_id": args.decision_id, "set_by": args.actor, "updated_at": now_iso()}
    save_state(state_path, state)
    event = append_event(events_path, "journal_status_changed", state["venue"])
    print(json.dumps({"status": "RECORDED", "venue": state["venue"], "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def start_unit(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    if not state_path.exists():
        print(json.dumps({"status": "BLOCK", "error": f"project state not found: {state_path}"}, ensure_ascii=False))
        return 1
    registry, units = load_registry()
    if args.unit_id not in units:
        print(json.dumps({"status": "BLOCK", "error": f"unknown work unit: {args.unit_id}", "known_units": sorted(units)}, ensure_ascii=False, indent=2))
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    current = state.get("current_unit_id")
    if current == args.unit_id:
        print(json.dumps({"status": "CONFLICT", "error": "work unit is already active", "unit_id": args.unit_id, "unit_status": state.get("units", {}).get(args.unit_id, {}).get("status")}, ensure_ascii=False, indent=2))
        return 2
    if current:
        current_status = state.get("units", {}).get(current, {}).get("status")
        print(json.dumps({"status": "BLOCK", "error": f"active work unit must be completed or explicitly escalated first: {current}", "current_status": current_status}, ensure_ascii=False, indent=2))
        return 2
    if args.unit_id == "journal-fit" and state.get("venue", {}).get("status", "not_selected") == "not_selected":
        print(json.dumps({"status": "BLOCK", "error": "journal-fit is not applicable while venue status is not_selected", "next_action": "record a candidate/confirmed journal or skip directly to template-driven submission packaging"}, ensure_ascii=False, indent=2))
        return 2
    requirements = start_requirements_for_mode(registry, args.unit_id, state.get("mode", "pipeline"))
    available = intact_registered_artifact_types(state)
    missing_all = sorted(set(requirements.get("all", [])) - available)
    any_options = set(requirements.get("any", []))
    missing_any = sorted(any_options) if any_options and not (any_options & available) else []
    if missing_all or missing_any:
        print(json.dumps({"status": "BLOCK", "error": "work-unit start contract not satisfied", "unit_id": args.unit_id, "missing_all": missing_all, "requires_any_of": missing_any, "available_artifact_types": sorted(available)}, ensure_ascii=False, indent=2))
        return 2
    capability_errors = capability_requirement_errors(state, registry, args.unit_id, "start")
    source_errors = source_requirement_errors(state, registry, args.unit_id, "start")
    if capability_errors or source_errors:
        print(json.dumps({"status": "BLOCK", "error": "runtime preflight contract not satisfied", "unit_id": args.unit_id, "capability_errors": capability_errors, "source_errors": source_errors}, ensure_ascii=False, indent=2))
        return 2
    uncertainty_blockers = uncertainty_blockers_for_unit(registry, units[args.unit_id], state)
    if uncertainty_blockers:
        print(json.dumps({"status": "BLOCK", "error": "open uncertainty checkpoint blocks this unit", "blockers": uncertainty_blockers}, ensure_ascii=False, indent=2))
        return 2
    state["current_unit_id"] = args.unit_id
    state["status"] = "running"
    unit_state = state.setdefault("units", {}).setdefault(args.unit_id, {})
    unit_state.update({"status": "in_progress", "started_at": now_iso(), "contract_version": registry.get("schema_version"), "project_profile": state.get("project_profile"), "iteration": int(unit_state.get("iteration", 0)) + 1, "artifact_ids": [], "gate_ids": []})
    save_state(state_path, state)
    event = append_event(events_path, "work_unit_selected", {"unit_id": args.unit_id, "state_version": state["state_version"]})
    print(json.dumps({"status": "STARTED", "unit_id": args.unit_id, "project_profile": state.get("project_profile"), "write_root": registry.get("unit_write_roots", {}).get(args.unit_id), "required_outputs": registry.get("completion_outputs", {}).get(args.unit_id, {}), "required_gates": units[args.unit_id].get("required_gates", []), "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def register_artifact(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    registry, units = load_registry()
    if args.unit_id not in units:
        print(json.dumps({"status": "BLOCK", "error": f"unknown work unit: {args.unit_id}"}, ensure_ascii=False))
        return 1
    error = mutation_error(state) or active_unit_error(state, args.unit_id, registry, {"in_progress", "awaiting_gate", "blocked"})
    if error:
        print(json.dumps({"status": "BLOCK", "error": error, "unit_id": args.unit_id}, ensure_ascii=False, indent=2))
        return 2
    if args.artifact_type not in set(units[args.unit_id].get("outputs", [])):
        print(json.dumps({"status": "BLOCK", "error": "artifact type is outside the unit contract", "artifact_type": args.artifact_type, "allowed": units[args.unit_id].get("outputs", [])}, ensure_ascii=False, indent=2))
        return 2
    artifact_path = Path(args.path)
    artifact_path = artifact_path.resolve() if artifact_path.is_absolute() else (root / artifact_path).resolve()
    allowed_root_name = registry.get("unit_write_roots", {}).get(args.unit_id)
    allowed_root = (root / allowed_root_name).resolve() if allowed_root_name else root
    if artifact_path != allowed_root and allowed_root not in artifact_path.parents:
        print(json.dumps({"status": "BLOCK", "error": "artifact path is outside the unit write scope", "allowed_root": str(allowed_root), "path": str(artifact_path)}, ensure_ascii=False, indent=2))
        return 2
    if not artifact_path.exists() or not artifact_path.is_file():
        print(json.dumps({"status": "BLOCK", "error": "artifact file does not exist", "path": str(artifact_path)}, ensure_ascii=False))
        return 2
    if args.artifact_type in STRUCTURED_JSON_REQUIRED_FIELDS and artifact_path.suffix.lower() != ".json":
        print(json.dumps({"status": "BLOCK", "error": f"{args.artifact_type} must be registered as schema-bearing JSON"}, ensure_ascii=False))
        return 2
    artifact_id = args.artifact_id
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:__[a-z0-9]+(?:-[a-z0-9]+)*)+__v[0-9]+\.[0-9]+\.[0-9]+", artifact_id):
        print(json.dumps({"status": "BLOCK", "error": "artifact id does not follow the semantic versioned naming contract", "artifact_id": artifact_id}, ensure_ascii=False, indent=2))
        return 2
    if artifact_id in state.setdefault("artifacts", {}):
        print(json.dumps({"status": "CONFLICT", "error": f"artifact id already exists: {artifact_id}"}, ensure_ascii=False))
        return 2
    unknown_inputs = sorted(set(args.input_artifact_id) - set(state.get("artifacts", {})))
    if unknown_inputs:
        print(json.dumps({"status": "BLOCK", "error": "input artifact ids are not registered", "artifact_ids": unknown_inputs}, ensure_ascii=False, indent=2))
        return 2
    if args.supersedes and args.supersedes not in state.get("artifacts", {}):
        print(json.dumps({"status": "BLOCK", "error": f"superseded artifact is not registered: {args.supersedes}"}, ensure_ascii=False))
        return 2
    file_errors = artifact_file_errors(artifact_path, artifact_id, args.artifact_type, args.unit_id, state.get("run_id", ""), state.get("project_id", ""))
    if not file_errors and args.artifact_type in {"journal_profile", "package_plan"}:
        structured = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact_venue_status = structured.get("status") if args.artifact_type == "journal_profile" else structured.get("journal_context", {}).get("status")
        if artifact_venue_status != state.get("venue", {}).get("status", "not_selected"):
            file_errors.append("artifact journal status does not match runtime venue state")
        if args.artifact_type == "package_plan" and structured.get("project_id") != state.get("project_id"):
            file_errors.append("package plan project_id does not match runtime project")
    if file_errors:
        print(json.dumps({"status": "BLOCK", "error": "artifact content does not satisfy the structural contract", "details": file_errors}, ensure_ascii=False, indent=2))
        return 2
    artifact_format = artifact_path.suffix.lower().lstrip(".")
    version = 1 + sum(1 for item in state.get("artifacts", {}).values() if item.get("artifact_type") == args.artifact_type)
    record = {
        "artifact_id": artifact_id,
        "artifact_type": args.artifact_type,
        "title": args.title or artifact_id,
        "path": str(artifact_path),
        "format": artifact_format,
        "source_unit_id": args.unit_id,
        "version": version,
        "status": args.status,
        "created_at": now_iso(),
        "content_hash": f"sha256:{hashlib.sha256(artifact_path.read_bytes()).hexdigest()}",
        "schema_version": registry.get("schema_version", ""),
        "input_artifact_ids": args.input_artifact_id,
        "source_refs": args.source_ref,
        "gate_ids": list(state["units"][args.unit_id].get("gate_ids", [])),
        "human_review": {"status": "not_requested", "reviewer": None, "decision_id": None},
        "supersedes": args.supersedes,
        "language": args.language,
        "language_stage": args.language_stage,
    }
    state["artifacts"][artifact_id] = record
    state["units"][args.unit_id].setdefault("artifact_ids", []).append(artifact_id)
    save_state(state_path, state)
    event = append_event(events_path, "artifact_registered", {"unit_id": args.unit_id, "artifact_id": artifact_id, "artifact_type": args.artifact_type})
    print(json.dumps({"status": "REGISTERED", "artifact": record, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def record_decision(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    if args.decision_id in known_decision_ids(state):
        print(json.dumps({"status": "CONFLICT", "error": f"decision id already exists: {args.decision_id}"}, ensure_ascii=False))
        return 2
    if args.checkpoint_id and args.checkpoint_id not in state.get("human_checkpoints", {}):
        print(json.dumps({"status": "BLOCK", "error": f"human checkpoint not found: {args.checkpoint_id}"}, ensure_ascii=False))
        return 2
    decision = {
        "decision_id": args.decision_id,
        "kind": args.kind,
        "question": args.question,
        "answer": args.answer,
        "actor": args.actor,
        "evidence": args.evidence,
        "checkpoint_id": args.checkpoint_id,
        "created_at": now_iso(),
        "run_id": state.get("run_id"),
    }
    state.setdefault("decisions", []).append(decision)
    save_state(state_path, state)
    event = append_event(events_path, "decision_recorded", decision)
    print(json.dumps({"status": "RECORDED", "decision": decision, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def record_gate(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    registry, units = load_registry()
    if args.unit_id not in units:
        print(json.dumps({"status": "BLOCK", "error": f"unknown work unit: {args.unit_id}"}, ensure_ascii=False))
        return 1
    error = mutation_error(state) or active_unit_error(state, args.unit_id, registry, {"in_progress", "awaiting_gate", "blocked"})
    if error:
        print(json.dumps({"status": "BLOCK", "error": error, "unit_id": args.unit_id}, ensure_ascii=False, indent=2))
        return 2
    required = set(units[args.unit_id].get("required_gates", []))
    if args.kind not in required and not args.advisory:
        print(json.dumps({"status": "BLOCK", "error": "gate kind is outside the unit contract", "kind": args.kind, "required_gates": sorted(required)}, ensure_ascii=False, indent=2))
        return 2
    definition = registry.get("gate_definitions", {}).get(args.kind, {})
    decision_required = definition.get("require_decision_id") or (args.verdict == "PASS_WITH_CONDITIONS" and registry.get("contract_defaults", {}).get("condition_verdict_requires_decision"))
    if decision_required and not args.decision_id:
        print(json.dumps({"status": "BLOCK", "error": f"{args.kind} {args.verdict} requires --decision-id"}, ensure_ascii=False))
        return 2
    if args.decision_id and args.decision_id not in known_decision_ids(state):
        print(json.dumps({"status": "BLOCK", "error": f"decision id is not registered: {args.decision_id}"}, ensure_ascii=False))
        return 2
    if definition.get("require_decision_id") and f"decision:{args.decision_id}" not in args.evidence:
        print(json.dumps({"status": "BLOCK", "error": "human gate evidence must cite its registered decision as decision:<id>"}, ensure_ascii=False))
        return 2
    if not args.advisory and definition.get("require_evidence_refs") and not args.evidence:
        print(json.dumps({"status": "BLOCK", "error": "required gate must cite structured evidence"}, ensure_ascii=False))
        return 2
    evidence_errors = structured_evidence_errors(state, root, args.evidence)
    if evidence_errors:
        print(json.dumps({"status": "BLOCK", "error": "gate evidence is invalid", "details": evidence_errors}, ensure_ascii=False, indent=2))
        return 2
    if not args.advisory and registry.get("contract_defaults", {}).get("required_gate_evidence_must_include_non_self_asserted_ref"):
        trusted_prefixes = ("artifact:", "decision:", "source:", "lookup:", "file:")
        if not any(item.startswith(trusted_prefixes) for item in args.evidence):
            print(json.dumps({"status": "BLOCK", "error": "required gate cannot pass from check:* self-assertions alone"}, ensure_ascii=False))
            return 2
    if not args.advisory and definition.get("bind_current_artifact_hash"):
        current_artifacts = set(state["units"][args.unit_id].get("artifact_ids", []))
        cited_artifacts = {item.split(":", 1)[1] for item in args.evidence if item.startswith("artifact:")}
        if not current_artifacts.intersection(cited_artifacts):
            print(json.dumps({"status": "BLOCK", "error": "gate must cite a current-unit artifact so the verdict is bound to its hash", "current_artifact_ids": sorted(current_artifacts)}, ensure_ascii=False, indent=2))
            return 2
    existing = [gate for gate in state.setdefault("gates", {}).values() if gate.get("unit_id") == args.unit_id and gate.get("kind") == args.kind]
    gate_id = f"gate--{args.unit_id}--{args.kind}--v{len(existing)+1:03d}"
    gate = {"gate_id": gate_id, "unit_id": args.unit_id, "kind": args.kind, "verdict": args.verdict, "blocking": args.verdict in {"BLOCK", "UNKNOWN", "NOT_CHECKED"} and not args.advisory, "advisory": args.advisory, "checks": [{"check_id": item} for item in args.check], "evidence": args.evidence, "human_decision_id": args.decision_id, "created_at": now_iso(), "run_id": state.get("run_id")}
    state["gates"][gate_id] = gate
    unit_state = state["units"][args.unit_id]
    unit_state.setdefault("gate_ids", []).append(gate_id)
    if not args.advisory:
        unit_state["status"] = "blocked" if gate["blocking"] else "awaiting_gate"
    if gate["blocking"]:
        state.setdefault("blockers", []).append({"blocker_id": gate_id, "kind": "gate", "gate_kind": args.kind, "source_gate_id": gate_id, "unit_id": args.unit_id, "status": "open", "message": f"{args.kind} gate: {args.verdict}", "created_at": gate["created_at"]})
    elif not args.advisory:
        for blocker in state.setdefault("blockers", []):
            if blocker.get("kind") == "gate" and blocker.get("unit_id") == args.unit_id and blocker.get("gate_kind") == args.kind and blocker.get("status") == "open":
                blocker["status"] = "resolved"
                blocker["resolved_at"] = gate["created_at"]
                blocker["resolution_gate_id"] = gate_id
    save_state(state_path, state)
    event = append_event(events_path, "gate_recorded", gate)
    print(json.dumps({"status": "RECORDED", "gate": gate, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0 if not gate["blocking"] else 2


def complete_unit(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    registry, units = load_registry()
    unit = units.get(args.unit_id)
    if not unit:
        print(json.dumps({"status": "BLOCK", "error": f"unknown work unit: {args.unit_id}"}, ensure_ascii=False))
        return 1
    unit_state = state.get("units", {}).get(args.unit_id, {})
    error = mutation_error(state) or active_unit_error(state, args.unit_id, registry, {"in_progress", "awaiting_gate"})
    if error:
        print(json.dumps({"status": "BLOCK", "error": error, "unit_status": unit_state.get("status")}, ensure_ascii=False, indent=2))
        return 2
    current_artifact_ids = set(unit_state.get("artifact_ids", []))
    current_gate_ids = set(unit_state.get("gate_ids", []))
    produced = registered_artifact_types(state, args.unit_id, current_artifact_ids)
    output_contract = registry.get("completion_outputs", {}).get(args.unit_id, {})
    missing_all = sorted(set(output_contract.get("all", [])) - produced)
    any_options = set(output_contract.get("any", []))
    missing_any = sorted(any_options) if any_options and not (any_options & produced) else []
    venue_status = state.get("venue", {}).get("status", "not_selected")
    if args.unit_id == "journal-fit":
        if venue_status == "confirmed":
            missing_all.extend(sorted({"journal_profile", "author_guideline_snapshot"} - produced))
        elif venue_status == "candidate" and "journal_exploration_report" not in produced:
            missing_all.append("journal_exploration_report")
    missing_all = sorted(set(missing_all))
    gate_failures = []
    for kind in unit.get("required_gates", []):
        gate = latest_gate(state, args.unit_id, kind, current_gate_ids)
        accepted = set(registry.get("gate_definitions", {}).get(kind, {}).get("accepted_verdicts", registry.get("contract_defaults", {}).get("accepted_completion_verdicts", ["PASS"])))
        if gate is None or gate.get("verdict") not in accepted or (gate.get("verdict") == "PASS_WITH_CONDITIONS" and not gate.get("human_decision_id")):
            gate_failures.append({"kind": kind, "latest": gate})
    uncertainty_blockers = uncertainty_blockers_for_unit(registry, unit, state)
    if uncertainty_blockers:
        gate_failures.append({"kind": "uncertainty", "open_blockers": uncertainty_blockers})
    capability_errors = capability_requirement_errors(state, registry, args.unit_id, "complete")
    source_errors = source_requirement_errors(state, registry, args.unit_id, "complete")
    if args.unit_id == "submission-package":
        records_by_type = {
            item.get("artifact_type"): item
            for key, item in state.get("artifacts", {}).items()
            if key in current_artifact_ids and item.get("source_unit_id") == args.unit_id and item.get("status") in {"candidate", "verified"}
        }
        plan_record = records_by_type.get("package_plan")
        report_record = records_by_type.get("submission_check_report")
        if plan_record:
            plan = json.loads(Path(plan_record["path"]).read_text(encoding="utf-8"))
            if plan.get("status") not in {"user_confirmed", "assembled", "checked"} or not plan.get("user_control", {}).get("shape_confirmed"):
                source_errors.append("submission package plan is not yet user-confirmed")
        if report_record:
            report = json.loads(Path(report_record["path"]).read_text(encoding="utf-8"))
            if report.get("overall_status") != "PASS":
                source_errors.append(f"submission package checks are {report.get('overall_status', 'NOT_CHECKED')}, not PASS")
    integrity_errors = registered_artifact_integrity_errors(state, args.unit_id) if registry.get("contract_defaults", {}).get("reject_changed_or_missing_artifacts") else []
    if missing_all or missing_any or gate_failures or integrity_errors or capability_errors or source_errors:
        unit_state["status"] = "awaiting_gate"
        save_state(state_path, state)
        print(json.dumps({"status": "BLOCK", "error": "completion contract not satisfied", "missing_all_outputs": missing_all, "requires_any_output": missing_any, "gate_failures": gate_failures, "capability_errors": capability_errors, "source_errors": source_errors, "artifact_integrity_errors": integrity_errors, "produced_artifact_types": sorted(produced), "state_version": state["state_version"]}, ensure_ascii=False, indent=2))
        return 2
    unit_state.update({"status": "completed", "completed_at": now_iso()})
    if state.get("current_unit_id") == args.unit_id:
        state["current_unit_id"] = None
    save_state(state_path, state)
    event = append_event(events_path, "work_unit_completed", {"unit_id": args.unit_id, "state_version": state["state_version"]})
    print(json.dumps({"status": "COMPLETED", "unit_id": args.unit_id, "next_candidates": unit.get("next_candidates", []), "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def create_handoff(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    state_path, _, events_path = state_paths(root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    conflict = check_expected_version(state, args.expected_version)
    if conflict:
        print(json.dumps(conflict, ensure_ascii=False, indent=2))
        return 2
    registry, units = load_registry()
    source = units.get(args.from_unit)
    if not source or args.to_unit not in units:
        print(json.dumps({"status": "BLOCK", "error": "unknown handoff unit"}, ensure_ascii=False))
        return 1
    error = mutation_error(state)
    if error:
        print(json.dumps({"status": "BLOCK", "error": error}, ensure_ascii=False, indent=2))
        return 2
    source_status = state.get("units", {}).get(args.from_unit, {}).get("status")
    if args.escalation:
        if state.get("current_unit_id") != args.from_unit or source_status != "blocked":
            print(json.dumps({"status": "BLOCK", "error": "escalation handoff requires the blocked active unit", "from_unit": args.from_unit, "source_status": source_status}, ensure_ascii=False, indent=2))
            return 2
        blocking_kinds = {
            blocker.get("gate_kind")
            for blocker in state.get("blockers", [])
            if blocker.get("kind") == "gate" and blocker.get("unit_id") == args.from_unit and blocker.get("status") == "open"
        }
        allowed_targets = sorted({target for kind in blocking_kinds for target in registry.get("block_transitions", {}).get(kind, [])})
    else:
        if source_status != "completed":
            print(json.dumps({"status": "BLOCK", "error": "source unit must be completed before standard handoff", "from_unit": args.from_unit, "source_status": source_status}, ensure_ascii=False, indent=2))
            return 2
        allowed_targets = source.get("next_candidates", [])
    if args.to_unit not in allowed_targets:
        print(json.dumps({"status": "BLOCK", "error": "handoff target is outside the contract", "allowed": allowed_targets}, ensure_ascii=False, indent=2))
        return 2
    unknown_decisions = sorted(set(args.decision_id) - known_decision_ids(state))
    if unknown_decisions:
        print(json.dumps({"status": "BLOCK", "error": "handoff cites unregistered decisions", "decision_ids": unknown_decisions}, ensure_ascii=False, indent=2))
        return 2
    requirements = start_requirements_for_mode(registry, args.to_unit, state.get("mode", "pipeline"))
    available = intact_registered_artifact_types(state)
    missing_all = sorted(set(requirements.get("all", [])) - available)
    any_options = set(requirements.get("any", []))
    missing_any = sorted(any_options) if any_options and not (any_options & available) else []
    if missing_all or missing_any:
        print(json.dumps({"status": "BLOCK", "error": "handoff target prerequisites are not satisfied", "to_unit": args.to_unit, "missing_all": missing_all, "requires_any_of": missing_any}, ensure_ascii=False, indent=2))
        return 2
    integrity_errors = registered_artifact_integrity_errors(state, args.from_unit)
    if integrity_errors:
        print(json.dumps({"status": "BLOCK", "error": "source artifacts changed after registration", "artifact_integrity_errors": integrity_errors}, ensure_ascii=False, indent=2))
        return 2
    handoff_id = f"hf--{args.from_unit}--{args.to_unit}--{len(state.setdefault('handoffs', {}))+1:03d}"
    handoff_status = "escalation" if args.escalation else "prepared"
    handoff = {"handoff_id": handoff_id, "from_unit": args.from_unit, "to_units": [args.to_unit], "status": handoff_status, "artifact_ids": state.get("units", {}).get(args.from_unit, {}).get("artifact_ids", []), "gate_ids": state.get("units", {}).get(args.from_unit, {}).get("gate_ids", []), "open_questions": args.open_question, "human_decisions": args.decision_id, "created_at": now_iso(), "run_id": state.get("run_id")}
    state["handoffs"][handoff_id] = handoff
    if args.escalation:
        state["units"][args.from_unit]["status"] = "escalated"
        state["current_unit_id"] = None
    save_state(state_path, state)
    event = append_event(events_path, "handoff_prepared", handoff)
    print(json.dumps({"status": "PREPARED", "handoff": handoff, "state_version": state["state_version"], "event_id": event["event_id"]}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SCI Review System runtime helper")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="initialize a project without overwriting files")
    init.add_argument("project_root")
    init.add_argument("--project-id", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--intent", required=True)
    init.add_argument("--mode", choices=sorted(MODES), default="pipeline")
    init.add_argument("--profile", default="auto", help="project profile id, auto, or none")
    init.add_argument("--allow-root-project", action="store_true", help="explicitly allow initialization at the repository root")
    init.set_defaults(func=init_project)
    inspect = sub.add_parser("inspect", help="print current project state")
    inspect.add_argument("project_root")
    inspect.set_defaults(func=lambda args: (print(json.dumps(load_state(args.project_root)[1], ensure_ascii=False, indent=2)) or 0))
    validate = sub.add_parser("validate-state", help="validate minimum state invariants")
    validate.add_argument("project_root")
    validate.set_defaults(func=validate_state)
    name = sub.add_parser("suggest-name", help="suggest a stable artifact id and path")
    name.add_argument("--kind", required=True)
    name.add_argument("--subject", required=True)
    name.add_argument("--variant", default="default")
    name.add_argument("--status", default="candidate")
    name.add_argument("--version", default="v0.1.0")
    name.add_argument("--directory", default="drafts")
    name.add_argument("--extension", default="md")
    name.set_defaults(func=suggest_name)
    event = sub.add_parser("event", help="append a hash-linked event")
    event.add_argument("project_root")
    event.add_argument("event_type")
    event.add_argument("--payload", default="{}")
    event.set_defaults(func=record_event)
    preflight = sub.add_parser("capability-preflight", help="record a passive, fail-honest execution capability preflight")
    preflight.add_argument("project_root")
    preflight.set_defaults(func=capability_preflight)
    capability = sub.add_parser("record-capability", help="record a checked capability or an explicit degraded/blocked state")
    capability.add_argument("project_root")
    capability.add_argument("capability_id")
    capability.add_argument("--category", required=True, choices=["network", "browser", "academic_database", "pdf", "docx", "reference_manager", "consensus", "scite", "other"])
    capability.add_argument("--status", required=True, choices=["READY", "DEGRADED", "BLOCKED"])
    capability.add_argument("--operation", default="verify capability")
    capability.add_argument("--method", default="runtime/user-assisted check")
    capability.add_argument("--reason", required=True)
    capability.add_argument("--required", action="store_true")
    capability.add_argument("--route", choices=["native_tool", "browser", "api", "local_application", "command_line", "user_assisted", "manual_equivalent", "none", "other"])
    capability.add_argument("--available-route", action="append", default=[], choices=["native_tool", "browser", "api", "local_application", "command_line", "user_assisted", "manual_equivalent", "none", "other"])
    capability.add_argument("--evidence", action="append", default=[])
    capability.add_argument("--fallback")
    capability.add_argument("--fallback-validated", action="store_true")
    capability.add_argument("--limitation", action="append", default=[])
    capability.add_argument("--dependent-unit", action="append", default=[])
    capability.add_argument("--expected-version", type=int, default=None)
    capability.set_defaults(func=record_capability)
    source = sub.add_parser("register-source", help="register a provenance-bearing external source record")
    source.add_argument("project_root")
    source.add_argument("source_id")
    source.add_argument("--title", required=True)
    source.add_argument("--source-type", required=True, choices=["journal_article", "preprint", "dataset", "standard", "official_guidance", "submission_portal", "registry_record", "bibliographic_record", "search_result", "citation_context", "book_or_handbook", "user_file", "personal_communication", "other"])
    source.add_argument("--locator-kind", required=True, choices=["url", "doi", "database_id", "api_endpoint", "local_path", "bibliographic_citation", "communication_id", "other"])
    source.add_argument("--locator", required=True)
    source.add_argument("--anchor")
    source.add_argument("--authority-level", required=True, choices=["A_OFFICIAL_PRIMARY", "A_SCHOLARLY_PRIMARY", "B_SCHOLARLY_SYNTHESIS", "B_TRUSTED_METADATA", "C_DISCOVERY_ONLY", "U_UNVERIFIED"])
    source.add_argument("--review-status", required=True, choices=["official", "peer_reviewed", "editorially_reviewed", "preprint", "not_applicable", "unknown"])
    source.add_argument("--publication-date")
    source.add_argument("--accessed-at")
    source.add_argument("--version-or-revision")
    source.add_argument("--freshness-class", required=True, choices=["volatile", "current", "stable", "historical"])
    source.add_argument("--max-age-days", type=int, default=180)
    source.add_argument("--freshness-status", required=True, choices=["PASS", "FAIL", "NOT_CHECKED"])
    source.add_argument("--check-status", required=True, choices=["PASS", "FAIL", "NOT_CHECKED"])
    source.add_argument("--method", default="source snapshot and metadata verification")
    source.add_argument("--permitted-use", action="append", required=True, choices=["discovery", "bibliographic_metadata", "scientific_claim", "numeric_claim", "field_synthesis", "journal_requirement", "submission_requirement", "citation_context", "provenance_only"])
    source.add_argument("--acquisition-method", required=True, choices=["browser", "api", "academic_database", "pdf_reader", "reference_manager", "user_assisted", "local_file", "personal_communication", "other"])
    source.add_argument("--snapshot")
    source.add_argument("--evidence-ref", action="append", default=[])
    source.add_argument("--lookup-id")
    source.add_argument("--capability-id")
    source.add_argument("--reason", required=True)
    source.add_argument("--note", action="append", default=[])
    source.add_argument("--expected-version", type=int, default=None)
    source.set_defaults(func=register_source)
    lookup = sub.add_parser("record-lookup", help="record an actually executed or explicitly unexecuted external lookup")
    lookup.add_argument("project_root")
    lookup.add_argument("lookup_id")
    lookup.add_argument("--unit-id", required=True)
    lookup.add_argument("--question", required=True)
    lookup.add_argument("--purpose", required=True, choices=["scientific_claim", "numeric_claim", "field_synthesis", "bibliographic_verification", "journal_requirement", "submission_requirement", "citation_context", "capability_probe", "other"])
    lookup.add_argument("--required", action="store_true")
    lookup.add_argument("--authority-floor", required=True, choices=["A_OFFICIAL_PRIMARY", "A_SCHOLARLY_PRIMARY", "B_SCHOLARLY_SYNTHESIS", "B_TRUSTED_METADATA", "C_DISCOVERY_ONLY", "U_UNVERIFIED"])
    lookup.add_argument("--freshness-required", action="store_true")
    lookup.add_argument("--acceptance-rule", required=True)
    lookup.add_argument("--planned-capability-id", required=True)
    lookup.add_argument("--actual-route", required=True, choices=["browser", "api", "academic_database", "pdf_reader", "reference_manager", "consensus_browser", "consensus_api", "scite_browser", "scite_api", "user_assisted", "manual_local", "not_executed", "other"])
    lookup.add_argument("--query")
    lookup.add_argument("--status", required=True, choices=["PASS", "FAIL", "NOT_CHECKED"])
    lookup.add_argument("--source-id", action="append", default=[])
    lookup.add_argument("--trace-file")
    lookup.add_argument("--trace-ref", action="append", default=[])
    lookup.add_argument("--fallback")
    lookup.add_argument("--limitation", action="append", default=[])
    lookup.add_argument("--reason", required=True)
    lookup.add_argument("--expected-version", type=int, default=None)
    lookup.set_defaults(func=record_lookup)
    journal = sub.add_parser("set-journal-status", help="record not-selected, candidate, or human-confirmed journal state")
    journal.add_argument("project_root")
    journal.add_argument("status", choices=["not_selected", "candidate", "confirmed"])
    journal.add_argument("--journal-name")
    journal.add_argument("--decision-id")
    journal.add_argument("--actor", choices=["user", "advisor", "coauthor"], default="user")
    journal.set_defaults(func=set_journal_status)
    route = sub.add_parser("route", help="start a semantic work unit after contract checks")
    route.add_argument("project_root")
    route.add_argument("unit_id")
    route.add_argument("--expected-version", type=int, default=None)
    route.set_defaults(func=start_unit)
    start = sub.add_parser("start-unit", help="start a work unit after checking prerequisites and uncertainty blockers")
    start.add_argument("project_root")
    start.add_argument("unit_id")
    start.add_argument("--expected-version", type=int, default=None)
    start.set_defaults(func=start_unit)
    artifact = sub.add_parser("register-artifact", help="register an existing output file within the unit write scope")
    artifact.add_argument("project_root")
    artifact.add_argument("unit_id")
    artifact.add_argument("artifact_id")
    artifact.add_argument("artifact_type")
    artifact.add_argument("path")
    artifact.add_argument("--status", choices=["candidate", "verified"], default="candidate")
    artifact.add_argument("--title", default=None)
    artifact.add_argument("--language", choices=["zh", "en", "bilingual", "neutral"], default="neutral")
    artifact.add_argument("--language-stage", default=None)
    artifact.add_argument("--input-artifact-id", action="append", default=[])
    artifact.add_argument("--source-ref", action="append", default=[])
    artifact.add_argument("--supersedes", default=None)
    artifact.add_argument("--expected-version", type=int, default=None)
    artifact.set_defaults(func=register_artifact)
    decision = sub.add_parser("record-decision", help="record a human or governance decision before a dependent gate")
    decision.add_argument("project_root")
    decision.add_argument("decision_id")
    decision.add_argument("--kind", choices=["human", "scope", "protocol", "journal", "package", "editorial", "rights", "release", "other"], default="human")
    decision.add_argument("--question", required=True)
    decision.add_argument("--answer", required=True)
    decision.add_argument("--actor", choices=["user", "advisor", "peer", "domain_expert", "editor", "rights_holder"], required=True)
    decision.add_argument("--evidence", action="append", default=[])
    decision.add_argument("--checkpoint-id", default=None)
    decision.add_argument("--expected-version", type=int, default=None)
    decision.set_defaults(func=record_decision)
    gate = sub.add_parser("record-gate", help="record a required or advisory gate verdict")
    gate.add_argument("project_root")
    gate.add_argument("unit_id")
    gate.add_argument("kind", choices=["science", "language", "mechanics", "uncertainty", "rights_submission", "human"])
    gate.add_argument("verdict", choices=["PASS", "PASS_WITH_CONDITIONS", "WARN", "BLOCK", "UNKNOWN", "NOT_CHECKED"])
    gate.add_argument("--check", action="append", default=[])
    gate.add_argument("--evidence", action="append", default=[])
    gate.add_argument("--decision-id", default=None)
    gate.add_argument("--advisory", action="store_true")
    gate.add_argument("--expected-version", type=int, default=None)
    gate.set_defaults(func=record_gate)
    complete = sub.add_parser("complete-unit", help="complete a unit only when outputs and required gates pass")
    complete.add_argument("project_root")
    complete.add_argument("unit_id")
    complete.add_argument("--expected-version", type=int, default=None)
    complete.set_defaults(func=complete_unit)
    handoff = sub.add_parser("handoff", help="prepare a contract-approved handoff from a completed unit")
    handoff.add_argument("project_root")
    handoff.add_argument("from_unit")
    handoff.add_argument("to_unit")
    handoff.add_argument("--open-question", action="append", default=[])
    handoff.add_argument("--decision-id", action="append", default=[])
    handoff.add_argument("--escalation", action="store_true", help="handoff a blocked unit only to a registered escalation target")
    handoff.add_argument("--expected-version", type=int, default=None)
    handoff.set_defaults(func=create_handoff)
    return parser


if __name__ == "__main__":
    try:
        parsed = build_parser().parse_args()
        raise SystemExit(parsed.func(parsed))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCK", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
