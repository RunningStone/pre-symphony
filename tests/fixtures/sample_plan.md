---
spec: docs/SPEC.md
project: pre-symphony-dev
default_labels: [symphony]
---

# Sample Plan

## [work] Implement PLAN parser @parser
```yaml
milestone: M1
spec_anchor: "SPEC#3.2"
priority: 2
depends_on: []
labels: [backend]
touch: [pre_symphony/parse_plan.py]
body: |
  Parse the PLAN markdown into a ParsedPlan.
acceptance:
  - Parses a minimal valid PLAN into nodes
  - Surfaces malformed metadata blocks
validation:
  - "pytest tests/unit/test_parse_plan.py"
```

## [work] Build the DAG @builder
```yaml
milestone: M1
spec_anchor: "SPEC#3.3"
depends_on: [parser]
touch: [pre_symphony/build_graph.py]
body: Build nodes and edges, assign stable ids.
acceptance:
  - Edges map blocks -> blocked_by
validation:
  - "pytest tests/unit/test_build_graph.py"
```

## [decision] Pick storage backend @storage-choice
```yaml
milestone: M2
spec_anchor: "SPEC#5"
depends_on: [builder]
options:
  - json-files
  - sqlite
body: Decide the local state format.
```
