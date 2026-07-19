---
name: sci-review-system
description: >
  Build, audit, revise, translate, and prepare evidence-grounded SCI review
  manuscripts and their supporting research artifacts with explicit review protocols, uncertainty triage,
  human checkpoints, claim-evidence contracts, cross-literature synthesis,
  quantitative comparison audits, Chinese humanization, natural academic
  English, bilingual back-checking, figure/citation provenance, journal
  adaptation, reviewer audits, and submission packages. Use across scientific
  and engineering fields, with optional project profiles for domain-specific
  terminology, mechanisms, comparison dimensions, and quantitative conditions.
  Enter through the user's intent or an existing project checkpoint; do not
  require a fixed numbered sequence. Produce human-readable artifacts that do
  not depend on an AI session.
---

# SCI Review System

Use this skill as a non-linear research workspace, not as a numbered tutorial.
Treat the existing project files as evidence-bearing assets and produce
structured artifacts that a human researcher can read, audit, revise, and reuse
without this skill.

This is a human-led research and writing system, not a one-shot paper
generator. A model may accelerate retrieval, comparison, drafting, checking,
and packaging, but it may not replace the author's scientific judgment or turn
an unverified draft into a submission claim. Track the current maturity level:

| Level | Meaning | Prohibited claim |
| --- | --- | --- |
| `scaffold` | scope, structure, and open questions exist | research-backed |
| `research-backed` | actual searches and source-linked evidence exist | human-verified |
| `human-verified` | named human decisions and required re-audits exist | submission-ready |
| `submission-ready` | user-approved package and all applicable checks pass | submitted, unless the user actually submitted it |

## First action: recover the project

Before doing substantive work:

1. Read the repository `AGENTS.md` when it exists. Read
   `.codex/reading-session.md` only when repository policy enables an active
   reading anchor or the request continues paper-level reading.
2. Locate the project state, current baseline, active artifact, and relevant
   handoff files. If no state exists, propose a project-state file and a
   semantic project directory layout.
3. Scan only the files needed for the requested intent. Do not preload full
   texts. For paper-level work, locate a lawful local, online, database, or
   user-provided source and read only the necessary pages or sections. Preserve
   page, section, figure, table, or line anchors in evidence records. If the
   repository defines an active reading-anchor policy, follow and update it.
4. Show the entry dashboard before writing:

```text
【Intent】 what the user wants
【Recommended work unit】 name and reason
【Existing assets】 paths, versions, and gate states
【Missing prerequisites】 fields, evidence, or decisions
【Scope】 what this run will and will not do
【Proposed artifacts】 names, formats, and destinations
【Checks】 deterministic, independent, and human checks
```

If the request can be answered from existing artifacts, do not restart research.
Before any unit that depends on external access, run `capability-preflight`,
then replace passive `NOT_CHECKED` results with evidence-backed
`record-capability` records as access is actually tested. `Consensus` and
`scite` are optional enhancement routes; lack of either must never block the
core review when an equivalent source-verification route exists.

## Select the review protocol before research expands

When the task is a review rather than a local edit, identify the review type
before broad retrieval or prose drafting: `narrative`, `systematic`, `scoping`,
`critical`, `methodological`, `meta-analysis`, or `meta-synthesis`. If the user
has not chosen, propose a type with alternatives and consequences, then record
the decision in a versioned `review_protocol` artifact. The protocol binds the
research question, scope, eligibility, databases, date range, screening,
appraisal, synthesis, deviations, and reporting claims.

Do not call a review systematic because it has many references. Do not claim
PRISMA, registration, or meta-analysis unless the corresponding protocol and
records exist. Use `review-protocol` and `scope-and-eligibility` before
`search-provenance` when the review method is not already fixed.

## Work-unit model

Route to one or more semantic work units. The visible unit is a bounded
deliverable; internal roles may be parallelized when their write scopes do not
overlap.

| Intent | Work unit | Typical artifacts |
| --- | --- | --- |
| recover or inspect a project | `intake-recover` | state, asset index, baseline, handoff |
| define review method or eligibility | `review-protocol` / `scope-and-eligibility` | review protocol, inclusion/exclusion, reporting plan |
| narrow a topic or design a search | `scope-question` | RQ, scope snapshot, terminology, query plan |
| find, screen, read, or assess sources | `search-provenance` / `corpus-curation` / `lawful-reading` / `evidence-synthesis` | source records, reading notes, evidence ledger, conflict log |
| learn review/journal patterns | `benchmark-profile` | benchmark matrix, style profile, adaptation risks |
| design the argument | `argument-architecture` | information chain, section map, paragraph contracts |
| write or revise scientific content | `science-drafting` | science draft, equation/claim map, open checks |
| verify scientific content | `science-audit` | claim-evidence audit, numerical audit, repair list |
| make prose natural in Chinese or English | `language-naturalization` | revised prose, protected-span diff, change ledger |
| align Chinese and English | `bilingual-alignment` | alignment table, back-check report, drift list |
| check figures, citations, or rights | `visual-reference-qa` | figure manifest, citation map, rights ledger, mechanical report |
| simulate pre-submission review | `reviewer-audit` | reviewer report, action/evidence map, re-review |
| select a journal or prepare submission | `journal-fit` / `submission-package` | venue profile, user-directed package plan, check report |
| process an actual editor decision | `editorial-decision-intake` / `editorial-revision-loop` | verified decision, comment map, revised manuscript, response and re-audit |
| handle uncertainty or expert judgment | `uncertainty-triage` / `human-checkpoint` | uncertainty record, human question package, decision and resume plan |
| synthesize or compare studies | `review-synthesis` / `method-comparison` | synthesis blocks, comparison matrix, gap-to-question map |
| audit numbers, citations, or terminology | `quantitative-audit` / `citation-integrity` / `terminology-guard` | audit report, citation view, protected-span and stance report |
| pause or resume after a decision | `pause-resume` | pause record, affected units, re-audit and resume plan |

Use `pipeline` mode for a complete project and `checkpoint` mode for a direct
entry. Other modes include `audit_only`, `revision`, `translation`, and
`submission`. A mode is a routing choice, not a promise to skip prerequisites.

## Work-unit contract

Before execution, bind a contract containing:

- `work_unit_id`, purpose, mode, project id, baseline artifact and run id;
- allowed inputs, required outputs, and explicit non-goals;
- prerequisite gate states and permitted write paths;
- artifact naming, version, language, and status requirements;
- deterministic checks, independent review checks, and human decisions;
- failure conditions, fallback path, and handoff schema.

Write only to the current work-unit output or the project's designated
structured directory. Never overwrite a frozen baseline. Prefer a new version
with a `supersedes` relation.

Treat `work-units/unit-registry.json` as the sole routing and contract source.
Use `scripts/sci_review_runtime.py` for `capability-preflight`,
`record-capability`, `register-source`, `record-lookup`, `set-journal-status`,
`plan-reaudit`, `start-unit`, `register-artifact`, `record-decision`, `record-gate`,
`complete-unit`, and `handoff`. Never claim in
chat that a unit passed, completed, or handed off unless the runtime persisted
that transition. A blocked unit may use only a registered escalation handoff.
Only gates listed in the registry may block a runtime transition. Treat extra
agent-authored checks as advisory until they are mapped to a required gate; do
not stop or self-declare `PASS` because of an invented check.

At unit start, read the returned `required_quality_checks`. Record each listed
check id on the gate kind defined in the registry, with evidence bound to the
current artifact. A generic gate verdict without the required check ids cannot
complete the unit.

## Structured artifact rules

Every major Markdown artifact must have YAML frontmatter with at least:

```yaml
artifact_id: <stable-id>
project_id: <project-id>
artifact_kind: <kind>
work_unit: <work-unit-id>
status: working | candidate | reviewed | frozen | blocked | superseded
language: zh | en | bilingual | neutral
baseline_artifact: <path-or-null>
source_registry: <path-or-null>
run_id: <run-id>
gate_status: runtime-managed
next_intents: []
```

Use semantic directories such as `control/`, `scope/`, `sources/`, `evidence/`,
`reading/`, `argument/`, `visuals/`, `drafts/`, `reviews/`, `journal/`, `rights/`,
and `delivery/`. Put project run logs under `<project-root>/_runs/` and skill
development tests under `<skill-root>/res/`. Do not create `new/`, `misc/`, `latest/`, `final2/`, or other
ambiguous names. If the user does not name an artifact, generate a stable
`<kind>__<subject>__<variant>__<status>__v<semver>` name and state why.

Every major artifact must also remain operable without AI. Include concise
human-facing sections for purpose and scope, inputs and sources, method or
operations performed, confirmed conclusions, uncertainty and prohibited use,
manual next actions, and field or table definitions where relevant.

## Scientific integrity and project profiles

Never invent papers, DOI, data, results, permissions, mechanisms, or dynamic
journal facts. Mark unsupported content for uncertainty triage or human review.
Reviews may support taxonomy, history, and context; source experiments must
support source-specific quantitative claims.

The core skill is field-neutral. Match a profile only when it is explicitly
registered for the current project; do not infer domain knowledge from a
directory name or a keyword alone. Load only the selected profile, record its
id, version, path, and selection reason in project state, and use an explicit
null profile when no profile is active. A profile may define terminology,
mechanism layers, comparison dimensions, quantitative conditions, and
prohibited equivalences; it may not replace the review protocol, evidence
policy, uncertainty gate, or claim-evidence contract.

Use claim/evidence records rather than prose memory:

```text
claim -> type, strength, scope, exact sentence -> evidence[]
evidence -> source, page/figure/table, conditions, values, relation
```

## Natural-language and bilingual loop

Do not run a final “polish” that silently changes the science. Apply the loops
in this order:

```text
scientific clarity
-> science audit
-> Chinese naturalization (if needed)
-> English faithful draft
-> English naturalization (if needed)
-> bilingual back-check
-> residual style and citation audit
```

Protect numbers, units, formulas, citations, terminology, quoted text, source
attribution, conditions, and conclusion strength. Use context-sensitive rules,
not a banned-word replacement list. Preserve ordinary technical abstraction;
remove empty authority scaffolding, theatrical emphasis, translationese,
mechanical transitions, and generic AI closure. If a sentence is already clear,
keep it and record `no_change_needed`.

Every language pass emits a change ledger and compares protected spans,
numbers, formulas, citations, and stance markers with the baseline. If those
sets drift without an explicit scientific decision, block the handoff.

## Validation and handoff

Use the following loop for non-trivial work:

```text
writer or researcher
-> deterministic checks
-> independent verifier
-> adversarial reviewer
-> main-agent integration
-> affected checks again
```

Classify each check as `PASS`, `PASS_WITH_CONDITIONS`, `WARN`, `FAIL`,
`NOT_CHECKED`, or `BLOCK`.
Always report:

```text
【Delivered】 artifact paths and ids
【Changed】 added, modified, preserved
【Evidence】 sources, anchors, numbers, and conditions
【Gate】 verdicts and blocking reasons
【Human checks】 decisions the user must make
【Next intents】 valid follow-up work units and prerequisites
```

Use scripts for paths, schemas, links, hashes, citations, figures, numbers,
formula delimiters, and protected-span diffs. Use agents or human review for
scientific interpretation, evidence sufficiency, fairness of comparison, and
naturalness. Hooks are optional and default to read-only reminders/blocking;
the explicit script path must work when hooks are unavailable.

The bundled checks include `uncertainty_triage.py`, `resolve_checkpoint.py`,
`build_dashboard.py`,
`check_numbers_and_units.py`, `check_protected_spans.py`,
`check_citations.py`, `validate_artifacts.py`, and
`audit_research_bundle.py`. Use the last script when a structured research
bundle should prove the complete source-to-revision trace. A script can detect a
problem; it cannot make an expert judgment or turn a `BLOCK` into a `PASS`.

`check:*` text is never sufficient evidence for a required gate. External
research claims must cite registered `source:<id>` and `lookup:<id>` records;
actual artifacts, files, or human decisions must be hash- or id-bound. Any
operation that was not performed or could not be checked is `NOT_CHECKED`, not
`PASS` and not an omitted field.

The runtime initializer must not be pointed at the repository root or the skill
package by default. Use a named project output root; use `--allow-root-project`
only after the user explicitly requests root-level machine state.

## Optional journal, flexible package, and editor feedback

Record journal state as `not_selected`, `candidate`, or `confirmed`.
`not_selected` is a legitimate state: skip journal adaptation and make no
journal-specific claim. `candidate` permits exploration only. `confirmed`
requires a registered human decision and fresh official author-guideline and
submission-route sources before requirements become enforceable.

Do not impose a universal submission bundle. Build `package_plan` from a user
manifest, user template, or explicit user instruction; map available artifacts
to that plan, report missing or unresolved items, and validate the assembled
package against the same basis. The user owns the final package shape, login,
payment, legal declarations, and Submit action. A package with unperformed
required checks remains `NOT_CHECKED` and cannot complete as submission-ready.

Keep simulated review separate from actual editorial correspondence. An
`editorial-decision-intake` requires the real received letter or message as a
registered primary source plus human confirmation. Map every editor and
reviewer comment separately to affected claims/sections, planned and completed
changes, supporting evidence, and the audits that must be rerun. The
`editorial-revision-loop` may prepare Chinese or English correspondence, but AI
drafting, human approval, and human sending are distinct states. Without a real
letter or revised manuscript, provide strategy only and never claim a formal
response is ready.

## Uncertainty is a first-class state

Do not complete a claim merely because the user expects prose. Classify each
important claim as `verified`, `supported`, `uncertain`, or
`human_review_required`. The last two states must remain visible in the claim
ledger and may block only the affected claim/unit rather than the whole project.

Create an `uncertainty_record` when a source is missing or abstract-only, a
number lacks page/figure/table, units, or conditions, papers conflict, a
mechanism or causal relation must be inferred, a recent result exceeds the
verified cutoff, methods are incomparable, terminology/formulas are ambiguous,
or the decision depends on expert, lab-internal, or mentor knowledge.

For `human_review_required`, stop the affected assertion and generate a
`human_checkpoint` containing the question, source text/judgment, evidence,
conflict, known boundary, non-self-judgment, suggested expert, affected claims,
baseline version, and resume plan. Do not write a generic “please confirm”. A
human answer unblocks only the listed claims and must trigger the listed
re-audits.

## Synthesize before you summarize

Cross-literature prose must explain shared comparison dimensions, what problem a
method solves, what new burden or limitation it introduces, why results differ,
and which evidence supports the resulting gap or research question. Do not use
paper order or chronology as a substitute for synthesis. Distinguish literature
facts, cross-paper synthesis, author interpretation, technical inference,
unverified hypothesis, and future recommendation.

Before comparing quantitative results, run `quantitative-audit` and retain the
study object or population, method or exposure, input and output definitions,
measurement conditions, metric and units, sample or dataset, protocol, split,
reference standard, uncertainty, confounders, bias, leakage risk, and the
comparability boundary. Load any additional domain conditions and prohibited
equivalences from the active project profile. Never treat a review summary as
the source experiment for a source-specific numerical claim.

## Pause, resume, and re-audit

When a checkpoint blocks work, record which unit and claims are affected, what
can continue independently, who must decide, which artifact is the recovery
baseline, and which audits must be rerun. A resolved checkpoint does not reopen
the whole project automatically; route only the affected units and then update
the handoff and state.

After any material change to protocol, scope, sources, evidence, claims,
numbers, structure, language, citations, visuals, journal/package basis, or an
editorial response, run `plan-reaudit` in preview mode. Apply the plan only after
the change scope is correct. Applying a plan marks only previously completed
affected units as `re_audit_required`; historical gates remain preserved as
evidence but cannot stand for the changed material.

## Collaboration

When the user has authorized delegation and the task supports independent
deliverables, assign bounded roles such as research architect, literature
scout, evidence auditor, structure architect, science writer, Chinese
humanizer, English naturalizer, figure/reference QA, and adversarial reviewer.
Each role writes only its own work-unit output. The main agent alone merges a
formal manuscript or changes a frozen scientific baseline. Never treat several
agents agreeing as evidence of truth.

## Progressive disclosure

Read only the references needed for the active work unit:

- optional project profiles and comparison boundaries:
  `project-profiles/index.json`, then the explicitly selected
  `project-profiles/<profile>.md`;
- review method and eligibility: `references/review-methodology.md`;
- evidence, uncertainty, and reading policy: `references/evidence-policy.md`,
  `references/source-obligation-and-capabilities.md`,
  `references/uncertainty-escalation.md`, and
  `references/reading-anchor-policy.md`;
- synthesis, comparison, and paragraph structure: `references/review-synthesis.md`,
  `references/quantitative-audit.md`, `references/argument-blueprint.md`, and
  `references/paragraph-contract.md`;
- citation and terminology integrity: `references/citation-integrity.md` and
  `references/terminology-policy.md`;
- structure and handoff: `references/argument-blueprint.md` and
  `references/collaboration-safety.md`;
- Chinese/English naturalization: `references/writing-zh-human.md`,
  `references/writing-en-natural.md`, and `references/bilingual-backcheck.md`;
- figures, journals, and submission: `references/figure-provenance.md`,
  `references/journal-adaptation.md`, and
  `references/optional-journal-and-package-policy.md`;
- actual editor decisions and correspondence:
  `references/editorial-feedback-loop.md` and the Chinese/English templates
  under `assets/templates/`.

Use the JSON schemas and scripts under the skill directory as executable
contracts. Do not load the old numbered documents as a default context.
