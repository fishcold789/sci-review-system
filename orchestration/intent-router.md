# Intent router

The router converts a user's request and existing artifacts into a bounded
work-unit plan. It never asks the user to remember an old number and never
assumes that a missing artifact is complete merely because a previous chat
mentioned it.

## Route algorithm

1. Classify the request as `pipeline`, `checkpoint`, `audit_only`,
   `translation`, `revision`, or `submission`.
2. Scan the project state, active artifact, handoffs, and relevant semantic
   directories. Do not scan PDFs unless the selected unit requires a named or
   explicitly requested paper.
3. Match the user's verbs, object, language, and artifact type to
   `work-units/unit-registry.json`.
4. If the task is review-level and no confirmed review protocol exists, route
   through `review-protocol` before broad retrieval or drafting. If a request
   contains uncertainty signals, route through `uncertainty-triage` before
   language smoothing or synthesis.
5. Check required inputs and gate states. Distinguish:
   - `ready`: all required inputs and gates exist;
   - `degradable`: a bounded output is possible with explicit warnings;
   - `blocked`: a missing source, decision, or permission prevents honest work.
   Before externally dependent units, record the capability preflight. A
   passive or unavailable check is `NOT_CHECKED`; Consensus and scite are
   optional enhancement routes and must have an equivalent fallback.
6. Propose a semantic artifact name and destination. Apply it unless the user
   requests a different name or an existing artifact would be superseded.
7. Show the entry dashboard, then execute only the selected unit(s).
8. Write the artifact manifest, gate results, event, uncertainty/checkpoint
   records, and handoff. Show the completion dashboard and valid next intents.

## Routing examples

| User request | Route | Important boundary |
| --- | --- | --- |
| “从现有资料开始做完整综述” | `pipeline` → `intake-recover` → `review-protocol` → `scope-question` → `evidence-synthesis` → `argument-architecture` → `science-drafting` | Do not restart assets that pass their gates |
| “我要写一篇系统综述” | `checkpoint` → `review-protocol` → `scope-and-eligibility` | Do not claim systematic methods before the protocol is confirmed |
| “把这篇论文的 Fig. 7 讲清楚” | `checkpoint` → `lawful-reading` | Read only the named source/pages needed; preserve anchor when repository policy requires it |
| “检查第三章数字和引用” | `audit_only` → `quantitative-audit` + `citation-integrity` | Produce audit reports before editing prose |
| “两篇论文结论冲突，帮我判断” | `audit_only` → `uncertainty-triage` → `human-checkpoint` | Do not choose a winner without comparable evidence or expert input |
| “比较哪种方法更好” | `audit_only` → `method-comparison` → `quantitative-audit` | Require condition/metric comparability before ranking |
| “把这段中文写成自然英文” | `translation` → `language-naturalization` | Require science baseline or mark missing evidence; protect LaTeX and claims |
| “模拟审稿人 2 会怎么批评” | `revision` → `reviewer-audit` | This is pre-submission simulation, not actual correspondence |
| “我收到编辑决定信，按它修改” | `revision` → `editorial-decision-intake` → `editorial-revision-loop` | Require the actual letter; map editor/reviewer comments separately and rerun affected audits |
| “准备投稿材料，期刊还没定” | `submission` → `submission-package` | Keep venue `not_selected`; follow the user's manifest/template and make no journal-compliance claim |
| “准备投到已确认期刊” | `submission` → `journal-fit` → `submission-package` | Verify fresh official author/submission requirements; user controls package shape and performs login/payment/Submit |

## Dashboard contract

Before execution, output:

```text
【Intent】...
【Mode】pipeline | checkpoint | audit_only | translation | revision | submission
【Recommended unit】...
【Detected assets】...
【Prerequisites】ready / degradable / blocked
【Will read】...
【Will not read】...
【Proposed artifacts】name + destination + format
【Checks】...
【Human decisions】...
```

After execution, output the same unit id, artifacts, changes, evidence anchors,
gate verdicts, unresolved questions, and next intents. Keep complete machine
fields in the project files rather than dumping JSON into the conversation.
