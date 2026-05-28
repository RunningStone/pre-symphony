"""Concrete Linear backend over ``schpet/linear-cli``'s raw GraphQL (FR9, DP1).

All writes go through ``linear api '<query>' --variables-json <json>``, which
reuses the CLI's auth (LINEAR_API_KEY / .linear.toml / `linear auth login`).
One uniform GraphQL path covers create / update / relation / milestone / query,
so we do not depend on higher-level CLI subcommand flag coverage.

NOTE: exact GraphQL field names are validated against a live workspace only by
the credential-gated integration tests (see DP1 in the project DECISION_TREE).
The reconcile algorithm in ``push_linear`` is what unit tests cover.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass

from .models import IssueRecord
from .push_linear import ExistingIssue

_MARKER_RE = re.compile(r"pre-symphony:node=([0-9a-f]+)")

_CREATE_ISSUE = """
mutation Create($input: IssueCreateInput!) {
  issueCreate(input: $input) { success issue { id identifier } }
}
"""
_UPDATE_ISSUE = """
mutation Update($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) { success }
}
"""
_CREATE_RELATION = """
mutation Rel($input: IssueRelationCreateInput!) {
  issueRelationCreate(input: $input) { success }
}
"""
_CREATE_MILESTONE = """
mutation Ms($input: ProjectMilestoneCreateInput!) {
  projectMilestoneCreate(input: $input) { success projectMilestone { id } }
}
"""
_CREATE_DOC = """
mutation Doc($input: DocumentCreateInput!) {
  documentCreate(input: $input) { success document { id } }
}
"""
_UPDATE_DOC = """
mutation DocU($id: String!, $input: DocumentUpdateInput!) {
  documentUpdate(id: $id, input: $input) { success }
}
"""
_PROJECT_ISSUES = """
query Issues($id: String!, $after: String) {
  project(id: $id) {
    issues(first: 50, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { id identifier title description state { name } labels { nodes { name } } }
    }
  }
}
"""
_TEAM_STATES = """
query States($id: String!) { team(id: $id) { states { nodes { id name } } } }
"""
_TEAM_LABELS = """
query Labels($id: String!) { team(id: $id) { labels { nodes { id name } } } }
"""


class LinearError(RuntimeError):
    pass


@dataclass
class LinearConfig:
    team_id: str
    project_id: str
    cmd: list[str] | None = None  # e.g. ["linear"] or ["deno","run","-A",".../main.ts"]


def _default_cmd() -> list[str]:
    env = os.environ.get("PRE_SYMPHONY_LINEAR_CMD")
    return shlex.split(env) if env else ["linear"]


class CliLinearClient:
    def __init__(self, config: LinearConfig):
        self.cfg = config
        self.cmd = config.cmd or _default_cmd()
        self._states: dict[str, str] | None = None
        self._labels: dict[str, str] | None = None

    # -- transport ---------------------------------------------------------
    def graphql(self, query: str, variables: dict | None = None) -> dict:
        args = [*self.cmd, "api", query]
        if variables:
            args += ["--variables-json", json.dumps(variables)]
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode != 0:
            raise LinearError(f"linear api failed ({proc.returncode}): {proc.stderr.strip()}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise LinearError(f"non-JSON response: {proc.stdout[:200]}") from exc
        if isinstance(payload, dict) and payload.get("errors"):
            raise LinearError(f"graphql errors: {payload['errors']}")
        return payload.get("data", payload) if isinstance(payload, dict) else {}

    def self_check(self) -> bool:
        self.graphql("query { viewer { id } }")
        return True

    # -- lookups -----------------------------------------------------------
    def _state_id(self, name: str) -> str | None:
        if self._states is None:
            data = self.graphql(_TEAM_STATES, {"id": self.cfg.team_id})
            nodes = data.get("team", {}).get("states", {}).get("nodes", [])
            self._states = {n["name"].lower(): n["id"] for n in nodes}
        return self._states.get(name.lower())

    def _label_ids(self, names: list[str]) -> list[str]:
        if self._labels is None:
            data = self.graphql(_TEAM_LABELS, {"id": self.cfg.team_id})
            nodes = data.get("team", {}).get("labels", {}).get("nodes", [])
            self._labels = {n["name"].lower(): n["id"] for n in nodes}
        return [self._labels[n.lower()] for n in names if n.lower() in self._labels]

    # -- protocol ----------------------------------------------------------
    def existing_markers(self) -> dict[str, ExistingIssue]:
        found: dict[str, ExistingIssue] = {}
        after = None
        while True:
            data = self.graphql(_PROJECT_ISSUES, {"id": self.cfg.project_id, "after": after})
            conn = (data.get("project") or {}).get("issues") or {}
            for node in conn.get("nodes", []):
                match = _MARKER_RE.search(node.get("description") or "")
                if not match:
                    continue
                found[match.group(1)] = ExistingIssue(
                    ref=node["id"],
                    title=node.get("title", ""),
                    description=node.get("description", "") or "",
                    state=(node.get("state") or {}).get("name", ""),
                    labels=[lbl["name"] for lbl in (node.get("labels") or {}).get("nodes", [])],
                )
            page = conn.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                break
            after = page.get("endCursor")
        return found

    def _issue_input(self, rec: IssueRecord) -> dict:
        data: dict = {
            "teamId": self.cfg.team_id,
            "projectId": self.cfg.project_id,
            "title": rec.title,
            "description": rec.description,
        }
        if rec.priority is not None:
            data["priority"] = rec.priority
        state_id = self._state_id(rec.state)
        if state_id:
            data["stateId"] = state_id
        label_ids = self._label_ids(rec.labels)
        if label_ids:
            data["labelIds"] = label_ids
        return data

    def create_issue(self, rec: IssueRecord) -> str:
        data = self.graphql(_CREATE_ISSUE, {"input": self._issue_input(rec)})
        result = data.get("issueCreate") or {}
        if not result.get("success"):
            raise LinearError(f"issueCreate failed for {rec.title!r}")
        return result["issue"]["id"]

    def update_issue(self, ref: str, rec: IssueRecord) -> None:
        payload = {"title": rec.title, "description": rec.description}
        state_id = self._state_id(rec.state)
        if state_id:
            payload["stateId"] = state_id
        self.graphql(_UPDATE_ISSUE, {"id": ref, "input": payload})

    def create_relation(self, blocker_ref: str, blocked_ref: str) -> None:
        self.graphql(
            _CREATE_RELATION,
            {"input": {"issueId": blocker_ref, "relatedIssueId": blocked_ref, "type": "blocks"}},
        )

    def ensure_milestone(self, name: str) -> str:
        data = self.graphql(
            _CREATE_MILESTONE,
            {"input": {"projectId": self.cfg.project_id, "name": name}},
        )
        result = data.get("projectMilestoneCreate") or {}
        if not result.get("success"):
            raise LinearError(f"projectMilestoneCreate failed for {name!r}")
        return result["projectMilestone"]["id"]

    def upsert_document(self, title: str, content: str, doc_id: str | None) -> str:
        if doc_id:
            self.graphql(_UPDATE_DOC, {"id": doc_id, "input": {"title": title, "content": content}})
            return doc_id
        data = self.graphql(
            _CREATE_DOC,
            {"input": {"projectId": self.cfg.project_id, "title": title, "content": content}},
        )
        result = data.get("documentCreate") or {}
        if not result.get("success"):
            raise LinearError("documentCreate failed")
        return result["document"]["id"]
