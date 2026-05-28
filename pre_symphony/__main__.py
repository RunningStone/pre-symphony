"""CLI entry point.

Pipeline:  build -> validate -> synth -> preview -> (confirm) -> push

- ``build``    PLAN -> plan_graph.json
- ``validate`` PLAN or graph -> report (exit 1 on errors)
- ``synth``    PLAN/graph -> issues.json (validates + annotates first)
- ``preview``  PLAN/graph -> Mermaid + dry-run summary (local, no network)
- ``push``     PLAN -> Linear; without --yes it only previews (the confirm gate)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .build_graph import BuildError, build_graph
from .parse_plan import ParseError, parse_plan
from .plan_stages import annotate_stages
from .push_linear import reconcile
from .state_store import load_linear_map, save_graph, save_issues, save_linear_map
from .synth_issues import synth_issues
from .validate import ValidationError, validate
from .visualize import dry_run_summary, to_mermaid


def _graph_from_args(args: argparse.Namespace):
    if getattr(args, "graph", None):
        from .state_store import load_graph

        return load_graph(args.graph)
    return build_graph(parse_plan(args.plan))


def _issues_from_args(args: argparse.Namespace):
    graph = _graph_from_args(args)
    validate(graph).raise_if_errors()
    annotate_stages(graph)
    return graph, synth_issues(graph)


def cmd_build(args: argparse.Namespace) -> None:
    graph = build_graph(parse_plan(args.plan))
    save_graph(graph, args.out)
    print(f"built {len(graph.nodes)} nodes, {len(graph.edges)} edges -> {args.out}")


def cmd_validate(args: argparse.Namespace) -> None:
    report = validate(_graph_from_args(args))
    print(report)
    if not report.ok:
        sys.exit(1)


def cmd_synth(args: argparse.Namespace) -> None:
    graph, issues = _issues_from_args(args)
    save_graph(graph, args.graph_out)
    save_issues(issues, args.out)
    print(f"synthesized {len(issues)} issue(s) -> {args.out}")


def cmd_preview(args: argparse.Namespace) -> None:
    graph, issues = _issues_from_args(args)
    print(dry_run_summary(graph, issues))
    print("\n--- mermaid ---")
    print(to_mermaid(graph))


def cmd_push(args: argparse.Namespace) -> None:
    graph, issues = _issues_from_args(args)
    if not args.yes:
        # Local confirm gate (NFR4): no network, nothing written.
        print(dry_run_summary(graph, issues))
        print("\nThis was a local preview. Re-run with --yes to push to Linear.")
        return

    team = args.team or os.environ.get("LINEAR_TEAM_ID")
    project = args.project or os.environ.get("LINEAR_PROJECT_ID")
    if not team or not project:
        print(
            "error: --team/--project (or LINEAR_TEAM_ID/LINEAR_PROJECT_ID) are "
            "required to push to Linear.",
            file=sys.stderr,
        )
        sys.exit(2)

    from .linear_client import CliLinearClient, LinearConfig

    client = CliLinearClient(LinearConfig(team_id=team, project_id=project))
    state_path = Path(args.state_dir) / "linear_map.json"
    result = reconcile(
        issues, load_linear_map(state_path), client, document_title=args.doc_title
    )
    save_linear_map(result.linear_map, state_path)
    print(
        f"pushed: created={len(result.created)} updated={len(result.updated)} "
        f"skipped={len(result.skipped)} -> {state_path}"
    )


def _add_source(parser: argparse.ArgumentParser, *, allow_graph: bool = True) -> None:
    parser.add_argument("--plan", help="PLAN markdown file")
    if allow_graph:
        parser.add_argument("--graph", help="a built plan_graph.json (instead of --plan)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="pre-symphony", description="PLAN -> Symphony-friendly Linear issues"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="parse a PLAN and build the DAG")
    p_build.add_argument("plan")
    p_build.add_argument("-o", "--out", default="state/plan_graph.json")
    p_build.set_defaults(func=cmd_build)

    p_val = sub.add_parser("validate", help="validate a PLAN or built graph")
    _add_source(p_val)
    p_val.set_defaults(func=cmd_validate)

    p_synth = sub.add_parser("synth", help="synthesize issues.json")
    _add_source(p_synth)
    p_synth.add_argument("-o", "--out", default="state/issues.json")
    p_synth.add_argument("--graph-out", default="state/plan_graph.json")
    p_synth.set_defaults(func=cmd_synth)

    p_prev = sub.add_parser("preview", help="local Mermaid + dry-run summary (no network)")
    _add_source(p_prev)
    p_prev.set_defaults(func=cmd_preview)

    p_push = sub.add_parser("push", help="push to Linear (requires --yes; previews otherwise)")
    p_push.add_argument("--plan")
    p_push.add_argument("--graph")
    p_push.add_argument("--team", help="Linear team id (or env LINEAR_TEAM_ID)")
    p_push.add_argument("--project", help="Linear project id (or env LINEAR_PROJECT_ID)")
    p_push.add_argument("--state-dir", default="state")
    p_push.add_argument("--doc-title", default="pre-symphony plan")
    p_push.add_argument("--yes", action="store_true", help="actually write to Linear")
    p_push.set_defaults(func=cmd_push)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (ParseError, BuildError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
