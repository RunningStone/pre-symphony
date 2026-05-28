from pre_symphony.models import IssueRecord, LinearMap
from pre_symphony.push_linear import ExistingIssue, reconcile


class FakeLinearClient:
    """In-memory stand-in implementing the LinearClient protocol."""

    def __init__(self, existing=None):
        self._existing = dict(existing or {})
        self.created: list[str] = []
        self.updated: list[str] = []
        self.relations: set[tuple[str, str]] = set()
        self.milestones: dict[str, str] = {}
        self.documents: dict[str, str] = {}
        self._issue_n = 0
        self._doc_n = 0

    def existing_markers(self):
        return dict(self._existing)

    def create_issue(self, rec):
        self._issue_n += 1
        ref = f"L-{rec.node_id[:4]}-{self._issue_n}"
        self.created.append(rec.node_id)
        self._existing[rec.node_id] = ExistingIssue(
            ref=ref, title=rec.title, description=rec.description,
            state=rec.state, labels=list(rec.labels),
        )
        return ref

    def update_issue(self, ref, rec):
        self.updated.append(rec.node_id)
        for nid, ex in self._existing.items():
            if ex.ref == ref:
                self._existing[nid] = ExistingIssue(
                    ref=ref, title=rec.title, description=rec.description,
                    state=rec.state, labels=list(rec.labels),
                )

    def create_relation(self, blocker_ref, blocked_ref):
        self.relations.add((blocker_ref, blocked_ref))

    def ensure_milestone(self, name):
        self.milestones[name] = f"ms-{name}"
        return self.milestones[name]

    def upsert_document(self, title, content, doc_id):
        if doc_id:
            self.documents[doc_id] = content
            return doc_id
        self._doc_n += 1
        did = f"doc-{self._doc_n}"
        self.documents[did] = content
        return did


def _issue(node_id, title="T", desc="D", state="Todo", labels=("symphony",), blocked_by=()):
    return IssueRecord(
        node_id=node_id, title=title, description=desc, state=state,
        labels=list(labels), blocked_by=list(blocked_by),
    )


def test_create_when_absent_and_wire_relations():
    client = FakeLinearClient()
    result = reconcile([_issue("a"), _issue("b", blocked_by=["a"])], LinearMap(), client)
    assert set(result.created) == {"a", "b"}
    assert not result.updated and not result.skipped
    a_ref = result.linear_map.by_node["a"]
    b_ref = result.linear_map.by_node["b"]
    assert (a_ref, b_ref) in client.relations


def test_skip_when_unchanged():
    client = FakeLinearClient()
    first = reconcile([_issue("a")], LinearMap(), client)
    second = reconcile([_issue("a")], first.linear_map, client)
    assert second.skipped == ["a"]
    assert not second.created and not second.updated
    assert client.created == ["a"]  # created exactly once


def test_update_when_changed():
    client = FakeLinearClient()
    first = reconcile([_issue("a", title="Old")], LinearMap(), client)
    result = reconcile([_issue("a", title="New")], first.linear_map, client)
    assert result.updated == ["a"]
    assert not result.created


def test_marker_recovery_without_local_map():
    client = FakeLinearClient(
        existing={
            "a": ExistingIssue(
                ref="L-existing", title="T", description="D", state="Todo", labels=["symphony"]
            )
        }
    )
    result = reconcile([_issue("a")], LinearMap(), client)
    assert result.created == []
    assert result.skipped == ["a"]
    assert result.linear_map.by_node["a"] == "L-existing"


def test_document_update_not_append():
    client = FakeLinearClient()
    first = reconcile([_issue("a", title="One")], LinearMap(), client)
    assert len(client.documents) == 1
    doc_id = first.linear_map.document_id
    second = reconcile([_issue("a", title="One v2", desc="changed")], first.linear_map, client)
    assert second.linear_map.document_id == doc_id
    assert len(client.documents) == 1  # replaced, not appended
    assert "One v2" in client.documents[doc_id]


def test_dry_run_plans_but_writes_nothing():
    client = FakeLinearClient()
    result = reconcile([_issue("a")], LinearMap(), client, dry_run=True)
    assert result.created == ["a"]  # planned
    assert client.created == []  # but nothing actually written
    assert not client.documents
    assert not client.relations
