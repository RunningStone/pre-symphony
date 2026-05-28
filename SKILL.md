---
name: pre-symphony
description: Turn a coding-agent's SPEC-based PLAN into Symphony-friendly Linear issues. Build a constrained, staged DAG of the plan, preview it, then push the active frontier as atomic, dependency-linked Linear issues. Use when the user says "拆成 issue", "plan to issues", "push to symphony", "feed symphony", or has a PLAN ready to hand to Symphony.
---

# pre-symphony

Bridge a free-form PLAN (written by claude-code / codex from a SPEC) into
**Symphony-friendly Linear issues**. The full DAG stays local; only the active
frontier is pushed. Engine-agnostic: drive it from any coding agent.

## Pipeline

```
build  ->  validate  ->  synth  ->  preview  ->  (human confirm)  ->  push
```

Run via the package CLI (no MCP; Linear access is through the `schpet/linear-cli`
submodule's raw GraphQL):

```bash
python -m pre_symphony build    PLAN.md                 # PLAN -> state/plan_graph.json
python -m pre_symphony validate --plan PLAN.md          # block on errors
python -m pre_symphony synth    --plan PLAN.md          # -> state/issues.json
python -m pre_symphony preview  --plan PLAN.md          # Mermaid + dry-run (local, no network)
python -m pre_symphony push     --plan PLAN.md          # PREVIEW ONLY (confirm gate)
python -m pre_symphony push     --plan PLAN.md --yes \
    --team "$LINEAR_TEAM_ID" --project "$LINEAR_PROJECT_ID"   # actually writes to Linear
```

## PLAN input contract

- Optional YAML front-matter: `spec`, `project`, `default_labels`.
- Each node: `## [<kind>] <title> @<role>` where `<kind>` ∈ `work` / `decision`
  / `milestone_marker`, and `<role>` is a short unique handle.
- Immediately followed by a fenced ```yaml block with: `milestone`,
  `spec_anchor`, `priority`, `depends_on` (list of roles), `labels`, `touch`,
  `body`, `acceptance`, `validation`, `options` (decision only).
- Node ids are auto-hashed from `spec_anchor + kind + role` — never write ids by
  hand; reference dependencies by `role`.

See `tests/fixtures/sample_plan.md` for a complete example.

## Key behaviors

- **Active frontier only.** Nodes behind an unresolved `decision` node are held
  locally. After the decision issue is resolved, re-run the pipeline to expand
  the chosen branch; unchosen branches are never created.
- **Ordering via blockedBy.** Pushed nodes are `Todo` with `blockedBy` relations;
  Symphony will not dispatch a Todo issue while a blocker is non-terminal.
- **Idempotent.** Re-running never duplicates: issues are matched by a hidden
  `pre-symphony:node=<hash>` marker plus `state/linear_map.json`.
- **Confirm gate.** `push` without `--yes` only previews; nothing is written.

## Setup

```bash
git submodule update --init --recursive           # vendor/linear-cli
uv venv && uv pip install -e ".[dev]"
# Linear auth (one of): LINEAR_API_KEY env, vendor/linear-cli `.linear.toml`, or `linear auth login`
```
