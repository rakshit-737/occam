"""Typed data contracts for OCCAM.

Everything is a plain dataclass so the engine is stdlib-only and every object
round-trips to JSON (``to_dict`` / ``from_dict``).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Consistency(int, Enum):
    """Heuer ACH consistency ratings. Only negative values count in ACH scoring."""

    CC = 2   # very consistent
    C = 1    # consistent
    N = 0    # neutral / not applicable
    I = -1   # inconsistent
    II = -2  # very inconsistent

    @classmethod
    def parse(cls, s: str) -> "Consistency":
        try:
            return cls[s.strip().upper()]
        except KeyError as exc:
            raise ValueError(f"unknown consistency rating {s!r}; use CC/C/N/I/II") from exc


class EvidenceKind(str, Enum):
    TTP = "ttp"
    TOOL = "tool"
    INFRASTRUCTURE = "infrastructure"
    VICTIMOLOGY = "victimology"
    CODE_OVERLAP = "code_overlap"          # shared code strings / functions
    LANGUAGE_ARTIFACT = "language_artifact"  # language settings, strings, comments
    METADATA = "metadata"                  # PE rich header, compile timestamps, etc.
    CLAIM = "claim"                        # self-attribution / persona claims


#: Evidence kinds an adversary can cheaply plant to mislead attribution.
SPOOFABLE_KINDS = frozenset(
    {EvidenceKind.CODE_OVERLAP, EvidenceKind.LANGUAGE_ARTIFACT, EvidenceKind.METADATA, EvidenceKind.CLAIM}
)

#: Admiralty (NATO) source reliability A–F -> weight.
RELIABILITY = {"A": 1.0, "B": 0.85, "C": 0.65, "D": 0.45, "E": 0.25, "F": 0.5}
#: Admiralty information credibility 1–6 -> weight.
CREDIBILITY = {1: 1.0, 2: 0.85, 3: 0.65, 4: 0.45, 5: 0.25, 6: 0.5}


@dataclass(frozen=True)
class SourceSpan:
    """Provenance: every extracted fact points back at the text that produced it."""

    source_id: str
    start: int
    end: int
    text: str


@dataclass
class Technique:
    id: str
    name: str
    tactic: str
    keywords: list[str] = field(default_factory=list)
    common: bool = False  # used by many actors -> low diagnosticity


@dataclass
class Indicator:
    type: str  # ipv4, domain, url, sha256, md5, cve, email
    value: str
    span: SourceSpan


@dataclass
class TechniqueHit:
    technique_id: str
    name: str
    matched: str
    span: SourceSpan


@dataclass
class ExtractionResult:
    source_id: str
    techniques: list[TechniqueHit]
    indicators: list[Indicator]
    tools: list[TechniqueHit]

    def technique_ids(self) -> set[str]:
        return {t.technique_id for t in self.techniques}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActorProfile:
    """Synthetic actor profile (the fixtures never describe real groups)."""

    id: str
    name: str
    techniques: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    infrastructure: list[str] = field(default_factory=list)  # infra patterns / ASNs / tags
    sectors: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActorProfile":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class Evidence:
    id: str
    description: str
    kind: EvidenceKind
    value: str = ""                         # technique id / tool / infra tag / sector
    points_to: list[str] = field(default_factory=list)  # actor ids a marker points at
    reliability: str = "B"                  # Admiralty A-F
    credibility: int = 2                    # Admiralty 1-6
    relevance: float = 1.0

    @property
    def spoofable(self) -> bool:
        return self.kind in SPOOFABLE_KINDS

    @property
    def weight(self) -> float:
        return RELIABILITY[self.reliability] * CREDIBILITY[self.credibility] * self.relevance

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Evidence":
        d = dict(d)
        d["kind"] = EvidenceKind(d["kind"])
        if d.get("reliability", "B") not in RELIABILITY:
            raise ValueError(f"bad reliability {d['reliability']!r}")
        if int(d.get("credibility", 2)) not in CREDIBILITY:
            raise ValueError(f"bad credibility {d['credibility']!r}")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class Hypothesis:
    id: str
    label: str
    kind: str  # "actor" | "false_flag" | "unknown"
    actor_id: str | None = None


@dataclass
class HypothesisScore:
    hypothesis: Hypothesis
    inconsistency: float  # <= 0; closer to 0 is better (Heuer)
    support: float        # >= 0; reported, not used for ranking
    spoofable_support_ratio: float


@dataclass
class Assessment:
    question: str
    ranking: list[HypothesisScore]
    matrix: dict[str, dict[str, Consistency]]  # evidence_id -> hypothesis_id -> rating
    diagnostic_weights: dict[str, float]
    confidence: str          # "high" | "moderate" | "low"
    likelihood_phrase: str   # ICD-203 style
    rationale: list[str]
    false_flag_indicators: list[str]
    what_would_change: list[str]

    @property
    def leading(self) -> HypothesisScore:
        return self.ranking[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "leading_hypothesis": self.leading.hypothesis.label,
            "confidence": self.confidence,
            "likelihood_phrase": self.likelihood_phrase,
            "ranking": [
                {
                    "id": s.hypothesis.id,
                    "label": s.hypothesis.label,
                    "kind": s.hypothesis.kind,
                    "inconsistency": round(s.inconsistency, 3),
                    "support": round(s.support, 3),
                    "spoofable_support_ratio": round(s.spoofable_support_ratio, 3),
                }
                for s in self.ranking
            ],
            "matrix": {e: {h: r.name for h, r in row.items()} for e, row in self.matrix.items()},
            "diagnostic_weights": {k: round(v, 3) for k, v in self.diagnostic_weights.items()},
            "rationale": self.rationale,
            "false_flag_indicators": self.false_flag_indicators,
            "what_would_change": self.what_would_change,
        }
