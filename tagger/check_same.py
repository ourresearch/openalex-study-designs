"""Check that tagger/study_design.py derives exactly what the certified configuration derives, work for work.

  python -m tagger.check_same                                   # vs harness/configs/r2_gate4.py, cached gates, no text
  python -m tagger.check_same --works works.jsonl               # the same, gates recomputed from the text (fetch_works)
  python -m tagger.check_same --reference other/study_design.py --works works.jsonl   # vs another copy of the module

For every cached Jev answer on the development set (benchmarks/data/dev/dev_jev_outputs.jsonl.gz) it compares the
eight class scores (exact float equality), the values, and each of the three gates; with text, also the Jev request
(questions() and state_for(), as JSON); with a reference module, every constant both modules define. It prints the
mismatch count per check and exits 1 if any is not zero.
"""
import argparse
import gzip
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tagger import study_design as sd  # noqa: E402

OUTPUTS = f"{ROOT}/benchmarks/data/dev/dev_jev_outputs.jsonl.gz"
CONSTANTS = ["JEV_URL", "JEV_MODEL", "CONFIG_NAME", "TAGGER_VERSION", "ABSTRACT_CHARS", "RULE", "DESIGN", "NOULS", "CLASSES",
             "THRESHOLDS", "SERVED_THRESHOLDS", "SCORE_EPS", "VALUE_ID", "PARENT", "SERVED_CLASSES", "DISPLAY_NAME", "DESCRIPTION", "PUBMED_MAP"]
GATES = ["stated_random", "simulation_title", "secondary_title"]


def opn(p):
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def load_module(path):
    spec = importlib.util.spec_from_file_location("reference_study_design", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reference", help="path to another study_design.py; default: the harness config r2_gate4")
    ap.add_argument("--works", help="JSONL with work_id, title, venue, abstract (python -m tagger.fetch_works)")
    ap.add_argument("--outputs", default=OUTPUTS, help="cached Jev answers (work_id, answers, gates)")
    a = ap.parse_args()
    if a.reference and not a.works:
        sys.exit("--reference needs --works: another module's gates read the text")

    rows = [json.loads(line) for line in opn(a.outputs)]
    text = {}
    if a.works:
        for line in opn(a.works):
            r = json.loads(line)
            if "error" not in r:
                text[str(r["work_id"])] = r

    mism = {"scores": 0, "values": 0, **{g: 0 for g in GATES}, "stored_scores": 0, "request": 0, "constants": 0, "served": 0}
    n = 0
    if a.reference:
        ref = load_module(a.reference)
        ref_name = a.reference
        ref_derive = ref.derive
        ref_values = getattr(ref, "tagger_values", None)
        ref_gates = {g: getattr(ref, g) for g in GATES if hasattr(ref, g)}
        for c in CONSTANTS:
            if hasattr(ref, c) and json.dumps(getattr(ref, c)) != json.dumps(getattr(sd, c)):
                print(f"  constant differs: {c}")
                mism["constants"] += 1
        for c in ("RAND", "SIM", "SECONDARY"):
            if hasattr(ref, c) and (getattr(ref, c).pattern, getattr(ref, c).flags) != (getattr(sd, c).pattern, getattr(sd, c).flags):
                print(f"  regex differs: {c}")
                mism["constants"] += 1
        if json.dumps(ref.questions()) != json.dumps(sd.questions()):
            mism["request"] += 1
        tags = list(sd.PUBMED_MAP) + ["Review", "Journal Article", "Scoping Review"]
        if hasattr(ref, "pubmed_values") and any(ref.pubmed_values([t]) != sd.pubmed_values([t]) for t in tags):
            mism["constants"] += 1
        if hasattr(ref, "pubmed_values") and ref.pubmed_values(tags) != sd.pubmed_values(tags):
            mism["constants"] += 1
    else:   # the certified config, as the harness scores it
        sys.path.insert(0, f"{ROOT}/harness")
        import textsig
        from configs import r2_gate4, r2_shortnoul
        ref_name = "harness/configs/r2_gate4.py"
        ref_derive = r2_gate4.derive
        ref_values = None
        ref_gates = {g: getattr(textsig, g) for g in GATES}
        if json.dumps(r2_shortnoul.questions()) != json.dumps(sd.questions()):
            mism["request"] += 1

    for r in rows:
        wid = r["work_id"]
        w = text.get(wid)
        if a.works and w is None:
            continue   # not served by OpenAlex any more
        n += 1
        if w is None:
            w = {"work_id": wid, "gates": r["gates"]}     # no text: the stored gate answers stand in
            ours = sd.derive_from_gates(r["answers"], r["gates"])
            our_gates = r["gates"]
        else:
            w = dict(w, work_id=wid)
            ours = sd.derive(r["answers"], w)
            our_gates = sd.gates(w)
            if a.reference and json.dumps(ref.state_for(w)) != json.dumps(sd.state_for(w)):
                mism["request"] += 1
            if not a.reference:
                from configs import r2_shortnoul
                if json.dumps(r2_shortnoul.state_for(w)) != json.dumps(sd.state_for(w)):
                    mism["request"] += 1
        theirs = ref_derive(r["answers"], w)
        if any(ours[c] != theirs.get(c) for c in sd.CLASSES) or set(theirs) != set(ours):
            mism["scores"] += 1
        if ref_values and ref_values(theirs) != sd.tagger_values(ours):
            mism["values"] += 1
        ref_served = getattr(ref, "served_classes", None) if a.reference else None
        if ref_served and ref_served(theirs) != sd.served_classes(ours):
            mism["served"] += 1
        for g, f in ref_gates.items():
            if bool(f(w)) != bool(our_gates[g]):
                mism[g] += 1
        if not a.works and ours != r["scores"]:
            mism["stored_scores"] += 1
    print(f"tagger/study_design.py vs {ref_name}: {n:,} cached development-set answers"
          f"{' with text' if a.works else ' (stored gate answers, no text)'}")
    for k, v in mism.items():
        print(f"  {k:18s} {v} mismatches")
    total = sum(mism.values())
    print(f"total mismatches: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
