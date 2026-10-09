"""Native epistemic-graph ingestion — Wire-First coverage for searxng-mcp.

Exercises the real ``ingest_entities`` / ``ingest_documents`` / ``ingest_search_results``
seam with a fake SDK ingest **transport** (one level below the facade, per
FLEET-SDK-MIGRATION-RECIPE.md §2b) — no engine required — asserting the records/
relationships the SDK's own request builder produces + the SearXNG response ->
:Document / :SearchQuery / :SearchEngine mapping. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from agent_connector_sdk.ingest import IngestError, KnowledgeIngest

from searxng_mcp.kg_ingest import (
    ingest_documents,
    ingest_entities,
    ingest_search_results,
)


class _FakeTransport:
    def __init__(self) -> None:
        self.requests = []

    async def source_status(self, connector, stream):
        return SimpleNamespace(accepted_checkpoint=None)

    async def submit(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            affected_count=len(request.records),
            relationship_count=len(request.relationships),
        )

    async def store_blob(self, data):
        raise AssertionError("this test's ingestion carries no media")


@pytest.fixture
def ingest():
    transport = _FakeTransport()
    return KnowledgeIngest(transport, loop=None), transport


@pytest.mark.asyncio
async def test_ingest_entities_writes_nodes_and_edges(ingest):
    service, transport = ingest
    res = await ingest_entities(
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
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(transport.requests) == 1
    request = transport.requests[0]
    by_id = {r.record_id: r for r in request.records}
    assert set(by_id) == {"searxng:query:x", "searxng:engine:google"}
    assert by_id["searxng:query:x"].mapping_reference.endswith("schema_mappings/SearchQuery")
    assert request.relationships[0].source.record_id == "searxng:query:x"
    assert request.relationships[0].target.record_id == "searxng:engine:google"
    assert request.relationships[0].relation_reference.endswith("/relations/fromEngine")


@pytest.mark.asyncio
async def test_ingest_documents_writes_document_nodes(ingest):
    service, transport = ingest
    res = await ingest_documents(
        [{"id": "searxng:result:http://a", "text": "hello", "source_uri": "http://a"}],
        ingest=service,
    )
    assert res == {"nodes": 1, "edges": 0}
    record = transport.requests[0].records[0]
    assert record.record_id == "searxng:result:http://a"
    assert record.mapping_reference.endswith("schema_mappings/Document")
    assert record.payload["text"] == "hello"


@pytest.mark.asyncio
async def test_ingest_search_results_maps_query_engine_and_results(ingest):
    service, transport = ingest
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
    res = await ingest_search_results("open source", response, language="en-US", ingest=service)
    # 1 query + 2 engines (entities) + 2 documents = 5 nodes
    assert res["nodes"] == 5
    # each result: resultOf + fromEngine = 4 edges
    assert res["edges"] == 4

    request = transport.requests[0]
    by_id = {r.record_id: r for r in request.records}

    # query node present with typed shape
    qids = [k for k in by_id if k.startswith("searxng:query:")]
    assert len(qids) == 1
    assert by_id[qids[0]].mapping_reference.endswith("schema_mappings/SearchQuery")
    assert by_id[qids[0]].payload["queryText"] == "open source"

    # engine nodes typed
    assert by_id["searxng:engine:duckduckgo"].mapping_reference.endswith("schema_mappings/SearchEngine")
    assert by_id["searxng:engine:wikipedia"].mapping_reference.endswith("schema_mappings/SearchEngine")

    # result documents typed + resultUrl set, empty-url result skipped.
    # `source_uri` is one of agent-connector-sdk's PersistencePrivacyGuard location
    # fields (privacy_rules.py) and is blanket-redacted at persistence time regardless
    # of content — the real URL survives on the non-reserved `resultUrl` field the
    # mapper also stamps. Same behavior as the retired agent-utilities guard it replaces.
    doc = by_id["searxng:result:https://ex.com/a"]
    assert doc.mapping_reference.endswith("schema_mappings/Document")
    assert doc.payload["source_uri"] == "[REDACTED_LOCATION]"
    assert doc.payload["resultUrl"] == "https://ex.com/a"
    assert "A" in doc.payload["text"] and "snippet a" in doc.payload["text"]
    assert not any("skip" in str(v) for v in by_id.values())

    # links: resultOf query + fromEngine
    rel_tuples = {
        (r.source.record_id, r.target.record_id, r.relation_reference.rsplit("/relations/", 1)[-1])
        for r in request.relationships
    }
    assert ("searxng:result:https://ex.com/a", qids[0], "resultOf") in rel_tuples
    assert ("searxng:result:https://ex.com/a", "searxng:engine:duckduckgo", "fromEngine") in rel_tuples


@pytest.mark.asyncio
async def test_missing_node_type_is_rejected(ingest):
    service, _ = ingest
    with pytest.raises(IngestError, match="needs an id and a node_type"):
        await ingest_entities([{"id": "a"}], ingest=service)


@pytest.mark.asyncio
async def test_empty_ingest_entities_is_rejected(ingest):
    service, _ = ingest
    with pytest.raises(IngestError, match="at least one entity"):
        await ingest_entities([], ingest=service)


@pytest.mark.asyncio
async def test_ingest_search_results_records_query_even_with_no_results(ingest):
    service, transport = ingest
    # A query that returned nothing still records the :SearchQuery node (provenance).
    res = await ingest_search_results("empty", {"results": []}, ingest=service)
    assert res == {"nodes": 1, "edges": 0}
    by_id = {r.record_id: r for r in transport.requests[0].records}
    qids = [k for k in by_id if k.startswith("searxng:query:")]
    assert len(qids) == 1
    assert by_id[qids[0]].mapping_reference.endswith("schema_mappings/SearchQuery")
