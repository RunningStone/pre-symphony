"""Integration (flow) tests against a real Linear workspace.

Credential-gated: SKIPPED unless LINEAR_API_KEY + LINEAR_TEAM_ID +
LINEAR_PROJECT_ID are set. These verify DP1 (linear-cli raw GraphQL covers
create/relation/state/label/milestone/document) and end-to-end idempotency.
Run manually:  LINEAR_API_KEY=... LINEAR_TEAM_ID=... LINEAR_PROJECT_ID=... \
                  .venv/bin/python -m pytest tests/integration -q
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not (
        os.environ.get("LINEAR_API_KEY")
        and os.environ.get("LINEAR_TEAM_ID")
        and os.environ.get("LINEAR_PROJECT_ID")
    ),
    reason="requires LINEAR_API_KEY + LINEAR_TEAM_ID + LINEAR_PROJECT_ID",
)

from pre_symphony.build_graph import build_graph  # noqa: E402
from pre_symphony.linear_client import CliLinearClient, LinearConfig  # noqa: E402
from pre_symphony.models import LinearMap  # noqa: E402
from pre_symphony.parse_plan import parse_plan  # noqa: E402
from pre_symphony.plan_stages import annotate_stages  # noqa: E402
from pre_symphony.push_linear import reconcile  # noqa: E402
from pre_symphony.synth_issues import synth_issues  # noqa: E402

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def _client() -> CliLinearClient:
    return CliLinearClient(
        LinearConfig(
            team_id=os.environ["LINEAR_TEAM_ID"],
            project_id=os.environ["LINEAR_PROJECT_ID"],
        )
    )


def test_self_check():
    assert _client().self_check()


def test_push_is_idempotent():
    graph = annotate_stages(build_graph(parse_plan(FIXTURE)))
    issues = synth_issues(graph)
    client = _client()
    first = reconcile(issues, LinearMap(), client)
    second = reconcile(issues, first.linear_map, client)
    assert not second.created, "second run must not create duplicate issues"
