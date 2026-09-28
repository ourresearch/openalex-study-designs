"""Train the student: fine-tune a small encoder to reproduce Jev's study-design outputs (13-way Choice + 2 Nouls).

Input = title \\n venue \\n abstract[:6000], truncated to --maxlen tokens. Loss = soft cross-entropy to Jev's 13
probabilities + binary cross-entropy to each Noul's probability. The released model (student-e5s-v1) is one epoch
over 1,496,608 works Jev had tagged, on one NVIDIA A10G (about 2 h 40 min, bf16 autocast):

  python student/train.py --train train.jsonl.gz --out student-e5s --base intfloat/multilingual-e5-small \\
      --epochs 1 --bs 32 --maxlen 512 --lr 5e-5 --warmup 500 --save-every 4000

Training rows (JSONL, gzip ok): {work_id, title, venue, abstract, probabilities: {13 options}, is_rct, human_subjects,
split}; only rows whose split is in --splits are used. Resumable: --out/last.pt holds model + optimizer + step; rerun
the same command to continue. Runs on CUDA, Apple MPS (slow; smoke tests only) or CPU.
"""
import argparse, gzip, json, math, os, random, sys, time
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
import torch, torch.nn.functional as F
from transformers import AutoTokenizer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CHOICES, NOULS, text_of, build_model

def rows_iter(path):
    f = gzip.open(path, "rt") if path.endswith(".gz") else open(path)
    for l in f: yield json.loads(l)

def load_rows(path, splits, limit, seed=0):
    rows = []
    for r in rows_iter(path):
        if splits and r.get("split", "train") not in splits: continue
        if not r.get("title"): continue
        rows.append(r)
    random.Random(seed).shuffle(rows)
    return rows[:limit] if limit else rows

def targets(r):
    pr = r["probabilities"]; p = torch.tensor([float(pr.get(c, 0.0)) for c in CHOICES]); p = p / p.sum().clamp_min(1e-6)
    n = torch.tensor([float(r.get("is_rct") or 0.0), float(r.get("human_subjects") or 0.0)]).clamp(0, 1)
    return p, n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True); ap.add_argument("--out", required=True); ap.add_argument("--base", default="intfloat/multilingual-e5-small")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--epochs", type=float, default=1.0); ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--maxlen", type=int, default=512); ap.add_argument("--lr", type=float, default=5e-5); ap.add_argument("--splits", default="train")
    ap.add_argument("--log-every", type=int, default=200); ap.add_argument("--save-every", type=int, default=5000); ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--noul-weight", type=float, default=1.0); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    torch.manual_seed(a.seed); os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    rows = load_rows(a.train, set(a.splits.split(",")) if a.splits else None, a.limit, a.seed)
    print(f"{len(rows):,} training rows from {a.train} splits={a.splits} ({time.time()-t0:.0f}s) device={dev}", flush=True)
    tok = AutoTokenizer.from_pretrained(a.base); m = build_model(a.base).to(dev)
    steps_per_epoch = math.ceil(len(rows) / a.bs); total = int(steps_per_epoch * a.epochs)
    opt = torch.optim.AdamW(m.parameters(), lr=a.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / a.warmup) * max(0.0, (total - s) / max(1, total - a.warmup)) if s >= a.warmup else (s + 1) / a.warmup)
    step = 0; last = f"{a.out}/last.pt"
    if os.path.exists(last):
        ck = torch.load(last, map_location=dev); m.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"]); sched.load_state_dict(ck["sched"]); step = ck["step"]
        print(f"resumed at step {step}", flush=True)
    json.dump(vars(a) | {"choices": CHOICES, "nouls": NOULS, "n_rows": len(rows), "total_steps": total}, open(f"{a.out}/train_args.json", "w"), indent=1)
    use_amp = dev == "cuda"
    m.train(); run_loss = run_c = run_n = 0.0; n_run = 0; t1 = time.time()
    def save(tag):
        torch.save({"model": m.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "step": step}, last + ".tmp"); os.replace(last + ".tmp", last)
        torch.save(m.state_dict(), f"{a.out}/{tag}.pt"); tok.save_pretrained(a.out)
        json.dump({"base": a.base, "maxlen": a.maxlen, "choices": CHOICES, "nouls": NOULS, "step": step}, open(f"{a.out}/student.json", "w"))
    while step < total:
        ep = step // steps_per_epoch; i = (step % steps_per_epoch) * a.bs
        if i == 0 and step > 0: random.Random(a.seed + ep).shuffle(rows)
        batch = rows[i:i + a.bs]
        if not batch: step += 1; continue
        enc = tok([text_of(r) for r in batch], padding=True, truncation=True, max_length=a.maxlen, return_tensors="pt")
        P = torch.stack([targets(r)[0] for r in batch]).to(dev); N = torch.stack([targets(r)[1] for r in batch]).to(dev)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=use_amp):
            lc, ln = m(enc["input_ids"].to(dev), enc["attention_mask"].to(dev))
        lc = lc.float(); ln = ln.float()
        loss_c = -(P * F.log_softmax(lc, -1)).sum(-1).mean(); loss_n = F.binary_cross_entropy_with_logits(ln, N)
        loss = loss_c + a.noul_weight * loss_n
        opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step(); sched.step(); step += 1
        run_loss += loss.item(); run_c += loss_c.item(); run_n += loss_n.item(); n_run += 1
        if step % a.log_every == 0 or step == total:
            el = time.time() - t1; rate = n_run * a.bs / el if el else 0
            print(f"step {step}/{total} ep {ep} loss {run_loss/n_run:.4f} (choice {run_c/n_run:.4f} noul {run_n/n_run:.4f}) lr {sched.get_last_lr()[0]:.2e} {rate:.0f} ex/s eta {(total-step)*a.bs/max(rate,1e-6)/60:.0f} min", flush=True)
            prog = {"step": step, "total": total, "loss": run_loss / n_run, "ex_per_s": rate, "eta_min": (total - step) * a.bs / max(rate, 1e-6) / 60, "t": time.time()}
            with open(f"{a.out}/progress.json", "w") as f: json.dump(prog, f)
            run_loss = run_c = run_n = 0.0; n_run = 0; t1 = time.time()
        if step % a.save_every == 0: save("model")
    save("model"); print(f"done: {step} steps, {time.time()-t0:.0f}s, saved {a.out}/model.pt", flush=True)

if __name__ == "__main__": main()
