#!/usr/bin/env python3
"""Dependency-free structural and runtime contract checks for the SCI review skill."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "sci_review_runtime.py"
CONTENT_AUDIT = ROOT / "scripts" / "audit_research_bundle.py"


def check(name: str, condition: bool, detail: str) -> dict[str, object]:
    return {"id": name, "verdict": "PASS" if condition else "BLOCK", "detail": detail}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(RUNTIME), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def run_content_audit(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(CONTENT_AUDIT), str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def write_markdown_artifact(project: Path, directory: str, filename: str, artifact_id: str, artifact_type: str, unit_id: str, run_id: str, project_id: str) -> Path:
    path = project / directory / filename
    path.write_text(
        "\n".join(
            [
                "---",
                f"artifact_id: {artifact_id}",
                f"project_id: {project_id}",
                f"artifact_kind: {artifact_type}",
                f"work_unit: {unit_id}",
                "status: candidate",
                "language: neutral",
                "baseline_artifact: null",
                "source_registry: null",
                f"run_id: {run_id}",
                "gate_status: pending",
                "next_intents: []",
                "---",
                "",
                "# Contract smoke artifact",
                "",
                "Purpose, sources, method, confirmed conclusions, uncertainty, and manual next actions are recorded here.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_json_artifact(project: Path, directory: str, filename: str, payload: dict[str, object]) -> Path:
    path = project / directory / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def runtime_contract_smoke() -> tuple[bool, str]:
    res = ROOT / "res"
    res.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="_contract-smoke-", dir=res))
    failures: list[str] = []

    def expect(label: str, process: subprocess.CompletedProcess[str], codes: set[int]) -> None:
        if process.returncode not in codes:
            failures.append(f"{label}: code={process.returncode}, out={process.stdout[-400:]}, err={process.stderr[-200:]}")

    try:
        project = temp_root / "review-project"
        expect("init", run_cli("init", str(project), "--project-id", "contract-smoke", "--title", "Generic SCI review", "--intent", "build a general review"), {0})
        state_path = project / ".sci-review-system" / "state" / "project_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        run_id = state["run_id"]
        if state.get("project_profile") is not None:
            failures.append("generic init unexpectedly selected a domain profile")

        expect("start review protocol", run_cli("start-unit", str(project), "review-protocol"), {0})
        expect("completion must block without outputs/gates", run_cli("complete-unit", str(project), "review-protocol"), {2})
        expect(
            "unstarted unit gate bypass",
            run_cli("record-gate", str(project), "science-audit", "science", "PASS", "--evidence", "check:forbidden-bypass"),
            {2},
        )

        bad_artifact_id = "review-protocol__self-declared-gate__candidate__v0.1.0"
        bad_artifact = write_markdown_artifact(project, "scope", "self-declared-gate.md", bad_artifact_id, "review_protocol", "review-protocol", run_id, "contract-smoke")
        bad_artifact.write_text(bad_artifact.read_text(encoding="utf-8").replace("gate_status: pending", "gate_status: PASS"), encoding="utf-8")
        expect("self-declared artifact gate", run_cli("register-artifact", str(project), "review-protocol", bad_artifact_id, "review_protocol", str(bad_artifact)), {2})

        artifact_id = "review-protocol__generic__candidate__v0.1.0"
        artifact = write_markdown_artifact(project, "scope", "review-protocol.md", artifact_id, "review_protocol", "review-protocol", run_id, "contract-smoke")
        expect("register protocol", run_cli("register-artifact", str(project), "review-protocol", artifact_id, "review_protocol", str(artifact)), {0})
        expect(
            "generic science gate",
            run_cli("record-gate", str(project), "review-protocol", "science", "PASS", "--check", "protocol-fields", "--evidence", f"artifact:{artifact_id}"),
            {0},
        )
        expect(
            "human gate without decision",
            run_cli("record-gate", str(project), "review-protocol", "human", "PASS", "--evidence", f"artifact:{artifact_id}"),
            {2},
        )
        expect(
            "record human decision",
            run_cli("record-decision", str(project), "D-001", "--kind", "protocol", "--question", "Approve protocol?", "--answer", "Approved", "--actor", "user"),
            {0},
        )
        expect(
            "human gate with decision",
            run_cli("record-gate", str(project), "review-protocol", "human", "PASS", "--decision-id", "D-001", "--evidence", "decision:D-001"),
            {0},
        )
        expect("generic gate name cannot satisfy stage quality", run_cli("complete-unit", str(project), "review-protocol"), {2})
        expect(
            "stage-specific science gate",
            run_cli("record-gate", str(project), "review-protocol", "science", "PASS", "--check", "scope-and-method", "--evidence", f"artifact:{artifact_id}"),
            {0},
        )
        expect("complete protocol", run_cli("complete-unit", str(project), "review-protocol"), {0})
        expect("valid handoff", run_cli("handoff", str(project), "review-protocol", "scope-and-eligibility"), {0})
        expect("illegal handoff", run_cli("handoff", str(project), "review-protocol", "submission-package"), {2})
        expect("missing start requirements", run_cli("start-unit", str(project), "science-audit"), {2})

        artifact.write_text(artifact.read_text(encoding="utf-8") + "\nchanged after gate\n", encoding="utf-8")
        expect("changed artifact state validation", run_cli("validate-state", str(project)), {1})
        expect("changed artifact handoff", run_cli("handoff", str(project), "review-protocol", "scope-question"), {2})

        blocker_project = temp_root / "blocker-project"
        expect("init blocker project", run_cli("init", str(blocker_project), "--project-id", "blocker-smoke", "--title", "Generic SCI review", "--intent", "resume a review"), {0})
        blocker_state_path = blocker_project / ".sci-review-system" / "state" / "project_state.json"
        blocker_run_id = json.loads(blocker_state_path.read_text(encoding="utf-8"))["run_id"]
        expect("start intake", run_cli("start-unit", str(blocker_project), "intake-recover"), {0})
        intake_id = "intake-snapshot__generic__candidate__v0.1.0"
        intake_artifact = write_markdown_artifact(blocker_project, "control", "intake.md", intake_id, "intake_snapshot", "intake-recover", blocker_run_id, "blocker-smoke")
        expect("register intake", run_cli("register-artifact", str(blocker_project), "intake-recover", intake_id, "intake_snapshot", str(intake_artifact)), {0})
        expect("mechanics block", run_cli("record-gate", str(blocker_project), "intake-recover", "mechanics", "BLOCK", "--check", "manifest", "--evidence", f"artifact:{intake_id}"), {2})
        expect("mechanics re-review pass", run_cli("record-gate", str(blocker_project), "intake-recover", "mechanics", "PASS", "--check", "project-recoverability", "--evidence", f"artifact:{intake_id}"), {0})
        expect("complete after re-review", run_cli("complete-unit", str(blocker_project), "intake-recover"), {0})
        blocker_state = json.loads(blocker_state_path.read_text(encoding="utf-8"))
        if any(item.get("kind") == "gate" and item.get("status") == "open" for item in blocker_state.get("blockers", [])):
            failures.append("BLOCK -> PASS left an open gate blocker")

        escalation_project = temp_root / "escalation-project"
        expect("init escalation", run_cli("init", str(escalation_project), "--project-id", "escalation-smoke", "--title", "Generic SCI review", "--intent", "test escalation"), {0})
        escalation_state_path = escalation_project / ".sci-review-system" / "state" / "project_state.json"
        escalation_run_id = json.loads(escalation_state_path.read_text(encoding="utf-8"))["run_id"]
        expect("start escalation intake", run_cli("start-unit", str(escalation_project), "intake-recover"), {0})
        escalation_artifact_id = "intake-snapshot__escalation__candidate__v0.1.0"
        escalation_artifact = write_markdown_artifact(escalation_project, "control", "intake.md", escalation_artifact_id, "intake_snapshot", "intake-recover", escalation_run_id, "escalation-smoke")
        expect("register escalation intake", run_cli("register-artifact", str(escalation_project), "intake-recover", escalation_artifact_id, "intake_snapshot", str(escalation_artifact)), {0})
        expect("block escalation intake", run_cli("record-gate", str(escalation_project), "intake-recover", "mechanics", "BLOCK", "--check", "manifest", "--evidence", f"artifact:{escalation_artifact_id}"), {2})
        expect("blocked standard handoff", run_cli("handoff", str(escalation_project), "intake-recover", "pause-resume"), {2})
        expect("registered escalation handoff", run_cli("handoff", str(escalation_project), "intake-recover", "pause-resume", "--escalation", "--open-question", "Repair the manifest before resuming"), {0})

        readonly_project = temp_root / "readonly-project"
        expect("init readonly", run_cli("init", str(readonly_project), "--project-id", "readonly-smoke", "--title", "Generic SCI review", "--intent", "audit"), {0})
        readonly_state_path = readonly_project / ".sci-review-system" / "state" / "project_state.json"
        readonly_state = json.loads(readonly_state_path.read_text(encoding="utf-8"))
        readonly_state["policy"]["write_mode"] = "read_only"
        readonly_state_path.write_text(json.dumps(readonly_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        expect("read-only mutation", run_cli("start-unit", str(readonly_project), "review-protocol"), {2})

        profile_project = temp_root / "profile-project"
        expect("domain-keyword init", run_cli("init", str(profile_project), "--project-id", "profile-smoke", "--title", "柔性曲面超声探测综述", "--intent", "review conformal ultrasonic arrays"), {0})
        profile_state = json.loads((profile_project / ".sci-review-system" / "state" / "project_state.json").read_text(encoding="utf-8"))
        if profile_state.get("project_profile") is not None:
            failures.append("domain keywords unexpectedly activated a runtime profile")
        profile_state.setdefault("blockers", []).append({"blocker_id": "U-SMOKE", "kind": "uncertainty", "status": "open", "affected_unit_ids": ["scope-question"], "message": "scope claim needs expert review"})
        profile_state_path = profile_project / ".sci-review-system" / "state" / "project_state.json"
        profile_state_path.write_text(json.dumps(profile_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        expect("science unit blocked by affected uncertainty", run_cli("start-unit", str(profile_project), "scope-question"), {2})
        expect("uncertainty resolution unit remains available", run_cli("start-unit", str(profile_project), "uncertainty-triage"), {0})
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    return not failures, "runtime bypass, gate evidence, human decision, hash, handoff, read-only, blocker recovery, and profile checks" if not failures else "; ".join(failures)


def robustness_contract_smoke() -> tuple[bool, str]:
    res = ROOT / "res"
    res.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="_robustness-smoke-", dir=res))
    failures: list[str] = []

    def expect(label: str, process: subprocess.CompletedProcess[str], codes: set[int], contains: str | None = None) -> None:
        if process.returncode not in codes or (contains and contains not in process.stdout):
            failures.append(f"{label}: code={process.returncode}, out={process.stdout[-500:]}, err={process.stderr[-200:]}")

    try:
        search = temp_root / "search-project"
        expect("search init", run_cli("init", str(search), "--project-id", "search-smoke", "--title", "Generic review", "--intent", "search literature", "--mode", "checkpoint"), {0})
        expect("search blocked before capability preflight", run_cli("start-unit", str(search), "search-provenance"), {2}, "capability_errors")
        expect("passive capability preflight", run_cli("capability-preflight", str(search)), {0})
        search_state_path = search / ".sci-review-system" / "state" / "project_state.json"
        search_state = json.loads(search_state_path.read_text(encoding="utf-8"))
        for optional in ("consensus", "scite"):
            capability = search_state.get("capabilities", {}).get(optional, {})
            if capability.get("required") or not capability.get("enhancement_only") or capability.get("checks", [{}])[0].get("status") != "NOT_CHECKED":
                failures.append(f"{optional} was not recorded as optional enhancement with NOT_CHECKED access")
        expect("start search after preflight", run_cli("start-unit", str(search), "search-provenance"), {0})
        search_state = json.loads(search_state_path.read_text(encoding="utf-8"))
        search_log_id = "search-log__generic__candidate__v0.1.0"
        search_log = write_markdown_artifact(search, "sources", "search-log.md", search_log_id, "search_log", "search-provenance", search_state["run_id"], search_state["project_id"])
        expect("register search log", run_cli("register-artifact", str(search), "search-provenance", search_log_id, "search_log", str(search_log)), {0})
        for kind in ("mechanics", "science"):
            check_id = "source-provenance" if kind == "mechanics" else "science-check"
            expect(f"search {kind} gate", run_cli("record-gate", str(search), "search-provenance", kind, "PASS", "--check", check_id, "--evidence", f"artifact:{search_log_id}"), {0})
        expect("search completion blocked without actual lookup", run_cli("complete-unit", str(search), "search-provenance"), {2}, "PASS lookup records")
        trace = search / "sources" / "lookup-trace.txt"
        trace.write_text("Executed user-assisted database query; captured one verified result.\n", encoding="utf-8")
        expect("register scholarly source", run_cli(
            "register-source", str(search), "SRC-001", "--title", "Verified article", "--source-type", "journal_article",
            "--locator-kind", "doi", "--locator", "10.0000/example", "--authority-level", "A_SCHOLARLY_PRIMARY",
            "--review-status", "peer_reviewed", "--freshness-class", "stable", "--freshness-status", "PASS", "--check-status", "PASS",
            "--permitted-use", "scientific_claim", "--acquisition-method", "user_assisted", "--snapshot", str(trace), "--reason", "metadata and trace checked"
        ), {0})
        expect("record evidence-backed lookup", run_cli(
            "record-lookup", str(search), "LKP-001", "--unit-id", "search-provenance", "--question", "Find evidence for the review scope",
            "--purpose", "field_synthesis", "--required", "--authority-floor", "A_SCHOLARLY_PRIMARY", "--acceptance-rule", "verified scholarly result",
            "--planned-capability-id", "academic_database", "--actual-route", "user_assisted", "--query", "generic review query", "--status", "PASS",
            "--source-id", "SRC-001", "--trace-file", str(trace), "--reason", "query actually executed"
        ), {0})
        expect("complete search with actual lookup", run_cli("complete-unit", str(search), "search-provenance"), {0})

        preview_state = json.loads(search_state_path.read_text(encoding="utf-8"))
        preview_version = preview_state["state_version"]
        expect("preview scope re-audit", run_cli(
            "plan-reaudit", str(search), "RAP-001", "--source-unit", "search-provenance", "--change-type", "scope",
            "--artifact-id", search_log_id, "--reason", "The research scope changed after the first search"
        ), {0}, "search-provenance")
        preview_state = json.loads(search_state_path.read_text(encoding="utf-8"))
        if preview_state["state_version"] != preview_version or "RAP-001" in preview_state.get("re_audit_plans", {}):
            failures.append("re-audit preview mutated project state")
        expect("apply scope re-audit", run_cli(
            "plan-reaudit", str(search), "RAP-001", "--source-unit", "search-provenance", "--change-type", "scope",
            "--artifact-id", search_log_id, "--reason", "The research scope changed after the first search", "--apply"
        ), {0}, "APPLIED")
        stale_state = json.loads(search_state_path.read_text(encoding="utf-8"))
        stale_plan = stale_state.get("re_audit_plans", {}).get("RAP-001", {})
        if stale_state.get("units", {}).get("search-provenance", {}).get("status") != "re_audit_required":
            failures.append("completed affected unit was not marked re_audit_required")
        if "search-provenance" not in stale_plan.get("affected_unit_ids", []) or not stale_plan.get("invalidated_gate_ids"):
            failures.append("re-audit plan did not retain affected units and invalidated gates")
        expect("stale search cannot hand off", run_cli("handoff", str(search), "search-provenance", "corpus-curation"), {2}, "re_audit_required")
        expect("restart stale search", run_cli("start-unit", str(search), "search-provenance"), {0}, "RAP-001")
        refreshed_log_id = "search-log__scope-v2__candidate__v0.2.0"
        refreshed_log = write_markdown_artifact(search, "sources", "search-log-v2.md", refreshed_log_id, "search_log", "search-provenance", search_state["run_id"], search_state["project_id"])
        refreshed_manifest_id = "source-manifest__scope-v2__candidate__v0.2.0"
        refreshed_manifest = write_markdown_artifact(search, "sources", "source-manifest-v2.md", refreshed_manifest_id, "source_manifest", "search-provenance", search_state["run_id"], search_state["project_id"])
        expect("register refreshed search log", run_cli("register-artifact", str(search), "search-provenance", refreshed_log_id, "search_log", str(refreshed_log)), {0})
        expect("register refreshed source manifest", run_cli("register-artifact", str(search), "search-provenance", refreshed_manifest_id, "source_manifest", str(refreshed_manifest)), {0})
        expect("refreshed search mechanics gate", run_cli("record-gate", str(search), "search-provenance", "mechanics", "PASS", "--check", "source-provenance", "--evidence", f"artifact:{refreshed_log_id}"), {0})
        expect("refreshed search science gate", run_cli("record-gate", str(search), "search-provenance", "science", "PASS", "--check", "science-check", "--evidence", f"artifact:{refreshed_log_id}"), {0})
        expect("complete search re-audit", run_cli("complete-unit", str(search), "search-provenance"), {0}, "RAP-001")
        resolved_state = json.loads(search_state_path.read_text(encoding="utf-8"))
        if resolved_state.get("re_audit_plans", {}).get("RAP-001", {}).get("status") != "resolved":
            failures.append("re-audit plan did not resolve after every stale unit completed")
        expect("handoff succeeds after re-audit", run_cli("handoff", str(search), "search-provenance", "corpus-curation"), {0})

        package = temp_root / "package-project"
        expect("package init", run_cli("init", str(package), "--project-id", "package-smoke", "--title", "Existing manuscript", "--intent", "package using my template", "--mode", "checkpoint"), {0})
        package_state_path = package / ".sci-review-system" / "state" / "project_state.json"
        package_state = json.loads(package_state_path.read_text(encoding="utf-8"))
        expect("start intake", run_cli("start-unit", str(package), "intake-recover"), {0})
        intake_id = "intake-snapshot__package__candidate__v0.1.0"
        baseline_id = "baseline-manuscript__package__candidate__v0.1.0"
        intake = write_markdown_artifact(package, "control", "intake.md", intake_id, "intake_snapshot", "intake-recover", package_state["run_id"], package_state["project_id"])
        baseline = write_markdown_artifact(package, "control", "baseline.md", baseline_id, "baseline_manuscript", "intake-recover", package_state["run_id"], package_state["project_id"])
        expect("register package intake", run_cli("register-artifact", str(package), "intake-recover", intake_id, "intake_snapshot", str(intake)), {0})
        expect("register baseline manuscript", run_cli("register-artifact", str(package), "intake-recover", baseline_id, "baseline_manuscript", str(baseline)), {0})
        expect("intake gate", run_cli("record-gate", str(package), "intake-recover", "mechanics", "PASS", "--check", "project-recoverability", "--evidence", f"artifact:{intake_id}"), {0})
        expect("complete intake", run_cli("complete-unit", str(package), "intake-recover"), {0})
        expect("unknown journal adaptation is skipped", run_cli("start-unit", str(package), "journal-fit"), {2}, "not_selected")
        expect("template package starts without selected journal", run_cli("start-unit", str(package), "submission-package"), {0})
        invalid_plan_id = "package-plan__invalid__candidate__v0.1.0"
        invalid_plan = write_json_artifact(package, "delivery", "invalid-plan.json", {
            "schema_version": "1.0", "package_plan_id": "PP-invalid", "project_id": package_state["project_id"], "status": "draft",
            "journal_context": {"status": "not_selected", "venue_profile_id": None, "compliance_claim_allowed": False},
            "package_bases": [], "items": [], "mappings": [], "conflicts": [],
            "user_control": {"final_shape_owner": "user", "shape_confirmed": False, "submission_actor": "user", "system_may_submit": False}, "updated_at": "2026-07-19T00:00:00+08:00"
        })
        expect("package cannot invent a universal shape", run_cli("register-artifact", str(package), "submission-package", invalid_plan_id, "package_plan", str(invalid_plan)), {2}, "user manifest")
        plan_id = "package-plan__user-template__candidate__v0.1.0"
        plan = write_json_artifact(package, "delivery", "package-plan.json", {
            "schema_version": "1.0", "package_plan_id": "PP-user-template", "project_id": package_state["project_id"], "status": "user_confirmed",
            "journal_context": {"status": "not_selected", "venue_profile_id": None, "compliance_claim_allowed": False},
            "package_bases": [{"basis_id": "PB-user", "basis_type": "user_template", "reference": "user-provided package layout", "content_hash": None, "confirmed_by_user": True, "captured_at": "2026-07-19T00:00:00+08:00"}],
            "items": [], "mappings": [], "conflicts": [],
            "user_control": {"final_shape_owner": "user", "shape_confirmed": True, "confirmed_at": "2026-07-19T00:00:00+08:00", "submission_actor": "user", "system_may_submit": False}, "check_report_path": None, "updated_at": "2026-07-19T00:00:00+08:00"
        })
        manifest_id = "submission-package-manifest__user-template__candidate__v0.1.0"
        report_id = "submission-check-report__user-template__candidate__v0.1.0"
        rights_id = "rights-status__package__candidate__v0.1.0"
        manifest = write_markdown_artifact(package, "delivery", "manifest.md", manifest_id, "submission_package_manifest", "submission-package", package_state["run_id"], package_state["project_id"])
        rights = write_markdown_artifact(package, "delivery", "rights.md", rights_id, "rights_status", "submission-package", package_state["run_id"], package_state["project_id"])
        report = write_json_artifact(package, "delivery", "check-report.json", {
            "schema_version": "1.0", "report_id": "SC-user-template", "package_plan_id": "PP-user-template", "package_fingerprint": "sha256:test", "checked_at": "2026-07-19T00:00:00+08:00", "overall_status": "PASS",
            "checks": [{"check_id": "CK-template", "label": "Template mapping", "target": "package", "rule_basis": "user_template", "rule_reference": "PB-user", "status": "PASS", "performed_by": "system", "checked_at": "2026-07-19T00:00:00+08:00", "evidence": [{"evidence_type": "manifest_entry", "reference": "manifest.md", "captured_at": "2026-07-19T00:00:00+08:00"}], "reason": None, "next_action": None}],
            "unresolved_items": [], "user_review": {"reviewed": True, "reviewed_at": "2026-07-19T00:00:00+08:00", "notes": "approved test template"}, "submission_status": "not_submitted"
        })
        for label, artifact_id, artifact_type, path in (("plan", plan_id, "package_plan", plan), ("manifest", manifest_id, "submission_package_manifest", manifest), ("report", report_id, "submission_check_report", report), ("rights", rights_id, "rights_status", rights)):
            expect(f"register package {label}", run_cli("register-artifact", str(package), "submission-package", artifact_id, artifact_type, str(path)), {0})
        expect("package decision", run_cli("record-decision", str(package), "D-PKG", "--kind", "package", "--question", "Approve package shape?", "--answer", "Approved", "--actor", "user"), {0})
        for kind in ("science", "language", "mechanics", "rights_submission"):
            check_id = "venue-and-package-basis" if kind == "rights_submission" else f"{kind}-check"
            expect(f"package {kind} gate", run_cli("record-gate", str(package), "submission-package", kind, "PASS", "--check", check_id, "--evidence", f"artifact:{report_id}"), {0})
        expect("package human gate", run_cli("record-gate", str(package), "submission-package", "human", "PASS", "--decision-id", "D-PKG", "--evidence", "decision:D-PKG"), {0})
        expect("complete template-driven package", run_cli("complete-unit", str(package), "submission-package"), {0})
        expect("editorial intake blocks without actual letter", run_cli("start-unit", str(package), "editorial-decision-intake"), {2}, "source_errors")
        letter = package / "editorial" / "editor-letter.txt"
        letter.write_text("Actual editor decision received for the manuscript.\n", encoding="utf-8")
        expect("register actual editor letter", run_cli(
            "register-source", str(package), "SRC-900", "--title", "Editor decision", "--source-type", "personal_communication",
            "--locator-kind", "local_path", "--locator", str(letter), "--authority-level", "A_OFFICIAL_PRIMARY", "--review-status", "official",
            "--freshness-class", "stable", "--freshness-status", "PASS", "--check-status", "PASS", "--permitted-use", "provenance_only",
            "--acquisition-method", "personal_communication", "--snapshot", str(letter), "--reason", "actual received letter retained locally"
        ), {0})
        expect("editorial intake starts with actual letter", run_cli("start-unit", str(package), "editorial-decision-intake"), {0})

        journal = temp_root / "journal-project"
        expect("journal init", run_cli("init", str(journal), "--project-id", "journal-smoke", "--title", "Journal adaptation", "--intent", "adapt to confirmed journal", "--mode", "checkpoint"), {0})
        expect("journal preflight", run_cli("capability-preflight", str(journal)), {0})
        expect("journal decision", run_cli("record-decision", str(journal), "D-JRN", "--kind", "journal", "--question", "Confirm journal?", "--answer", "Confirmed", "--actor", "user"), {0})
        expect("confirm journal", run_cli("set-journal-status", str(journal), "confirmed", "--journal-name", "Example Journal", "--decision-id", "D-JRN"), {0})
        stale = journal / "journal" / "stale-guidance.txt"
        stale.write_text("Old author and submission guidance snapshot.\n", encoding="utf-8")
        expect("register stale official source", run_cli(
            "register-source", str(journal), "SRC-100", "--title", "Old official guide", "--source-type", "official_guidance", "--locator-kind", "url", "--locator", "https://example.org/guide",
            "--authority-level", "A_OFFICIAL_PRIMARY", "--review-status", "official", "--accessed-at", "2020-01-01T00:00:00+00:00", "--freshness-class", "current", "--max-age-days", "180",
            "--freshness-status", "PASS", "--check-status", "PASS", "--permitted-use", "journal_requirement", "--permitted-use", "submission_requirement", "--acquisition-method", "browser", "--snapshot", str(stale), "--reason", "historical snapshot used to test freshness"
        ), {0})
        expect("record stale lookup", run_cli(
            "record-lookup", str(journal), "LKP-100", "--unit-id", "journal-fit", "--question", "Verify current journal requirements", "--purpose", "journal_requirement", "--required", "--authority-floor", "A_OFFICIAL_PRIMARY", "--freshness-required",
            "--acceptance-rule", "current official author and submission guidance", "--planned-capability-id", "browser", "--actual-route", "browser", "--query", "official journal requirements", "--status", "PASS", "--source-id", "SRC-100", "--trace-file", str(stale), "--reason", "lookup trace exists but is stale"
        ), {0})
        expect("start confirmed journal", run_cli("start-unit", str(journal), "journal-fit"), {0})
        journal_state = json.loads((journal / ".sci-review-system" / "state" / "project_state.json").read_text(encoding="utf-8"))
        profile_id = "journal-profile__example__candidate__v0.1.0"
        profile = write_json_artifact(journal, "journal", "profile.json", {
            "schema_version": "1.0", "profile_id": "VP-example", "status": "confirmed", "target_journal": {"name": "Example Journal", "publisher": None, "issn": None, "article_type": "Review"}, "use_mode": "enforceable",
            "decision": {"confirmed_by_user": True, "rationale": "test", "skip_reason": None, "confirmed_at": "2026-07-19T00:00:00+08:00", "confirmed_by": "user"},
            "freshness_policy": {"maximum_age_days": 180, "evaluated_at": "2026-07-19T00:00:00+08:00", "basis": "runtime policy"},
            "sources": [{"source_id": "VS-guide", "source_type": "author_guidelines", "authority": "official_journal", "title": "Guide", "url": "https://example.org/guide", "access_date": "2026-07-19", "freshness": {"status": "current", "evaluated_at": "2026-07-19T00:00:00+08:00", "age_days": 0, "basis": "profile claim"}, "extracted_facts": ["test"], "notes": None}, {"source_id": "VS-system", "source_type": "submission_system", "authority": "official_journal", "title": "System", "url": "https://example.org/submit", "access_date": "2026-07-19", "freshness": {"status": "current", "evaluated_at": "2026-07-19T00:00:00+08:00", "age_days": 0, "basis": "profile claim"}, "extracted_facts": ["test"], "notes": None}],
            "requirements": [], "updated_at": "2026-07-19T00:00:00+08:00"
        })
        guide_id = "author-guideline-snapshot__example__candidate__v0.1.0"
        guide = write_markdown_artifact(journal, "journal", "guideline.md", guide_id, "author_guideline_snapshot", "journal-fit", journal_state["run_id"], journal_state["project_id"])
        expect("register journal profile", run_cli("register-artifact", str(journal), "journal-fit", profile_id, "journal_profile", str(profile)), {0})
        expect("register journal snapshot", run_cli("register-artifact", str(journal), "journal-fit", guide_id, "author_guideline_snapshot", str(guide)), {0})
        expect("journal rights gate", run_cli("record-gate", str(journal), "journal-fit", "rights_submission", "PASS", "--check", "venue-and-package-basis", "--evidence", f"artifact:{profile_id}"), {0})
        expect("journal human gate", run_cli("record-gate", str(journal), "journal-fit", "human", "PASS", "--decision-id", "D-JRN", "--evidence", "decision:D-JRN"), {0})
        expect("stale official source blocks completion", run_cli("complete-unit", str(journal), "journal-fit"), {2}, "missing verified source")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    return not failures, "capability, lookup, optional journal, flexible package, editorial-source, and freshness contracts" if not failures else "; ".join(failures)


def stage_quality_contracts(registry: dict[str, object], units: list[dict[str, object]]) -> tuple[bool, str]:
    definitions = registry.get("quality_check_definitions", {})
    mappings = registry.get("unit_quality_checks", {})
    gate_definitions = registry.get("gate_definitions", {})
    unit_by_id = {unit["unit_id"]: unit for unit in units}
    missing_mappings = sorted(set(unit_by_id) - set(mappings))
    unknown_mapping_units = sorted(set(mappings) - set(unit_by_id))
    undefined_checks: list[str] = []
    unreachable_checks: list[str] = []
    malformed_definitions: list[str] = []
    used_checks: set[str] = set()
    for unit_id, check_ids in mappings.items():
        if not isinstance(check_ids, list) or not check_ids:
            unreachable_checks.append(f"{unit_id}:empty")
            continue
        for check_id in check_ids:
            used_checks.add(check_id)
            definition = definitions.get(check_id)
            if not definition:
                undefined_checks.append(f"{unit_id}:{check_id}")
                continue
            gate_kind = definition.get("gate_kind")
            if gate_kind not in gate_definitions or not definition.get("evaluator") or not definition.get("pass_condition"):
                malformed_definitions.append(check_id)
            if unit_id in unit_by_id and gate_kind not in unit_by_id[unit_id].get("required_gates", []):
                unreachable_checks.append(f"{unit_id}:{check_id}->{gate_kind}")
    unused_definitions = sorted(set(definitions) - used_checks)
    runtime = RUNTIME.read_text(encoding="utf-8")
    enforcement_present = all(token in runtime for token in ("def quality_check_failures", "required_quality_checks", "quality_check_failures"))
    ok = not any((missing_mappings, unknown_mapping_units, undefined_checks, unreachable_checks, malformed_definitions, unused_definitions)) and enforcement_present
    detail = {
        "definitions": len(definitions),
        "mapped_units": len(mappings),
        "missing_mappings": missing_mappings,
        "unknown_mapping_units": unknown_mapping_units,
        "undefined_checks": undefined_checks,
        "unreachable_checks": unreachable_checks,
        "malformed_definitions": sorted(set(malformed_definitions)),
        "unused_definitions": unused_definitions,
        "runtime_enforcement": enforcement_present,
    }
    return ok, json.dumps(detail, ensure_ascii=False, separators=(",", ":"))


def change_impact_contracts(registry: dict[str, object], units: list[dict[str, object]], skill: str) -> tuple[bool, str]:
    rules = registry.get("change_impact_rules", {})
    unit_ids = {unit["unit_id"] for unit in units}
    gate_kinds = set(registry.get("gate_definitions", {}))
    schema = json.loads((ROOT / "schemas" / "re-audit-plan.schema.json").read_text(encoding="utf-8"))
    schema_types = set(schema["properties"]["change_types"]["items"]["enum"])
    rule_types = set(rules)
    malformed: list[str] = []
    unknown_units: dict[str, list[str]] = {}
    unknown_gates: dict[str, list[str]] = {}
    for change_type, rule in rules.items():
        affected = rule.get("affected_units", [])
        required_gates = rule.get("required_gate_kinds", [])
        if not affected or not required_gates or not rule.get("reason"):
            malformed.append(change_type)
        invalid_units = sorted(set(affected) - unit_ids)
        invalid_gates = sorted(set(required_gates) - gate_kinds)
        if invalid_units:
            unknown_units[change_type] = invalid_units
        if invalid_gates:
            unknown_gates[change_type] = invalid_gates
    runtime = RUNTIME.read_text(encoding="utf-8")
    runtime_support = all(token in runtime for token in ("def plan_reaudit", 'rule.get("affected_units"', 'status"] = "re_audit_required"', 'plan["status"] = "resolved"'))
    skill_support = "`plan-reaudit`" in skill and "re_audit_required" in skill
    ok = rule_types == schema_types and not malformed and not unknown_units and not unknown_gates and runtime_support and skill_support
    detail = {
        "rules": len(rules),
        "schema_mismatch": sorted(rule_types.symmetric_difference(schema_types)),
        "malformed": malformed,
        "unknown_units": unknown_units,
        "unknown_gates": unknown_gates,
        "runtime_support": runtime_support,
        "skill_support": skill_support,
    }
    return ok, json.dumps(detail, ensure_ascii=False, separators=(",", ":"))


def content_forward_smoke() -> tuple[bool, str]:
    pass_path = ROOT / "evals" / "fixtures" / "research-content-pass.json"
    fail_path = ROOT / "evals" / "fixtures" / "research-content-fail.json"
    passed = run_content_audit(pass_path)
    failed = run_content_audit(fail_path)
    try:
        pass_result = json.loads(passed.stdout)
        fail_result = json.loads(failed.stdout)
    except json.JSONDecodeError as exc:
        return False, f"content audit emitted invalid JSON: {exc}"
    required_failures = {
        "ANCHOR_LOCATOR_REQUIRED",
        "UNKNOWN_ANCHOR",
        "CLAIM_EVIDENCE_REQUIRED",
        "NUMERIC_CONDITIONS_REQUIRED",
        "SYNTHESIS_SOURCE_COUNT",
        "SYNTHESIS_DIMENSIONS_REQUIRED",
        "SYNTHESIS_CONFLICT_ASSESSMENT_REQUIRED",
        "SYNTHESIS_BOUNDARY_REQUIRED",
        "UNKNOWN_CLAIM",
        "REVISION_CHANGE_REF_REQUIRED",
        "REVISION_EVIDENCE_REQUIRED",
    }
    observed_failures = {item.get("code") for item in fail_result.get("issues", [])}
    ok = (
        passed.returncode == 0
        and pass_result.get("verdict") == "PASS"
        and not pass_result.get("issues")
        and failed.returncode == 1
        and fail_result.get("verdict") == "BLOCK"
        and required_failures.issubset(observed_failures)
    )
    detail = {
        "pass_code": passed.returncode,
        "pass_verdict": pass_result.get("verdict"),
        "fail_code": failed.returncode,
        "fail_verdict": fail_result.get("verdict"),
        "missing_expected_failures": sorted(required_failures - observed_failures),
    }
    return ok, json.dumps(detail, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = skill.startswith("---\n") and "name:" in skill.split("---", 2)[1] and "description:" in skill.split("---", 2)[1]
    registry = json.loads((ROOT / "work-units" / "unit-registry.json").read_text(encoding="utf-8"))
    units = registry.get("units", [])
    ids = [unit.get("unit_id", "") for unit in units]
    semantic_ids = bool(ids) and len(ids) == len(set(ids)) and all(not re.match(r"^(?:[0-9]+[-_])", unit_id) for unit_id in ids)
    id_set = set(ids)
    transition_fields = ("next_candidates", "rework_candidates")
    dangling = {
        unit["unit_id"]: [target for field in transition_fields for target in unit.get(field, []) if target not in id_set]
        for unit in units
    }
    dangling = {key: value for key, value in dangling.items() if value}
    block_dangling = {kind: [target for target in targets if target not in id_set] for kind, targets in registry.get("block_transitions", {}).items()}
    block_dangling = {key: value for key, value in block_dangling.items() if value}
    excluded_tokens = {
        "pass-with-conditions", "needs-human-check", "no-change-needed", "rights-submission", "quality-judgment",
        "allow-root-project", "human-review-required", "meta-analysis", "meta-synthesis", "cross-literature",
        "sci-review-system", "start-unit", "register-artifact", "record-decision", "record-gate",
        "complete-unit", "project-profiles", "capability-preflight", "record-capability", "register-source",
        "record-lookup", "set-journal-status", "research-backed", "human-verified", "submission-ready",
        "plan-reaudit",
    }
    referenced_units: set[str] = set()
    for path in (ROOT / "SKILL.md", ROOT / "orchestration" / "intent-router.md"):
        referenced_units.update(token for token in re.findall(r"`([a-z][a-z0-9-]+)`", path.read_text(encoding="utf-8")) if "-" in token and token not in excluded_tokens)
    missing_unit_refs = sorted(referenced_units - id_set)

    outputs_by_unit = {unit["unit_id"]: set(unit.get("outputs", [])) for unit in units}
    completion_mismatch = {
        unit_id: sorted((set(contract.get("all", [])) | set(contract.get("any", []))) - outputs_by_unit.get(unit_id, set()))
        for unit_id, contract in registry.get("completion_outputs", {}).items()
    }
    completion_mismatch = {key: value for key, value in completion_mismatch.items() if value}
    produced_types = set().union(*outputs_by_unit.values()) if outputs_by_unit else set()
    missing_start_types = sorted(
        {
            artifact_type
            for contract in registry.get("start_requirements", {}).values()
            for artifact_type in [*contract.get("all", []), *contract.get("any", []), *contract.get("pipeline_all", []), *contract.get("pipeline_any", [])]
            if artifact_type not in produced_types
        }
    )

    references = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "references").glob("*.md"))
    protection = all(token in references for token in ("numbers", "units", "formulas", "citations", "causality"))
    runtime = RUNTIME.read_text(encoding="utf-8")
    runtime_ok = all(token in runtime for token in ("init", "validate-state", "suggest-name", "append_event", "route", "register-artifact", "record-decision", "record-gate", "plan-reaudit", "complete-unit", "handoff"))
    uncertainty_ref = (ROOT / "references" / "uncertainty-escalation.md").read_text(encoding="utf-8")
    uncertainty_ok = all(token in uncertainty_ref for token in ("verified", "uncertain", "human_review_required", "human_checkpoint")) and (ROOT / "schemas" / "uncertainty-record.schema.json").exists() and (ROOT / "schemas" / "human-checkpoint.schema.json").exists()
    review_protocol_ok = (ROOT / "references" / "review-methodology.md").exists() and (ROOT / "schemas" / "review-protocol.schema.json").exists() and "scope-and-eligibility" in next(unit["next_candidates"] for unit in units if unit["unit_id"] == "review-protocol")
    generic_files = skill + "\n" + "\n".join((ROOT / "references" / name).read_text(encoding="utf-8") for name in ("evidence-policy.md", "review-synthesis.md", "quantitative-audit.md"))
    domain_hardcoding = any(token in generic_files for token in ("material, defect, frequency, sensor, curvature, coupling", "clearer signal       != more accurate sizing", "sharper image        != smaller localization error"))
    profile_index = json.loads((ROOT / "project-profiles" / "index.json").read_text(encoding="utf-8"))
    generic_core = "name: sci-review-system" in skill and "# SCI Review System" in skill and not domain_hardcoding and isinstance(profile_index.get("profiles"), list)
    contract_registry = all(key in registry for key in ("contract_defaults", "gate_definitions", "block_transitions", "unit_write_roots", "start_requirements", "completion_outputs"))
    runtime_smoke_ok, runtime_smoke_detail = runtime_contract_smoke()
    robustness_smoke_ok, robustness_smoke_detail = robustness_contract_smoke()
    stage_quality_ok, stage_quality_detail = stage_quality_contracts(registry, units)
    change_impact_ok, change_impact_detail = change_impact_contracts(registry, units, skill)
    content_smoke_ok, content_smoke_detail = content_forward_smoke()

    results = [
        check("skill-frontmatter", frontmatter, "root metadata present"),
        check("semantic-unit-registry", semantic_ids, f"{len(ids)} unique semantic work units"),
        check("unit-transitions", not dangling and not block_dangling and not missing_unit_refs, f"dangling={dangling}; block_dangling={block_dangling}; missing_refs={missing_unit_refs}"),
        check("unit-artifact-contracts", not completion_mismatch and not missing_start_types, f"completion_mismatch={completion_mismatch}; missing_start_types={missing_start_types}"),
        check("generic-core", generic_core, "field-neutral SCI core with lazy optional project profiles"),
        check("conditional-reading-anchor", "If repository policy enables" in (ROOT / "references" / "reading-anchor-policy.md").read_text(encoding="utf-8"), "reading anchor is repository-policy driven"),
        check("no-numbered-router", "00-20" not in (ROOT / "orchestration" / "intent-router.md").read_text(encoding="utf-8"), "router is intent-based"),
        check("language-protection", protection, "language references contain protected-span rules"),
        check("runtime-contracts", runtime_ok, "runtime helper exposes enforced transition commands"),
        check("contract-registry", contract_registry, "registry carries gate definitions, block paths, prerequisites, outputs, and write scopes"),
        check("stage-quality-contracts", stage_quality_ok, stage_quality_detail),
        check("change-impact-contracts", change_impact_ok, change_impact_detail),
        check("runtime-contract-smoke", runtime_smoke_ok, runtime_smoke_detail),
        check("robustness-contract-smoke", robustness_smoke_ok, robustness_smoke_detail),
        check("content-forward-smoke", content_smoke_ok, content_smoke_detail),
        check("uncertainty-escalation", uncertainty_ok, "uncertainty states and human checkpoint contracts present"),
        check("review-protocol", review_protocol_ok, "review protocol routes to eligibility before broad retrieval"),
    ]
    verdict = "PASS" if all(item["verdict"] == "PASS" for item in results) else "BLOCK"
    print(json.dumps({"verdict": verdict, "checks": results}, ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
