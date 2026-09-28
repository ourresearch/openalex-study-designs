"""The RCT check: a second model reads every work the tagger serves as a randomized controlled trial and says whether it
is the trial's own report. Where it says no, OpenAlex serves neither Randomized Controlled Trial nor Clinical Trial.

Why: Jev reads literally, so digests, journal-club pieces and commentaries that reprint another trial's abstract look
like the trial to it, and neither thresholds, venue rules nor an extra Jev question separated them. On 2,119 judged
RCT-tagged works (benchmarks/data/calibration and the first certification sample) this check removed 43 of 58 wrong
tags and 11 of 2,054 right ones. The prompt was written after reading those errors, so it is scored on a fresh sample
(benchmarks/data/pubmed).

    python3 tagger/rct_check.py --input works.jsonl --out checks.jsonl     # needs `pip install anthropic`, ANTHROPIC_API_KEY

Input rows: work_id, title, venue, abstract (tagger/fetch_works.py writes them). Resumable: skips work_ids in --out.
"""
import argparse, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

MODEL = "claude-sonnet-5"
FALLBACK_MODEL = "claude-opus-5-5"   # asked only when MODEL refuses (it declines some ordinary biomedical papers)
SYSTEM = "You check one claim about a scholarly work for an index that must not mislabel papers: that this work is the original report of a randomized controlled trial's results. Read the title, the venue and the abstract. Say no when the work is a summary, digest, journal-club piece, commentary, editorial, letter, news item, review or reprinted abstract of a trial published elsewhere (signs: a digest or evidence-summary venue, a title that reads as a comment or a theme rather than the trial, an abstract that describes another group's trial); when it is a protocol; when it is a secondary, post-hoc, subgroup, exploratory, mediation or pooled analysis of an earlier trial's data; when the units randomized are not people, clusters of people or treatment periods (animals, firms, documents, devices); or when the text never states that allocation was random ('randomly selected' patients is sampling, not allocation). Primary, updated, follow-up or extension results of the trial itself count as yes."
SCHEMA = {'type': 'object', 'properties': {'own_trial_report': {'type': 'boolean'}, 'reason': {'type': 'string'}}, 'required': ['own_trial_report', 'reason'], 'additionalProperties': False}
ABSTRACT_CHARS = 6000


def work_text(w: dict) -> str:
    return f"Title: {w.get('title') or ''}\nVenue: {w.get('venue') or ''}\nAbstract: {(w.get('abstract') or '')[:ABSTRACT_CHARS]}"


def check(client, w: dict, model: str = MODEL) -> dict:
    """One work -> {work_id, own_trial_report, reason, model, in, out, checked_at}, or {work_id, error}."""
    def ask(mdl):
        return client.messages.create(model=mdl, max_tokens=4000,   # room for the model's own reasoning before the JSON
                                      system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                                      messages=[{"role": "user", "content": work_text(w)}],
                                      output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
    try:
        m = ask(model)
        if m.stop_reason == "refusal":
            model = FALLBACK_MODEL
            m = ask(model)
        ans = json.loads("".join(b.text for b in m.content if b.type == "text"))
        return {"work_id": w["work_id"], "own_trial_report": bool(ans["own_trial_report"]), "reason": ans["reason"][:400],
                "model": model, "in": m.usage.input_tokens, "out": m.usage.output_tokens,
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    except Exception as e:  # malformed JSON (rare) or an API error: the next run retries it
        return {"work_id": w["work_id"], "error": repr(e)[:300]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY"),
                                 max_retries=8, timeout=300)
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            r = json.loads(line)
            if "error" not in r:
                done.add(r["work_id"])
    todo = [w for w in map(json.loads, open(a.input)) if w["work_id"] not in done]
    lock, out, n = threading.Lock(), open(a.out, "a"), [0, 0]

    def one(w):
        r = check(client, w, a.model)
        with lock:
            out.write(json.dumps(r) + "\n"); out.flush()
            n[0] += 1; n[1] += "error" in r
            if n[0] % 500 == 0:
                print(f"  {n[0]:,}/{len(todo):,} errors={n[1]}", file=sys.stderr, flush=True)

    with ThreadPoolExecutor(a.concurrency) as ex:
        list(ex.map(one, todo))
    print(f"wrote {a.out}: {n[0]:,} checked, {n[1]} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
