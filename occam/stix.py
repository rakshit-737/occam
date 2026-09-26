"""STIX 2.1 export (hand-built dicts) with optional python-stix2 validation.

Exports carry the confidence grade and full ACH matrix as a ``note`` so
downstream consumers cannot strip the uncertainty from the conclusion.
``validate`` round-trips a bundle through ``stix2.parse`` (strict, no custom
properties) when the optional ``stix`` extra is installed.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .models import Assessment, ExtractionResult

_NS = uuid.UUID("6f1b8f8e-0cca-4d00-9a11-0ccaa0ccaa00")
_CONF = {"high": 85, "moderate": 50, "low": 15}


def _id(kind: str, key: str) -> str:
    return f"{kind}--{uuid.uuid5(_NS, kind + ':' + key)}"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _pattern(t: str, v: str) -> str | None:
    v = v.replace("\\", "\\\\").replace("'", "\\'")
    return {
        "ipv4": f"[ipv4-addr:value = '{v}']",
        "domain": f"[domain-name:value = '{v}']",
        "url": f"[url:value = '{v}']",
        "sha256": f"[file:hashes.'SHA-256' = '{v}']",
        "md5": f"[file:hashes.MD5 = '{v}']",
    }.get(t)


def export(extraction: ExtractionResult | None = None, assessment: Assessment | None = None) -> dict:
    now = _now()
    objs: list[dict] = []
    if extraction:
        for h in extraction.techniques:
            objs.append({"type": "attack-pattern", "spec_version": "2.1", "id": _id("attack-pattern", h.technique_id),
                         "created": now, "modified": now, "name": h.name,
                         "external_references": [{"source_name": "mitre-attack", "external_id": h.technique_id}]})
        for i in extraction.indicators:
            p = _pattern(i.type, i.value)
            if p:
                objs.append({"type": "indicator", "spec_version": "2.1", "id": _id("indicator", i.type + i.value),
                             "created": now, "modified": now, "pattern": p, "pattern_type": "stix",
                             "valid_from": now, "description": f"extracted from {i.span.source_id}@{i.span.start}"})
    if assessment:
        ref_ids = [o["id"] for o in objs] or [_id("report", assessment.question)]
        objs.append({"type": "note", "spec_version": "2.1", "id": _id("note", assessment.question + now),
                     "created": now, "modified": now,
                     "abstract": f"ACH assessment: {assessment.leading.hypothesis.label} ({assessment.confidence} confidence)",
                     "content": json.dumps(assessment.to_dict(), indent=1),
                     "confidence": _CONF[assessment.confidence],
                     "object_refs": ref_ids})
    return {"type": "bundle", "id": f"bundle--{uuid.uuid4()}", "objects": objs}


def validate(bundle: dict) -> int:
    """Strictly parse a bundle with python-stix2; returns the object count.

    Raises ``ImportError`` if python-stix2 is missing and a ``stix2``
    exception if any object violates the STIX 2.1 specification.
    """
    import stix2

    parsed = stix2.parse(json.dumps(bundle), allow_custom=False, version="2.1")
    return len(parsed.objects)
