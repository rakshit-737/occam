#!/usr/bin/env python
"""Resolve every identifier in paper/refs.bib and check it against the entry.

For each BibTeX entry:

* ``doi``    -- resolved through https://doi.org with content negotiation
  (CSL-JSON); the returned title, first-author family name and year are
  compared with the entry;
* ``eprint`` -- looked up in the arXiv API (export.arxiv.org; falls back to the
  abstract page's citation meta tags when the API rate-limits); title, first
  author and year are compared;
* ``url``    -- fetched (GET, redirects followed); the HTTP status, content type
  and, for HTML, the page title are recorded. Hosts that refuse scripted
  requests (HTTP 401/403/429) are recorded as needing a manual check, not as
  failures.

Writes ``paper/refs_check.log`` and exits 1 if any DOI or arXiv record does not
resolve or does not match. Network access is needed; requests are spaced out.

Usage::

    python scripts/check_refs.py            # -> paper/refs_check.log
    python scripts/check_refs.py --bib paper/refs.bib --log -
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UA = "occam-refcheck/1.0 (+https://github.com/rakshit-737/occam)"
PAUSE = 3.0  # seconds between requests (arXiv asks for >= 3 s)


def parse_bib(text: str) -> list[dict]:
    """Minimal BibTeX parser for this file: @type{key, field = {value}, ...}."""
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        i, depth = m.end(), 1
        j = i
        while depth and j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        body = text[i:j - 1]
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*", body):
            k = f.group(1).lower()
            rest = body[f.end():]
            if rest.startswith("{"):
                d, n = 1, 1
                while d and n < len(rest):
                    d += {"{": 1, "}": -1}.get(rest[n], 0)
                    n += 1
                fields.setdefault(k, rest[1:n - 1])
            else:
                fields.setdefault(k, rest.split(",")[0].strip())
        entries.append({"type": m.group(1).lower(), "key": m.group(2), **fields})
    return entries


def norm(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+|[{}\\]", "", s or "")
    s = unicodedata.normalize("NFKD", html.unescape(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def first_author(bib_author: str) -> str:
    a = (bib_author or "").split(" and ")[0]
    return norm(a.split(",")[0] if "," in a else a.split()[-1] if a.split() else "")


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def get(url: str, accept: str | None = None, retries: int = 4) -> tuple[int, str, bytes]:
    headers = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if accept:
        headers["Accept"] = accept
    for k in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                data = r.read(4_000_000)
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return r.status, r.headers.get("Content-Type", ""), data
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and k + 1 < retries:
                time.sleep(PAUSE * 4 * (k + 1))
                continue
            return e.code, e.headers.get("Content-Type", "") if e.headers else "", b""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if k + 1 < retries:
                time.sleep(PAUSE * 2 * (k + 1))
                continue
            return 0, f"error: {e}", b""
    return 0, "error: retries exhausted", b""


def check_doi(e: dict) -> tuple[bool, str]:
    doi = e["doi"]
    st, _, data = get("https://doi.org/" + urllib.parse.quote(doi, safe="/()<>;:.-"),
                      accept="application/vnd.citationstyles.csl+json")
    if st != 200 or not data:
        return False, f"doi {doi}: HTTP {st}"
    c = json.loads(data)

    def one(x) -> str:
        return (x[0] if x else "") if isinstance(x, list) else (x or "")

    title, subtitle = one(c.get("title")), one(c.get("subtitle"))
    fam = norm((c.get("author") or [{}])[0].get("family", ""))
    # registries record the online and the print date; a journal article is often online the year before its issue
    years = {str(((c.get(k) or {}).get("date-parts") or [[None]])[0][0]) for k in ("issued", "published-print", "published-online")}
    years.discard("None")
    venue = one(c.get("container-title")) or one(c.get("publisher"))
    bib_title = e.get("title", "")
    t_ok = max(similar(title, bib_title), similar(f"{title} {subtitle}", bib_title),
               similar(title, bib_title.split(":")[0])) >= 0.85
    a_ok, y_ok = fam == first_author(e.get("author", "")), e.get("year") in years
    ok = t_ok and a_ok and y_ok
    shown = f"{title}: {subtitle}" if subtitle else title
    return ok, (f"doi {doi}: HTTP 200, title {'match' if t_ok else 'MISMATCH'} ({shown!r}), first author "
                f"{'match' if a_ok else 'MISMATCH'} ({fam}), year {'match' if y_ok else 'MISMATCH'} "
                f"(registry dates: {', '.join(sorted(years))}), venue {venue!r}")


def _arxiv_api(aid: str) -> tuple[str, list[str], str] | None:
    st, _, data = get(f"https://export.arxiv.org/api/query?id_list={aid}&max_results=1", retries=2)
    x = data.decode("utf-8", "replace")
    if st != 200 or "<entry>" not in x:
        return None
    entry = x.split("<entry>", 1)[1]
    t = re.search(r"<title>(.*?)</title>", entry, re.S)
    p = re.search(r"<published>(\d{4})", entry)
    if not t or not p:
        return None
    return " ".join(t.group(1).split()), re.findall(r"<name>(.*?)</name>", entry), p.group(1)


def _arxiv_abs(aid: str) -> tuple[str, list[str], str] | None:
    st, _, data = get(f"https://arxiv.org/abs/{aid}")
    x = data.decode("utf-8", "replace")
    t = re.search(r'<meta name="citation_title" content="([^"]*)"', x)
    d = re.search(r'<meta name="citation_date" content="(\d{4})', x)
    if st != 200 or not t or not d:
        return None
    authors = [html.unescape(a) for a in re.findall(r'<meta name="citation_author" content="([^"]*)"', x)]
    return html.unescape(t.group(1)), authors, d.group(1)


def check_arxiv(e: dict) -> tuple[bool, str]:
    aid = e["eprint"]
    rec, src = _arxiv_api(aid), "arXiv API"
    if rec is None:
        time.sleep(PAUSE)
        rec, src = _arxiv_abs(aid), "arXiv abstract page"
    if rec is None:
        return False, f"arXiv {aid}: not resolved (API and abstract page)"
    title, authors, year = rec
    a0 = authors[0] if authors else ""
    fam = norm(a0.split(",")[0] if "," in a0 else a0.split()[-1] if a0.split() else "")
    t_ok, a_ok, y_ok = similar(title, e.get("title", "")) >= 0.85, fam == first_author(e.get("author", "")), year == e.get("year")
    return t_ok and a_ok and y_ok, (f"arXiv {aid} ({src}): title {'match' if t_ok else 'MISMATCH'} ({title!r}), first author "
                                    f"{'match' if a_ok else 'MISMATCH'} ({a0}), year {'match' if y_ok else 'MISMATCH'} ({year})")


def check_url(e: dict) -> tuple[bool | None, str]:
    url = e["url"]
    st, ctype, data = get(url, retries=2)
    if st in (401, 403, 429):
        return None, f"url {url}: HTTP {st} to scripted requests -> MANUAL CHECK"
    if st != 200:
        return False, f"url {url}: HTTP {st} {ctype}"
    what = ctype.split(";")[0]
    if "html" in what:
        t = re.search(rb"<title[^>]*>(.*?)</title>", data, re.S | re.I)
        title = " ".join(html.unescape(t.group(1).decode("utf-8", "replace")).split()) if t else ""
        hit = similar(title, e.get("title", "")) >= 0.5 or norm(e.get("title", ""))[:30] in norm(data.decode("utf-8", "replace"))
        return True, f"url {url}: HTTP 200 {what}, page title {title!r}, entry title {'found' if hit else 'NOT found'} on page"
    return True, f"url {url}: HTTP 200 {what}, {len(data)} bytes"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bib", type=Path, default=REPO / "paper" / "refs.bib")
    ap.add_argument("--log", default=str(REPO / "paper" / "refs_check.log"), help="log file, or - for stdout")
    a = ap.parse_args(argv)
    entries = parse_bib(a.bib.read_text(encoding="utf-8"))
    lines = [f"# refs.bib identifier check, {dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}",
             f"# script: scripts/check_refs.py; {len(entries)} entries", ""]
    failed, manual, unresolved = [], [], []
    for e in entries:
        lines.append(f"[{e['key']}] {e['type']}: {norm(e.get('title', ''))[:90]}")
        checks = []
        if "doi" in e:
            checks.append(("doi", *check_doi(e)))
            time.sleep(PAUSE)
        if "eprint" in e:
            checks.append(("arxiv", *check_arxiv(e)))
            time.sleep(PAUSE)
        if "url" in e:
            checks.append(("url", *check_url(e)))
            time.sleep(PAUSE)
        if not checks:
            unresolved.append(e["key"])
            lines.append("  NO IDENTIFIER (no doi, eprint or url)")
        for kind, ok, msg in checks:
            lines.append(f"  {'OK    ' if ok else 'MANUAL' if ok is None else 'FAIL  '} {msg}")
            if ok is None:
                manual.append(e["key"])
            elif not ok and kind in ("doi", "arxiv"):
                failed.append(e["key"])
            elif not ok:
                failed.append(e["key"])
        lines.append("")
    lines.append(f"# summary: {len(entries)} entries; failed: {sorted(set(failed)) or 'none'}; "
                 f"manual check needed: {sorted(set(manual)) or 'none'}; without identifier: {unresolved or 'none'}")
    text = "\n".join(lines) + "\n"
    if a.log == "-":
        print(text)
    else:
        Path(a.log).write_text(text, encoding="utf-8")
        print(text)
    return 1 if failed or unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
