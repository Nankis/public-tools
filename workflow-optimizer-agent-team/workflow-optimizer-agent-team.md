# 工作流评估与优化 Agent Team

## 目标

建立一个可复用的 agent team，用来读取任意工作流，做结构审计、压测实验、对照比较，并输出可执行的优化方案。核心不是让流程变得更“规范”，而是让工作流持续变轻、可运行、可衡量、可自动化。

这个团队默认反对三类膨胀：

- 上下文膨胀：说明、规则、模板、历史材料越堆越多，agent 每次都被迫读全量。
- Harness 膨胀：测试/门禁/模板过重，限制 agent 判断力，导致为了流程而流程。
- 自动化不足：重复人工步骤太多，agent 不能直接读、跑、比、改。

## 设计原则

1. 先测量再优化：没有 baseline 的“优化”只算主观整理。
2. 先裁剪再增强：优先删掉无效上下文、重复步骤和伪门禁。
3. 小 team，大闭环：角色数量控制在 5-7 个，避免 agent team 本身变成新负担。
4. 用任务样本压测，而不是只读文档评价。
5. 优化方案必须能回归验证：不能只给建议，要能比较优化前后效果。

## Team 架构

### 1. Orchestrator / 评估调度官

职责：

- 接收目标工作流路径、任务样本和优化目标。
- 拆分评估任务，分配给其他 agent。
- 维护一次评估运行的状态文件。
- 最终合并审计、实验、优化建议和回归结果。

不做：

- 不亲自改写全部流程。
- 不凭直觉给结论。

核心产物：

- `run.json`
- `final-report.md`
- `optimization-backlog.md`

### 2. Workflow Cartographer / 工作流制图员

职责：

- 读取目标工作流的全部入口文件、规则、模板、脚本和示例。
- 画出实际执行路径：输入、步骤、分支、人工节点、输出物、依赖。
- 标出“agent 每次必须读”和“只在特定场景读取”的内容。

重点发现：

- 重复规则
- 过期规则
- 隐含依赖
- 步骤循环
- 人工决策点
- 可以懒加载的上下文

核心产物：

- `workflow-map.md`
- `context-inventory.json`

### 3. Context Auditor / 上下文成本审计员

职责：

- 估算工作流运行所需 token、文件数量、规则数量、样例数量。
- 区分启动上下文、按需上下文、归档上下文。
- 识别高成本低收益内容。

关键指标：

- `startup_context_tokens`：启动时必须读的 token。
- `total_available_context_tokens`：全量可读上下文 token。
- `context_reuse_ratio`：多次任务中真正复用的上下文比例。
- `dead_context_ratio`：读了但没有影响输出的上下文比例。
- `instruction_conflict_count`：互相冲突或重复的规则数量。

核心产物：

- `context-audit.md`
- `context-budget.json`

### 4. Harness Critic / 测试框架反脆弱审计员

职责：

- 判断现有 harness 是帮助 agent 变强，还是把 agent 绑死。
- 检查门禁是否对应真实风险。
- 找出“形式正确但产出变差”的流程约束。

重点问题：

- 哪些检查应该自动化？
- 哪些检查应该降级成抽样？
- 哪些规则阻碍 agent 自主判断？
- 哪些模板导致输出千篇一律？
- 哪些验收标准只是在制造 token 消耗？

核心产物：

- `harness-audit.md`
- `gate-risk-matrix.md`

### 5. Experiment Runner / 对照实验员

职责：

- 用同一批任务样本分别跑 baseline 和候选优化版。
- 记录运行时间、上下文读取量、步骤数、失败点、产物质量。
- 尽量使用真实任务，不只用 toy case。

实验类型：

- A/B：原流程 vs 优化流程。
- Ablation：删除某个规则/模板/门禁后看结果是否变差。
- Stress：给复杂输入、残缺输入、长上下文输入，看是否失控。
- Replay：用历史任务复跑，验证结果是否稳定。

核心产物：

- `experiments/*.jsonl`
- `comparison-report.md`

### 6. Workflow Surgeon / 工作流外科医生

职责：

- 基于审计和实验结果提出最小改动方案。
- 将工作流拆成启动核心、按需模块、归档材料、自动化脚本。
- 输出可直接应用的改写 patch 或新版本草案。

优化手段：

- 合并重复规则。
- 删除低价值模板。
- 将长文档改为索引 + 按需读取。
- 将人工 checklist 改成脚本检查。
- 将宽泛流程改成任务分级。
- 将大而全 harness 改成风险触发门禁。

核心产物：

- `proposed-workflow-vNext.md`
- `patch-plan.md`
- `migration-notes.md`

### 7. Regression Judge / 回归裁判

职责：

- 对优化版做最终验收。
- 防止为了省 token 把质量、省略风险控制或关键知识删掉。
- 给出是否合并的判断。

验收维度：

- 成本是否下降。
- 成功率是否不低于 baseline。
- 产物质量是否不低于 baseline。
- 自动化程度是否提升。
- 复杂任务是否仍有足够自由度。
- 新流程是否更容易被下一个 agent 理解。

核心产物：

- `regression-verdict.md`
- `merge-decision.json`

## 对抗与辩护机制

有必要加入“对抗比较”和“原工作流辩护”，但不建议把它们做成默认常驻 agent。原因很简单：这个 team 的目标是反臃肿，如果再固定增加很多审判型角色，最后会变成新的复杂 harness。

推荐做成两个按需触发的模式。

### Workflow Defender / 原工作流辩护人

触发时机：

- Surgeon 准备删除高风险门禁、事实核验、质量验收规则时。
- Candidate 计划删除超过 20% 的启动规则时。
- Candidate 删除了有历史失败案例支持的规则时。
- 优化方案主要来自“省 token”而不是“提升完成率”时。

职责：

- 站在原工作流作者视角，为现有设计辩护。
- 解释某些复杂度当初可能是在防什么风险。
- 找出“看起来冗余，但在边界场景有价值”的规则。
- 指出优化版可能损害质量、风格、安全或可复现性的地方。

输出：

- `defense-brief.md`

必须回答：

- 这个被删除/降级的部分原本解决什么问题？
- 有没有历史失败案例证明它有价值？
- 如果删掉，最可能在哪类任务上出事？
- 能否改成按需触发，而不是完全删除？

### Red Team Comparator / 对抗比较员

触发时机：

- Baseline 和 candidate 指标差距不明显时。
- Candidate 在质量上有争议时。
- 工作流面向高风险任务、长期复用任务或生产交付任务时。

职责：

- 故意寻找 candidate 优化方案的失败场景。
- 用边界样本、复杂样本、信息缺失样本压测 baseline 和 candidate。
- 判断优化是否只是“把问题藏起来”，而不是真正解决。

输出：

- `red-team-comparison.md`

必须比较：

- baseline 哪些地方虽然慢但稳？
- candidate 哪些地方虽然快但脆？
- 两者在复杂任务、异常输入、长上下文任务上的表现差异。
- 是否存在“平均成本下降，但尾部风险上升”的情况。

### 触发规则

默认不触发对抗机制。满足任一条件时触发：

- 样本数少于 5 个，但结论准备进入合并或标准化。
- 工作流属于高风险、长期复用或生产交付流程。
- 计划删除超过 20% 的启动规则。
- 计划移除任何安全、事实核验、质量验收相关门禁。
- Candidate token 成本下降超过 40%。
- Baseline 成功但 candidate 失败任一任务样本。
- Candidate 输出质量评分低于 baseline。
- Candidate 质量评分方差上升。
- Edge sample、long-context sample 或 incomplete-input sample 失败。
- Orchestrator 或 Regression Judge 对结论没有把握。

### 决策权重

Defender 和 Red Team 不能直接否决优化方案，但它们的反对意见必须进入 Regression Judge 的最终判断。

推荐规则：

- 如果 Defender 证明某个复杂度对应真实高频风险，优先改成按需触发，不直接删除。
- 如果 Red Team 发现尾部风险明显上升，不能 merge，只能 `merge_with_guardrail` 或 `retry`。
- 如果原工作流无法证明某个复杂度的真实价值，可以删除或归档。

## 跨模型复跑机制

有必要用不同模型跑两轮及以上，但它应该是验证层，不是每次都默认全量执行。原因是工作流优化有一个隐藏风险：某个流程可能只适配某个模型的习惯，看起来效果很好，换一个模型就失效。反过来，某个流程可能太繁琐，强模型能绕过去，弱模型却被束缚得更严重。

### 适用场景

满足任一条件时，建议触发跨模型复跑：

- 工作流会长期复用，并准备沉淀成 Skill、团队标准或自动化模板。
- Baseline 与 candidate 的差距不明显。
- Baseline 与 candidate 的质量方差上升。
- Candidate 主要通过减少上下文或降低门禁获得收益。
- 任务依赖复杂推理、长上下文、多步工具调用或创意判断。
- 你怀疑当前结论只是某个模型的偏好。

### 推荐模型组合

至少跑两类模型：

- Strong model：用于判断工作流在高智能模型下是否释放能力。
- Smaller/Faster model：用于判断工作流是否足够清晰、稳健、低成本。

可选第三类：

- Different-family model：用于检查流程是否过度绑定某个模型供应商或提示风格。

### 复跑规则

同一批任务样本必须保持一致：

- 相同输入。
- 相同可用文件。
- 相同工具权限。
- 相同验收标准。
- 分别运行 baseline 和 candidate。

不要只比较最终答案。必须记录：

- 是否完成任务。
- 是否需要额外澄清。
- 是否走错流程。
- 是否误读规则。
- 是否过度依赖模板。
- 是否能自主跳过无关步骤。
- 成本、耗时、质量和失败模式。

### 输出

- `model-comparison-report.md`
- `model-runs/*.jsonl`

建议字段：

```json
{
  "model": "strong-or-fast-model-name",
  "workflow_version": "baseline|candidate",
  "task_id": "sample-001",
  "completed": true,
  "quality_score": 4,
  "estimated_context_tokens": 12000,
  "round_trips": 3,
  "failure_mode": null,
  "notes": "Candidate skipped irrelevant archived examples correctly."
}
```

### 判断标准

跨模型结果按下面方式解释：

- Strong 和 smaller model 都变好：高置信 merge。
- Strong 变好、smaller 变差：流程可能依赖强模型补洞，需要补清晰度或保留 guardrail。
- Strong 变差、smaller 变好：流程可能过度模板化，限制强模型发挥。
- 不同模型结论相反：不能直接 merge，进入 Red Team Comparator 或扩大样本。
- 只有成本下降但质量分歧变大：不能视为稳定优化。

### 运行频率

默认策略：

- 日常小改：单模型 + Regression Judge 即可。
- 中等改动：两模型、每个至少 1 轮。
- 重大重构：两模型以上、每个至少 2 轮，必要时加入不同模型家族。

这能防止把“某个模型刚好会处理”误判成“工作流真的优秀”。

## 运行模式

为了防止优化 team 自身膨胀，评估必须先选择运行模式。

### audit_only

只做静态审计，不生成 candidate。适合初次了解陌生 workflow、只想知道上下文成本、文件结构和潜在臃肿点，或暂时没有真实任务样本。

输出：`run.json`、`context-inventory.json`、`workflow-map.md`、`metrics-summary.json`。

### single_candidate_eval

默认 MVP 模式。只生成 1 个候选优化方案，用 3-5 个任务样本跑 baseline/candidate 单模型对比。

预算限制：最多 1 个候选方案、默认 3 个样本、默认 1 轮复跑、不默认触发跨模型复跑。

结论限制：3 个样本最多输出 `proceed_to_pilot`、`revise` 或 `reject`。正式 `merge` 至少需要 5 个样本，且覆盖 easy / typical / edge / long-context / incomplete-input 中至少 3 类。

### full_eval

完整评估模式，包含 Defender、Red Team 和跨模型复跑。适合准备沉淀成 Skill/标准工作流/自动化模板、候选方案删除高风险门禁、baseline/candidate 结论接近、高风险或生产交付流程。

## 测量协议

第一版必须把指标分成三类，避免把主观判断伪装成硬数据。

### 自动采集

- `startup_files_count`
- `startup_estimated_tokens`
- `total_files_count`
- `total_estimated_tokens`
- `markdown_files_count`
- `headings_count`
- `rule_like_lines_count`
- `checklist_items_count`
- `template_markers_count`
- `file_size_bytes`
- `mtime`

### 运行记录

- `workflow_version`
- `task_id`
- `model`
- `started_at`
- `ended_at`
- `duration_seconds`
- `completed`
- `files_read_count`
- `tool_calls_count`
- `manual_clarifications_count`
- `failure_mode`
- `blocked_by_harness_count`
- `unnecessary_gate_count`
- `skipped_irrelevant_steps_count`

### LLM/人工评分

- `quality_score_1_5`
- `critical_errors`
- `risk_missed`
- `usable_without_rework`
- `harness_limited_intelligence`
- `notes`

`dead_context_ratio`、`context_reuse_ratio`、`agent 自主性` 这类指标可以保留，但第一版只能作为 Judge 的定性字段，不作为硬性 merge 条件。

## Runner Contract

为了避免“自称实验过”，每次运行必须有固定目录和可复跑文件。

推荐目录：

```
runs/workflow-optimizer/YYYY-MM-DD-HHMM-<workflow-name>/
  run.json
  task-samples.jsonl
  context-inventory.json
  workflow-map.md
  metrics-summary.json
  experiments/
    experiment-runs.jsonl
    comparison-report.md
  candidate/
    workflow/
    proposed-workflow-vNext.md
    patch-plan.md
  judge/
    judge-rubric.json
    regression-verdict.md
    merge-decision.json
```

Candidate 必须写入 run 目录或临时副本，禁止直接覆盖原 workflow。只有 Regression Judge 给出可合并结论后，才允许生成 patch plan 或由人工决定是否应用。

### task-samples.jsonl

每行一个任务样本，必填字段：`task_id`、`type`、`input`、`acceptance_criteria`、`risk_level`。`type` 使用 easy / typical / edge / long-context / incomplete-input。

### experiment-runs.jsonl

每行一次 baseline 或 candidate 运行记录，必填字段：`task_id`、`workflow_version`、`model`、`completed`、`duration_seconds`、`estimated_context_tokens`、`files_read_count`、`quality_score_1_5`、`critical_errors`、`risk_missed`、`usable_without_rework`、`failure_mode`。

### merge-decision.json

必须包含：`decision`、`confidence`、`reason`、`required_next_steps`。MVP 的 3 样本评估默认不能直接给 `merge`，最多给 `proceed_to_pilot`。

## 标准运行流程

### Phase 0. Intake

输入：

- `workflow_path`：目标工作流目录或文件。
- `task_samples`：3-10 个真实任务样本。
- `optimization_goal`：例如降 token、提自动化、降复杂度、提升成功率。
- `risk_level`：low / medium / high。

输出：

- 运行 ID。
- 状态目录。
- 初始假设。

建议目录：

```
runs/workflow-optimizer/YYYY-MM-DD-HHMM-<workflow-name>/
```

### Phase 1. Baseline Read

Workflow Cartographer 读取现状，产出地图。
Context Auditor 统计上下文成本。
Harness Critic 审查门禁和约束。

这一阶段禁止修改工作流。

### Phase 2. Baseline Experiment

Experiment Runner 用任务样本跑原流程，记录：

- 是否完成
- 完成时间
- 读了哪些文件
- 大致 token 消耗
- 人工介入次数
- 输出质量评分
- 失败和卡顿点

### Phase 3. Diagnosis

Orchestrator 合并审计结论，输出问题列表。

问题按优先级分类：

- P0：导致失败或严重浪费。
- P1：高频消耗，明显可优化。
- P2：可读性/维护性问题。
- P3：暂不处理的风格或偏好问题。

### Phase 4. Optimization Draft

Workflow Surgeon 只提出 1-3 个候选方案：

- Conservative：最小裁剪，不改变核心流程。
- Balanced：重组上下文 + 自动化部分检查。
- Aggressive：重新拆分 workflow/skills/scripts/harness。

每个方案必须说明：

- 删除什么
- 保留什么
- 延迟加载什么
- 自动化什么
- 预期收益
- 潜在风险

如果候选方案涉及删除关键规则、降低门禁或大幅减少上下文，触发 Workflow Defender 产出 `defense-brief.md`。

### Phase 5. Candidate Experiment

Experiment Runner 对候选方案复跑同一批任务样本。

必须和 baseline 对比：

- token 变化
- 耗时变化
- 成功率变化
- 质量变化
- agent 自主性变化
- 维护复杂度变化

如果 baseline 与 candidate 质量差距不明显，或 candidate 更快但更脆，触发 Red Team Comparator 产出 `red-team-comparison.md`。

如果该工作流会长期复用并准备沉淀成 Skill/标准流程，或实验结论依赖单一模型表现，触发跨模型复跑，产出 `model-comparison-report.md`。

### Phase 6. Regression Verdict

Regression Judge 给结论：

- merge：可以合并。
- merge_with_guardrail：可以合并，但必须保留某些保护。
- retry：需要继续实验。
- reject：优化损害质量或风险过高。

如果存在 `defense-brief.md` 或 `red-team-comparison.md`，Regression Judge 必须逐条回应其中的核心反对意见。
如果存在 `model-comparison-report.md`，Regression Judge 必须说明最终结论是否跨模型稳定。

### Phase 7. Final Report

最终报告必须包含：

- 当前工作流地图。
- 主要臃肿来源。
- baseline 指标。
- 候选优化方案。
- A/B 对比结果。
- 推荐合并方案。
- 后续观察指标。

## 评估指标

### 成本指标

- 启动读取文件数
- 启动 token 估算
- 全量 token 估算
- 平均任务 token 估算
- 重复上下文比例
- 死上下文比例

### 效率指标

- 完成时间
- agent 往返轮数
- 人工介入次数
- 失败重试次数
- 输出物数量
- 中间文件数量

### 质量指标

- 任务完成度
- 事实准确性
- 交付物可用性
- 风格一致性
- 边界条件处理
- 是否遗漏关键风险

### 智能化指标

- agent 是否能自主选择路径
- 是否被模板限制表达
- 是否能跳过无关步骤
- 是否能在异常输入下自救
- 是否能提出比流程更好的做法

## 推荐状态文件协议

```json
{
  "run_id": "2026-05-26-1225-example",
  "workflow_path": "path/to/workflow",
  "goal": "reduce_context_and_complexity",
  "status": "running",
  "phase": "baseline_experiment",
  "agents": {
    "orchestrator": {"status": "running", "artifact": "final-report.md"},
    "cartographer": {"status": "done", "artifact": "workflow-map.md"},
    "context_auditor": {"status": "done", "artifact": "context-audit.md"},
    "harness_critic": {"status": "done", "artifact": "harness-audit.md"},
    "experiment_runner": {"status": "running", "artifact": "comparison-report.md"},
    "workflow_surgeon": {"status": "pending", "artifact": "proposed-workflow-vNext.md"},
    "regression_judge": {"status": "pending", "artifact": "regression-verdict.md"}
  },
  "metrics": {
    "baseline": {},
    "candidate": {},
    "delta": {}
  },
  "decision": null
}
```

## 最小可运行版本

第一版不要一次性实现完整系统。建议先做轻量 CLI + 4 个逻辑角色：

1. Orchestrator
2. Cartographer + Context Auditor
3. Experiment Runner
4. Regression Judge

Surgeon 和 Regression Judge 可以由同一个执行环境串联，但判断权必须隔离：Surgeon 只提出 candidate，Regression Judge 只能读取 baseline/candidate 产物和固定 rubric，不能把 Surgeon 的自我辩护当作主要证据。

第一版只要求能完成：

- 读取一个 workflow 目录。
- 生成上下文清单。
- 用 3 个任务样本跑 baseline，结论最多到 `proceed_to_pilot`。
- 提出 1 个优化版。
- 复跑并对比。
- 输出 final report。

第一版先落地 `AI工作区/AI超级个体/tools/workflow-optimizer/`：实现 `audit`、`init-samples`、`compare` 三个命令，再逐步接入 agent prompt。

## Agent Prompt 草案

### Orchestrator

```
你是工作流优化调度官。你的任务是评估一个 agent workflow 是否过度臃肿、上下文成本是否过高、harness 是否限制 agent 智能，并组织其他 agent 产出可验证的优化方案。

输入包括 workflow_path、task_samples、optimization_goal、risk_level。

你必须按阶段推进：baseline read -> baseline experiment -> diagnosis -> optimization draft -> candidate experiment -> regression verdict -> final report。

不要凭感觉下结论。每个建议都必须连接到观察证据、实验结果或明确的风险判断。
```

### Cartographer + Context Auditor

```
你是工作流制图和上下文审计 agent。读取目标 workflow 的入口、规则、模板、脚本、样例和历史材料，画出实际执行路径，并估算哪些内容是启动必读、按需读取、归档参考或可删除内容。

重点找出重复、冲突、过时、低收益高成本、以及可以懒加载的上下文。

输出 workflow-map.md、context-inventory.json、context-audit.md。
```

### Experiment Runner

```
你是工作流对照实验 agent。你必须用同一批任务样本分别运行 baseline 和候选优化版，记录完成情况、耗时、文件读取、上下文规模、失败点、人工介入次数和输出质量。

不要只看文档评价。必须通过任务样本观察流程实际表现。

输出 experiments/*.jsonl 和 comparison-report.md。
```

### Surgeon + Regression Judge

```
你是工作流外科医生和回归裁判。你的目标是用最小必要改动降低上下文成本和流程复杂度，同时不损害关键质量、风险控制和 agent 自主性。

优先策略：删除重复规则、拆分启动核心和按需模块、把机械 checklist 自动化、把大而全 harness 改成风险触发门禁。

你必须给出是否合并的明确结论：merge、merge_with_guardrail、retry 或 reject。
```

## 默认优化策略库

### 上下文瘦身

- 把长工作流拆成 `README.md` + `modules/*.md`。
- README 只保留目标、入口、最小步骤和模块索引。
- 大样例移到 `examples/`，只在需要时读取。
- 历史复盘移到 `archive/`，不进入启动上下文。
- 用“触发条件”替代“每次都读”。

### Harness 降复杂度

- 高风险检查保留为强门禁。
- 中风险检查改为抽样或任务等级触发。
- 低风险检查改为 checklist 或后置提醒。
- 形式检查交给脚本。
- 主观质量判断交给 regression judge，而不是写死模板。

### 自动化升级

- 文件结构检查脚本化。
- token/文件数量统计脚本化。
- 输出物存在性检查脚本化。
- 对照实验记录 JSONL 化。
- final report 模板化，但结论保持自由生成。

## 第一批适合试验的对象

优先选择这三类工作流：

- 已经多次迭代、文档变长的 workflow。
- 每次执行都要读大量上下文的 workflow。
- 有真实历史任务可 replay 的 workflow。

当前本地可优先试验：

- `AI工作区/AI超级个体/workflows/idea-validation-flow.md`
- `AI工作区/AI超级个体/workflows/imported/*.README.md`
- `AI工作区/AI超级个体/11-自媒体工作流/项目/007-动漫电影AI解说工作流/`

## 判断标准

一个优化版只有满足以下条件，才算真正变好：

- 启动上下文减少 30% 以上，或平均任务上下文减少 20% 以上。
- 输出质量不低于 baseline。
- 成功率不低于 baseline。
- agent 可自主跳过无关步骤。
- 新 workflow 的入口文档能在 3 分钟内读懂。
- 后续新增规则有明确放置位置，不会继续污染启动上下文。

如果只减少 token 但质量下降，不合并。
如果流程更“漂亮”但更难跑，不合并。
如果 harness 更完整但 agent 更笨，不合并。
