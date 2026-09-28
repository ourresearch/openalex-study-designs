"""The judge: Opus, rubric v2 (harness/rubric_v2.py = the schema's definitions). One call per work -> one JSON line.
Cached system block, effort medium, JSON schema output, a second model only when the first refuses, resumable on work_id.
The development set's labels are this script's output with --model claude-opus-5 (label_opus_5) and
--model claude-opus-5-5 (label_opus_5_5). SYSTEM and SCHEMA are also in judge_prompt.md.

  python -m tagger.fetch_works --ids benchmarks/data/dev/dev_set.jsonl.gz --out works.jsonl
  ANTHROPIC_API_KEY=... python harness/judge_v2.py --inp works.jsonl --out judge.jsonl --model claude-opus-5-5 [--limit N]
"""
import argparse, json, os, sys, time, collections, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import anthropic
from rubric_v2 import RULE, DESIGN, NOULS, VERSION
FALLBACK = 'claude-fable-5-1'   # asked only when the judge refuses (5 to 6 of 5,069 works)
CLASSES = list(DESIGN)
SYSTEM = ("You are judging works from OpenAlex, a scholarly index, to build the gold standard for a per-work study-design field. "
          "Your labels define the field, so apply the definitions below literally and consistently.\n\n"
          "Rule: " + RULE + "\n\nStudy design classes (pick exactly one):\n" +
          "\n".join(f"- {k}: {v}" for k, v in DESIGN.items()) +
          "\n\nThen answer two yes/no questions:\n" + "\n".join(f"- {k}: {v}" for k, v in NOULS.items()) +
          "\n\nGive a one-line reason (under 25 words). Judge only what the paper itself reports and states. "
          "Non-English works: read them in their language. If the title and abstract do not say enough, answer unknown rather than guessing.")
SCHEMA = {"type": "object", "properties": {
    "design": {"type": "string", "enum": CLASSES}, "is_rct": {"type": "boolean"}, "human_subjects": {"type": "boolean"},
    "reason": {"type": "string"}}, "required": ["design", "is_rct", "human_subjects", "reason"], "additionalProperties": False}

def work_text(w, cap=6000):
    t = f"Title: {w['title']}\n"
    if w.get('venue'): t += f"Venue: {w['venue']}\n"
    return t + f"Abstract: {(w.get('abstract') or '')[:cap] or '(none)'}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int); ap.add_argument('--concurrency', type=int, default=8)
    ap.add_argument('--model', default='claude-opus-5-5'); ap.add_argument('--cap', type=int, default=6000); ap.add_argument('--effort', default='medium')
    ap.add_argument('--out', required=True); ap.add_argument('--inp', required=True, help='JSONL with work_id, title, venue, abstract'); a = ap.parse_args()
    done = set(json.loads(l)['work_id'] for l in open(a.out) if 'error' not in json.loads(l)) if os.path.exists(a.out) else set()
    works = [json.loads(l) for l in open(a.inp)]; works = [w for w in works if 'error' not in w and w['work_id'] not in done]
    if a.limit: works = works[:a.limit]
    print(f"judge_v2 {a.model} effort={a.effort} {VERSION}: {len(works)} to do ({len(done)} done)", file=sys.stderr, flush=True)
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'], max_retries=4, timeout=600)
    out = open(a.out, 'a'); lock = threading.Lock(); tot = collections.Counter(); t0 = time.time()
    def call(model, txt):
        return client.messages.create(model=model, max_tokens=8000, system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": txt}], output_config={"effort": a.effort, "format": {"type": "json_schema", "schema": SCHEMA}})
    def usage_of(r, model):
        u = r.usage
        return {'in': u.input_tokens, 'out': u.output_tokens, 'cache_read': getattr(u, 'cache_read_input_tokens', 0) or 0,
                'cache_write': getattr(u, 'cache_creation_input_tokens', 0) or 0}
    def one(w):
        ts = time.time(); txt = "Judge this work.\n\n" + work_text(w, a.cap)
        rec = {'work_id': w['work_id'], 'model': a.model, 'effort': a.effort, 'rubric': VERSION}
        try: r = call(a.model, txt)
        except Exception as e: rec['error'] = repr(e)[:400]; return rec
        rec['usage'] = usage_of(r, a.model); rec['stop_reason'] = r.stop_reason
        if r.stop_reason == 'refusal':
            fb = FALLBACK
            try:
                r = call(fb, txt); rec['model'] = fb; rec['fallback'] = True; u2 = usage_of(r, fb); rec['usage'] = {k: rec['usage'][k] + u2[k] for k in u2}
            except Exception as e: rec['error'] = 'fallback failed: ' + repr(e)[:300]; return rec
            if r.stop_reason == 'refusal': rec['error'] = 'refused twice'; return rec
        text = "".join(b.text for b in r.content if b.type == 'text')
        try: ans = json.loads(text)
        except Exception: rec['error'] = 'bad_json'; rec['raw'] = text[:500]; return rec
        rec.update({'design': ans['design'], 'is_rct': bool(ans['is_rct']), 'human_subjects': bool(ans['human_subjects']), 'reason': ans['reason'], 'latency_s': round(time.time() - ts, 1)})
        return rec
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        for f in as_completed({ex.submit(one, w): w for w in works}):
            rec = f.result()
            with lock:
                out.write(json.dumps(rec, ensure_ascii=False) + '\n'); out.flush()
                tot['n'] += 1; tot['err'] += 'error' in rec; tot['fb'] += bool(rec.get('fallback'))
                if 'error' in rec: print(f"ERR {rec['work_id']} {rec['error'][:120]}", file=sys.stderr, flush=True)
                if tot['n'] % 100 == 0 or tot['n'] == len(works):
                    el = time.time() - t0
                    print(f"  checkpoint {tot['n']}/{len(works)} err={tot['err']} fallback={tot['fb']} {el:.0f}s eta {el/tot['n']*(len(works)-tot['n'])/60:.0f}min", file=sys.stderr, flush=True)
    print(f"done n={tot['n']} err={tot['err']} fallback={tot['fb']}", file=sys.stderr, flush=True)
if __name__ == '__main__': main()
