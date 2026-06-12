# AI Delivery Workflow Skill

A Codex-style skill for improving AI-assisted software delivery in teams where AI already writes code, runs tests, fixes compilation errors, and generates documentation.

The skill focuses on the two weak links around coding agents:

1. **Before coding**: turn vague PRDs into an engineering battle card with code evidence, product questions, AI coding context, and boundary conditions.
2. **After coding**: turn PRD + diff into a developer self-verification pack with API, DB, log, edge-case, and handoff checks.

It is designed for microservice teams with unclear PRDs, fragmented service ownership, heavy manual verification, and frequent AI-generated code rework.

## Files

- [`SKILL.md`](./SKILL.md) - The skill definition and workflow instructions.

## Suggested Use

Copy `SKILL.md` into a Codex skill directory, or paste the relevant mode prompt into your AI coding workflow.

Use the skill in two phases:

- `Pre-code battle card`: before asking an AI coding agent to implement a requirement.
- `Post-code self-verification pack`: after code changes exist and before handing off to test/product or starting release flow.
