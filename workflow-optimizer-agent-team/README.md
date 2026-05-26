# Workflow Optimizer Agent Team

A lightweight agent-team workflow and CLI for auditing, testing, and improving AI workflows.

The goal is not to make every workflow more formal. The goal is to make workflows easier to run, cheaper to load, measurable, and safer to optimize.

## What It Does

- Maps a workflow's files, startup context, templates, examples, and support material.
- Estimates context cost with simple local heuristics.
- Separates startup context from lazy-loaded or archival context.
- Provides JSONL contracts for baseline/candidate task experiments.
- Summarizes manually recorded A/B experiment runs.
- Gives an agent-team operating model for workflow optimization.

## Contents

- `workflow-optimizer-agent-team.md` - agent-team design, roles, phases, guardrails, and decision rules.
- `workflow_optimizer.py` - MVP CLI runner.
- `schemas/` - JSON schemas for task samples and experiment runs.
- `templates/` - starter report and judge rubric templates.
- `examples/ai-workflow-audit-summary.md` - local smoke audit summary for the `ai-workflow` repository.

## Quick Start

Run a static audit:

```bash
python3 workflow_optimizer.py audit \
  --workflow /path/to/workflow-or-repo \
  --out runs/my-workflow-audit
```

Create starter task samples:

```bash
python3 workflow_optimizer.py init-samples \
  --out runs/my-workflow-audit/task-samples.jsonl
```

Summarize baseline/candidate experiment rows:

```bash
python3 workflow_optimizer.py compare \
  --run runs/my-workflow-audit
```

## Run Contract

The CLI creates a run folder with:

- `run.json`
- `context-inventory.json`
- `workflow-map.md`
- `metrics-summary.json`
- `task-samples.jsonl`
- `experiments/experiment-runs.jsonl`
- `experiments/comparison-report.md` after `compare`

Candidate workflow drafts should live under `candidate/workflow/` during evaluation. Do not overwrite the source workflow while testing.

## MVP Limits

This is intentionally small. The current CLI performs static audit, sample initialization, and comparison summaries. It does not yet automatically run multiple agents, generate candidate workflows, or judge merges without human/agent-entered experiment rows.
