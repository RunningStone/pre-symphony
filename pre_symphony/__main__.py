"""CLI entry point. M1 exposes ``build`` and ``validate``; ``synth`` / ``preview``
/ ``push`` arrive in later milestones.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build_graph import BuildError, build_graph
from .models import graph_from_dict, graph_to_dict
from .parse_plan import ParseError, parse_plan
from .validate import ValidationError, validate


def cmd_build(args: argparse.Namespace) -> None:
    graph = build_graph(parse_plan(args.plan))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(graph_to_dict(graph), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"built {len(graph.nodes)} nodes, {len(graph.edges)} edges -> {out}")


def cmd_validate(args: argparse.Namespace) -> None:
    if args.plan:
        graph = build_graph(parse_plan(args.plan))
    else:
        graph = graph_from_dict(json.loads(Path(args.graph).read_text(encoding="utf-8")))
    report = validate(graph)
    print(report)
    if not report.ok:
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="pre-symphony", description="PLAN -> Symphony-friendly Linear issues"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="parse a PLAN and build the DAG")
    build.add_argument("plan", help="path to the PLAN markdown file")
    build.add_argument("-o", "--out", default="state/plan_graph.json")
    build.set_defaults(func=cmd_build)

    val = sub.add_parser("validate", help="validate a PLAN or a built graph")
    source = val.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan", help="validate straight from a PLAN markdown file")
    source.add_argument("--graph", help="validate a built plan_graph.json")
    val.set_defaults(func=cmd_validate)

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
