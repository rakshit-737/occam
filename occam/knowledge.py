"""Full MITRE ATT&CK STIX 2.1 loader: techniques, groups, software, campaigns,
relationships and procedure examples.

Pure standard library. The bundle is parsed once into plain dataclasses so the
rest of OCCAM (attribution, clustering, classifier training) never touches raw
STIX. ``python-stix2`` is only used (optionally) to *validate* exports.

Usage::

    data = AttackData.load("enterprise-attack-19.2.json")
    profiles = data.actor_profiles()          # one ActorProfile per ATT&CK group
    kb = data.to_kb()                         # AttackKB with usage-based rarity
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .attack import AttackKB
from .models import ActorProfile, Technique

_CITATION = re.compile(r"\(Citation:[^)]*\)")
_MDLINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_CODE = re.compile(r"<code>(.*?)</code>", re.S)


def clean_text(s: str) -> str:
    """Strip ATT&CK citation markers, markdown links and HTML code tags."""
    s = _CITATION.sub("", s or "")
    s = _MDLINK.sub(r"\1", s)
    s = _CODE.sub(r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _ext_id(obj: dict[str, Any]) -> str | None:
    for r in obj.get("external_references", []):
        if r.get("source_name") == "mitre-attack" and r.get("external_id"):
            return r["external_id"]
    return None


def _refs(rel: dict[str, Any]) -> list[str]:
    return [r["source_name"] for r in rel.get("external_references", []) if r.get("source_name")]


@dataclass
class TechniqueInfo:
    id: str
    name: str
    tactics: list[str]
    description: str
    is_subtechnique: bool

    @property
    def parent(self) -> str:
        return self.id.split(".")[0]


@dataclass
class EntityInfo:
    """Group, software or campaign."""

    id: str
    name: str
    kind: str  # group | malware | tool | campaign
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    first_seen: str = ""
    last_seen: str = ""


@dataclass
class Use:
    source: str        # G/S/C id
    target: str        # T or S id
    description: str   # cleaned procedure text
    references: list[str]


@dataclass
class AttackData:
    version: str
    techniques: dict[str, TechniqueInfo]
    groups: dict[str, EntityInfo]
    software: dict[str, EntityInfo]
    campaigns: dict[str, EntityInfo]
    uses: list[Use]
    attributed_to: dict[str, str]  # campaign id -> group id

    # -- loading --------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> AttackData:
        return cls.from_bundle(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_bundle(cls, bundle: dict[str, Any]) -> AttackData:
        objs = [o for o in bundle.get("objects", []) if not o.get("revoked") and not o.get("x_mitre_deprecated")]
        stix2ext: dict[str, str] = {}
        techniques: dict[str, TechniqueInfo] = {}
        groups: dict[str, EntityInfo] = {}
        software: dict[str, EntityInfo] = {}
        campaigns: dict[str, EntityInfo] = {}
        version = ""
        for o in objs:
            t = o.get("type")
            if t == "x-mitre-collection":
                version = o.get("x_mitre_version", "")
            eid = _ext_id(o)
            if not eid:
                continue
            if t == "attack-pattern":
                stix2ext[o.get("id", eid)] = eid
                techniques[eid] = TechniqueInfo(
                    eid,
                    o.get("name", ""),
                    [p["phase_name"] for p in o.get("kill_chain_phases", []) if p.get("kill_chain_name", "mitre-attack") == "mitre-attack"],
                    clean_text(o.get("description", "")),
                    bool(o.get("x_mitre_is_subtechnique")),
                )
            elif t == "intrusion-set":
                stix2ext[o.get("id", eid)] = eid
                groups[eid] = EntityInfo(eid, o["name"], "group", [a for a in o.get("aliases", []) if a != o["name"]],
                                         clean_text(o.get("description", "")))
            elif t in ("malware", "tool"):
                stix2ext[o.get("id", eid)] = eid
                software[eid] = EntityInfo(eid, o["name"], t, [a for a in o.get("x_mitre_aliases", []) if a != o["name"]],
                                           clean_text(o.get("description", "")))
            elif t == "campaign":
                stix2ext[o.get("id", eid)] = eid
                campaigns[eid] = EntityInfo(eid, o["name"], "campaign", [a for a in o.get("aliases", []) if a != o["name"]],
                                            clean_text(o.get("description", "")), o.get("first_seen", ""), o.get("last_seen", ""))
        uses: list[Use] = []
        attributed: dict[str, str] = {}
        for o in objs:
            if o.get("type") != "relationship":
                continue
            s, d = stix2ext.get(o.get("source_ref", "")), stix2ext.get(o.get("target_ref", ""))
            if not s or not d:
                continue
            rt = o.get("relationship_type")
            if rt == "uses":
                uses.append(Use(s, d, clean_text(o.get("description", "")), _refs(o)))
            elif rt == "attributed-to" and s in campaigns and d in groups:
                attributed[s] = d
        return cls(version, techniques, groups, software, campaigns, uses, attributed)

    # -- usage ----------------------------------------------------------------
    def usage(self, entity_id: str, via_software: bool = False) -> set[str]:
        """Technique + software ids used by a group/campaign/software."""
        direct = {u.target for u in self.uses if u.source == entity_id}
        if via_software:
            for sid in [x for x in direct if x in self.software]:
                direct |= {u.target for u in self.uses if u.source == sid and u.target in self.techniques}
        return direct

    def _usage_index(self) -> dict[str, set[str]]:
        idx: dict[str, set[str]] = defaultdict(set)
        for u in self.uses:
            idx[u.source].add(u.target)
        return idx

    def group_usage_counts(self) -> Counter[str]:
        """How many groups use each technique / software (for rarity)."""
        idx = self._usage_index()
        c: Counter[str] = Counter()
        for gid in self.groups:
            c.update(idx.get(gid, set()))
        return c

    def actor_profiles(self, min_items: int = 1, exclude: Iterable[str] = ()) -> list[ActorProfile]:
        idx = self._usage_index()
        excl = set(exclude)
        out = []
        for gid, g in sorted(self.groups.items()):
            used = idx.get(gid, set())
            if len(used) < min_items:
                continue
            out.append(ActorProfile(
                id=gid,
                name=g.name,
                techniques=sorted(x for x in used if x in self.techniques and x not in excl),
                tools=sorted(x for x in used if x in self.software and x not in excl),
                description=g.description[:280],
            ))
        return out

    def procedures(self) -> list[tuple[str, str, str]]:
        """(text, technique_id, source_id) procedure examples for classifier training."""
        return [(u.description, u.target, u.source) for u in self.uses if u.target in self.techniques and u.description]

    # -- compact KB -----------------------------------------------------------
    def to_kb(self, common_frac: float = 0.30, rare_max: int = 3) -> AttackKB:
        counts = self.group_usage_counts()
        n = len(self.groups) or 1
        techs = {
            tid: Technique(tid, t.name, t.tactics[0] if t.tactics else "", [t.name.lower()],
                           counts.get(tid, 0) >= common_frac * n)
            for tid, t in self.techniques.items()
        }
        tools = {
            sid: Technique(sid, s.name, "tool", _software_keywords(s))
            for sid, s in self.software.items()
        }
        return AttackKB(techs, tools, usage=dict(counts), n_groups=n, common_frac=common_frac, rare_max=rare_max)

    def summary(self) -> dict[str, int | str]:
        return {
            "version": self.version,
            "techniques": len(self.techniques),
            "subtechniques": sum(t.is_subtechnique for t in self.techniques.values()),
            "groups": len(self.groups),
            "software": len(self.software),
            "campaigns": len(self.campaigns),
            "uses_relationships": len(self.uses),
            "procedure_examples": len(self.procedures()),
            "attributed_campaigns": len(self.attributed_to),
        }


#: Software names that are also ordinary words / OS utilities; matching them in
#: prose produces false hits, so they are only matched case-sensitively in full.
_GENERIC_SOFTWARE = {
    "at", "net", "cmd", "ping", "route", "tor", "ftp", "arp", "reg", "ver", "expand", "xcopy", "systeminfo",
    "ipconfig", "netstat", "tasklist", "schtasks", "whoami", "nltest", "certutil", "esentutl", "dsquery",
    "nbtstat", "netsh", "wevtutil", "msiexec", "rundll32", "attrib", "shell", "agent", "backdoor", "loader",
    "downloader", "dropper", "stealer", "wiper", "rat", "sys", "power", "lock", "cobalt", "empire",
}


def _software_keywords(s: EntityInfo) -> list[str]:
    kws = []
    for a in [s.name, *s.aliases]:
        if len(a) >= 3 and a.lower() not in _GENERIC_SOFTWARE:
            kws.append(a)
    return kws
