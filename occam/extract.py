"""Prose -> IOCs + ATT&CK techniques, every hit carrying a source span.

Baseline is deterministic keyword/regex matching. A trained sentence-level
text->technique classifier (:mod:`occam.classifier`) can be layered on top;
like any future (e.g. LLM) extractor it must emit span-anchored
``TechniqueHit`` objects so that hallucinated facts (no span) can be rejected.
"""
from __future__ import annotations

import bisect
import re

from .attack import AttackKB, load_bundled
from .models import ExtractionResult, Indicator, SourceSpan, TechniqueHit

_IOC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("cve", re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)),
    ("sha256", re.compile(r"\b[a-f0-9]{64}\b", re.I)),
    ("md5", re.compile(r"\b[a-f0-9]{32}\b", re.I)),
    ("url", re.compile(r"\b(?:https?|hxxps?)://[^\s\"'<>]+", re.I)),
    # every repetition is bounded: unbounded nested repeats are super-linear on
    # crafted input such as "a.a.a.a..." (ReDoS)
    ("email", re.compile(r"\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,10}\b")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("domain", re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,10}(?:com|net|org|info|biz|io|ru|cn|kp|ir|xyz|top|example|test)\b", re.I)),
]


def _normalize(text: str) -> str:
    # Same-length refanging so offsets in the normalized text equal offsets in the original.
    t = text.replace("[.]", "\x00.\x00")
    t = re.sub(r"hxxp", "http", t, flags=re.I)
    return t


def _clean_value(v: str) -> str:
    return v.replace("\x00", "").rstrip(".,);]")


def extract(text: str, source_id: str = "doc", kb: AttackKB | None = None, classifier=None) -> ExtractionResult:
    """Extract IOCs, techniques and software from prose.

    ``classifier`` (optional, see :mod:`occam.classifier`) adds sentence-level
    technique predictions; each still carries the sentence span it came from.
    """
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
    # claimed spans are disjoint, kept sorted by start: overlap test is O(log n)
    starts: list[int] = []
    ends: list[int] = []
    for ioc_type, pat in _IOC_PATTERNS:
        for m in pat.finditer(condensed):
            s, e = m.start(), m.end()
            k = bisect.bisect_left(starts, e)  # spans starting before e
            if k and ends[k - 1] > s:
                continue  # already covered by a more specific IOC (e.g. domain inside URL)
            value = _clean_value(m.group(0))
            if ioc_type == "url":
                value = re.sub(r"^hxxp", "http", value, flags=re.I)
            os_, oe = offsets[s], offsets[e - 1] + 1
            starts.insert(k, s)
            ends.insert(k, e)
            indicators.append(Indicator(ioc_type, value, SourceSpan(source_id, os_, oe, text[os_:oe])))

    lower = text.lower()

    def _match(entries) -> list[TechniqueHit]:
        hits: list[TechniqueHit] = []
        for t in entries:
            for kw, pat, case in _patterns(t):
                m = pat.search(text if case else lower)
                if m:
                    hits.append(TechniqueHit(t.id, t.name, kw, SourceSpan(source_id, m.start(), m.end(), text[m.start():m.end()])))
                    break
        return hits

    techniques = _match(kb.techniques.values())
    if classifier is not None:
        seen = {h.technique_id for h in techniques}
        for h in classifier.hits(text, source_id):
            if h.technique_id not in seen and h.technique_id in kb.techniques:
                seen.add(h.technique_id)
                techniques.append(h)

    return ExtractionResult(
        source_id=source_id,
        techniques=techniques,
        indicators=indicators,
        tools=_match(kb.tools.values()),
    )


_PAT_CACHE: dict[tuple[str, tuple[str, ...]], list[tuple[str, re.Pattern[str], bool]]] = {}


def _patterns(t) -> list[tuple[str, re.Pattern[str], bool]]:
    """Compiled keyword patterns. Keywords containing capitals (software proper
    names from ATT&CK) match case-sensitively; lower-case keywords do not."""
    key = (t.id, tuple(t.keywords))
    pats = _PAT_CACHE.get(key)
    if pats is None:
        pats = []
        for kw in t.keywords:
            case = kw != kw.lower()
            body = re.escape(kw if case else kw.lower())
            pats.append((kw, re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])"), case))
        _PAT_CACHE[key] = pats
    return pats


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
