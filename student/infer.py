"""Run the student over works and decide, per work, whether its answer stands or the work goes to Jev.

  python student/infer.py --model student-e5s --input works.jsonl --out student.jsonl [--bs 64] [--limit N]

--model is the unpacked release asset (student-e5s-v1.tar.gz: model.pt, student.json, tokenizer files). --input is
JSONL with work_id, title, venue, abstract (python -m tagger.fetch_works makes it). The base model's configuration
and weights are fetched once from the Hugging Face Hub (intfloat/multilingual-e5-small); the fine-tuned weights then
replace every weight.

Output row: {work_id, probabilities: {13 options}, is_rct, human_subjects, scores: {8 classes}, route, values}.
`scores` go through tagger.study_design.derive() and its gates, exactly as Jev's answers do. `route` is "student" when
the student may tag the work on its own (student/route.py); then `values` are its study designs. When `route` is
"jev", `values` is null: in production that work went to Jev.

On a GPU the encoder runs in bf16 autocast, as in production; on CPU or Apple MPS in fp32, which moves probabilities
by about 0.001 on average (at most 0.008 on 300 judged works).
"""
import argparse
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from common import CHOICES, NOULS, answers_from, build_model, text_of  # noqa: E402
from route import student_route, student_values  # noqa: E402
from tagger import study_design as sd  # noqa: E402


class StudentModel:
    """Loads <model_dir>/{student.json, model.pt, tokenizer files}; predict(works) -> list of (probs, is_rct, human)."""

    def __init__(self, model_dir, device=None, batch_size=128):
        import torch
        from transformers import AutoTokenizer

        meta = json.load(open(os.path.join(model_dir, "student.json")))
        assert meta["choices"] == CHOICES and meta["nouls"] == NOULS, "student.json disagrees with student/common.py"
        self.maxlen = int(meta["maxlen"])
        self.device = device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        self.bs = batch_size
        self.model = build_model(meta["base"])
        self.model.load_state_dict(torch.load(os.path.join(model_dir, "model.pt"), map_location="cpu"))
        self.model.to(self.device).eval()
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.meta = meta

    def predict(self, works, progress=False):
        import torch

        out = [None] * len(works)
        order = sorted(range(len(works)), key=lambda i: len(text_of(works[i])))   # length-sorted batches pad less
        t0 = time.time()
        with torch.no_grad():
            for s in range(0, len(order), self.bs):
                idx = order[s:s + self.bs]
                enc = self.tok([text_of(works[i]) for i in idx], padding=True, truncation=True, max_length=self.maxlen,
                               return_tensors="pt")
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=self.device == "cuda"):
                    lc, ln = self.model(enc["input_ids"].to(self.device), enc["attention_mask"].to(self.device))
                pc = torch.softmax(lc.float(), -1).cpu().numpy()
                pn = torch.sigmoid(ln.float()).cpu().numpy()
                for j, i in enumerate(idx):
                    out[i] = ({c: round(float(p), 4) for c, p in zip(CHOICES, pc[j])}, round(float(pn[j][0]), 4),
                              round(float(pn[j][1]), 4))
                if progress and (s // self.bs) % 50 == 0:
                    print(f"  {s + len(idx):,}/{len(works):,} {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
        return out


def row_for(w, probs, is_rct, human):
    scores = sd.derive(answers_from(probs, is_rct, human), w)
    route = student_route(scores)
    return {"work_id": w["work_id"], "probabilities": probs, "is_rct": is_rct, "human_subjects": human,
            "scores": scores, "route": route, "values": student_values(scores) if route == "student" else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    works = []
    with (gzip.open(a.input, "rt") if a.input.endswith(".gz") else open(a.input)) as f:
        for line in f:
            w = json.loads(line)
            if "error" in w:
                continue
            works.append(w)
            if a.limit and len(works) >= a.limit:
                break
    m = StudentModel(a.model, batch_size=a.bs)
    t0 = time.time()
    preds = m.predict(works, progress=True)
    with open(a.out, "w") as f:
        for w, (probs, is_rct, human) in zip(works, preds):
            f.write(json.dumps(row_for(w, probs, is_rct, human)) + "\n")
    el = max(time.time() - t0, 1e-6)
    print(f"wrote {a.out}: {len(works):,} works, {len(works) / el:.0f} works/s on {m.device}", file=sys.stderr)


if __name__ == "__main__":
    main()
