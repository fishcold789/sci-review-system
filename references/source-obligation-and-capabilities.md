# Source obligations and capability preflight

Use this policy whenever a work unit depends on facts outside the project. It
applies to scientific claims, bibliographic metadata, journal instructions,
submission rules, and citation-context judgments.

## 1. Non-negotiable boundary

- Do not convert memory, model knowledge, a plausible URL, or an agent-written
  checklist into proof that an external lookup occurred.
- Record each lookup attempt and every source used. A conclusion without an
  attributable record is `NOT_CHECKED`, not `PASS`.
- Treat search snippets and AI summaries as discovery leads. Open the source
  needed for the claim before using it as evidence.
- If a required check cannot run, state the limitation and either use an
  approved fallback or block the dependent work unit.
- Never infer access to a login, subscription, API, browser session, or local
  application merely because that capability normally exists.

## 2. Source authority

Assign one authority level in `source-record.schema.json`:

| Level | Meaning | Typical use |
| --- | --- | --- |
| `A_OFFICIAL_PRIMARY` | First-party rule, standard, registry, journal site, or submission portal | Journal and submission requirements; official definitions |
| `A_SCHOLARLY_PRIMARY` | Original scholarly report or dataset | Methods, observations, and study-specific results |
| `B_SCHOLARLY_SYNTHESIS` | Review, meta-analysis, consensus statement, or scholarly handbook | Field synthesis and discovery of primary studies |
| `B_TRUSTED_METADATA` | Curated bibliographic/indexing record | DOI, title, venue, author, and indexing checks |
| `C_DISCOVERY_ONLY` | Search result, snippet, recommendation, or machine-generated lead | Discovery only; not final claim evidence |
| `U_UNVERIFIED` | User-provided or otherwise unverified material | Leads or explicitly qualified provisional work |

Authority is purpose-dependent. Only an official journal source can establish
current author instructions. An original paper can establish what that study
reports, but not a field-wide consensus by itself. A review can synthesize a
field, but should not silently replace its cited primary source for a precise
numeric claim.

Record peer-review state separately. A preprint remains a primary source, but
its `review_status` must not be upgraded to `peer_reviewed`.

## 3. Access date and freshness

Every online, API, or database record must include `accessed_at`. Classify its
freshness:

- `volatile`: journal instructions, submission portals, fees, deadlines,
  editorial contacts, indexing status, software/API behavior, and live metrics.
- `current`: bibliographic metadata and other records that can be corrected.
- `stable`: published article content, archived standards, and versioned files.
- `historical`: deliberately time-bounded evidence retained for provenance.

Set a project-specific `max_age_days` for `volatile` and `current` sources.
Do not invent a universal number. A freshness check is:

- `PASS`: the source was observed within policy and the relevant page/version
  is identifiable.
- `FAIL`: it is older than policy, contradicted by a newer official source, or
  the referenced content is no longer present.
- `NOT_CHECKED`: no fresh observation or no executable way to verify it.

Stable scientific content does not become false merely because it is old.
Freshness assesses whether the record still represents the intended version;
scientific recency and relevance are separate review-design questions.

## 4. Lookup obligation

Create a lookup record before treating an external check as complete. Specify:

1. the question and why it is required;
2. the planned capability and source-authority floor;
3. the actual query or navigation action;
4. time of execution and access route;
5. returned source IDs and an external trace or artifact reference;
6. `PASS`, `FAIL`, or `NOT_CHECKED`, with a reason.

`PASS` means the lookup actually ran and yielded enough attributable evidence
for its stated question. `FAIL` means it ran but failed its acceptance rule.
`NOT_CHECKED` means it did not run, could not be observed, or produced no
verifiable trace. An agent-authored `check:*` statement alone is not an
external trace.

Journal-specific obligations may be skipped only while venue status is
explicitly `not_selected`. Once a journal is confirmed, its current official
author guidance and submission route become required lookups.

## 5. Capability preflight

Run preflight before a work unit promises external operations. Assess at least:

- network access;
- an operable browser or equivalent page-retrieval route;
- scholarly databases or search services required by the review protocol;
- PDF discovery, opening, text extraction, and page-level anchoring;
- DOCX reading/writing when DOCX is an expected input or deliverable;
- Zotero or another declared reference manager when library synchronization or
  export is promised;
- Consensus academic search, if selected as an enhancement;
- scite Smart Citations or citation-context inspection, if selected as an
  enhancement.

Capability state meanings:

- `READY`: the required operation was exercised successfully in this
  environment, or a validated equivalent route is ready.
- `DEGRADED`: only a documented fallback is available, or a non-critical
  enhancement is unavailable. State what remains possible.
- `BLOCKED`: a required operation has no acceptable route; dependent work must
  stop or be narrowed by an explicit human decision.

Each preflight check has its own `PASS`, `FAIL`, or `NOT_CHECKED` result.
`NOT_CHECKED` never contributes positive evidence of readiness. Do not report
an overall `READY` state while any required capability is `NOT_CHECKED`,
`DEGRADED`, or `BLOCKED`.

## 6. Consensus and scite

Consensus and scite are optional evidence-enhancement capabilities, not
mandatory APIs and not substitutes for reading sources.

- Use Consensus, when available, to improve scholarly discovery and to expose
  candidate evidence. Verify important claims against the underlying paper.
- Use scite, when available, to inspect citation contexts and whether later
  literature reports supporting, contrasting, or mentioning relationships.
  Treat these labels as context signals, not final truth judgments.
- Never assume authenticated API access or an active subscription. Check the
  actual route first.
- Allowed fallbacks include an accessible browser workflow, user-assisted
  export, another scholarly index, and manual citation-context inspection.
- If either service is unavailable, mark that capability `DEGRADED` or
  `BLOCKED` according to whether it was optional for this run. Preserve the
  core review route when equivalent evidence work remains possible.

## 7. Fail-closed decision rule

For every dependent work unit:

1. If all required lookups are `PASS` and their sources meet authority and
   freshness rules, continue.
2. If a lookup is `FAIL`, correct or replace it before continuing.
3. If a required lookup is `NOT_CHECKED`, use an approved fallback; otherwise
   block the unit and expose the missing check.
4. If only an optional enhancement is unavailable, continue in `DEGRADED`
   mode and record the omitted benefit.
5. Never promote `DEGRADED`, `BLOCKED`, `FAIL`, or `NOT_CHECKED` to `PASS`
   through prose, confidence, or experience.

