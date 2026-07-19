# Editorial feedback to manuscript loop

Use this workflow only for correspondence actually received from a journal editor
or submission system. Treat simulated editorial review as pre-submission critique,
not as editor feedback.

## Non-negotiable boundaries

- Require the original decision email, letter, or submission-portal export. Preserve
  its path, hash, language, received time, and a stable content anchor.
- Keep editor comments separate from reviewer comments. Preserve reviewer grouping
  and the original order; do not merge similar comments before recording them.
- Do not invent missing comments, deadlines, manuscript identifiers, or editorial
  intent. Mark ambiguous passages for human clarification.
- Without confirmed real correspondence, provide only general revision strategy.
  Do not create or claim a formal point-by-point response.
- Without an actual revised manuscript, provide only a change plan and response
  strategy. Do not use completion wording such as "we revised" or "has been added."
- AI may classify, map, edit, and draft. A human author verifies the interpretation,
  scientific changes, declarations, addressees, attachments, and final send action.
- Sending email, uploading files, accepting legal terms, and pressing Submit remain
  human actions.

## Required records

Create an editorial decision record conforming to
`schemas/editorial-decision.schema.json`. It records whether the source is missing,
unverified, or actually received; only the last state with a confirmed authenticity
check can make a formal-response workflow eligible.

After the source is confirmed, create a comment map conforming to
`schemas/editorial-comment-map.schema.json`. Use one row per atomic request:

```text
original comment and source anchor
  -> origin: editor or reviewer N
  -> affected claims and baseline sections
  -> planned action and evidence needed
  -> completed change and revised-manuscript anchors
  -> point-by-point response
  -> relevant re-audits and their evidence
```

Do not treat a response sentence as proof that the manuscript changed. The completed
change must point to the revised artifact and exact section, paragraph, table, figure,
or line anchor. When no manuscript change is proposed, record the scientific or
editorial reason and make the response respectful and evidence-based.

## Execution sequence

1. **Authenticate intake.** Save the received artifact, compute its hash, capture a
   stable anchor, and have a human confirm that it is real correspondence for this
   manuscript. Extract the decision label and deadline without interpreting beyond
   the text.
2. **Freeze the baseline.** Record the manuscript version and hash that the decision
   concerns. Never apply comments to an unidentified or moving baseline.
3. **Atomize without losing hierarchy.** Separate editorial, administrative, and
   reviewer requests. Split compound comments into atomic records while retaining a
   shared parent identifier and original wording.
4. **Map impact before editing.** Link every request to claims, sections, figures,
   tables, references, supplementary items, declarations, or package items. Record
   `none` explicitly when a request is purely administrative.
5. **Plan the response.** Choose change, clarification, justified no-change,
   clarification request, or another explicit disposition. State the evidence and
   checks required before completion.
6. **Implement against one controlled candidate.** Only the integration owner edits
   the formal manuscript candidate. Record actual change anchors and evidence after
   the edit exists.
7. **Re-audit affected surfaces.** Re-run the checks affected by each change, such as
   evidence scope, citations, numbers and units, cross-section consistency, figures,
   terminology, language, declarations, journal requirements, and package integrity.
   A required check that could not run is `NOT_CHECKED`, never `PASS`.
8. **Draft the response from the map.** Quote or faithfully paraphrase the comment,
   answer it directly, describe only completed changes, and give precise revised-text
   anchors. Keep planned work in future tense.
9. **Human approval.** The corresponding author reviews the full response, revised
   manuscript, tracked/clean versions, attachments, deadlines, authorship, and legal
   statements. Record approval before marking the response ready to send.
10. **Record the outcome.** Author approval is not delivery. Only after the human
    sends or uploads may `delivery_status` become `sent_by_human`; preserve the
    receipt reference and exact submitted package fingerprint.

## Re-audit selection

Apply audits according to impact rather than using a ceremonial fixed checklist.

| Change | Minimum relevant re-audits |
| --- | --- |
| Scientific claim or interpretation | evidence scope, contradiction, logic, citation |
| Number, equation, or unit | source anchor, calculation, units, cross-text consistency |
| Method or eligibility criterion | reproducibility, protocol deviation, affected results |
| Figure or table | data provenance, caption, in-text references, numbering, accessibility |
| Added or removed citation | identity, support relation, bibliography consistency |
| Language-only edit | meaning preservation, terminology, protected numbers/citations |
| Journal or administrative request | current official requirement and package consistency |

An audit is `NOT_APPLICABLE` only with a reason. `NOT_CHECKED` blocks readiness when
the audit is required. If a change creates a new scientific uncertainty, route it
through the system's uncertainty and human-checkpoint process before replying.

## Communication templates

Use `assets/templates/editor-letter-zh.md` or
`assets/templates/editor-letter-en.md` as a starting point. Select only the needed
block and delete irrelevant text. The templates cover decision receipt, revised
submission, status inquiry, and optional transfer, appeal, or withdrawal messages.
They are aids, not mandatory package shapes or permission to send.

For cross-language correspondence, draft in the editor's working language when it is
known, then retain a human-reviewed Chinese or English counterpart for internal
checking. Prefer short factual sentences. Do not translate a stronger claim than the
source or the revised manuscript supports.
