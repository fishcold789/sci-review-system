# Quantitative and technical comparison audit

Never compare numbers across papers before checking comparability. For each
comparison record the study object or population, method/intervention/exposure,
input and output definitions, measurement conditions, metric definition and
units, sample or dataset, protocol, data split, reference standard, uncertainty,
confounders, bias, and possible leakage. Add domain-specific conditions from the
active project profile rather than hard-coding one field's variables here.

The audit must distinguish missing information from a negative result. Missing
conditions produce `uncertain` or `human_review_required`, not an assumed match.

Generic forbidden equivalences:

```text
surrogate metric     != target outcome without validation
statistical change   != practical or clinical significance
association          != causation
benchmark gain       != out-of-domain robustness
review summary       != original experimental result
```

Output a comparison table, comparability verdict, missing-condition list,
metric/ground-truth notes, data-leakage check, and a bounded wording proposal.
