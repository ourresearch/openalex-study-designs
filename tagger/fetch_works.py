"""Fetch title, venue and abstract for OpenAlex work ids from the public API (standard library only).

The repo never ships abstracts or titles (publishers hold the copyright); its datasets carry work ids and labels. This
script rebuilds the text the tagger reads, from https://api.openalex.org, 100 ids per request. The abstract is rebuilt
from OpenAlex's inverted index. Ids the batch filter does not return are fetched one at a time.

  python -m tagger.fetch_works --ids benchmarks/data/dev/dev_set.jsonl.gz --out works.jsonl --mailto you@example.org
  python -m tagger.fetch_works --ids ids.txt --out works.jsonl          # one id per line (W123, or an openalex.org URL)

Output, one line per work: {work_id, doi, pmid, title, venue, abstract}; the input of tagger/tag.py. A work OpenAlex
no longer serves gets {"work_id": ..., "error": ...}. Texts can change upstream, so a rebuilt abstract may differ from
the one the tagger read in September 2026.
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openalex.org"
SELECT = "id,doi,ids,title,primary_location,abstract_inverted_index"


def short_id(x) -> str:
    """'https://openalex.org/W123', 'W123' or 123 -> 'W123'."""
    x = str(x).strip().rsplit("/", 1)[-1]
    return x if x.upper().startswith("W") else f"W{x}"


def read_ids(path: str) -> list:
    op = gzip.open if path.endswith(".gz") else open
    ids = []
    with op(path, "rt") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ids.append(short_id(json.loads(line)["work_id"] if line.startswith("{") else line))
    return list(dict.fromkeys(ids))


def abstract_from_index(inv) -> str:
    if not inv:
        return ""
    pos = [(i, w) for w, idx in inv.items() for i in idx]
    return " ".join(w for _, w in sorted(pos))


def get(url: str, api_key: str = "", attempts: int = 6) -> dict:
    headers = {"User-Agent": "openalex-study-designs"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    for k in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"error": "not found"}
            if e.code not in (429, 500, 502, 503, 504) or k == attempts - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if k == attempts - 1:
                raise
        time.sleep(min(30, 2 ** k))
    return {"error": "gave up"}


def row_of(rec: dict, work_id: str) -> dict:
    loc = rec.get("primary_location") or {}
    src = loc.get("source") or {}
    pmid = (rec.get("ids") or {}).get("pmid")
    return {"work_id": work_id,
            "doi": (rec.get("doi") or "").replace("https://doi.org/", "") or None,
            "pmid": pmid.rsplit("/", 1)[-1] if pmid else None,
            "title": rec.get("title") or "",
            "venue": src.get("display_name") or "",
            "abstract": abstract_from_index(rec.get("abstract_inverted_index"))}


def params(extra: dict, mailto: str) -> str:
    p = dict(extra)
    if mailto:
        p["mailto"] = mailto
    return urllib.parse.urlencode(p, safe=":|,")


def fetch(ids: list, mailto: str = "", api_key: str = "", sleep: float = 0.1) -> list:
    out = {}
    for s in range(0, len(ids), 100):
        chunk = ids[s:s + 100]
        q = params({"filter": "openalex:" + "|".join(chunk), "select": SELECT, "per_page": 100}, mailto)
        for rec in get(f"{API}/works?{q}", api_key).get("results", []):
            wid = short_id(rec["id"])
            if wid in chunk:
                out[wid] = row_of(rec, wid)
        print(f"  {min(s + 100, len(ids)):,}/{len(ids):,} ids, {len(out):,} works", file=sys.stderr, flush=True)
        time.sleep(sleep)
    missed = [i for i in ids if i not in out]
    if missed:
        print(f"  {len(missed):,} ids not returned by the batch filter; fetching one by one", file=sys.stderr, flush=True)
    for i in missed:   # the batch filter can miss recent ids that /works/{id} serves; merged works resolve here too
        rec = get(f"{API}/works/{i}?{params({'select': SELECT}, mailto)}", api_key)
        out[i] = {"work_id": i, "error": rec["error"]} if "error" in rec else row_of(rec, i)
        time.sleep(sleep)
    return [out[i] for i in ids]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ids", required=True, help="text file of ids, or a JSONL(.gz) with a work_id field")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mailto", default=os.environ.get("OPENALEX_MAILTO", ""), help="your email (OpenAlex's polite pool)")
    ap.add_argument("--api-key", default=os.environ.get("OPENALEX_API_KEY", ""),
                    help="optional OpenAlex API key (sent as a Bearer header), for more than the anonymous daily credits")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    ids = read_ids(a.ids)
    if a.limit:
        ids = ids[:a.limit]
    rows = fetch(ids, a.mailto, a.api_key)
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_err = sum("error" in r for r in rows)
    n_abs = sum(bool(r.get("abstract")) for r in rows)
    print(f"wrote {a.out}: {len(rows):,} works, {n_abs:,} with an abstract, {n_err:,} not served", file=sys.stderr)


if __name__ == "__main__":
    main()
