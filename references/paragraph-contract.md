# Review paragraph contract

Use this contract for non-IMRaD reviews and for local chapter/section entry.

```yaml
paragraph_id: P-001
problem: "本段要回答的问题"
core_claim: "本段主要主张"
method_or_concept: "涉及的方法/概念"
representative_evidence: [E-001]
evidence_boundary: "材料、条件、范围、冲突"
interface_previous: "上一段交付什么"
interface_next: "本段交给下一段什么"
must_not_claim: ["不能提前声称的结论"]
language_stage: science_baseline | zh_naturalization | en_faithful | en_naturalization
```

One paragraph should have one main job. Multiple agents may propose packages,
but the integrator must rebuild transitions, terminology, evidence strength,
and the relationship between paragraphs before promotion to a manuscript.

