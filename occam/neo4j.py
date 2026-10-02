"""Neo4j export of the Diamond-model graph as a Cypher script (stdlib only).

OCCAM keeps its graph in memory. This adapter writes the same Diamond schema
(``Event``, ``Capability``, ``Infrastructure``, ``Victim``, ``Adversary``
nodes; ``USES`` / ``OBSERVED`` / ``TARGETS`` / ``ATTRIBUTED_TO`` edges and an
optional ``campaign`` property on events) as idempotent ``MERGE`` statements,
so it can be loaded with ``cypher-shell -f graph.cypher`` or the Neo4j Browser.
No driver and no network connection are needed to produce the file.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

LABELS = {"capability": ("Capability", "USES"), "infrastructure": ("Infrastructure", "OBSERVED"),
          "victim": ("Victim", "TARGETS"), "adversary": ("Adversary", "ATTRIBUTED_TO")}


def _lit(s: str) -> str:
    """Cypher string literal with every quote, backslash and control char escaped."""
    out = []
    for ch in str(s):
        if ch in "\\'\"":
            out.append("\\" + ch)
        elif ord(ch) < 0x20 or ch in "\u2028\u2029":
            out.append("\\u" + format(ord(ch), "04x"))
        else:
            out.append(ch)
    return "'" + "".join(out) + "'"


def to_cypher(events: Mapping[str, Mapping[str, Iterable[str]]], campaigns: Mapping[str, str] | None = None) -> str:
    """Render ``{event_id: {facet: [values]}}`` (the `occam.graph` input) as Cypher."""
    lines = [
        "// OCCAM Diamond-model graph -- generated, idempotent (MERGE)",
        *(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{lab}) REQUIRE n.value IS UNIQUE;" for lab, _ in LABELS.values()),
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Event) REQUIRE n.id IS UNIQUE;",
    ]
    for ev in sorted(events):
        facets = events[ev]
        camp = (campaigns or {}).get(ev)
        props = f" SET e.campaign = {_lit(camp)}" if camp is not None else ""
        lines.append(f"MERGE (e:Event {{id: {_lit(ev)}}}){props};")
        for facet in sorted(facets):
            if facet not in LABELS:
                raise ValueError(f"unknown Diamond facet {facet!r}")
            label, rel = LABELS[facet]
            for v in sorted(set(facets[facet])):
                lines.append(f"MATCH (e:Event {{id: {_lit(ev)}}}) MERGE (x:{label} {{value: {_lit(v)}}}) MERGE (e)-[:{rel}]->(x);")
    return "\n".join(lines) + "\n"
