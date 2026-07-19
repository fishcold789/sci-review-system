# Collaboration and write-scope safety

Use subagents only for bounded, independently verifiable work. Give each role
the minimum artifact context and an explicit output schema. Do not share a
writer's diagnosis with an independent verifier when blind checking matters.

## Safe parallel work

- independent literature searches or metadata normalization;
- evidence extraction for different papers or sections;
- figure manifest and citation-link checks;
- separate language audits on non-overlapping sections;
- adversarial review after a baseline is frozen.

## Sequential work

- scope and research-question freeze;
- evidence freeze before science drafting;
- main-agent integration of distributed paragraph packages;
- science audit before language naturalization;
- bilingual back-check after English rewriting;
- final rights and submission gate.

Every role writes to its own work-unit output or run directory. Never allow two
roles to edit the same formal manuscript concurrently. The main agent alone
merges and promotes a candidate into a frozen artifact.

