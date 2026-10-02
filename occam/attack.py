"""ATT&CK knowledge base: bundled subset + optional loader for the full STIX bundle.

The full ``enterprise-attack.json`` is fetched by ``scripts/download_data.py``
(pinned + checksummed) and parsed by `occam.knowledge`;
``convert_stix_bundle`` turns it into OCCAM's compact KB format.
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
    """Techniques + software, with optional usage statistics.

    ``usage`` maps a technique/software id to the number of ATT&CK groups that
    use it. When present it drives diagnosticity: items used by at least
    ``common_frac`` of all groups are *common* (non-diagnostic, rated N) and
    items used by at most ``rare_max`` groups are *rare* (strongly diagnostic).
    The bundled synthetic subset has no usage data and relies on explicit
    ``common`` flags instead.
    """

    techniques: dict[str, Technique]
    tools: dict[str, Technique] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)
    n_groups: int = 0
    common_frac: float = 0.30
    rare_max: int = 3

    def get(self, tid: str) -> Technique | None:
        return self.techniques.get(tid) or self.tools.get(tid)

    def is_common(self, tid: str) -> bool:
        t = self.techniques.get(tid)
        if t and t.common:
            return True
        if self.n_groups and tid in self.usage:
            return self.usage[tid] >= self.common_frac * self.n_groups
        return False

    def is_rare(self, tid: str) -> bool:
        """Distinctive item: known to be used by only a handful of groups."""
        return bool(self.n_groups) and 0 < self.usage.get(tid, 0) <= self.rare_max

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AttackKB:
        techs = {
            t["id"]: Technique(t["id"], t["name"], t.get("tactic", ""), list(t.get("keywords", [])), bool(t.get("common", False)))
            for t in d.get("techniques", [])
        }
        tools = {
            t["id"]: Technique(t["id"], t["name"], "tool", list(t.get("keywords", [])))
            for t in d.get("tools", [])
        }
        return cls(techs, tools, dict(d.get("usage", {})), int(d.get("n_groups", 0)),
                   float(d.get("common_frac", 0.30)), int(d.get("rare_max", 3)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "techniques": [
                {"id": t.id, "name": t.name, "tactic": t.tactic, "keywords": t.keywords, "common": t.common}
                for t in self.techniques.values()
            ],
            "tools": [{"id": t.id, "name": t.name, "keywords": t.keywords} for t in self.tools.values()],
            "usage": self.usage,
            "n_groups": self.n_groups,
            "common_frac": self.common_frac,
            "rare_max": self.rare_max,
        }


def load_bundled() -> AttackKB:
    text = resources.files("occam.data").joinpath("attack_subset.json").read_text(encoding="utf-8")
    return AttackKB.from_dict(json.loads(text))


def load(path: str | Path | None = None) -> AttackKB:
    if path is None:
        return load_bundled()
    return AttackKB.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def convert_stix_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Convert a MITRE ATT&CK STIX 2.x bundle into OCCAM's compact KB format.

    Technique keywords are the lower-cased technique name (the keyword
    baseline); software keywords are the software name and aliases. Group
    usage counts are included so rarity/commonness is data-driven.
    """
    from .knowledge import AttackData  # local import: knowledge imports this module

    return AttackData.from_bundle(bundle).to_kb().to_dict()
