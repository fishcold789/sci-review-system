# Bilingual back-check

Compare Chinese and English at both sentence and claim level. The check is a
semantic integrity gate, not a fluency score.

## Required comparisons

- claim set and section purpose;
- observation, interpretation, recommendation, and causal strength;
- modal verbs, negation, uncertainty, and limitations;
- numbers, ranges, units, precision, sample counts, and thresholds;
- terms, abbreviations, author attribution, citations, figures, and equations;
- experimental conditions, comparison baseline, dataset split, and scope.

`MATERIAL_DRIFT` in numbers, negation, causality, responsibility, scope, or
citations is `BLOCK`. `MINOR_DRIFT` requires human confirmation. A fluent
translation that drops a limitation still fails.

The output must contain: sentence/claim alignment, drift records, affected
artifact ids, repair recommendations, and a gate verdict. Re-run the check
after any language repair or reviewer-driven revision.

