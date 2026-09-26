"""Prose -> IOCs + ATT&CK techniques, every hit carrying a source span.

Baseline is deterministic keyword/regex matching (Grade A). A trained
text->technique classifier and LLM extraction are TODO (Grade B/C); any such
extractor must emit the same span-anchored ``TechniqueHit`` objects so that
hallucinated facts (no span) can be rejected.
"""
from __future__ import annotations

import re

from .attack import AttackKB, load_bundled
from .models import ExtractionResult, Indicator, SourceSpan, TechniqueHit

_IOC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("cve", re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)),
    ("sha256", re.compile(r"\b[a-f0-9]{64}\b", re.I)),
    ("md5", re.compile(r"\b[a-f0-9]{32}\b", re.I)),
    ("url", re.compile(r"\b(?:https?|hxxps?)://[^\s\"'<>]+", re.I)),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("domain", re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|info|biz|io|ru|cn|kp|ir|xyz|top|example|test)\b", re.I)),
]


def _normalize(text: str) -> str:
    # Same-length refanging so offsets in the normalized text equal offsets in the original.
    t = text.replace("[.]", "\x00.\x00")
    t = re.sub(r"hxxp", "http", t, flags=re.I)
    return t


def _clean_value(v: str) -> str:
    return v.replace("\x00", "").rstrip(".,);]")


def extract(text: str, source_id: str = "doc", kb: AttackKB | None = None) -> ExtractionResult:
    kb = kb or load_bundled()
    norm = _normalize(text)
    # For IOC matching, treat NULs as removable: build a condensed view with an offset map.
    condensed_chars, offsets = [], []
    for i, ch in enumerate(norm):
        if ch != "\x00":
            condensed_chars.append(ch)
            offsets.append(i)
    condensed = "".join(condensed_chars)
    offsets.append(len(norm))

    indicators: list[Indicator] = []
    claimed: list[tuple[int, int]] = []
    for ioc_type, pat in _IOC_PATTERNS:
        for m in pat.finditer(condensed):
            s, e = m.start(), m.end()
            if any(s < ce and e > cs for cs, ce in claimed):
                continue  # already covered by a more specific IOC (e.g. domain inside URL)
            value = _clean_value(m.group(0))
            if ioc_type == "url":
                value = re.sub(r"^hxxp", "http", value, flags=re.I)
            os_, oe = offsets[s], offsets[e - 1] + 1
            claimed.append((s, e))
            indicators.append(Indicator(ioc_type, value, SourceSpan(source_id, os_, oe, text[os_:oe])))

    lower = text.lower()

    def _match(entries) -> list[TechniqueHit]:
        hits: list[TechniqueHit] = []
        for t in entries:
            for kw in t.keywords:
                pat = re.compile(r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"(?![a-z0-9])")
                m = pat.search(lower)
                if m:
                    hits.append(TechniqueHit(t.id, t.name, kw, SourceSpan(source_id, m.start(), m.end(), text[m.start():m.end()])))
                    break
        return hits

    return ExtractionResult(
        source_id=source_id,
        techniques=_match(kb.techniques.values()),
        indicators=indicators,
        tools=_match(kb.tools.values()),
    )


def navigator_layer(result: ExtractionResult, name: str = "OCCAM extraction") -> dict:
    """Minimal ATT&CK Navigator layer (v4.5 format) for the extracted techniques."""
    return {
        "name": name,
        "versions": {"layer": "4.5", "navigator": "4.9.1"},
        "domain": "enterprise-attack",
        "description": f"Auto-extracted by OCCAM from {result.source_id}",
        "techniques": [
            {"techniqueID": h.technique_id, "score": 1, "comment": f"span {h.span.start}-{h.span.end}: {h.span.text!r}"}
            for h in result.techniques
        ],
        "gradient": {"colors": ["#ffffff", "#ff6666"], "minValue": 0, "maxValue": 1},
    }
