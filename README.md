# SCI Review System

An evidence-grounded, auditable Codex skill for planning, building, revising,
and checking SCI review manuscripts.

SCI Review System is a human-led research and writing workspace. It can enter
an existing project at the appropriate checkpoint instead of forcing every
project through a fixed numbered pipeline. Its runtime records artifacts,
sources, decisions, gates, uncertainty, and handoffs so that the work remains
readable and reusable outside an AI session.

This is the first public version. It is not a one-shot paper generator, does
not replace scientific judgment, and does not promise journal acceptance or
submission outcomes.

## Core Capabilities

- select and record narrative, systematic, scoping, critical, methodological,
  meta-analysis, or meta-synthesis review protocols;
- narrow research questions and build reproducible source records;
- preserve page, section, figure, table, and line-level evidence anchors;
- connect scientific claims to evidence, conditions, conflicts, and uncertainty;
- synthesize literature across shared comparison dimensions instead of listing
  papers one by one;
- design argument blueprints, paragraph contracts, and evidence-backed drafts;
- audit quantitative comparability, citations, terminology, formulas, figures,
  rights, and conclusion strength;
- produce plain scientific Chinese, natural academic English, and bilingual
  meaning-preservation reports;
- support optional journal adaptation, user-directed submission packaging, and
  real editor/reviewer feedback loops without claiming actions that were not
  performed.

The core is field-neutral. The repository includes an optional project profile
for flexible curved-surface ultrasonic inspection.

## Install As A Codex Skill

Python 3.10 or later is recommended.

PowerShell:

```powershell
git clone https://github.com/fishcold789/sci-review-system.git "$HOME\.codex\skills\sci-review-system"
python -m pip install -r "$HOME\.codex\skills\sci-review-system\requirements.txt"
```

Bash:

```bash
git clone https://github.com/fishcold789/sci-review-system.git ~/.codex/skills/sci-review-system
python -m pip install -r ~/.codex/skills/sci-review-system/requirements.txt
```

Restart or reload Codex after installation, then invoke the skill by intent or
explicitly:

```text
Use $sci-review-system to recover this review project and continue from the
appropriate checkpoint.
```

## Runtime Quick Start

Initialize state in a named project directory, not in this skill repository:

```powershell
python scripts/sci_review_runtime.py init ..\my-review `
  --project-id my-review `
  --title "My SCI Review" `
  --intent "Recover the project and define the next evidence-backed work unit"
```

Inspect the resulting state:

```powershell
python scripts/sci_review_runtime.py inspect ..\my-review
```

The runtime also supports capability preflight, source and lookup registration,
work-unit routing, artifact registration, human decisions, gate recording,
completion, and controlled handoff. Run the command help for the complete list:

```powershell
python scripts/sci_review_runtime.py --help
```

## Validation

Run the bundled contract and robustness checks:

```powershell
python evals/run_evals.py
```

The checks cover semantic work-unit transitions, artifact contracts, source and
lookup obligations, gate evidence, human decisions, hash integrity, uncertainty
recovery, optional journal handling, flexible package plans, and real editorial
source requirements.

## Repository Layout

```text
SKILL.md             Codex execution instructions and routing policy
agents/              Codex interface metadata
assets/templates/    Chinese and English editorial correspondence templates
evals/               Contract and robustness checks
hooks/               Optional read-only runtime hooks
orchestration/       Intent routing rules
project-profiles/    Optional domain-specific scientific constraints
references/          On-demand policies and writing references
schemas/             JSON Schema contracts
scripts/             Runtime and deterministic checks
work-units/          Semantic work-unit registry
```

See [SKILL.md](SKILL.md) for the complete operating contract.
