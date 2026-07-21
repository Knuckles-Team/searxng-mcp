"""Native epistemic-graph ingestion for SearXNG results and documents.

All writes use the required ``agent_utilities.knowledge_graph.memory.native_ingest``
primitive. Nodes use canonical ``node_type`` and edges use canonical ``relationship``;
nodes and edges commit in one native transaction. Missing engine dependencies, rejected
records, conflicts, and transaction failures propagate as ``NativeIngestError``.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from agent_utilities.knowledge_graph.memory.native_ingest import (
    NativeIngestError,
)
from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_documents as _native_ingest_documents,
)
from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_entities as _native_ingest_entities,
)

logger = logging.getLogger("searxng_mcp.kg")

_SOURCE = "searxng-mcp"
_DOMAIN = "searxng"

def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships in one native transaction."""
    return _native_ingest_entities(
        entities, relationships, source=source, domain=domain, client=client, graph=graph
    )


def ingest_documents(
    documents: list[dict[str, Any]],
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write text records as canonical Document nodes."""
    return _native_ingest_documents(
        documents, source=source, domain=domain, client=client, graph=graph
    )


def _query_id(query: str, language: str | None = None) -> str:
    digest = hashlib.sha256(f"{query}|{language or ''}".encode()).hexdigest()[:32]
    return f"searxng:query:{digest}"


def ingest_search_results(
    query: str,
    response: dict[str, Any],
    *,
    language: str | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Map a SearXNG ``web_search`` response → KG nodes and ingest.

    Creates one ``:SearchQuery`` node, one ``:SearchEngine`` node per distinct engine,
    and one ``:Document`` (typed as a search result) per returned result — linking each
    result ``:resultOf`` the query and ``:fromEngine`` its engine. Aggregates the node/edge
    counts from both the entity txn (query + engines) and the document txn (results).
    Returns the combined ``{"nodes":n, "edges":m}``.
    """
    if not query or not isinstance(response, dict):
        raise NativeIngestError("SearXNG ingestion requires a query and response mapping")
    results = response.get("results") or []
    if not isinstance(results, list):
        raise NativeIngestError("SearXNG response results must be a list")

    qid = _query_id(query, language)
    entities: list[dict[str, Any]] = [
        {
            "id": qid,
            "node_type": "SearchQuery",
            "queryText": query,
            "language": language,
            "searxngId": qid.split(":")[-1],
            "number_of_results": response.get("number_of_results"),
        }
    ]
    relationships: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    seen_engines: set[str] = set()

    for res in results:
        if not isinstance(res, dict):
            continue
        url = res.get("url")
        if not url:
            continue
        did = f"searxng:result:{url}"
        title = res.get("title")
        content = res.get("content") or ""
        text = f"{title}\n\n{content}".strip() if title else content
        if not text:
            continue
        category = res.get("category")
        engine = res.get("engine")
        documents.append(
            {
                "id": did,
                "title": title,
                "text": text,
                "source_uri": url,
                "resultUrl": url,
                "score": res.get("score"),
                "engine": engine,
                "category": category,
                "publishedDate": res.get("publishedDate"),
                "query": query,
            }
        )
        relationships.append({"source": did, "target": qid, "relationship": "resultOf"})
        if engine:
            eid = f"searxng:engine:{engine}"
            if engine not in seen_engines:
                seen_engines.add(engine)
                entities.append({"id": eid, "node_type": "SearchEngine", "name": engine})
            relationships.append({"source": did, "target": eid, "relationship": "fromEngine"})

    ent_res = ingest_entities(entities, client=client, graph=graph)
    doc_res = (
        _native_ingest_documents(
            documents,
            relationships,
            source=_SOURCE,
            domain=_DOMAIN,
            client=client,
            graph=graph,
        )
        if documents
        else {"nodes": 0, "edges": 0}
    )

    nodes = ent_res["nodes"] + doc_res["nodes"]
    edges = ent_res["edges"] + doc_res["edges"]
    return {"nodes": nodes, "edges": edges}
