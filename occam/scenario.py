"""Load actor profiles and ACH scenarios from JSON fixtures."""
from __future__ import annotations

import json
from pathlib import Path

from .models import ActorProfile, Evidence


def load_actors(path: str | Path) -> list[ActorProfile]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [ActorProfile.from_dict(a) for a in data["actors"]]


def load_scenario(path: str | Path) -> tuple[str, list[ActorProfile], list[Evidence], dict]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    actors_ref = data.get("actors", "../actors.json")
    if isinstance(actors_ref, str):
        actors = load_actors((path.parent / actors_ref).resolve())
    else:
        actors = [ActorProfile.from_dict(a) for a in actors_ref]
    evidence = [Evidence.from_dict(e) for e in data["evidence"]]
    known = {a.id for a in actors}
    for e in evidence:
        unknown = set(e.points_to) - known
        if unknown:
            raise ValueError(f"evidence {e.id} points to unknown actors {sorted(unknown)}")
    return data.get("question", "Who conducted the activity?"), actors, evidence, data.get("expected", {})
