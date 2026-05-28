# pre-symphony

Turn a coding-agent's SPEC-based plan into **Symphony-friendly Linear issues**: build a
constrained, staged DAG of the plan and emit trackable, rollback-able issues.

## What it does

[Symphony](https://github.com/openai/symphony) only *reads* issues from a tracker (Linear)
and runs Codex per issue — it never creates the issue list. `pre-symphony` fills that gap:
it takes the free-form PLAN a coding agent (claude-code / codex) writes from a SPEC, models
it as a directed acyclic graph (dependencies, decision nodes, stage markers, acceptance +
validation gates), and emits a set of atomic, dependency-linked Linear issues that Symphony
can pick up and execute.

```
claude-code (SPEC+PLAN) ─▶ pre-symphony (this) ─▶ Linear ─▶ Symphony + Codex
```

## Status

Pre-implementation. Requirements are being defined first — see
[`DOCs/PRD/`](DOCs/PRD/20260528-pre-symphony-requirements.md).

## Components

- **A SKILL** (`SKILL.md`) — the entry point a coding agent invokes; orchestrates the Python steps.
- **Python** — parse PLAN → build/validate DAG → synthesize issues → idempotent push.
- **`vendor/linear-cli`** (git submodule, [`schpet/linear-cli`](https://github.com/schpet/linear-cli)) —
  Linear access via CLI + raw GraphQL. No MCP.

## Setup

```bash
git clone --recurse-submodules git@github.com:RunningStone/pre-symphony.git
# or, after a plain clone:
git submodule update --init --recursive
```
