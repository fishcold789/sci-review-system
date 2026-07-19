# Chinese scientific humanization

Use only after the scientific baseline is stable or explicitly mark the input
as unverified. The target is plain, precise academic Chinese, not chatty prose.

## Order

1. Detect scene and scope: `structural`, `bounded`, or `in-place`.
2. Freeze protected spans: numbers, units, formulas, citations, terminology,
   source attribution, conditions, limitations, and responsibility.
3. Make scientific clarity edits: identify the true subject and action, separate
   observation from interpretation, and keep modal strength.
4. Remove template signals only when they carry no information: empty openers,
   value inflation, narrator commentary, translationese, mechanical transitions,
   and empty conclusions.
5. Run a fidelity reread, then a residual-style reread.

Do not mechanically replace a banned-word list. Preserve ordinary technical
abstraction and normal academic passive constructions when they are clearer.
If the input is already natural, emit `NO_CHANGE_NEEDED` and retain it.

## Unsourced authority

Use `rewrite-safe` only when the authority phrase can be removed without losing
the claim; use `audit-only` for scientific documents with missing attribution;
use `rewrite-with-placeholder` only when the user explicitly asks to preserve
the structure. Never invent a source.

## Required output

Return the revised artifact, a JSONL modification ledger, protected-span diff,
and a `PASS/WARN/BLOCK` language gate. Language review is not evidence review.

