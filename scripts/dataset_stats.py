#!/usr/bin/env python
"""Write results/datasets.json: the counts and checksums the README and docs quote.

Usage::

    python scripts/dataset_stats.py                      # needs the data from download_data.py
    python scripts/dataset_stats.py --data D:/data/occam --out /tmp/datasets.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from _benchutil import provenance  # noqa: E402

from occam.knowledge import AttackData  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA, help="dataset directory (default: $OCCAM_DATA or ../../datasets/occam)")
    ap.add_argument("--out", type=Path, default=REPO / "results" / "datasets.json", help="output JSON file")
    a = ap.parse_args(argv)
    data_dir = a.data
    for need in ("enterprise-attack-19.2.json", "tram/multi_label.json", "aptnotes/index.json",
                 "rcatt/training_data_original.csv"):
        if not (data_dir / need).is_file():
            ap.error(f"{data_dir / need} not found: run scripts/download_data.py first (or pass --data)")
    out: dict = {}
    for name, rel in (("attack_enterprise_19.2", "enterprise-attack-19.2.json"),
                      ("attack_enterprise_12.1", "attack-history/enterprise-attack-12.1.json"),
                      ("attack_enterprise_15.1", "attack-history/enterprise-attack-15.1.json")):
        p = data_dir / rel
        d = AttackData.load(p)
        s = d.summary()
        s["procedure_examples"] = sum(1 for u in d.uses if u.description)
        s["sha256"] = sha256(p)
        out[name] = s
    tram = json.loads((data_dir / "tram" / "multi_label.json").read_text(encoding="utf-8"))
    out["tram2_multi_label"] = {"sentences": len(tram), "documents": len({r.get("doc_title") or r.get("document") for r in tram}),
                                "sha256": sha256(data_dir / "tram" / "multi_label.json")}
    idx = json.loads((data_dir / "aptnotes" / "index.json").read_text(encoding="utf-8"))
    out["aptnotes_labelled"] = {"reports": len(idx), "groups": len({r["group"] for r in idx}),
                                "label_sources": {k: sum(1 for r in idx if r.get("label_source") == k) for k in ("group", "campaign")}}
    import csv

    with (data_dir / "rcatt" / "training_data_original.csv").open(encoding="ISO-8859-1", newline="") as f:
        csv.field_size_limit(10**9)
        rows = list(csv.reader(f))
    out["rcatt_training_data"] = {"reports": len(rows) - 1, "label_columns": len(rows[0]) - 1,
                                  "sha256": sha256(data_dir / "rcatt" / "training_data_original.csv")}
    out["provenance"] = provenance(argv=argv)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
