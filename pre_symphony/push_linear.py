"""Idempotent reconcile of issue records into Linear (FR8/FR10/FR11).

This module holds the *testable core*: the reconcile algorithm and the client
Protocol it depends on. The concrete subprocess/GraphQL client lives in
``linear_client`` and is exercised only by credential-gated integration tests.

Idempotency (CD-4/CD-5): each node has a stable hash id. An issue is matched by
(a) the local ``linear_map.json`` and (b) the hidden ``pre-symphony:node=<hash>``
marker in its Linear description, so re-running never creates duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import IssueRecord, LinearMap


@dataclass
class ExistingIssue:
    ref: str
    title: str
    description: str
    state: str
    labels: list[str] = field(default_factory=list)


class LinearClient(Protocol):
    """What reconcile needs from a Linear backend."""

    def existing_markers(self) -> dict[str, ExistingIssue]:
        """Return {node_id: ExistingIssue} for issues carrying our marker."""

    def create_issue(self, rec: IssueRecord) -> str: ...
    def update_issue(self, ref: str, rec: IssueRecord) -> None: ...
    def create_relation(self, blocker_ref: str, blocked_ref: str) -> None: ...
    def ensure_milestone(self, name: str) -> str: ...
    def upsert_document(self, title: str, content: str, doc_id: str | None) -> str: ...


@dataclass
class ReconcileResult:
    linear_map: LinearMap
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _differs(cur: ExistingIssue, rec: IssueRecord) -> bool:
    return (
        cur.title != rec.title
        or cur.description.strip() != rec.description.strip()
        or cur.state != rec.state
        or sorted(cur.labels) != sorted(rec.labels)
    )


def render_document(issues: list[IssueRecord]) -> str:
    """Render the *current active frontier* as one document body (FR11).

    This replaces the previous document content wholesale (update-style upload);
    closed/no-longer-active nodes simply drop out on the next reconcile.
    """
    lines = ["# pre-symphony — active frontier", ""]
    for rec in issues:
        blk = f" (blockedBy {len(rec.blocked_by)})" if rec.blocked_by else ""
        lines.append(f"## [{rec.state}] {rec.title}{blk}")
        if rec.description:
            lines.append(rec.description)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def reconcile(
    issues: list[IssueRecord],
    lmap: LinearMap,
    client: LinearClient,
    *,
    document_title: str = "pre-symphony plan",
    dry_run: bool = False,
) -> ReconcileResult:
    existing = client.existing_markers()
    new_map = LinearMap(
        by_node=dict(lmap.by_node),
        document_id=lmap.document_id,
        milestones=dict(lmap.milestones),
    )
    result = ReconcileResult(linear_map=new_map)

    for milestone in sorted({r.milestone for r in issues if r.milestone}):
        if milestone not in new_map.milestones:
            new_map.milestones[milestone] = (
                "<dry-run>" if dry_run else client.ensure_milestone(milestone)
            )

    for rec in issues:
        ref = new_map.by_node.get(rec.node_id)
        if ref is None and rec.node_id in existing:
            ref = existing[rec.node_id].ref  # marker recovery (CD-5)

        if ref is None:
            if not dry_run:
                ref = client.create_issue(rec)
                new_map.by_node[rec.node_id] = ref
            result.created.append(rec.node_id)
            continue

        current = existing.get(rec.node_id)
        if current is not None and not _differs(current, rec):
            result.skipped.append(rec.node_id)
        else:
            if not dry_run:
                client.update_issue(ref, rec)
            result.updated.append(rec.node_id)
        new_map.by_node[rec.node_id] = ref

    if not dry_run:
        for rec in issues:
            blocked_ref = new_map.by_node.get(rec.node_id)
            if not blocked_ref:
                continue
            for blocker_node in rec.blocked_by:
                blocker_ref = new_map.by_node.get(blocker_node)
                if blocker_ref:
                    client.create_relation(blocker_ref, blocked_ref)

        new_map.document_id = client.upsert_document(
            document_title, render_document(issues), new_map.document_id
        )

    return result
