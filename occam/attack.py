"""ATT&CK knowledge base: bundled subset + optional loader for the full STIX bundle.

The full ``enterprise-attack.json`` is never downloaded automatically. If you
have a local copy, ``convert_stix_bundle`` turns it into OCCAM's compact format.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from .models import Technique


@dataclass
class AttackKB:
    techniques: dict[str, Technique]
    tools: dict[str, Technique] = field(default_factory=dict)

    def get(self, tid: str) -> Technique | None:
        return self.techniques.get(tid) or self.tools.get(tid)

    def is_common(self, tid: str) -> bool:
        t = self.techniques.get(tid)
        return bool(t and t.common)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AttackKB":
        techs = {
            t["id"]: Technique(t["id"], t["name"], t.get("tactic", ""), list(t.get("keywords", [])), bool(t.get("common", False)))
            for t in d.get("techniques", [])
        }
        tools = {
            t["id"]: Technique(t["id"], t["name"], "tool", list(t.get("keywords", [])))
            for t in d.get("tools", [])
        }
        return cls(techs, tools)


def load_bundled() -> AttackKB:
    text = resources.files("occam.data").joinpath("attack_subset.json").read_text(encoding="utf-8")
    return AttackKB.from_dict(json.loads(text))


def load(path: str | Path | None = None) -> AttackKB:
    if path is None:
        return load_bundled()
    return AttackKB.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def convert_stix_bundle(bundle: dict[str, Any], max_keywords: int = 3) -> dict[str, Any]:
    """Convert a MITRE ATT&CK STIX 2.x bundle into OCCAM's compact KB format.

    Keywords default to the lower-cased technique name; this is a naive
    baseline and is documented as such (a trained classifier is TODO).
    """
    out: dict[str, Any] = {"techniques": [], "tools": []}
    for obj in bundle.get("objects", []):
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        ext_id = next(
            (r.get("external_id") for r in obj.get("external_references", []) if r.get("source_name") == "mitre-attack"),
            None,
        )
        if not ext_id:
            continue
        name = obj.get("name", "")
        if obj.get("type") == "attack-pattern":
            phases = obj.get("kill_chain_phases") or [{}]
            out["techniques"].append(
                {"id": ext_id, "name": name, "tactic": phases[0].get("phase_name", ""), "keywords": [name.lower()][:max_keywords]}
            )
        elif obj.get("type") in ("malware", "tool"):
            aliases = [a.lower() for a in obj.get("x_mitre_aliases", [])] or [name.lower()]
            out["tools"].append({"id": f"tool:{name.lower().replace(' ', '')}", "name": name, "keywords": aliases[:max_keywords]})
    return out
