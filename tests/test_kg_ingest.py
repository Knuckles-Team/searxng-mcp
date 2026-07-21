"""Native epistemic-graph ingestion — Wire-First coverage for searxng-mcp.

Exercises the real ``ingest_entities`` / ``ingest_documents`` / ``ingest_search_results``
seam with a fake ChangeEnvelope-capable engine client (no engine required), asserting the
apply()'d add_node/add_edge operations + the SearXNG response -> :Document / :SearchQuery /
:SearchEngine mapping. Mirrors agent-utilities' own canonical
``tests/knowledge_graph/test_native_ingest.py`` fakes — the retired raw ``txn``-only fake is
deliberately rejected by ``native_ingest`` now. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from typing import Any

import msgpack
import pytest
from agent_utilities.knowledge_graph.core.session import GraphSession, use_session
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError
from agent_utilities.models.company_brain import ActorType
from agent_utilities.security.brain_context import ActorContext, use_actor

from searxng_mcp.kg_ingest import (
    ingest_documents,
    ingest_entities,
    ingest_search_results,
)


@pytest.fixture(autouse=True)
def _governed_session():
    """Every native_ingest write requires a verified ambient GraphSession
    (CONCEPT:AU-P0-1) — no development bypass exists by design. Mint a
    synthetic, scoped session the same way agent-utilities' own
    ``tests/knowledge_graph/test_native_ingest.py`` does."""
    actor = ActorContext(
        actor_id="subject:opaque:synthetic",
        actor_type=ActorType.AUTOMATED_SERVICE,
        roles=(),
        tenant_id="tenant:opaque:synthetic",
        authenticated=True,
    )
    session = GraphSession(
        actor=actor,
        tenant=actor.tenant_id,
        scopes=frozenset({"kg:write"}),
        graph="graph:opaque:synthetic",
        policy_version="policy:opaque:synthetic",
        audience="epistemic-graph",
    )
    with use_actor(actor), use_session(session):
        yield


class _FakeNodes:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def properties(self, node_id: str) -> dict[str, Any] | None:
        return self.values.get(node_id)

    def list(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self.values.items())


class _FakeChanges:
    def __init__(self, nodes: _FakeNodes) -> None:
        self.nodes = nodes
        self.edges: list[tuple[str, str, dict[str, Any]]] = []
        self.applied: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, dict[str, Any]] = {}

    def get(self, envelope_id: str) -> dict[str, Any] | None:
        return self.records.get(envelope_id)

    def content_version(self, object_id: str) -> dict[str, Any] | None:
        return self.versions.get(object_id)

    def cursor(self, _source: str, _partition: str = "") -> None:
        return None

    def apply(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.applied.append(envelope)
        mutation = envelope["mutation"]
        for operation in mutation["operations"]:
            method = operation["method"]
            params = method["params"]
            properties = msgpack.unpackb(params["properties_msgpack"], raw=False)
            if method["method"] == "AddNode":
                self.nodes.values[params["node_id"]] = properties
            elif method["method"] == "AddEdge":
                self.edges.append(
                    (params["source_id"], params["target_id"], properties)
                )
        version = envelope["content_version"]
        self.versions[version["object_id"]] = version
        self.records[envelope["envelope_id"]] = envelope
        return {
            "batch_id": mutation["batch_id"],
            "replayed": False,
            "projection_pending": False,
        }


class _FakeRdf:
    def validate_shacl(self, _shapes: str, _data_graph: str) -> dict[str, Any]:
        return {"conforms": True, "results": []}


class _FakeClient:
    def __init__(self) -> None:
        self.nodes = _FakeNodes()
        self.changes = _FakeChanges(self.nodes)
        self.rdf = _FakeRdf()

    @staticmethod
    def supports(operation: str) -> bool:
        return operation == "ApplyChangeEnvelope"


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "searxng:query:x", "node_type": "SearchQuery", "queryText": "q"},
            {
                "id": "searxng:engine:google",
                "node_type": "SearchEngine",
                "name": "google",
            },
        ],
        [
            {
                "source": "searxng:query:x",
                "target": "searxng:engine:google",
                "relationship": "fromEngine",
            }
        ],
        client=c,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.changes.applied
    assert set(c.nodes.values) == {"searxng:query:x", "searxng:engine:google"}
    # provenance is stamped
    assert c.nodes.values["searxng:query:x"]["source"] == "searxng-mcp"
    assert c.nodes.values["searxng:query:x"]["domain"] == "searxng"
    assert c.changes.edges == [
        ("searxng:query:x", "searxng:engine:google", {"relationship": "fromEngine"})
    ]


def test_ingest_documents_writes_document_nodes():
    c = _FakeClient()
    res = ingest_documents(
        [{"id": "searxng:result:http://a", "text": "hello", "source_uri": "http://a"}],
        client=c,
    )
    assert res == {"nodes": 1, "edges": 0}
    node = c.nodes.values["searxng:result:http://a"]
    assert node["node_type"] == "Document"
    assert node["text"] == "hello"
    assert node["source"] == "searxng-mcp"


def test_ingest_search_results_maps_query_engine_and_results():
    c = _FakeClient()
    response = {
        "number_of_results": 2,
        "results": [
            {
                "url": "https://ex.com/a",
                "title": "A",
                "content": "snippet a",
                "engine": "duckduckgo",
                "category": "general",
                "score": 1.5,
            },
            {
                "url": "https://ex.com/b",
                "title": "B",
                "content": "snippet b",
                "engine": "wikipedia",
                "category": "general",
            },
            {"url": "", "title": "skip", "content": "no url"},
        ],
    }
    res = ingest_search_results("open source", response, language="en-US", client=c)
    # 1 query + 2 engines (entities) + 2 documents = 5 nodes
    assert res["nodes"] == 5
    # each result: resultOf + fromEngine = 4 edges
    assert res["edges"] == 4

    # query node present with typed shape
    qids = [k for k in c.nodes.values if k.startswith("searxng:query:")]
    assert len(qids) == 1
    assert c.nodes.values[qids[0]]["node_type"] == "SearchQuery"
    assert c.nodes.values[qids[0]]["queryText"] == "open source"

    # engine nodes typed
    assert c.nodes.values["searxng:engine:duckduckgo"]["node_type"] == "SearchEngine"
    assert c.nodes.values["searxng:engine:wikipedia"]["node_type"] == "SearchEngine"

    # result documents typed + resultUrl set, empty-url result skipped.
    # `source_uri` is one of agent-utilities' PersistencePrivacyGuard
    # `_LOCATION_FIELDS` (persistence_privacy.py) and is blanket-redacted at
    # persistence time regardless of content — the real URL survives on the
    # non-reserved `resultUrl` field the mapper also stamps.
    doc = c.nodes.values["searxng:result:https://ex.com/a"]
    assert doc["node_type"] == "Document"
    assert doc["source_uri"] == "[REDACTED_LOCATION]"
    assert doc["resultUrl"] == "https://ex.com/a"
    assert "A" in doc["text"] and "snippet a" in doc["text"]
    assert not any("skip" in str(v) for v in c.nodes.values.values())

    # links: resultOf query + fromEngine
    assert (
        "searxng:result:https://ex.com/a",
        qids[0],
        {"relationship": "resultOf"},
    ) in c.changes.edges
    assert (
        "searxng:result:https://ex.com/a",
        "searxng:engine:duckduckgo",
        {"relationship": "fromEngine"},
    ) in c.changes.edges


def test_retired_structural_alias_is_rejected():
    with pytest.raises(NativeIngestError, match="canonical node_type"):
        ingest_entities([{"id": "a", "type": "SearchQuery"}], client=_FakeClient())


def test_empty_native_ingest_is_rejected():
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_entities([], client=_FakeClient())


def test_ingest_search_results_records_query_even_with_no_results():
    # A query that returned nothing still records the :SearchQuery node (provenance).
    c = _FakeClient()
    res = ingest_search_results("empty", {"results": []}, client=c)
    assert res == {"nodes": 1, "edges": 0}
    qids = [k for k in c.nodes.values if k.startswith("searxng:query:")]
    assert len(qids) == 1
    assert c.nodes.values[qids[0]]["node_type"] == "SearchQuery"
