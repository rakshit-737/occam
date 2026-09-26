#!/usr/bin/env python
"""Fetch OCCAM's public evaluation data into a directory OUTSIDE the repo.

Sources (all pinned to immutable commits, all verified by checksum):

* MITRE ATT&CK Enterprise 19.2 STIX 2.1 bundle (mitre-attack/attack-stix-data)
  -- techniques, groups, software, campaigns and relationships.
* MITRE CTID TRAM2 annotated sentences (Apache-2.0) -- sentence-level
  ATT&CK technique labels from ~150 real threat reports.
* APTnotes (aptnotes/data metadata + kbandla/APTnotes PDF mirror) -- public
  APT report PDFs; a subset whose filename names an ATT&CK group is fetched
  and converted to text. Each PDF is verified against its git blob SHA-1.

Nothing here downloads or executes malware: every file is JSON, CSV or a PDF
report. PDFs are parsed as text only (pypdf) and never opened in a viewer.

Usage::

    python scripts/download_data.py                      # everything (~180 MB)
    python scripts/download_data.py --only attack tram   # skip APTnotes PDFs
    python scripts/download_data.py --aptnotes-max 60
    OCCAM_DATA=D:/data/occam python scripts/download_data.py
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))

ATTACK_COMMIT = "6cda5ad8462c79e14fbb872f4e09059b18e0cfc4"
TRAM_COMMIT = "f29793d8d665f7f552898696e00065ef24a29a20"
APTNOTES_META_COMMIT = "8595fbdee6747be9e9f730fd0bacd247157314df"
APTNOTES_PDF_COMMIT = "586aaa5e3960bb951a83050f898a2117bd46ebcf"

GH = "https://raw.githubusercontent.com"
FILES = {
    "attack": [
        (
            f"{GH}/mitre-attack/attack-stix-data/{ATTACK_COMMIT}/enterprise-attack/enterprise-attack-19.2.json",
            "enterprise-attack-19.2.json",
            "SHA256_ATTACK",
        ),
    ],
    "tram": [
        (f"{GH}/center-for-threat-informed-defense/tram/{TRAM_COMMIT}/data/tram2-data/multi_label.json",
         "tram/multi_label.json", "SHA256_TRAM_MULTI"),
        (f"{GH}/center-for-threat-informed-defense/tram/{TRAM_COMMIT}/data/tram2-data/single_label.json",
         "tram/single_label.json", "SHA256_TRAM_SINGLE"),
        (f"{GH}/center-for-threat-informed-defense/tram/{TRAM_COMMIT}/LICENSE.txt", "tram/LICENSE.txt", None),
    ],
    "aptnotes": [
        (f"{GH}/aptnotes/data/{APTNOTES_META_COMMIT}/APTnotes.csv", "aptnotes/APTnotes.csv", "SHA256_APTNOTES_CSV"),
    ],
}

#: sha256 of the pinned files (filled from the first verified download).
CHECKSUMS = {
    "SHA256_ATTACK": "dc1639caa5501d720e280cf1cbd8fbe009884a0c9b3e6e9ed9d0c25166c3d8f4",
    "SHA256_TRAM_MULTI": "8a0c6644e4477eab28c92efd3bd7004b9563cb120ae1681d7d0a05dc170cd91b",
    "SHA256_TRAM_SINGLE": "7f9966dd8647e777e28e02aa08d7a38499f4b6ba5682a2366508a7b63b82cc0f",
    "SHA256_APTNOTES_CSV": "dac4579a78ad0ad644d6f57670f31ac54f0424b3ab2619c8119d8f65e48adf0b",
}

UA = {"User-Agent": "occam-data-fetch/0.2 (+https://github.com/rakshit-737/occam)", "Accept-Encoding": "gzip"}


def _headers(url: str) -> dict[str, str]:
    h = dict(UA)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        h["Authorization"] = f"Bearer {token}"  # 5000 req/h instead of 60
    return h


def _get(url: str, retries: int = 5, timeout: int = 120) -> bytes:
    """GET with chunked reads (a stalled socket times out per chunk) and retries."""
    last: Exception | None = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=_headers(url)), timeout=timeout) as r:
                chunks = []
                while True:
                    c = r.read(1 << 20)
                    if not c:
                        break
                    chunks.append(c)
                data = b"".join(chunks)
                expected = r.headers.get("Content-Length")
                if expected and int(expected) != len(data):
                    raise OSError(f"short read {len(data)}/{expected}")
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)  # ~9x smaller transfer for STIX JSON
                return data
        except Exception as exc:  # noqa: BLE001 - network errors vary by platform
            last = exc
            print(f"    retry {i + 1}/{retries}: {exc}", flush=True)
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def fetch_pinned(group: str, out: Path) -> None:
    for url, rel, key in FILES[group]:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        expected = CHECKSUMS.get(key or "", "")
        if dest.exists() and (not expected or sha256(dest) == expected):
            print(f"  ok (cached) {rel}")
            continue
        print(f"  fetch {rel}")
        dest.write_bytes(_get(url))
        got = sha256(dest)
        if expected and got != expected:
            dest.unlink()
            raise SystemExit(f"checksum mismatch for {rel}: {got} != {expected}")
        print(f"    sha256 {got}")


# -- APTnotes PDF subset -----------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _group_aliases(attack_path: Path) -> dict[str, str]:
    """normalised alias -> ATT&CK group id (e.g. 'pawnstorm' -> 'G0007')."""
    bundle = json.loads(attack_path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for o in bundle["objects"]:
        if o.get("type") != "intrusion-set" or o.get("revoked") or o.get("x_mitre_deprecated"):
            continue
        gid = next(r["external_id"] for r in o["external_references"] if r.get("source_name") == "mitre-attack")
        for a in {o["name"], *o.get("aliases", [])}:
            n = _norm(a)
            if len(n) >= 5 and not n.isdigit():  # skip ambiguous short aliases
                out.setdefault(n, gid)
    return out


def fetch_aptnotes(out: Path, max_pdfs: int, max_mb: float, max_pages: int = 40, pdf_timeout: int = 60) -> None:
    attack = out / "enterprise-attack-19.2.json"
    if not attack.exists():
        raise SystemExit("fetch ATT&CK first (--only attack)")
    aliases = _group_aliases(attack)
    api = f"https://api.github.com/repos/kbandla/APTnotes/git/trees/{APTNOTES_PDF_COMMIT}?recursive=1"
    tree = json.loads(_get(api))["tree"]
    pdfs = [t for t in tree if t["path"].lower().endswith(".pdf") and t.get("size", 0) <= max_mb * 1e6]
    labelled = []
    for t in pdfs:
        stem = _norm(Path(t["path"]).stem)
        hits = sorted({gid for a, gid in aliases.items() if a in stem})
        if len(hits) == 1:  # unambiguous single-group label from the filename
            labelled.append((t, hits[0]))
    labelled.sort(key=lambda x: x[0]["path"])
    labelled = labelled[:max_pdfs]
    pdf_dir, txt_dir = out / "aptnotes" / "pdf", out / "aptnotes" / "text"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)
    index = []
    try:
        import pypdf  # noqa: F401  (optional dependency)
        have_pypdf = True
    except ImportError:
        have_pypdf = False
        print("  pypdf not installed: PDFs will be fetched but not converted to text")
    for t, gid in labelled:
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", t["path"])
        dest = pdf_dir / name
        if not dest.exists() or git_blob_sha1(dest.read_bytes()) != t["sha"]:
            url = f"{GH}/kbandla/APTnotes/{APTNOTES_PDF_COMMIT}/" + urllib.parse.quote(t["path"])
            data = _get(url)
            if git_blob_sha1(data) != t["sha"]:
                print(f"  SKIP {t['path']}: blob sha mismatch")
                continue
            dest.write_bytes(data)
        txt = txt_dir / (dest.stem + ".txt")
        if have_pypdf and not txt.exists():
            # pypdf can spin for minutes on pathological PDFs, so each conversion
            # runs in a child process with a hard timeout.
            try:
                subprocess.run([sys.executable, __file__, "--pdf2txt", str(dest), str(txt), str(max_pages)],
                               check=True, timeout=pdf_timeout, capture_output=True)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
                print(f"  SKIP {name}: text extraction failed ({type(exc).__name__})", flush=True)
                txt.unlink(missing_ok=True)
                continue
        if not txt.exists():
            continue
        index.append({"file": dest.name, "text": txt.name, "path": t["path"], "git_sha1": t["sha"], "group": gid})
        print(f"  {gid:<6} {t['path']}", flush=True)
    (out / "aptnotes" / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"  {len(index)} labelled APTnotes reports -> {out / 'aptnotes'}")


def pdf_to_text(pdf: Path, txt: Path, max_pages: int) -> None:
    """Text-only PDF parsing (never rendered or opened in a viewer)."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))
    pages = list(reader.pages)[:max_pages]  # bounded: some report PDFs are huge / image-heavy
    txt.write_text("\n".join((p.extract_text() or "") for p in pages), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--pdf2txt"]:  # internal: child process used by fetch_aptnotes
        pdf_to_text(Path(argv[1]), Path(argv[2]), int(argv[3]))
        return 0
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=DEFAULT_DATA)
    p.add_argument("--only", nargs="+", choices=["attack", "tram", "aptnotes"], default=["attack", "tram", "aptnotes"])
    p.add_argument("--aptnotes-max", type=int, default=120)
    p.add_argument("--aptnotes-max-mb", type=float, default=6.0)
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    print(f"data dir: {a.out}")
    for group in ("attack", "tram", "aptnotes"):
        if group in a.only:
            print(f"[{group}]")
            fetch_pinned(group, a.out)
            if group == "aptnotes":
                fetch_aptnotes(a.out, a.aptnotes_max, a.aptnotes_max_mb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
