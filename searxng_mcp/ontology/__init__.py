"""Searxng ontology contribution (CONCEPT:AU-KG.ontology.federation-provider-leg).

Data-only subpackage: it carries ``searxng.ttl`` (the ``owl:Ontology``
``http://knuckles.team/kg/searxng`` module — search queries, the ranked web results
they return, the aggregated search engines, and the serving instance) which the
scion-sdk hub federates in via the ``scion_sdk.ontology_providers``
entry-point. It holds no business logic and no heavy imports so the hub can resolve
it cheaply.
"""
