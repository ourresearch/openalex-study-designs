"""Tag works with the study-design tagger: JSONL in, one Jev request per work, JSONL out.

  export JEV_API_KEY=...          # a TypeSafe AI key (https://typesafe.ai)
  python -m tagger.fetch_works --ids ids.txt --out works.jsonl
  python -m tagger.tag --input works.jsonl --out tagged.jsonl [--rps 20] [--concurrency 16] [--limit N]

Input rows: {work_id, title, venue, abstract} (extra fields are ignored). As in production, a work is tagged only when
its title has at least 10 characters and its abstract at least 100 (the tagger is certified on title + abstract), and
OpenAlex runs it only on research-carrying types (article, review, preprint, conference paper, book chapter,
dissertation, report, data paper). Output rows, in input order:
  {work_id, values, scores, is_rct, human_subjects, tagger_values, probabilities, gates, tagger_version, jev_model}
`values` are the study designs OpenAlex would serve; `scores` the eight class scores after the gates; `is_rct` and
`human_subjects` Jev's two yes/no scores; `tagger_values` also keeps other-primary-research. A failed request is
written as {work_id, error}. Rerunning with the same --out skips works already tagged there.

Jev is not bit-deterministic: re-tagging moves probabilities by a few hundredths. On 29 development-set works re-tagged
with this script, every work got the same values as its cached answer, and the largest probability change was 0.13.
The cached answers in benchmarks/data/dev/ are the ones that were certified.
"""
import argparse
import gzip
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tagger import study_design as sd  # noqa: E402

MIN_TITLE, MIN_ABSTRACT = 10, 100


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rps", type=float, default=20.0, help="requests per second (your Jev account's cap applies)")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default=sd.JEV_MODEL, help="Jev snapshot; the tagger is certified on the default only")
    a = ap.parse_args()

    works, skipped = [], 0
    with (gzip.open(a.input, "rt") if a.input.endswith(".gz") else open(a.input)) as f:
        for line in f:
            w = json.loads(line)
            if "error" in w or len(w.get("title") or "") < MIN_TITLE or len(w.get("abstract") or "") < MIN_ABSTRACT:
                skipped += 1
                continue
            works.append(w)
            if a.limit and len(works) >= a.limit:
                break
    done = {}
    if os.path.exists(a.out):
        for line in open(a.out):
            r = json.loads(line)
            if "error" not in r:
                done[r["work_id"]] = r
    todo = [w for w in works if w["work_id"] not in done]
    print(f"{len(works):,} works to consider ({skipped:,} skipped: no abstract, or too short), {len(done):,} already tagged, {len(todo):,} to tag",
          file=sys.stderr, flush=True)

    client = sd.JevClient(concurrency=a.concurrency, rps=a.rps, model=a.model)
    lock = threading.Lock()
    t0 = time.time()
    n = [0, 0]

    def on_result(w, r):
        row = sd.answer_row(w, r) if r.get("ok") else None
        with lock:
            if row is None:
                n[1] += 1
                done[w["work_id"]] = {"work_id": w["work_id"], "error": r.get("error") or "malformed answer",
                                      "status": r.get("status")}
            else:
                n[0] += 1
                done[w["work_id"]] = row
            if sum(n) % 200 == 0:
                el = time.time() - t0
                print(f"  {sum(n):,}/{len(todo):,} ok={n[0]:,} failed={n[1]:,} {sum(n) / el:.1f} works/s", file=sys.stderr, flush=True)

    client.tag_many(todo, on_result)
    with open(a.out, "w") as f:
        for w in works:
            if w["work_id"] in done:
                f.write(json.dumps(done[w["work_id"]], ensure_ascii=False) + "\n")
    print(f"wrote {a.out}: {n[0]:,} tagged, {n[1]:,} failed, {client.total_tokens / max(1, n[0]):.0f} input tokens per work",
          file=sys.stderr)


if __name__ == "__main__":
    main()
