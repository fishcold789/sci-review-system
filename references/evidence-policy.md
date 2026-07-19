# Evidence and claim policy

## Claim record

Every important statement should be representable as:

```yaml
claim_id: C-001
text: "..."
claim_type: definition | mechanism | comparison | numeric | limitation | gap
strength: observed | supported | suggests | established
scope: "population-or-system/method-or-exposure/dataset/protocol/condition"
evidence_ids: [E-001]
do_not_upgrade: true
status: verified | conditional | needs-human-check | rejected
```

## Evidence record

```yaml
evidence_id: E-001
source_id: S-001
anchor: "PDF p. 9, Fig. 7"
evidence_kind: original-experiment | review | method | guideline
quote_or_paraphrase: "..."
conditions: "..."
values: "..."
relation: supports | contradicts | partial | insufficient
```

## Non-negotiable rules

- Do not invent bibliographic metadata, DOI, page, result, or permission.
- Do not use a citation as evidence unless the cited source supports the exact
  claim and scope.
- Keep numerical values attached to units and conditions.
- Preserve disagreement instead of averaging incompatible studies.
- Use `[需要人工核查]` or the structured `needs-human-check` status when the
  source, value, or interpretation is incomplete.
- Language rewriting may not change claim strength, scope, or attribution.

## Audit direction

Audit both directions: every high-risk sentence must point to claim/evidence;
every high-risk evidence record must show where it is used or why it remains
unused. A missing link is a warning or block depending on claim severity.
