#!/usr/bin/env python
"""Compare freshly generated result files with the committed ones.

Walks every ``*.json`` in NEW that also exists in OLD and reports numbers that
differ by more than a tolerance, keys that are new, and keys that disappeared.
Run-specific fields (provenance, runtimes, checksums of paired inputs) are
ignored. Used by the ``bench`` workflow; prints Markdown for the job summary.

Usage::

    python scripts/compare_results.py NEW_DIR OLD_DIR [--tol 1e-9] [--strict]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

IGNORE = {"provenance", "runtime_s", "paired_with_sha256"}


def walk(new, old, path: str, out: dict, tol: float) -> None:
    if isinstance(new, dict) and isinstance(old, dict):
        for k in new:
            if k in IGNORE:
                continue
            if k not in old:
                out["added"].append(f"{path}/{k}")
            else:
                walk(new[k], old[k], f"{path}/{k}", out, tol)
        out["removed"] += [f"{path}/{k}" for k in old if k not in new and k not in IGNORE]
    elif isinstance(new, list) and isinstance(old, list):
        if len(new) != len(old):
            out["changed"].append((path, f"list of {len(old)}", f"list of {len(new)}"))
            return
        for i, (a, b) in enumerate(zip(new, old)):
            walk(a, b, f"{path}[{i}]", out, tol)
    elif isinstance(new, bool) or isinstance(old, bool) or not isinstance(new, (int, float)) or not isinstance(old, (int, float)):
        if new != old:
            out["changed"].append((path, old, new))
    elif abs(new - old) > tol * max(1.0, abs(old)):
        out["changed"].append((path, old, new))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new", type=Path)
    ap.add_argument("old", type=Path)
    ap.add_argument("--tol", type=float, default=1e-9, help="relative tolerance for numbers")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any shared value changed")
    a = ap.parse_args(argv)
    total = 0
    lines = ["## Regenerated results vs committed", "", "| File | Changed values | New keys | Removed keys |", "|---|---|---|---|"]
    details = []
    for f in sorted(a.new.glob("*.json")):
        o = a.old / f.name
        if not o.exists():
            lines.append(f"| {f.name} | (new file) | | |")
            continue
        out: dict = {"changed": [], "added": [], "removed": []}
        walk(json.loads(f.read_text(encoding="utf-8")), json.loads(o.read_text(encoding="utf-8")), "", out, a.tol)
        total += len(out["changed"])
        lines.append(f"| {f.name} | {len(out['changed'])} | {len(out['added'])} | {len(out['removed'])} |")
        for p, x, y in out["changed"][:15]:
            details.append(f"- `{f.name}{p}`: {x!r} -> {y!r}")
    if details:
        lines += ["", "First changed values per file:", "", *details]
    print("\n".join(lines))
    return 1 if a.strict and total else 0


if __name__ == "__main__":
    sys.exit(main())
