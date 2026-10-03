#!/usr/bin/env python
"""Snapshot the bundled ACH scenarios for the static React workbench demo.

Writes ``ui/public/demo-data.json``: the same payload ``POST /ach`` returns,
plus each evidence row's Admiralty base weight so the browser can recompute
the ranking after cell edits when no API is running (GitHub Pages).

Usage::

    python scripts/export_demo.py                    # -> ui/public/demo-data.json
    python scripts/export_demo.py --out /tmp/demo.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.ach import SPOOFABLE_DISCOUNT, ACHEngine  # noqa: E402
from occam.attack import load_bundled  # noqa: E402
from occam.scenario import load_scenario  # noqa: E402


def snapshot(path: Path) -> dict:
    q, actors, evidence, _ = load_scenario(path)
    eng = ACHEngine(actors, evidence, q, kb=load_bundled())
    out = eng.assess().to_dict()
    out["hypotheses"] = [{"id": h.id, "label": h.label, "kind": h.kind} for h in eng.hypotheses]
    out["evidence"] = [{"id": e.id, "description": e.description, "kind": e.kind.value, "spoofable": e.spoofable,
                        "grade": f"{e.reliability}{e.credibility}", "base_weight": round(e.weight, 6)} for e in evidence]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO / "ui" / "public" / "demo-data.json", help="output JSON file")
    a = ap.parse_args(argv)
    scen = sorted((REPO / "occam" / "demo" / "scenarios").glob("*.json"))
    data = {"spoofable_discount": SPOOFABLE_DISCOUNT, "scenarios": {p.stem: snapshot(p) for p in scen}}
    out = a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(data['scenarios'])} scenarios)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
