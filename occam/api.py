"""FastAPI service: extraction, ACH with live cell overrides, STIX export,
a minimal read-only TAXII 2.1 endpoint and the analyst workbench UI.

Run::

    pip install -e ".[api]"
    uvicorn occam.api:app --reload        # http://127.0.0.1:8000

Localhost-only by default; there is no authentication, so do not expose it.
"""
from __future__ import annotations

import os
import uuid
from importlib import resources
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from . import __version__
from .ach import ACHEngine
from .attack import load
from .demo import DEMO
from .extract import extract, navigator_layer
from .models import ActorProfile, Evidence
from .scenario import load_scenario
from .stix import export

FIXTURES = Path(os.environ.get("OCCAM_FIXTURES") or DEMO)
TAXII = "application/taxii+json;version=2.1"
COLLECTION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "occam/assessments"))

app = FastAPI(title="OCCAM", version=__version__, description="Auditable ACH attribution + TTP extraction")
_kb = load(os.environ.get("OCCAM_KB") or None)
_published: list[dict[str, Any]] = []  # in-memory TAXII collection


class ExtractIn(BaseModel):
    text: str = Field(..., max_length=2_000_000)
    source_id: str = "api"


class Override(BaseModel):
    evidence: str
    hypothesis: str
    rating: str


class AchIn(BaseModel):
    scenario: str | None = None                 # fixture scenario name
    actors: list[dict[str, Any]] | None = None  # or an inline scenario
    evidence: list[dict[str, Any]] | None = None
    question: str = "Who conducted the activity?"
    overrides: list[Override] = []
    publish: bool = False


def _scenario_path(name: str) -> Path:
    p = (FIXTURES / "scenarios" / f"{name}.json").resolve()
    if p.parent != (FIXTURES / "scenarios").resolve() or not p.exists():
        raise HTTPException(404, f"unknown scenario {name!r}")
    return p


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "techniques": len(_kb.techniques)}


@app.post("/extract")
def api_extract(body: ExtractIn) -> dict[str, Any]:
    r = extract(body.text, body.source_id, _kb)
    return {"extraction": r.to_dict(), "navigator": navigator_layer(r)}


@app.get("/scenarios")
def scenarios() -> list[str]:
    return sorted(p.stem for p in (FIXTURES / "scenarios").glob("*.json"))


@app.post("/ach")
def api_ach(body: AchIn) -> dict[str, Any]:
    try:
        if body.scenario:
            q, actors, evidence, _ = load_scenario(_scenario_path(body.scenario))
        elif body.actors is not None and body.evidence is not None:
            q = body.question
            actors = [ActorProfile.from_dict(a) for a in body.actors]
            evidence = [Evidence.from_dict(e) for e in body.evidence]
        else:
            raise HTTPException(422, "give either `scenario` or inline `actors` + `evidence`")
        eng = ACHEngine(actors, evidence, q, kb=_kb)
        for o in body.overrides:
            eng.override(o.evidence, o.hypothesis, o.rating)
        a = eng.assess()
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    out = a.to_dict()
    out["hypotheses"] = [{"id": h.id, "label": h.label, "kind": h.kind} for h in eng.hypotheses]
    out["evidence"] = [
        {"id": e.id, "description": e.description, "kind": e.kind.value, "spoofable": e.spoofable,
         "grade": f"{e.reliability}{e.credibility}"}
        for e in evidence
    ]
    out["overridden"] = [f"{e}:{h}" for e, h in eng.overrides]
    if body.publish:
        _published.append(export(assessment=a))
    return out


@app.post("/stix")
def api_stix(body: AchIn) -> dict[str, Any]:
    body.publish = False
    q, actors, evidence, _ = load_scenario(_scenario_path(body.scenario or ""))
    eng = ACHEngine(actors, evidence, q, kb=_kb)
    for o in body.overrides:
        eng.override(o.evidence, o.hypothesis, o.rating)
    return export(assessment=eng.assess())


# -- minimal read-only TAXII 2.1 ---------------------------------------------
def _taxii(obj: Any) -> JSONResponse:
    return JSONResponse(obj, media_type=TAXII)


@app.get("/taxii2/")
def taxii_discovery() -> JSONResponse:
    return _taxii({"title": "OCCAM TAXII", "default": "/taxii2/api/", "api_roots": ["/taxii2/api/"]})


@app.get("/taxii2/api/")
def taxii_root() -> JSONResponse:
    return _taxii({"title": "OCCAM assessments", "versions": [TAXII], "max_content_length": 10_000_000})


@app.get("/taxii2/api/collections/")
def taxii_collections() -> JSONResponse:
    return _taxii({"collections": [{"id": COLLECTION_ID, "title": "ACH assessments", "can_read": True,
                                    "can_write": False, "media_types": ["application/stix+json;version=2.1"]}]})


@app.get("/taxii2/api/collections/{cid}/objects/")
def taxii_objects(cid: str) -> JSONResponse:
    if cid != COLLECTION_ID:
        raise HTTPException(404, "unknown collection")
    objs = [o for b in _published for o in b["objects"]]
    return _taxii({"more": False, "objects": objs})


@app.get("/", response_class=HTMLResponse)
def workbench() -> str:
    return resources.files("occam.web").joinpath("index.html").read_text(encoding="utf-8")
