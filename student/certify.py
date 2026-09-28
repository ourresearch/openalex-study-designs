"""Score the student on the 5,069 judged development-set works the way Jev is certified: tagger derive() + gates, the
student's per-class thresholds (student/route.py STUDENT_TAU_POS, chosen on the judged dev split at the bar), reported
pooled with the one-sided 95% lower bound.

  python student/certify.py                                   # the shipped outputs (benchmarks/data/dev/dev_student_outputs.jsonl.gz)
  python student/certify.py --preds student.jsonl             # your own student/infer.py output on the same works
  python student/certify.py --judge opus-5.5
  python student/certify.py --thresholds dev                 # re-pick each threshold on the dev split

Standard library only (no torch): the student's outputs are cached. Under the Opus 5 labels, re-picking on dev gives
exactly STUDENT_TAU_POS. RCT has none (no student score clears 0.99 on dev), so RCT stays with Jev.
"""
import argparse
import collections
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "harness"))
import score as S  # noqa: E402  (harness/score.py)
from run import load_eval, JUDGES, DEV  # noqa: E402
from common import answers_from  # noqa: E402
from route import STUDENT_TAU_POS, student_route  # noqa: E402
from tagger import study_design as sd  # noqa: E402


def load_preds(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        return {r["work_id"]: r for r in map(json.loads, f)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--preds", default=f"{DEV}/dev_student_outputs.jsonl.gz")
    ap.add_argument("--judge", default="opus-5", choices=sorted(JUDGES))
    ap.add_argument("--thresholds", default="shipped", choices=["shipped", "dev"]); a = ap.parse_args()
    works, judged = load_eval(a.judge)
    preds = load_preds(a.preds)
    st = {i: sd.derive_from_gates(answers_from(p["probabilities"], p["is_rct"], p["human_subjects"]), works[i]["gates"])
          for i, p in preds.items() if i in works}
    ids = [i for i in judged if i in st]
    dev = [i for i in ids if judged[i]["split"] == "dev"]
    print(f"student on {len(ids)} judged works (judge {a.judge}); thresholds: "
          + ("student/route.py STUDENT_TAU_POS" if a.thresholds == "shipped" else f"re-picked on the {len(dev)} dev works"))
    print("| Class | bar | t | positives | FP | precision | one-sided 95% lower | recall | route.py TAU_POS |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in S.CLASSES:
        tr = {i: c in S.truth_sets(judged[i]["design"], judged[i].get("is_rct")) for i in ids}
        sw = S.sweep([st[i][c] for i in dev], [tr[i] for i in dev], S.BARS[c])
        tau = STUDENT_TAU_POS.get(c, "none")
        t = STUDENT_TAU_POS.get(c) if a.thresholds == "shipped" else (sw["at_bar"]["t"] if sw["at_bar"] else None)
        if t is None:
            print(f"| {c} | {S.BARS[c]:.2f} | none clears on dev | | | | | | {tau} |"); continue
        pos = [i for i in ids if st[i][c] >= t]; tp = sum(tr[i] for i in pos); nt = sum(tr.values())
        wl = S.wilson_lower(tp, len(pos)); flag = "" if wl >= S.BARS[c] else " (short)"
        print(f"| {c} | {S.BARS[c]:.2f} | {t:.2f} | {len(pos)} | {len(pos) - tp} | {tp / len(pos):.3f} | {wl:.3f}{flag} | {tp / nt:.3f} | {tau} |")
    routes = collections.Counter(student_route(st[i]) for i in st)
    print(f"\nroute on all {len(st)} development-set works: student {routes['student']}, Jev {routes['jev']} "
          "(the set oversamples hard cases; on a uniform sample of the corpus 13.7% went to Jev)")


if __name__ == "__main__":
    main()
