---
name: ai-delivery-workflow
description: Use when a software team already uses AI coding agents but still loses time because PRDs are vague, service context is missing, AI-generated code is only partially correct, and developers must manually verify DB/API/log behavior. Generates pre-code battle cards, AI coding context packs, product clarification questions, and post-code self-verification packs from PRDs, code evidence, and diffs.
---

# AI Delivery Workflow

Use this skill to improve the success rate of AI-assisted development. Do **not** focus on making another coding agent. Focus on making existing coding agents more accurate before coding and easier to verify after coding.

Core belief: when an AI coding agent produces only 60-70% correct code, the root cause is often not the model. It is missing business context, service evidence, data-source clarity, edge cases, and verification criteria.

## When To Use

Use this skill when:

- product PRDs are AI-generated, vague, or full of assumptions
- product owners do not know service boundaries or data availability
- requirements span multiple microservices
- developers spend too much time finding related code before coding
- AI-generated code needs repeated prompts to fix business details
- code compiles but business behavior is still uncertain
- developers manually verify DB/API/log behavior before handoff

Avoid this skill when the user only needs generic code review, compilation fixes, test generation, release automation, or service knowledge-base lookup. Those are separate capabilities.

## Output Modes

Choose one mode based on where the user is in the development flow.

### Mode 1: Pre-Code Battle Card

Use before implementation. Input can be a PRD, ticket, product idea, rough notes, screenshots, or chat history.

Return a battle card that answers:

- what is the actual requirement?
- what is unclear and must not be guessed?
- what should product confirm?
- what code evidence exists?
- what similar logic already exists?
- what context should be passed to the AI coding agent?
- what business and edge cases must be covered?

### Mode 2: AI Coding Context Pack

Use when the user is ready to ask a coding agent to implement. Convert the battle card into a narrow, high-signal prompt.

Return:

- exact task scope
- relevant files/symbols/search terms
- business rules
- forbidden assumptions
- edge cases
- expected output
- tests or checks to run
- what not to change

### Mode 3: Post-Code Self-Verification Pack

Use after code changes exist. Input should include PRD/spec plus git diff, changed files, API info, or developer notes.

Return:

- change summary
- API verification cases
- DB read-only verification templates
- log query keywords
- edge-case checklist
- rollout/gray/fallback checks
- handoff note for product/test

This mode should generate templates and checklists by default. Do not execute database writes, production operations, or risky release actions.

### Mode 4: End-to-End Delivery Pack

Use when the user wants the full workflow:

PRD -> battle card -> coding context pack -> self-verification pack.

Keep each section concise enough for real engineering use.

## Workflow

### 1. Understand the Requirement

Extract the requirement into one sentence:

```text
In [scenario], [user/system] should [do/see/receive] [result], under [constraints].
```

If this sentence cannot be written without guessing, mark the requirement as `NOT_READY`.

### 2. Separate Product Questions From Engineering Investigation

Product managers are not expected to know services, tables, RPCs, repository structure, or code owners.

Ask product only about business facts:

- who is the user?
- what scenario triggers the requirement?
- what should the user see?
- what data means in business terms
- expected behavior when data is missing
- status priority and decision rules
- before/after behavior
- examples and counterexamples
- acceptance criteria

Put technical unknowns under engineering investigation:

- which service owns the data?
- is there an existing API/table/event/cache?
- does this service have access permission?
- is cross-service dependency needed?
- is a feature flag, gray release, or fallback needed?
- are there compatibility concerns?

### 3. Search For Code Evidence Before Inferring

When repository access is available, search before reasoning. Prefer evidence from:

- route definitions
- handlers/controllers
- service methods
- RPC clients
- DAO/repository/query code
- domain models, structs, enums, constants
- config files and feature flags
- tests and fixtures
- migrations or schema definitions
- log keys and metric names

Use exact file paths and symbol names when possible. If evidence is weak, say so.

### 4. Generate The Pre-Code Battle Card

Use this structure:

```markdown
# Requirement Battle Card

## 1. Requirement Translation
One sentence describing the actual outcome.

## 2. Readiness Verdict
READY / PARTIAL / NOT_READY, with reasons.

## 3. Do-Not-Guess Items
Facts that must be confirmed instead of invented.

## 4. Product Confirmation Questions
Concrete questions product can answer.

## 5. Engineering Investigation Items
Technical checks for developers.

## 6. Code Evidence
Relevant files, symbols, routes, structs, configs, or tests with why they matter.

## 7. Similar Existing Logic
Existing implementation patterns that the coding agent should follow.

## 8. Business Rules
Deterministic rules and priority order.

## 9. Edge Cases
Missing data, no permission, timeout, duplicate request, old data, old app version, fallback, gray disabled.

## 10. AI Coding Context Pack
The prompt-ready context for implementation.

## 11. Developer Self-Verification Seed
Initial API/DB/log checks that should be expanded after diff exists.
```

### 5. Generate The AI Coding Context Pack

This pack should be small enough to paste into a coding agent.

Template:

```text
Task:
Implement only [narrow requirement].

Requirement:
[one-sentence requirement]

Relevant code evidence:
- [file]: [symbol/purpose]
- [file]: [symbol/purpose]

Business rules:
- [rule]

Do not guess:
- [unknown]

Edge cases to cover:
- [case]

Constraints:
- keep compatibility unless specified
- do not refactor unrelated code
- follow existing patterns in [files]
- ask before changing contracts not listed here

Expected output:
- code changes
- tests or test updates
- brief verification notes
```

### 6. Generate The Post-Code Self-Verification Pack

Use PRD/spec and diff to produce:

```markdown
# Developer Self-Verification Pack

## 1. Change Summary
What changed, from a business perspective and code perspective.

## 2. API Verification
List curl/HTTP/RPC verification cases. Include normal, empty, permission, and failure paths.

## 3. DB Read-Only Verification
Read-only SQL templates or field checks. Mark sensitive or production data access as requiring internal approval.

## 4. Log Verification
Log keywords, request ids, error keys, fallback keys, and expected log shape.

## 5. Edge-Case Checklist
Business boundaries that must be checked before handoff.

## 6. Product/Test Handoff
Plain-language scenarios product/test should verify.

## 7. Release Risk Notes
Feature flag, gray release, fallback, rollback, monitoring, compatibility.
```

Do not invent exact SQL, endpoints, or log keys unless they are present in the supplied context. Use placeholders when needed.

## Scoring And Prioritization

If multiple possible improvements exist, score them:

| Factor | Question |
|---|---|
| Frequency | Does this happen every week? |
| Time saved | Can this save at least 10 minutes per requirement? |
| Independence | Can one developer use it without cross-team approval? |
| Evidence | Can it use code/diff evidence instead of pure guessing? |
| Risk | Is it read-only and human-reviewed? |
| Demo value | Can before/after be shown in 3-5 days? |

Prefer small, evidence-backed workflows over large agents.

## Prompt Templates

### Pre-Code Battle Card Prompt

```text
你是资深后端技术负责人。不要直接写代码。

目标：把下面的 PRD/需求整理成研发开工前的“需求落地作战单”，用于减少 AI 编码 agent 猜错和研发反复补上下文。

要求：
1. 先用一句话翻译真实需求。
2. 判断 READY / PARTIAL / NOT_READY。
3. 列出不能脑补的点。
4. 把“产品需要确认的问题”和“研发需要调查的问题”分开。
5. 如果提供代码上下文，请基于代码证据分析；不要凭空发明服务、接口、表或字段。
6. 输出给 AI 编码 agent 的上下文包。
7. 输出开发完成后的自验证种子清单。

PRD/需求：
{{PRD}}

代码/服务上下文：
{{CODE_CONTEXT}}
```

### AI Coding Context Pack Prompt

```text
你是 AI 编码助手。请只完成下面的窄任务，不要扩大范围。

任务：
{{TASK}}

需求背景：
{{REQUIREMENT_TRANSLATION}}

代码证据：
{{CODE_EVIDENCE}}

业务规则：
{{BUSINESS_RULES}}

禁止假设：
{{DO_NOT_GUESS}}

边界条件：
{{EDGE_CASES}}

约束：
1. 遵循已有代码模式。
2. 不重构无关代码。
3. 不改变未声明的接口兼容性。
4. 不确定时先列问题，不要猜。
5. 修改后给出验证建议。
```

### Post-Code Self-Verification Prompt

```text
你是负责交付质量的后端研发。不要执行线上操作。

目标：基于 PRD/spec 和 git diff，生成开发自验证包，让研发在交给测试/产品前检查业务正确性。

请输出：
1. 变更摘要
2. API/RPC 验证用例
3. DB 只读验证模板
4. 日志验证关键词
5. 边界场景 checklist
6. 发给产品/测试的验收说明
7. 发布风险：灰度、回滚、监控、兼容性

不要编造不存在的接口、表、字段或日志 key。不确定时使用占位符并标注 UNCONFIRMED。

PRD/spec：
{{SPEC}}

git diff / changed files：
{{DIFF}}
```

## Anti-Patterns

Avoid:

- asking product managers which microservices are involved
- polishing PRD wording without producing engineering leverage
- generating code from unreviewed vague requirements
- treating AI-generated code as correct because it compiles
- hiding unknowns to make the output look confident
- creating a large autonomous agent when a markdown battle card would reduce most friction
- executing DB writes, production commands, or release actions from this skill

## Done Criteria

The output is successful when it:

- reduces repeated AI chat needed before implementation
- makes missing business facts visible
- gives the coding agent concrete code evidence and constraints
- lists business edge cases before coding
- gives developers a clear self-verification path after coding
- can be tested on a real requirement within 3-5 days
