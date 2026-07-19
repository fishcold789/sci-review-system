# Optional journal adaptation and template-driven submission packaging

This policy separates three decisions that must not be conflated: choosing a
journal, adapting a manuscript to verified journal requirements, and arranging
files for submission. Journal selection is optional. Packaging is controlled by
the user's requested shape rather than by a universal file list.

## Non-negotiable rules

- Record the journal status as `not_selected`, `candidate`, or `confirmed`.
- Never turn memory, convention, a search snippet, or another journal's rules
  into a target-journal requirement.
- A missing or unperformed check is `NOT_CHECKED`, never `PASS`.
- The user owns the final package shape and performs account login, legal
  declarations, payment, and the final submission action.
- The system may organize, map, rename, convert, render, and check files only
  within the package plan authorized by the user.

## Journal status contract

### `not_selected`

This is a valid state, not a failure. Record why selection is being deferred and
continue with journal-neutral research, drafting, audit, or revision. Journal
adaptation is skipped. Outputs must not say that author guidelines, submission
fields, limits, templates, fees, indexing, or policies were checked. A package
may still be arranged from a user manifest or template, but it must be labelled
generic rather than journal-compliant.

### `candidate`

Candidate journals may be explored and compared. Observations may guide a
question list or a provisional estimate, but they are non-binding and cannot
become gates, hard limits, automated rewrites, or claims of compliance. Keep the
requirements in exploratory mode. Third-party sources may support discovery but
do not establish an official rule.

### `confirmed`

Confirmation is a recorded user decision identifying one target journal. Before
journal-specific adaptation or compliance claims, capture current official
sources for at least the author guidelines and the submission system. Each
source record must include its URL, source type, official authority, access
date, freshness evaluation, and the facts extracted from it. Other dynamic
requirements, such as article type, length, abstract, figures, references,
anonymization, declarations, data policy, AI disclosure, fees, and file formats,
must be tied to the official page on which they were found.

A stale, inaccessible, contradictory, or freshness-unknown source cannot support
a hard constraint. Resolve it, request human confirmation, or downgrade the
profile to exploratory use. Do not infer facts that an official source does not
state.

## Freshness and provenance

Freshness is evaluated at use time, not merely when a link is first recorded.
The venue profile records a maximum acceptable source age and the evaluation
basis. Recheck dynamic requirements close to packaging because journal pages
and submission systems change. Preserve access dates and the exact facts used
so a later audit can distinguish an old rule from a current one.

## Package authority

Every package plan starts from one or more user-authorized bases:

- a manifest supplied or confirmed by the user;
- a directory or naming template supplied or confirmed by the user; or
- explicit user instructions describing the desired package.

The plan maps source artifacts into that requested shape. It may add validation
rules drawn from a confirmed venue profile, but those rules do not silently add,
remove, or reorder deliverables. If a publisher template conflicts with the
user's package instruction, report the conflict and ask for a decision rather
than choosing on the user's behalf.

There is intentionally no universal mandatory list of manuscript, cover letter,
highlights, declarations, figures, supplementary files, or source files. Such
items appear only when the user's basis or a verified confirmed-journal rule
requires them.

## Check semantics

Package checking is deterministic where possible and evidence-bearing:

- `PASS`: the check ran against the stated target and evidence supports it.
- `FAIL`: the check ran and found a mismatch or missing requirement.
- `NOT_CHECKED`: the check did not run, could not access its target, lacked a
  trustworthy rule, or could not produce verifiable evidence.

An overall `PASS` requires every reported check to be `PASS`. Any `FAIL` makes
the overall result `FAIL`. With no failures, one or more `NOT_CHECKED` results
make the overall result `NOT_CHECKED`. A report with no checks is also
`NOT_CHECKED`.

The package check report is advisory until the user reviews the planned shape,
resolves failures and unchecked items, and confirms the final package. The
system must never claim that a package was submitted.

