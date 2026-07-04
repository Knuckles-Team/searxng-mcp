"""Native epistemic-graph ingestion for SearXNG search results.

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The searxng-mcp connector natively
pushes its data into the ONE epistemic-graph knowledge graph from its own code:

* each web result → a shared ``:Document`` node (text worth semantic search) carrying the
  result title/snippet + ``source_uri`` (the result URL), plus a typed ``:SearchResult`` shape;
* the query itself → a ``:SearchQuery`` node, and each engine that surfaced results →
  ``:SearchEngine`` nodes, linked ``:resultOf`` / ``:fromEngine``.

This is a thin mapper over the shared primitive
``agent_utilities.knowledge_graph.memory.native_ingest`` (imported GUARDED). When that
primitive is not present in the installed ``agent_utilities`` — or no engine is reachable —
every entry point **no-ops** (returns ``None``) via a self-contained txn fallback, so the
connector runs with zero KG infrastructure. Node ids follow ``searxng:<class>:<extId>`` and
``type`` matches the classes federated by ``searxng_mcp.ontology`` (``searxng.ttl``).
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger("searxng_mcp.kg")

_SOURCE = "searxng-mcp"
_DOMAIN = "searxng"
_DEFAULT_GRAPH = "__commons__"

# Prefer the shared fleet primitive; fall back to a self-contained txn path when the
# installed agent_utilities predates it (the primitive is not yet shipped there).
try:  # pragma: no cover - exercised by environment, not unit tests
    from agent_utilities.knowledge_graph.memory.native_ingest import (
        ingest_documents as _shared_ingest_documents,
    )
    from agent_utilities.knowledge_graph.memory.native_ingest import (
        ingest_entities as _shared_ingest_entities,
    )

    _HAVE_PRIMITIVE = True
except Exception:  # noqa: BLE001 - primitive absent -> use local fallback
    _shared_ingest_documents = None
    _shared_ingest_entities = None
    _HAVE_PRIMITIVE = False


def _client() -> tuple[Any | None, str]:
    """Return ``(engine_client, graph_name)`` or ``(None, "")`` when unavailable."""
    try:
        from agent_utilities.knowledge_graph.core.graph_compute import (
            GraphComputeEngine,
        )
    except Exception as e:  # noqa: BLE001 - KG stack absent
        logger.debug("KG ingest unavailable (import): %s", e)
        return None, ""
    try:
        engine = GraphComputeEngine()
        client = getattr(engine, "_client", None)
        if client is None:
            return None, ""
        return client, (getattr(engine, "graph_name", None) or _DEFAULT_GRAPH)
    except Exception as e:  # noqa: BLE001 - engine unreachable
        logger.debug("KG ingest: engine unreachable: %s", e)
        return None, ""


def _write_nodes(
    client: Any,
    graph: str,
    nodes: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None,
) -> dict[str, int] | None:
    """Self-contained fallback: stamp provenance, MERGE nodes in one txn, add edges."""
    nodes = [n for n in nodes if n.get("id")]
    if not nodes:
        return None
    try:
        txn = client.txn.begin(graph=graph)
        for node in nodes:
            props = {k: v for k, v in node.items() if k != "id" and v is not None}
            props.setdefault("source", _SOURCE)
            props.setdefault("domain", _DOMAIN)
            client.txn.add_node(txn, node["id"], props)
        committed = client.txn.commit(txn)
    except Exception as e:  # noqa: BLE001 - engine/txn failure is non-fatal
        logger.warning("KG ingest: txn failed: %s", e)
        return None
    if not committed:
        logger.warning("KG ingest: txn not committed (conflict)")
        return None

    edges = 0
    for rel in relationships or []:
        try:
            client.edges.add(
                rel["source"], rel["target"], {"type": rel.get("type", "RELATED")}
            )
            edges += 1
        except Exception as e:  # noqa: BLE001 - pure edge link, best-effort
            logger.debug("KG ingest: edge skipped: %s", e)

    logger.info("KG ingest: wrote %d nodes, %d edges", len(nodes), edges)
    return {"nodes": len(nodes), "edges": edges}


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write typed OWL nodes (+ edges) into epistemic-graph.

    ``entities``: ``[{"id":..., "type":<owl:Class>, ...props}]``.
    ``relationships``: ``[{"source":id, "target":id, "type":<link>}]``.
    Returns ``{"nodes":n, "edges":m}`` or ``None`` (no engine / failure; never raises).
    """
    entities = [e for e in (entities or []) if e.get("id")]
    if not entities:
        return None
    if client is None and _HAVE_PRIMITIVE:
        return _shared_ingest_entities(
            entities, relationships, source=_SOURCE, domain=_DOMAIN, graph=graph
        )
    if client is None:
        client, graph = _client()
    if client is None:
        return None
    return _write_nodes(client, graph or _DEFAULT_GRAPH, entities, relationships)


def ingest_documents(
    documents: list[dict[str, Any]],
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write text records as ``:Document`` nodes (semantic-search fodder).

    Each doc: ``{"id":..., "text":..., "title"?:..., "source_uri"?:..., ...props}``.
    Returns ``{"nodes":n, "edges":0}`` or ``None``.
    """
    documents = [d for d in (documents or []) if d.get("id")]
    if not documents:
        return None
    if client is None and _HAVE_PRIMITIVE:
        return _shared_ingest_documents(
            documents, source=_SOURCE, domain=_DOMAIN, graph=graph
        )
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    nodes: list[dict[str, Any]] = []
    for doc in documents:
        text = doc.get("text") or doc.get("content")
        if not text:
            continue
        node = {k: v for k, v in doc.items() if k not in ("content",) and v is not None}
        node["type"] = "Document"
        node["text"] = text
        node.setdefault("created_at", now)
        nodes.append(node)
    if not nodes:
        return None
    if client is None:
        client, graph = _client()
    if client is None:
        return None
    return _write_nodes(client, graph or _DEFAULT_GRAPH, nodes, None)


def _query_id(query: str, language: str | None = None) -> str:
    digest = hashlib.sha1(  # noqa: S324 - non-crypto stable id
        f"{query}|{language or ''}".encode()
    ).hexdigest()[:16]
    return f"searxng:query:{digest}"


def ingest_search_results(
    query: str,
    response: dict[str, Any],
    *,
    language: str | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Map a SearXNG ``web_search`` response → KG nodes and ingest.

    Creates one ``:SearchQuery`` node, one ``:SearchEngine`` node per distinct engine,
    and one ``:Document`` (typed as a search result) per returned result — linking each
    result ``:resultOf`` the query and ``:fromEngine`` its engine. Aggregates the node/edge
    counts from both the entity txn (query + engines) and the document txn (results).
    Returns the combined ``{"nodes":n, "edges":m}`` or ``None``.
    """
    if not query or not isinstance(response, dict):
        return None
    results = response.get("results") or []
    if not isinstance(results, list):
        return None

    qid = _query_id(query, language)
    entities: list[dict[str, Any]] = [
        {
            "id": qid,
            "type": "SearchQuery",
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
        relationships.append({"source": did, "target": qid, "type": "resultOf"})
        if engine:
            eid = f"searxng:engine:{engine}"
            if engine not in seen_engines:
                seen_engines.add(engine)
                entities.append({"id": eid, "type": "SearchEngine", "name": engine})
            relationships.append({"source": did, "target": eid, "type": "fromEngine"})

    ent_res = ingest_entities(entities, relationships, client=client, graph=graph)
    doc_res = ingest_documents(documents, client=client, graph=graph)

    if ent_res is None and doc_res is None:
        return None
    nodes = (ent_res or {}).get("nodes", 0) + (doc_res or {}).get("nodes", 0)
    edges = (ent_res or {}).get("edges", 0) + (doc_res or {}).get("edges", 0)
    return {"nodes": nodes, "edges": edges}
