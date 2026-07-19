# SCI Review System

**把一次次容易丢上下文的科研对话，变成可恢复、可检查、可交接的综述工作区。**

[中文介绍](#中文介绍) | [English](#english)

## 中文介绍

SCI Review System 是一套面向 SCI 综述研究与写作的 Codex 技能和可执行运行时。它把选题、检索、筛选、精读、证据整理、跨文献综合、框架设计、科学写作、中文自然化、英文写作、引用核查、图表管理、期刊适配和编辑反馈处理，组织成 28 个可以独立进入的工作单元。

这套系统适合从零开始，也适合接手已经做到一半的项目。你可以拿着一个模糊选题进来，也可以直接交给它一份文献库、精读笔记、章节草稿或编辑决定信。它会先识别现有材料和当前阶段，再决定下一步，不要求每次都从固定流程的第一步重来。

第一版已经不只是一组提示词。仓库里包含状态机、来源记录、JSON Schema、质量门、人工确认点、哈希校验、可恢复交接和自动评测。研究者可以随时查看它依据了什么、改了什么、哪些结论还不能写、下一步需要谁来判断。

> 这是一个由研究者主导的科研写作系统。它可以承担大量整理、比较、起草和检查工作，但不会代替作者判断，也不会承诺录用、投稿成功或任何期刊结果。

### 它解决什么问题

- **聊天结束，研究资产还在。** 项目状态、来源、主张、证据、决定、质量门和交接记录都写入可读文件，不依赖某一次对话的记忆。
- **已有项目不用推倒重来。** 系统按意图和现有资产进入合适的工作单元，可以从选题、文献、草稿、润色、返修等任意阶段继续。
- **引用不是装饰。** 关键主张需要关联具体来源和页码、章节、图表或行号；数字还要保留单位、条件、样本和比较边界。
- **证据不够时会停。** 缺全文、论文互相冲突、实验条件不可比、结论需要专家判断时，系统会记录不确定性并生成明确的人工核验问题。
- **润色不能偷偷改科学含义。** 中文“说人话”、英文忠实稿、英文自然稿和双语回查分开处理，数字、公式、引用、术语、否定、条件和结论强度都受保护。
- **系统只承认做过的检查。** 没有执行的外部检索、期刊核验或文件检查记为 `NOT_CHECKED`，不会因为文字写得像完成了就变成 `PASS`。

### 主要特性

#### 1. 从任意阶段接入

运行时会扫描当前项目状态、基线文件、活动产物和交接记录，再选择合适的工作单元。完整项目可以使用 `pipeline`，已有材料可以从 `checkpoint`、`revision`、`translation`、`audit_only` 或 `submission` 模式进入。

#### 2. 先定综述方法，再扩展检索

系统区分 narrative、systematic、scoping、critical、methodological、meta-analysis 和 meta-synthesis。研究问题、纳入排除标准、数据库、时间范围、筛选方式、质量评价和综合方法会进入版本化研究协议，避免“参考文献很多，所以就是系统综述”这种常见误判。

#### 3. 主张和证据单独管理

科学正文不会只存在于段落里。系统把重要内容拆成可追溯记录：

```text
claim -> 类型、强度、范围、原句 -> evidence[]
evidence -> 来源、页码/图表、条件、数值、支持或冲突关系
```

这样可以双向检查：正文里的高风险判断是否有证据，已经整理的关键证据是否被正确使用。

#### 4. 跨文献综合，而不是逐篇复述

系统要求先建立共同的比较维度，再说明每类方法解决了什么问题、增加了什么代价、为什么不同研究会得出不同结果，以及这些差异能否支持研究空白。定量比较还会检查实验对象、输入输出、测量条件、指标定义、数据划分、真值、混杂因素和数据泄漏风险。

#### 5. 不确定性是正式状态

每个重要判断可以标记为 `verified`、`supported`、`uncertain` 或 `human_review_required`。需要导师、同门或领域专家判断时，系统会记录原文、已有证据、冲突、影响范围和恢复计划，不用一句含糊的“请确认”把问题推回给作者。

#### 6. 中文、英文和科学底稿分层

语言处理遵循下面的顺序：

```text
科学清晰化
-> 科学审计
-> 中文自然化
-> 英文忠实稿
-> 英文自然化
-> 中英文回查
-> 残留风格与引用检查
```

中文稿可以去掉模板腔、翻译腔、机械过渡和空泛收尾；英文稿会处理语法、句序、名词化、被动堆叠和不自然连接。任何语言改动都不能把 `may` 写成 `proves`，也不能把相关关系改成因果关系。

#### 7. 来源和工具能力先核验

需要联网、数据库、PDF、DOCX、Zotero 或其他外部能力时，系统先运行 capability preflight。每次外部查找都会记录问题、实际查询、访问路径、时间、返回来源和结果。搜索摘要和 AI 总结只能用于发现线索，不能替代原始来源。

#### 8. 期刊和投稿包按需启用

期刊状态分为 `not_selected`、`candidate` 和 `confirmed`。没有目标期刊时，项目可以继续写作和审计；确认期刊后，只有最新的官方作者指南和投稿系统信息才能成为硬约束。投稿包由用户给出的模板、清单或明确要求决定，系统不会擅自规定一套“所有期刊都适用”的文件列表。

#### 9. 区分模拟审稿和真实编辑反馈

预投稿审查可以用于找漏洞，但不会冒充期刊编辑意见。进入正式返修流程前，必须登记真实的决定信或投稿系统消息，保留文件哈希和锚点，并逐条映射编辑、审稿人、稿件修改和重新审计结果。AI 可以起草回复，作者负责确认和发送。

#### 10. 可执行的质量门

第一版包含：

- 28 个语义工作单元；
- 17 份 JSON Schema；
- 14 项合同与鲁棒性评测；
- 来源、查找、能力、人工决定、文件哈希和交接记录；
- 数字与单位、引用、protected spans、产物结构和不确定性检查脚本。

工作单元只有在必需产物和质量门都满足时才能完成。文件在检查后被修改，原来的通过状态会失效；未完成的单元也不能直接跳到不允许的后续阶段。

### 适合谁用

- 正在准备综述、学位论文相关工作或研究计划的研究生；
- 需要整理大量跨方法、跨实验条件文献的研究人员；
- 已经有草稿，但引用、数字、结构和语言版本逐渐失控的项目；
- 需要把中文科学稿转成自然英文，同时保留科学含义的作者；
- 收到编辑或审稿意见，需要建立“意见—修改—证据—回复”对应关系的团队。

核心规则不绑定具体学科。仓库额外提供柔性曲面超声检测项目档案，用来约束该领域的物理层次、方法比较条件和常见错误等价关系。

### 安装为 Codex Skill

建议使用 Python 3.10 或更高版本。

PowerShell：

```powershell
git clone https://github.com/fishcold789/sci-review-system.git "$HOME\.codex\skills\sci-review-system"
python -m pip install -r "$HOME\.codex\skills\sci-review-system\requirements.txt"
```

Bash：

```bash
git clone https://github.com/fishcold789/sci-review-system.git ~/.codex/skills/sci-review-system
python -m pip install -r ~/.codex/skills/sci-review-system/requirements.txt
```

安装后重新加载 Codex。可以按自然语言触发，也可以明确指定：

```text
Use $sci-review-system to recover this review project and continue from the
appropriate checkpoint.
```

### Runtime 快速开始

请在单独的科研项目目录中初始化状态，不要把运行状态写进 skill 仓库：

```powershell
python scripts/sci_review_runtime.py init ..\my-review `
  --project-id my-review `
  --title "My SCI Review" `
  --intent "Recover the project and define the next evidence-backed work unit"
```

查看项目状态：

```powershell
python scripts/sci_review_runtime.py inspect ..\my-review
```

查看全部命令：

```powershell
python scripts/sci_review_runtime.py --help
```

### 验证

运行仓库自带的合同与鲁棒性检查：

```powershell
python evals/run_evals.py
```

当前评测覆盖工作单元转换、产物合同、来源和查找义务、质量门证据、人工决定、哈希完整性、不确定性恢复、可选期刊、用户控制的投稿包和真实编辑来源要求。

### 仓库结构

```text
SKILL.md             Codex 执行规则和路由入口
agents/              Codex 界面元数据
assets/templates/    中英文编辑往来模板
evals/               合同与鲁棒性评测
hooks/               可选的只读运行时 hooks
orchestration/       意图路由规则
project-profiles/    可选的领域科学约束
references/          按需加载的政策与写作参考
schemas/             JSON Schema 合同
scripts/             运行时和确定性检查脚本
work-units/          语义工作单元注册表
```

完整执行合同见 [SKILL.md](SKILL.md)。

## English

SCI Review System is an evidence-grounded Codex skill and executable runtime
for planning, building, revising, and auditing scientific review manuscripts.
It turns research conversations into a recoverable workspace with explicit
artifacts, sources, decisions, uncertainty states, quality gates, and handoffs.

The system supports both new and existing projects. It can start from a rough
topic, a curated corpus, reading notes, a manuscript draft, or an actual editor
decision. Instead of forcing every project through a numbered tutorial, it
routes the current intent and available assets to one of 28 semantic work units.

This first public version is more than a prompt collection. It includes a state
runtime, source and lookup records, 17 JSON Schemas, hash-bound artifacts,
human checkpoints, controlled transitions, and 14 contract and robustness
checks. Researchers can inspect what was used, what changed, what remains
uncertain, and what must happen next without relying on chat history.

> SCI Review System is human-led. It can accelerate research organization,
> comparison, drafting, language revision, and verification, but it does not
> replace scientific judgment or promise acceptance, submission success, or
> any journal outcome.

### What It Handles

- review protocol selection and eligibility design;
- research-question refinement and reproducible source records;
- lawful, anchored reading at page, section, figure, table, or line level;
- claim-evidence ledgers with conditions, conflicts, and uncertainty;
- cross-literature synthesis and bounded quantitative comparison;
- argument blueprints, paragraph contracts, and evidence-backed drafting;
- science, citation, terminology, formula, figure, rights, and number audits;
- plain scientific Chinese, faithful English, natural academic English, and
  bilingual meaning-preservation checks;
- optional journal adaptation and user-directed submission packaging;
- separate workflows for simulated review and real editor/reviewer feedback.

### Design Highlights

#### Enter At The Right Checkpoint

Use `pipeline` for a complete project, or enter through `checkpoint`,
`revision`, `translation`, `audit_only`, or `submission` when reusable assets
already exist. The runtime inspects state and prerequisites before starting a
work unit.

#### Evidence Before Claims

Important statements are represented as traceable claim-evidence records:

```text
claim -> type, strength, scope, exact sentence -> evidence[]
evidence -> source, page/figure/table, conditions, values, relation
```

The system checks both directions: high-risk prose must point to evidence, and
high-risk evidence must show where it is used or why it remains unused.

#### Uncertainty Can Stop A Claim

Claims may be `verified`, `supported`, `uncertain`, or
`human_review_required`. Missing sources, incompatible experiments, ambiguous
mechanisms, conflicting papers, and expert-only decisions produce structured
uncertainty records and focused human checkpoints instead of polished guesses.

#### Language Revision Cannot Rewrite The Science

Chinese humanization, faithful English drafting, English naturalization, and
bilingual back-checking are separate passes. Numbers, units, equations,
citations, terms, attribution, negation, conditions, and claim strength remain
protected. A fluent translation that drops a limitation still fails.

#### External Checks Must Actually Run

Capability preflight and lookup records distinguish `PASS`, `FAIL`, and
`NOT_CHECKED`. Search snippets and model summaries are discovery aids, not
final evidence. Journal-specific rules become enforceable only after the user
confirms a venue and current official sources are registered.

#### Real Editorial Feedback Has Its Own Workflow

Pre-submission critique remains separate from actual editor correspondence.
Formal revision work requires the received decision letter or portal message,
a frozen manuscript baseline, atomic comment mapping, evidence-linked changes,
re-audits, and human approval before any response is ready to send.

### Install As A Codex Skill

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

Reload Codex, then invoke the skill by intent or explicitly:

```text
Use $sci-review-system to recover this review project and continue from the
appropriate checkpoint.
```

### Runtime Quick Start

Initialize state in a named research project directory, not in this skill
repository:

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

List all runtime commands:

```powershell
python scripts/sci_review_runtime.py --help
```

### Validation

Run the bundled contract and robustness checks:

```powershell
python evals/run_evals.py
```

The current suite covers semantic work-unit transitions, artifact contracts,
source and lookup obligations, gate evidence, human decisions, hash integrity,
uncertainty recovery, optional journal handling, user-directed package plans,
and real editorial source requirements.

### Repository Layout

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
