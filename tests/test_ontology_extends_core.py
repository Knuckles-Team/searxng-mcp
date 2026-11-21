"""The pack extends only the core ontology (CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R003)."""

import re
from pathlib import Path

import pytest

ONTOLOGY_DIR = Path(__file__).resolve().parents[1] / "searxng_mcp" / "ontology"
CORE_TERMS = {
    "SearchEngine",
    "SearchQuery",
    "SearchResult",
    "resultUrl",
}


@pytest.mark.spec("CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R003")
def test_pack_declares_no_core_term():
    declared = set()
    for ttl in ONTOLOGY_DIR.glob("*.ttl"):
        declared |= set(
            re.findall(r"^:([A-Za-z0-9_]+)\s+(?:a|rdf:type)\s", ttl.read_text(), re.M)
        )
    assert declared.isdisjoint(CORE_TERMS), sorted(declared & CORE_TERMS)
