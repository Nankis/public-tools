# AI Workflow Audit Summary

Local smoke test target:

```text
ai-workflow repository
```

Command:

```bash
AI_WORKFLOW_PATH=/path/to/ai-workflow
python3 workflow_optimizer.py audit \
  --workflow "$AI_WORKFLOW_PATH" \
  --out runs/ai-workflow-audit \
  --mode audit_only
```

Starter samples command:

```bash
python3 workflow_optimizer.py init-samples \
  --out runs/ai-workflow-audit/task-samples.jsonl
```

## Metrics

| Metric | Value |
| --- | ---: |
| Total files | 99 |
| Markdown files | 86 |
| Total estimated tokens | 62,558 |
| Startup candidate files | 26 |
| Startup estimated tokens | 19,416 |
| Headings | 783 |
| Rule-like lines | 773 |
| Checklist items | 2,119 |
| Template markers | 226 |
| Example files | 2 |
| Template files | 14 |

## Initial Reading

The audit suggests that `ai-workflow` already has a healthy separation between core rules, templates, skills, examples, and program history. The main optimization opportunity is startup-context pressure: the heuristic classified 26 files as startup candidates, mostly because `README.md`, `AGENTS.md`, `core/DEV-FLOW.md`, `programs/README.md`, and many `skills/**/SKILL.md` files look like entry or workflow files.

This does not mean all 26 files are actually read on every task. It means the next optimization pass should tighten startup rules and make skill loading more explicitly trigger-based.

## Recommended Next Checks

- Confirm the true mandatory startup set from `AGENTS.md` and `core/BOOT.md`.
- Treat `skills/**/SKILL.md` as lazy-loaded unless a task trigger matches.
- Keep Program history out of startup context unless the user names a Program.
- Use 3-5 real task samples before proposing a candidate workflow change.
