"""Shared helpers for the benchmark scripts: provenance and small-sample intervals.

Every ``bench_*.py`` writes ``provenance(...)`` into its JSON so each result
file records the code commit, command, package versions, input checksums and,
when it ran in GitHub Actions, the workflow run that produced it.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import math
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_PACKAGES = ("numpy", "scikit-learn", "networkx", "pypdf", "nltk", "matplotlib")


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=30,
                              check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(inputs: list[Path] | None = None, argv: list[str] | None = None) -> dict:
    """Where a result came from: commit, dirty flag, command, versions, inputs, CI run."""
    status = _git("status", "--porcelain", "--untracked-files=no")
    versions = {"python": platform.python_version()}
    for pkg in _PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass
    run_id = os.environ.get("GITHUB_RUN_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    out = {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_describe": _git("describe", "--tags", "--always", "--dirty"),
        "git_dirty": bool(status) if status is not None else None,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "argv": [Path(sys.argv[0]).name, *(sys.argv[1:] if argv is None else argv)],
        "platform": f"{platform.system()} {platform.machine()}",
        "versions": versions,
        "inputs": {p.name: sha256_file(p) for p in (inputs or []) if p.is_file()},
        "github_run_id": run_id,
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_workflow": os.environ.get("GITHUB_WORKFLOW"),
        "run_url": f"{server}/{repo}/actions/runs/{run_id}" if run_id and repo else None,
    }
    return out


def source_line(prov: dict | None) -> str:
    """One Markdown line naming the run that produced a table."""
    if not prov:
        return "*Source: run not recorded (generated before provenance was added).*"
    commit = (prov.get("git_commit") or "unknown")[:7]
    dirty = " (uncommitted changes)" if prov.get("git_dirty") else ""
    if prov.get("run_url"):
        where = f"GitHub Actions run [{prov['github_run_id']}]({prov['run_url']})"
    else:
        where = f"a local run on {prov.get('platform', '?')}"
    return f"*Source: {where}, commit `{commit}`{dirty}, {prov.get('generated_utc', '?')}.*"


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials (n may be an effective size)."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def degenerate_safe(ci: tuple[float, float], rate: float, n_eff: int) -> tuple[tuple[float, float], bool]:
    """Replace a degenerate cluster-bootstrap interval (a rate of exactly 0 or 1,
    so every resample gives the same value) with a Wilson interval whose sample
    size is the number of clusters -- the worst-case design effect, since a
    rate of 0 gives no handle on the intra-cluster correlation. Returns the
    interval and whether it was replaced."""
    lo, hi = ci
    if hi - lo > 1e-12:
        return (lo, hi), False
    return wilson(rate * n_eff, n_eff), True
