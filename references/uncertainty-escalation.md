# Uncertainty triage and human escalation

The skill must know when not to continue. Uncertainty is a structured state,
not a vague disclaimer at the end of a paragraph.

## Evidence states

| State | Meaning | Permitted action |
| --- | --- | --- |
| `verified` | Reliable source and precise anchor support the statement | write as a bounded fact |
| `supported` | Evidence supports it but scope, strength, or conditions are limited | use qualified wording and preserve limits |
| `uncertain` | Source, conditions, interpretation, or inference is incomplete | do not write as settled fact |
| `human_review_required` | Expert judgment, conflict, novelty, or high-risk interpretation is needed | create checkpoint and pause affected claim |

## Mandatory escalation triggers

Escalate when the source is missing or abstract-only; a number lacks page,
figure/table, units, or conditions; papers conflict; a physical mechanism or
causal relation must be inferred; a latest result is beyond the verified
cutoff; methods are compared under incompatible conditions; a term, formula,
algorithm, setting, internal lab practice, or expert judgment is unclear; or a
claim would change a high-stakes conclusion.

For `human_review_required`, stop the affected assertion and create a
`human_checkpoint` containing the question, source text/judgment, evidence,
conflict, known boundary, suggested expert, affected claims, baseline version,
and resume plan.

## Human question package

```text
问题：
需要核验的原文或判断：
已有证据：
冲突/不确定性：
模型可以确定的部分：
不能自行判断的部分：
建议请教对象：导师 / 同门 / 领域专家
核验结果：
核验日期：
影响的主张、章节和产物：
恢复时使用的基线版本：
```

Do not ask the user to “确认一下” without this package. A human decision
unblocks only the listed claims and downstream units; it does not silently
validate unrelated assertions.
