#!/usr/bin/env python
"""Write results/datasets.json: the counts and checksums the README and docs quote.

Usage::

    python scripts/dataset_stats.py      # needs the data from download_data.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.knowledge import AttackData  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out: dict = {}
    for name, rel in (("attack_enterprise_19.2", "enterprise-attack-19.2.json"),
                      ("attack_enterprise_12.1", "attack-history/enterprise-attack-12.1.json"),
                      ("attack_enterprise_15.1", "attack-history/enterprise-attack-15.1.json")):
        p = DATA / rel
        d = AttackData.load(p)
        s = d.summary()
        s["procedure_examples"] = sum(1 for u in d.uses if u.description)
        s["sha256"] = sha256(p)
        out[name] = s
    tram = json.loads((DATA / "tram" / "multi_label.json").read_text(encoding="utf-8"))
    out["tram2_multi_label"] = {"sentences": len(tram), "documents": len({r.get("doc_title") or r.get("document") for r in tram}),
                                "sha256": sha256(DATA / "tram" / "multi_label.json")}
    idx = json.loads((DATA / "aptnotes" / "index.json").read_text(encoding="utf-8"))
    out["aptnotes_labelled"] = {"reports": len(idx), "groups": len({r["group"] for r in idx}),
                                "label_sources": {k: sum(1 for r in idx if r.get("label_source") == k) for k in ("group", "campaign")}}
    import csv

    with (DATA / "rcatt" / "training_data_original.csv").open(encoding="ISO-8859-1", newline="") as f:
        csv.field_size_limit(10**9)
        rows = list(csv.reader(f))
    out["rcatt_training_data"] = {"reports": len(rows) - 1, "label_columns": len(rows[0]) - 1,
                                  "sha256": sha256(DATA / "rcatt" / "training_data_original.csv")}
    (REPO / "results" / "datasets.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
