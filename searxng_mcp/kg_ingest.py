"""Native epistemic-graph ingestion for SearXNG results and documents.

All writes go through the SDK's knowledge-ingest facade (:mod:`agent_connector_sdk.ingest`),
which submits a typed ``ChangeSet`` through the generated epistemic-graph ``SourceIngest``
request/receipt types. Nodes use canonical ``node_type`` and edges use canonical
``relationship``; nodes, documents and edges commit in one atomic transaction. Missing engine
dependencies, rejected records, conflicts, and transaction failures propagate as
:class:`~agent_connector_sdk.ingest.IngestError`.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from agent_connector_sdk.ingest import (
    ChangeSet,
    Document,
    Entity,
    IngestBinding,
    IngestError,
    KnowledgeIngest,
    Relationship,
    current_ingest,
)

logger = logging.getLogger("searxng_mcp.kg")

_BINDING = IngestBinding(connector="searxng-mcp", stream="searxng")


def _to_entity(record: dict[str, Any]) -> Entity:
    return Entity(
        id=record.get("id"),
        node_type=record.get("node_type"),
        properties={k: v for k, v in record.items() if k not in ("id", "node_type")},
    )


def _to_relationship(record: dict[str, Any]) -> Relationship:
    props = {k: v for k, v in record.items() if k not in ("source", "target", "relationship")}
    return Relationship(
        source=record["source"],
        target=record["target"],
        relationship=record["relationship"],
        properties=props or None,
    )


def _to_document(record: dict[str, Any]) -> Document:
    return Document(
        id=record["id"],
        text=record["text"],
        title=record.get("title"),
        source_uri=record.get("source_uri"),
        properties={
            k: v for k, v in record.items() if k not in ("id", "text", "title", "source_uri", "updated_at")
        },
        updated_at=record.get("updated_at"),
    )


async def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships in one SDK ingest transaction."""
    if not entities:
        raise IngestError("ingest_entities needs at least one entity")
    change_set = ChangeSet(
        entities=tuple(_to_entity(e) for e in entities),
        relationships=tuple(_to_relationship(r) for r in relationships or ()),
    )
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


async def ingest_documents(
    documents: list[dict[str, Any]],
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Write text records as canonical Document nodes."""
    if not documents:
        raise IngestError("ingest_documents needs at least one document")
    change_set = ChangeSet(documents=tuple(_to_document(d) for d in documents))
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


def _query_id(query: str, language: str | None = None) -> str:
    digest = hashlib.sha256(f"{query}|{language or ''}".encode()).hexdigest()[:32]
    return f"searxng:query:{digest}"


async def ingest_search_results(
    query: str,
    response: dict[str, Any],
    *,
    language: str | None = None,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Map a SearXNG ``web_search`` response → KG nodes and ingest.

    Creates one ``:SearchQuery`` node, one ``:SearchEngine`` node per distinct engine,
    and one ``:Document`` (typed as a search result) per returned result — linking each
    result ``:resultOf`` the query and ``:fromEngine`` its engine, all in ONE atomic
    ``ChangeSet`` submission (the pre-migration code split this into two transactions;
    the SDK's ``ChangeSet`` carries entities, documents and relationships together).
    Returns the combined ``{"nodes":n, "edges":m}``.
    """
    if not query or not isinstance(response, dict):
        raise IngestError("SearXNG ingestion requires a query and response mapping")
    results = response.get("results") or []
    if not isinstance(results, list):
        raise IngestError("SearXNG response results must be a list")

    qid = _query_id(query, language)
    entities: list[Entity] = [
        Entity(
            id=qid,
            node_type="SearchQuery",
            properties={
                "queryText": query,
                "language": language,
                "searxngId": qid.split(":")[-1],
                "number_of_results": response.get("number_of_results"),
            },
        )
    ]
    relationships: list[Relationship] = []
    documents: list[Document] = []
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
            Document(
                id=did,
                text=text,
                title=title,
                source_uri=url,
                properties={
                    "resultUrl": url,
                    "score": res.get("score"),
                    "engine": engine,
                    "category": category,
                    "publishedDate": res.get("publishedDate"),
                    "query": query,
                },
            )
        )
        relationships.append(Relationship(source=did, target=qid, relationship="resultOf"))
        if engine:
            eid = f"searxng:engine:{engine}"
            if engine not in seen_engines:
                seen_engines.add(engine)
                entities.append(Entity(id=eid, node_type="SearchEngine", properties={"name": engine}))
            relationships.append(Relationship(source=did, target=eid, relationship="fromEngine"))

    change_set = ChangeSet(
        entities=tuple(entities),
        documents=tuple(documents),
        relationships=tuple(relationships),
    )
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}
