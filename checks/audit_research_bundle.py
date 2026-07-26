#!/usr/bin/env python3
"""Audit a minimal source-to-revision research bundle.

This checker validates traceability and contract completeness. It deliberately
does not score prose quality or naturalness, which require independent or human
review.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]*$")
CLAIM_STATUSES = {"verified", "supported", "uncertain", "human_review_required"}
REVISION_STATUSES = {"open", "planned", "in_progress", "completed", "accepted_no_change"}
EVIDENCE_RELATIONS = {"supports", "contradicts", "contextualizes"}
SECTIONS = (
    ("sources", "source_id"),
    ("evidence", "evidence_id"),
    ("claims", "claim_id"),
    ("syntheses", "synthesis_id"),
    ("paragraph_contracts", "paragraph_id"),
    ("revision_items", "issue_id"),
)


def add_issue(issues: list[dict[str, str]], code: str, path: str, message: str) -> None:
    issues.append({"code": code, "path": path, "message": message})


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def read_records(data: dict[str, Any], section: str, issues: list[dict[str, str]]) -> list[dict[str, Any]]:
    value = data.get(section)
    if not isinstance(value, list) or not value:
        add_issue(issues, "MISSING_SECTION", section, f"{section} must be a non-empty array")
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            add_issue(issues, "INVALID_RECORD", f"{section}[{index}]", "record must be an object")
            continue
        records.append(item)
    return records


def index_records(
    records: list[dict[str, Any]],
    section: str,
    id_field: str,
    issues: list[dict[str, str]],
    all_ids: dict[str, str],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        path = f"{section}[{index}].{id_field}"
        record_id = record.get(id_field)
        if not nonempty_text(record_id) or not ID_PATTERN.fullmatch(record_id):
            add_issue(issues, "INVALID_ID", path, "id must start with a letter and contain only letters, digits, '.', '_', ':', or '-'")
            continue
        if record_id in indexed:
            add_issue(issues, "DUPLICATE_ID", path, f"duplicate {id_field}: {record_id}")
            continue
        if record_id in all_ids:
            add_issue(issues, "CROSS_TYPE_DUPLICATE_ID", path, f"{record_id} is already used in {all_ids[record_id]}")
        all_ids[record_id] = section
        indexed[record_id] = record
    return indexed


def string_list(record: dict[str, Any], field: str, path: str, issues: list[dict[str, str]]) -> list[str]:
    value = record.get(field, [])
    if not isinstance(value, list):
        add_issue(issues, "INVALID_LIST", f"{path}.{field}", f"{field} must be an array")
        return []
    output: list[str] = []
    for index, item in enumerate(value):
        if not nonempty_text(item):
            add_issue(issues, "INVALID_LIST_ITEM", f"{path}.{field}[{index}]", "item must be non-empty text")
        else:
            output.append(item)
    return output


def audit_bundle(data: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return {"verdict": "BLOCK", "issues": [{"code": "INVALID_ROOT", "path": "$", "message": "root must be an object"}]}
    if data.get("schema_version") != "0.1":
        add_issue(issues, "SCHEMA_VERSION", "schema_version", "schema_version must be 0.1")
    if not nonempty_text(data.get("bundle_id")) or not ID_PATTERN.fullmatch(data.get("bundle_id", "")):
        add_issue(issues, "INVALID_ID", "bundle_id", "bundle_id must be a stable id")

    records = {section: read_records(data, section, issues) for section, _ in SECTIONS}
    all_ids: dict[str, str] = {}
    indexes = {
        section: index_records(records[section], section, id_field, issues, all_ids)
        for section, id_field in SECTIONS
    }

    anchor_index: set[tuple[str, str]] = set()
    for index, source in enumerate(records["sources"]):
        path = f"sources[{index}]"
        source_id = source.get("source_id")
        for field in ("title", "source_type", "locator"):
            if not nonempty_text(source.get(field)):
                add_issue(issues, "SOURCE_IDENTITY_REQUIRED", f"{path}.{field}", f"source {field} is required")
        anchors = source.get("anchors")
        if not isinstance(anchors, list) or not anchors:
            add_issue(issues, "SOURCE_ANCHOR_REQUIRED", f"{path}.anchors", "source must contain at least one exact anchor")
            continue
        seen_anchor_ids: set[str] = set()
        for anchor_number, anchor in enumerate(anchors):
            anchor_path = f"{path}.anchors[{anchor_number}]"
            if not isinstance(anchor, dict):
                add_issue(issues, "INVALID_RECORD", anchor_path, "anchor must be an object")
                continue
            anchor_id = anchor.get("anchor_id")
            if not nonempty_text(anchor_id) or not ID_PATTERN.fullmatch(anchor_id):
                add_issue(issues, "INVALID_ID", f"{anchor_path}.anchor_id", "anchor_id must be a stable id")
                continue
            if anchor_id in seen_anchor_ids:
                add_issue(issues, "DUPLICATE_ID", f"{anchor_path}.anchor_id", f"duplicate anchor id in source: {anchor_id}")
            seen_anchor_ids.add(anchor_id)
            if not nonempty_text(anchor.get("locator")):
                add_issue(issues, "ANCHOR_LOCATOR_REQUIRED", f"{anchor_path}.locator", "anchor needs a page, section, figure, table, or line locator")
            if nonempty_text(source_id):
                anchor_index.add((source_id, anchor_id))

    evidence_index = indexes["evidence"]
    for index, evidence in enumerate(records["evidence"]):
        path = f"evidence[{index}]"
        source_id = evidence.get("source_id")
        anchor_id = evidence.get("anchor_id")
        if source_id not in indexes["sources"]:
            add_issue(issues, "UNKNOWN_SOURCE", f"{path}.source_id", f"unknown source: {source_id}")
        if (source_id, anchor_id) not in anchor_index:
            add_issue(issues, "UNKNOWN_ANCHOR", f"{path}.anchor_id", "evidence must reference an exact anchor in its source")
        if evidence.get("relation") not in EVIDENCE_RELATIONS:
            add_issue(issues, "INVALID_EVIDENCE_RELATION", f"{path}.relation", f"relation must be one of {sorted(EVIDENCE_RELATIONS)}")
        if not nonempty_text(evidence.get("summary")):
            add_issue(issues, "EVIDENCE_SUMMARY_REQUIRED", f"{path}.summary", "evidence summary is required")

    claim_index = indexes["claims"]
    for index, claim in enumerate(records["claims"]):
        path = f"claims[{index}]"
        text = claim.get("text")
        status = claim.get("status")
        evidence_ids = string_list(claim, "evidence_ids", path, issues)
        conditions = string_list(claim, "conditions", path, issues)
        if not nonempty_text(text):
            add_issue(issues, "CLAIM_TEXT_REQUIRED", f"{path}.text", "claim text is required")
        if status not in CLAIM_STATUSES:
            add_issue(issues, "INVALID_CLAIM_STATUS", f"{path}.status", f"status must be one of {sorted(CLAIM_STATUSES)}")
        if status in {"supported", "verified"} and not evidence_ids:
            add_issue(issues, "CLAIM_EVIDENCE_REQUIRED", f"{path}.evidence_ids", f"{status} claims require evidence")
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_index:
                add_issue(issues, "UNKNOWN_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence: {evidence_id}")
        if (claim.get("claim_type") == "quantitative" or (nonempty_text(text) and re.search(r"\d", text))) and not conditions:
            add_issue(issues, "NUMERIC_CONDITIONS_REQUIRED", f"{path}.conditions", "numeric claims must record the conditions under which the value holds")

    for index, synthesis in enumerate(records["syntheses"]):
        path = f"syntheses[{index}]"
        source_ids = list(dict.fromkeys(string_list(synthesis, "source_ids", path, issues)))
        evidence_ids = list(dict.fromkeys(string_list(synthesis, "evidence_ids", path, issues)))
        dimensions = string_list(synthesis, "shared_dimensions", path, issues)
        agreements = string_list(synthesis, "agreements", path, issues)
        conflicts = string_list(synthesis, "conflicts", path, issues)
        if len(source_ids) < 2:
            add_issue(issues, "SYNTHESIS_SOURCE_COUNT", f"{path}.source_ids", "cross-study synthesis requires at least two sources")
        for source_id in source_ids:
            if source_id not in indexes["sources"]:
                add_issue(issues, "UNKNOWN_SOURCE", f"{path}.source_ids", f"unknown source: {source_id}")
        if not dimensions:
            add_issue(issues, "SYNTHESIS_DIMENSIONS_REQUIRED", f"{path}.shared_dimensions", "record at least one shared comparison dimension")
        if not agreements and not conflicts:
            add_issue(issues, "SYNTHESIS_RELATION_REQUIRED", path, "record at least one agreement or conflict")
        if not nonempty_text(synthesis.get("conflict_assessment")):
            add_issue(issues, "SYNTHESIS_CONFLICT_ASSESSMENT_REQUIRED", f"{path}.conflict_assessment", "state whether and why evidence conflicts")
        if not nonempty_text(synthesis.get("boundary")):
            add_issue(issues, "SYNTHESIS_BOUNDARY_REQUIRED", f"{path}.boundary", "state the applicability or comparability boundary")
        linked_sources: set[str] = set()
        for evidence_id in evidence_ids:
            evidence = evidence_index.get(evidence_id)
            if evidence:
                linked_sources.add(evidence.get("source_id"))
            else:
                add_issue(issues, "UNKNOWN_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence: {evidence_id}")
        if len(linked_sources.intersection(source_ids)) < 2:
            add_issue(issues, "SYNTHESIS_EVIDENCE_COVERAGE", f"{path}.evidence_ids", "synthesis evidence must cover at least two listed sources")

    for index, paragraph in enumerate(records["paragraph_contracts"]):
        path = f"paragraph_contracts[{index}]"
        claim_ids = string_list(paragraph, "claim_ids", path, issues)
        evidence_ids = string_list(paragraph, "evidence_ids", path, issues)
        contract_type = paragraph.get("contract_type", "content")
        if not nonempty_text(paragraph.get("job")):
            add_issue(issues, "PARAGRAPH_JOB_REQUIRED", f"{path}.job", "paragraph job is required")
        if contract_type not in {"content", "transition"}:
            add_issue(issues, "INVALID_PARAGRAPH_TYPE", f"{path}.contract_type", "contract_type must be content or transition")
        if contract_type == "content" and not claim_ids:
            add_issue(issues, "PARAGRAPH_CLAIMS_REQUIRED", f"{path}.claim_ids", "content paragraphs require at least one claim")
        if contract_type == "content" and not evidence_ids:
            add_issue(issues, "PARAGRAPH_EVIDENCE_REQUIRED", f"{path}.evidence_ids", "content paragraphs require evidence")
        for claim_id in claim_ids:
            if claim_id not in claim_index:
                add_issue(issues, "UNKNOWN_CLAIM", f"{path}.claim_ids", f"unknown claim: {claim_id}")
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_index:
                add_issue(issues, "UNKNOWN_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence: {evidence_id}")
        required_evidence = {
            evidence_id
            for claim_id in claim_ids
            for evidence_id in claim_index.get(claim_id, {}).get("evidence_ids", [])
            if evidence_id in evidence_index
        }
        missing_evidence = sorted(required_evidence - set(evidence_ids))
        if missing_evidence:
            add_issue(issues, "PARAGRAPH_EVIDENCE_GAP", f"{path}.evidence_ids", f"paragraph omits claim evidence: {missing_evidence}")

    for index, revision in enumerate(records["revision_items"]):
        path = f"revision_items[{index}]"
        status = revision.get("status")
        evidence_ids = string_list(revision, "evidence_ids", path, issues)
        if status not in REVISION_STATUSES:
            add_issue(issues, "INVALID_REVISION_STATUS", f"{path}.status", f"status must be one of {sorted(REVISION_STATUSES)}")
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_index:
                add_issue(issues, "UNKNOWN_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence: {evidence_id}")
        if status == "completed":
            if not nonempty_text(revision.get("action")):
                add_issue(issues, "REVISION_ACTION_REQUIRED", f"{path}.action", "completed revision needs the action actually taken")
            change_refs = revision.get("change_refs")
            if not isinstance(change_refs, list) or not change_refs:
                add_issue(issues, "REVISION_CHANGE_REF_REQUIRED", f"{path}.change_refs", "completed revision needs at least one artifact and location reference")
            else:
                for ref_number, ref in enumerate(change_refs):
                    ref_path = f"{path}.change_refs[{ref_number}]"
                    if not isinstance(ref, dict) or not nonempty_text(ref.get("artifact_id")) or not nonempty_text(ref.get("location")):
                        add_issue(issues, "INVALID_CHANGE_REF", ref_path, "change reference needs artifact_id and location")
            if not evidence_ids:
                add_issue(issues, "REVISION_EVIDENCE_REQUIRED", f"{path}.evidence_ids", "completed revision needs supporting or verification evidence")

    counts = {section: len(records[section]) for section, _ in SECTIONS}
    return {"verdict": "PASS" if not issues else "BLOCK", "bundle_id": data.get("bundle_id"), "counts": counts, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a structured source-to-revision research bundle")
    parser.add_argument("bundle", help="path to a JSON research bundle")
    args = parser.parse_args()
    path = Path(args.bundle).expanduser().resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"verdict": "BLOCK", "bundle": str(path), "issues": [{"code": "READ_ERROR", "path": "$", "message": str(exc)}]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    result = audit_bundle(data)
    result["bundle"] = str(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
