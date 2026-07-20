"""Native epistemic-graph ingestion — Wire-First coverage for searxng-mcp.

Exercises the real ``ingest_entities`` / ``ingest_documents`` / ``ingest_search_results``
seam with a fake engine client (no engine required), asserting the txn add_node/commit +
edge calls and the SearXNG response -> :Document / :SearchQuery / :SearchEngine mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError

from searxng_mcp.kg_ingest import (
    ingest_documents,
    ingest_entities,
    ingest_search_results,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def add_edge(self, txn, source, target, props):
        self.edges.append((source, target, props))

    def commit(self, txn):
        self.committed = True
        return True


class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "searxng:query:x", "node_type": "SearchQuery", "queryText": "q"},
            {"id": "searxng:engine:google", "node_type": "SearchEngine", "name": "google"},
        ],
        [
            {
                "source": "searxng:query:x",
                "target": "searxng:engine:google",
                "relationship": "fromEngine",
            }
        ],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"searxng:query:x", "searxng:engine:google"}
    # provenance is stamped
    assert c.txn.nodes["searxng:query:x"]["source"] == "searxng-mcp"
    assert c.txn.nodes["searxng:query:x"]["domain"] == "searxng"
    assert c.txn.edges == [
        ("searxng:query:x", "searxng:engine:google", {"relationship": "fromEngine"})
    ]


def test_ingest_documents_writes_document_nodes():
    c = _FakeClient()
    res = ingest_documents(
        [{"id": "searxng:result:http://a", "text": "hello", "source_uri": "http://a"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 1, "edges": 0}
    node = c.txn.nodes["searxng:result:http://a"]
    assert node["node_type"] == "Document"
    assert node["text"] == "hello"
    assert node["source"] == "searxng-mcp"
    assert "created_at" in node


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
    qids = [k for k in c.txn.nodes if k.startswith("searxng:query:")]
    assert len(qids) == 1
    assert c.txn.nodes[qids[0]]["node_type"] == "SearchQuery"
    assert c.txn.nodes[qids[0]]["queryText"] == "open source"

    # engine nodes typed
    assert c.txn.nodes["searxng:engine:duckduckgo"]["node_type"] == "SearchEngine"
    assert c.txn.nodes["searxng:engine:wikipedia"]["node_type"] == "SearchEngine"

    # result documents typed + source_uri set, empty-url result skipped
    doc = c.txn.nodes["searxng:result:https://ex.com/a"]
    assert doc["node_type"] == "Document"
    assert doc["source_uri"] == "https://ex.com/a"
    assert "A" in doc["text"] and "snippet a" in doc["text"]
    assert not any("skip" in str(v) for v in c.txn.nodes.values())

    # links: resultOf query + fromEngine
    assert (
        "searxng:result:https://ex.com/a",
        qids[0],
        {"relationship": "resultOf"},
    ) in c.txn.edges
    assert (
        "searxng:result:https://ex.com/a",
        "searxng:engine:duckduckgo",
        {"relationship": "fromEngine"},
    ) in c.txn.edges


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
    qids = [k for k in c.txn.nodes if k.startswith("searxng:query:")]
    assert len(qids) == 1
    assert c.txn.nodes[qids[0]]["node_type"] == "SearchQuery"
